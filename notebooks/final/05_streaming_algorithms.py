#!/usr/bin/env python
# coding: utf-8

# # 05 Streaming algorithms against exact answers
# 
# `python -m etl.streaming_algos`. Stream: enwiki page-change events in publish order, 2026-10-19 23:00 to 2026-11-13 23:59 UTC. HyperLogLog and Flajolet-Martin (PCSA) for distinct pages and editors (E4), a Bloom filter on meta_id over the raw Bronze lines, DGIM for revert events in the last hour, reservoir sampling and the AMS second moment. Memory of the exact answer is an estimate (8 bytes per distinct hash).

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
d = run('streaming_algos.json')
d['stream'], d['exact_distinct']


# ## Distinct counts: error and memory (5 hash salts per sketch)

# In[2]:


pd.DataFrame(d['distinct'])


# In[3]:


pd.DataFrame(d['spark_approx_count_distinct'])


# In[4]:


d['editors_merged_daily_hll12']


# ## Bloom filter on meta_id

# In[5]:


pd.DataFrame(d['bloom_meta_id'])


# ## DGIM: revert events in the last hour

# In[6]:


pd.DataFrame(d['dgim_reverts_last_hour'])


# ## Reservoir sampling and AMS

# In[7]:


d['reservoir_edits'], d['ams_f2_edits_per_page']

