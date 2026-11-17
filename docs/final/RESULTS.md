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


## Gold extended to Nov 13 (2026-11-15 09:41 UTC)

Commands: `python -m etl.run cohorts --as-of 2026-11-13T23:59:59.999999Z` (46 s, peak 6.4 GB), `python -m etl.run cohorts_ext --as-of 2026-11-13T23:59:59.999999Z` (60 s, 6.1 GB), `python -m etl.gold_run --as-of 2026-11-13T23:59:59.999999Z` (57 s), `python -m etl.gold_checks --out data/lake/_runs/gold_checks_ext.json` (**30 of 30 passed** again: the published cohorts do not move).

`live_ext` = the live rules of `label_live.py`, unchanged, on the edits of 2026-10-20 to 2026-11-08 (window end 2026-11-09 00:00; every edit has 4 days of follow-up before the as_of). Only `config.LIVE_WINDOW` is swapped during the call (`etl/silver_cohorts.py: build_ext`).

| Table | Rows at Nov 13 | Version | Change from the parity version |
| --- | --- | --- | --- |
| silver/live_ext_revisions | 2,397,738 | v1 | new |
| silver/live_ext_revert_links | 122,192 | v1 | new |
| gold/fact_edit | 2,972,220 | v3 | +2,397,738 inserted, 0 updated |
| gold/dim_page | 2,324,643 | v3 | +1,558,086 versions, 15,707 closed |
| gold/dim_user | 185,465 | v2 | +119,168, 42 updated |
| gold/dim_time | 33,118 | v2 | +24,478 |
| gold/mart_el_curve | 117 | v2 | overwrite |
| gold/mart_el_by_burst | 162 | v2 | overwrite |

E(L), all editors, `gold/mart_el_curve` v2:

| Wait | live known of 17,818 | live E(L) | live_ext known of 112,937 | live_ext E(L) | history E(L) |
| --- | --- | --- | --- | --- | --- |
| 0 | 0 | 1.0000 | 0 | 1.0000 | 1.0000 |
| 1 min | 3,986 | 0.7763 | 25,333 | 0.7757 | 0.8013 |
| 5 min | 6,958 | 0.6095 | 43,789 | 0.6123 | 0.6484 |
| 15 min | 8,398 | 0.5287 | 53,335 | 0.5277 | 0.5615 |
| 1 h | 10,326 | 0.4205 | 66,344 | 0.4126 | 0.4434 |
| 6 h | 13,405 | 0.2477 | 85,045 | 0.2470 | 0.2690 |
| 1 d | 15,936 | 0.1056 | 102,207 | 0.0950 | 0.1104 |
| 2 d | 16,699 | 0.0628 | 107,367 | 0.0493 | 0.0522 |
| 4 d | 17,818 | 0.0000 | 112,937 | 0.0000 | 0.0000 |

## Hypotheses (2026-11-15 09:47 UTC)

Command: `python -m etl.hypotheses` (55 s; output `data/lake/_runs/hypotheses.json`). Gold versions read: {'fact_edit': 3, 'dim_page': 3, 'fact_revert_label': 1, 'mart_el_curve': 2}. Intervals: Poisson bootstrap over pages, B = 2,000, seed 226 (a page's reverts move together).

### H1, long-tailed lag (thresholds 60% at 1 h, 95% at 48 h)

| Series | Eventual reverts | Pages | Known at 1 h (95% CI) | Known at 48 h (95% CI) | Verdict |
| --- | --- | --- | --- | --- | --- |
| live | 17,818 | 10,471 | 57.95% (56.71-59.28) | 93.72% (92.66-94.59) | not falsified |
| live_ext_october | 67,998 | 35,420 | 58.11% (57.29-59.0) | 94.64% (94.1-95.08) | not falsified; an interval crosses its threshold, so the call is not robust |
| live_ext | 112,937 | 56,531 | 58.74% (58.04-59.49) | 95.07% (94.72-95.37) | falsified (point estimate); an interval crosses its threshold, so the call is not robust |
| history | 17,646 | 10,364 | 55.66% (54.49-56.88) | 94.78% (94.12-95.4) | not falsified; an interval crosses its threshold, so the call is not robust |

Reading: on the October 2026 cohort that H1 names (live, Oct 20-22), H1 is **not falsified**: 57.95% < 60% and 93.72% < 95%, and both intervals lie below their thresholds. The 48 h share matches DECISIONS.md (16,699 of 17,818 = 93.7%). On the longer live_ext window the 48 h share is 95.07%, just over 95% (interval 94.72-95.37 crosses it), so the 48 h part is borderline; restricted to October edits it is 94.64% (94.10-95.08), below the threshold but also not robust. The 1 h part holds in every series.

### H3, bursty pages converge slowest (burst = 10 or more page edits in the prior hour, D20)

| Series | L | Burst reverts (pages) | E(L) burst (95% CI) | E(L) rest (95% CI) | Burst - rest (95% CI) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| history | 1 h | 343 (83) | 0.2566 (0.1367-0.4051) | 0.4471 (0.4353-0.4587) | -0.1905 (-0.3125 to -0.0532) | falsified: burst E(L) lower, intervals apart |
| history | 1 d | 343 (83) | 0.0700 (0.0060-0.1566) | 0.1113 (0.1030-0.1200) | -0.0413 (-0.1050 to +0.0509) | falsified (intervals overlap) |
| live | 1 h | 439 (70) | 0.2255 (0.0479-0.4503) | 0.4254 (0.4138-0.4369) | -0.1999 (-0.3716 to +0.0097) | falsified (intervals overlap) |
| live | 1 d | 439 (70) | 0.1367 (0.0023-0.3748) | 0.1048 (0.0970-0.1131) | +0.0318 (-0.1033 to +0.2528) | falsified (intervals overlap) |
| live_ext | 1 h | 3,401 (506) | 0.2887 (0.1884-0.3965) | 0.4164 (0.4111-0.4218) | -0.1277 (-0.2259 to -0.0210) | falsified: burst E(L) lower, intervals apart |
| live_ext | 1 d | 3,401 (506) | 0.0641 (0.0120-0.1366) | 0.0960 (0.0929-0.0991) | -0.0319 (-0.0834 to +0.0475) | falsified (intervals overlap) |
| live_ext_october | 1 h | 2,038 (298) | 0.3548 (0.2122-0.4923) | 0.4208 (0.4146-0.4268) | -0.0661 (-0.2122 to +0.0704) | falsified (intervals overlap) |
| live_ext_october | 1 d | 2,038 (298) | 0.1021 (0.0168-0.2165) | 0.1003 (0.0961-0.1046) | +0.0018 (-0.0836 to +0.1115) | falsified (intervals overlap) |

Reading: H3 is **falsified** in every series. Its criterion is that the intervals must not overlap with burst higher; they overlap at 1 d everywhere, and at 1 h the burst E(L) is *lower* (reverts on bursty pages become known faster), with intervals apart in history and live_ext. This matches R5 (bursts do not have higher revert rates) and the plan's expectation of a null or reversed effect.

### H4, page identity (title at event time via `dim_page` SCD2 vs the page's current title)

Facts of a cohort are keyed by page title, as a title-keyed system would do: once by the `dim_page` version valid at the edit (as-of join on `page_key`), once by the page's current version (`is_current`). Revert label: stream label for live_ext; dump label within 4 days for history.

| Measure | history (Sep 8-10) | live_ext (Oct 20 - Nov 8) |
| --- | --- | --- |
| Facts | 295,016 | 2,397,738 |
| Facts whose title or namespace at edit time differs from now | 3,381 (1.146%) | 16,762 (0.699%) |
| Pages | 165,415 | 1,238,130 |
| Pages with a fact under an older title (pages affected) | 966 (0.584%) | 3,454 (0.279%) |
| Title keys | 166,059 | 1,238,578 |
| Title keys whose edit or revert count changes | 1,853 (1.116%) | 6,779 (0.547%) |
| Title keys whose revert rate changes | 1,497 (0.901%) | 3,154 (0.255%) |
| Title keys whose revert count changes | 168 (0.101%) | 601 (0.049%) |
| Reverts attributed to a different title | 406 | 1,596 |

Beside it (PLAN Phase 4): `silver/history_revisions` rows whose `page_title` differs from `page_title_historical`: 2,319. The fact count above (3,381) is lower because `dim_page` also uses the stream's moves after the dump and the observation at the dump cutoff, and compares title and namespace per version.

Reading: the floor for H4 is not set in DECISIONS.md. The effect is real but small: 0.3-0.6% of pages, 0.5-1.1% of title keys, and 0.05-0.10% of title keys for revert counts. At a floor of 1% of pages (this build's choice, for the team to confirm) H4 is **falsified** in both cohorts; only the edit-count measure in history (1.12% of title keys) passes 1%.

## Time travel, "then vs now" (2026-11-15 09:49 UTC)

Command: `python -m etl.time_travel` (SQL `etl/sql/80_time_travel_then_and_now.sql`; output `data/lake/_runs/time_travel.json`). Versions are found by commit metadata `as_of`, never by timestamp: fact_edit {'early': 1, 'parity': 2, 'ext': 3}.

| Known at | fact_edit version | Live revisions | Reverted as known | % reverted | Newest known_dt |
| --- | --- | --- | --- | --- | --- |
| then: as_of 2026-10-24T00:00:00.000000Z | v1 | 279,466 | 17,040 | 6.097 | 2026-10-23 23:59:03.674000 |
| parity: as_of 2026-10-27T20:59:59.999999Z | v2 | 279,466 | 17,818 | 6.376 | 2026-10-26 18:30:28.229000 |
| now: as_of 2026-11-13T23:59:59.999999Z | v3 | 279,466 | 17,818 | 6.376 | 2026-10-26 18:30:28.229000 |

Change Data Feed of gold/fact_edit between the versions: v2 holds 778 update pre/post-image pairs, all live revisions that became reverted (778), none with a changed page_key; their median time from edit to known revert is 245,324 s (2.84 days). v3 holds 2,397,738 inserts (live_ext) and no update of the published cohorts.

Silver by version, `silver/live_revert_links`:

| Version | as_of | Links | Within 4-day follow-up |
| --- | --- | --- | --- |
| v1 | 2026-10-24T00:00:00.000000Z | 17,040 | 17,040 |
| v2 | 2026-10-27T20:59:59.999999Z | 18,358 | 17,818 |
| v3 | 2026-11-13T23:59:59.999999Z | 19,513 | 17,818 |

The kit's version of the SQL compared fact_revert_label at two History snapshots. No 2026-10 snapshot exists on the VPS or the Mac (STATUS.md, blocker 1), so the knowledge axis here is the stream's as_of. fact_revert_label has one load (v1, 2026-09, 5,266,843 rows).

## Streaming algorithms against exact answers (2026-11-15 09:53 UTC)

Command: `python -m etl.streaming_algos` (85 s; output `data/lake/_runs/streaming_algos.json`). Stream: enwiki page-change events of `silver/page_change` v28 in publish order, 2026-10-19 23:00:00.504000+00:00 to 2026-11-13 23:59:59.844000+00:00: 4,617,893 events, 170,315 revert events. Bloom filter: the raw `bronze/page_change_events` v49 lines in capture order (repeats included). One pass per sketch; memory is the sketch's own size. "Exact bytes" is an estimate (8 bytes per distinct 64-bit hash, a lower bound for a hash set).

### Distinct pages and editors (E4): HyperLogLog and Flajolet-Martin (PCSA)

Exact: 2,153,428 distinct pages, 229,828 distinct editors (user id + name). Each sketch ran with 5 independent hash functions (salts); the table gives the first run and the spread.

| Item | Sketch | Memory (bytes) | Estimate (salt 1) | Error salt 1 | Mean error, 5 salts | SD, 5 salts | Max abs error | Theory SE | Exact memory est. (bytes) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pages | HLL p=10 | 768 | 2,163,285 | +0.46% | +1.60% | 2.94% | 5.62% | 3.25% | 17,227,424 |
| pages | HLL p=12 | 3,072 | 2,169,372 | +0.74% | +0.60% | 1.20% | 1.52% | 1.62% | 17,227,424 |
| pages | HLL p=14 | 12,288 | 2,148,428 | -0.23% | -0.30% | 1.18% | 2.36% | 0.81% | 17,227,424 |
| pages | FM-PCSA m=64 | 256 | 2,304,677 | +7.02% | +2.05% | 10.21% | 15.67% | 9.75% | 17,227,424 |
| pages | FM-PCSA m=256 | 1,024 | 2,224,966 | +3.32% | +5.35% | 5.17% | 10.26% | 4.88% | 17,227,424 |
| pages | FM-PCSA m=1024 | 4,096 | 2,156,754 | +0.15% | +2.37% | 2.88% | 7.17% | 2.44% | 17,227,424 |
| editors | HLL p=10 | 768 | 219,584 | -4.46% | +0.11% | 2.60% | 4.46% | 3.25% | 1,838,624 |
| editors | HLL p=12 | 3,072 | 225,641 | -1.82% | -0.56% | 1.60% | 2.61% | 1.62% | 1,838,624 |
| editors | HLL p=14 | 12,288 | 225,220 | -2.00% | -0.74% | 1.16% | 2.00% | 0.81% | 1,838,624 |
| editors | FM-PCSA m=64 | 256 | 264,175 | +14.95% | +3.30% | 12.26% | 14.95% | 9.75% | 1,838,624 |
| editors | FM-PCSA m=256 | 1,024 | 240,941 | +4.83% | +2.20% | 3.62% | 4.83% | 4.88% | 1,838,624 |
| editors | FM-PCSA m=1024 | 4,096 | 239,478 | +4.20% | +1.44% | 3.63% | 5.05% | 2.44% | 1,838,624 |

Spark's built-in HyperLogLog++ (`approx_count_distinct`) on the same rows: rsd 0.05 gives 2,198,477 pages and 220,940 editors; rsd 0.01 gives 2,153,746 pages (+0.01%) and 229,227 editors (-0.26%).

Mergeability: one HLL (p = 12) per day, merged by register-wise max = 225,641 distinct editors over the whole period (-1.82%, the same registers as one sketch over the whole stream). Adding the exact daily counts instead gives 466,959, double-counting editors active on several days.

A check of the HLL code on synthetic data (8 trials of 229,828 random 64-bit keys): p = 14 mean error +0.36%, SD 0.76% (theory 0.81%); p = 12 mean +1.31%, SD 2.32%.

### Bloom filter on meta_id (repeat check) against the Silver MERGE

| Target FP rate | Bits | Hashes | Memory | Events | Exact repeats (= removed by Silver) | Flagged | True repeats found | False positives | False negatives | Observed FP rate | Exact set memory est. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.01 | 44,262,813 | 7 | 5,532,852 B | 4,617,897 | 4 | 7,566 | 4 | 7,562 | 0 | 0.001638 | 36,943,144 B |
| 0.001 | 66,394,219 | 10 | 8,299,278 B | 4,617,897 | 4 | 591 | 4 | 587 | 0 | 0.000127 | 36,943,144 B |

The filter was sized for the whole stream, so the observed rate over the stream is below the target (the target holds when the filter is full). A Bloom filter has no false negatives, so it can screen events: only the flagged ones (0.013% at the 0.001 target) need the exact lookup that the insert-only MERGE does on every event.

### DGIM: revert events in the last hour (time-based window, 10-minute evaluation marks)

| Scope | r (buckets per size) | Eval points | Mean rel. error | p95 rel. error | Max rel. error | Bound | Max buckets | Memory est. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| wiki-wide | 2 | 3,599 | 11.25% | 24.1% | 40.13% | 50.0% | 17 | 136 B vs exact window 7,024 B |
| wiki-wide | 4 | 3,599 | 5.24% | 10.84% | 16.32% | 25.0% | 31 | 248 B vs exact window 7,024 B |
| per page (200 pages with most reverts) | 2 | 34,634 | 41.18% | 50.0% | 50.0% | 50.0% | 9 | 9 buckets |

Wiki-wide, DGIM stays inside its bound with 17-31 buckets instead of every timestamp in the window. Per page, hourly revert counts are tiny (often 1), and DGIM's "half the oldest bucket" rule then costs up to 50%: for single pages an exact deque is as small and exact. This is the expected trade-off, reported as measured.

### Two more course techniques, small

- Reservoir sampling (k = 10,000, seed 226) over 4,209,083 edit events: revert-event share in the sample 3.76% (95% CI 3.387-4.133%) against the exact 4.046%: the interval holds the exact value.
- AMS estimate of the second moment F2 of edits per page (exact 249,630,183): 100 variables give 50,088,088 (-79.94%), 1000 variables give 215,925,958 (-13.5%). Edits per page are heavy-tailed, so few variables underestimate badly; error falls with more variables (median of 10 means).


## Spark Structured Streaming, Bronze to Silver (2026-11-15 10:01 UTC)

Command: `python -m etl.stream_sss` (346 s in all; output `data/lake/_runs/stream_sss.json`). Spark 4.2.0, master `local[4]`, on the laptop. A producer process appends captured page-change lines from `bronze/page_change_events` (capture order, from 2026-10-20) to a demo Delta table at a fixed rate, one delta-rs commit per second, each row stamped `produced_at` just before its commit. The streaming query reads that table as a Delta stream (trigger 1 s), parses `raw_json` with `from_json`, keeps enwiki, non-canary events with meta.id and meta.dt, drops repeated meta_id, and in `foreachBatch` MERGEs (insert-only on meta_id) into a demo Silver table. Latency of an event = the commit time of its micro-batch MERGE - produced_at (so it includes the producer's commit). 30 s per rate. Demo tables: `data/lake/stream_demo/` (the lake tables are only read).

| Input rate (events/s) | Events | Micro-batches | Throughput (events/s) | p50 latency (s) | p95 latency (s) | Max latency (s) | Mean rows per batch | Mean batch time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1,000 | 30,000 | 24 | 981.8 | 1.897 | 2.901 | 3.045 | 1,250.0 | 1.229 |
| 2,500 | 75,000 | 22 | 2,428.0 | 2.046 | 3.303 | 3.808 | 3,409.1 | 1.255 |
| 5,000 | 150,000 | 22 | 4,717.6 | 2.177 | 3.406 | 3.791 | 6,818.2 | 1.291 |
| 10,000 | 300,000 | 19 | 9,391.2 | 2.544 | 4.066 | 4.16 | 15,789.5 | 1.562 |
| 20,000 | 599,997 | 16 | 18,275.9 | 3.483 | 5.216 | 5.492 | 37,499.8 | 1.925 |

Drain without a rate limit: 500,000 lines pre-loaded in 50 commits, read with `availableNow` and 5 files per micro-batch: 10 batches in 30.1 s = **16,614.6 events/s**.

Correctness: the 500,000 rows that the drain wrote equal the batch `silver/page_change` rows for the same events (0 rows only in the stream output; 0 rows differ in rev_id, page_id, kind or meta_dt).

E5 reading: p95 latency stays under 5 s up to 10,000 events/s (4.07 s) and first passes 5 s at 20,000 events/s (5.22 s). The proposal's target of 2,500 events/s or more is met (p95 3.30 s at 2,500/s). For scale, the captured enwiki page-change stream averages about 2.1 events/s (4,871,014 events in 26.4 days). At 20,000/s the stream wrote 599,997 of 600,000 lines: the 3 missing lines are repeated meta_ids in that slice of Bronze (1 on Oct 24, 2 on Oct 26), which Silver also drops.


## End-to-end rebuild from scratch (2026-11-15 10:00-10:12 UTC)

Command: `SKIP_EXTRAS=1 bash etl/build_all.sh data/lake_e2e` (log `data/logs/lake/build_all_e2e.log`): a new, empty lake folder, built from `data/raw` and `data/history` through every step and check in knowledge order. 729 s wall time, exit 0.

| Compared with the main lake (`data/lake`) | Result |
| --- | --- |
| Bronze parity (3 streams), Silver parity (3 tables), cohort parity (6 tables) | all match |
| Gold checks at the parity as_of / at Nov 13 | 30 of 30 / 30 of 30 |
| E(L) curves (all cohorts, all waits) | identical |
| H1, H3, H4 results (bootstrap seed 226) | identical |
| Time travel (fact_edit v1, v2, v3 known reverts) | identical |

The rebuild folder was deleted afterwards to free 5.7 GB; the command above recreates it.

## Second History snapshot 2026-10: filter, load, label changes, reconciliation (2026-11-15 10:39-10:50 UTC)

Input: the public month files of snapshot 2026-10, downloaded by Scott to `data/history_raw/2026-10/` (Last-Modified 2026-11-04 20:19-21:28 GMT, `LAST_MODIFIED.txt`). This answers blocker 1 of STATUS.md.

### Filter (`python -m etl.history_slim <file>`)

Local cut to the 12 slim columns, modeled on `ingest/vps/filter_history.py`: keep `event_entity = 'revision'`, stop on any row without 78 fields, only an empty field becomes null, write `.tmp` then rename, refuse `data/history/` and any existing output. Tests: `tests_lake/test_history_slim.py`, 3 passed. Attempt 1 wrote correct files but failed on the stats line (a relative path); the three outputs were deleted and attempt 2 ran clean.

| Month file | bz2 size | Rows in (page / revision / user) | Revision rows out | Slim Parquet | Seconds |
| --- | --- | --- | --- | --- | --- |
| 2026-10.enwiki.2026-09.tsv.bz2 | 557,770,750 | 6,369,591 (646,922 / 5,266,819 / 455,850) | 5,266,819 | 102,193,721 B | 39.8 |
| 2026-10.enwiki.2026-10.tsv.bz2 | 573,546,947 | 6,560,727 (720,361 / 5,344,733 / 495,633) | 5,344,733 | 103,567,804 B | 40.8 |
| 2026-10.enwiki.2026-11.tsv.bz2 | 1,301,790 | 16,131 (1,234 / 14,028 / 869) | 14,028 | 265,564 B | 0.1 |

No row had other than 78 fields. The September file of snapshot 2026-10 holds 5,266,819 revisions, 24 fewer than the same month in snapshot 2026-09 (5,266,843).

### Bronze and Silver (`python -m etl.history bronze --snapshot 2026-10`, then `silver --snapshot 2026-10`)

`bronze/history_slim` v12-v34: 3 files appended (5,266,819 + 5,344,733 + 14,028 rows; each file's row count equals its highest source_row), 8 s. `silver/history_slim` v2: 10,625,580 typed rows in partition `snapshot = 2026-10`, 20 s.

### Gold (`python -m etl.gold_run --as-of 2026-11-13T23:59:59.999999Z --snapshot 2026-10 --steps ddl,dims,labels,label_change,recon,marts`, 68 s)

| Table | Version | Change |
| --- | --- | --- |
| gold/dim_snapshot | v3 | column `snapshot_published_at` added (v2), row 2026-10 inserted: cutoff 2026-11-01 01:30:05 (newest revision of the 2026-11 file), published 2026-11-04 21:28:39 UTC, 10,625,580 revisions. Row 2026-09: cutoff 2026-10-01 01:38:27, published unknown |
| gold/fact_revert_label | v2 | ONE MERGE commit, 10.5 s: 5,358,769 revisions inserted, 40,721 labels updated (10,625,612 rows) |
| gold/mart_label_change | v1 | 40,721 rows from the change feed of v2 |
| gold/mart_reconciliation | v1 | live cohort vs 2026-10, 5 classes |
| gold/recon_mismatch | v1 | 391 rows (stream_only + dump_only + not_in_dump) |
| gold/mart_el_curve, mart_el_by_burst | v3 | new series: live cohort with dump labels |

A re-run of either snapshot load (`--snapshot 2026-09` and `--snapshot 2026-10`, `--steps dims,labels,label_change`) wrote no commit in any table. `python -m etl.gold_checks`: 33 of 33 passed (the 30 earlier checks plus delta-rs read-back of the 3 new marts).

### Phase 5 checks (`python -m etl.snapshot_checks`, output `data/lake/_runs/snapshot_checks.json`)

| Check | Expected | Got |
| --- | --- | --- |
| History cohort at the 2026-09 load (fact_revert_label v1): reverted / within 20 d / within 4 d | 19,858 / 19,700 / 17,646 | 19,858 / 19,700 / 17,646 |
| History cohort at the 2026-10 load (v2): reverted / within 20 d / within 4 d | (new) | 20,925 / 19,695 / 17,641 |
| Change feed of v2: update pre-images = post-images = mart_label_change rows | equal | 40,721 = 40,721 = 40,721 |
| Label changes by class (all namespaces) | (new) | became_reverted 40,683; became_unreverted 36; reverter or time changed 2 |
| Label changes among history-cohort revisions | (new) | became_reverted 1,072; became_unreverted 5; other 1 |
| Live revisions with less than 4 days before the 2026-10 cutoff | report | 0 of 279,466 (live_ext: 1,560,837 of 2,397,738, so live_ext is not reconciled) |
| EC HW2 cross-check: `late_reverts` class exact (published 2,970) shown as became_reverted | high share | 2,967 of 2,970 (99.9%); method_unknown 1,122 of 1,182; inexact_undo 2 of 198 (an inexact undo is not an identity revert in the dump) |

Reconciliation of the live cohort (Oct 20-22, stream label = a covering exact revert within 4 days, seen in the stream) with the 2026-10 dump label (identity-reverted within 4 days), `gold/mart_reconciliation` v1, label version 2:

| Class | Revisions | Share |
| --- | --- | --- |
| both_reverted | 17,752 | 6.352% |
| dump_only | 325 | 0.116% |
| neither | 261,323 | 93.508% |
| not_in_dump | 0 | 0.000% |
| stream_only | 66 | 0.024% |

Agreement 279,075 of 279,466 = 99.86%. Of the dump's 18,077 reverts the stream found 98.2%; of the stream's 17,818 the dump confirms 99.6%. Median time to revert in the dump: 106,870 s for the dump-only cases; the stream-only cases have a median stream T of 929 s and, where the dump reverts them later, a median dump T of 431,291 s (beyond 4 days).

E(L) of the live cohort with the two label sources, `gold/mart_el_curve` v3, all editors:

| Wait | Stream: known of 17,818 | Stream E(L) | 2026-10 dump: known of 18,077 | Dump E(L) |
| --- | --- | --- | --- | --- |
| 0 | 0 | 1.0000 | 0 | 1.0000 |
| 1 min | 3,986 | 0.7763 | 4,186 | 0.7684 |
| 5 min | 6,958 | 0.6095 | 6,994 | 0.6131 |
| 15 min | 8,398 | 0.5287 | 8,427 | 0.5338 |
| 1 h | 10,326 | 0.4205 | 10,365 | 0.4266 |
| 6 h | 13,405 | 0.2477 | 13,470 | 0.2549 |
| 1 d | 15,936 | 0.1056 | 16,028 | 0.1133 |
| 2 d | 16,699 | 0.0628 | 16,843 | 0.0683 |
| 4 d | 17,818 | 0.0000 | 18,077 | 0.0000 |

The dump series uses T only (no stream delay K): it is when the reverting edit was saved, not when a subscriber could know it.

### Time travel on the snapshot axis (restored `etl/sql/80_time_travel_then_and_now.sql`)

Command: `python -m etl.time_travel` (output `data/lake/_runs/time_travel.json`; it also re-runs the as_of demo, now `etl/sql/81_time_travel_as_of.sql`, with unchanged results). fact_revert_label versions found by commit metadata `snapshot`: {'2026-09': 1, '2026-10': 2}.

| Snapshot loaded | fact_revert_label version | History-cohort revisions reverted as known then | Reverted now |
| --- | --- | --- | --- |
| 2026-09 | v1 | 19,858 | 20,925 |
| 2026-10 | v2 | 20,925 | 20,925 |

The "then" value at the 2026-09 load is 19,858, as the plan requires. The second snapshot adds 1,067 reverted history-cohort revisions (reverts made after the 2026-09 cutoff), while the within-4-day count barely moves (17,646 to 17,641: 5 labels became unreverted).

### End-to-end rebuild with the second snapshot (2026-11-15 10:51-11:07 UTC)

Command: `SKIP_EXTRAS=1 bash etl/build_all.sh data/lake_e2e` (log `data/logs/lake/build_all_e2e2.log`), a new empty lake folder; the filter step was skipped because the slim files existed. 926 s, exit 0. Against the main lake: Phase 5 checks equal value for value (2 passed, 0 failed, 15 checks), Gold checks 33 of 33 at Nov 13, E(L) curves identical, both time-travel axes identical, H1/H3/H4 identical. The folder was deleted afterwards.

## Loop 2 (2026-11-15 12:20-13:00 UTC): results.json, fallback notebooks, export fix

### results.json and the number check

- `python scripts/make_results.py` collects every reportable number from `data/lake/_runs/*.json`, the Gold and Silver tables, the export manifest, the build logs, the config constants and a pytest run (49 passed) into `docs/final/results.json`, stamped with the commit hash.
- `python scripts/render_report.py` fills `docs/final/report_draft.template.md` into `docs/final/report_draft.md`.
- `python scripts/check_numbers.py`: commit stamp ok; fresh collection equal; draft equals the rendered template; every number token in the draft is a fact. Last line: `ZERO MISMATCHES`.
- `python scripts/check_evidence.py`: see the end of this section.

Derived totals that the draft uses (sums of numbers above): Bronze stream lines in all 12,328,679; Bronze History rows 15,892,423 (snapshot 2026-09 plus the three month files of 2026-10); distinct pages in `gold/dim_page` 2,253,040.

### Export fix found by the reservoir check

`notebooks/fallback/moments_reservoir.ipynb` compares the editor-kind mix of the not-reverted sample in `data/exports/lsh_edits.parquet` with the population of not-reverted `live_ext` edits (2,284,801) and with a one-pass reservoir sample of the same size (112,937).
- First run (12:42 UTC, export as built earlier): the export sample was off by up to 2.05 points (bots 28.04% against 30.09% in the population; registered 64.15% against 62.36%); the reservoir by 0.08.
- Cause: `etl/exports.py` drew the sample with `sample(fraction).limit(n)`, which cuts the last sampled rows in file order (the latest edits).
- Fix: `ORDER BY xxhash64(rev_id, seed) LIMIT n` (uniform, exact size). `python -m etl.exports` re-run at 12:46 UTC: only `lsh_edits.parquet` and `lsh_edits.csv` changed (same 261,166 rows; the label-0 rows differ). The earlier manifest is kept in `data/logs/lake/exports_manifest_before_uniform_fix.json`.
- After the fix: export sample within 0.1 points, reservoir within 0.08. No number of RESULTS.md above changes (it reported only the row counts of the export).

### Fallback notebooks (`python notebooks/fallback/make_fallback.py`; built by Claude for Scott; teammate work wins)

All facts below are in `data/lake/_runs/fallback_lsh.json`, `fallback_privacy.json`, `fallback_moments.json` and in `results.json`.

| Fact | Value |
| --- | --- |
| `lsh.distinct_texts` | 49,140 |
| `lsh.edits_in_export` | 261,166 |
| `lsh.edits_kept` | 91,092 |
| `lsh.edits_sharing_exact_text` | 45,315 |
| `lsh.exact_join_seconds` | 190.8 |
| `lsh.full_join_seconds` | 104.2 |
| `lsh.groups` | 1,419 |
| `lsh.hash_tables` | 5 |
| `lsh.jaccard_min` | 0.6 |
| `lsh.labels.all.pairs` | 80 |
| `lsh.labels.all.precision_hi` | 98.7 |
| `lsh.labels.all.precision_lo` | 89.5 |
| `lsh.labels.all.precision_pct` | 96.2 |
| `lsh.labels.all.same_pattern` | 77 |
| `lsh.labels.by_band.pairs` | 40 |
| `lsh.labels.by_band.precision_hi` | 100.0 |
| `lsh.labels.by_band.precision_lo` | 91.2 |
| `lsh.labels.by_band.precision_pct` | 100.0 |
| `lsh.labels.by_band.same_pattern` | 40 |
| `lsh.labels.by_group.pairs` | 40 |
| `lsh.labels.by_group.precision_hi` | 97.4 |
| `lsh.labels.by_group.precision_lo` | 80.1 |
| `lsh.labels.by_group.precision_pct` | 92.5 |
| `lsh.labels.by_group.same_pattern` | 37 |
| `lsh.labels.by_person` | 0 |
| `lsh.labels.groups_sampled` | 40 |
| `lsh.largest_group_texts` | 1,186 |
| `lsh.min_chars` | 20 |
| `lsh.min_words` | 4 |
| `lsh.near_dup_pairs` | 420,629 |
| `lsh.not_reverted.edits` | 64,446 |
| `lsh.not_reverted.exact_dup_pct` | 63.02 |
| `lsh.not_reverted.near_dup_pct` | 64.45 |
| `lsh.not_reverted.reuses_pct` | 72.56 |
| `lsh.recall_pct.tables1` | 89.32 |
| `lsh.recall_pct.tables20` | 96.16 |
| `lsh.recall_pct.tables5` | 96.11 |
| `lsh.reverted.edits` | 26,646 |
| `lsh.reverted.exact_dup_pct` | 17.63 |
| `lsh.reverted.near_dup_pct` | 14.99 |
| `lsh.reverted.reuses_pct` | 24.63 |
| `lsh.sample_exact_pairs` | 2,162 |
| `lsh.sample_pairs_compared` | 7,998,000 |
| `lsh.sample_texts` | 4,000 |
| `lsh.seconds.tables1` | 1.0 |
| `lsh.seconds.tables20` | 3.6 |
| `lsh.seconds.tables5` | 0.8 |
| `lsh.shingle_k` | 5 |
| `lsh.texts_with_near_dup` | 9,988 |
| `moments.ams.v100.mean_abs_error_pct` | 63.33 |
| `moments.ams.v100.mean_error_pct` | -60.03 |
| `moments.ams.v100.variables` | 100 |
| `moments.ams.v100.worst_abs_error_pct` | 84.49 |
| `moments.ams.v1000.mean_abs_error_pct` | 20.36 |
| `moments.ams.v1000.mean_error_pct` | -8.85 |
| `moments.ams.v1000.variables` | 1,000 |
| `moments.ams.v1000.worst_abs_error_pct` | 47.12 |
| `moments.ams.v10000.mean_abs_error_pct` | 4.59 |
| `moments.ams.v10000.mean_error_pct` | 0.0 |
| `moments.ams.v10000.variables` | 10,000 |
| `moments.ams.v10000.worst_abs_error_pct` | 13.16 |
| `moments.ams.v300.mean_abs_error_pct` | 37.8 |
| `moments.ams.v300.mean_error_pct` | -32.93 |
| `moments.ams.v300.variables` | 300 |
| `moments.ams.v300.worst_abs_error_pct` | 72.63 |
| `moments.ams.v3000.mean_abs_error_pct` | 11.36 |
| `moments.ams.v3000.mean_error_pct` | -5.45 |
| `moments.ams.v3000.variables` | 3,000 |
| `moments.ams.v3000.worst_abs_error_pct` | 26.26 |
| `moments.edit_events` | 4,209,083 |
| `moments.export_kind_max_dev_points` | 0.1 |
| `moments.f0` | 1,889,644 |
| `moments.f1` | 4,209,083 |
| `moments.f2` | 249,630,183 |
| `moments.groups` | 10 |
| `moments.max_edits_one_page` | 4,265 |
| `moments.neg_population` | 2,284,801 |
| `moments.neg_sample_size` | 112,937 |
| `moments.reservoir.k1000.binomial_se_points` | 0.623 |
| `moments.reservoir.k1000.exact_share_pct` | 4.046 |
| `moments.reservoir.k1000.mean_estimate_pct` | 4.104 |
| `moments.reservoir.k1000.mean_relative_position` | 0.5 |
| `moments.reservoir.k1000.sample_size` | 1,000 |
| `moments.reservoir.k1000.sd_of_estimates_points` | 0.693 |
| `moments.reservoir.k1000.within_2_se_pct` | 90.5 |
| `moments.reservoir.k10000.binomial_se_points` | 0.197 |
| `moments.reservoir.k10000.exact_share_pct` | 4.046 |
| `moments.reservoir.k10000.mean_estimate_pct` | 4.063 |
| `moments.reservoir.k10000.mean_relative_position` | 0.5 |
| `moments.reservoir.k10000.sample_size` | 10,000 |
| `moments.reservoir.k10000.sd_of_estimates_points` | 0.206 |
| `moments.reservoir.k10000.within_2_se_pct` | 94.5 |
| `moments.reservoir.k100000.binomial_se_points` | 0.062 |
| `moments.reservoir.k100000.exact_share_pct` | 4.046 |
| `moments.reservoir.k100000.mean_estimate_pct` | 4.048 |
| `moments.reservoir.k100000.mean_relative_position` | 0.5 |
| `moments.reservoir.k100000.sample_size` | 100,000 |
| `moments.reservoir.k100000.sd_of_estimates_points` | 0.064 |
| `moments.reservoir.k100000.within_2_se_pct` | 96.0 |
| `moments.reservoir_kind_max_dev_points` | 0.08 |
| `moments.reservoir_runs` | 200 |
| `moments.seeds` | 30 |
| `privacy.eps_high` | 1.0 |
| `privacy.eps_low` | 0.1 |
| `privacy.eps_mid` | 0.5 |
| `privacy.epsilons` | 3 |
| `privacy.grid.k10.rows_below` | 209 |
| `privacy.grid.k10.rows_below_pct` | 11.15 |
| `privacy.grid.k2.rows_below` | 7 |
| `privacy.grid.k2.rows_below_pct` | 0.37 |
| `privacy.grid.k20.rows_below` | 627 |
| `privacy.grid.k20.rows_below_pct` | 33.44 |
| `privacy.grid.k5.edits_kept_pct` | 99.168 |
| `privacy.grid.k5.rows_below` | 74 |
| `privacy.grid.k5.rows_below_pct` | 3.95 |
| `privacy.grid.k5.rows_kept_pct` | 96.05 |
| `privacy.grid.min_editors` | 1 |
| `privacy.grid.rows` | 1,875 |
| `privacy.grid.two_diverse_pct` | 92.69 |
| `privacy.k` | 5 |
| `privacy.k_small` | 2 |
| `privacy.l` | 2 |
| `privacy.laplace.history.dump.all.mae.eps_high` | 9e-05 |
| `privacy.laplace.history.dump.all.mae.eps_low` | 0.00094 |
| `privacy.laplace.history.dump.all.mae.eps_mid` | 0.00019 |
| `privacy.laplace.history.dump.all.n` | 17,646 |
| `privacy.laplace.live.stream.all.mae.eps_high` | 9e-05 |
| `privacy.laplace.live.stream.all.mae.eps_low` | 0.00093 |
| `privacy.laplace.live.stream.all.mae.eps_mid` | 0.00018 |
| `privacy.laplace.live.stream.all.n` | 17,818 |
| `privacy.laplace.live.stream.bot.mae.eps_high` | 0.01204 |
| `privacy.laplace.live.stream.bot.mae.eps_low` | 0.15468 |
| `privacy.laplace.live.stream.bot.mae.eps_mid` | 0.02346 |
| `privacy.laplace.live.stream.bot.n` | 141 |
| `privacy.laplace.live.stream.registered.mae.eps_high` | 0.0002 |
| `privacy.laplace.live.stream.registered.mae.eps_low` | 0.002 |
| `privacy.laplace.live.stream.registered.mae.eps_mid` | 0.00041 |
| `privacy.laplace.live.stream.registered.n` | 7,905 |
| `privacy.laplace.live.stream.temporary.mae.eps_high` | 0.00017 |
| `privacy.laplace.live.stream.temporary.mae.eps_low` | 0.00168 |
| `privacy.laplace.live.stream.temporary.mae.eps_mid` | 0.00035 |
| `privacy.laplace.live.stream.temporary.n` | 9,772 |
| `privacy.laplace.live_ext.stream.all.mae.eps_high` | 1e-05 |
| `privacy.laplace.live_ext.stream.all.mae.eps_low` | 0.00014 |
| `privacy.laplace.live_ext.stream.all.mae.eps_mid` | 3e-05 |
| `privacy.laplace.live_ext.stream.all.n` | 112,937 |
| `privacy.laplace.sensitivity` | 1 |
| `privacy.laplace.small_groups` | 1 |
| `privacy.laplace.trials` | 1,000 |
| `privacy.page.all_reverted_pct` | 0.162 |
| `privacy.page.all_reverted_rows` | 2,526 |
| `privacy.page.all_reverted_single_editor` | 2,170 |
| `privacy.page.k10.edits_below_pct` | 94.02 |
| `privacy.page.k10.rows_below_pct` | 99.75 |
| `privacy.page.k2.edits_below_pct` | 52.56 |
| `privacy.page.k2.rows_below_pct` | 81.63 |
| `privacy.page.k20.edits_below_pct` | 97.18 |
| `privacy.page.k20.rows_below_pct` | 99.95 |
| `privacy.page.k5.edits_below_pct` | 85.33 |
| `privacy.page.k5.rows_below_pct` | 98.42 |
| `privacy.page.rows` | 1,559,483 |
| `privacy.page.single_editor_pct` | 81.63 |
| `privacy.page.single_editor_rows` | 1,273,073 |
| `privacy.page.two_diverse_pct` | 4.8 |
| `privacy.suppress.history.ruleA.bias_points` | 6.52 |
| `privacy.suppress.history.ruleA.edits_kept_pct` | 7.17 |
| `privacy.suppress.history.ruleA.released_revert_rate_pct` | 12.5 |
| `privacy.suppress.history.ruleA.reverts_kept_pct` | 14.99 |
| `privacy.suppress.history.ruleA.rows_kept_pct` | 0.74 |
| `privacy.suppress.history.ruleA.true_revert_rate_pct` | 5.98 |
| `privacy.suppress.history.ruleB.bias_points` | 6.43 |
| `privacy.suppress.history.ruleB.edits_kept_pct` | 7.17 |
| `privacy.suppress.history.ruleB.released_revert_rate_pct` | 12.41 |
| `privacy.suppress.history.ruleB.reverts_kept_pct` | 14.86 |
| `privacy.suppress.history.ruleB.rows_kept_pct` | 0.74 |
| `privacy.suppress.history.ruleB.true_revert_rate_pct` | 5.98 |
| `privacy.suppress.history.ruleC.bias_points` | 15.98 |
| `privacy.suppress.history.ruleC.edits_kept_pct` | 4.05 |
| `privacy.suppress.history.ruleC.released_revert_rate_pct` | 21.97 |
| `privacy.suppress.history.ruleC.reverts_kept_pct` | 14.86 |
| `privacy.suppress.history.ruleC.rows_kept_pct` | 0.4 |
| `privacy.suppress.history.ruleC.true_revert_rate_pct` | 5.98 |
| `privacy.suppress.live.ruleA.bias_points` | 9.19 |
| `privacy.suppress.live.ruleA.edits_kept_pct` | 7.38 |
| `privacy.suppress.live.ruleA.released_revert_rate_pct` | 15.57 |
| `privacy.suppress.live.ruleA.reverts_kept_pct` | 18.03 |
| `privacy.suppress.live.ruleA.rows_kept_pct` | 0.73 |
| `privacy.suppress.live.ruleA.true_revert_rate_pct` | 6.38 |
| `privacy.suppress.live.ruleB.bias_points` | 8.76 |
| `privacy.suppress.live.ruleB.edits_kept_pct` | 7.35 |
| `privacy.suppress.live.ruleB.released_revert_rate_pct` | 15.14 |
| `privacy.suppress.live.ruleB.reverts_kept_pct` | 17.44 |
| `privacy.suppress.live.ruleB.rows_kept_pct` | 0.73 |
| `privacy.suppress.live.ruleB.true_revert_rate_pct` | 6.38 |
| `privacy.suppress.live.ruleC.bias_points` | 17.26 |
| `privacy.suppress.live.ruleC.edits_kept_pct` | 4.7 |
| `privacy.suppress.live.ruleC.released_revert_rate_pct` | 23.64 |
| `privacy.suppress.live.ruleC.reverts_kept_pct` | 17.44 |
| `privacy.suppress.live.ruleC.rows_kept_pct` | 0.44 |
| `privacy.suppress.live.ruleC.true_revert_rate_pct` | 6.38 |
| `privacy.suppress.live_ext.ruleA.bias_points` | 7.34 |
| `privacy.suppress.live_ext.ruleA.edits_kept_pct` | 16.44 |
| `privacy.suppress.live_ext.ruleA.released_revert_rate_pct` | 12.05 |
| `privacy.suppress.live_ext.ruleA.reverts_kept_pct` | 42.08 |
| `privacy.suppress.live_ext.ruleA.rows_kept_pct` | 1.8 |
| `privacy.suppress.live_ext.ruleA.true_revert_rate_pct` | 4.71 |
| `privacy.suppress.live_ext.ruleB.bias_points` | 7.34 |
| `privacy.suppress.live_ext.ruleB.edits_kept_pct` | 16.44 |
| `privacy.suppress.live_ext.ruleB.released_revert_rate_pct` | 12.05 |
| `privacy.suppress.live_ext.ruleB.reverts_kept_pct` | 42.05 |
| `privacy.suppress.live_ext.ruleB.rows_kept_pct` | 1.8 |
| `privacy.suppress.live_ext.ruleB.true_revert_rate_pct` | 4.71 |
| `privacy.suppress.live_ext.ruleC.bias_points` | 14.21 |
| `privacy.suppress.live_ext.ruleC.edits_kept_pct` | 10.47 |
| `privacy.suppress.live_ext.ruleC.released_revert_rate_pct` | 18.92 |
| `privacy.suppress.live_ext.ruleC.reverts_kept_pct` | 42.05 |
| `privacy.suppress.live_ext.ruleC.rows_kept_pct` | 1.04 |
| `privacy.suppress.live_ext.ruleC.true_revert_rate_pct` | 4.71 |

### Bundle (`bash scripts/make_bundle.sh`, 2026-11-15 13:06 UTC)

Built in `dist/` (git-ignored) from a fresh `git clone` of the local repository, so only committed files go in. Output of the run:

    bundle: <repo>/dist
    files in dist: 36   total: 8236 KB
    largest file in dist: <repo>/dist/truthlag_repo_a9af00c.zip (6630 KB)
    code zip: truthlag_code_a9af00c.zip (702 KB, 136 files); tests from the unzipped copy: 49 passed in 4.66s
    check_numbers:  ZERO MISMATCHES
    check_evidence: 14 rubric lines, 0 failing
    commit: a9af00c7a69be5314b40f31728f63f17b08d374c

Head of `dist/MANIFEST.txt`:

    TruthLag submission bundle
    commit:  a9af00c7a69be5314b40f31728f63f17b08d374c
    branch:  final-lake
    built:   2026-11-15T13:02:49Z from a fresh clone of the local repository
    working tree of the source repository: 0 uncommitted path(s) (not in the bundle)
    results.json commit stamp: 84624f44d0dc0e9f0c2491bce9ea70d6baa96671
    check_numbers (in the clone, without the lake):  ZERO MISMATCHES
    check_evidence (in the clone, data outputs not present):  14 rubric lines, 0 failing
    
    tests run from the unzipped code zip:  49 passed in 4.66s
    
    code zip (upload this): truthlag_code_a9af00c.zip  files: 136  size: 702 KB
    largest file inside the code zip: notebooks/final/02_gold_star_schema.ipynb (132 KB)
    repo zip (everything tracked, with the EC HW2 material): truthlag_repo_a9af00c.zip  files: 396  size: 6630 KB
    largest file inside the repo zip: ec-hw2/notebooks/01_data.ipynb (688 KB)
    tracked files left out of both zips (over 1200 KB):
      ec-hw2/report/REPORT_SKELETON.docx	3253 KB

`dist/` holds the code zip, the repo zip, the 11 executed notebooks with `.py` copies, the pair labels, 3 figures, `results.json`, `report_draft.md`, `RUBRIC_EVIDENCE.md`, `GENAI_LOG.md`, `GATE_MON.md` and `MANIFEST.txt` (every file with size and SHA-256). After this entry was committed, `dist/` was rebuilt once more so that it matches the last commit; its `MANIFEST.txt` names that commit.

`python scripts/check_evidence.py` on the Mac after the bundle: 14 rubric lines, 0 failing.

<!-- teammates:begin (written by scripts/make_results.py; do not edit by hand) -->

## Teammates' analyses, collected into results.json (2026-11-17T08:59:46Z)

`python scripts/make_results.py` reads these numbers from files the teammates committed. Nothing is recomputed and no lake number is replaced: the keys are `wanru.*` and `zhenni.*`. Sources: `ec-hw2/results/cypher_*.csv`, the stored outputs of `notebooks/neo4j_history_edit_wars_wanru.ipynb` and `notebooks/lsh_minhash_wanru.ipynb`, and `notebooks/privacy_zhenni/outputs/`.

### Wanru: Neo4j graph of the history cohort (20-day follow-up, as in EC HW2)

| What | Value | Same number recomputed from the lake's Silver tables |
| --- | --- | --- |
| Editor nodes | 37,546 | 37,546 |
| Page nodes | 165,415 | 165,415 |
| EDITED relationships | 295,013 | 295,013 |
| REVERTED relationships | 13,269 | 13,269 |
| Mutual-revert pairs | 462 | 462 |
| Pages with a mutual-revert pair | 397 | 397 |
| Editors in mutual-revert pairs | 631 | 631 |

| What | Value |
| --- | --- |
| Contested pages | 126 |
| Mutual-revert pairs with a bot | 25 |
| Louvain communities | 28,615 |
| Louvain modularity | 0.9142 |
| Communities with two or more editors | 1,191 |
| Communities of one editor | 27,424 |
| Largest community: editors | 564 |
| Largest community: revert actions | 661 |
| Largest community: bots | 1 |
| Largest community: share of REVERTED relationships that touch its top reverter, % | 69.1 |
| Page with the most warring editors: warring editors | 10 |
| Same page: mutual pairs | 9 |
| Same page: revert actions | 34 |
| Same page: edits | 39 |

### Wanru: MinHash LSH on edit comments

| What | Value |
| --- | --- |
| Edits in the export | 261,166 |
| Edits kept | 91,092 |
| Distinct cleaned texts | 49,140 |
| Texts in the exact-join sample | 4,000 |
| Pairs compared in the exact join | 7,998,000 |
| True near-duplicate pairs in the sample | 2,162 |
| Exact join, seconds | 190.8 |
| Near-duplicate pairs on all texts | 420,629 |
| Texts with a near-duplicate | 9,988 |
| Groups | 1,419 |
| Largest group, texts | 1,186 |
| Reverted edits that reuse a summary, % | 24.63 |
| Not-reverted edits that reuse a summary, % | 72.56 |
| Labeled pairs | 80 |
| Labeled pairs with the same edit pattern | 77 |
| Precision, % | 96.2 |
| Precision, Wilson 95% low | 89.5 |
| Precision, Wilson 95% high | 98.7 |
| By similarity band: same pattern | 40 |
| By group: same pattern | 37 |

| Hash tables | Pairs returned | True pairs found | Recall, % | Seconds |
| --- | --- | --- | --- | --- |
| 1 | 1,937 | 1,931 | 89.32 | 1.0 |
| 3 | 2,077 | 2,069 | 95.7 | 0.7 |
| 5 | 2,086 | 2,078 | 96.11 | 0.8 |
| 10 | 2,087 | 2,079 | 96.16 | 1.3 |
| 20 | 2,087 | 2,079 | 96.16 | 3.6 |

### Zhenni: k-anonymity, l-diversity, suppression

| Table | Rows | k | Rows below k | Rows below k, % | Edits in those rows, % | Edits kept if those rows are dropped, % (100 minus the column before) |
| --- | --- | --- | --- | --- | --- | --- |
| kind x date x hour | 1,875 | 2 | 7 | 0.37 | 0.01 | 99.99 |
| kind x date x hour | 1,875 | 5 | 74 | 3.95 | 0.83 | 99.17 |
| kind x date x hour | 1,875 | 10 | 209 | 11.15 | 3.04 | 96.96 |
| kind x date x hour | 1,875 | 20 | 627 | 33.44 | 25.4 | 74.6 |
| page summary | 1,559,483 | 2 | 1,273,073 | 81.63 | 52.56 | 47.44 |
| page summary | 1,559,483 | 5 | 1,534,855 | 98.42 | 85.33 | 14.67 |
| page summary | 1,559,483 | 10 | 1,555,567 | 99.75 | 94.02 | 5.98 |
| page summary | 1,559,483 | 20 | 1,558,722 | 99.95 | 97.18 | 2.82 |

| Table | Rows with both labels, % | Rows with only reverted edits | Those, % | Rows with no reverted edit, % | Only-reverted rows from a single editor |
| --- | --- | --- | --- | --- | --- |
| kind x date x hour | 92.69 | 3 | 0.16 | 7.15 | 3 |
| page summary | 4.8 | 2,526 | 0.162 | 95.04 | 2,170 |

| Cohort | Rule | Rows kept, % | Edits kept, % | Reverts kept, % | True revert rate, % | Released revert rate, % | Bias, points |
| --- | --- | --- | --- | --- | --- | --- | --- |
| history | A | 0.74 | 7.17 | 14.99 | 5.98 | 12.5 | 6.52 |
| history | B | 0.74 | 7.17 | 14.86 | 5.98 | 12.41 | 6.43 |
| history | C | 0.4 | 4.05 | 14.86 | 5.98 | 21.97 | 15.98 |
| live | A | 0.73 | 7.38 | 18.03 | 6.38 | 15.57 | 9.19 |
| live | B | 0.73 | 7.35 | 17.44 | 6.38 | 15.14 | 8.76 |
| live | C | 0.44 | 4.7 | 17.44 | 6.38 | 23.64 | 17.26 |
| live_ext | A | 1.8 | 16.44 | 42.08 | 4.71 | 12.05 | 7.34 |
| live_ext | B | 1.8 | 16.44 | 42.05 | 4.71 | 12.05 | 7.34 |
| live_ext | C | 1.04 | 10.47 | 42.05 | 4.71 | 18.92 | 14.21 |

### Zhenni: Laplace noise on the E(L) counts (1,000 trials, seed 226)

Mean absolute error of E(L) over seven waits, shown to six decimals.

| Cohort | Label source | Editor kind | Eventual reverts | MAE at epsilon 0.1 | MAE at epsilon 0.5 | MAE at epsilon 1.0 |
| --- | --- | --- | --- | --- | --- | --- |
| live_ext | stream | all | 112,937 | 0.000145 | 0.000029 | 0.000015 |
| live_ext | stream | temporary | 59,675 | 0.000282 | 0.000057 | 0.000027 |
| live_ext | stream | registered | 51,302 | 0.000318 | 0.000061 | 0.000032 |
| live | dump | all | 18,077 | 0.000896 | 0.000184 | 0.000090 |
| live | stream | all | 17,818 | 0.000927 | 0.000182 | 0.000093 |
| history | dump | all | 17,646 | 0.000942 | 0.000186 | 0.000092 |
| live | dump | temporary | 9,881 | 0.001693 | 0.000334 | 0.000167 |
| history | dump | temporary | 9,863 | 0.001694 | 0.000335 | 0.000169 |
| live | stream | temporary | 9,772 | 0.001676 | 0.000354 | 0.000171 |
| live | dump | registered | 8,056 | 0.001996 | 0.000419 | 0.000203 |
| live | stream | registered | 7,905 | 0.002004 | 0.000411 | 0.000203 |
| history | dump | registered | 7,623 | 0.002061 | 0.000418 | 0.000204 |
| live_ext | stream | bot | 1,960 | 0.008404 | 0.001712 | 0.000866 |
| history | dump | bot | 157 | 0.171987 | 0.021101 | 0.010557 |
| live | stream | bot | 141 | 0.154684 | 0.023457 | 0.012041 |
| live | dump | bot | 140 | 0.204427 | 0.024604 | 0.011546 |
| history | dump | unknown | 3 | 11.494742 | 2.243155 | 0.997243 |

### Teammate numbers against the lake and the fallback notebooks

163 teammate numbers have a lake or fallback number that measures the same thing (`lsh.*`, `privacy.*`, `el.*.n_eventual`, `lakecheck.graph.*`). Compared at the precision of the less precise of the two: 159 agree, 4 disagree.

| Teammate fact | Value | Lake or fallback fact | Value |
| --- | --- | --- | --- |
| `zhenni.privacy.laplace.history.dump.all.mae.eps1_0` | 9.20599809702619e-05 | `privacy.laplace.history.dump.all.mae.eps_high` | 9e-05 |
| `zhenni.privacy.laplace.live.stream.all.mae.eps1_0` | 9.320430484493767e-05 | `privacy.laplace.live.stream.all.mae.eps_high` | 9e-05 |
| `zhenni.privacy.laplace.live_ext.stream.all.mae.eps0_5` | 2.946601208092208e-05 | `privacy.laplace.live_ext.stream.all.mae.eps_mid` | 3e-05 |
| `zhenni.privacy.laplace.live_ext.stream.all.mae.eps1_0` | 1.455512280759135e-05 | `privacy.laplace.live_ext.stream.all.mae.eps_high` | 1e-05 |

Automated tests at this collection: 51 passed.

<!-- teammates:end -->
