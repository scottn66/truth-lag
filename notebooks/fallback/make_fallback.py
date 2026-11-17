"""Build, run and export the fallback notebooks: rubric techniques that teammates own, built by Claude for Scott
in case a teammate's notebook does not arrive. Teammate work always wins.

    lsh_minhash        MinHash LSH on the comments of cohort edits (data/exports/lsh_edits.parquet)
    privacy            k-anonymity, l-diversity, suppression, Laplace noise on the exported marts
    moments_reservoir  AMS second moment and reservoir sampling, error against exact answers

Each notebook is executed here and gets a .py copy. Results go to data/lake/_runs/fallback_<name>.json
(read by scripts/make_results.py). No edit comment and no editor name is shown in any output.

Run (from the repository root, lake environment)
    .venv-lake/bin/python notebooks/fallback/make_fallback.py [lsh_minhash] [privacy] [moments_reservoir]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).resolve().parent
NBCONVERT = str(Path(sys.executable).parent / "jupyter-nbconvert")

HEADER = ("**Fallback, built by Claude for Scott.** This notebook exists so that the rubric technique is covered if the "
          "teammate's own notebook does not arrive. Teammate work always wins: if {owner}'s notebook arrives, use it and drop this one. "
          "Written with Claude Code (see `docs/final/GENAI_LOG.md`). No edit comment and no editor name is shown in any output.")

SETUP = """import json, os, sys, time, re, math
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
"""

LSH = [
    ("md", "# Fallback: MinHash LSH on edit comments\n\n" + HEADER.format(owner="Wanru") + "\n\n"
     "**Question.** Do reverted edits reuse near-identical edit summaries? Locality-sensitive hashing finds near-duplicate comments without comparing every pair.\n\n"
     "**Input.** `data/exports/lsh_edits.parquet` (`python -m etl.exports`): every cohort edit reverted within 4 days (label 1) and an equal-size sample of edits not reverted (label 0); comments have user links, temporary-account names and IP addresses masked.\n\n"
     "**Method.** Clean the comment (drop the section marker, lower-case), keep comments with at least 20 characters and 4 words that are not themselves reverts, remove exact duplicates, cut each text into character 5-shingles, hash the shingle set to a binary vector (`HashingTF`), and run `pyspark.ml.feature.MinHashLSH` with `approxSimilarityJoin` at Jaccard distance 0.4 (similarity at least 0.6).\n\n"
     "**Measured.** (1) Recall against an exact all-pairs join on a sample, for 1 to 20 hash tables, with run time. (2) Precision on 40 hand-labeled pairs (`notebooks/fallback/lsh_pair_labels.csv`). (3) How many comments have a near-duplicate, for reverted and not-reverted edits.\n\n"
     "**Outputs.** `data/lake/_runs/fallback_lsh.json`; `notebooks/fallback/lsh_pair_labels.csv` (pair ids and labels only, no text); `data/exports/lsh_pairs_to_label.csv` (the same pairs with text, for labeling; not committed)."),
    ("code", SETUP),
    ("md", "## 1. Documents"),
    ("code", """K_SHINGLE, MIN_CHARS, MIN_WORDS, JACCARD_MIN = 5, 20, 4, 0.6
SECTION = re.compile(r'/\\*.*?\\*/')
def clean(c):
    return re.sub(r'\\s+', ' ', SECTION.sub(' ', c or '').lower()).strip()
raw = pd.read_parquet(EXPORTS / 'lsh_edits.parquet', columns=['cohort_id', 'rev_id', 'comment', 'label', 'is_revert'])
raw['text'] = raw.comment.map(clean)
docs = raw[(~raw.is_revert.fillna(False)) & (raw.text.str.len() >= MIN_CHARS) & (raw.text.str.split().str.len() >= MIN_WORDS)].copy()
per_text = docs.groupby('text').agg(copies=('rev_id', 'size'), n_reverted=('label', 'sum')).reset_index()
per_text['doc_id'] = np.arange(len(per_text))
per_text['sh'] = per_text.text.map(lambda t: sorted({t[i:i + K_SHINGLE] for i in range(len(t) - K_SHINGLE + 1)}))
docs = docs.merge(per_text[['text', 'doc_id']], on='text')
print('edits in the export:', len(raw), '| edits kept:', len(docs), '| by label:', docs.label.value_counts().sort_index().to_dict())
print('distinct texts:', len(per_text), '| texts used by more than one edit:', int((per_text.copies > 1).sum()),
      '| edits that share their exact text with another edit:', int(per_text.copies[per_text.copies > 1].sum()))
print('shingles per text: median', int(per_text.sh.map(len).median()), '| largest exact-duplicate group:', int(per_text.copies.max()), 'edits')"""),
    ("md", "## 2. MinHash LSH in Spark"),
    ("code", """from etl.spark_session import get_spark
from pyspark.ml.feature import HashingTF, MinHashLSH
from pyspark.sql import functions as F
spark = get_spark('fallback_lsh', shuffle_partitions=16)
sdf = spark.createDataFrame(per_text[['doc_id', 'sh']])
feat = HashingTF(inputCol='sh', outputCol='features', numFeatures=1 << 18, binary=True).transform(sdf).cache()
print('vectors:', feat.count())

def lsh_pairs(data, tables, seed=SEED):
    model = MinHashLSH(inputCol='features', outputCol='hashes', numHashTables=tables, seed=seed).fit(data)
    j = model.approxSimilarityJoin(data, data, 1 - JACCARD_MIN, distCol='dist')
    return (j.where(F.col('datasetA.doc_id') < F.col('datasetB.doc_id'))
             .select(F.col('datasetA.doc_id').alias('a'), F.col('datasetB.doc_id').alias('b'), (1 - F.col('dist')).alias('jaccard')))"""),
    ("md", "## 3. Recall against an exact join (sample of 4,000 texts)\n\nThe exact join compares all pairs of the sample with Spark array functions. LSH returns only pairs whose Jaccard similarity is really at least 0.6 (the join filters by the true distance), so what LSH can lose is recall."),
    ("code", """N_SAMPLE = 4000
rng = np.random.default_rng(SEED)
sample_ids = sorted(rng.choice(len(per_text), size=N_SAMPLE, replace=False).tolist())
samp = feat.join(spark.createDataFrame(pd.DataFrame({'doc_id': sample_ids})), 'doc_id').cache()
samp.count()
t0 = time.time()
x, y = samp.alias('x'), samp.alias('y')
exact = (x.join(y, F.col('x.doc_id') < F.col('y.doc_id'))
          .select(F.col('x.doc_id').alias('a'), F.col('y.doc_id').alias('b'),
                  (F.size(F.array_intersect('x.sh', 'y.sh')) / F.size(F.array_union('x.sh', 'y.sh'))).alias('jaccard'))
          .where(F.col('jaccard') >= JACCARD_MIN).toPandas())
t_exact = time.time() - t0
exact_set = set(zip(exact.a, exact.b))
print('pairs compared:', N_SAMPLE * (N_SAMPLE - 1) // 2, '| exact near-duplicate pairs:', len(exact_set), '| seconds:', round(t_exact, 1))
rows = []
for tables in (1, 3, 5, 10, 20):
    t0 = time.time()
    got = lsh_pairs(samp, tables).toPandas()
    sec = time.time() - t0
    found = set(zip(got.a, got.b))
    rows.append({'hash_tables': tables, 'pairs_returned': len(found), 'true_pairs_found': len(found & exact_set),
                 'recall_pct': round(100 * len(found & exact_set) / max(1, len(exact_set)), 2),
                 'agree_with_exact_pct': round(100 * len(found & exact_set) / max(1, len(found)), 2), 'seconds': round(sec, 1)})
recall = pd.DataFrame(rows)
recall"""),
    ("md", "`agree_with_exact_pct` is below 100 only when hashing the shingles to 2^18 buckets changes a similarity near the 0.6 line."),
    ("md", "## 4. All texts: near-duplicate pairs and groups (5 hash tables)"),
    ("code", """TABLES = 5
t0 = time.time()
pairs = lsh_pairs(feat, TABLES).toPandas().sort_values(['a', 'b']).reset_index(drop=True)
t_full = time.time() - t0
print('near-duplicate pairs among', len(per_text), 'distinct texts:', len(pairs), '| seconds:', round(t_full, 1))
# groups = connected components of the pair graph (union-find)
parent = list(range(len(per_text)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
for a, b in zip(pairs.a, pairs.b):
    ra, rb = find(int(a)), find(int(b))
    if ra != rb: parent[rb] = ra
per_text['group'] = [find(i) for i in range(len(per_text))]
in_pair = np.zeros(len(per_text), bool); in_pair[pairs.a.to_numpy()] = True; in_pair[pairs.b.to_numpy()] = True
per_text['has_near_dup'] = in_pair
sizes = per_text[per_text.has_near_dup].groupby('group').size()
print('texts with a near-duplicate:', int(in_pair.sum()), '| groups:', len(sizes), '| largest group:', int(sizes.max()), 'texts | groups of 10 or more:', int((sizes >= 10).sum()))
pairs.jaccard.describe().round(3).to_frame().T"""),
    ("md", "## 5. Reverted against not-reverted edits\n\nAn edit 'reuses' a summary when its text is shared exactly with another edit or has a near-duplicate text."),
    ("code", """d = docs.merge(per_text[['doc_id', 'copies', 'has_near_dup']], on='doc_id')
d['exact_dup'] = d.copies > 1
d['reuses'] = d.exact_dup | d.has_near_dup
by_label = d.groupby('label').agg(edits=('rev_id', 'size'), exact_dup_pct=('exact_dup', lambda s: round(100 * s.mean(), 2)),
                                  near_dup_pct=('has_near_dup', lambda s: round(100 * s.mean(), 2)),
                                  reuses_pct=('reuses', lambda s: round(100 * s.mean(), 2)))
by_label.index = by_label.index.map({0: 'not reverted (label 0)', 1: 'reverted (label 1)'})
by_label"""),
    ("md", "## 6. Precision on hand-labeled pairs\n\nTwo samples, seed 226. `by_band`: 40 pairs, 10 from each similarity band (0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0). `by_group`: one random pair from each of 40 random near-duplicate groups, which is the harder test because the few largest template families cannot fill it. A pair is labeled 1 when the two summaries are the same edit pattern (the same sentence or template with small changes), 0 when they only share words. The labels in `lsh_pair_labels.csv` were set by Claude (column `claude_label`) by reading both texts; a person can overwrite any of them in the column `human_label`, which wins when filled."),
    ("code", """bands = [(0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]
parts = []
for lo, hi in bands:
    b = pairs[(pairs.jaccard >= lo) & (pairs.jaccard < hi)]
    parts.append(b.sample(n=min(10, len(b)), random_state=SEED).assign(band=f'{lo:.1f}-{min(hi, 1.0):.1f}'))
by_band = pd.concat(parts).sort_values(['band', 'a', 'b']).assign(sample='by_band')
# second sample: one random pair from each of 40 random groups, so that the few largest template families do not fill it
pairs['group'] = per_text.group.reindex(pairs.a).to_numpy()
chosen = pd.Series(sorted(pairs.group.unique())).sample(n=40, random_state=SEED)
by_group = pd.concat([pairs[pairs.group == g].sample(n=1, random_state=SEED) for g in chosen]).sort_values(['a', 'b'])
by_group = by_group.assign(sample='by_group', band=by_group.jaccard.map(lambda j: next(f'{lo:.1f}-{min(hi, 1.0):.1f}' for lo, hi in bands if lo <= j < hi)))
sample = pd.concat([by_band, by_group]).reset_index(drop=True)
rep = docs.sort_values('rev_id').drop_duplicates('doc_id').set_index('doc_id')[['cohort_id', 'rev_id']]
sample['pair_id'] = np.arange(1, len(sample) + 1)
for side in ('a', 'b'):
    sample[f'cohort_{side}'] = rep.cohort_id.reindex(sample[side]).to_numpy()
    sample[f'rev_id_{side}'] = rep.rev_id.reindex(sample[side]).to_numpy()
    sample[f'text_{side}'] = per_text.text.reindex(sample[side]).to_numpy()
sample['jaccard'] = sample.jaccard.round(4)
sample[['pair_id', 'sample', 'band', 'jaccard', 'cohort_a', 'rev_id_a', 'text_a', 'cohort_b', 'rev_id_b', 'text_b']].to_csv(EXPORTS / 'lsh_pairs_to_label.csv', index=False)
labels_path = REPO / 'notebooks' / 'fallback' / 'lsh_pair_labels.csv'
keys = ['pair_id', 'sample', 'band', 'jaccard', 'cohort_a', 'rev_id_a', 'cohort_b', 'rev_id_b']
if labels_path.exists():
    lab = pd.read_csv(labels_path)
    assert lab[['rev_id_a', 'rev_id_b']].equals(sample[['rev_id_a', 'rev_id_b']].reset_index(drop=True)), 'labels file does not match the sampled pairs'
    lab['label'] = lab.human_label.where(lab.human_label.notna(), lab.claude_label)
    def wilson(k, n, z=1.96):
        p = k / n
        return ((p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n), (p + z*z/(2*n) + z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n))
    prec = {}
    for name, g in list(lab.groupby('sample')) + [('all', lab)]:
        n, k = int(g.label.notna().sum()), int(g.label.sum())
        lo, hi = wilson(k, n)
        prec[name] = {'n': n, 'k': k, 'pct': round(100 * k / n, 1), 'lo': round(100 * lo, 1), 'hi': round(100 * hi, 1)}
        print(f'{name}: labeled pairs {n} | same edit pattern {k} | precision {100*k/n:.1f}% (Wilson 95% interval {100*lo:.1f} to {100*hi:.1f})')
    print('labeled by a person:', int(lab.human_label.notna().sum()), 'of', len(lab))
    display(lab.groupby(['sample', 'band']).agg(pairs=('label', 'size'), same_pattern=('label', 'sum')))
else:
    sample[keys].assign(claude_label=np.nan, human_label=np.nan, note='').to_csv(labels_path, index=False)
    lab, prec = None, {}
    print('wrote an empty labels file; label the pairs in data/exports/lsh_pairs_to_label.csv, then run again')"""),
    ("md", "## 7. Results file"),
    ("code", """r5 = recall[recall.hash_tables == 5].iloc[0]; r1 = recall[recall.hash_tables == 1].iloc[0]; r20 = recall[recall.hash_tables == 20].iloc[0]
facts = {
    'lsh.edits_in_export': int(len(raw)), 'lsh.edits_kept': int(len(docs)), 'lsh.distinct_texts': int(len(per_text)),
    'lsh.edits_sharing_exact_text': int(per_text.copies[per_text.copies > 1].sum()),
    'lsh.shingle_k': K_SHINGLE, 'lsh.min_chars': MIN_CHARS, 'lsh.min_words': MIN_WORDS, 'lsh.jaccard_min': JACCARD_MIN,
    'lsh.hash_tables': TABLES, 'lsh.sample_texts': N_SAMPLE, 'lsh.sample_pairs_compared': N_SAMPLE * (N_SAMPLE - 1) // 2,
    'lsh.sample_exact_pairs': int(len(exact_set)), 'lsh.exact_join_seconds': round(t_exact, 1),
    'lsh.recall_pct.tables1': float(r1.recall_pct), 'lsh.recall_pct.tables5': float(r5.recall_pct), 'lsh.recall_pct.tables20': float(r20.recall_pct),
    'lsh.seconds.tables1': float(r1.seconds), 'lsh.seconds.tables5': float(r5.seconds), 'lsh.seconds.tables20': float(r20.seconds),
    'lsh.near_dup_pairs': int(len(pairs)), 'lsh.texts_with_near_dup': int(in_pair.sum()), 'lsh.groups': int(len(sizes)),
    'lsh.largest_group_texts': int(sizes.max()), 'lsh.full_join_seconds': round(t_full, 1),
    'lsh.reverted.edits': int(by_label.loc['reverted (label 1)', 'edits']), 'lsh.not_reverted.edits': int(by_label.loc['not reverted (label 0)', 'edits']),
    'lsh.reverted.reuses_pct': float(by_label.loc['reverted (label 1)', 'reuses_pct']), 'lsh.not_reverted.reuses_pct': float(by_label.loc['not reverted (label 0)', 'reuses_pct']),
    'lsh.reverted.near_dup_pct': float(by_label.loc['reverted (label 1)', 'near_dup_pct']), 'lsh.not_reverted.near_dup_pct': float(by_label.loc['not reverted (label 0)', 'near_dup_pct']),
    'lsh.reverted.exact_dup_pct': float(by_label.loc['reverted (label 1)', 'exact_dup_pct']), 'lsh.not_reverted.exact_dup_pct': float(by_label.loc['not reverted (label 0)', 'exact_dup_pct']),
}
for name, r in prec.items():
    facts.update({f'lsh.labels.{name}.pairs': r['n'], f'lsh.labels.{name}.same_pattern': r['k'], f'lsh.labels.{name}.precision_pct': r['pct'],
                  f'lsh.labels.{name}.precision_lo': r['lo'], f'lsh.labels.{name}.precision_hi': r['hi']})
if prec:
    facts['lsh.labels.by_person'] = int(lab.human_label.notna().sum())
    facts['lsh.labels.groups_sampled'] = 40
save_facts('fallback_lsh.json', facts, {'recall_table': recall.to_dict('records')})
spark.stop()"""),
]

PRIVACY = [
    ("md", "# Fallback: privacy checks on the released tables\n\n" + HEADER.format(owner="Zhenni") + "\n\n"
     "**Question.** If the Gold extracts were published, could a row single out an editor, and how much accuracy does protection cost?\n\n"
     "**Inputs** (`python -m etl.exports`): `group_sizes_by_kind_hour.csv` (cohort, editor kind, UTC date, UTC hour), `page_revert_summary.parquet` (cohort, page), `mart_el_curve.csv` (the E(L) mart).\n\n"
     "**Method.** (1) k-anonymity: a released row describes a group of editors; its group size is `distinct_editors`. A table is k-anonymous when every row has at least k editors. (2) l-diversity with the sensitive attribute *reverted within 4 days*: a group is 2-diverse when it holds both reverted and not-reverted edits; a group whose edits were all reverted tells an attacker that any editor known to be in it was reverted. (3) Suppression of small or homogeneous groups, with the cost in rows and in the revert rate. (4) Differential privacy: Laplace noise on the E(L) counts at 3 epsilons, with the error of E(L).\n\n"
     "**Output.** `data/lake/_runs/fallback_privacy.json`."),
    ("code", SETUP),
    ("md", "## 1. k-anonymity: group sizes of the two released tables"),
    ("code", """grid = pd.read_csv(EXPORTS / 'group_sizes_by_kind_hour.csv')
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
kt"""),
    ("md", "The hourly grid is coarse enough to be safe at small k. The page-level table is not: most pages were edited by a single editor in the window, so a page row is that editor's row."),
    ("md", "## 2. l-diversity for the sensitive attribute *reverted within 4 days*"),
    ("code", """def diversity(df, name):
    n, r = df.edits, df.reverted_4d
    both = (r > 0) & (r < n)
    all_rev = (r == n)
    none_rev = (r == 0)
    return {'table': name, 'rows': len(df), 'two_diverse_pct': round(100 * both.mean(), 2), 'all_reverted_rows': int(all_rev.sum()),
            'all_reverted_pct': round(100 * all_rev.mean(), 3), 'none_reverted_pct': round(100 * none_rev.mean(), 2),
            'all_reverted_and_single_editor': int((all_rev & (df.distinct_editors == 1)).sum())}
ld = pd.DataFrame([diversity(grid, 'kind x date x hour'), diversity(page, 'page summary')])
ld"""),
    ("md", "## 3. Suppression and what it costs\n\nRules for the page summary (k = 5): A = drop rows with fewer than 5 editors. B = A, and also drop rows whose edits were all reverted. C = keep only rows with at least 5 editors that are 2-diverse. Cost: rows, edits and reverts kept, and the revert rate computed from the released rows against the true one."),
    ("code", """K = 5
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
sup"""),
    ("md", "Suppressing small page rows keeps only busy pages, and busy pages are reverted more often: the released revert rate is biased upward. A page-level release needs generalization (for example page categories) or noise, not only suppression."),
    ("md", "## 4. Differential privacy: Laplace noise on the E(L) counts\n\nOne revert falls into exactly one bin of the histogram *first known in the wait interval (L[j-1], L[j]]*. Adding or removing one revert changes one bin by one, so the histogram has sensitivity 1 and each bin gets Laplace noise of scale 1/epsilon (epsilon-differential privacy at the level of one edit). Known counts are the running sums of the noisy bins; the total is their sum; E(L) follows. 1,000 trials per epsilon, seed 226. Error = mean absolute difference between the noisy and the true E(L) over the 7 waits from 1 min to 2 d."),
    ("code", """mart = pd.read_csv(EXPORTS / 'mart_el_curve.csv').sort_values(['cohort_id', 'label_source', 'user_kind', 'wait_s'])
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
show"""),
    ("code", """import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=110)
for _, r in lap[lap.cohort == 'live'][lap.labels == 'stream'].iterrows():
    ax.plot(EPS, [r[f'mae_eps_{e}'] for e in EPS], 'o-', label=f"{r.editor_kind} (n = {r.eventual_reverts:,})")
ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('epsilon'); ax.set_ylabel('mean absolute error of E(L)')
ax.set_title('Laplace noise on the E(L) counts, live cohort'); ax.grid(alpha=.3); ax.legend(fontsize=8)
fig.savefig(REPO / 'docs' / 'final' / 'figures' / 'privacy_laplace.png', bbox_inches='tight')
plt.show()"""),
    ("md", "Reading: for the published series (thousands of reverts) the error is far below the differences the report discusses, even at the smallest epsilon. For the smallest groups (the bot series, with about a hundred reverts) the error at the smallest epsilon is as large as the differences between series, so small groups should stay suppressed or be merged. Limit: this is edit-level privacy; protecting an editor's whole history would need a cap on reverts per editor first."),
    ("md", "## 5. Results file"),
    ("code", """def kt_get(table, k, col): return kt[(kt.table == table) & (kt.k == k)][col].iloc[0]
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
save_facts('fallback_privacy.json', facts, {'laplace_table': lap.to_dict('records'), 'k_table': kt.to_dict('records'), 'suppression': sup.to_dict('records')})"""),
]

MOMENTS = [
    ("md", "# Fallback: stream moments (AMS) and reservoir sampling\n\n" + HEADER.format(owner="a teammate") + "\n\n"
     "**Why.** `etl/streaming_algos.py` already measures an AMS estimate and one reservoir sample (notebook 05). This notebook measures both properly: error against the number of variables or the sample size, over many seeds, against exact answers.\n\n"
     "**Input.** The enwiki page-change events of `silver/page_change` in publish order up to 2026-11-13 (the same stream as notebook 05), and the cohort `live_ext` of `gold/fact_edit`.\n\n"
     "**Measured.** (1) Frequency moments of edits per page: exact F0, F1, F2, and the Alon-Matias-Szegedy estimate of F2 for 100 to 10,000 variables over 30 seeds. (2) Reservoir sampling (Algorithm L, one pass, fixed memory): error of the revert share for sample sizes 1,000 to 100,000 over 200 reservoirs, against the binomial standard error; and a reservoir draw of not-reverted edits as an alternative to the sample in the LSH export.\n\n"
     "**Output.** `data/lake/_runs/fallback_moments.json`."),
    ("code", SETUP),
    ("md", "## 1. The stream"),
    ("code", """from etl import streaming_algos, lake_config
t = streaming_algos.load_stream()
kind = np.array(t.column('kind').to_pylist())
is_edit = kind == 'edit'
page = t.column('page_id').to_numpy(zero_copy_only=False)[is_edit]
is_revert = np.array([m is not None for m in t.column('revert_method').to_pylist()])[is_edit]
n = len(page)
_, inv, counts = np.unique(page, return_inverse=True, return_counts=True)
F0, F1, F2 = int(len(counts)), int(n), int((counts.astype(np.int64) ** 2).sum())
print('edit events:', n, '| F0 (distinct pages):', F0, '| F1:', F1, '| F2 (sum of squared edits per page):', F2)
print('edits per page: mean', round(F1 / F0, 2), '| max', int(counts.max()), '| pages with one edit:', int((counts == 1).sum()))"""),
    ("md", "## 2. AMS estimate of the second moment\n\nFor a random position q, let c be the number of times the page at q appears from q to the end. X = n (2c - 1) has expectation F2. Take v such variables, average them in 10 groups and report the median of the group means."),
    ("code", """# c for every position at once: occurrences of the page from this position on
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
ams"""),
    ("md", "Edits per page are heavy-tailed (a few pages carry a large share of F2), so the median of means sits below F2 until the sample is large enough to hit those pages."),
    ("md", "## 3. Reservoir sampling (Algorithm L)"),
    ("code", """def reservoir_positions(n, k, rng):
    \"\"\"Positions of a uniform sample of k items from a stream of n, in one pass with k slots (Li's Algorithm L).\"\"\"
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
res"""),
    ("md", "The spread of the estimates matches the binomial standard error, and the sampled positions are centered on the middle of the stream: the reservoir is a uniform sample although it never knew the stream length."),
    ("md", "## 4. A reservoir draw as an alternative to the export sample\n\nThe LSH export holds every reverted `live_ext` edit and an equal-size sample of not-reverted edits, drawn by Spark with a full sort on a hash of the revision id. A reservoir draws the same kind of sample in one pass with fixed memory. Check: the editor-kind mix of each sample against the population of not-reverted edits.\n\nThis check found a flaw: the first version of the export drew its sample with `sample(fraction).limit(n)`, which cut off the latest edits and shifted the editor-kind mix (numbers in `docs/final/RESULTS.md`, \"Fallback notebooks\"). The export now takes a uniform sample, and the table below is for the corrected export."),
    ("code", """from deltalake import DeltaTable
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
mix"""),
    ("md", "## 5. Results file"),
    ("code", """facts = {'moments.edit_events': n, 'moments.f0': F0, 'moments.f1': F1, 'moments.f2': F2, 'moments.max_edits_one_page': int(counts.max()),
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
save_facts('fallback_moments.json', facts, {'ams_table': ams.to_dict('records'), 'reservoir_table': res.to_dict('records'), 'kind_mix': mix.reset_index().to_dict('records')})"""),
]

NOTEBOOKS = {"lsh_minhash": LSH, "privacy": PRIVACY, "moments_reservoir": MOMENTS}


def build(names) -> None:
    for name in names:
        nb = nbf.v4.new_notebook()
        nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in NOTEBOOKS[name]]
        nb.metadata["kernelspec"] = {"name": "truthlag-lake", "display_name": "TruthLag lake (.venv-lake)", "language": "python"}
        path = HERE / f"{name}.ipynb"
        nbf.write(nb, path)
        subprocess.run([NBCONVERT, "--to", "notebook", "--execute", "--inplace", "--ExecutePreprocessor.timeout=3600",
                        "--ExecutePreprocessor.kernel_name=truthlag-lake", str(path)], check=True, cwd=HERE)
        subprocess.run([NBCONVERT, "--to", "script", str(path)], check=True, cwd=HERE)
        print(name, path.stat().st_size, "bytes")


if __name__ == "__main__":
    build(sys.argv[1:] or list(NOTEBOOKS))
