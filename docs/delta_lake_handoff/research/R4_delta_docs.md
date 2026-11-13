# R4 — Delta Lake docs fact sheet

> **Research report, not yet reviewed.** Output of the research agent `delta_docs` in a cloud Claude Code session on Nov 13, 2026, as returned. Evidence labels: RAN = executed in that session on made-up data; READ = read at the cited file and line; DERIVED = arithmetic on values that were read; UNVERIFIED = not checked. Paths that start with /tmp/claude-0/ or /home/user/ are on that session's machine and cannot be opened from elsewhere. Repository state read: scottn66/truth-lag at 8e28012.

## Summary

Fact sheet for 17 Delta topics, built from the Delta docs clone (master, 4.5.0-SNAPSHOT, a88e32f), PROTOCOL.md and the delta-rs docs copies. Every claim is READ at a cited file:line; nothing was RAN against a Delta engine. Where the docs are silent I read the Delta Spark source in the same clone and say so.

Path key (absolute): DOCS = /home/user/delta-io/delta/docs/src/content/docs ; PROTO = /home/user/delta-io/delta/PROTOCOL.md ; SRC = /home/user/delta-io/delta/spark/src/main/scala/org/apache/spark/sql/delta ; STORAGE = /home/user/delta-io/delta/storage/src/main/java/io/delta/storage ; ERRJSON = /home/user/delta-io/delta/spark/src/main/resources/error/delta-error-classes.json ; RS = /tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/wf_dl/verify_demo/dl/rsdocs

Findings most likely to change the plan:
1. Open-source Delta accepts only the Serializable isolation level (source; the docs clone has no isolation-level section). An append can therefore conflict with a concurrent MERGE/UPDATE/DELETE on the same table unless the partitions are disjoint and named in the merge condition.
2. A write with txnAppId/txnVersion is skipped when the version recorded for that app id is greater than or equal to the one passed. MERGE, UPDATE and DELETE honour the same pair through session confs (source only, not in the docs).
3. Change data feed: insert-only commits write no _change_data files; change data follows table retention and is deleted by VACUUM; row-tracking fields cannot be read from the feed.
4. Time travel needs both log (default 30 days) and data files (default 7 days before VACUUM may delete). Commit timestamps come from file modification time unless delta.enableInCommitTimestamps is on, so copying a table breaks timestamp time travel. In-commit timestamps have no docs page, only PROTOCOL.md and source.
5. The local file system has no guarantee for concurrent writers; the lock in the source is per JVM, so plan for one writing process per table.
6. delta.targetFileSize is not an open-source Delta property. delta.checkpointInterval (default 10) and delta.dataSkippingStatsColumns exist in source but not in the docs property reference.
7. Liquid clustering cannot be combined with partitioning or ZORDER. Identity columns disable concurrent transactions. Deletion vectors are off by default.
8. delta-rs: idempotent writes are a manual check-then-write; deletion-vector support is stated inconsistently; identity columns are unsupported; DynamoDB is the only AWS S3 locking provider; in-commit timestamps, row tracking, liquid clustering and VARIANT are not mentioned in the copies.
9. Version drift: the docs are master, and their compatibility table stops at Delta 4.3.x with Spark 4.0.x/4.1.x, so the delta-spark 4.4.1 + pyspark 4.3.0 pairing is undocumented here.

## 0 Path key, versions and evidence labels

**Path key (all absolute)**
- DOCS = `/home/user/delta-io/delta/docs/src/content/docs` (Delta docs, master; `/home/user/delta-io/delta/version.sbt` says `4.5.0-SNAPSHOT`, HEAD a88e32f)
- PROTO = `/home/user/delta-io/delta/PROTOCOL.md`
- SRC = `/home/user/delta-io/delta/spark/src/main/scala/org/apache/spark/sql/delta` (Delta Spark source in the same clone; used only where the docs are silent)
- STORAGE = `/home/user/delta-io/delta/storage/src/main/java/io/delta/storage`
- ERRJSON = `/home/user/delta-io/delta/spark/src/main/resources/error/delta-error-classes.json`
- RS = `/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/wf_dl/verify_demo/dl/rsdocs` (delta-rs docs copies; no version stamp inside them)

**Evidence labels.** Every claim below is READ at the cited file:line. Nothing was RAN against a Delta engine; I only ran grep, sed and wc over these files. A statement marked INFERENCE combines two cited facts and is UNVERIFIED. Quotes are exact except that line wraps are joined; where I removed markdown link markup I say so.

**Version caveat.** The Delta docs are master (4.5.0-SNAPSHOT), not the 4.4.1 release. Their compatibility table ends at “4.3.x | 4.0.x, 4.1.x” (DOCS/releases.mdx:19).

## 1 Idempotent writes: txnAppId and txnVersion

- **Batch (DataFrameWriter).** Two options make a write idempotent: `txnAppId` (a stable string per job) and `txnVersion` (a number that grows with each new batch; a retry must reuse the same number). READ DOCS/delta-batch.mdx:1394-1397. Quote: “Any subsequent restarts of the same job needs to have the same value for `txnVersion`.”
- **What makes a write a no-op.** The write is skipped when the version already recorded in the table for that `txnAppId` is greater than or equal to the `txnVersion` passed. READ DOCS/delta-batch.mdx:1403: “Any attempt to write data with `txnAppId = dailyETL` and `txnVersion` as `23422` or less is ignored because the `txnVersion` is less than the last recorded `txnVersion` in the table.” The equal case is in the source, READ SRC/commands/DeltaCommand.scala:379-382: `if (currentVersion >= version)` and the log line “Already completed batch ... This will be skipped.” A different `txnAppId` is tracked separately (DOCS/delta-batch.mdx:1404).
- **The skip looks only at the two ids, never at the data.** READ DOCS/delta-batch.mdx:1410: “If a write attempt in a Delta table succeeds but due to some downstream failure there is a second write attempt with same txn options but different data, then that second write attempt will be ignored.”
- **Session-level form.** `spark.databricks.delta.write.txnAppId`, `spark.databricks.delta.write.txnVersion` and `spark.databricks.delta.write.txnVersion.autoReset.enabled`. READ DOCS/delta-batch.mdx:1406: “When both the writer options and session configuration are set, we will use the writer option values.”
- **MERGE, UPDATE and DELETE (source only, not in the docs).** These commands run the same check against the session confs, so a MERGE can be made idempotent by setting the two confs before it. READ SRC/commands/MergeIntoCommand.scala:89 `if (hasBeenExecuted(deltaTxn, spark))`; SRC/commands/UpdateCommand.scala:101; SRC/commands/DeleteCommand.scala:133; DataFrame writes at SRC/commands/WriteIntoDelta.scala:110. The confs are declared `.internal()` (SRC/sources/DeltaSQLConf.scala:3271-3302).
- **foreachBatch.** Pass the micro-batch id as `txnVersion` and a fixed application id as `txnAppId` on every write inside the function (Delta 2.0.0+). READ DOCS/delta-streaming/index.mdx:317-351: “Delta table uses the combination of `txnAppId` and `txnVersion` to identify duplicate writes and ignore them.” Trap, lines 333-336: “If you delete the streaming checkpoint and restart the query with a new checkpoint, you must provide a different `appId`; otherwise, writes from the restarted query will be ignored”. For a MERGE inside foreachBatch the docs only say to make it idempotent yourself (DOCS/delta-update.mdx:1086-1088).
- **In the log.** Stored as a `txn` action (`appId`, `version`, optional `lastUpdated`). READ PROTO:698-721: “Delta only ensures that the latest `version` for a given `appId` is available in the table snapshot.” Ids do not expire unless `delta.setTransactionRetentionDuration` is set (default none, DOCS/table-properties.mdx:18).

## 2 Change Data Feed

- **Enable.** Table property `delta.enableChangeDataFeed = true` in `CREATE TABLE ... TBLPROPERTIES` or `ALTER TABLE ... SET TBLPROPERTIES`; for every new table in a session, `spark.databricks.delta.properties.defaults.enableChangeDataFeed = true`. Off by default and not retroactive. READ DOCS/delta-change-data-feed.mdx:14, 24-54, 63: “Only changes made _after_ you enable the change data feed are recorded; past changes to a table are not captured.”
- **Which operations record change files.** READ DOCS/delta-change-data-feed.mdx:68: “Delta Lake records change data for `UPDATE`, `DELETE`, and `MERGE` operations in the `_change_data` folder under the Delta table directory.” and “insert-only operations and full partition deletes will not generate data in the `_change_data` directory.” For such versions the reader derives the changes from the data files, READ PROTO:650: “If a version has no `cdc` action, then the data in `add` and `remove` actions are read as inserted and deleted rows, respectively.”
- **Read, SQL.** `SELECT * FROM table_changes('tableName', 0, 10)`, also with timestamp strings; `table_changes_by_path(...)` for path tables (DOCS/delta-change-data-feed.mdx:85-97).
- **Read, DataFrame options.** `.option("readChangeFeed", "true")` plus `startingVersion`/`endingVersion` or `startingTimestamp`/`endingTimestamp`; start and end are inclusive; omit the end to read up to the latest version (lines 74, 104-130). Timestamp format `yyyy-MM-dd[ HH:mm:ss[.SSS]]` (line 76).
- **Extra columns.** `_change_type` with the values `insert`, `update_preimage`, `update_postimage`, `delete`; `_commit_version` (long); `_commit_timestamp` (timestamp). READ lines 253-257.
- **How long it is kept; VACUUM.** READ line 70: “The files in the `_change_data` folder follow the retention policy of the table.” The next sentence says running VACUUM also deletes change data feed data. Line 286: “Change records follow the same retention policy as out-of-date table versions, and will be cleaned up through VACUUM if they are outside the specified retention period.” INFERENCE (UNVERIFIED): a change read also needs the JSON commit files of the range, because checkpoints “must not preserve” change data actions (PROTO:2183, link markup removed), so `delta.logRetentionDuration` bounds it too.
- **Stated limitations.** (a) A start before the feed was enabled is an error (line 78). (b) A version or timestamp past the last commit raises `timestampGreaterThanLatestCommit` unless `spark.databricks.delta.changeDataFeed.timestampOutOfRange.enabled` is true (lines 223-237). (c) The schema used is that of the latest table version (line 242). (d) With column mapping, a range that spans a non-additive schema change fails (lines 262-276). (e) Delta 1.2.1 or below can no longer write the table (line 61). (f) Row-tracking fields cannot be read from the feed (DOCS/delta-row-tracking.mdx:183).
- **Protocol.** Writer version 4, reader version 1 (DOCS/versioning.mdx:107); as a table feature it is `changeDataFeed`, writers only (PROTO:2571). It is not in the list of droppable features (DOCS/delta-drop-feature.mdx:27-37).

## 3 Retention and how far time travel reaches

- **Defaults.** `delta.logRetentionDuration` = `interval 30 days`; `delta.deletedFileRetentionDuration` = `interval 1 week`. READ DOCS/table-properties.mdx:15 and 13; DOCS/delta-batch.mdx:886 and 890 (which writes the second as `interval 7 days`).
- **What each one controls.** Log, READ DOCS/delta-batch.mdx:888: “Each time a checkpoint is written, Delta automatically cleans up log entries older than the retention interval.” Data, line 890: “controls how long ago a file must have been deleted _before being a candidate for_ `VACUUM`”. Data files are never removed automatically, only by `VACUUM`, and `VACUUM` never removes log files (line 880; DOCS/delta-utility/index.mdx:14, 24).
- **How far time travel reaches.** READ DOCS/delta-batch.mdx:878: “To time travel to a previous version, you must retain _both_ the log and the data files for that version.” Line 882: “By default you can time travel to a Delta table up to 30 days old unless you have:” run `VACUUM`, or changed the two retention properties (lines 884-890). After a vacuum, the ability to reach “a version older than the retention period is lost after running `vacuum`.” (DOCS/delta-utility/index.mdx:29-30). Edge case, lines 894-903: log cleanup can make versions inside the interval unreachable when the entries before a checkpoint are gone.
- **Long-term history.** The docs do not warn against long retention. They say a large log retention “should not impact performance as operations against the log are constant time” while history operations get more expensive (DOCS/delta-batch.mdx:888), that keeping deleted files longer “may cause your storage costs to go up” (line 892), and they show an archive clone with both properties at `'3650 days'` (DOCS/delta-utility/index.mdx:849-861). For a permanent record they point at a table fed from the change feed, READ DOCS/delta-change-data-feed.mdx:18: “Capture the change data feed as a Delta table provides perpetual storage and efficient query capability to see all changes over time”.
- **Details from the source, not in the docs.** Interval strings: months “and years are not accepted. You may specify '365 days' for a year instead.” (SRC/DeltaConfig.scala:452-453). `delta.enableExpiredLogCleanup` default `true` (SRC/DeltaConfig.scala:533-539). `delta.checkpointRetentionDuration` default `interval 2 days` (lines 466-477).
- **VACUUM guard.** A retention under 7 days is refused unless `spark.databricks.delta.retentionDurationCheck.enabled` is `false` (DOCS/delta-utility/index.mdx:110-119). `VACUUM` skips directories whose name starts with `_` (lines 20-23).
- **Streams.** A stream that lags past the log retention loses data without failing (DOCS/delta-streaming/index.mdx:43-49).

## 4 Concurrency control

- **Model.** Optimistic concurrency in three steps: read, write, validate and commit; a conflicting writer fails with an exception (DOCS/concurrency-control.mdx:15-19).
- **Write-conflict table** (READ DOCS/concurrency-control.mdx:25-29; “Compaction” means a rewrite with the option `dataChange` set to `false`, line 23):

| | INSERT | UPDATE, DELETE, MERGE INTO | COMPACTION |
|---|---|---|---|
| INSERT | Cannot conflict | | |
| UPDATE, DELETE, MERGE INTO | Can conflict | Can conflict | |
| COMPACTION | Cannot conflict | Can conflict | Can conflict |

- **Isolation levels and the default.** The docs in this clone have no isolation-level section. The only mentions are DOCS/index.md:12 (“Serializable isolation levels ensure that readers never see inconsistent data.”) and the `isolationLevel` column of `DESCRIBE HISTORY` (DOCS/delta-utility/index.mdx:210; the example rows show `Serializable`). From the source: the table property `delta.isolationLevel` defaults to `Serializable` and accepts nothing else. READ SRC/DeltaConfig.scala:805-816: comment “Delta currently supports one isolation level: Serializable.” (wrapped over lines 807-808), validation `_ == Serializable`, message “must be Serializable”. The code defines three levels (Serializable, WriteSerializable, SnapshotIsolation; SRC/isolationLevels.scala:37, 54, 70) and line 75 has `val DEFAULT = WriteSerializable`, but a commit takes its level from the table property (SRC/util/TransactionHelper.scala:88-90), and commits that change no data are downgraded to SnapshotIsolation (SRC/OptimisticTransaction.scala:2934-2943). So WriteSerializable cannot be selected in open-source Delta, and the “Can conflict” cell for INSERT against UPDATE/DELETE/MERGE applies.
- **Avoiding conflicts.** READ DOCS/concurrency-control.mdx:33: “whether the two operations will conflict depends on whether they operate on the same set of files. You can make the two sets of files disjoint by partitioning the table by the same columns as those used in the conditions of the operations.” Partitioning alone is not enough for MERGE: the partition values must be written into the merge condition (lines 43-83), because otherwise “the condition is not explicit enough and can scan the entire table and can conflict with concurrent operations updating any other partitions.” (line 63). The fix shown adds `t.date = '<date>' AND t.country = '<country>'` to the condition (line 72).
- **Exceptions.** ConcurrentAppendException, ConcurrentDeleteReadException, ConcurrentDeleteDeleteException, MetadataChangedException, ConcurrentTransactionException (two streaming queries on one checkpoint), ProtocolChangedException, which also occurs “When multiple writers are writing to an empty path at the same time.” (lines 39-107).
- **Other stated conflict sources.** Changing a table property conflicts with concurrent writes (DOCS/delta-batch.mdx:1977-1982). An identity column “disables concurrent transactions” (DOCS/delta-batch.mdx:497-499).

## 5 MERGE

- **Several source rows match one target row.** The merge fails. READ DOCS/delta-update.mdx:589-599: “A `merge` operation can fail if multiple rows of the source dataset match and the merge attempts to update the same rows of the target Delta table.” Error class `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE`: “Cannot perform Merge as multiple source rows matched and attempted to modify the same target row in the Delta table in possibly conflicting ways.” (ERRJSON:2432-2435). One exception in the source: no error when the only matched clause is a single unconditional DELETE (SRC/commands/MergeIntoCommandBase.scala:266-281). The docs' remedy is to reduce the source to the latest change per key first (example at DOCS/delta-update.mdx:956-963).
- **Insert-only merge for deduplication.** Section “Data deduplication when writing into Delta tables”, DOCS/delta-update.mdx:726-841. Pattern (Python, lines 745-749): `deltaTable.alias("logs").merge(newDedupedLogs.alias("newDedupedLogs"), "logs.uniqueId = newDedupedLogs.uniqueId").whenNotMatchedInsertAll().execute()`. Two conditions: “The dataset containing the new logs needs to be deduplicated within itself.” (line 784), and for speed bound the target with a date range on a date-partitioned table (lines 787-838). Downstream streaming stays possible “because an insert-only merge only appends new data to the Delta table” (line 841). Note: the first SQL tab (lines 733-739) already carries the 7-day predicate while the Python and Scala tabs beside it do not.
- **SCD Type 2 example.** Section “Slowly changing data (SCD) Type 2 operation into Delta tables”, DOCS/delta-update.mdx:843-937 (Python at 852-891). Target schema `(customerId, address, current, effectiveDate, endDate)`. Pattern: (1) join the updates to the current target rows whose value changed; (2) build the staged source as those rows with `NULL as mergeKey`, unioned with all updates with `customerId as mergeKey`; (3) `MERGE ... ON customers.customerId = mergeKey`; (4) `WHEN MATCHED AND customers.current = true AND customers.address <> staged_updates.address` set `current = false` and `endDate = staged_updates.effectiveDate`; (5) `WHEN NOT MATCHED` insert the new row with `current = true` and `endDate = null`. The NULL merge key is what sends the new version of an existing key into the insert branch.
- **Schema evolution in MERGE.** Off by default. Turn it on per statement with SQL `MERGE WITH SCHEMA EVOLUTION INTO ...` or the builder call `.withSchemaEvolution()` (Delta 3.2.0+), or session-wide with `spark.databricks.delta.schema.autoMerge.enabled` (DOCS/delta-update.mdx:615-641). Version trap, line 640: the SQL clause “is honored by Delta Lake 4.3.0 and above”; on 4.0.0 through 4.2.x “the statement is accepted but the clause has no effect”. Effect: new source columns are added to the target; target columns missing in the source are left unchanged on update and set to NULL on insert (lines 619-620). The docs advise against the session-wide switch (DOCS/delta-batch.mdx:1917).
- **WHEN NOT MATCHED BY SOURCE.** Updates or deletes target rows that have no source row; builder APIs since Delta 2.3, SQL since 2.4 (DOCS/delta-update.mdx:408-416). READ line 416: “We recommend adding an optional conditional clause to avoid fully rewriting the target table.” Such a clause cannot reference source columns (line 587).
- **Clause rules.** Several `whenMatched` clauses are evaluated in order and all but the last need a condition (line 540); unspecified insert columns get NULL (line 562). Since Delta 2.2 the source is materialized automatically, so a non-deterministic source is safe (lines 389-406).
- **Performance and conflicts.** Put partition predicates in the match condition; “it will also reduce the chances of conflicts with other concurrent operations” (lines 704-716).

## 6 Table properties useful here

- **`delta.appendOnly`** (default `false`). READ DOCS/table-properties.mdx:8: “If append-only, existing records cannot be deleted, and existing values cannot be updated.” Protocol wording, PROTO:2389-2390: “New log entries MUST NOT change or remove data from the table.” and “New log entries may rearrange data (i.e. `add` and `remove` actions where `dataChange=false`).”, so compaction stays legal. Error text on a violation: “This table is configured to only allow appends.” (ERRJSON:294-296). Session default for new tables: `spark.databricks.delta.properties.defaults.appendOnly` (DOCS/delta-batch.mdx:684-688).
- **`delta.checkpointInterval`.** Not in the docs: the property reference (DOCS/table-properties.mdx:8-19) lists 12 properties and this is not one of them. Source: default `10`, comment “How often to checkpoint the delta log.” (SRC/DeltaConfig.scala:479-485).
- **`delta.dataSkippingNumIndexedCols`** (default `32`; `-1` means all columns). READ DOCS/table-properties.mdx:12: “Updating this property does not automatically collect statistics again”. Long string columns should sit after this index (DOCS/optimizations-oss/index.mdx:113).
- **`delta.dataSkippingStatsColumns`.** Not in the docs. Source: a comma-separated column list; “If present, it takes precedences over dataSkippingNumIndexedCols config” (SRC/DeltaConfig.scala:678-705).
- **`delta.targetFileSize`.** Not a property of open-source Delta: absent from DOCS and from SRC/DeltaConfig.scala (a search of the clone finds the word only as a local variable in three test files). The OPTIMIZE target is the session conf `spark.databricks.delta.optimize.maxFileSize`, internal, default 1 GiB (SRC/sources/DeltaSQLConf.scala:2629-2635); files below `optimize.minFileSize`, also 1 GiB, are the candidates (lines 2618-2627).
- **Auto compaction** (Delta 3.1.0+). Table property `delta.autoOptimize.autoCompact` or session conf `spark.databricks.delta.autoCompact.enabled`. READ DOCS/optimizations-oss/index.mdx:87: “Auto compaction occurs after a write to a table has succeeded and runs synchronously on the cluster that has performed the write.” Target 128 MB (line 102); it fires only when a partition has enough small files (`spark.databricks.delta.autoCompact.minNumFiles`, source default 50, SRC/sources/DeltaSQLConf.scala:435-441).
- **Optimized writes** (Delta 3.1.0+). READ DOCS/optimizations-oss/index.mdx:224: “The optimized write feature is **disabled** by default.” Enable with table property `delta.autoOptimize.optimizeWrite`, session conf `spark.databricks.delta.optimizeWrite.enabled`, or writer option `optimizeWrite` (lines 226-228); bin size default 512MiB (line 232). It adds a shuffle before the write (line 212).
- **Setting properties.** Use `TBLPROPERTIES` in `CREATE` or `ALTER`; any `delta.<conf>` can be defaulted for new tables through `spark.databricks.delta.properties.defaults.<conf>` (DOCS/delta-batch.mdx:676-688). Changing a property is itself a write that conflicts with concurrent writes (lines 1977-1982).

## 7 Generated columns and identity columns

- **Generated columns: support.** Supported; the page still labels them “This feature is new and is in Preview.” (DOCS/delta-batch.mdx:330). MERGE works with them “when you set `spark.databricks.delta.schema.autoMerge.enabled` to true” (line 405).
- **Generated columns: syntax.** The docs show only the DeltaTable builder: Python `.addColumn("eventDate", "DATE", generatedAlwaysAs="CAST(eventTime AS DATE)")` (line 431), Scala `DeltaTable.columnBuilder(...).generatedAlwaysAs(...)` (lines 382-386). The SQL form `column_name column_type GENERATED ALWAYS AS ( generation_expr )` appears only in a source comment (SRC/GeneratedColumn.scala:54-65), not in the docs.
- **Generated columns: rules.** Values are stored (“they occupy storage”, line 396). An explicit value must satisfy `(<value> <=> <generation expression>) IS TRUE` or the write fails (line 332). No UDFs, aggregates, window functions or multi-row functions (lines 400-404). A filter on the base column becomes a partition filter when the partition column is generated by `CAST(col AS DATE)`, `YEAR`/`MONTH`/`DAY`/`HOUR`, `DATE_FORMAT`, `DATE_TRUNC`, `TRUNC` or `SUBSTRING` (lines 407-419, 451).
- **Generated columns: protocol.** Writer version 4, reader version 1 (DOCS/versioning.mdx:108); on writer version 7 the feature `generatedColumns` must be listed (PROTO:2441-2445).
- **Identity columns: support.** READ DOCS/delta-batch.mdx:502: “Delta Lake identity columns are supported in Delta Lake 3.3 and above.” Cost, lines 497-499: “Declaring an identity column on a Delta table disables concurrent transactions.”
- **Identity columns: syntax.** Python `from delta.tables import DeltaTable, IdentityGenerator`, then `.addColumn("id", dataType=LongType(), generatedAlwaysAs=IdentityGenerator(start=..., step=...))` or `generatedByDefaultAs=` (lines 507-517). The docs state “SQL APIs for identity columns are not supported yet.” (line 552), but a test in the same clone creates one in SQL: `id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 10 INCREMENT BY 2)` (`/home/user/delta-io/delta/spark/src/test/scala/org/apache/spark/sql/delta/IdentityColumnSuite.scala:594`). Treat SQL support as unconfirmed until run.
- **Identity columns: limits.** `LongType` only (line 566); values are unique but “not guaranteed to be contiguous” (line 562); no partitioning by it, no `ADD`/`REPLACE`/`CHANGE`, no update of an existing value (lines 656-661); not definable in CTAS (line 572).
- **Identity columns: protocol.** Writer version 6, reader version 1 (DOCS/versioning.mdx:110), or the feature `identityColumns` on writer version 7 (PROTO:2471-2475).

## 8 Constraints: NOT NULL and CHECK

- **NOT NULL.** Declared in the schema at `CREATE TABLE` (`id INT NOT NULL`); removed with `ALTER TABLE t CHANGE COLUMN col DROP NOT NULL`. READ DOCS/delta-constraints.mdx:27-45. A NOT NULL on a field inside a struct also constrains the parent struct; fields inside arrays or maps cannot take it (line 50).
- **CHECK.** `ALTER TABLE t ADD CONSTRAINT name CHECK (expr)` and `ALTER TABLE t DROP CONSTRAINT name`. READ line 54: “`ALTER TABLE ADD CONSTRAINT` verifies that all existing rows satisfy the constraint before adding it to the table.” The docs show no CHECK clause inside `CREATE TABLE`. Constraints are stored and shown as table properties (line 78), under the key `delta.constraints.{name}` (PROTO:2430).
- **On violation.** READ line 8: “When a constraint is violated, Delta Lake throws an `InvariantViolationException` to signal that the new data can't be added.” The whole write fails, PROTO:2439: “the write operation must fail and the table must stay unchanged.”
- **Protocol.** READ line 14: “Adding a constraint automatically upgrades the table writer protocol version.” CHECK needs writer version 3, reader version 1 (DOCS/versioning.mdx:106) and concerns writers only (line 61); on writer version 7 the feature `checkConstraints` must be listed (PROTO:2426-2428). `checkConstraints` can be dropped again (DOCS/delta-drop-feature.mdx:33).

## 9 OPTIMIZE, Z-ordering and liquid clustering

- **OPTIMIZE (compaction).** Open source since Delta 1.2.0. SQL `OPTIMIZE table_name [WHERE <partition predicate>]`; Python `DeltaTable.forPath(spark, path).optimize().executeCompaction()` (API since 2.0). READ DOCS/optimizations-oss/index.mdx:13-77. It is idempotent (line 68) and changes no data, line 79: “`OPTIMIZE` makes no data related changes to the table, so a read before and after an `OPTIMIZE` has the same results.” It does not disturb streams that read the table (line 79). Old files stay until `VACUUM`.
- **Z-ordering.** Open source since Delta 2.0.0. SQL `OPTIMIZE events [WHERE date = '2021-11-18'] ZORDER BY (eventType)`; Python `.optimize().executeZOrderBy(col)` (lines 115-161). READ line 170: “Z-Ordering is *not idempotent*.” It only helps on columns that have statistics (line 167). An error class exists for Z-ordering on a partition column (`DELTA_ZORDERING_ON_PARTITION_COLUMN`, ERRJSON:4003).
- **Liquid clustering: status.** READ DOCS/delta-clustering.mdx:11: “This feature is available in Delta Lake 3.1.0 and above.” The preview flag was removed in 3.2 (lines 198-204).
- **Liquid clustering: syntax.** `CREATE TABLE table1(col0 int, col1 string) USING DELTA CLUSTER BY (col0)` (line 40); CTAS form from 3.3 (lines 42-45); builder `.clusterBy("col0")` from 3.2 (lines 52-57); on an existing unpartitioned table `ALTER TABLE t CLUSTER BY (cols)` from 3.3 (lines 83-90); `ALTER TABLE t CLUSTER BY NONE` (line 176); `OPTIMIZE t` clusters incrementally and `OPTIMIZE t FULL` reclusters everything (lines 122-147). Enabling it does not recluster data already written (lines 98-100).
- **What cannot be combined.** READ line 27: “Clustering is not compatible with partitioning or `ZORDER`.” Errors: `DELTA_CLUSTER_BY_WITH_PARTITIONED_BY`, “Clustering and partitioning cannot both be specified.” (ERRJSON:702-704); `DELTA_CLUSTERING_WITH_ZORDER_BY`, “OPTIMIZE command for Delta table with clustering cannot specify ZORDER BY.” (ERRJSON:690-692); “ALTER TABLE CLUSTER BY cannot be applied to a partitioned table.” (ERRJSON:136-138); OPTIMIZE on a clustered table “doesn't support partition predicates” (ERRJSON:686). Protocol, PROTO:1833: “Writers must not define clustered and partitioned table at the same time.”
- **Limits and protocol.** At most 4 clustering columns, and only columns with statistics (lines 194-195). A clustered table has the writer features `clustering` and `domainMetadata`, writer version 7, reader version 1 (lines 77-80).
- **Partitioning rule of thumb** (for choosing between the two). READ DOCS/best-practices.mdx:12-13: do not partition by a high-cardinality column, and “You can partition by a column if you expect data in that partition to be at least 1 GB.”

## 10 Deletion vectors

- **Default state.** Off. They “can be enabled on Delta Lake tables” with `ALTER TABLE <table_name> SET TBLPROPERTIES('delta.enableDeletionVectors' = true)` (DOCS/delta-deletion-vectors.mdx:13, 26-32); the source default of the property is `false` (SRC/DeltaConfig.scala:620-628). The page says “This feature is in experimental support mode.” (lines 9-10).
- **Which operations use them** (once the property is on). READ lines 17-22: `SCAN` from 2.3.0; `DELETE` from 2.4.0; `UPDATE` from 3.0.0, on by default from 3.1.0; `MERGE` from 3.1.0.
- **When rows are physically removed.** By `OPTIMIZE`, by `REORG TABLE ... APPLY (PURGE)`, or by DML run with deletion vectors disabled; the old files then still need `VACUUM` (lines 45-59).
- **Reader and writer requirements.** READ PROTO:1028: “a table must have Reader Version 3 and Writer Version 7. A feature name `deletionVectors` must exist in the table's `readerFeatures` and `writerFeatures`.” Consequence, DOCS/delta-deletion-vectors.mdx:37: “After upgrading, the table will not be readable by Delta Lake clients that do not support deletion vectors.” Readers must apply existing vectors even if the property is later switched off (PROTO:1032).
- **Dropping.** `deletionVectors` is a droppable feature; the two pages disagree on the version: “In Delta Lake 3.0 and above” (DOCS/delta-deletion-vectors.mdx:39) versus “available in Delta Lake 4.0.0 and above” (DOCS/delta-drop-feature.mdx:27).

## 11 Storage: local file system, S3, concurrent processes

- **What Delta needs from storage.** Atomic visibility, mutual exclusion (“Only one writer must be able to create (or rename) a file at the final destination.”) and consistent listing (DOCS/delta-storage.mdx:8-12).
- **Local file system.** No guarantee for concurrent writers. READ DOCS/delta-storage.mdx:27-30: “Delta Lake on local file system may not support concurrent transactional writes. This is because the local file system may or may not provide atomic renames. So you should not use the local file system for testing concurrent writes.”
- **Several processes on one local table.** Not safe by anything the docs promise. In the source, a `file:` path gets the default `HDFSLogStore` (SRC/storage/DelegatingLogStore.scala:47, 63-70, 186-196), and for the local file system that store only takes a lock inside one JVM. READ STORAGE/HDFSLogStore.java:58-66: “We need to add `synchronized` for RawLocalFileSystem as its rename will not throw an exception when the target file exists.” INFERENCE (UNVERIFIED by a run): threads in one Spark driver are serialized, but two separate processes could both write the same commit file, so the plan should keep one writing process per table at a time.
- **S3, default (single driver).** READ DOCS/delta-storage.mdx:159: “concurrent writes to S3 must originate from a _single_ Spark driver in order for Delta Lake to provide transactional guarantees. This is because S3 currently does not provide mutual exclusion”. Warning, lines 162-164: “Concurrent writes to the same Delta table on S3 storage from multiple Spark drivers can lead to data loss.” Reads from many clusters are fine (lines 150-155). It needs the `hadoop-aws` jar that matches Spark's Hadoop build (line 171).
- **S3, multi-cluster.** READ line 225: “This support is new and experimental.” Set `spark.delta.logStore.s3a.impl=io.delta.storage.S3DynamoDBLogStore`, add the `delta-storage-s3-dynamodb` jar, and use a DynamoDB table keyed by `tablePath` and `fileName` (lines 241-328). It is “only safe when all writers use this `LogStore` implementation as well as the same DynamoDB table and region” (lines 230-233).
- **Not covered.** These Spark docs say nothing about S3 conditional writes. Azure storage has full guarantees for concurrent writes from multiple clusters out of the box (lines 431-433).

## 12 Structured Streaming: Delta as source and sink, change feed as a stream

- **Source basics.** `spark.readStream.format("delta").load(path)` processes the existing table and then new commits (DOCS/delta-streaming/index.mdx:18-29). Rate limits: `maxFilesPerTrigger` (default 1000) and `maxBytesPerTrigger` (lines 38-41).
- **Commits that are not appends.** READ line 53: “Structured Streaming does not handle input that is not an append and throws an exception if any modifications occur on the table being used as a source.” Options, lines 57-59: `skipChangeCommits` (recommended) skips whole commits that contain `UPDATE`, `MERGE INTO`, `DELETE` or `OVERWRITE`, so “downstream does not see rows from those commits”; `ignoreDeletes` (legacy) ignores deletes at partition boundaries; `ignoreChanges` (deprecated) re-emits rewritten files, so “Unchanged rows may still be emitted” and “Deletes are not propagated downstream.”
- **Start position.** `startingVersion` (inclusive, or `latest`) or `startingTimestamp`, never both. READ line 71: “They take effect only when starting a new streaming query.” The schema is always the latest table schema (lines 73-80).
- **What keeps a table usable as a source.** An insert-only MERGE (DOCS/delta-update.mdx:841) and `OPTIMIZE` (DOCS/optimizations-oss/index.mdx:79) do not break readers. `RESTORE` re-emits data to streams (DOCS/delta-utility/index.mdx:697-719). A stream lagging past `logRetentionDuration` drops data silently (DOCS/delta-streaming/index.mdx:43-49).
- **Sink.** `df.writeStream.format("delta").outputMode("append").option("checkpointLocation", ...).start(path)` or `.toTable(name)`; complete mode is also supported (lines 207-311). READ line 201: “The transaction log enables Delta Lake to guarantee exactly-once processing, even when there are other streams or batch queries running concurrently against the table.” Checkpoints may live under `<table>/_checkpoints` because `VACUUM` skips `_` directories (line 204). Two queries must never share a checkpoint (DOCS/concurrency-control.mdx:97-99).
- **Change feed as a stream.** `spark.readStream.format("delta").option("readChangeFeed", "true").option("startingVersion", 0).table("t")` (DOCS/delta-change-data-feed.mdx:173-190). READ line 218: without a start “the stream returns the latest snapshot of the table at the time of streaming as an `INSERT` and future changes as change data.” Rate limits and `excludeRegex` also apply (line 218).
- **MERGE from a stream.** Use `foreachBatch` (DOCS/delta-update.mdx:1020-1083) together with the idempotence options of topic 1.

## 13 Protocol: versions, table features, dropping a feature

- **Two numbers plus feature lists.** Every table has a reader protocol version and a writer protocol version; the property defaults are reader 1, writer 2 (DOCS/table-properties.mdx:16-17). From reader version 3 and writer version 7 the protocol also carries `readerFeatures` and `writerFeatures` (PROTO:167-169, 741). A writer must satisfy both sides (DOCS/versioning.mdx:47).
- **Which feature raises which version** (READ DOCS/versioning.mdx:103-122, as writer/reader): basic 2/1; CHECK constraints 3/1; change data feed 4/1; generated columns 4/1; column mapping 5/2; identity columns 6/1; deletion vectors 7/3; TimestampNTZ 7/3; V2 checkpoints 7/3; row tracking 7/3; type widening 7/3; variant 7/3. From the feature pages: liquid clustering writer 7, reader 1 (DOCS/delta-clustering.mdx:77-80); in-commit timestamps writer 7 only (PROTO:1986-1987).
- **Writer-only versus reader-and-writer features** (READ PROTO:2562-2585). Writers only: `appendOnly`, `invariants`, `checkConstraints`, `generatedColumns`, `allowColumnDefaults`, `changeDataFeed`, `identityColumns`, `rowTracking`, `domainMetadata`, `clustering`, `inCommitTimestamp`. Readers and writers: `columnMapping`, `deletionVectors`, `timestampNtz`, `v2Checkpoint`, `vacuumProtocolCheck`, `catalogManaged`; also `typeWidening` (PROTO:2035-2036) and `variantType` (PROTO:1863-1864), which the appendix table omits.
- **Upgrades are one-way.** READ DOCS/versioning.mdx:132: “Protocol version upgrades are irreversible”. The docs recommend “using the lowest protocol versions that support the Delta Lake features required for your table” (line 126). Enabling a feature upgrades the protocol by itself (examples: DOCS/delta-constraints.mdx:14; DOCS/delta-deletion-vectors.mdx:37); a manual upgrade is `ALTER TABLE t SET TBLPROPERTIES('delta.minReaderVersion' = '1', 'delta.minWriterVersion' = '3')` (line 146).
- **Can a feature be dropped?** Only some. `ALTER TABLE <table-name> DROP FEATURE <feature-name> [TRUNCATE HISTORY]`, Delta 4.0.0+ (DOCS/delta-drop-feature.mdx:10-21). Droppable list, lines 27-35: `deletionVectors`, `typeWidening-preview`, `typeWidening`, `v2Checkpoint`, `columnMapping`, `vacuumProtocolCheck`, `checkConstraints`, `inCommitTimestamp`, `checkpointProtection`. READ line 37 (link markup removed): “You cannot drop other Delta table features”. So change data feed, row tracking, clustering, generated columns and identity columns stay for good; row tracking says so itself (DOCS/delta-row-tracking.mdx:184). A drop adds the writer feature `checkpointProtection` (line 46); the `TRUNCATE HISTORY` form “removes all transaction log data older than 24 hours” and with it time travel (line 98).
- **Disagreement inside the sources.** Row tracking is listed with reader version 3 in DOCS/versioning.mdx:118, but is “Writers only” in PROTO:2575 and needs only writer version 7 in PROTO:1656-1657.

## 14 In-commit timestamps

- **What they are.** READ PROTO:1983: “The In-Commit Timestamps writer feature strongly associates a monotonically increasing timestamp with each commit by storing it in the commit's metadata.” The value is the field `inCommitTimestamp` (milliseconds since the epoch) of the `commitInfo` action, which must be the first action of the commit; it is the larger of the commit attempt time and the previous commit's value plus one millisecond (PROTO:1993-1997).
- **How to enable.** Table property `delta.enableInCommitTimestamps = true`; the table must be on writer version 7 with `inCommitTimestamp` in `writerFeatures` (PROTO:1985-1988). Source: property default `false` (SRC/DeltaConfig.scala:974-980); the feature is added automatically when the property is set and is removable (SRC/TableFeature.scala:1433-1442). Enabling it on an existing table records `delta.inCommitTimestampEnablementVersion` and `delta.inCommitTimestampEnablementTimestamp` (PROTO:1998-2000). There is no page for it in DOCS; the only mentions are DOCS/delta-catalog-managed-tables.mdx:27 and DOCS/delta-drop-feature.mdx:34.
- **How timestamps are determined without them.** From the modification time of the commit file. READ DOCS/delta-batch.mdx:740-745: “The timestamp of each version N depends on the timestamp of the log file corresponding to the version N in Delta table log. Hence, time travel by timestamp can break if you copy the entire Delta table directory to a new location. Time travel by version will be unaffected.” The source reads `fs.getFileStatus(deltaFile).getModificationTime` and then forces the sequence to increase by moving an out-of-order commit to the previous one plus 1 ms (SRC/DeltaHistoryManager.scala:195-197, 209-214, 881-884).
- **The problem they solve.** Timestamp time travel, `DESCRIBE HISTORY` and the change feed's `_commit_timestamp` stop depending on file metadata, so they survive a copy or a sync of the table. READ PROTO:2005: “readers should use the `inCommitTimestamp` as the commit timestamp for operations like time travel”; PROTO:692 says the same for `_commit_timestamp`. The FAQ's advice without them: “Remember to copy files without changing the timestamps” (DOCS/delta-faq.mdx:30).
- **How a timestamp maps to a version** (source only). The version chosen is the latest commit at or before the timestamp: “Returns the latest commit that happened at or before `time`.” (SRC/DeltaHistoryManager.scala:295). A timestamp later than the last commit is an error by default (`canReturnLastCommit: Boolean = false`, SRC/DeltaTable.scala:544-558; SRC/DeltaHistoryManager.scala:401-404): “Timestamp <providedTimestamp> is after the table's latest version (<lastCommitTimestamp>). Use a timestamp at or before <maximumTimestamp>.” (ERRJSON:3319-3321). A timestamp before the earliest kept commit is also an error (ERRJSON:3312-3315).
- **Mixed history.** For a table that enabled the feature later, versions before the enablement version still use file modification time (PROTO:2007-2013).
- **Log cleanup.** The JSON commit at the cut-off checkpoint is kept because checkpoints do not hold `commitInfo`, which in-commit timestamps need (PROTO:2366).

## 15 The VARIANT type and type widening

- **VARIANT: status.** Listed as a Delta 4.0.0 feature with writer version 7 and reader version 3 (DOCS/versioning.mdx:32, 121). There is no user page for it in DOCS; the definition is in the protocol. READ PROTO:1863-1864: “The table must be on Reader Version 3 and Writer Version 7” and “The feature `variantType` must exist in the table `protocol`'s `readerFeatures` and `writerFeatures`.” Variant shredding is still Preview (DOCS/versioning.mdx:33).
- **VARIANT: limits** (READ PROTO:1924-1934). It cannot be a partition column or a clustering column (“Variant is not a comparable data type”); it has only the `nullCount` statistic unless shredding is enabled, so no min/max data skipping on it; it cannot be the result type of a generated column but can be its input; it is allowed in CHECK constraints and with the change data feed.
- **Type widening: status.** READ DOCS/delta-type-widening.mdx:9: “This feature is available in preview in Delta Lake 3.2 and above, and fully supported in Delta Lake 4.0 and above.”
- **Type widening: use.** Enable with `'delta.enableTypeWidening' = 'true'` at create or by `ALTER TABLE` (lines 52-67), then `ALTER TABLE <table_name> ALTER COLUMN <col_name> TYPE <new_type>`; “The table schema is updated without rewriting the underlying Parquet files.” (lines 93-98). Supported: `byte`→`short`→`int`→`long`, `float`→`double`, `date`→`timestampNTZ`, wider `decimal`, and integers to `decimal` or `double` by manual command only (lines 18-28, 114). With schema evolution on, a wider incoming type widens the column automatically (lines 100-112).
- **Type widening: protocol.** READ line 47: it “sets the Delta table feature `typeWidening`, a reader/writer protocol feature”; reader version 3, writer version 7 (PROTO:2034-2036). It can be dropped with `ALTER TABLE <table_name> DROP FEATURE 'typeWidening' [TRUNCATE HISTORY]` (lines 118-138). Without it, the FAQ says “Changing a column's type or dropping a column requires rewriting the table.” (DOCS/delta-faq.mdx:50, last line).

## 16 delta-rs (from the rsdocs copies)

All from the delta-rs docs copies in RS. They carry no version stamp; they include the Python 1.0.0 and Rust 1.1.0 migration guides. Several pages use `{{ code_example(...) }}` macros, so the example code itself is not in the copies.

- **MERGE.** Supported in Rust and Python (RS/d_feature-table.md:32). API: `dt.merge(source=..., predicate="target.x = source.x", source_alias="source", target_alias="target")` followed by `when_matched_update`, `when_matched_update_all`, `when_not_matched_insert`, `when_not_matched_insert_all`, `when_matched_delete`, `when_not_matched_by_source_update`, `when_not_matched_by_source_delete`, each with an optional `predicate`, then `.execute()` (RS/d_usage_merging-tables.md:13-23, 157, 280, 391, 508-513, 598). Order matters, line 443: “when multiple match conditions are met, the first condition that matches is executed.” The source is read once by default (`streamed_exec=True`, line 676). The copies do not say what happens when several source rows match one target row, and do not describe schema evolution for merge.
- **Change data feed, read.** `DeltaTable.load_cdf` (RS/d_upgrade-guides_guide-1.0.0.md:42). The page RS/d_usage_read-cdf.md:1-12 says only: “The `delta.enableChangeDataFeed` configuration needs to be set to `true` when creating the delta table.” (line 5).
- **Change data feed, write.** Marked supported as a writer requirement (row “Version 4 | Change Data Feed | ✅”, RS/d_feature-table.md:52), and a “change data feed writer” exists (RS/d_usage_environment-variables.md:25). Which operations write change files is not stated.
- **Deletion vectors.** The copies contradict each other. RS/d_usage_delta-lake-best-practices.md:67: “Note: delta-rs doesn’t support deletion vectors yet.” RS/d_usage_querying-delta-tables.md:41-42: “The datafusion engine also reads tables the pyarrow engine cannot (column mapping, deletion vectors)”, and the same for `DeltaTable.scan` (lines 139-142). Since 1.0.0 an unsupported feature is a hard error: “DeltaLake will now raise an error if it detects unsupported features in a table.” (RS/d_upgrade-guides_guide-1.0.0.md:216-220). Reading is documented for the datafusion engine; writing them is not documented.
- **Constraints.** Add and drop are supported (RS/d_feature-table.md:36-37, 51). READ RS/d_usage_constraints.md:5: “delta-rs evaluates CHECK constraints using DataFusion SQL semantics.” Its example: `n / 2 = 3` accepts 7 in delta-rs and not in Spark. A failing row rejects the whole append (RS/d_usage_delta-lake-best-practices.md:57).
- **Generated columns.** Supported (RS/d_feature-table.md:53); expressions are evaluated with DataFusion SQL semantics, “which can differ from Spark SQL” (RS/d_usage_writing_index.md:39-45).
- **Identity columns.** Not supported: status “-” (RS/d_feature-table.md:55).
- **Liquid clustering.** No support statement. The optimize API offers only `dt.optimize.compact()` and `dt.optimize.z_order()` (RS/d_usage_managing-tables.md:65-68; RS/d_feature-table.md:30-31); the only mention of liquid clustering is a general sentence on the Dagster page (RS/d_integrations_delta-lake-dagster.md:10).
- **In-commit timestamps, row tracking, VARIANT, type widening.** Not mentioned anywhere in the copies (searched). Unknown.
- **App transactions (idempotent writes).** `Transaction(app_id, version)`, `CommitProperties(app_transactions=[...])`, `DeltaTable.transaction_version(app_id)` (RS/d_usage_writing_idempotent-writes.md:7-9). Unlike Spark, the skip is manual, line 13: “Before writing, read the latest version recorded for your application id. If it is already at or past the batch you are about to write, an earlier attempt committed it and the batch can be skipped.” A concurrent commit for the same app id is rejected with `CommitFailedError`, but only if the check and the write use the same `DeltaTable` object (lines 21-23). Merge, update and delete can record them too (line 8). `delta.setTransactionRetentionDuration` is honoured (line 35).
- **S3 and conditional writes.** For AWS S3, READ RS/d_usage_writing_writing-to-s3-with-locking-provider.md:11: “DynamoDB is the only available locking provider at the moment in delta-rs.” S3 writes need it unless `AWS_S3_ALLOW_UNSAFE_RENAME` is `true` (lines 5, 116-119); the DynamoDB scheme is compatible with Spark's when both use `s3a://` (line 61). Conditional puts are documented for Cloudflare R2 and MinIO through `aws_conditional_put: 'etag'` (RS/d_integrations_object-storage_s3-like.md:3, 207-213); the copies do not say this works on AWS S3 itself.
- **Other storage.** Local is listed as supported (RS/d_feature-table.md:11); ACID writes are “done by default when writing to all supported object stores except AWS S3” (locking-provider page, line 3); mounted storage has the opt-out `MOUNT_ALLOW_UNSAFE_RENAME` (RS/d_integrations_object-storage_special_configuration.md:19).
- **Time travel and maintenance.** `DeltaTable(path, version=2)`, `dt.load_version(1)`, `dt.load_with_datetime("2021-11-04 00:05:23.283+00:00")` (RS/d_usage_loading-table.md:173-207). `dt.vacuum()` is a dry run by default and keeps one week (RS/d_usage_managing-tables.md:15-17). History is kept 30 days by default (RS/d_usage_examining-table.md:91-97).
- **Stated as not supported.** Multi-table transactions (RS/d_how-delta-lake-works_delta-lake-acid-transactions.md:179), identity columns, credentials from `.aws/config` (RS/d_integrations_object-storage_s3.md:19). The pyarrow read engine is deprecated (RS/d_usage_querying-delta-tables.md:74-76).

## 17 Row tracking and other help for 'what did the table say at time T' and 'which rows changed'

- **Row tracking: what it gives.** Two hidden fields per row. READ DOCS/delta-row-tracking.mdx:113-116: `_metadata.row_id` (“The unique identifier of the row.”) and `_metadata.row_commit_version` (“The table version at which the row was last inserted or updated.”). A row keeps its id through `MERGE` and `UPDATE` (line 10). They must be selected explicitly: `SELECT _metadata.row_id, _metadata.row_commit_version, * FROM table_name` (lines 118-124).
- **Row tracking: enable and cost.** `delta.enableRowTracking = true` at create (Delta 3.2.0+) or by `ALTER TABLE` on an existing table (3.3.0+), which backfills and “may cause multiple new versions of the table to be created” (lines 13-16, 31, 56, 99-103). It needs writer version 7 with `rowTracking` and `domainMetadata` (PROTO:1655-1659) and may grow the table (line 107).
- **Row tracking: limits.** READ lines 183-184: “The row ids and row commit versions metadata fields cannot be accessed while reading the Change data feed.” and “Once the Row Tracking feature is added to the table it cannot be removed without recreating the table.” INFERENCE (UNVERIFIED): a filter `_metadata.row_commit_version > N` finds rows inserted or updated after version N in the current snapshot, but not deleted rows and not earlier values; the change feed gives those.
- **Time travel.** SQL `SELECT * FROM table_name TIMESTAMP AS OF timestamp_expression` and `SELECT * FROM table_name VERSION AS OF version`; reader options `timestampAsOf` and `versionAsOf` (DOCS/delta-batch.mdx:757-758, 798-799). The expression may be a string, a date, or for example `current_timestamp() - interval 12 hours`, but not a subquery (lines 764-775). To hold one version for a whole job, read the latest version from `DESCRIBE HISTORY` and pass it as `versionAsOf` (lines 809-818).
- **DESCRIBE HISTORY.** One row per commit with `version`, `timestamp`, `operation`, `operationParameters`, `readVersion`, `isBlindAppend`, `operationMetrics`, `userMetadata` (DOCS/delta-utility/index.mdx:196-213); MERGE metrics include `numTargetRowsInserted`, `numTargetRowsUpdated`, `numTargetRowsDeleted` (lines 260-271). READ line 135: “By default table history is retained for 30 days.”
- **Tagging commits.** Writer option `userMetadata` or session conf `spark.databricks.delta.commitInfo.userMetadata` stores a free string in the commit, readable in the history (DOCS/delta-batch.mdx:1448-1450). It can carry the batch or snapshot id a commit belongs to.
- **Which rows changed between versions.** The change data feed: `table_changes('t', v1, v2)` returns each changed row with `_change_type`, `_commit_version` and `_commit_timestamp` (topic 2).
- **Freezing a state.** `CREATE TABLE ... SHALLOW CLONE source VERSION AS OF v` pins a version under its own retention settings (DOCS/delta-utility/index.mdx:783, 849-861), but the clone still reads the source's data files, so a `VACUUM` of the source breaks it (lines 746-750). `RESTORE TABLE t TO VERSION AS OF v` rolls a table back and fails if the files were vacuumed (lines 626-650).
- **Timestamps.** Whether a timestamp query stays stable after a copy depends on in-commit timestamps, and a timestamp past the last commit is an error by default (topic 14).

## Test matrix

| Feature | Status | Evidence |
| --- | --- | --- |
| 1 Spark: idempotent DataFrame write with txnAppId + txnVersion | works | READ DOCS/delta-batch.mdx:1390-1406; skip rule SRC/commands/DeltaCommand.scala:379-382 |
| 1 Spark: idempotent MERGE/UPDATE/DELETE through session confs | works | READ source only (not in DOCS, not run): SRC/commands/MergeIntoCommand.scala:89; UpdateCommand.scala:101; DeleteCommand.scala:133 |
| 2 Spark: Change Data Feed (batch and stream read, UPDATE/DELETE/MERGE recorded) | works | READ DOCS/delta-change-data-feed.mdx:24-130, 253-257 |
| 3 Spark: time travel within retention (30 days log, 7 days deleted files) | works | READ DOCS/delta-batch.mdx:876-903; DOCS/table-properties.mdx:13, 15 |
| 4 Spark: isolation level other than Serializable as a table setting | fails | READ SRC/DeltaConfig.scala:805-816 ("must be Serializable"); DOCS has no isolation-level section |
| 5 Spark: MERGE incl. insert-only dedup, SCD Type 2 pattern, WHEN NOT MATCHED BY SOURCE | works | READ DOCS/delta-update.mdx:408-416, 726-841, 843-937 |
| 5 Spark: SQL clause MERGE WITH SCHEMA EVOLUTION | works | READ DOCS/delta-update.mdx:640 (honored from Delta 4.3.0; no effect on 4.0.0-4.2.x) |
| 6 Spark: delta.appendOnly | works | READ DOCS/table-properties.mdx:8; PROTO:2383-2392 |
| 6 Spark: delta.checkpointInterval and delta.dataSkippingStatsColumns | works | READ source only: SRC/DeltaConfig.scala:479-485 and 678-705; absent from DOCS/table-properties.mdx:8-19 |
| 6 Spark: delta.targetFileSize table property | fails | READ absent from DOCS and from SRC/DeltaConfig.scala; OPTIMIZE uses SRC/sources/DeltaSQLConf.scala:2629-2635 |
| 6 Spark: auto compaction and optimized writes | works | READ DOCS/optimizations-oss/index.mdx:81-103 and 204-234 (both off unless enabled) |
| 7 Spark: generated columns | works | READ DOCS/delta-batch.mdx:328-489 (labelled Preview; builder API only in docs); PROTO:2441-2450 |
| 7 Spark: identity columns | partial | READ DOCS/delta-batch.mdx:491-666 (3.3+, disables concurrent transactions, docs say no SQL API) |
| 8 Spark: NOT NULL and CHECK constraints | works | READ DOCS/delta-constraints.mdx:8-78; PROTO:2424-2439 |
| 9 Spark: OPTIMIZE and ZORDER BY | works | READ DOCS/optimizations-oss/index.mdx:13-79, 115-176 |
| 9 Spark: liquid clustering on an unpartitioned table | works | READ DOCS/delta-clustering.mdx:11, 27-147 |
| 9 Spark: liquid clustering together with PARTITIONED BY or ZORDER BY | fails | READ DOCS/delta-clustering.mdx:27; ERRJSON:690-692, 702-704; PROTO:1833 |
| 10 Spark: deletion vectors (opt-in, off by default) | works | READ DOCS/delta-deletion-vectors.mdx:8-41; SRC/DeltaConfig.scala:620-628; PROTO:1026-1032 |
| 11 Spark: concurrent writers from several processes on a local file system table | fails | READ DOCS/delta-storage.mdx:27-30; STORAGE/HDFSLogStore.java:58-66 (lock is per JVM); not run |
| 11 Spark: S3 with a single driver | works | READ DOCS/delta-storage.mdx:157-165 |
| 11 Spark: S3 multi-cluster writes with DynamoDB | partial | READ DOCS/delta-storage.mdx:223-234 ("new and experimental") |
| 12 Spark: Delta as streaming source and sink, change feed as a stream | works | READ DOCS/delta-streaming/index.mdx:16-80, 199-311; DOCS/delta-change-data-feed.mdx:168-218 |
| 13 Spark: dropping a table feature | partial | READ DOCS/delta-drop-feature.mdx:27-37 (only nine listed features; not changeDataFeed, rowTracking, clustering) |
| 14 Spark: in-commit timestamps | works | READ PROTO:1981-2013; SRC/DeltaConfig.scala:974-980; no page in DOCS; not run |
| 15 Spark: VARIANT type | works | READ DOCS/versioning.mdx:32, 121; PROTO:1857-1934; no user page in DOCS |
| 15 Spark: type widening | works | READ DOCS/delta-type-widening.mdx:9-138 |
| 17 Spark: row tracking | works | READ DOCS/delta-row-tracking.mdx:8-184 (not readable in CDF, not removable) |
| 16 delta-rs: MERGE | works | READ RS/d_feature-table.md:32; RS/d_usage_merging-tables.md:13-23, 443 |
| 16 delta-rs: change data feed read (load_cdf) | works | READ RS/d_upgrade-guides_guide-1.0.0.md:42; RS/d_usage_read-cdf.md:5 |
| 16 delta-rs: change data feed write | partial | READ RS/d_feature-table.md:52; RS/d_usage_environment-variables.md:25 (which operations write it is not stated) |
| 16 delta-rs: deletion vectors | partial | READ RS/d_usage_delta-lake-best-practices.md:67 (not supported) vs RS/d_usage_querying-delta-tables.md:41-44 (datafusion engine reads them) |
| 16 delta-rs: CHECK constraints and generated columns | works | READ RS/d_feature-table.md:36-37, 51, 53; RS/d_usage_constraints.md:5 (DataFusion semantics differ from Spark) |
| 16 delta-rs: identity columns | fails | READ RS/d_feature-table.md:55 (status '-') |
| 16 delta-rs: liquid clustering | untested | READ no support statement; only compact and z_order in RS/d_usage_managing-tables.md:65-68 |
| 16 delta-rs: in-commit timestamps, row tracking, VARIANT, type widening | untested | READ not mentioned anywhere in the RS copies |
| 16 delta-rs: app transactions for idempotent writes | works | READ RS/d_usage_writing_idempotent-writes.md:7-23 (manual check-then-write, not an automatic skip) |
| 16 delta-rs: S3 conditional writes | partial | READ RS/d_integrations_object-storage_s3-like.md:3, 207-213 (R2 and MinIO only); AWS S3 needs DynamoDB per RS/d_usage_writing_writing-to-s3-with-locking-provider.md:11 |

## Tested snippets

### 1 Spark: idempotent DataFrame write with txnAppId + txnVersion

```text
df.write.format("delta").mode("append").option("txnAppId", app_id).option("txnVersion", version).save(path)
```

### 1 Spark: idempotent MERGE/UPDATE/DELETE through session confs

```text
spark.conf.set("spark.databricks.delta.write.txnAppId", app_id); spark.conf.set("spark.databricks.delta.write.txnVersion", str(n))
```

### 2 Spark: Change Data Feed (batch and stream read, UPDATE/DELETE/MERGE recorded)

```sql
SELECT * FROM table_changes('tableName', 0, 10)
```

### 3 Spark: time travel within retention (30 days log, 7 days deleted files)

```sql
SELECT * FROM t VERSION AS OF 123
```

### 5 Spark: SQL clause MERGE WITH SCHEMA EVOLUTION

```sql
MERGE WITH SCHEMA EVOLUTION INTO target_table t USING source_table s ON t.key = s.key WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
```

### 8 Spark: NOT NULL and CHECK constraints

```sql
ALTER TABLE t ADD CONSTRAINT dateWithinRange CHECK (birthDate > '1900-01-01')
```

### 9 Spark: OPTIMIZE and ZORDER BY

```sql
OPTIMIZE events WHERE date = '2021-11-18' ZORDER BY (eventType)
```

### 9 Spark: liquid clustering on an unpartitioned table

```sql
CREATE TABLE table1(col0 int, col1 string) USING DELTA CLUSTER BY (col0)
```

### 14 Spark: in-commit timestamps

```sql
ALTER TABLE t SET TBLPROPERTIES ('delta.enableInCommitTimestamps' = 'true')
```

### 17 Spark: row tracking

```sql
SELECT _metadata.row_id, _metadata.row_commit_version, * FROM table_name
```

## Open questions

- Version drift: the Delta docs read here are master (4.5.0-SNAPSHOT). Their compatibility table ends at Delta 4.3.x with Spark 4.0.x/4.1.x (DOCS/releases.mdx:19), so the delta-spark 4.4.1 + pyspark 4.3.0 pairing is not documented. The master build lists Spark 4.0.1, 4.1.0, 4.2.0 and 4.3.0 with 4.2.0 as default (/home/user/delta-io/delta/project/CrossSparkVersions.scala:289-353). Needs a run.
- Isolation level: the docs clone has no isolation-level section and the source accepts only Serializable. Not run: whether 4.4.1 rejects delta.isolationLevel = WriteSerializable, and whether an append that lands during a MERGE on the same table really fails the MERGE with ConcurrentAppendException.
- Idempotent MERGE through spark.databricks.delta.write.txnAppId / txnVersion is in the source but not in the docs, and the confs are marked internal. Not run on 4.4.1, including whether a skipped MERGE returns silently.
- Identity columns in SQL: the docs say the SQL API is not supported (DOCS/delta-batch.mdx:552) but a test in the clone uses GENERATED ALWAYS AS IDENTITY in SQL (IdentityColumnSuite.scala:594). Not run.
- Generated columns in SQL (GENERATED ALWAYS AS (expr) inside CREATE TABLE) appear only in a source comment (SRC/GeneratedColumn.scala:54-65); the docs show only the DeltaTable builder. Not run.
- TIMESTAMP AS OF a time later than the last commit: the source suggests the error DELTA_TIMESTAMP_GREATER_THAN_COMMIT. Not run for SQL or the timestampAsOf option; this decides how 'what the warehouse knew at T' must be queried when T is after the last commit.
- Change feed lifetime: my reading that a change read also needs the JSON commit files (so logRetentionDuration bounds it) and that insert-only versions depend on the original data files surviving VACUUM is an inference from PROTO:650 and PROTO:2183, not a documented statement and not run.
- Does an insert-only MERGE succeed on a table with delta.appendOnly = true? The docs say such a merge only appends (DOCS/delta-update.mdx:841) but do not state that the append-only check accepts it.
- Local file system with more than one writing process (two Spark drivers, or Spark plus delta-rs): Spark gives no guarantee and the delta-rs copies state no explicit local-disk guarantee beyond 'all supported object stores except AWS S3'. Not run.
- Row tracking protocol: DOCS/versioning.mdx:118 says reader version 3, PROTO:2575 and PROTO:1656-1657 say writers only. Which protocol a 4.4.1 table actually gets was not checked.
- delta-rs copies: version unknown, and the code examples (read_cdf, idempotent_writes) are macros that are missing from the copies. Unknown from these docs: the load_cdf signature, whether delta-rs MERGE writes _change_data files, whether it can write deletion vectors, and whether deletalake 1.6.6 can open a table on which Spark enabled inCommitTimestamp, rowTracking, deletionVectors or changeDataFeed (the 1.0.0 guide says unsupported features raise an error).
- S3 conditional writes on AWS S3 itself: not mentioned in the Spark docs; the delta-rs copies document aws_conditional_put only for R2 and MinIO and name DynamoDB as the only locking provider for AWS S3.
- delta.targetFileSize: not an open-source Spark property. The delta-rs copies mention a default 100 MiB target_file_size (RS/d_usage_environment-variables.md:21) but do not say whether it reads the table property.
- Deletion vector drop version is stated two ways: 'Delta Lake 3.0 and above' (DOCS/delta-deletion-vectors.mdx:39) and '4.0.0 and above' (DOCS/delta-drop-feature.mdx:27).
