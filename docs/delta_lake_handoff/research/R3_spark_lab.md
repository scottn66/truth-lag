# R3 — PySpark and delta-spark lab: what works

> **Research report, not yet reviewed.** Output of the research agent `spark_lab` in a cloud Claude Code session on Nov 13, 2026, as returned. Evidence labels: RAN = executed in that session on made-up data; READ = read at the cited file and line; DERIVED = arithmetic on values that were read; UNVERIFIED = not checked. Paths that start with /tmp/claude-0/ or /home/user/ are on that session's machine and cannot be opened from elsewhere. Repository state read: scottn66/truth-lag at 8e28012.

## Summary

PySpark + delta-spark works on this machine, and every building block S1-S11 was executed with real code (RAN) in /tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/spark_lab. Nothing was written to /home/user/truth-lag (git status --porcelain is empty; no spark-warehouse, metastore_db or derby.log there).

Headline facts:
- delta-spark==4.4.1 pulls pyspark 4.2.0, not 4.3.0 (its metadata caps pyspark at <=4.2.0, and Maven has no delta-spark_4.3_2.13:4.4.1). Scala 2.13.18, Java 21.0.12.1.
- Maven Central is reachable through the proxy with the pre-set JAVA_TOOL_OPTIONS only; no Ivy settings needed. First start 28.8 s, later starts 5 s. A no-network start with two local jars in spark.jars also works (3.7 s).
- All of these work in Spark: generated-column partitioning, appendOnly, CDF, CHECK (via ALTER or TBLPROPERTIES, not inline), liquid clustering, txnAppId/txnVersion idempotent appends, file-source streaming with availableNow, foreachBatch insert-only MERGE (exactly-once across a simulated crash), SCD Type 2 MERGE, label upsert with CDF, time travel, RESTORE, OPTIMIZE/ZORDER, VACUUM, deletion vectors, VARIANT.
- Scale (local[2], spark.driver.memory=4g): 5,000,000 rows x 12 string columns written in 14.1 s (453 MB); MERGE of 300,000 updates 20.9 s (11.4 s with deletion vectors); insert-only MERGE of 300,000 rows 3.2 s; peak JVM RSS 2.8 GB.

Findings that should change the plan:
1. A gzip file still being written (no end marker) or truncated fails the whole Bronze micro-batch (safe, but blocks); with ignoreCorruptFiles=true it is read partially, marked done, and the rest is silently lost for good.
2. The generated event_date is computed in the writer's session time zone: a non-UTC session put the same instant in a different partition and a later query silently missed the row. Pin spark.sql.session.timeZone=UTC.
3. whenNotMatchedInsertAll fails when the target has a generated column the source lacks; insert-only MERGE does not dedup inside the source.
4. No-op MERGE updates do produce CDF rows; a guard predicate removes them, but on a plain table a guarded re-run still writes a commit that rewrites files. Pre-filtering the source (or deletion vectors) gives a true no-op (no commit).
5. Without in-commit timestamps the commit timestamp is the log file's mtime, so cp -r breaks TIMESTAMP AS OF; enabling delta.enableInCommitTimestamps at CREATE fixes it, but then delta-rs cannot write to the table.
6. delta-rs 1.6.6 reads every Spark table kind except deletion-vector tables through its pyarrow readers; it cannot write to liquid-clustered, in-commit-timestamp or identity-column tables, and an append with schema_mode='merge' to a VARIANT table rewrote the schema so Spark could no longer read it.
7. VACUUM takes 39 s on a tiny table in local mode unless spark.sql.sources.parallelPartitionDiscovery.parallelism is lowered (4.6 s at 2).
8. Python workers pick PATH python3 (3.13) and fail with PYTHON_VERSION_MISMATCH unless PYSPARK_PYTHON is set to the venv interpreter.

One thing I could not do: a built-in safety check refused my cleanup command, so about 1.8 GB of test tables remain in the scratch folder (tables/s10 is most of it) for a person to delete.

## Versions

All RAN unless marked.

| Item | Value |
|---|---|
| Python | 3.12.3 in a uv venv (uv 0.11.32). PATH `python3` is 3.13, which matters for workers (see Pitfalls) |
| delta-spark | 4.4.1 |
| pyspark pulled by delta-spark 4.4.1 | **4.2.0** (not 4.3.0). READ `venv/lib/python3.12/site-packages/delta_spark-4.4.1.dist-info/METADATA:24`: `Requires-Dist: pyspark<=4.2.0,>=4.0.1` |
| py4j | 0.10.9.9 |
| Scala | 2.13.18 (`scala.util.Properties.versionString`) |
| Java | OpenJDK 21.0.12.1 (Ubuntu), `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64` |
| Delta jar | `io.delta:delta-spark_4.2_2.13:4.4.1` chosen by `configure_spark_with_delta_pip` (READ `venv/lib/python3.12/site-packages/delta/pip_utils.py:88-93`), plus delta-storage, delta-kernel-api, delta-kernel-defaults, delta-kernel-unitycatalog 4.4.1 and 28 transitive jars (33 jars, 87 MB) |
| delta-rs (second venv) | deltalake 1.6.6, pyarrow 26.0.1, Python 3.12.3 |

Maven check (RAN, curl through the proxy): `delta-spark_4.0_2.13`, `delta-spark_4.1_2.13`, `delta-spark_4.2_2.13` and `delta-spark_2.13` at 4.4.1 return HTTP 200; `delta-spark_4.3_2.13:4.4.1` returns **404**. So pyspark 4.3.0 cannot be paired with delta-spark 4.4.1.

**Network.** Maven Central (repo1.maven.org) works through the proxy with the already-exported `JAVA_TOOL_OPTIONS` (`-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=38979 -Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts`). No Ivy proxy or trust-store settings were needed. Spark's second resolver is blocked but harmless: `Server access error at url https://repos.spark-packages.org/... (java.io.IOException: Unable to tunnel through proxy. Proxy returns "HTTP/1.1 403 Forbidden")` appears 34 times under `:: problems summary :: ERRORS` and the session still starts.

**SparkSession config that works here (RAN in every test):**

```python
import os, sys
os.environ['PYSPARK_PYTHON'] = sys.executable          # else PYTHON_VERSION_MISMATCH (3.13 worker vs 3.12 driver)
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
HOME = '/abs/path/outside/the/repo'
b = (SparkSession.builder.master('local[2]').appName('truthlag')
     .config('spark.sql.extensions', 'io.delta.sql.DeltaSparkSessionExtension')
     .config('spark.sql.catalog.spark_catalog', 'org.apache.spark.sql.delta.catalog.DeltaCatalog')
     .config('spark.driver.memory', '4g')                 # max heap reported: 4096 MB
     .config('spark.sql.shuffle.partitions', '4')         # 8 in the 5M-row test
     .config('spark.sql.session.timeZone', 'UTC')         # generated event_date depends on it
     .config('spark.sql.warehouse.dir', HOME + '/warehouse')
     .config('spark.driver.extraJavaOptions', f'-Dderby.system.home={HOME}/derby -Duser.timezone=UTC')
     .config('spark.local.dir', HOME + '/sparktmp')
     .config('spark.jars.ivy', HOME + '/ivy')             # keeps the Ivy cache out of ~/.ivy2
     .config('spark.ui.enabled', 'false')
     .config('spark.ui.showConsoleProgress', 'false'))
spark = configure_spark_with_delta_pip(b).getOrCreate()
spark.sparkContext.setLogLevel('ERROR')
# set at runtime in the VACUUM test: 39.0 s -> 4.6 s
spark.conf.set('spark.sql.sources.parallelPartitionDiscovery.parallelism', '2')
```

**No-network alternative (RAN, start 3.7 s):** drop `configure_spark_with_delta_pip` and set `spark.jars` to the two jars Ivy already downloaded, `<ivy>/jars/io.delta_delta-spark_4.2_2.13-4.4.1.jar,<ivy>/jars/io.delta_delta-storage-4.4.1.jar`. With only those two jars, CREATE (generated column + CDF + deletion vectors + in-commit timestamps), MERGE, DELETE, CDF read, OPTIMIZE ZORDER, time travel, DESCRIBE HISTORY, the Delta streaming source and VARIANT all worked.

**Which settings keep side files out of the working directory (RAN control runs from empty folders):**
- Default in-memory catalog, no settings: only `spark-warehouse/` appears, and only once a managed table is created. `spark.sql.warehouse.dir` moves it; the folder then stays empty. No `metastore_db` or `derby.log` is created without Hive support.
- With `enableHiveSupport()` and no settings: `derby.log`, `metastore_db`, `spark-warehouse` appear. With `spark.sql.warehouse.dir` plus `spark.driver.extraJavaOptions=-Dderby.system.home=<dir>` the folder stays empty.
- `spark.jars.ivy` moved the Ivy cache (no `~/.ivy2*` was created); `spark.local.dir` holds shuffle files; every stream had an explicit `checkpointLocation`.
- Table names: with the in-memory catalog a `CREATE TABLE name USING DELTA LOCATION` registration is lost when the session ends. With Hive support a second session saw both tables by name.

## Recommended patterns

Each block below is the code that ran successfully here (paths shortened to `{...}`).

**S1 DDL for path-based tables**

```sql
-- Bronze stream table: generated partition column + append-only. Protocol reader 1 / writer 7 [appendOnly, generatedColumns, invariants]
CREATE TABLE IF NOT EXISTS delta.`{bronze}` (
  raw STRING, source_file STRING, source_file_mtime TIMESTAMP,
  meta_id STRING, meta_dt TIMESTAMP, ingested_at TIMESTAMP,
  event_date DATE GENERATED ALWAYS AS (CAST(meta_dt AS DATE)))
USING DELTA PARTITIONED BY (event_date)
TBLPROPERTIES ('delta.appendOnly'='true');
-- retention properties accepted at CREATE, protocol unchanged:
--   'delta.logRetentionDuration'='interval 3650 days', 'delta.deletedFileRetentionDuration'='interval 30 days'

-- CDF: reader 1 / writer 7 [appendOnly, changeDataFeed, invariants]; also works via ALTER TABLE ... SET TBLPROPERTIES
CREATE TABLE delta.`{p}` (...) USING DELTA TBLPROPERTIES ('delta.enableChangeDataFeed'='true');

-- CHECK: not inline in CREATE. Either of these (reader 1 / writer 3):
ALTER TABLE delta.`{p}` ADD CONSTRAINT rev_id_positive CHECK (rev_id > 0);
CREATE TABLE delta.`{p}` (wiki_db STRING, rev_id BIGINT) USING DELTA TBLPROPERTIES ('delta.constraints.rev_pos'='rev_id > 0');

-- Liquid clustering: reader 1 / writer 7 [appendOnly, clustering, domainMetadata, invariants]; not together with PARTITIONED BY
CREATE TABLE delta.`{p}` (wiki_db STRING, rev_id BIGINT, page_id BIGINT, is_reverted BOOLEAN) USING DELTA CLUSTER BY (wiki_db, rev_id);

-- protocol check after each
DESCRIBE DETAIL delta.`{p}`;   -- minReaderVersion, minWriterVersion, tableFeatures
```

Python builder equivalents also ran: `DeltaTable.createIfNotExists(spark).location(p).addColumn('event_date', 'DATE', generatedAlwaysAs='CAST(meta_dt AS DATE)').partitionedBy('event_date').property('delta.appendOnly', 'true').execute()` (second call is a no-op, still version 0) and `.clusterBy('wiki_db', 'rev_id')`.

**S2 idempotent batch append**

```python
(df.write.format('delta').mode('append')
   .option('txnAppId', 'hist_snapshot_load')   # one appId per logical load
   .option('txnVersion', 1)                    # same or lower version for that appId = skipped, no commit
   .save(path))
```
SQL form: `spark.conf.set('spark.databricks.delta.write.txnAppId', 'sqlapp')` and `...write.txnVersion`, then `INSERT INTO`; the second identical INSERT added nothing. The confs stay set afterwards, so unset them.

**S3 files to Bronze**

```python
df = (spark.readStream.format('text')
        .option('pathGlobFilter', '*.ndjson.gz').option('recursiveFileLookup', 'true')
        .option('maxFilesPerTrigger', '3')          # optional; 10 files gave 4 commits with availableNow
        .load(f'{RAW}/mediawiki.recentchange')      # .../dt=YYYY-MM-DD/hour=HH/part-*.ndjson.gz
        .select(F.col('value').alias('raw'),
                F.col('_metadata.file_path').alias('source_file'),
                F.col('_metadata.file_modification_time').alias('source_file_mtime'),
                F.get_json_object('value', '$.meta.id').alias('meta_id'),
                F.to_timestamp(F.get_json_object('value', '$.meta.dt')).alias('meta_dt'),
                F.current_timestamp().alias('ingested_at')))
(df.writeStream.format('delta').option('checkpointLocation', ckpt)
   .trigger(availableNow=True).start(bronze_path).awaitTermination())
```
A glob path `.../dt=*/hour=*/*.ndjson.gz` also works and picks up `dt=` folders created later. Do not set `ignoreCorruptFiles`.

**S4 Bronze to Silver, exactly-once**

```python
COLS = ['meta_id', 'meta_dt', 'wiki', 'rc_id', 'rev_id', 'title']
def upsert(batch_df, batch_id):
    typed = (batch_df.where('meta_id IS NOT NULL')
             .select('meta_id', 'meta_dt',
                     F.get_json_object('raw', '$.wiki').alias('wiki'),
                     F.get_json_object('raw', '$.id').cast('bigint').alias('rc_id'),
                     F.get_json_object('raw', '$.revision.new').cast('bigint').alias('rev_id'),
                     F.get_json_object('raw', '$.title').alias('title'))
             .dropDuplicates(['meta_id']))                      # MERGE does not dedup inside the source
    (DeltaTable.forPath(batch_df.sparkSession, silver).alias('t')
       .merge(typed.alias('s'), 't.meta_id = s.meta_id')
       .whenNotMatchedInsert(values={c: f's.{c}' for c in COLS})  # explicit list: target has a generated column
       .execute())
(spark.readStream.format('delta').load(bronze)
   .writeStream.foreachBatch(upsert).option('checkpointLocation', ckpt)
   .trigger(availableNow=True).start().awaitTermination())
```
For a plain append inside foreachBatch (the label-observation table): `batch_df.write.format('delta').mode('append').option('txnAppId', 'bronze_to_obs').option('txnVersion', batch_id).save(sink)`; a crash after the append followed by a replay left 4050 rows, one commit.

**S5 SCD Type 2 for dim_page (re-run writes no commit)**

```sql
CREATE OR REPLACE TEMP VIEW changed AS
SELECT u.*, d.page_id IS NOT NULL AS has_current
FROM page_updates u
LEFT JOIN (SELECT * FROM delta.`{dim}` WHERE is_current) d
  ON d.wiki_db = u.wiki_db AND d.page_id = u.page_id
WHERE d.page_id IS NULL
   OR (NOT (d.page_title <=> u.page_title) AND u.observed_at > d.valid_from);   -- add one <=> per tracked attribute

MERGE INTO delta.`{dim}` t
USING (SELECT page_id AS merge_key, * FROM changed WHERE has_current        -- closes the old current row
       UNION ALL
       SELECT CAST(NULL AS BIGINT) AS merge_key, * FROM changed) s          -- NULL key never matches: inserted as the new current row
ON t.wiki_db = s.wiki_db AND t.page_id = s.merge_key AND t.is_current = true
WHEN MATCHED THEN UPDATE SET is_current = false, valid_to = s.observed_at
WHEN NOT MATCHED THEN INSERT (wiki_db, page_id, page_title, valid_from, valid_to, is_current)
  VALUES (s.wiki_db, s.page_id, s.page_title, s.observed_at, NULL, true);
```
The classic form (all incoming rows in the source, change test in `WHEN MATCHED AND ...`) and the Python API form (`whenMatchedUpdate(condition=..., set=...)`, `whenNotMatchedInsert(values=...)`) also give identical rows on re-run, but each re-run writes a commit that rewrites the matched files.

**S6 label upsert with CDF**

```sql
MERGE INTO delta.`{lab}` t
USING (SELECT s.* FROM labels_in s
       LEFT JOIN delta.`{lab}` t ON t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id
       WHERE t.rev_id IS NULL
          OR NOT (t.is_reverted <=> s.is_reverted AND t.reverting_rev_id <=> s.reverting_rev_id AND t.revert_ts <=> s.revert_ts)) s
ON t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id
WHEN MATCHED AND NOT (t.is_reverted <=> s.is_reverted AND t.reverting_rev_id <=> s.reverting_rev_id AND t.revert_ts <=> s.revert_ts)
  THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

SELECT * FROM table_changes_by_path('{lab}', 1, 4);      -- also table_changes('delta.`{lab}`', 0) and table_changes('name', 0)
```
```python
spark.read.format('delta').option('readChangeFeed', 'true').option('startingVersion', 0).load(lab)
spark.readStream.format('delta').option('readChangeFeed', 'true').option('startingVersion', 0).load(lab)   # with foreachBatch + availableNow
```
Change columns: `_change_type` (insert, update_preimage, update_postimage), `_commit_version`, `_commit_timestamp`.

**S7 time travel**

```sql
CREATE TABLE delta.`{p}` (...) USING DELTA TBLPROPERTIES ('delta.enableInCommitTimestamps'='true');   -- at CREATE, not later
SELECT count(*) FROM delta.`{p}` VERSION AS OF 1;
SELECT count(*) FROM delta.`{p}` TIMESTAMP AS OF '2026-11-13 11:29:53.810';
DESCRIBE HISTORY delta.`{p}`;
RESTORE TABLE delta.`{p}` TO VERSION AS OF 2;
```
```python
spark.read.format('delta').option('versionAsOf', 2).load(p)      # or load(p + '@v2')
df.write.format('delta').mode('append').option('userMetadata', 'load batch 0').save(p)
spark.conf.set('spark.databricks.delta.commitInfo.userMetadata', 'run_id=abc123 snapshot=2026-05')   # for SQL, UPDATE, MERGE
```

**S8 maintenance**

```sql
OPTIMIZE delta.`{p}` WHERE event_date = DATE'2026-05-01';
OPTIMIZE delta.`{p}` ZORDER BY (page_id);            -- not a partition column, not on a clustered table
VACUUM delta.`{p}` DRY RUN;                          -- default 7-day retention
VACUUM delta.`{p}` RETAIN 0 HOURS;                   -- only after spark.databricks.delta.retentionDurationCheck.enabled=false
```
Set `spark.sql.sources.parallelPartitionDiscovery.parallelism` to 2 before VACUUM in local mode.

**S11 raw JSON in Bronze: keep STRING.** VARIANT works (`parse_json`, `try_parse_json`, `variant_get(raw_v, '$.meta.id', 'string')`, `raw_v:meta.id::string`), but it raises the table to reader 3 / writer 7, saved only about 10% of space here, was not faster to query in a single run, and is unsafe to touch from delta-rs.

## Protocol by feature

From `DESCRIBE DETAIL` after each DDL (RAN). `tableFeatures` in DESCRIBE DETAIL also lists the features implied by legacy writer versions.

| Table created with | minReader | minWriter | tableFeatures |
|---|---|---|---|
| nothing special (default) | 1 | 2 | appendOnly, invariants |
| `delta.appendOnly=true` + log / deleted-file retention durations | 1 | 2 | appendOnly, invariants |
| CHECK constraint (ALTER ADD CONSTRAINT or `delta.constraints.<name>` property) | 1 | 3 | appendOnly, checkConstraints, invariants |
| generated column `event_date` | 1 | 7 | appendOnly, generatedColumns, invariants |
| `delta.enableChangeDataFeed=true` (at CREATE or by ALTER) | 1 | 7 | appendOnly, changeDataFeed, invariants |
| `CLUSTER BY` (liquid) | 1 | 7 | appendOnly, clustering, domainMetadata, invariants |
| `delta.enableInCommitTimestamps=true` | 1 | 7 | appendOnly, inCommitTimestamp, invariants |
| `GENERATED ALWAYS AS IDENTITY` column | 1 | 7 | appendOnly, identityColumns, invariants |
| `delta.enableDeletionVectors=true` (at CREATE or by ALTER) | **3** | 7 | appendOnly, deletionVectors, invariants |
| VARIANT column | **3** | 7 | appendOnly, invariants, variantType |
| table created by delta-rs `write_deltalake` | 1 | 2 | appendOnly, invariants |
| table created by delta-rs with `delta.enableChangeDataFeed` | 1 | 4 | (legacy writer 4) |

Raw protocol action of the VARIANT table: `{"protocol":{"minReaderVersion":3,"minWriterVersion":7,"readerFeatures":["variantType"],"writerFeatures":["variantType","invariants","appendOnly"]}}`.

Deletion vectors are **off by default** in delta-spark 4.4.1: a new table is reader 1 / writer 2, and a DELETE rewrote the file (numAddedFiles 1, numRemovedFiles 1, numDeletionVectorsAdded 0). After enabling, the same DELETE added one deletion vector and rewrote nothing. Dropping a CHECK constraint leaves the protocol at writer 3. Enabling in-commit timestamps by ALTER adds `delta.inCommitTimestampEnablementVersion` and `delta.inCommitTimestampEnablementTimestamp`; earlier commits keep file-mtime timestamps.

## delta-rs compatibility

deltalake 1.6.6 against tables written by Spark 4.2.0 / Delta 4.4.1 (all RAN). Spark re-read every table afterwards.

| Spark-written table | delta-rs read | delta-rs append | delta-rs merge | Notes |
|---|---|---|---|---|
| plain (12 commits, checkpoint at v10) | OK, also `version=3` and `load_as_version(5)` | OK | OK | Spark then appended and merged; delta-rs read back 15 rows |
| CDF-enabled, after a Spark MERGE | OK; `load_cdf` OK | OK | OK, writes cdc files | Spark reads the change feed across both engines' commits (14 rows) and the reverse works too |
| generated column + partition | OK | OK, computes `event_date` itself | OK | wrong generated value rejected: `Invalid data found: 1 rows failed validation check` |
| CHECK constraint | OK | OK | OK | violating row rejected with the same message |
| appendOnly | OK | OK | rejected | `CommitFailedError: The transaction includes Remove action with data change but Delta table is append-only` (also for delete) |
| liquid-clustered | OK | **fails** | **fails** | `CommitFailedError: Unsupported table features required: [ClusteredTable, DomainMetadata]` |
| in-commit timestamps | OK, history OK | **fails** | **fails** | `CommitFailedError: Unsupported table features required: [InCommitTimestamp]` |
| identity column | OK | **fails** | **fails** | `CommitFailedError: Unsupported table features required: [IdentityColumns]` |
| deletion vectors after a DELETE | `to_pyarrow_table`, `to_pandas`, `to_pyarrow_dataset` **fail**; `QueryBuilder` SQL works (990 rows, min id 10, matching Spark) | OK | OK and honours the vector (989 rows copied); Spark then read 992 rows, none of the deleted ids | `DeltaProtocolError: The table has set these reader features: {'deletionVectors'} but these are not yet supported by the deltalake reader.` |
| VARIANT column | OK, but as `struct<metadata: binary, value: binary>` (undecoded) | without the column: `SchemaMismatchError: Cannot cast schema, number of fields does not match: 2 vs 3`. With `schema_mode='merge'`: succeeds **and breaks the table for Spark** | OK (existing variant values kept, new row NULL); Spark still reads | after the schema_mode='merge' append the table schema says struct, and Spark fails: `Invalid Spark read type: expected optional group raw_v (VARIANT(1)) {...} to be variant type but found STRUCT<metadata: BINARY NOT NULL, value: BINARY NOT NULL>` |

Tables created by delta-rs (plain partitioned, and CDF-enabled followed by a delta-rs merge): Spark read them, read the delta-rs change feed (6 rows: 4 insert, 1 update_preimage, 1 update_postimage), appended, ran MERGE and OPTIMIZE, and produced its own change rows; delta-rs then read everything back including `load_cdf` over the mixed commits (9 rows). Protocols stayed at 1/2 and 1/4.

Practical reading: delta-rs is a safe reader for everything except deletion-vector tables via pyarrow, and a safe writer only for tables limited to appendOnly, CHECK, generated columns and CDF. Not tested: both engines writing at the same moment on the local filesystem (UNVERIFIED; keep one writer at a time).

## Pitfalls

All RAN unless marked UNVERIFIED.

**Setup**
- pyspark 4.3.0 is not usable with delta-spark 4.4.1 (pip cap `<=4.2.0`; Maven 404 for `delta-spark_4.3_2.13:4.4.1`).
- Python workers start PATH `python3` (3.13) and fail: `[PYTHON_VERSION_MISMATCH] Python in worker has different version: 3.13 than that in driver: 3.12, PySpark cannot run with different minor versions.` It hit `createDataFrame` from Python rows. Fix: `os.environ['PYSPARK_PYTHON'] = sys.executable` before building the session.
- Ivy adds hadoop-client 3.4.2, parquet 1.16.0 and jackson 2.13.5 jars next to pyspark's own (hadoop-client 3.5.0). Nothing failed, but the two-jar `spark.jars` start avoids the duplication and the network.
- The console progress bar overwrites printed lines; set `spark.ui.showConsoleProgress=false`. Expected failures still print full executor stack traces.
- In-memory catalog: table names vanish at session end. Use `delta.`path`` identifiers or re-register with `CREATE TABLE IF NOT EXISTS name USING DELTA LOCATION` each session. Hive support persists names. UNVERIFIED: embedded Derby allows only one process at a time.

**Bronze ingestion**
- capture.py writes each file under its final name while open (READ `/home/user/truth-lag/ingest/vps/capture.py:52-63`), so open files look like finished ones. With default options one such file, or one truncated file, fails the whole micro-batch: `[FAILED_READ_FILE.NO_HINT] Encountered error while reading file ...part-S1-0.ndjson.gz. SQLSTATE: KD001`, caused by `java.io.EOFException: Unexpected end of input stream`. Nothing is committed (0 rows), and the next run after the file is complete ingests everything once. A file left truncated for good blocks every run until it is moved or repaired.
- `ignoreCorruptFiles=true` is worse: the readable prefix is ingested (600 of 1000 lines for the open file, 596 for the truncated one), the file is recorded as done, and after the file was completed the missing 400 lines were never read. The file source tracks paths, not sizes.
- The generated `event_date` uses the writer's session time zone. The instant 2026-05-02T03:00:00Z landed in `event_date=2026-05-02` from a UTC session and in `event_date=2026-05-01` from an America/Los_Angeles session; a UTC query `WHERE meta_dt >= '2026-05-02'` then returned 1 of 2 rows. Pin `spark.sql.session.timeZone=UTC` everywhere. delta-rs computed the value in UTC.
- Without `recursiveFileLookup`, the text source adds typed partition columns from the folders: `struct<value:string,dt:date,hour:int>`.

**MERGE**
- `whenNotMatchedInsertAll()` fails if the target has a generated column absent from the source: `[DELTA_MERGE_UNRESOLVED_EXPRESSION] Cannot resolve event_date in INSERT clause given columns s.meta_id, s.meta_dt, s.wiki, s.rc_id, s.rev_id, s.title.` Use an explicit column list (SQL or `whenNotMatchedInsert(values=...)`), or compute the column in the source.
- Insert-only MERGE does not dedup inside the source: 3 source rows with 2 distinct keys inserted 3 rows. Call `dropDuplicates` first.
- No-op updates produce change rows: an identical reload through `WHEN MATCHED THEN UPDATE` gave 3 update_preimage + 3 update_postimage rows. The `<=>` guard gives 0 change rows, but on a plain table the guarded re-run still wrote a commit (version 2 to 3, numTargetRowsCopied 3, one file rewritten). The same happened for the classic SCD2 form (numTargetRowsCopied 6). With a pre-filtered source, or with deletion vectors enabled, the re-run wrote no commit at all.
- With the guard, columns outside the guard are not refreshed (the `snapshot` column stayed '2026-05' on unchanged rows).
- delta-rs `when_matched_update_all()` without a predicate also emits no-op update pairs.
- An insert-only MERGE that inserts nothing writes no commit (replayed batch left the Silver version at 2).
- foreachBatch can be called with an empty batch (seen right after OPTIMIZE on the source), and is not called at all when nothing is new.
- UNVERIFIED: several changes for one page in a single SCD2 batch would make two source rows match one target row; reduce to one row per key per run.

**Streaming from Delta**
- An UPDATE on a source table kills the stream: `[DELTA_SOURCE_TABLE_IGNORE_CHANGES] Detected a data update (for example UPDATE ...) in the source table at version 2. This is currently not supported...`. `skipChangeCommits=true` got past it, but the next run without the option failed again on the same version, so the option has to stay. Keeping Bronze `appendOnly` avoids the case. OPTIMIZE and VACUUM on the source did not disturb the stream.

**Time travel and maintenance**
- Without in-commit timestamps the commit timestamp is the mtime of `_delta_log/N.json` (history showed 11:29:50.574 = file mtime, while commitInfo.timestamp was 11:29:50.545). After `cp -r` all four commits showed the copy time and `TIMESTAMP AS OF` the original time failed: `[DELTA_TIMESTAMP_EARLIER_THAN_COMMIT_RETENTION] The provided timestamp (2026-11-13 11:30:50.03) is before the earliest version available to this table (2026-11-13 11:31:00.961).` `VERSION AS OF` still worked, and `cp -rp` preserved everything.
- With `delta.enableInCommitTimestamps=true` set at CREATE, history and `TIMESTAMP AS OF` were identical after `cp -r`. Enabled later by ALTER, earlier commits carry no inCommitTimestamp. The price: delta-rs cannot write to the table.
- VACUUM in local mode: 39.0 s for a DRY RUN on a 20,000-row table because `spark.sql.sources.parallelPartitionDiscovery.parallelism` defaults to 10000; 4.6 s at 2.
- The retention error text names `delta.retentionDurationCheck.enabled`; the conf that worked is `spark.databricks.delta.retentionDurationCheck.enabled`.
- After `VACUUM ... RETAIN 0 HOURS`, `count(*) ... VERSION AS OF 1` still returned 5000 (answered from log statistics) while a real read failed with `[FAILED_READ_FILE.FILE_NOT_EXIST]`. Do not use count(*) to prove an old version is readable.
- VACUUM adds two commits (VACUUM START, VACUUM END). Identity values are unique but not consecutive (1, 2, 4, 5, 6, 7).
- Rejections worth knowing: inline `CONSTRAINT ... CHECK` in CREATE (`[UNSUPPORTED_FEATURE.TABLE_OPERATION] ... does not support table constraint`); `PARTITIONED BY` with `CLUSTER BY` (`Clustering and partitioning cannot both be specified`); ZORDER on a clustered table (`[DELTA_CLUSTERING_WITH_ZORDER_BY]`); ZORDER on a partition column (`[DELTA_ZORDERING_ON_PARTITION_COLUMN]`); CDF read on a table without CDF (`[DELTA_MISSING_CHANGE_DATA]`).

## Performance

All RAN on this machine (4 CPUs, 15 GB), `local[2]`, `spark.driver.memory=4g` (max heap 4096 MB). The scale test ran with no other JVM of mine alive; other agents' load is unknown. Single runs, no repeats.

**Scale test (S10): 5,000,000 rows x 12 string columns, shuffle partitions 8**

| Step | Plain table | Deletion vectors on |
|---|---|---|
| Write 5,000,000 rows | 14.1 s, 453 MB parquet, 2 files | 12.2 s, 453 MB, 2 files |
| MERGE 300,000 updates (keys spread over the whole table) | **20.9 s**; 4,700,000 rows copied, 2 files removed, 8 added; folder grows to 909 MB | **11.4 s**; 0 rows copied, 2 deletion vectors, 8 files added; 472 MB |
| Verify (count reverted, count all) | 1.4 s | 1.8 s |

- Insert-only MERGE of 300,000 source rows (150,000 new) into the 5M-row table: 3.2 s.
- OPTIMIZE afterwards (11 files to 1): 27.0 s. Full-scan groupBy over 5M rows: 3.1 s.
- Peak JVM resident memory over the whole run: 2.81 GB (VmHWM), so a 4g driver fits the 6 GB budget.

**Start-up and install**
- `uv pip install delta-spark==4.4.1`: 1 min 46 s (resolution 1 min 33 s, pyspark built from sdist). venv sizes: Spark 478 MB, delta-rs 424 MB; Ivy cache 174 MB.
- First session start 28.8 s (Ivy resolve 16.8 s, download 6.8 s). Later starts 5.0 s with the Ivy cache, 3.7 s with two local jars in `spark.jars`.

**Small operations**
- Tiny-table commits cost seconds, not milliseconds: a script doing three small MERGEs plus checks took 18 to 31 s; twelve single-row INSERTs took 27 s. Batch work into few commits.
- VACUUM DRY RUN on a 20,000-row table: 39.0 s default, 4.6 s with listing parallelism 2; real VACUUM 6.1 s.
- Streaming runs with availableNow over a handful of small files: 5 to 12 s each including checkpoint work.

**STRING versus VARIANT, 300,000 synthetic recentchange-like events**
- STRING table 28.2 MB (write 1.7 s); VARIANT table 25.3 MB (parse + write 5.5 s).
- Extracting two fields over all rows: `get_json_object` on STRING 2.6 s, `variant_get` on VARIANT 3.9 s (same results).

The raw data is not in this container, so none of these numbers are from real TruthLag files.

## Test matrix

| Feature | Status | Evidence |
| --- | --- | --- |
| S0 install: which pyspark delta-spark==4.4.1 pulls | works | RAN: uv installed delta-spark 4.4.1, pyspark 4.2.0, py4j 0.10.9.9 (not pyspark 4.3.0). READ venv/lib/python3.12/site-packages/delta_spark-4.4.1.dist-info/METADATA:24 'Requires-Dist: pyspark<=4.2.0,>=4.0.1'. RAN curl: io.delta:delta-spark_4.3_2.13:4.4.1 returns 404; _4.0, _4.1, _4.2 and unsuffixed return 200. |
| S0 Ivy fetch of Delta jars from Maven Central through the proxy | works | RAN: no extra settings; the exported JAVA_TOOL_OPTIONS (https.proxyHost/Port, trustStore) is enough. Log: 'found io.delta#delta-spark_4.2_2.13;4.4.1 in central', ':: resolution report :: resolve 16773ms :: artifacts dl 6792ms', '33 artifacts copied, 0 already retrieved (87065kB/59ms)'. First start 28.8 s, later 5.0 s. Non-fatal: 'Server access error at url https://repos.spark-packages.org/... (java.io.IOException: Unable to tunnel through proxy. Proxy returns "HTTP/1.1 403 Forbidden")' x34. |
| S0 start without Ivy or network (two local jars in spark.jars) | works | RAN: start 3.7 s with only io.delta_delta-spark_4.2_2.13-4.4.1.jar and io.delta_delta-storage-4.4.1.jar. Create (generated column + CDF + deletion vectors + in-commit timestamps), MERGE, DELETE, CDF read (1035 rows), OPTIMIZE ZORDER, time travel, history, Delta streaming source and VARIANT all OK. |
| S0 keeping spark-warehouse / metastore_db / derby.log out of the working directory | works | RAN control runs from empty folders. In-memory catalog, no settings: 'cwd entries after run: [spark-warehouse]'; with spark.sql.warehouse.dir: []. With enableHiveSupport and no settings: ['derby.log', 'metastore_db', 'spark-warehouse']; with spark.sql.warehouse.dir plus -Dderby.system.home: []. spark.jars.ivy kept the Ivy cache out of ~/.ivy2. Repo check: git status --porcelain empty. |
| S0 Python workers (createDataFrame from Python rows) inside the venv | partial | RAN: fails by default with '[PYTHON_VERSION_MISMATCH] Python in worker has different version: 3.13 than that in driver: 3.12, PySpark cannot run with different minor versions.' Works after setting PYSPARK_PYTHON to the venv interpreter. |
| S1 partition by a generated column (event_date from meta_dt), path-based | works | RAN: protocol reader 1 / writer 7, features [appendOnly, generatedColumns, invariants]. Inserts without event_date fill it; partition folders event_date=2026-05-01..03; a filter on meta_dt pruned to 1 of 3 files. Wrong explicit value rejected: '[DELTA_VIOLATE_CONSTRAINT_WITH_VALUES] CHECK constraint Generated Column (event_date <=> CAST(meta_dt AS DATE)) violated by row with values'. |
| S1 generated event_date across session time zones | partial | RAN: the same instant 2026-05-02T03:00:00Z was stored with event_date 2026-05-02 from a UTC session and 2026-05-01 from an America/Los_Angeles session; a UTC query WHERE meta_dt >= '2026-05-02' then returned 1 of 2 rows. Correct only if every writer pins the session time zone. |
| S1 TBLPROPERTIES delta.appendOnly + retention durations | works | RAN: protocol stays reader 1 / writer 2. DELETE, UPDATE, MERGE with update and INSERT OVERWRITE all fail with '[DELTA_CANNOT_MODIFY_APPEND_ONLY] This table is configured to only allow appends. If you would like to permit updates or deletes, use 'ALTER TABLE null SET TBLPROPERTIES (delta.appendOnly=false)'.' Insert-only MERGE and OPTIMIZE are allowed. |
| S1 TBLPROPERTIES delta.enableChangeDataFeed | works | RAN: reader 1 / writer 7, features [appendOnly, changeDataFeed, invariants], both at CREATE and after ALTER TABLE SET TBLPROPERTIES on a plain 1/2 table; also together with appendOnly. |
| S1 CHECK constraint via ALTER TABLE or delta.constraints.<name> property | works | RAN: reader 1 / writer 3, features [appendOnly, checkConstraints, invariants]. Violating insert: '[DELTA_VIOLATE_CONSTRAINT_WITH_VALUES] CHECK constraint rev_id_positive (rev_id > 0) violated by row with values: - rev_id : -5'. Adding a constraint existing rows break: '[DELTA_NEW_CHECK_CONSTRAINT_VIOLATION] 1 rows in delta.`...` violate the new CHECK constraint (lag_s > 100)'. Protocol stays writer 3 after DROP CONSTRAINT. |
| S1 inline CONSTRAINT ... CHECK inside CREATE TABLE | fails | RAN: 'AnalysisException: [UNSUPPORTED_FEATURE.TABLE_OPERATION] The feature is not supported: Table `spark_catalog`.`delta`.`...` does not support table constraint.' |
| S1 liquid clustering (CLUSTER BY) | works | RAN: reader 1 / writer 7, features [appendOnly, clustering, domainMetadata, invariants]; clusteringColumns [wiki_db, rev_id]. OPTIMIZE clustered 8 files into 1; ALTER TABLE CLUSTER BY (page_id) and MERGE work. Rejected: 'Operation not allowed: Clustering and partitioning cannot both be specified.' and '[DELTA_CLUSTERING_WITH_ZORDER_BY] OPTIMIZE command for Delta table with clustering cannot specify ZORDER BY.' |
| S1 Python DeltaTable builder (generated column, properties, clusterBy) | works | RAN: createIfNotExists twice leaves a single version 0 with reader 1 / writer 7 and delta.appendOnly=true; .clusterBy('wiki_db','rev_id') gives the same protocol as the SQL form. |
| S2 idempotent batch append with txnAppId / txnVersion | works | RAN: (app,1) wrote 100 rows as v0; (app,1) again: rows 100, still v0, no commit; (app,2): 200 rows, v1; (app,1) again: skipped; (another_app,1): 300 rows, v2. Log holds {"txn":{"appId":"hist_snapshot_load","version":1,...}}. A lower version for the same appId is silently skipped. SQL INSERT with the session confs spark.databricks.delta.write.txnAppId/txnVersion is idempotent too (10 rows after two inserts); the confs stay set. READ /home/user/delta-io/delta/docs/src/content/docs/delta-streaming/index.mdx:325-330. |
| S3 file-source streaming of .ndjson.gz into Bronze, availableNow + checkpoint | works | RAN: run 1 ingested 3 files (3000 rows); run 2 with no new files added nothing and no commit; run 3 picked up only the new file (500 rows, 3500 total). History: v1 STREAMING UPDATE numOutputRows 3000, v2 500. One string column per line plus _metadata.file_path and file_modification_time. maxFilesPerTrigger=3 over 10 files gave 4 commits; a glob path picked up a dt= folder created later (2200 rows). |
| S3 gzip without end marker (file still being written) or truncated, default options | partial | RAN, same for both cases: the micro-batch fails with '[STREAM_FAILED] ... [FAILED_READ_FILE.NO_HINT] Encountered error while reading file file:///...part-S1-0.ndjson.gz. SQLSTATE: KD001', cause 'java.io.EOFException: Unexpected end of input stream'. Bronze stays at 0 rows, including the good file in the same batch. After the file was completed the next run ingested all 2000 rows once. Safe, but one bad file blocks the stream. Batch spark.read.text fails the same way. |
| S3 same bad gzip files with ignoreCorruptFiles=true | fails | RAN: silent loss. Open file: 600 of 1000 lines ingested; truncated file: 596 of 1000. The file is recorded as processed; after it was completed under the same path the next run added nothing (totals stayed 1600 and 1596 instead of 2000). |
| S4 Bronze to Silver: Delta readStream + foreachBatch insert-only MERGE, availableNow | works | RAN: run 1 3500 rows; run 2 nothing (foreachBatch not called); then Bronze got 550 rows (300 new ids, 50 in-batch duplicates, 200 duplicates of old ids) and the batch function raised after its MERGE had committed: Silver 3800 rows, 3800 distinct. Replay of the same batch: still 3800, Silver version unchanged at 2. History: v1 MERGE inserted 3500; v2 MERGE inserted 300 of 500 source rows. Bounded batches work (maxFilesPerTrigger=1 gave 7 calls). |
| S4 whenNotMatchedInsertAll when the target has a generated column | fails | RAN: '[DELTA_MERGE_UNRESOLVED_EXPRESSION] Cannot resolve event_date in INSERT clause given columns s.meta_id, s.meta_dt, s.wiki, s.rc_id, s.rev_id, s.title.' Working alternatives, all RAN: whenNotMatchedInsert(values=explicit columns), SQL INSERT (cols) VALUES (...), or computing event_date in the source. |
| S4 dedup inside the MERGE source | partial | RAN: insert-only MERGE with source rows (a,1),(a,2),(b,3) inserted 3 rows. MERGE only dedups against the target; dropDuplicates(['meta_id']) on the batch is required. |
| S4 foreachBatch plain append made idempotent with txnAppId + txnVersion=batch_id | works | RAN: batch function raised after the append; 4050 rows after the crash, 4050 after the replay, history shows a single WRITE. |
| S4 Delta streaming source when the source table is changed or maintained | partial | RAN: UPDATE on the source fails the stream: '[DELTA_SOURCE_TABLE_IGNORE_CHANGES] Detected a data update (for example UPDATE ...) in the source table at version 2. This is currently not supported.' skipChangeCommits=true passed, but a later run without it failed again on version 2. OPTIMIZE and VACUUM RETAIN 0 HOURS on an appendOnly source did not disturb the stream (0 rows, then exactly the 1 new row each time). READ /home/user/delta-io/delta/docs/src/content/docs/delta-streaming/index.mdx:57-59. |
| S5 SCD Type 2 MERGE, staged source with NULL merge key (SQL and Python API) | works | RAN: batch 2 (1 unchanged, 2 changed, 1 new) updated 2 and inserted 3; one current row per page. Re-run: num_affected_rows 0 and identical rows, but a new commit (version 2 to 3) that rewrote a file (numTargetRowsCopied 6). Python API form behaved the same (numTargetRowsCopied 4). IDENTITY surrogate key works in Spark (reader 1 / writer 7, identityColumns). |
| S5 SCD Type 2 with the staged source pre-filtered to changed/new pages | works | RAN on a plain table and a CDF table: re-run reports 0 rows, rows identical, and the version stays 2 (no commit, no file rewrite). |
| S6 label upsert MERGE with Change Data Feed, reading changes | works | RAN: table_changes_by_path('{p}', v0, v1), table_changes('delta.`{p}`', 0) and table_changes('name', 0) all return the feed (12 rows); option readChangeFeed with startingVersion works in batch and in a stream (one batch, 12 rows). A real change produced update_preimage + update_postimage for the changed revision and an insert for the new one. _change_data folder holds the cdc files. |
| S6 do no-op updates produce change rows, and the predicate that avoids them | partial | RAN: yes. An identical reload through WHEN MATCHED THEN UPDATE gave num_updated_rows 3 and 6 change rows (3 preimage, 3 postimage, equal values). With the guard: 0 change rows. But on a plain table the guarded re-run still wrote a commit (numTargetRowsCopied 3, 1 file added, 2 removed). No commit at all when the source is pre-filtered, or when deletion vectors are enabled (version 1 stays 1). |
| S7 VERSION AS OF, TIMESTAMP AS OF, path@vN, versionAsOf | works | RAN: all return the right counts; a timestamp between two commits resolves to the earlier one. Errors: '[DELTA_TIMESTAMP_GREATER_THAN_COMMIT] Timestamp 2030-01-01 00:00:00.0 is after the table's latest version' and '[DELTA_TIMESTAMP_EARLIER_THAN_COMMIT_RETENTION] The provided timestamp (2020-01-01 00:00:00.0) is before the earliest version available to this table'. |
| S7 DESCRIBE HISTORY (operation metrics, user metadata) and RESTORE | works | RAN: history shows operation, operationMetrics (numOutputRows, numFiles, numUpdatedRows ...) and userMetadata set by the writer option ('load batch 0') or by the session conf for SQL ('run_id=abc123 snapshot=2026-05'). RESTORE TABLE ... TO VERSION AS OF 2 returned {num_restored_files: 1, num_removed_files: 3}, undid the UPDATE and was logged as operation RESTORE (v5). |
| S7 TIMESTAMP AS OF after cp -r, without in-commit timestamps | fails | RAN: the commit timestamp is the mtime of _delta_log/N.json. After cp -r, history shows the copy time for all four commits (11:31:00.961 to .964) and the original timestamp fails: '[DELTA_TIMESTAMP_EARLIER_THAN_COMMIT_RETENTION] The provided timestamp (2026-11-13 11:30:50.03) is before the earliest version available to this table (2026-11-13 11:31:00.961).' VERSION AS OF still works; cp -rp preserves timestamps. |
| S7 in-commit timestamps (delta.enableInCommitTimestamps) | works | RAN: reader 1 / writer 7, feature inCommitTimestamp; each commitInfo carries inCommitTimestamp and is the first action. After cp -r, history timestamps were identical and TIMESTAMP AS OF the original times returned 10 and 20 rows as expected. Enabled later by ALTER: adds delta.inCommitTimestampEnablementVersion=4, and commits 0-3 have no inCommitTimestamp, so enable it at CREATE. |
| S8 OPTIMIZE and ZORDER BY | works | RAN: 24 files; OPTIMIZE with a partition predicate added 1, removed 12; OPTIMIZE ZORDER BY (page_id) added 2, removed 13, leaving 2 live files. Python optimize().executeCompaction() works. ZORDER on a partition column: '[DELTA_ZORDERING_ON_PARTITION_COLUMN] event_date is a partition column. Z-Ordering can only be performed on data columns'. |
| S8 VACUUM (retention check, DRY RUN) | works | RAN: default-retention DRY RUN lists 0 paths. RETAIN 0 HOURS with the check on: '[DELTA_VACUUM_RETENTION_PERIOD_TOO_SHORT] The specified VACUUM retention period is too low and may corrupt this Delta table if any writes are in progress.' With spark.databricks.delta.retentionDurationCheck.enabled=false: DRY RUN lists 25 paths and deletes nothing; the real run deleted 25 (27 parquet files on disk down to 2). VACUUM LITE DRY RUN parses. Slow by default: 39.0 s for a DRY RUN versus 4.6 s with spark.sql.sources.parallelPartitionDiscovery.parallelism=2. After it, a real read of version 1 fails with [FAILED_READ_FILE.FILE_NOT_EXIST] while count(*) still answers 5000 from statistics. |
| S8 deletion vectors: default and effect on the protocol | works | RAN: off by default in delta-spark 4.4.1 (new table reader 1 / writer 2; DELETE rewrote the file, numDeletionVectorsAdded 0). With delta.enableDeletionVectors=true, at CREATE or by ALTER, the protocol becomes reader 3 / writer 7 with feature deletionVectors; DELETE then adds 1 vector and rewrites no file; MERGE and REORG TABLE ... APPLY (PURGE) work. |
| S9 delta-rs READ: plain (with checkpoint), CDF after MERGE, generated column, CHECK, appendOnly, identity, in-commit timestamps, liquid-clustered | works | RAN with deltalake 1.6.6: to_pyarrow_table returned the right row counts for all of these; load_cdf on the CDF table returned 6 rows (insert, update_preimage, update_postimage); time travel by version works; history() works on the ICT, liquid and generated tables. |
| S9 delta-rs READ: deletion vectors after a DELETE | partial | RAN: to_pyarrow_table, to_pandas and to_pyarrow_dataset fail with 'DeltaProtocolError: The table has set these reader features: {'deletionVectors'} but these are not yet supported by the deltalake reader.' QueryBuilder SQL works and honours the vector: [{'c': 990, 'min_id': 10}], same as Spark. |
| S9 delta-rs READ and WRITE: VARIANT column | partial | RAN: read works but the column arrives as struct<metadata: binary not null, value: binary not null>. Merge with a source lacking the column succeeded and Spark still read the table. Append with schema_mode='merge' succeeded but rewrote the table schema to a struct; Spark then fails: 'Invalid Spark read type: expected optional group raw_v (VARIANT(1)) {...} to be variant type but found STRUCT<metadata: BINARY NOT NULL, value: BINARY NOT NULL>'. Append without the column and without schema_mode: 'SchemaMismatchError: Cannot cast schema, number of fields does not match: 2 vs 3'. |
| S9 delta-rs WRITE (append, merge): plain, CDF, generated column, CHECK, deletion vectors | works | RAN: append and merge succeeded on all five; Spark read consistent results afterwards. Generated value computed by delta-rs (event_date 2026-05-03); a wrong generated value and a CHECK-violating row were rejected with 'Invalid data found: 1 rows failed validation check'. Merge on the CDF table wrote cdc files that Spark reads. Merge on the deletion-vector table copied 989 rows; Spark then saw 992 rows and none of the deleted ids. appendOnly table: append OK, merge and delete rejected with 'The transaction includes Remove action with data change but Delta table is append-only'. |
| S9 delta-rs WRITE: liquid-clustered, in-commit timestamps, identity column | fails | RAN: 'CommitFailedError: Unsupported table features required: [ClusteredTable, DomainMetadata]', 'CommitFailedError: Unsupported table features required: [InCommitTimestamp]', 'CommitFailedError: Unsupported table features required: [IdentityColumns]' for both append and merge. The tables were left untouched (Spark history shows only Spark commits). |
| S9 Spark reads and writes tables created by delta-rs, including after a delta-rs merge with CDF | works | RAN: delta-rs created a partitioned table (reader 1 / writer 2) and a CDF table (reader 1 / writer 4) and merged into it (cdc action written). Spark read both, read the delta-rs change feed (6 rows), then INSERT, MERGE and OPTIMIZE; Spark's MERGE produced its own change rows; protocols unchanged. delta-rs read everything back, load_cdf over mixed commits returned 9 rows. History shows engineInfo 'delta-rs:py-1.6.6' and 'Apache-Spark/4.2.0 Delta-Lake/4.4.1'. |
| S10 scale sanity: 5,000,000 rows x 12 string columns, MERGE 300,000 updates | works | RAN, local[2], spark.driver.memory=4g (max heap 4096 MB), shuffle partitions 8. Write 14.1 s (453 MB, 2 files). MERGE of 300,000 updates 20.9 s on a plain table (4,700,000 rows copied; scan 3.2 s, rewrite 17.0 s) and 11.4 s with deletion vectors (0 rows copied). Insert-only MERGE of 300,000 rows 3.2 s; OPTIMIZE 27.0 s; verified 300,000 reverted of 5,000,000. Peak JVM RSS 2.81 GB. |
| S11 VARIANT column with Delta, versus STRING for raw JSON | works | RAN: CREATE with a VARIANT column, parse_json, variant_get, schema_of_variant and the raw_v:meta.id::string syntax all work; protocol reader 3 / writer 7 with readerFeatures [variantType]. parse_json fails on bad input ('[MALFORMED_RECORD_IN_PARSING.WITHOUT_SUGGESTION]'); try_parse_json returns NULL. 300,000 events: STRING 28.2 MB versus VARIANT 25.3 MB; extracting two fields 2.6 s versus 3.9 s. delta-rs sees undecoded binaries and can break the table (see the VARIANT row above). |

## Tested snippets

### S0 install: which pyspark delta-spark==4.4.1 pulls

```bash
uv venv --python 3.12 venv && uv pip install --python venv/bin/python delta-spark==4.4.1
```

### S0 Ivy fetch of Delta jars from Maven Central through the proxy

```text
spark = configure_spark_with_delta_pip(builder).getOrCreate()
```

### S0 start without Ivy or network (two local jars in spark.jars)

```text
.config('spark.jars', IVY + '/jars/io.delta_delta-spark_4.2_2.13-4.4.1.jar,' + IVY + '/jars/io.delta_delta-storage-4.4.1.jar')
```

### S0 keeping spark-warehouse / metastore_db / derby.log out of the working directory

```text
.config('spark.sql.warehouse.dir', HOME + '/warehouse').config('spark.driver.extraJavaOptions', '-Dderby.system.home=' + HOME + '/derby')
```

### S0 Python workers (createDataFrame from Python rows) inside the venv

```text
os.environ['PYSPARK_PYTHON'] = sys.executable; os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
```

### S1 partition by a generated column (event_date from meta_dt), path-based

```sql
CREATE TABLE delta.`{p}` (meta_id STRING NOT NULL, meta_dt TIMESTAMP, raw STRING, source_file STRING, event_date DATE GENERATED ALWAYS AS (CAST(meta_dt AS DATE))) USING DELTA PARTITIONED BY (event_date)
```

### S1 generated event_date across session time zones

```text
.config('spark.sql.session.timeZone', 'UTC')
```

### S1 TBLPROPERTIES delta.appendOnly + retention durations

```text
TBLPROPERTIES ('delta.appendOnly'='true','delta.logRetentionDuration'='interval 3650 days','delta.deletedFileRetentionDuration'='interval 30 days')
```

### S1 TBLPROPERTIES delta.enableChangeDataFeed

```sql
CREATE TABLE delta.`{p}` (id BIGINT, v STRING) USING DELTA TBLPROPERTIES ('delta.enableChangeDataFeed'='true')
```

### S1 CHECK constraint via ALTER TABLE or delta.constraints.<name> property

```sql
ALTER TABLE delta.`{p}` ADD CONSTRAINT rev_id_positive CHECK (rev_id > 0)
```

### S1 inline CONSTRAINT ... CHECK inside CREATE TABLE

```sql
CREATE TABLE delta.`{p}` (wiki_db STRING, rev_id BIGINT, CONSTRAINT rev_pos CHECK (rev_id > 0)) USING DELTA
```

### S1 liquid clustering (CLUSTER BY)

```sql
CREATE TABLE delta.`{p}` (wiki_db STRING, rev_id BIGINT, page_id BIGINT, is_reverted BOOLEAN) USING DELTA CLUSTER BY (wiki_db, rev_id)
```

### S1 Python DeltaTable builder (generated column, properties, clusterBy)

```text
DeltaTable.createIfNotExists(spark).location(p).addColumn('event_date','DATE',generatedAlwaysAs='CAST(meta_dt AS DATE)').partitionedBy('event_date').property('delta.appendOnly','true').execute()
```

### S2 idempotent batch append with txnAppId / txnVersion

```text
df.write.format('delta').mode('append').option('txnAppId','hist_snapshot_load').option('txnVersion',1).save(p)
```

### S3 file-source streaming of .ndjson.gz into Bronze, availableNow + checkpoint

```text
spark.readStream.format('text').option('pathGlobFilter','*.ndjson.gz').option('recursiveFileLookup','true').load(src) ... .writeStream.format('delta').option('checkpointLocation',ck).trigger(availableNow=True).start(sink)
```

### S4 Bronze to Silver: Delta readStream + foreachBatch insert-only MERGE, availableNow

```text
spark.readStream.format('delta').load(bronze).writeStream.foreachBatch(upsert).option('checkpointLocation',ck).trigger(availableNow=True).start()
```

### S4 whenNotMatchedInsertAll when the target has a generated column

```text
.whenNotMatchedInsert(values={c: f's.{c}' for c in COLS})
```

### S4 dedup inside the MERGE source

```text
typed = batch_df...dropDuplicates(['meta_id'])
```

### S4 foreachBatch plain append made idempotent with txnAppId + txnVersion=batch_id

```text
batch_df.write.format('delta').mode('append').option('txnAppId','bronze_to_obs').option('txnVersion',batch_id).save(sink)
```

### S5 SCD Type 2 MERGE, staged source with NULL merge key (SQL and Python API)

```text
ON t.wiki_db = s.wiki_db AND t.page_id = s.merge_key AND t.is_current = true WHEN MATCHED AND NOT (t.page_title <=> s.page_title ...) THEN UPDATE SET is_current = false, valid_to = s.observed_at WHEN NOT MATCHED THEN INSERT ...
```

### S5 SCD Type 2 with the staged source pre-filtered to changed/new pages

```text
USING (SELECT page_id AS merge_key, * FROM changed WHERE has_current UNION ALL SELECT CAST(NULL AS BIGINT) AS merge_key, * FROM changed) s
```

### S6 label upsert MERGE with Change Data Feed, reading changes

```sql
SELECT * FROM table_changes_by_path('{p}', 1, 4)
```

### S6 do no-op updates produce change rows, and the predicate that avoids them

```text
WHEN MATCHED AND NOT (t.is_reverted <=> s.is_reverted AND t.reverting_rev_id <=> s.reverting_rev_id AND t.revert_ts <=> s.revert_ts) THEN UPDATE SET *
```

### S7 VERSION AS OF, TIMESTAMP AS OF, path@vN, versionAsOf

```sql
SELECT count(*) FROM delta.`{p}` TIMESTAMP AS OF '2026-11-13 11:29:53.810'
```

### S7 DESCRIBE HISTORY (operation metrics, user metadata) and RESTORE

```text
spark.conf.set('spark.databricks.delta.commitInfo.userMetadata', 'run_id=abc123 snapshot=2026-05')
```

### S7 in-commit timestamps (delta.enableInCommitTimestamps)

```text
TBLPROPERTIES ('delta.enableInCommitTimestamps'='true')
```

### S8 OPTIMIZE and ZORDER BY

```sql
OPTIMIZE delta.`{p}` ZORDER BY (page_id)
```

### S8 VACUUM (retention check, DRY RUN)

```text
spark.conf.set('spark.sql.sources.parallelPartitionDiscovery.parallelism', '2')
```

### S8 deletion vectors: default and effect on the protocol

```text
TBLPROPERTIES ('delta.enableDeletionVectors'='true')
```

### S9 delta-rs READ: plain (with checkpoint), CDF after MERGE, generated column, CHECK, appendOnly, identity, in-commit timestamps, liquid-clustered

```text
DeltaTable(path).to_pyarrow_table()
```

### S9 delta-rs READ: deletion vectors after a DELETE

```text
QueryBuilder().register('t', DeltaTable(p)).execute('select count(*) as c, min(id) as min_id from t').read_all()
```

### S9 delta-rs WRITE (append, merge): plain, CDF, generated column, CHECK, deletion vectors

```text
write_deltalake(path, data, mode='append'); DeltaTable(path).merge(src, predicate='t.id = s.id', source_alias='s', target_alias='t').when_matched_update_all().when_not_matched_insert_all().execute()
```

### S9 Spark reads and writes tables created by delta-rs, including after a delta-rs merge with CDF

```text
write_deltalake(p, data, configuration={'delta.enableChangeDataFeed': 'true'})
```

### S10 scale sanity: 5,000,000 rows x 12 string columns, MERGE 300,000 updates

```sql
MERGE INTO delta.`{p}` t USING upd s ON t.rev_id = s.rev_id WHEN MATCHED THEN UPDATE SET t.is_reverted = s.is_reverted, t.comment = s.comment WHEN NOT MATCHED THEN INSERT (rev_id, is_reverted, comment) VALUES (s.rev_id, s.is_reverted, s.comment)
```

### S11 VARIANT column with Delta, versus STRING for raw JSON

```sql
INSERT INTO delta.`{p}` SELECT id, raw, parse_json(raw) FROM ev
```

## Open questions

- Which engine reads and writes each layer? If delta-rs must write a table, that table cannot use in-commit timestamps, liquid clustering or identity columns; if delta-rs must read it through pyarrow or pandas, it cannot use deletion vectors. This decides fact_revert_label (in-commit timestamps wanted for TIMESTAMP AS OF) and dim_page (IDENTITY surrogate key).
- Deletion vectors on Gold tables: they halved the 300,000-row MERGE (11.4 s vs 20.9 s) and make a guarded no-op MERGE write no commit, but raise the reader version to 3. Use them, or rely on pre-filtered sources only?
- How will files still being written by the capture be kept out of the Bronze source folder? capture.py opens files under their final name, and one open or truncated .gz fails the whole micro-batch. Options not tested here: copy only closed hours, or validate with gzip -t and quarantine or repair truncated files before the stream runs.
- Catalog choice: path-only tables, in-memory names re-registered each session, or Hive support with an embedded Derby metastore (names persisted across sessions in my test; single-process locking is UNVERIFIED).
- Real data volume is unknown here (data/ is empty), so the scale numbers are synthetic. Row counts and file sizes of the real raw capture and History snapshots would tell whether 4g and local[2] are enough.
- Should txnAppId be one id per snapshot or file with a constant version? A lower txnVersion for the same appId is silently skipped, so reloading an older snapshot under a shared appId would be dropped without any error.
- Not tested: both engines writing concurrently on the local filesystem, RESTORE TO TIMESTAMP AS OF, schema evolution in appends or MERGE, several changes for one page inside a single SCD2 batch, log-retention expiry, and any object store.
- Spark 4.3 is not available with delta-spark 4.4.1. Is pinning pyspark 4.2.0 acceptable for the course deliverable?
- A safety check blocked my cleanup, so about 1.8 GB of test tables remain under the scratch folder (mostly tables/s10). Someone may want to delete /tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/spark_lab/tables.
