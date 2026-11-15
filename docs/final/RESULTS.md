# TruthLag final build: results

Every number here comes from a command that ran on Scott's Mac (macOS, Darwin 27.2, 10 cores, 16 GB RAM) on the real data. Each entry gives the command and the table version. Times are UTC unless marked PT.

Environment: `.venv-lake` (uv, Python 3.12.13) from `docs/delta_lake_handoff/requirements-lake.txt`: delta-spark 4.4.1, pyspark 4.2.0, deltalake 1.6.6, pandas 2.3.3, pyarrow 26.0.1, polars 2.1.0, numpy 2.5.4. `uv pip check`: all 125 packages compatible. Java: Homebrew openjdk@21 (21.0.13).

## Phase 0 gate (2026-11-15 09:2x UTC)

| Check | Expected | Got |
| --- | --- | --- |
| Old ingest tests `python -m pytest ec-hw2/tests/test_history.py ec-hw2/tests/test_stream.py -q -p no:cacheprovider` | 30 passed | 30 passed (4.95 s) |
| `config.ALIAS_SECRET` present (value never printed) | true | true |
| Prototype parity tests `TRUTHLAG_HW2_DIR=$PWD/ec-hw2 python -m pytest tests_lake/test_parity.py -q -p no:cacheprovider` | 16 passed | 16 passed (4.71 s) |
| Spark gate `python docs/delta_lake_handoff/proto_fixture_pipeline/checks/cross_engine.py data/spark_home` | last line `STEP1C OK` | `STEP1C OK` on fix attempt 1 (Spark start 2.5 s) |
| `data/parsed/_SUCCESS_parsed.json` is the published state | 1,231,427 page-change rows, newest 2026-10-27T20:59:59Z | 1,231,427 rows; last_meta_dt 2026-10-27T20:59:59.729Z; revert_risk 789,634 lines -> 789,631 rows; tags 1,603,253 |
| Parity reference copied | `data/parity_ref/{parsed,tables}` | 23 files; SHA-256 list in `data/parity_ref/SHA256SUMS.txt` |
| Free disk | >= 10 GB | 46 GB |

Spark on macOS needed two changes, now in `etl/spark_session.py`:
1. First start failed: Netty `setsockopt() failed: Invalid argument` while the driver bound to the LAN address. Fix: `spark.driver.host`/`bindAddress` = 127.0.0.1 and `spark.{rpc,shuffle,network}.io.mode` = NIO (SPARK_LOCAL_IP=127.0.0.1).
2. Then the check's assertion failed: Python converted Spark timestamps to local time (7 h off, PDT). Fix: `TZ=UTC` for the Python process. Not a Spark bug; the check compares naive datetimes.

Exact gate command that passed:
`TZ=UTC JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home SPARK_LOCAL_IP=127.0.0.1 PYSPARK_SUBMIT_ARGS="--conf spark.driver.host=127.0.0.1 --conf spark.driver.bindAddress=127.0.0.1 --conf spark.rpc.io.mode=NIO --conf spark.shuffle.io.mode=NIO --conf spark.network.io.mode=NIO pyspark-shell" .venv-lake/bin/python docs/delta_lake_handoff/proto_fixture_pipeline/checks/cross_engine.py data/spark_home`

## Bronze (2026-11-15 09:2x UTC)

Command: `TRUTHLAG_HW2_DIR=$PWD/ec-hw2 .venv-lake/bin/python -m etl.run bronze --raw-dir data/raw` (log `data/logs/lake/bronze_run1.log`). Input: `data/raw/` after the read-only rsync from the VPS on 2026-11-15 (3.3 GB gzip; capture through 2026-11-15 ~09:20 UTC). Run time 170 s, peak RSS 2.6 GB.

| Table | Rows | Files | Cut-short files kept as complete lines | Commits (version) | Size on disk |
| --- | --- | --- | --- | --- | --- |
| bronze/page_change_events | 4,871,014 | 688 | 52 | 49 (v49) | 1.6 GB |
| bronze/revert_risk_events | 3,113,810 | 686 | 56 | 32 (v32) | 968 MB |
| bronze/tags_events | 4,343,855 | 734 | 79 | 44 (v44) | 822 MB |

Re-run (`bronze_run2.log`): 0 new rows, 0 commits in every table, 24 s.

Parity with the published parse (`python -m etl.parity bronze`, output `data/logs/lake/bronze_parity.json`). The cut is rebuilt from `data/parity_ref/parsed/_SUCCESS_parsed.json`: files in hour folders up to `dt=2026-10-27/hour=20`, minus `files_skipped_open`, cut-short files limited to `lines_kept`, no capture session that started after the parse.

| Stream | Files in cut | Published files_read | Bronze lines in cut | Published lines | Match |
| --- | --- | --- | --- | --- | --- |
| page_change | 232 | 232 | 1,231,430 | 1,231,430 | yes |
| revert_risk | 230 | 230 | 789,634 | 789,634 | yes |
| tags | 286 | 286 | 1,603,253 | 1,603,253 | yes |

No cut-short file of the parse grew later: the capture leaves a file without its gzip end marker when it restarts (about every 15 min), so these files are final.

Bronze rows per event date (UTC date of meta_dt; Nov 15 is partial):

| Date | page_change | revert_risk | tags |
| --- | --- | --- | --- |
| 2026-10-17 | 0 | 0 | 136,275 |
| 2026-10-18 | 0 | 0 | 147,792 |
| 2026-10-19 | 5,756 | 3,079 | 147,174 |
| 2026-10-20 | 161,649 | 95,059 | 157,771 |
| 2026-10-21 | 128,814 | 84,462 | 135,537 |
| 2026-10-22 | 137,043 | 89,493 | 139,945 |
| 2026-10-23 | 158,094 | 95,507 | 153,334 |
| 2026-10-24 | 155,627 | 107,418 | 142,640 |
| 2026-10-25 | 183,349 | 124,679 | 162,852 |
| 2026-10-26 | 162,638 | 102,816 | 156,603 |
| 2026-10-27 | 161,578 | 100,288 | 144,273 |
| 2026-10-28 | 185,389 | 115,247 | 144,707 |
| 2026-10-29 | 236,796 | 154,442 | 165,167 |
| 2026-10-30 | 193,442 | 134,911 | 137,705 |
| 2026-10-31 | 184,492 | 127,543 | 141,802 |
| 2026-11-01 | 200,384 | 138,431 | 143,841 |
| 2026-11-02 | 205,870 | 127,068 | 163,400 |
| 2026-11-03 | 165,329 | 107,288 | 144,215 |
| 2026-11-04 | 158,027 | 99,422 | 136,177 |
| 2026-11-05 | 180,055 | 106,477 | 157,090 |
| 2026-11-06 | 198,511 | 124,625 | 152,659 |
| 2026-11-07 | 212,787 | 145,255 | 142,172 |
| 2026-11-08 | 204,702 | 139,314 | 146,288 |
| 2026-11-09 | 186,952 | 112,781 | 151,296 |
| 2026-11-10 | 209,261 | 120,468 | 161,818 |
| 2026-11-11 | 179,669 | 111,124 | 143,892 |
| 2026-11-12 | 251,315 | 145,436 | 148,612 |
| 2026-11-13 | 210,368 | 139,317 | 146,018 |
| 2026-11-14 | 168,640 | 105,159 | 139,374 |
| 2026-11-15 | 84,477 | 56,701 | 53,426 |

## Silver stream tables (2026-11-15 09:31 UTC)

Command: `python -m etl.run silver` (log `data/logs/lake/silver_run1.log`), all 28 event dates, 181 s, peak RSS 6.4 GB.

| Table | Rows (all dates) | Repeats removed | Version |
| --- | --- | --- | --- |
| silver/page_change | 4,871,010 | 4 repeated meta_id | v28 |
| silver/revert_risk | 3,113,807 (one per revision) | 3 repeated rev_id | v28 |
| silver/tag_events | 4,343,852 | 3 repeated meta_id | v30 |
| silver/capture_gaps | 5 gaps over 120 s | | v1 |

Parity at `meta_dt <= 2026-10-27T20:59:59.999999Z` against `data/parity_ref/parsed/*.parquet` (`python -m etl.parity silver`, output `data/logs/lake/silver_parity.json`): same keys and same values, times to the microsecond.

| Table | Lake rows at the cut | Published rows | Only in lake | Only in published | Same content |
| --- | --- | --- | --- | --- | --- |
| page_change | 1,231,427 | 1,231,427 | 0 | 0 | True |
| tag_events | 1,603,253 | 1,603,253 | 0 | 0 | True |
| revert_risk | 789,631 | 789,631 | 0 | 0 | True |

Rows per day at the cut equal `rows_per_day` of the published parse for every date (page_change Oct 19-27, tag_events Oct 17-27). Capture gaps: the 3 published gaps (revert-risk stream, 850 s in total, before the cut) are reproduced; 2 more gaps fall after the cut.

## Silver cohort tables at the parity as_of (2026-11-15 09:35 UTC)

Commands: `python -m etl.history all` (Bronze history_slim 5,266,843 rows and history_full 300,564 rows, each equal to its file's highest source_row; silver/history_slim 5,266,843; history cohort via `parse_history.run`, 22.5 s), then `python -m etl.run cohorts --as-of 2026-10-27T20:59:59.999999Z` (7 s), then `python -m etl.parity cohorts` (output `data/logs/lake/cohort_parity.json`). This is the real-data parity test: every table equals the published Parquet file in `data/parity_ref/tables/`, value for value.

| Table | Lake rows | Published rows | Same content | Lake version |
| --- | --- | --- | --- | --- |
| silver/history_revisions | 295,016 | 295,016 | True | v1 |
| silver/history_revert_links | 19,858 | 19,858 | True | v1 |
| silver/live_revisions | 279,466 | 279,466 | True | v2 |
| silver/live_revert_links | 18,358 | 18,358 | True | v2 |
| silver/live_revert_links_all | 59,127 | 59,127 | True | v2 |
| silver/late_reverts | 4,350 | 4,350 | True | v2 |

A second cohort build with the same as_of wrote no new version (`cohorts_parity_rerun.log`: wrote=False for all four tables). The prototype fixture test still passes (`tests_lake/test_parity.py`, 16 passed); the real-data parity above is the stronger check.


## Gold at the parity as_of: star schema and E(L) (2026-11-15 09:37 UTC)

Build order (knowledge order, so the table histories tell the story; each `gold_run` refuses an older as_of):
1. `python -m etl.run cohorts --as-of 2026-10-24T00:00:00.000000Z`, then `python -m etl.gold_run --as-of 2026-10-24T00:00:00.000000Z --steps ddl,dims,facts,labels` (37 s; the marts step is refused before 2026-10-27 00:05, guard 4). Gold versions v1.
2. `python -m etl.run cohorts --as-of 2026-10-27T20:59:59.999999Z`, then `python -m etl.gold_run --as-of 2026-10-27T20:59:59.999999Z` (41 s). dim_page v2 (+302,576 versions, 1,499 closed), fact_edit v2 (778 rows updated: live labels learned between Oct 24 and Oct 27), mart_el_curve v1, mart_el_by_burst v1.
3. `python -m etl.gold_checks --out data/lake/_runs/gold_checks_parity.json`: **30 of 30 checks passed**.

| Check | Expected | Got |
| --- | --- | --- |
| fact_edit history rows | 295016 | 295016  |
| fact_edit live rows | 279466 | 279466  |
| fact_edit history rows by user_kind | {"bot": 33483, "temporary": 38164, "registered": 223366, "unknown": 3} | {"temporary": 38164, "registered": 223366, "unknown": 3, "bot": 33483}  |
| fact_edit live rows by user_kind | {"bot": 31973, "temporary": 36314, "registered": 211179} | {"temporary": 36314, "registered": 211179, "bot": 31973}  |
| mart_el_curve history known by wait (all editors) | {"0": 0, "1 min": 3506, "5 min": 6204, "15 min": 7737, "1 h": 9822, "6 h": 12900, "1 d": 15697, "2 d": 16725, "4 d": 17646} | {"0": 0, "1 min": 3506, "5 min": 6204, "15 min": 7737, "1 h": 9822, "6 h": 12900, "1 d": 15697, "2 d": 16725, "4 d": 17646}  |
| mart_el_curve live known by wait (all editors) | {"0": 0, "1 min": 3986, "5 min": 6958, "15 min": 8398, "1 h": 10326, "6 h": 13405, "1 d": 15936, "2 d": 16699, "4 d": 17818} | {"0": 0, "1 min": 3986, "5 min": 6958, "15 min": 8398, "1 h": 10326, "6 h": 13405, "1 d": 15936, "2 d": 16699, "4 d": 17818}  |
| live E(1 h) = 0.4205 | 0.4205 | 0.4205  |
| history E(1 h) = 0.4434 | 0.4434 | 0.4434  |
| live share known at 1 h = 57.95% | 57.95 | 57.95  |
| mart_el_curve history temporary at 1 h (known, eventual) | [6157, 9863] | [6157, 9863]  |
| mart_el_curve history registered at 1 h (known, eventual) | [3622, 7623] | [3622, 7623]  |
| mart_el_curve live temporary at 1 h (known, eventual) | [6358, 9772] | [6358, 9772]  |
| mart_el_curve live registered at 1 h (known, eventual) | [3928, 7905] | [3928, 7905]  |
| fact_edit history revisions per burst group (0,1,2-4,5-9,10+) | [202410, 42155, 32697, 11888, 5866] | [202410, 42155, 32697, 11888, 5866]  |
| mart_el_by_burst history eventual reverts in 10+ | 343 | 343  |
| fact_edit live revisions per burst group (0,1,2-4,5-9,10+) | [190392, 39277, 30782, 11929, 7086] | [190392, 39277, 30782, 11929, 7086]  |
| mart_el_by_burst live eventual reverts in 10+ | 439 | 439  |
| dim_page: pages without exactly one current row | 0 | 0  |
| dim_page: gaps or overlaps between consecutive versions | 0 | 0  |
| fact_edit rows with no page_key | 0 | 0  |
| fact_edit rows that join to other than exactly one dim_page version | 0 | 0  |
| delta-rs row count of gold/dim_cohort equals Spark's | 3 | 3  |
| delta-rs row count of gold/dim_snapshot equals Spark's | 1 | 1  |
| delta-rs row count of gold/dim_time equals Spark's | 8640 | 8640  |
| delta-rs row count of gold/dim_user equals Spark's | 66297 | 66297  |
| delta-rs row count of gold/dim_page equals Spark's | 766557 | 766557  |
| delta-rs row count of gold/fact_edit equals Spark's | 574482 | 574482  |
| delta-rs row count of gold/fact_revert_label equals Spark's | 5266843 | 5266843  |
| delta-rs row count of gold/mart_el_curve equals Spark's | 81 | 81  |
| delta-rs row count of gold/mart_el_by_burst equals Spark's | 108 | 108  |

E(L) from `gold/mart_el_curve` v1, all editors (4-day horizon, 9 waits from `config.WAIT_POINTS_S`):

| Wait | History known of 17,646 | History E(L) | Live known of 17,818 | Live E(L) |
| --- | --- | --- | --- | --- |
| 0 | 0 | 1.0000 | 0 | 1.0000 |
| 1 min | 3,506 | 0.8013 | 3,986 | 0.7763 |
| 5 min | 6,204 | 0.6484 | 6,958 | 0.6095 |
| 15 min | 7,737 | 0.5615 | 8,398 | 0.5287 |
| 1 h | 9,822 | 0.4434 | 10,326 | 0.4205 |
| 6 h | 12,900 | 0.2690 | 13,405 | 0.2477 |
| 1 d | 15,697 | 0.1104 | 15,936 | 0.1056 |
| 2 d | 16,725 | 0.0522 | 16,699 | 0.0628 |
| 4 d | 17,646 | 0.0000 | 17,818 | 0.0000 |

A re-run at the same as_of (`--steps dims,facts,labels`, `gold_parity_rerun.log`) wrote no commit in any dimension or fact. A run at the older as_of 2026-10-24 is refused (guard 3: it differs from `_runs/latest.json`).

Design changes against LAKE_DESIGN.md, made for the real data:
- `fact_edit` key is `(cohort_id, wiki_db, rev_id)`: the extended cohort `live_ext` contains the live cohort, so one revision can be a fact of two cohorts.
- `fact_edit.user_kind` (D19) added. `visibility_change` events are left out of the page observations (they change no title, namespace or deleted state). Stream observations need `meta_dt <= as_of` too.
- The dump's current title enters `dim_page` as an observation at `config.HISTORY_DUMP_LAST_REVISION` (PLAN Phase 4 step 7).
- `dim_snapshot` takes the cutoff from `config.HISTORY_DUMP_LAST_REVISION`, not from the newest slim row.
- The mart series "live cohort, dump labels" is not built: no 2026-10 snapshot exists (see STATUS.md, blocker 1).

