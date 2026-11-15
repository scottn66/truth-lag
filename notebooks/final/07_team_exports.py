#!/usr/bin/env python
# coding: utf-8

# # 07 Extracts for the team (data/exports/)
# 
# `python -m etl.exports`. For Wanru (MinHash LSH on comments and titles), Zhenni (k-anonymity and Laplace noise) and the charts. Schemas and regeneration: `docs/final/HANDOFF_TEAM.md`. Human editors appear only as pseudonyms.

# In[1]:


import json, os, sys
from pathlib import Path
REPO = Path.cwd().resolve().parents[1] if Path.cwd().name == 'final' else Path.cwd()
sys.path.insert(0, str(REPO))
os.environ.setdefault('TRUTHLAG_HW2_DIR', str(REPO / 'ec-hw2'))
import pandas as pd
pd.set_option('display.width', 160); pd.set_option('display.max_columns', 20)
from deltalake import DeltaTable
LAKE = REPO / 'data' / 'lake'
RUNS = LAKE / '_runs'
def run(name): return json.loads((RUNS / name).read_text())
def table(name, version=None, columns=None):
    return DeltaTable(str(LAKE / name), version=version).to_pandas(columns=columns)
def history(name, n=10):
    h = DeltaTable(str(LAKE / name)).history(n)
    return pd.DataFrame([{k: e.get(k) for k in ('version', 'operation', 'step', 'as_of', 'snapshot', 'rows')} for e in h])
m = json.loads((REPO / 'data/exports/manifest.json').read_text())
print(m['lake_versions'])
pd.DataFrame(m['files']).T[['rows', 'bytes']]


# In[2]:


lsh = pd.read_parquet(REPO / 'data/exports/lsh_edits.parquet')
lsh.groupby(['cohort_id', 'label']).size()


# In[3]:


g = pd.read_csv(REPO / 'data/exports/group_sizes_by_kind_hour.csv')
g.describe()

