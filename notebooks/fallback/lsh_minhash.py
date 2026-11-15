#!/usr/bin/env python
# coding: utf-8

# # Fallback: MinHash LSH on edit comments
# 
# **Fallback, built by Claude for Scott.** This notebook exists so that the rubric technique is covered if the teammate's own notebook does not arrive. Teammate work always wins: if Wanru's notebook arrives, use it and drop this one. Written with Claude Code (see `docs/final/GENAI_LOG.md`). No edit comment and no editor name is shown in any output.
# 
# **Question.** Do reverted edits reuse near-identical edit summaries? Locality-sensitive hashing finds near-duplicate comments without comparing every pair.
# 
# **Input.** `data/exports/lsh_edits.parquet` (`python -m etl.exports`): every cohort edit reverted within 4 days (label 1) and an equal-size sample of edits not reverted (label 0); comments have user links, temporary-account names and IP addresses masked.
# 
# **Method.** Clean the comment (drop the section marker, lower-case), keep comments with at least 20 characters and 4 words that are not themselves reverts, remove exact duplicates, cut each text into character 5-shingles, hash the shingle set to a binary vector (`HashingTF`), and run `pyspark.ml.feature.MinHashLSH` with `approxSimilarityJoin` at Jaccard distance 0.4 (similarity at least 0.6).
# 
# **Measured.** (1) Recall against an exact all-pairs join on a sample, for 1 to 20 hash tables, with run time. (2) Precision on 40 hand-labeled pairs (`notebooks/fallback/lsh_pair_labels.csv`). (3) How many comments have a near-duplicate, for reverted and not-reverted edits.
# 
# **Outputs.** `data/lake/_runs/fallback_lsh.json`; `notebooks/fallback/lsh_pair_labels.csv` (pair ids and labels only, no text); `data/exports/lsh_pairs_to_label.csv` (the same pairs with text, for labeling; not committed).

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


# ## 1. Documents

# In[2]:


K_SHINGLE, MIN_CHARS, MIN_WORDS, JACCARD_MIN = 5, 20, 4, 0.6
SECTION = re.compile(r'/\*.*?\*/')
def clean(c):
    return re.sub(r'\s+', ' ', SECTION.sub(' ', c or '').lower()).strip()
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
print('shingles per text: median', int(per_text.sh.map(len).median()), '| largest exact-duplicate group:', int(per_text.copies.max()), 'edits')


# ## 2. MinHash LSH in Spark

# In[3]:


from etl.spark_session import get_spark
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
             .select(F.col('datasetA.doc_id').alias('a'), F.col('datasetB.doc_id').alias('b'), (1 - F.col('dist')).alias('jaccard')))


# ## 3. Recall against an exact join (sample of 4,000 texts)
# 
# The exact join compares all pairs of the sample with Spark array functions. LSH returns only pairs whose Jaccard similarity is really at least 0.6 (the join filters by the true distance), so what LSH can lose is recall.

# In[4]:


N_SAMPLE = 4000
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
recall


# `agree_with_exact_pct` is below 100 only when hashing the shingles to 2^18 buckets changes a similarity near the 0.6 line.

# ## 4. All texts: near-duplicate pairs and groups (5 hash tables)

# In[5]:


TABLES = 5
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
pairs.jaccard.describe().round(3).to_frame().T


# ## 5. Reverted against not-reverted edits
# 
# An edit 'reuses' a summary when its text is shared exactly with another edit or has a near-duplicate text.

# In[6]:


d = docs.merge(per_text[['doc_id', 'copies', 'has_near_dup']], on='doc_id')
d['exact_dup'] = d.copies > 1
d['reuses'] = d.exact_dup | d.has_near_dup
by_label = d.groupby('label').agg(edits=('rev_id', 'size'), exact_dup_pct=('exact_dup', lambda s: round(100 * s.mean(), 2)),
                                  near_dup_pct=('has_near_dup', lambda s: round(100 * s.mean(), 2)),
                                  reuses_pct=('reuses', lambda s: round(100 * s.mean(), 2)))
by_label.index = by_label.index.map({0: 'not reverted (label 0)', 1: 'reverted (label 1)'})
by_label


# ## 6. Precision on hand-labeled pairs
# 
# Two samples, seed 226. `by_band`: 40 pairs, 10 from each similarity band (0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0). `by_group`: one random pair from each of 40 random near-duplicate groups, which is the harder test because the few largest template families cannot fill it. A pair is labeled 1 when the two summaries are the same edit pattern (the same sentence or template with small changes), 0 when they only share words. The labels in `lsh_pair_labels.csv` were set by Claude (column `claude_label`) by reading both texts; a person can overwrite any of them in the column `human_label`, which wins when filled.

# In[7]:


bands = [(0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]
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
    print('wrote an empty labels file; label the pairs in data/exports/lsh_pairs_to_label.csv, then run again')


# ## 7. Results file

# In[8]:


r5 = recall[recall.hash_tables == 5].iloc[0]; r1 = recall[recall.hash_tables == 1].iloc[0]; r20 = recall[recall.hash_tables == 20].iloc[0]
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
spark.stop()

