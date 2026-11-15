#!/usr/bin/env python
# coding: utf-8

# # 04 Time travel: then vs now
# 
# `python -m etl.time_travel` runs `etl/sql/80_time_travel_then_and_now.sql`. Versions of `gold/fact_edit` are found by their commit metadata `as_of`, never by timestamp. Here the same query is repeated with delta-rs, to show that both engines read the same versions.

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
tt = run('time_travel.json')
print(tt['fact_edit_versions'])


# ## Snapshot axis: fact_revert_label as loaded from History snapshot 2026-09 and 2026-10
# 
# `etl/sql/80_time_travel_then_and_now.sql`: reverted history-cohort revisions as known at each snapshot's load (VERSION AS OF) and now.

# In[2]:


print(tt['snapshot_axis']['fact_revert_label_versions'])
pd.DataFrame(tt['snapshot_axis']['then_and_now'])


# ## Stream axis: fact_edit at the three build as_of values (`etl/sql/81_time_travel_as_of.sql`)

# In[3]:


pd.DataFrame(tt['then_and_now'])


# ## The same, read by delta-rs at each version

# In[4]:


rows = []
for k, v in tt['fact_edit_versions'].items():
    f = table('gold/fact_edit', version=v, columns=['cohort_id', 'live_revert_flag'])
    f = f[f.cohort_id == 'live']
    rows.append({'build': k, 'version': v, 'live_revisions': len(f), 'reverted_as_known': int(f.live_revert_flag.fillna(False).sum())})
pd.DataFrame(rows)


# ## Change Data Feed of fact_edit between the versions

# In[5]:


pd.DataFrame(tt['change_feed'])


# In[6]:


tt['early_to_parity_updates']


# ## Silver by version: live_revert_links at each build

# In[7]:


pd.DataFrame(tt['silver_live_revert_links_by_version'])

