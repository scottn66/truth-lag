# The ingest folders: how the raw data becomes tables

There are **two** folders named `ingest`. Do not mix them up.

| Folder | What is in it | Used for HW2? |
|---|---|---|
| repo-root `ingest/vps/` | A copy of the capture that runs on the VPS | Yes, as a record only. Never run it from here. |
| repo-root `ingest/collect_eventstreams.py` | The older collector for the Mac | **No.** Do not run it. |
| `ec-hw2/ingest/` (this folder) | The parse scripts that turn the copied files into tables | Yes |

All rules (time windows, user kinds, thresholds) come from [`../config.py`](../config.py).
Every column of every table is listed in [`../DATA_MODEL.md`](../DATA_MODEL.md). If a script and DATA_MODEL.md disagree, the bug is in the script.
All data times are UTC.

---

## 1. The VPS capture (repo-root `ingest/vps/`)

The live capture runs on the VPS `vps-coin`, in `/opt/truthlag`. The repo keeps a copy of its files, so the report can show the code:

| File | What it does |
|---|---|
| [`capture.py`](../../ingest/vps/capture.py) | Reads EventStreams, keeps only English Wikipedia (`enwiki`), drops test (canary) events, and saves each event as one line in a `.ndjson.gz` file. |
| [`truthlag-capture-a.service`](../../ingest/vps/truthlag-capture-a.service) | systemd unit A: `mediawiki.page_change.v1` + `mediawiki.page_revert_risk_prediction_change.v1`, replayed from 2026-10-19 23:00 UTC (unit running since 2026-10-24 04:52 UTC). |
| [`truthlag-capture-b.service`](../../ingest/vps/truthlag-capture-b.service) | systemd unit B: `mediawiki.revision-tags-change`, replayed from 2026-10-17 00:00 UTC (unit running since 2026-10-24 04:52 UTC). |
| [`filter_history.py`](../../ingest/vps/filter_history.py) | Ran once. It read the 557 MB History dump for 2026-09 and wrote the two smaller files we use. |
| [`filter_stats.json`](../../ingest/vps/filter_stats.json) | The filter's counts: 6,369,430 rows read, 0 bad rows, 300,564 cohort rows, 5,266,843 September revisions, 154 seconds. |
| [`README.md`](../../ingest/vps/README.md) | How the capture works on the VPS. |

**The live copy runs on the VPS. Never edit it from here.** A change in this repo does not change the VPS.
Never stop, restart or change the units `truthlag-capture-a` and `truthlag-capture-b`.

Facts about the raw files (the parse scripts depend on them):
- The layout is `data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-<session>-<n>.ndjson.gz`.
- `dt` and `hour` come from `meta.dt`, the time the stream published the event.
- Each run of `capture.py` is one session, and each session writes its own part files. So one hour can have several part files.
- After a restart, the capture resumes from its last saved position. Some events can then appear twice. The parse script keeps one row per `meta.id`.
- A file that is still open has no gzip end marker yet. The parse script skips files changed in the last 2 minutes (`config.OPEN_FILE_GRACE_S` = 120 seconds).
- The Mac gets the files only by rsync: `rsync -az --partial vps-coin:/opt/truthlag/data/raw/ data/raw/`. **Never add `--delete`.**

## 2. The older Mac collector (repo-root `ingest/collect_eventstreams.py`)

This was the first collector, written for the final project. It is **not used for HW2**.
Do not run it: it opens an EventStreams connection, and the VPS needs both connection slots that Wikimedia allows.

---

## 3. The parse scripts (this folder)

Run them from the repo folder (`truth-lag`), in this order. Each one writes a file named `name.tmp` first, then renames it, then writes a `_SUCCESS_<step>.json` file with its row counts. The next script checks that file.

| # | Script | Reads | Writes | Run |
|---|---|---|---|---|
| - | `history_columns.py` | (a helper, not a script) | Nothing. It lists the 78 dump columns and their types, and `cast_history_frame` turns the text columns into numbers, true/false and UTC times. | (imported by the scripts) |
| 1 | `parse_history.py` | `data/history/enwiki_rev_ns0_2026-09-08_10.parquet` (78 columns) and `data/history/enwiki_rev_all_2026-09_slim.parquet` (12 columns). All columns are text. | `data/tables/history_revisions.parquet`, `history_revert_links.parquet`, `history_summary.json`, `_SUCCESS_history.json` | `.venv/bin/python ec-hw2/ingest/parse_history.py` |
| 2 | `parse_stream.py` | `data/raw/<stream>/dt=*/hour=*/part-*.ndjson.gz` for the 3 streams | `data/parsed/page_change.parquet`, `revert_risk.parquet`, `tag_events.parquet`, `capture_gaps.csv`, `_SUCCESS_parsed.json` | `.venv/bin/python ec-hw2/ingest/parse_stream.py` |
| 3 | `label_live.py` | `data/parsed/page_change.parquet`, `tag_events.parquet`, `revert_risk.parquet` | `data/tables/live_revisions.parquet`, `live_revert_links.parquet`, `live_revert_links_all.parquet`, `live_summary.json`, `_SUCCESS_live.json` | `.venv/bin/python ec-hw2/ingest/label_live.py` |
| 4 | `late_reverts.py` | the slim September file, `data/parsed/page_change.parquet` and `tag_events.parquet`, `data/tables/live_revert_links_all.parquet` and `history_revisions.parquet` | `data/tables/late_reverts.parquet`, `late_reverts_summary.json`, `_SUCCESS_late_reverts.json` | `.venv/bin/python ec-hw2/ingest/late_reverts.py` |
| 5 | `build_documents.py` | the tables in `data/tables/` | MongoDB documents for `load_mongo.py` (in memory). On disk, only `ec-hw2/results/sample_documents.json`: one history and one live document, with pseudonyms (`editor_` + 10 hex digits, a keyed hash with `ALIAS_SECRET` from `ec-hw2/.env`). | Used by `load_mongo.py`. It also runs alone (`.venv/bin/python ec-hw2/ingest/build_documents.py`): it checks the inputs, builds every document without a database, prints the counts and writes the sample file. |

`parse_history.py` and `parse_stream.py` do not depend on each other. Steps 3 and 4 need step 2, and step 4 also needs step 3.

### What each table holds (short version of DATA_MODEL.md)
- **`data/parsed/page_change.parquet`**: one row per page_change event, in **all namespaces** and of all kinds (edit, create, move, delete, ...). It includes the revert fields of each event.
- **`data/parsed/revert_risk.parquet`**: one revert-risk score per rev_id (the earliest one).
- **`data/parsed/tag_events.parquet`**: one row per tags event, with the tags added and removed, and whether `mw-reverted` was added.
- **`data/parsed/capture_gaps.csv`**: every hole longer than 120 seconds between two events of one stream.
- **`history_revisions.parquet`** and **`live_revisions.parquet`**: one row per revision of the cohort, with the same columns in both. Only the history table has the revert labels (`reverted`, `secs_to_revert`, the reverter).
- **`history_revert_links.parquet`** and **`live_revert_links.parquet`**: one row per reverted cohort revision, with the revert that undid it and the time to revert (T). The live rows also have the stream delay (K). For the live cohort it is the first covering exact revert.
- **`live_revert_links_all.parquet`**: every (reverted, reverting) pair, for all revert methods. It is used for checks.
- **`late_reverts.parquet`**: September revisions that the dump calls "not reverted", but that the October stream shows being reverted. The counts are lower bounds.

### Rules the scripts share (all in `config.py`)
- Both cohorts drop null revisions (no text change, such as page moves), revisions outside the window, and revisions not in namespace 0.
- The **user kind** is checked in this order: unknown (empty name), bot, temporary (logged-out editor), registered.
- **Reverted** means within 20 days for the history cohort and within 4 days for the live cohort.
- The stream labels of the live cohort are PROVISIONAL until the capture is past 2026-10-27 00:05 UTC. `label_live.py` writes this flag into `_SUCCESS_live.json`.
- Never delete or change anything in `data/raw/` or `data/history/`. Those files cannot be made again.

### Tests
The ingest tests are `ec-hw2/tests/test_history.py` and `ec-hw2/tests/test_stream.py` (all tests: `.venv/bin/python -m pytest ec-hw2/tests -q`). Run one like this:
```
.venv/bin/python -m pytest ec-hw2/tests/test_history.py -q
```
You should see `passed` and no `failed`.
