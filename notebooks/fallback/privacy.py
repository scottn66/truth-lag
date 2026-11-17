#!/usr/bin/env python
# coding: utf-8

# # Fallback: privacy checks on the released tables
# 
# **Fallback, built by Claude for Scott.** This notebook exists so that the rubric technique is covered if the teammate's own notebook does not arrive. Teammate work always wins: if Zhenni's notebook arrives, use it and drop this one. Written with Claude Code (see `docs/final/GENAI_LOG.md`). No edit comment and no editor name is shown in any output.
# 
# **Question.** If the Gold extracts were published, could a row single out an editor, and how much accuracy does protection cost?
# 
# **Inputs** (`python -m etl.exports`): `group_sizes_by_kind_hour.csv` (cohort, editor kind, UTC date, UTC hour), `page_revert_summary.parquet` (cohort, page), `mart_el_curve.csv` (the E(L) mart).
# 
# **Method.** (1) k-anonymity: a released row describes a group of editors; its group size is `distinct_editors`. A table is k-anonymous when every row has at least k editors. (2) l-diversity with the sensitive attribute *reverted within 4 days*: a group is 2-diverse when it holds both reverted and not-reverted edits; a group whose edits were all reverted tells an attacker that any editor known to be in it was reverted. (3) Suppression of small or homogeneous groups, with the cost in rows and in the revert rate. (4) Differential privacy: Laplace noise on the E(L) counts at 3 epsilons, with the error of E(L).
# 
# **Output.** `data/lake/_runs/fallback_privacy.json`.

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


# ## 1. k-anonymity: group sizes of the two released tables

# In[2]:


grid = pd.read_csv(EXPORTS / 'group_sizes_by_kind_hour.csv')
page = pd.read_parquet(EXPORTS / 'page_revert_summary.parquet')
KS = (2, 5, 10, 20)
def k_table(df, name):
    rows = []
    for k in KS:
        small = df.distinct_editors < k
        rows.append({'table': name, 'k': k, 'rows': len(df), 'rows_below_k': int(small.sum()), 'rows_below_k_pct': round(100 * small.mean(), 2),
                     'edits_in_those_rows_pct': round(100 * df.loc[small, 'edits'].sum() / df.edits.sum(), 2)})
    return rows
grid = grid.rename(columns={'revisions': 'edits'})
kt = pd.DataFrame(k_table(grid, 'kind x date x hour') + k_table(page, 'page summary'))
print('smallest group: grid', int(grid.distinct_editors.min()), 'editors; page summary', int(page.distinct_editors.min()), 'editor(s)')
print('pages in the summary:', len(page), '| pages with exactly one editor:', int((page.distinct_editors == 1).sum()))
kt


# The hourly grid is coarse enough to be safe at small k. The page-level table is not: most pages were edited by a single editor in the window, so a page row is that editor's row.

# ## 2. l-diversity for the sensitive attribute *reverted within 4 days*

# In[3]:


def diversity(df, name):
    n, r = df.edits, df.reverted_4d
    both = (r > 0) & (r < n)
    all_rev = (r == n)
    none_rev = (r == 0)
    return {'table': name, 'rows': len(df), 'two_diverse_pct': round(100 * both.mean(), 2), 'all_reverted_rows': int(all_rev.sum()),
            'all_reverted_pct': round(100 * all_rev.mean(), 3), 'none_reverted_pct': round(100 * none_rev.mean(), 2),
            'all_reverted_and_single_editor': int((all_rev & (df.distinct_editors == 1)).sum())}
ld = pd.DataFrame([diversity(grid, 'kind x date x hour'), diversity(page, 'page summary')])
ld


# ## 3. Suppression and what it costs
# 
# Rules for the page summary (k = 5): A = drop rows with fewer than 5 editors. B = A, and also drop rows whose edits were all reverted. C = keep only rows with at least 5 editors that are 2-diverse. Cost: rows, edits and reverts kept, and the revert rate computed from the released rows against the true one.

# In[4]:


K = 5
def release(df, rule):
    keep = df.distinct_editors >= K
    if rule == 'B': keep &= df.reverted_4d < df.edits
    if rule == 'C': keep &= (df.reverted_4d > 0) & (df.reverted_4d < df.edits)
    return df[keep]
rows = []
for cohort, d in page.groupby('cohort_id'):
    true_rate = 100 * d.reverted_4d.sum() / d.edits.sum()
    for rule in ('A', 'B', 'C'):
        r = release(d, rule)
        rate = 100 * r.reverted_4d.sum() / r.edits.sum()
        rows.append({'cohort': cohort, 'rule': rule, 'rows_kept_pct': round(100 * len(r) / len(d), 2), 'edits_kept_pct': round(100 * r.edits.sum() / d.edits.sum(), 2),
                     'reverts_kept_pct': round(100 * r.reverted_4d.sum() / d.reverted_4d.sum(), 2), 'true_revert_rate_pct': round(true_rate, 2),
                     'released_revert_rate_pct': round(rate, 2), 'bias_points': round(rate - true_rate, 2)})
sup = pd.DataFrame(rows)
g5 = grid[grid.distinct_editors >= K]
print('hourly grid at k = 5: rows kept', round(100 * len(g5) / len(grid), 2), '% | edits kept', round(100 * g5.edits.sum() / grid.edits.sum(), 3), '%')
sup


# Suppressing small page rows keeps only busy pages, and busy pages are reverted more often: the released revert rate is biased upward. A page-level release needs generalization (for example page categories) or noise, not only suppression.

# ## 4. Differential privacy: Laplace noise on the E(L) counts
# 
# One revert falls into exactly one bin of the histogram *first known in the wait interval (L[j-1], L[j]]*. Adding or removing one revert changes one bin by one, so the histogram has sensitivity 1 and each bin gets Laplace noise of scale 1/epsilon (epsilon-differential privacy at the level of one edit). Known counts are the running sums of the noisy bins; the total is their sum; E(L) follows. 1,000 trials per epsilon, seed 226. Error = mean absolute difference between the noisy and the true E(L) over the 7 waits from 1 min to 2 d.

# In[5]:


mart = pd.read_csv(EXPORTS / 'mart_el_curve.csv').sort_values(['cohort_id', 'label_source', 'user_kind', 'wait_s'])
EPS = (0.1, 0.5, 1.0)
TRIALS = 1000
rng = np.random.default_rng(SEED)
rows = []
for (cohort, source, kind), g in mart.groupby(['cohort_id', 'label_source', 'user_kind']):
    known = g.n_known.to_numpy(float)
    total = float(g.n_eventual.iloc[0])
    bins = np.diff(np.concatenate([[0.0], known, [total]]))          # 9 wait bins + "not known by the last wait"
    true_e = 1 - known / total
    rec = {'cohort': cohort, 'labels': source, 'editor_kind': kind, 'eventual_reverts': int(total)}
    for eps in EPS:
        noisy = bins[None, :] + rng.laplace(0.0, 1.0 / eps, size=(TRIALS, len(bins)))
        n_known = np.cumsum(noisy, axis=1)[:, :len(known)]
        n_total = np.maximum(noisy.sum(axis=1, keepdims=True), 1.0)
        e = 1 - n_known / n_total
        err = np.abs(e - true_e[None, :])[:, 1:8]
        rec[f'mae_eps_{eps}'] = float(err.mean())
        rec[f'p95_eps_{eps}'] = float(np.percentile(err.max(axis=1), 95))
    rows.append(rec)
lap = pd.DataFrame(rows).sort_values('eventual_reverts', ascending=False).reset_index(drop=True)
show = lap.copy()
for c in show.columns[4:]:
    show[c] = show[c].round(5)
show


# In[6]:


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=110)
for _, r in lap[lap.cohort == 'live'][lap.labels == 'stream'].iterrows():
    ax.plot(EPS, [r[f'mae_eps_{e}'] for e in EPS], 'o-', label=f"{r.editor_kind} (n = {r.eventual_reverts:,})")
ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('epsilon'); ax.set_ylabel('mean absolute error of E(L)')
ax.set_title('Laplace noise on the E(L) counts, live cohort'); ax.grid(alpha=.3); ax.legend(fontsize=8)
fig.savefig(REPO / 'docs' / 'final' / 'figures' / 'privacy_laplace.png', bbox_inches='tight')
plt.show()


# Reading: for the published series (thousands of reverts) the error is far below the differences the report discusses, even at the smallest epsilon. For the smallest groups (the bot series, with about a hundred reverts) the error at the smallest epsilon is as large as the differences between series, so small groups should stay suppressed or be merged. Limit: this is edit-level privacy; protecting an editor's whole history would need a cap on reverts per editor first.

# ## 5. Results file

# In[7]:


def kt_get(table, k, col): return kt[(kt.table == table) & (kt.k == k)][col].iloc[0]
def lap_get(cohort, labels, kind, col): return float(lap[(lap.cohort == cohort) & (lap.labels == labels) & (lap.editor_kind == kind)][col].iloc[0])
small = lap[lap.eventual_reverts < 100]
facts = {
    'privacy.grid.rows': int(len(grid)), 'privacy.grid.min_editors': int(grid.distinct_editors.min()),
    'privacy.page.rows': int(len(page)), 'privacy.page.single_editor_rows': int((page.distinct_editors == 1).sum()),
    'privacy.page.single_editor_pct': round(100 * float((page.distinct_editors == 1).mean()), 2),
    'privacy.k': K, 'privacy.k_small': 2, 'privacy.l': 2, 'privacy.laplace.trials': TRIALS, 'privacy.laplace.sensitivity': 1,
    'privacy.eps_low': EPS[0], 'privacy.eps_mid': EPS[1], 'privacy.eps_high': EPS[2], 'privacy.epsilons': len(EPS),
    'privacy.grid.two_diverse_pct': float(ld.two_diverse_pct[0]), 'privacy.page.two_diverse_pct': float(ld.two_diverse_pct[1]),
    'privacy.page.all_reverted_rows': int(ld.all_reverted_rows[1]), 'privacy.page.all_reverted_pct': float(ld.all_reverted_pct[1]),
    'privacy.page.all_reverted_single_editor': int(ld.all_reverted_and_single_editor[1]),
    'privacy.grid.k5.rows_kept_pct': round(100 * len(g5) / len(grid), 2), 'privacy.grid.k5.edits_kept_pct': round(100 * float(g5.edits.sum() / grid.edits.sum()), 3),
    'privacy.laplace.small_groups': int(len(small)),
}
for k in KS:
    facts[f'privacy.grid.k{k}.rows_below'] = int(kt_get('kind x date x hour', k, 'rows_below_k'))
    facts[f'privacy.grid.k{k}.rows_below_pct'] = float(kt_get('kind x date x hour', k, 'rows_below_k_pct'))
    facts[f'privacy.page.k{k}.rows_below_pct'] = float(kt_get('page summary', k, 'rows_below_k_pct'))
    facts[f'privacy.page.k{k}.edits_below_pct'] = float(kt_get('page summary', k, 'edits_in_those_rows_pct'))
for _, r in sup.iterrows():
    b = f"privacy.suppress.{r.cohort}.rule{r.rule}"
    for c in ('rows_kept_pct', 'edits_kept_pct', 'reverts_kept_pct', 'true_revert_rate_pct', 'released_revert_rate_pct', 'bias_points'):
        facts[f'{b}.{c}'] = float(r[c])
for cohort, labels, kind in (('live', 'stream', 'all'), ('live', 'stream', 'temporary'), ('live', 'stream', 'registered'), ('live', 'stream', 'bot'),
                             ('live_ext', 'stream', 'all'), ('history', 'dump', 'all')):
    b = f'privacy.laplace.{cohort}.{labels}.{kind}'
    facts[b + '.n'] = int(lap_get(cohort, labels, kind, 'eventual_reverts'))
    for e, name in zip(EPS, ('eps_low', 'eps_mid', 'eps_high')):
        facts[f'{b}.mae.{name}'] = round(lap_get(cohort, labels, kind, f'mae_eps_{e}'), 5)
save_facts('fallback_privacy.json', facts, {'laplace_table': lap.to_dict('records'), 'k_table': kt.to_dict('records'), 'suppression': sup.to_dict('records')})

