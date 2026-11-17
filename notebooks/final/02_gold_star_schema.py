#!/usr/bin/env python
# coding: utf-8

# # 02 Gold: star schema, SCD Type 2 page dimension, E(L) marts
# 
# Spark SQL writes Gold (`python -m etl.gold_run --as-of ...`). Builds ran in knowledge order: as_of 2026-10-24 (early), 2026-10-27T20:59:59.999999Z (parity), 2026-11-13T23:59:59.999999Z (extended). The checks are in `python -m etl.gold_checks`.

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


# ## Tables, versions and row counts

# In[2]:


rows = []
for t in ['dim_cohort', 'dim_snapshot', 'dim_time', 'dim_user', 'dim_page', 'fact_edit', 'fact_revert_label', 'mart_el_curve', 'mart_el_by_burst']:
    dt = DeltaTable(str(LAKE / 'gold' / t))
    rows.append({'table': 'gold/' + t, 'version': dt.version(), 'rows': sum(b.num_rows for b in dt.to_pyarrow_dataset().to_batches(columns=[dt.schema().to_arrow().names[0]])), 'cdf': dt.metadata().configuration.get('delta.enableChangeDataFeed')})
pd.DataFrame(rows)


# ## Commit history of fact_edit (commit metadata holds step and as_of)

# In[3]:


history('gold/fact_edit')


# ## Checks at the parity and the extended as_of

# In[4]:


for f in ('gold_checks_parity.json', 'gold_checks_ext.json'):
    g = run(f); print(f, g['passed'], 'of', g['total'], 'passed; versions', g['versions'])
pd.DataFrame(run('gold_checks_ext.json')['checks'])[['check', 'ok']]


# ## dim_page (SCD Type 2): one moved page, with its versions
# 
# The page with the most versions among history-cohort pages. Titles are page titles (public), not editor names.

# In[5]:


dp = table('gold/dim_page')
fe = table('gold/fact_edit', columns=['cohort_id', 'page_key', 'event_dt'])
hist_pages = dp[dp.page_key.isin(fe[fe.cohort_id == 'history'].page_key)].page_id.unique()
n = dp[dp.page_id.isin(hist_pages)].groupby('page_id').size().sort_values(ascending=False)
pid = n.index[0]
dp[dp.page_id == pid].sort_values('valid_from')


# ## E(L) curve, all editors

# In[6]:


el = table('gold/mart_el_curve')
el[el.user_kind == 'all'].pivot_table(index=['wait_s', 'wait_label'], columns=['cohort_id', 'label_source'], values='e_l').round(4)


# ## E(L) at 1 h by editor kind (kind at edit time); small groups flagged

# In[7]:


el[el.wait_label == '1 h'][['cohort_id', 'label_source', 'user_kind', 'n_eventual', 'n_known', 'e_l', 'small_group']].sort_values(['cohort_id', 'label_source', 'user_kind'])


# ## Figure

# In[8]:


from IPython.display import Image
Image(filename=str(REPO / 'docs/final/figures/el_curve.png'))

