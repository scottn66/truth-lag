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
