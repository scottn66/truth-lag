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
