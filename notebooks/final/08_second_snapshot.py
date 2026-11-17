#!/usr/bin/env python
# coding: utf-8

# # 08 Second History snapshot (2026-10): label changes and reconciliation
# 
# The 2026-10 month files were cut to the slim columns locally (`python -m etl.history_slim`), loaded with `python -m etl.history bronze|silver --snapshot 2026-10`, and merged into `gold/fact_revert_label` as one commit (`python -m etl.gold_run --snapshot 2026-10 --steps ddl,dims,labels,label_change,recon,marts`). Checks: `python -m etl.snapshot_checks`.

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
sc = run('snapshot_checks.json')
print(sc['label_versions'], sc['passed'], 'passed,', sc['failed'], 'failed')
table('gold/dim_snapshot')


# ## fact_revert_label history (one commit per snapshot load)

# In[2]:


history('gold/fact_revert_label')


# ## Checks

# In[3]:


pd.DataFrame([{k: c[k] for k in ('check', 'ok')} | {'got': str(c['got'])[:160]} for c in sc['checks']])


# ## Label changes between the snapshots (from the Change Data Feed)

# In[4]:


lc = table('gold/mart_label_change')
lc.groupby(['from_snapshot', 'to_snapshot', 'change_class']).size()


# ## Live cohort: stream label against the 2026-10 dump label

# In[5]:


table('gold/mart_reconciliation').sort_values('recon_class')


# ## E(L) of the live cohort: stream labels vs dump labels

# In[6]:


el = table('gold/mart_el_curve')
el[(el.cohort_id == 'live') & (el.user_kind == 'all')].pivot_table(index=['wait_s', 'wait_label'], columns='label_source', values=['n_known', 'e_l']).round(4)

