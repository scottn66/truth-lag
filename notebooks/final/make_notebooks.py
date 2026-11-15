"""Build, run and export the final-project notebooks (one per component) with their .py copies.

Each notebook reads the lake (data/lake/) and the run records in data/lake/_runs/*.json that the etl commands
wrote; it re-runs no heavy job. Outputs stay small (< 1 MB per notebook). No editor names are shown.

Run (from the repository root, lake environment)
    .venv-lake/bin/python notebooks/final/make_notebooks.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

SETUP = """import json, os, sys
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
"""

NOTEBOOKS = {
    "01_bronze_silver_parity": [
        ("md", "# 01 Bronze and Silver: load and parity\n\nRaw capture files go to Bronze with delta-rs (append-only, one row per captured line). Silver applies the EC HW2 parser rules. This notebook shows the row counts and the parity checks against the published EC HW2 tables (`data/parity_ref/`).\n\nCommands that made the tables: `python -m etl.run bronze --raw-dir data/raw`, `python -m etl.run silver`, `python -m etl.history all`, `python -m etl.parity bronze|silver|cohorts`."),
        ("code", SETUP),
        ("md", "## Bronze tables: versions and commits"),
        ("code", "for t in ['bronze/page_change_events', 'bronze/revert_risk_events', 'bronze/tags_events', 'bronze/history_slim', 'bronze/history_full']:\n    print(t, 'version', DeltaTable(str(LAKE / t)).version())\nhistory('bronze/page_change_events', 5)"),
        ("md", "## Bronze parity with the published parse cut\n\nThe cut is rebuilt from `_SUCCESS_parsed.json`: hour folders up to 2026-10-27 hour 20, minus files skipped as open, cut-short files limited to the lines the parse kept."),
        ("code", "bp = json.loads((REPO / 'data/logs/lake/bronze_parity.json').read_text())\npd.DataFrame({s.split('.')[1] if 'revision' not in s else 'tags': {k: v for k, v in d.items() if k != 'bronze_rows_per_day'} for s, d in bp.items()}).T"),
        ("md", "## Bronze rows per event date"),
        ("code", "pd.DataFrame({s.split('mediawiki.')[1]: d['bronze_rows_per_day'] for s, d in bp.items()}).fillna(0).astype(int)"),
        ("md", "## Silver parity at the published cut (meta_dt <= 2026-10-27T20:59:59.999999Z)"),
        ("code", "sp = json.loads((REPO / 'data/logs/lake/silver_parity.json').read_text())\npd.DataFrame({k: {c: v[c] for c in ('rows_lake', 'rows_ref', 'only_in_lake', 'only_in_ref', 'same_content')} for k, v in sp.items()}).T"),
        ("md", "## Cohort tables against `data/tables` (built at the parity as_of)"),
        ("code", "cp = json.loads((REPO / 'data/logs/lake/cohort_parity.json').read_text())\npd.DataFrame({k: {c: v[c] for c in ('rows_lake', 'rows_ref', 'only_in_lake', 'only_in_ref', 'same_content', 'lake_version')} for k, v in cp.items()}).T"),
        ("md", "## Capture gaps over 120 s"),
        ("code", "table('silver/capture_gaps')"),
    ],
    "02_gold_star_schema": [
        ("md", "# 02 Gold: star schema, SCD Type 2 page dimension, E(L) marts\n\nSpark SQL writes Gold (`python -m etl.gold_run --as-of ...`). Builds ran in knowledge order: as_of 2026-10-24 (early), 2026-10-27T20:59:59.999999Z (parity), 2026-11-13T23:59:59.999999Z (extended). The checks are in `python -m etl.gold_checks`."),
        ("code", SETUP),
        ("md", "## Tables, versions and row counts"),
        ("code", "rows = []\nfor t in ['dim_cohort', 'dim_snapshot', 'dim_time', 'dim_user', 'dim_page', 'fact_edit', 'fact_revert_label', 'mart_el_curve', 'mart_el_by_burst']:\n    dt = DeltaTable(str(LAKE / 'gold' / t))\n    rows.append({'table': 'gold/' + t, 'version': dt.version(), 'rows': sum(b.num_rows for b in dt.to_pyarrow_dataset().to_batches(columns=[dt.schema().to_arrow().names[0]])), 'cdf': dt.metadata().configuration.get('delta.enableChangeDataFeed')})\npd.DataFrame(rows)"),
        ("md", "## Commit history of fact_edit (commit metadata holds step and as_of)"),
        ("code", "history('gold/fact_edit')"),
        ("md", "## Checks at the parity and the extended as_of"),
        ("code", "for f in ('gold_checks_parity.json', 'gold_checks_ext.json'):\n    g = run(f); print(f, g['passed'], 'of', g['total'], 'passed; versions', g['versions'])\npd.DataFrame(run('gold_checks_ext.json')['checks'])[['check', 'ok']]"),
        ("md", "## dim_page (SCD Type 2): one moved page, with its versions\n\nThe page with the most versions among history-cohort pages. Titles are page titles (public), not editor names."),
        ("code", "dp = table('gold/dim_page')\nfe = table('gold/fact_edit', columns=['cohort_id', 'page_key', 'event_dt'])\nhist_pages = dp[dp.page_key.isin(fe[fe.cohort_id == 'history'].page_key)].page_id.unique()\nn = dp[dp.page_id.isin(hist_pages)].groupby('page_id').size().sort_values(ascending=False)\npid = n.index[0]\ndp[dp.page_id == pid].sort_values('valid_from')"),
        ("md", "## E(L) curve, all editors"),
        ("code", "el = table('gold/mart_el_curve')\nel[el.user_kind == 'all'].pivot_table(index=['wait_s', 'wait_label'], columns='cohort_id', values='e_l').round(4)"),
        ("md", "## E(L) at 1 h by editor kind (kind at edit time); small groups flagged"),
        ("code", "el[el.wait_label == '1 h'][['cohort_id', 'user_kind', 'n_eventual', 'n_known', 'e_l', 'small_group']].sort_values(['cohort_id', 'user_kind'])"),
        ("md", "## Figure"),
        ("code", "from IPython.display import Image\nImage(filename=str(REPO / 'docs/final/figures/el_curve.png'))"),
    ],
    "03_hypotheses": [
        ("md", "# 03 Hypotheses H1, H3, H4\n\nDefinitions: `docs/delta_lake_handoff/DECISIONS.md`. Computed by `python -m etl.hypotheses` from Gold (versions below). Intervals: Poisson bootstrap over pages, B = 2,000, seed 226."),
        ("code", SETUP + "h = run('hypotheses.json')\nprint('Gold versions read:', h['gold_versions'])"),
        ("md", "## H1: share of eventual reverts known at 1 h (threshold 60%) and 48 h (threshold 95%)"),
        ("code", "pd.DataFrame(h['H1'])[['series', 'eventual_reverts', 'pages', 'known_1h_pct', 'known_1h_ci', 'known_48h_pct', 'known_48h_ci', 'verdict']]"),
        ("md", "## H3: E(L) for burst edits (>= 10 page edits in the prior hour) against the rest"),
        ("code", "pd.DataFrame(h['H3'])[['series', 'L', 'burst_reverts', 'E_burst', 'E_burst_ci', 'E_rest', 'E_rest_ci', 'diff_burst_minus_rest', 'diff_ci', 'verdict']]"),
        ("md", "## H4: title at event time (dim_page version) against the current title"),
        ("code", "pd.DataFrame({k: v for k, v in h['H4'].items() if isinstance(v, dict)})"),
        ("code", "print('history_revisions rows with page_title != page_title_historical:', h['H4']['history_revisions_title_differs_from_historical'])"),
        ("md", "## E(L) by burst group (gold/mart_el_by_burst)"),
        ("code", "b = table('gold/mart_el_by_burst')\nb[b.wait_label.isin(['1 h', '1 d'])].pivot_table(index=['cohort_id', 'burst_group'], columns='wait_label', values=['n_eventual', 'e_l']).round(4)"),
    ],
    "04_time_travel": [
        ("md", "# 04 Time travel: then vs now\n\n`python -m etl.time_travel` runs `etl/sql/80_time_travel_then_and_now.sql`. Versions of `gold/fact_edit` are found by their commit metadata `as_of`, never by timestamp. Here the same query is repeated with delta-rs, to show that both engines read the same versions."),
        ("code", SETUP + "tt = run('time_travel.json')\nprint(tt['fact_edit_versions'])"),
        ("code", "pd.DataFrame(tt['then_and_now'])"),
        ("md", "## The same, read by delta-rs at each version"),
        ("code", "rows = []\nfor k, v in tt['fact_edit_versions'].items():\n    f = table('gold/fact_edit', version=v, columns=['cohort_id', 'live_revert_flag'])\n    f = f[f.cohort_id == 'live']\n    rows.append({'build': k, 'version': v, 'live_revisions': len(f), 'reverted_as_known': int(f.live_revert_flag.fillna(False).sum())})\npd.DataFrame(rows)"),
        ("md", "## Change Data Feed of fact_edit between the versions"),
        ("code", "pd.DataFrame(tt['change_feed'])"),
        ("code", "tt['early_to_parity_updates']"),
        ("md", "## Silver by version: live_revert_links at each build"),
        ("code", "pd.DataFrame(tt['silver_live_revert_links_by_version'])"),
    ],
    "05_streaming_algorithms": [
        ("md", "# 05 Streaming algorithms against exact answers\n\n`python -m etl.streaming_algos`. Stream: enwiki page-change events in publish order, 2026-10-19 23:00 to 2026-11-13 23:59 UTC. HyperLogLog and Flajolet-Martin (PCSA) for distinct pages and editors (E4), a Bloom filter on meta_id over the raw Bronze lines, DGIM for revert events in the last hour, reservoir sampling and the AMS second moment. Memory of the exact answer is an estimate (8 bytes per distinct hash)."),
        ("code", SETUP + "d = run('streaming_algos.json')\nd['stream'], d['exact_distinct']"),
        ("md", "## Distinct counts: error and memory (5 hash salts per sketch)"),
        ("code", "pd.DataFrame(d['distinct'])"),
        ("code", "pd.DataFrame(d['spark_approx_count_distinct'])"),
        ("code", "d['editors_merged_daily_hll12']"),
        ("md", "## Bloom filter on meta_id"),
        ("code", "pd.DataFrame(d['bloom_meta_id'])"),
        ("md", "## DGIM: revert events in the last hour"),
        ("code", "pd.DataFrame(d['dgim_reverts_last_hour'])"),
        ("md", "## Reservoir sampling and AMS"),
        ("code", "d['reservoir_edits'], d['ams_f2_edits_per_page']"),
    ],
    "06_structured_streaming": [
        ("md", "# 06 Spark Structured Streaming, Bronze to Silver (E5, small)\n\n`python -m etl.stream_sss`. A producer process appends captured lines to a demo Delta table at a fixed rate; a streaming query (trigger 1 s, `foreachBatch`) parses them and MERGEs them into a demo Silver table. Latency = MERGE commit time - produced_at. Runs on one laptop (local[4])."),
        ("code", SETUP + "s = run('stream_sss.json')\npd.DataFrame(s['rates'])[['target_rate_eps', 'events', 'micro_batches', 'throughput_eps', 'latency_p50_s', 'latency_p95_s', 'latency_max_s', 'mean_batch_rows', 'mean_batch_merge_s']]"),
        ("code", "s['drain']"),
        ("code", "import matplotlib.pyplot as plt\nr = pd.DataFrame(s['rates'])\nfig, ax = plt.subplots(figsize=(6, 3.5))\nax.plot(r.target_rate_eps, r.latency_p95_s, 'o-', label='p95')\nax.plot(r.target_rate_eps, r.latency_p50_s, 's-', label='p50')\nax.axhline(5, color='grey', ls='--', label='5 s (E5)')\nax.axvline(2500, color='grey', ls=':', label='2,500 events/s target')\nax.set_xscale('log'); ax.set_xlabel('input rate (events/s)'); ax.set_ylabel('latency (s)'); ax.legend(); ax.grid(alpha=.3)"),
    ],
    "07_team_exports": [
        ("md", "# 07 Extracts for the team (data/exports/)\n\n`python -m etl.exports`. For Wanru (MinHash LSH on comments and titles), Zhenni (k-anonymity and Laplace noise) and the charts. Schemas and regeneration: `docs/final/HANDOFF_TEAM.md`. Human editors appear only as pseudonyms."),
        ("code", SETUP + "m = json.loads((REPO / 'data/exports/manifest.json').read_text())\nprint(m['lake_versions'])\npd.DataFrame(m['files']).T[['rows', 'bytes']]"),
        ("code", "lsh = pd.read_parquet(REPO / 'data/exports/lsh_edits.parquet')\nlsh.groupby(['cohort_id', 'label']).size()"),
        ("code", "g = pd.read_csv(REPO / 'data/exports/group_sizes_by_kind_hour.csv')\ng.describe()"),
    ],
}


def build() -> None:
    for name, cells in NOTEBOOKS.items():
        nb = nbf.v4.new_notebook()
        nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in cells]
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        path = HERE / f"{name}.ipynb"
        nbf.write(nb, path)
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
                        "--ExecutePreprocessor.timeout=600", str(path)], check=True, cwd=HERE)
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "script", str(path)], check=True, cwd=HERE)
        print(name, path.stat().st_size, "bytes")


if __name__ == "__main__":
    only = sys.argv[1:]
    if only:
        NOTEBOOKS = {k: v for k, v in NOTEBOOKS.items() if k in only}
    build()
