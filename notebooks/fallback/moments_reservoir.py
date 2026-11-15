#!/usr/bin/env python
# coding: utf-8

# # Fallback: stream moments (AMS) and reservoir sampling
# 
# **Fallback, built by Claude for Scott.** This notebook exists so that the rubric technique is covered if the teammate's own notebook does not arrive. Teammate work always wins: if a teammate's notebook arrives, use it and drop this one. Written with Claude Code (see `docs/final/GENAI_LOG.md`). No edit comment and no editor name is shown in any output.
# 
# **Why.** `etl/streaming_algos.py` already measures an AMS estimate and one reservoir sample (notebook 05). This notebook measures both properly: error against the number of variables or the sample size, over many seeds, against exact answers.
# 
# **Input.** The enwiki page-change events of `silver/page_change` in publish order up to 2026-11-13 (the same stream as notebook 05), and the cohort `live_ext` of `gold/fact_edit`.
# 
# **Measured.** (1) Frequency moments of edits per page: exact F0, F1, F2, and the Alon-Matias-Szegedy estimate of F2 for 100 to 10,000 variables over 30 seeds. (2) Reservoir sampling (Algorithm L, one pass, fixed memory): error of the revert share for sample sizes 1,000 to 100,000 over 200 reservoirs, against the binomial standard error; and a reservoir draw of not-reverted edits as an alternative to the sample in the LSH export.
# 
# **Output.** `data/lake/_runs/fallback_moments.json`.

# In[1]:


import json, os, sys, time, re, math
from pathlib import Path
REPO = Path.cwd().resolve().parents[1] if Path.cwd().name == 'fallback' else Path.cwd()
sys.path.insert(0, str(REPO))
os.environ.setdefault('TRUTHLAG_HW2_DIR', str(REPO / 'ec-hw2'))
import numpy as np, pandas as pd
pd.set_option('display.width', 170); pd.set_option('display.max_columns', 30)
EXPORTS = REPO / 'data' / 'exports'
RUNS = REPO / 'data' / 'lake' / '_runs'
SEED = 226
def save_facts(name, facts, extra=None):
    doc = {'facts': facts, **(extra or {})}
    (RUNS / name).write_text(json.dumps(doc, indent=1, default=str))
    print('wrote', (RUNS / name).relative_to(REPO), 'with', len(facts), 'facts')


# ## 1. The stream

# In[2]:


from etl import streaming_algos, lake_config
t = streaming_algos.load_stream()
kind = np.array(t.column('kind').to_pylist())
is_edit = kind == 'edit'
page = t.column('page_id').to_numpy(zero_copy_only=False)[is_edit]
is_revert = np.array([m is not None for m in t.column('revert_method').to_pylist()])[is_edit]
n = len(page)
_, inv, counts = np.unique(page, return_inverse=True, return_counts=True)
F0, F1, F2 = int(len(counts)), int(n), int((counts.astype(np.int64) ** 2).sum())
print('edit events:', n, '| F0 (distinct pages):', F0, '| F1:', F1, '| F2 (sum of squared edits per page):', F2)
print('edits per page: mean', round(F1 / F0, 2), '| max', int(counts.max()), '| pages with one edit:', int((counts == 1).sum()))


# ## 2. AMS estimate of the second moment
# 
# For a random position q, let c be the number of times the page at q appears from q to the end. X = n (2c - 1) has expectation F2. Take v such variables, average them in 10 groups and report the median of the group means.

# In[3]:


# c for every position at once: occurrences of the page from this position on
order = np.argsort(inv, kind='stable')
rank = np.empty(n, dtype=np.int64)
starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
rank[order] = np.arange(n) - np.repeat(starts, counts)        # 0-based rank of this occurrence within its page
c_all = counts[inv] - rank
X_all = n * (2.0 * c_all - 1.0)
assert abs(X_all.mean() - F2) / F2 < 1e-9                     # the estimator is unbiased over all positions
rows = []
SEEDS = 30
for v in (100, 300, 1000, 3000, 10000):
    errs = []
    for s in range(SEEDS):
        r = np.random.default_rng(SEED + s)
        x = X_all[r.integers(0, n, size=v)]
        est = np.median([g.mean() for g in np.array_split(x, 10)])
        errs.append(100 * (est - F2) / F2)
    errs = np.array(errs)
    rows.append({'variables': v, 'mean_error_pct': round(float(errs.mean()), 2), 'mean_abs_error_pct': round(float(np.abs(errs).mean()), 2),
                 'worst_abs_error_pct': round(float(np.abs(errs).max()), 2), 'memory_bytes': v * 16})
ams = pd.DataFrame(rows)
ams


# Edits per page are heavy-tailed (a few pages carry a large share of F2), so the median of means sits below F2 until the sample is large enough to hit those pages.

# ## 3. Reservoir sampling (Algorithm L)

# In[4]:


def reservoir_positions(n, k, rng):
    """Positions of a uniform sample of k items from a stream of n, in one pass with k slots (Li's Algorithm L)."""
    res = np.arange(k)
    w = math.exp(math.log(rng.random()) / k)
    i = k - 1
    while True:
        i += int(math.log(rng.random()) / math.log(1.0 - w)) + 1
        if i >= n:
            return res
        res[rng.integers(0, k)] = i
        w *= math.exp(math.log(rng.random()) / k)

p_true = float(is_revert.mean())
rows = []
RUNS_PER_K = 200
for k in (1000, 10000, 100000):
    est, pos = [], []
    for s in range(RUNS_PER_K):
        idx = reservoir_positions(n, k, np.random.default_rng(SEED + s))
        est.append(is_revert[idx].mean()); pos.append(idx.mean() / n)
    est = np.array(est)
    se = math.sqrt(p_true * (1 - p_true) / k)
    rows.append({'sample_size': k, 'exact_share_pct': round(100 * p_true, 3), 'mean_estimate_pct': round(100 * float(est.mean()), 3),
                 'sd_of_estimates_points': round(100 * float(est.std(ddof=1)), 3), 'binomial_se_points': round(100 * se, 3),
                 'within_2_se_pct': round(100 * float((np.abs(est - p_true) <= 2 * se).mean()), 1),
                 'mean_relative_position': round(float(np.mean(pos)), 3)})
res = pd.DataFrame(rows)
res


# The spread of the estimates matches the binomial standard error, and the sampled positions are centered on the middle of the stream: the reservoir is a uniform sample although it never knew the stream length.

# ## 4. A reservoir draw as an alternative to the export sample
# 
# The LSH export holds every reverted `live_ext` edit and an equal-size sample of not-reverted edits, drawn by Spark with a full sort on a hash of the revision id. A reservoir draws the same kind of sample in one pass with fixed memory. Check: the editor-kind mix of each sample against the population of not-reverted edits.
# 
# This check found a flaw: the first version of the export drew its sample with `sample(fraction).limit(n)`, which cut off the latest edits and shifted the editor-kind mix (numbers in `docs/final/RESULTS.md`, "Fallback notebooks"). The export now takes a uniform sample, and the table below is for the corrected export.

# In[5]:


from deltalake import DeltaTable
fe = DeltaTable(str(REPO / 'data' / 'lake' / 'gold' / 'fact_edit')).to_pandas(columns=['cohort_id', 'rev_id', 'user_kind', 'live_revert_flag'])
fe = fe[fe.cohort_id == 'live_ext'].sort_values('rev_id').reset_index(drop=True)
neg = fe[~fe.live_revert_flag.fillna(False)].reset_index(drop=True)
k = int(fe.live_revert_flag.fillna(False).sum())
idx = reservoir_positions(len(neg), k, np.random.default_rng(SEED))
resv = neg.iloc[idx]
export = pd.read_parquet(EXPORTS / 'lsh_edits.parquet', columns=['cohort_id', 'label', 'user_kind'])
export = export[(export.cohort_id == 'live_ext') & (export.label == 0)]
mix = pd.DataFrame({'population_pct': 100 * neg.user_kind.value_counts(normalize=True),
                    'reservoir_pct': 100 * resv.user_kind.value_counts(normalize=True),
                    'export_sample_pct': 100 * export.user_kind.value_counts(normalize=True)}).fillna(0).round(2)
mix['reservoir_minus_population'] = (mix.reservoir_pct - mix.population_pct).round(2)
mix['export_minus_population'] = (mix.export_sample_pct - mix.population_pct).round(2)
print('not-reverted live_ext edits:', len(neg), '| sample size:', k, '| reservoir memory: the', k, 'slots only')
mix


# ## 5. Results file

# In[6]:


facts = {'moments.edit_events': n, 'moments.f0': F0, 'moments.f1': F1, 'moments.f2': F2, 'moments.max_edits_one_page': int(counts.max()),
         'moments.seeds': SEEDS, 'moments.reservoir_runs': RUNS_PER_K, 'moments.groups': 10,
         'moments.neg_population': int(len(neg)), 'moments.neg_sample_size': k,
         'moments.reservoir_kind_max_dev_points': float(mix.reservoir_minus_population.abs().max()),
         'moments.export_kind_max_dev_points': float(mix.export_minus_population.abs().max())}
for _, r in ams.iterrows():
    b = f"moments.ams.v{int(r.variables)}"
    facts[b + '.variables'] = int(r.variables)
    facts[b + '.mean_error_pct'], facts[b + '.mean_abs_error_pct'], facts[b + '.worst_abs_error_pct'] = float(r.mean_error_pct), float(r.mean_abs_error_pct), float(r.worst_abs_error_pct)
for _, r in res.iterrows():
    b = f"moments.reservoir.k{int(r.sample_size)}"
    facts[b + '.sample_size'] = int(r.sample_size)
    for c in ('exact_share_pct', 'mean_estimate_pct', 'sd_of_estimates_points', 'binomial_se_points', 'within_2_se_pct', 'mean_relative_position'):
        facts[f'{b}.{c}'] = float(r[c])
save_facts('fallback_moments.json', facts, {'ams_table': ams.to_dict('records'), 'reservoir_table': res.to_dict('records'), 'kind_mix': mix.reset_index().to_dict('records')})

