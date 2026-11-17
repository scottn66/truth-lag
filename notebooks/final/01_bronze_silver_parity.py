#!/usr/bin/env python
# coding: utf-8

# # 01 Bronze and Silver: load and parity
# 
# Raw capture files go to Bronze with delta-rs (append-only, one row per captured line). Silver applies the EC HW2 parser rules. This notebook shows the row counts and the parity checks against the published EC HW2 tables (`data/parity_ref/`).
# 
# Commands that made the tables: `python -m etl.run bronze --raw-dir data/raw`, `python -m etl.run silver`, `python -m etl.history all`, `python -m etl.parity bronze|silver|cohorts`.

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


# ## Bronze tables: versions and commits

# In[2]:


for t in ['bronze/page_change_events', 'bronze/revert_risk_events', 'bronze/tags_events', 'bronze/history_slim', 'bronze/history_full']:
    print(t, 'version', DeltaTable(str(LAKE / t)).version())
history('bronze/page_change_events', 5)


# ## Bronze parity with the published parse cut
# 
# The cut is rebuilt from `_SUCCESS_parsed.json`: hour folders up to 2026-10-27 hour 20, minus files skipped as open, cut-short files limited to the lines the parse kept.

# In[3]:


bp = run('bronze_parity.json')
pd.DataFrame({s.split('.')[1] if 'revision' not in s else 'tags': {k: v for k, v in d.items() if k != 'bronze_rows_per_day'} for s, d in bp.items()}).T


# ## Bronze rows per event date

# In[4]:


pd.DataFrame({s.split('mediawiki.')[1]: d['bronze_rows_per_day'] for s, d in bp.items()}).fillna(0).astype(int)


# ## Silver parity at the published cut (meta_dt <= 2026-10-27T20:59:59.999999Z)

# In[5]:


sp = run('silver_parity.json')
pd.DataFrame({k: {c: v[c] for c in ('rows_lake', 'rows_ref', 'only_in_lake', 'only_in_ref', 'same_content')} for k, v in sp.items()}).T


# ## Cohort tables against `data/tables` (built at the parity as_of)

# In[6]:


cp = run('cohort_parity.json')
pd.DataFrame({k: {c: v[c] for c in ('rows_lake', 'rows_ref', 'only_in_lake', 'only_in_ref', 'same_content', 'lake_version')} for k, v in cp.items()}).T


# ## Capture gaps over 120 s

# In[7]:


table('silver/capture_gaps')

