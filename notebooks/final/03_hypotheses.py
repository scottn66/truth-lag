#!/usr/bin/env python
# coding: utf-8

# # 03 Hypotheses H1, H3, H4
# 
# Definitions: `docs/delta_lake_handoff/DECISIONS.md`. Computed by `python -m etl.hypotheses` from Gold (versions below). Intervals: Poisson bootstrap over pages, B = 2,000, seed 226.

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
h = run('hypotheses.json')
print('Gold versions read:', h['gold_versions'])


# ## H1: share of eventual reverts known at 1 h (threshold 60%) and 48 h (threshold 95%)

# In[2]:


pd.DataFrame(h['H1'])[['series', 'eventual_reverts', 'pages', 'known_1h_pct', 'known_1h_ci', 'known_48h_pct', 'known_48h_ci', 'verdict']]


# ## H3: E(L) for burst edits (>= 10 page edits in the prior hour) against the rest

# In[3]:


pd.DataFrame(h['H3'])[['series', 'L', 'burst_reverts', 'E_burst', 'E_burst_ci', 'E_rest', 'E_rest_ci', 'diff_burst_minus_rest', 'diff_ci', 'verdict']]


# ## H4: title at event time (dim_page version) against the current title

# In[4]:


pd.DataFrame({k: v for k, v in h['H4'].items() if isinstance(v, dict)})


# In[5]:


print('history_revisions rows with page_title != page_title_historical:', h['H4']['history_revisions_title_differs_from_historical'])


# ## E(L) by burst group (gold/mart_el_by_burst)

# In[6]:


b = table('gold/mart_el_by_burst')
b[b.wait_label.isin(['1 h', '1 d'])].pivot_table(index=['cohort_id', 'label_source', 'burst_group'], columns='wait_label', values=['n_eventual', 'e_l']).round(4)

