# R2 — delta-rs lab (deltalake 1.6.6): what works

> **Research report, not yet reviewed.** Output of the research agent `deltars_lab` in a cloud Claude Code session on Nov 13, 2026, as returned. Evidence labels: RAN = executed in that session on made-up data; READ = read at the cited file and line; DERIVED = arithmetic on values that were read; UNVERIFIED = not checked. Paths that start with /tmp/claude-0/ or /home/user/ are on that session's machine and cannot be opened from elsewhere. Repository state read: scottn66/truth-lag at 8e28012.

## Summary

delta-rs (Python deltalake 1.6.6, Python 3.12, local filesystem) can carry the whole Bronze / Silver / Gold design without Spark. All 15 building blocks were run on synthetic TruthLag-shaped data, and the recommended patterns (bronze idempotent append, silver dedup MERGE, label upsert with Change Data Feed, SCD2 in one MERGE, time-travel read, CDF read, maintenance) ran end to end in one script with exit code 0.

Six behaviours need a workaround written into the plan:
1. app_transactions are not enforced. Re-running the same (app_id, version) appended the rows again (1000 -> 2000 -> 3000 -> 4000). It is only safe when the code checks transaction_version() and writes with the same DeltaTable object.
2. Timestamp time travel resolves on the modification time of the commit files, not on the commit timestamp. On a cp -r copy every earlier timestamp silently returned version 0 (0 rows). Version numbers and history() timestamps are copy-safe.
3. With default settings, commit files older than the log retention (30 days per the docs; a 40-day-old mtime in the test) are deleted at the next automatic checkpoint, and time travel to them fails. Set delta.logRetentionDuration and delta.enableExpiredLogCleanup=false at creation.
4. A merge predicate written as "a IS DISTINCT FROM b OR c IS DISTINCT FROM d" without parentheses is parsed wrongly and silently skipped 3 real changes. Parenthesise each term.
5. MERGE does not dedup its source: an insert-only merge inserted 130 rows for 100 distinct keys, and an upsert with duplicate matching keys raises an error.
6. With pyarrow 26.0.1, files rewritten by MERGE / UPDATE / DELETE are read as string_view, and string filters on the pyarrow read path fail; a script that exits right after to_pyarrow_table aborted with exit code 134 in 5 of 8 runs. DeltaTable.scan, QueryBuilder and polars do not have either problem.

Not available in delta-rs 1.6.6: in-commit timestamps, liquid clustering, row tracking, writing deletion vectors, a streaming API. The duckdb delta extension could not be downloaded here, so delta_scan is untested.

Scale is not a concern on this machine: 5M-row build 3.6 s, MERGE of 300k label updates 1.1 s (partitioned, literal partition predicate) to 7.3 s (unpartitioned, full rewrite), z-order 7.9 s, 500k raw-JSON events appended in 1.3 to 1.6 s, peak memory at most 3.65 GB. Timings are indicative: other agents shared the 4 CPUs.

## Versions

All RAN in a uv venv at `/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/deltars_lab/venv`.

| Package | Version |
|---|---|
| Python | 3.12.3 |
| deltalake | 1.6.6 (`rust_core_version()` = `py-1.6.6`, commits carry `engineInfo: delta-rs:py-1.6.6`) |
| pandas | 2.3.3 |
| pyarrow | 26.0.1 |
| polars | 2.1.0 (polars-runtime-32 2.1.0) |
| duckdb | 2.0.0 |
| numpy | 2.5.4 |
| arro3-core | 0.9.1 (deltalake returns its `RecordBatchReader` / `Table` types) |

A second venv (`venv_pa17`) with deltalake 1.6.6 + pyarrow 17.0.0 + pandas 2.3.3 was used for one check only (the string_view problem).

Storage: local filesystem only. Machine: 4 CPUs, 15 GB RAM, shared with other agents while the timings were taken.

The local docs clone (`.../scratchpad/wf_dl/verify_demo/dl/rsdocs/`) is newer than 1.6.6 in places. RAN: `to_pandas(engine='datafusion')` gives `TypeError: DeltaTable.to_pandas() got an unexpected keyword argument 'engine'`, and the documented `dt.load_version(1)` / `dt.load_with_datetime(...)` give `AttributeError`. In 1.6.6 the names are `DeltaTable(path, version=n)`, `load_as_version(int | str | datetime)` and `scan(columns, predicate)`.

## Recommended patterns

The code below is the content of `/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/deltars_lab/patterns.py`. RAN end to end, exit code 0, output in `out/patterns.txt`:
- bronze: `written`, then `skipped`, 1000 rows.
- silver: inserted 1000 then 0; a batch with 100 in-batch duplicates gave 1000 rows, 1000 distinct meta_id.
- labels: inserted 100; second snapshot updated 35; re-run updated 0 and made no commit; CDF from the second commit = 35 update_preimage + 35 update_postimage.
- time travel: 20 reverted at the first version, 25 now; `version_at` returned the right version; `snapshot` custom metadata visible in `history()`.
- SCD2: first load inserted 3; change run updated 2 and inserted 3 in one commit; re-run 0 / 0 and no commit; 4 current rows for 4 pages (one title was NULL on purpose).
- maintenance: compact, z_order, checkpoint, vacuum dry run.

```python
import datetime as dt
import polars as pl
import pyarrow as pa
from deltalake import CommitProperties, DeltaTable, Transaction, write_deltalake
from deltalake.exceptions import CommitFailedError

# ---- 0. table properties (set at creation) ----
KEEP_HISTORY = {
    "delta.logRetentionDuration": "interval 3650 days",        # default 30 days: old commits are deleted at checkpoints
    "delta.deletedFileRetentionDuration": "interval 3650 days",  # makes an accidental vacuum(retention_hours=..) fail
    "delta.enableExpiredLogCleanup": "false",
}
BRONZE_PROPS = {**KEEP_HISTORY, "delta.appendOnly": "true", "delta.dataSkippingStatsColumns": "meta_id,meta_dt,wiki_id,page_id,rev_id"}
SILVER_PROPS = {**KEEP_HISTORY}
GOLD_PROPS = {**KEEP_HISTORY, "delta.enableChangeDataFeed": "true"}


def ensure_table(path, schema, props, partition_by=None, name=None):
    return DeltaTable.create(path, schema=schema, partition_by=partition_by, name=name, configuration=props, mode="ignore")


# ---- 1. bronze: idempotent append ----
def bronze_append(path, data, app_id, version, meta=None, retries=3):
    """Append once per (app_id, version). The check and the write use the SAME DeltaTable object."""
    for _ in range(retries):
        t = DeltaTable(path)
        last = t.transaction_version(app_id)
        if last is not None and last >= version:
            return "skipped"
        try:
            write_deltalake(
                t,
                data,
                mode="append",
                commit_properties=CommitProperties(app_transactions=[Transaction(app_id=app_id, version=version)], custom_metadata=meta),
            )
            return "written"
        except CommitFailedError:
            continue  # someone else committed: reload and check again
    raise RuntimeError(f"bronze_append gave up after {retries} tries")


# ---- 2. silver: insert-only MERGE (dedup on meta_id) ----
def silver_insert_new(path, batch):
    src = pl.from_arrow(batch).unique(subset=["meta_id"], keep="first", maintain_order=True)  # MERGE does not dedup the source
    if src.height == 0:
        return {"num_target_rows_inserted": 0}
    days = ", ".join(f"'{d}'" for d in sorted({str(d) for d in src["event_date"].to_list()}))  # literal partition filter -> pruning
    return (
        DeltaTable(path)
        .merge(src, f"t.meta_id = s.meta_id AND t.event_date IN ({days})", source_alias="s", target_alias="t")
        .when_not_matched_insert_all()
        .execute()
    )


# ---- 3. gold: label upsert, change rows only for real changes ----
LABEL_CHANGED = "(t.is_reverted IS DISTINCT FROM s.is_reverted) OR (t.reverting_rev_id IS DISTINCT FROM s.reverting_rev_id)"  # keep the parentheses


def label_upsert(path, labels, meta=None):
    src = pl.from_arrow(labels).unique(subset=["wiki_db", "rev_id"], keep="last", maintain_order=True)  # duplicate keys make MERGE fail
    return (
        DeltaTable(path)
        .merge(src, "t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id", source_alias="s", target_alias="t", commit_properties=CommitProperties(custom_metadata=meta))
        .when_matched_update_all(predicate=LABEL_CHANGED)
        .when_not_matched_insert_all()
        .execute()
    )


# ---- 4. gold: dim_page SCD Type 2 in ONE merge ----
PAGE_CHANGED = "((t.title IS DISTINCT FROM s.title) OR (t.namespace IS DISTINCT FROM s.namespace))"


def scd2_merge(path, incoming):
    """incoming: one row per page_id with page_id, title, namespace, valid_from, valid_to=NULL, is_current=true."""
    inc = pl.from_arrow(incoming).unique(subset=["page_id"], keep="last", maintain_order=True)
    cur = pl.from_arrow(read_table(path, columns=["page_id", "title", "namespace"], predicate="is_current = true"))
    cur = cur.with_columns(pl.lit(True).alias("_has_cur"))  # marker: do NOT test title_cur for NULL, titles can be NULL
    j = inc.join(cur, on="page_id", how="left", suffix="_cur")
    changed = j.filter(
        pl.col("_has_cur").is_not_null()
        & (pl.col("title").ne_missing(pl.col("title_cur")) | pl.col("namespace").ne_missing(pl.col("namespace_cur")))  # null-safe, same as IS DISTINCT FROM
    ).select(inc.columns)
    staged = pl.concat(
        [
            inc.with_columns(pl.col("page_id").alias("merge_key")),            # closes the old row, or inserts a new page
            changed.with_columns(pl.lit(None, dtype=pl.Int64).alias("merge_key")),  # NULL key never matches -> inserted as the new current row
        ]
    )
    return (
        DeltaTable(path)
        .merge(staged, "t.page_id = s.merge_key AND t.is_current = true", source_alias="s", target_alias="t")
        .when_matched_update(updates={"valid_to": "s.valid_from", "is_current": "false"}, predicate=PAGE_CHANGED)
        .when_not_matched_insert(updates={"page_id": "s.page_id", "title": "s.title", "namespace": "s.namespace", "valid_from": "s.valid_from", "valid_to": "s.valid_to", "is_current": "true"})
        .execute()
    )


# ---- 5. reads: current, time travel, change data ----
def _plain(t):
    """DataFusion returns string_view / binary_view; many pyarrow kernels (count_distinct, ==) do not take them."""
    if pa.types.is_string_view(t):
        return pa.string()
    if pa.types.is_binary_view(t):
        return pa.binary()
    if pa.types.is_list(t) or pa.types.is_large_list(t) or pa.types.is_list_view(t):
        return pa.list_(_plain(t.value_type))
    return t


def to_plain(tbl):
    return tbl.cast(pa.schema([pa.field(f.name, _plain(f.type), f.nullable) for f in tbl.schema]))


def read_table(path, columns=None, predicate=None, version=None):
    """DataFusion scan -> pyarrow Table with plain string columns. version=None is the latest."""
    return to_plain(pa.table(DeltaTable(path, version=version).scan(columns=columns, predicate=predicate)))


def version_at(path, ts):
    """Latest version committed at or before ts, from commitInfo timestamps (file mtimes are NOT used)."""
    ms = int(ts.timestamp() * 1000)
    ok = [h["version"] for h in DeltaTable(path).history() if h["timestamp"] <= ms]
    return max(ok) if ok else None


def read_changes(path, starting_version, ending_version=None, columns=None, predicate=None):
    return to_plain(pa.table(DeltaTable(path).load_cdf(starting_version=starting_version, ending_version=ending_version, columns=columns, predicate=predicate)))


# ---- 6. maintenance ----
def maintain(path, zorder_cols=None, partition_filters=None):
    t = DeltaTable(path)
    out = {"compact": t.optimize.compact(partition_filters=partition_filters)}
    if zorder_cols:
        out["z_order"] = DeltaTable(path).optimize.z_order(zorder_cols, partition_filters=partition_filters)
    DeltaTable(path).create_checkpoint()
    out["vacuum_would_delete"] = len(DeltaTable(path).vacuum())  # dry run only: a real vacuum breaks time travel and CDF
    return out
```

Notes for the plan (each RAN unless marked):
- **Bronze app_id.** One app_id per source file with version 1 (for example `file:page_change_2026-10-20T00.ndjson.gz`), or one app_id per stream with an increasing batch number. delta-rs does not check that versions increase: a lower version was accepted and then `transaction_version` returned the lower number. Markers survive checkpoints. `custom_metadata` keys appear at the top level of each `history()` entry.
- **Marker with MERGE.** `commit_properties` with `app_transactions` works on `merge`, but a merge that changes nothing makes no commit, so the marker is not recorded. An empty append with the marker does commit. If Silver needs a per-batch marker, write it with an empty append or keep a small control table.
- **Silver partition predicate.** The literal `IN (...)` list is what prunes files with the default `streamed_exec=True`. `t.event_date = s.event_date` prunes only with `streamed_exec=False`.
- **Label upsert.** One run is 0 or 1 commit. Without `LABEL_CHANGED` a re-run rewrote the file and produced 120 preimage + 120 postimage change rows for identical values.
- **SCD2.** The staged source must be computed from the current table inside the same run; re-using an old staged source inserted the changed rows twice. A two-merge variant (close changed rows, then insert rows with no current row) gives identical rows and is also idempotent, but it is two commits: between them the changed pages have no current row.
- **CDF read.** `load_cdf(starting_version=n)` beyond the latest version raises `Invalid table version: 99`; pass `allow_out_of_range=True` to get 0 rows instead.
- **Rebuildable partitions.** `write_deltalake(path, day_rows, mode="overwrite", predicate="event_date = '2026-09-01'")` replaced one partition, was idempotent on re-run (row count stable) and rejected rows outside the predicate. Each run makes a commit and delete + insert change rows. It is refused on an appendOnly table.
- **`ensure_table` with mode="ignore"** returns an existing table unchanged; it does not update properties.
- UNVERIFIED: `delta.dataSkippingStatsColumns` in `BRONZE_PROPS` names page_change columns; other streams need their own list.

## Pitfalls

Ordered by how much damage they can do. RAN unless marked.

1. **Timestamp time travel uses file modification times.** `history()[i]['timestamp']` equals `commitInfo.timestamp`, but `load_as_version(datetime)` resolves on the mtime of `_delta_log/*.json`. After `cp -r` (mtimes = copy time) every earlier timestamp returned version 0 with 0 rows and no error. After `cp -a` it was correct. After `os.utime` on two commit files the answer followed the fake mtimes. A timestamp before the first commit also returns version 0 silently. Use version numbers, or `version_at()` (same answer on the original and on the cp -r copy). `load_cdf(starting_timestamp=...)` was not affected by the copy.
2. **Default log retention ends time travel.** With default properties, commit files with a 40-day-old mtime were deleted at the next automatic checkpoint; `DeltaTable(path, version=1)` then failed with `_internal.TableNotFoundError: Generic delta kernel error: No files in log segment` and `history()` listed only the remaining versions. READ `d_usage_examining-table.md:95-97`: history is kept 30 days by default. With `delta.logRetentionDuration='interval 3650 days'` + `delta.enableExpiredLogCleanup='false'` nothing was deleted. `PostCommitHookProperties(cleanup_expired_logs=False)` also works but must be passed on every write.
3. **app_transactions do not make a write idempotent by themselves.** Same (app_id, version) again: appended again, whether the same object, a path string or a fresh object was passed. Rejection happens only for a writer whose snapshot is older than a commit with the same app_id, and only if it passes that DeltaTable object: `_internal.CommitFailedError: Failed to commit transaction: Concurrent transaction failed.` Passing the path string in that situation duplicated the batch.
4. **IS DISTINCT FROM precedence.** `t.a IS DISTINCT FROM s.a OR t.b IS DISTINCT FROM s.b` is logged in the commit as `t.is_reverted IS DISTINCT FROM (s.is_reverted OR t.reverting_rev_id IS DISTINCT FROM s.reverting_rev_id)`. With 3 rows going from reverted to not reverted it updated 0 rows. With parentheses it updated 3.
5. **MERGE and duplicate source keys.** Insert-only: both copies are inserted. With a matched clause: `MERGE matched a target row with multiple source rows that satisfy duplicate relevant WHEN MATCHED clauses (file: ..., row ordinal in file: 1)`.
6. **string_view after MERGE / UPDATE / DELETE (pyarrow 26.0.1).** Files written by these three operations read back as `string_view` in pyarrow (files from append, compact and z_order read as `string`). Then `to_pyarrow_table(filters=[('snapshot','=','b')])`, `to_pandas(filters=...)`, `to_pyarrow_dataset().to_table(filter=...)`, duckdb over the registered dataset and `pq.read_table(filters=...)` fail with `pyarrow.lib.ArrowNotImplementedError: Function 'equal' has no kernel matching input types (string, string_view)`. Reading without a string filter works. The same files read as `string` and filter correctly with pyarrow 17.0.0. `DeltaTable.scan`, QueryBuilder and polars `scan_delta` work. Their results also carry `string_view`, and `pc.count_distinct` fails on it (`Function 'count_distinct' has no kernel matching input types (string_view)`), hence `to_plain()` in the patterns.
7. **Abort at interpreter exit.** A script whose last action was `DeltaTable(...).to_pyarrow_table(...)` on a 500k-row table ended with `terminate called without an active exception`, exit code 134, in 5 of 8 runs (2 of 8 when the read was inside a function). 0 of 8 with a 0.5 s pause after the read, with QueryBuilder, polars, `to_pandas`, a native pyarrow filesystem (`SubTreeFileSystem(path, LocalFileSystem())`) or `to_pyarrow_dataset().to_table(use_threads=False)`. The data and commits were complete each time; only the exit code is wrong. Root cause UNVERIFIED (looks timing dependent). Two such aborts are recorded in `out/t13_phase2.txt`.
8. **`filters=` with a date partition needs a `datetime.date`.** `filters=[('event_date','=','2026-10-21')]` fails: `Function 'equal' has no kernel matching input types (date32[day], string)`. `partitions=[...]` takes strings but prints `DeprecationWarning: partitions is deprecated; use filters instead`.
9. **Concurrent writers.** Any two merges that touch the same partition conflict, even insert-only merges with different keys: `_internal.CommitFailedError: Failed to commit transaction: Commit failed: a concurrent transactions added new data. Help: This transaction's query must be rerun to include the new data. Also, if you don't care to require this check to pass in the future, the isolation level can be set to Snapshot Isolation.` An append from a stale DeltaTable object after a merge fails with `Commit failed: a concurrent transaction deleted data this operation read.` Plan one writer per table, or retry on a fresh `DeltaTable(path)`.
10. **Vacuum.** After `vacuum(retention_hours=0, enforce_retention_duration=False, dry_run=False)`, an old version still opens and `count()` still answers (from log statistics), but reading fails: `FileNotFoundError: Object at location .../part-00000-...snappy.parquet not found`. `load_cdf` from an old version fails too, because plain-append versions are served from the data files. `vacuum(full=True)` also deletes `_change_data` files.
11. **Lenient casting and schema_mode='merge'.** Numeric strings into a long column, int32 into long, and nanosecond timestamps into the microsecond column were accepted silently (nanoseconds truncated). After a `schema_mode='merge'` append the partition column moved to the end of the schema, and after one from a pandas frame `meta_dt` and `event_date` lost NOT NULL. Prefer an Arrow table built with the declared schema and `alter.add_columns` for new columns.
12. **Table properties are not validated.** `'3650 days'` (no `interval`) and `delta.checkpointInterval='0'` were accepted. Unknown or custom keys raise `Kernel: Generic delta kernel error: Error parsing property 'truthlag.layer':'bronze'` unless `raise_if_not_exists=False`.
13. **appendOnly is not a full lock.** `restore(1)` succeeded on an appendOnly table and removed data; compact, z_order and vacuum are allowed; anyone can set the property back to false.
14. **CDF details.** Enable it at creation: on a table where it was enabled later, `load_cdf(starting_version=0)` fails with `Reading a table version: 0 that does not have change data enabled`. `load_cdf` returns an arro3 `RecordBatchReader` with no `.to_pandas()`; wrap it in `pa.table(...)`. `pl.from_arrow(reader)` returns a Series, not a DataFrame; use `pl.DataFrame(reader)`. `_commit_timestamp` is `timestamp[ms]` without a time zone.
15. **Unpartitioned MERGE rewrites everything it touches.** 300k random label updates rewrote all 5M rows each time and the folder grew from 198 MB to 428 MB to 661 MB (old files and change data are kept). Partition the big tables and put a literal partition predicate in the ON clause.
16. **Constraints.** The violation message does not name the constraint. Expressions are stored rewritten in DataFusion form: `event_date = CAST(meta_dt AS DATE)` became `event_date = arrow_cast(meta_dt, 'Date32')`. READ `d_usage_constraints.md:5`: constraint semantics are DataFusion's and can differ from Spark. Whether Spark accepts the rewritten text is UNVERIFIED.
17. **Time zones.** A tz-naive timestamp into a tz-aware column fails: `_internal.CommitFailedError: Table features must be specified, please specify: TimestampWithoutTimezone`. A new table with a tz-naive column becomes `timestamp_ntz` with protocol 3 / 7. Keep every timestamp `timestamp[us, tz=UTC]`.
18. **SCD2 change detection must be null-safe on both sides.** A first version of the staged-source code used `title_cur IS NOT NULL` as the test for an existing current row. With a NULL title the old row was closed but the new row was only inserted on the next run. The pattern above uses a marker column and `ne_missing`.
19. **duckdb.** `INSTALL delta` fails here: `IO Error: Failed to download extension "delta" at URL "http://extensions.duckdb.org/v2.0.0/linux_amd64/delta.duckdb_extension.gz" ... (ERROR Could not establish connection)`. Use `con.register(name, DeltaTable(path).to_pyarrow_dataset())` (subject to pitfall 6 for string filters) or `read_parquet(dt.file_uris(), hive_partitioning=true)`.
20. **Smaller ones.** `optimize.z_order` refuses partition columns. `max_commit_retries=0` makes even two plain appends collide (`Failed to commit transaction: 0`). QueryBuilder has no JSON functions (`Invalid function 'json_get_str'`) and cannot insert. pandas turns a nullable int32 column into float64 and a nullable bool into object.

## Performance

RAN, one process per stage, wall time from `time.perf_counter`, peak memory from `resource.getrusage(...).ru_maxrss` (`/usr/bin/time` is not installed here). Other agents were using the same 4 CPUs, so treat the times as indicative. Outputs: `out/t13_phase1.txt`, `out/t13_phase2.txt`, `out/t13_phase3.txt`.

Slim-shaped table: 5,000,000 rows, 12 string columns (the names in `config.HISTORY_SLIM_COLUMNS`).

| Stage | Wall | Peak RSS | Result |
|---|---|---|---|
| Build, unpartitioned, streamed from Parquet, CDF on | 3.59 s | 1,443 MB | 2 files, 198 MB (snappy) |
| Build, partitioned by event_date (30 days) | 3.16 s | 2,022 MB | 30 files, 212 MB |
| MERGE 300k label updates, random keys, unpartitioned, streamed_exec=True | 7.02 s | 2,261 MB | 299,597 updated, 4,700,403 copied: every file rewritten |
| Same, streamed_exec=False | 7.34 s | 2,430 MB | every file rewritten |
| MERGE 300k updates in a narrow id range, after z-order by page_id | 4.42 s | 1,983 MB | every file rewritten |
| MERGE 300k updates inside 3 days, partitioned, no partition literal, streamed_exec=True | 3.50 s | 3,555 MB | 3 of 30 files rewritten |
| Same, streamed_exec=False | 1.81 s | 859 MB | 3 files rewritten |
| Same, default streamed_exec, ON clause with `t.event_date BETWEEN DATE '2026-09-08' AND DATE '2026-09-10'` | 1.08 s | 881 MB | 3 files rewritten |
| Insert-only dedup MERGE, 300k source rows (200k new), unpartitioned | 1.61 s (1.88 s with streamed_exec=False) | 3,514 MB (3,650 MB) | 200,000 inserted, nothing rewritten |
| `optimize.z_order(['page_id'])` | 7.86 s | 1,499 MB | 3 files to 2, 142 MB |
| `optimize.compact()` after the merges | 0.17 s | 250 MB | 2 small files to 1 |
| `to_pandas`, 3 columns of all 5M rows | 2.00 s | 2,547 MB | |

Filtered read of one page (548 rows of 5M):

| Reader | Before z-order | After z_order(page_id) |
|---|---|---|
| `to_pyarrow_table(filters=...)` | 1.32 s | 0.12 s |
| polars `scan_delta().filter()` | 0.35 s | 0.10 s |
| duckdb over `to_pyarrow_dataset()` | 0.26 s | 0.13 s |
| QueryBuilder `count(*) where page_id = ...` | 0.12 s | 0.04 s |

A lookup of 10 revision_id values took 0.06 s before and 0.15 s after the z-order by page_id (the table was naturally ordered by revision_id before). A full group-by over 5M rows took 0.04 to 0.07 s in QueryBuilder and 0.08 to 0.09 s in polars.

Bronze: 500,000 raw-JSON events, average 1,557 characters, 778.5 MB of JSON, 3 date partitions, appended in one call.

| Compression | Wall | Peak RSS | Files | Table size |
|---|---|---|---|---|
| snappy (default) | 1.27 s | 2,942 MB | 6 | 441.8 MB |
| ZSTD level 3 | 1.62 s | 2,718 MB | 3 | 187.0 MB |

Reading one day (166,274 rows): two small columns 0.03 to 0.04 s; the raw_json column 0.24 s (snappy) or 0.35 s (zstd), 259.5 MB in Arrow.

Memory depends on the source of the append: the same 500k-event append peaked at 1,897 MB when fed from `pq.ParquetFile.iter_batches`, 2,866 MB from a pyarrow dataset scanner and 3,307 MB from a whole in-memory table. Appending one hourly file at a time keeps it lower.

Disk growth: the unpartitioned table folder reached 1,016 MB after 4 merges and a z-order (old file versions are kept, `_change_data` 67 MB). The partitioned one reached 348 MB after 3 merges (`_change_data` 69 MB).

The highest peak in the whole lab was 3.65 GB.

UNVERIFIED: the synthetic raw_json is built from 2,000 template bodies plus a random tail per row, so the compression ratios may not match real events. Label upserts larger than 300k rows were not measured.

## Documented limitations (T15)

Docs = local clone in `/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/wf_dl/verify_demo/dl/rsdocs/`.

| Topic | Docs (READ) | Tested here (RAN) | Consequence |
|---|---|---|---|
| Deletion vectors | `d_usage_delta-lake-best-practices.md:67`: "Note: delta-rs doesn't support deletion vectors yet." `d_usage_querying-delta-tables.md:42` says the DataFusion read path can read such tables, but that page describes an `engine=` argument 1.6.6 does not have. | `alter.add_feature(TableFeatures.DeletionVectors, allow_protocol_versions_increase=True)` is accepted, but `delete()` still rewrote the file (add + remove, no deletionVector). | Every update or delete rewrites whole files. Design for partition-sized rewrites. |
| Liquid clustering | Not in the feature table (`d_feature-table.md:22-56` lists compaction and Z-order only). The only mention is a marketing bullet in `d_integrations_delta-lake-dagster.md:10`. | `delta.clusteringColumns` rejected: `Error parsing property 'delta.clusteringColumns':'rev_id'`. | Use partitioning plus `optimize.z_order`. |
| Generated columns | `d_feature-table.md:53` supported. `d_usage_writing_index.md:37-48`: evaluated with DataFusion SQL semantics, which can differ from Spark (integer division, concat with NULL). | `event_date` generated as `CAST(meta_dt AS DATE)` was filled on append and on insert-only MERGE; wrong supplied values were rejected. Protocol 1 / 4. | Usable. Computing event_date in the ETL and adding a CHECK constraint is the engine-neutral option. |
| Column mapping | `d_feature-table.md:54,60` supported. | Create with `delta.columnMapping.mode=name` gave protocol 2 / 5 and physical names `col-<uuid>`; append and read worked. | Not needed. It raises the protocol. |
| Streaming | No Structured Streaming equivalent is documented: a search for `structured streaming`, `readStream`, `writeStream` over the 58 pages has no hits. `d_usage_writing_idempotent-writes.md:3` describes batch retries and stream consumers that call the writer themselves. | Not applicable. | delta-rs is batch only. Micro-batches = `write_deltalake` or `merge` plus app_transactions; incremental reads = `load_cdf`. |
| Change data feed | `d_usage_read-cdf.md:5`: the property "needs to be set to true when creating the delta table". `d_feature-table.md:52` supported. | Written for merge, update, delete and partition overwrite; read with `load_cdf` only. | Enable at creation. Vacuum can destroy it. |
| In-commit timestamps | Not mentioned anywhere in the docs. | `Error parsing property 'delta.enableInCommitTimestamps':'true'` at create and at alter. Forced with `raise_if_not_exists=False` the key is stored but ignored: no inCommitTimestamp in the commit, protocol stays 1 / 2. | Not available. Timestamp time travel stays tied to file mtimes (pitfall 1). |
| Row tracking, identity columns | `d_feature-table.md:55`: identity columns not supported. | `delta.enableRowTracking` rejected with the same parse error. | Not available. |
| Unsupported features in a table | `d_upgrade-guides_guide-1.0.0.md:216-220`: since 1.0 delta-rs raises an error when it detects unsupported features. | Not tested with a Spark-written table. | UNVERIFIED: if Spark enables deletion vectors, row tracking or in-commit timestamps on a table, delta-rs 1.6.6 may refuse to work with it. |
| CHECK constraints | `d_usage_constraints.md:5`: DataFusion semantics; verify the same data passes in each engine. | See T10. | Matters only if Spark also writes. |
| Log retention | `d_usage_examining-table.md:95-97`: history kept 30 days by default, set by `delta.logRetentionDuration`. | See pitfall 2. | Set the property at creation. |
| MERGE pruning | `d_usage_merging-tables.md:676` says that with `streamed_exec=True` a pruning predicate is built while the source is read. | In 1.6.6 it was not: 5 files scanned, 0 skipped. The 1.6.6 docstring says streamed_exec "implicitly disables source table stats to derive an early_pruning_predicate". | Put the partition literal in the ON clause. |

## Evidence files and how to re-run

Folder: `/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/deltars_lab/`. Run any script from that folder with `./venv/bin/python <script>`.

| Script | Covers | Output |
|---|---|---|
| `common.py` | synthetic data and helpers | |
| `t01_04.py` | T1 to T4 | `out/t01_04.txt` |
| `t05_07.py` | T5 (stops at its T6 part on `to_pandas`; T5 output is complete) | `out/t05_07.txt` |
| `t06_07.py`, `dbg_pred.py` | T6, T7, predicate precedence | `out/t06_07.txt`, `out/dbg_pred.txt` |
| `t08.py` | T8 | `out/t08.txt` |
| `t09.py` | T9 | `out/t09.txt` |
| `t10_11.py` | T10, T11 | `out/t10_11.txt` |
| `t12_14.py` | T12, T14 | `out/t12.txt`, `out/t14.txt` |
| `t13.py`, `t13b.py` | T13 | `out/t13_phase1.txt`, `out/t13_phase2.txt`, `out/t13_phase3.txt` |
| `t_extra.py` | string_view per operation, default log retention, CDF on a copy, feature properties, SCD2 crash recovery | `out/t_extra.txt` |
| `t_final.py` | `scan`, column mapping, generated column, markers on MERGE, `version_at`, partition overwrite | `out/t_final.txt` |
| `patterns.py` | the recommended patterns, end to end | `out/patterns.txt` |

Things to know:
- `common.py`, `t01_04.py`, `t05_07.py`, `t06_07.py` and `dbg_pred.py` were left in the folder by an interrupted earlier run. I read them, re-ran all of them in this session and report only the re-run output.
- The 5M-row and 500k-event data (`scale/`, 2.7 GB) was deleted after the measurements. `t13.py gen_slim`, `t13.py build`, `t13.py gen_json` regenerate it.
- The four small scripts used to count the exit aborts were deleted with that data. The counts are from this session's run; `out/abort4.txt` holds the last set and `out/t13_phase2.txt` shows two aborts.
- The one-off pyarrow 17 check and the pandas append check were run inline and have no script.
- Nothing was written to `/home/user/truth-lag` (`git status --porcelain` was empty after the lab) or to `/home/user/delta-io`. No network use other than package installs and the failed duckdb extension download.

## Test matrix

| Feature | Status | Evidence |
| --- | --- | --- |
| T1 Create a partitioned table with explicit schema and table properties, at creation and later; read back properties and protocol | works | RAN (t01_04.py, out/t01_04.txt). DeltaTable.create with a pyarrow schema, partition_by, name, description and the 5 properties gave version 0; metadata().configuration returned all 5; protocol() = minReader 1 / minWriter 4, reader_features None, writer_features None. Arrow nullable=False is kept as NOT NULL. A plain table is 1 / 2. Setting the properties later, one commit each: appendOnly stays 1 / 2, enableChangeDataFeed moves to 1 / 4, the other three change nothing. Creating again: 'Generic error: A Delta Lake table already exists at that location.'; mode='ignore' returns the existing table. write_deltalake(..., configuration=...) also sets properties when it creates the table. Caveats: unknown or custom keys raise "Kernel: Generic delta kernel error: Error parsing property 'truthlag.layer':'bronze'" unless raise_if_not_exists=False; values are not validated ('3650 days' without 'interval' and checkpointInterval '0' were accepted). |
| T2 Idempotent append with CommitProperties(app_transactions=[Transaction(app_id, version)]) | partial | RAN (t01_04.py; t_final.py F4). After one commit with (app_id, 1), re-running the same (app_id, 1) was neither skipped nor rejected: rows went 1000 -> 2000 -> 3000 -> 4000 (same DeltaTable object, path string, fresh object). A lower version (0) was accepted too and transaction_version then returned 0. Rejection happens only when the writer's snapshot is older than a commit carrying the same app_id AND the stale DeltaTable object is passed: '_internal.CommitFailedError: Failed to commit transaction: Concurrent transaction failed.'; passing the path string in that case duplicated the batch. Different app_ids do not conflict. Read back: DeltaTable.transaction_version(app_id) -> int, or None for an unknown app; correct after create_checkpoint. Tested pattern (check, then write with the same object): written / skipped / written. A no-op MERGE with a marker makes no commit, so the marker is not stored; an empty append with a marker does commit. READ d_usage_writing_idempotent-writes.md:13-23 describes the same pattern. |
| T3 delta.appendOnly enforcement | works | RAN (t01_04.py). On an appendOnly table, delete (with and without predicate), update, write_deltalake mode='overwrite' (plain, by path, and with predicate), merge when_matched_update_all and merge when_matched_delete all fail with the same error: '_internal.CommitFailedError: The transaction includes Remove action with data change but Delta table is append-only'. Append and insert-only merge (when_not_matched_insert_all) succeed. Not blocked: optimize.compact, optimize.z_order, vacuum, restore(1) (returned {'numRemovedFile': 2, 'numRestoredFile': 2}, so it removed data), and set_table_properties({'delta.appendOnly': 'false'}), after which delete works. |
| T4 Schema enforcement on append; schema_mode='merge' | partial | RAN (t01_04.py; inline pandas check). Extra column: '_internal.SchemaMismatchError: Cannot cast schema, number of fields does not match: 8 vs 7'. Missing column, nullable or not: same error with '6 vs 7'. Wrong type with a value that cannot be cast: "_internal.DeltaError: Generic DeltaTable error: Arrow error: Cast error: Cannot cast string 'abc' to value of Int64 type". Values that can be cast are accepted silently: numeric strings into long, int32 into long, timestamp[ns] into the microsecond column. tz-naive timestamp into the tz-aware column: '_internal.CommitFailedError: Table features must be specified, please specify: TimestampWithoutTimezone'. NULL in a NOT NULL column: 'Invalid data found: 5 rows failed validation check.' Reordered columns are accepted (matched by name). A pandas DataFrame with matching columns appends directly. schema_mode='merge': an extra column is added (old rows NULL) and a missing nullable column is filled with NULL; a missing NOT NULL column still fails. Side effects seen: the partition column moved to the end of the schema, and after a merge-append from pandas meta_dt and event_date lost NOT NULL. schema_mode='overwrite' with append: 'Schema overwrite not supported for Append'. alter.add_columns(Field('ingest_run', 'string')) works. |
| T5 Insert-only MERGE for dedup on meta_id: duplicate source keys, partition pruning, metrics | partial | RAN (t05_07.py, out/t05_07.txt). execute() returns a dict: num_source_rows, num_target_rows_inserted / updated / deleted / copied, num_output_rows, num_target_files_scanned, num_target_files_skipped_during_scan, num_target_files_added / removed, execution_time_ms, scan_time_ms, rewrite_time_ms. A 300-row batch (100 existing + 200 new) inserted 200; the same batch again inserted 0 and made no commit. Duplicates inside the source are NOT removed: 130 source rows with 100 distinct new keys inserted 130 rows. Duplicated keys that already exist insert nothing. With when_matched_update_all, duplicated matching keys raise 'MERGE matched a target row with multiple source rows that satisfy duplicate relevant WHEN MATCHED clauses'. Partition pruning: 't.event_date = s.event_date' with the default streamed_exec=True pruned nothing (5 scanned, 0 skipped); the same with streamed_exec=False pruned (3 scanned, 3 skipped; the commit logs predicate "meta_id >= ... AND meta_id <= ... AND event_date = '2026-09-02'::date"). A literal in the ON clause prunes with the default: equality 4 scanned / 3 skipped; IN list and BETWEEN DATE ... AND DATE ... also prune. A polars DataFrame is accepted as source. |
| T6 Upsert MERGE on the label table with Change Data Feed; load_cdf; no-op updates | works | RAN (t06_07.py, dbg_pred.py, t_extra.py X3). With delta.enableChangeDataFeed=true, merge writes _change_data/*.parquet and a 'cdc' action; update() and delete() do too. load_cdf(starting_version=0) by (version, type): v1 insert 100 (plain append, served from the data file); v2 insert 20 + update_preimage 100 + update_postimage 100; v3 same source again without a predicate: update_preimage 120 + update_postimage 120, so no-op updates DO produce change rows and rewrite the file; v4 with the predicate: 3 + 3; v5 update(): 1 + 1; v6 delete(): delete 1. Columns: the table columns plus _change_type (string_view), _commit_version (uint64), _commit_timestamp (timestamp[ms], no time zone, equal to commitInfo.timestamp). load_cdf returns an arro3 RecordBatchReader; use pa.table(reader). Predicate that avoids no-ops: '(t.is_reverted IS DISTINCT FROM s.is_reverted) OR (t.reverting_rev_id IS DISTINCT FROM s.reverting_rev_id)': same source again gave 0 updated and no commit. Without the parentheses it is parsed as 't.is_reverted IS DISTINCT FROM (s.is_reverted OR t.reverting_rev_id IS DISTINCT FROM s.reverting_rev_id)' and missed 3 real changes. Also: columns= and predicate= work; starting_version past the end raises 'Invalid table version: 99' unless allow_out_of_range=True; starting_timestamp works; on a table created without CDF, load_cdf(starting_version=0) raises 'Reading a table version: 0 that does not have change data enabled'. |
| T7 SCD Type 2 for dim_page: (a) two merges, (b) one merge with a staged source and NULL merge key | works | RAN (t06_07.py, t_extra.py X5, patterns.py). (a) and (b) produce identical rows: page 1 untouched; pages 2 and 3 closed (valid_to = new valid_from, is_current = false) with new current rows; page 4 inserted. (b) works in delta-rs: one commit, metrics inserted 3, updated 2, copied 1. Re-run: (a) 0 / 0 and no commit; (b) with the staged source recomputed from the current table 0 / 0 and no commit; (b) with a stale staged source inserted the 2 changed rows a second time. (a) is two commits: after step 1 alone pages 2 and 3 had no current row, and a full re-run repaired it (step 1 updated 0, step 2 inserted 3). A second change later and an as-of query (valid_from <= ts AND (valid_to IS NULL OR valid_to > ts)) gave the right rows. Duplicate page_id in the incoming data that needs an update makes the MERGE fail. The change test in the staged source must be null-safe and must not use a nullable attribute as the 'has current row' test: with a NULL title an earlier version closed the row without inserting the new one until the next run. |
| T8 Time travel by version and by timestamp; which timestamp; copies; history() fields | partial | RAN (t08.py, t_extra.py X3, t_final.py F5). By version: DeltaTable(path, version=n) and load_as_version(n) gave 0 / 100 / 200 / 300 / 400 rows for versions 0 to 4. Unknown version: '_internal.DeltaError: Kernel error: Generic delta kernel error: LogSegment end version 5 not the same as the specified end version 99'. By timestamp: load_as_version(datetime or ISO string) returned the expected version on the original table. Which timestamp: history()['timestamp'] equals commitInfo.timestamp (ms), but timestamp travel resolves on the commit file's modification time. After cp -r (mtimes = copy time) the timestamps taken before commits 2, 3 and 4 all returned version 0 with 0 rows and no error. After cp -a (mtimes kept) the answers were right. After os.utime on two commit files the answer followed the fake mtimes. A timestamp before the first commit returns version 0; a future one returns the latest. Travel by version and history() timestamps were identical on the copies. load_cdf(starting_timestamp, ending_timestamp) returned the same versions on a cp -r copy. history() entry keys: timestamp, operation, operationParameters, operationMetrics, engineInfo, clientVersion, version, plus each custom_metadata key at top level (run_id, source_file, rows_in; a non-string value such as 100 is kept as a number). The docs' load_version / load_with_datetime do not exist in 1.6.6. |
| T9 Maintenance: optimize.compact, optimize.z_order, vacuum, create_checkpoint, cleanup_metadata | works | RAN (t09.py, t_extra.py X2). compact: 40 files became 2 (one per partition); partition_filters works; when there is nothing to do no commit is made. z_order on ['rev_id'], ['page_id','rev_id'] and a string column works; on the partition column: '_internal.DeltaError: Generic DeltaTable error: Z-order columns cannot be partition columns. Found: ["event_date"]'. OPTIMIZE commits have dataChange=false. vacuum() is a dry run by default and returns the file list; retention check: '_internal.DeltaError: Generic error: Invalid retention period, minimum retention for vacuum is configured to be greater than 168 hours, got 0 hours' unless enforce_retention_duration=False. A real vacuum writes two commits (VACUUM START, VACUUM END). Effect on time travel: after vacuum with retention 0, DeltaTable(path, version=3) still opens and count() still returns 1500, but reading fails with 'FileNotFoundError: Object at location .../event_date=2026-09-02/part-00000-...snappy.parquet not found'. Effect on change data: the default vacuum kept the _change_data files but removed old data files, and load_cdf(starting_version=0) then failed; vacuum(full=True) deleted the _change_data files as well and load_cdf failed for the older versions. With delta.deletedFileRetentionDuration='interval 3650 days', vacuum(retention_hours=0) is refused ('... greater than 87600 hours, got 0 hours') and vacuum() deletes nothing. Checkpoints: automatic every delta.checkpointInterval commits (5 gave v4 and v9; default gave v99); create_checkpoint() works; PostCommitHookProperties(create_checkpoint=False) turns the automatic one off. Log cleanup runs with each automatic checkpoint: on a default table, commit files with a 40-day-old mtime were deleted and time travel to v1 failed ('_internal.TableNotFoundError: Generic delta kernel error: No files in log segment'). With logRetentionDuration 3650 days + enableExpiredLogCleanup=false all commits stayed. cleanup_metadata() does the same on demand. |
| T10 CHECK constraints via alter.add_constraint | works | RAN (t10_11.py, t_final.py F3). add_constraint({'rev_id_positive': 'rev_id > 0'}) makes an 'ADD CONSTRAINT' commit and stores configuration 'delta.constraints.rev_id_positive'. Protocol goes from 1 / 2 to 1 / 3; a table that already has CDF is 1 / 4 and stays there. A violation on append, merge or update raises: '_internal.DeltaError: Generic DeltaTable error: External error: Invalid data found: 1 rows failed validation check.' followed by 'Preview of invalid data:' and a table of the bad rows; the constraint name is not in the message. Adding a constraint that existing rows violate fails the same way ('51 rows failed validation check'). Same name with another expression: "Cannot add constraint 'rev_id_positive': a constraint with this name already exists with a different expression. Existing: 'rev_id > 0', New: 'rev_id > 1'". Several constraints in one call work. drop_constraint works; a missing name raises "Constraint with name 'nope' does not exist." Expressions are stored rewritten: 'is_reverted = false OR reverting_rev_id IS NOT NULL' became 'NOT is_reverted OR reverting_rev_id IS NOT NULL'; 'event_date = CAST(meta_dt AS DATE)' became "event_date = arrow_cast(meta_dt, 'Date32')" and rejected 20 rows with a wrong event_date. |
| T11 Two writers on the same version: append vs append, merge vs merge, append vs merge | works | RAN (t10_11.py): deterministic tests (A and B load the same version, B commits, then A commits) and real 2-process races released by a barrier, 4 repetitions each. append vs append: both commit. merge vs merge (upsert on the same rows, updates of different rows in one file, insert-only with different keys, insert-only with the same keys): the first commits, the second fails with "_internal.CommitFailedError: Failed to commit transaction: Commit failed: a concurrent transactions added new data." then on a new line "Help: This transaction's query must be rerun to include the new data. Also, if you don't care to require this check to pass in the future, the isolation level can be set to Snapshot Isolation." append then merge: the merge fails with the same message (in the real race the append won all 4 times). merge then an append from a stale DeltaTable object: the append fails with 'Commit failed: a concurrent transaction deleted data this operation read.' Partitioned table, insert-only merges with a literal partition predicate: different partitions both commit; the same partition conflicts. Retry: running the operation again on a fresh DeltaTable(path) succeeded in every case; for insert merges with the same keys the retry inserted 0 rows, so no duplicates. CommitProperties(max_commit_retries=0) makes even two appends collide: 'Failed to commit transaction: 0'; with the default they both pass. No option was found that retries a merge automatically after a logical conflict. |
| T12 Readers: pandas with partition filters, polars, duckdb, deltalake SQL (QueryBuilder), DeltaTable.scan | partial | RAN (t12_14.py, t_extra.py X1 / X4, t_final.py F1, inline pyarrow 17 check). pandas: to_pandas(filters=[('event_date','=', datetime.date(2026,9,2))], columns=[...]) works; row filters on int columns work; dtypes are datetime64[us, UTC], date as object; types_mapper=pd.ArrowDtype works. A string value for the date column in filters= fails ("Function 'equal' has no kernel matching input types (date32[day], string)"); partitions=[...] takes strings but is deprecated. polars 2.1.0: read_delta, scan_delta (version=, a DeltaTable object, partition filter pushed down to one file) and write_delta work. duckdb 2.0.0: the delta extension cannot be downloaded here ('IO Error: Failed to download extension "delta" at URL "http://extensions.duckdb.org/v2.0.0/linux_amd64/delta.duckdb_extension.gz" ... (ERROR Could not establish connection)'), so delta_scan is untested; con.register(name, dt.to_pyarrow_dataset()) and read_parquet(dt.file_uris(), hive_partitioning=true) work, including json_extract_string on raw_json. QueryBuilder().register(name, dt).execute(sql) returns a RecordBatchReader; group by, window functions and joining two versions of a table work; no JSON functions ("Invalid function 'json_get_str'") and no INSERT. DeltaTable.scan(columns, predicate) works, also on old versions. Two defects on the pyarrow path with pyarrow 26.0.1: string filters fail on files rewritten by merge / update / delete ("Function 'equal' has no kernel matching input types (string, string_view)"; fine with pyarrow 17.0.0), and a process that exits right after to_pyarrow_table aborted with exit code 134 in 5 of 8 runs. |
| T13 Scale sanity: 5M-row slim-shaped table, MERGE of 300k label updates, z-order, filtered read, 500k raw-JSON events | works | RAN (t13.py, t13b.py; out/t13_phase1.txt, t13_phase2.txt, t13_phase3.txt). Build 5M rows x 12 string columns: 3.59 s, peak 1,443 MB, 2 files, 198 MB. MERGE of 300k label updates into it: 7.02 s / 2,261 MB (streamed_exec=True) and 7.34 s / 2,430 MB (False); both rewrote all 5M rows (299,597 updated, 4,700,403 copied). Partitioned by event_date (30 partitions), 300k updates inside 3 days: 3.50 s / 3,555 MB with no partition literal and streamed_exec=True; 1.81 s / 859 MB with streamed_exec=False; 1.08 s / 881 MB with a literal BETWEEN on event_date; 3 of 30 files rewritten each time. Insert-only dedup merge of 300k rows (200k new): 1.61 s, 3,514 MB. z_order(['page_id']): 7.86 s, 1,499 MB. Filtered read of one page (548 rows): 1.32 s before and 0.12 s after the z-order with pyarrow filters; 0.12 s and 0.04 s with QueryBuilder. to_pandas of 3 columns x 5M rows: 2.0 s, 2,547 MB. Append of 500,000 raw-JSON events (average 1,557 characters, 778.5 MB): 1.27 s, 2,942 MB, table 441.8 MB with snappy; 1.62 s, 2,718 MB, table 187.0 MB with ZSTD level 3. Full table in the Performance section. |
| T14 Types and statistics: UTC timestamps, list<string>, nulls, long strings, min/max on raw_json | works | RAN (t12_14.py T14, t_extra.py X4). timestamp[us, tz=UTC] round-trips exactly (…56.123456 and the next microsecond). Nanosecond input is truncated to microseconds without an error (…123456789 ns stored as …123456). A value in America/Los_Angeles is stored as the same instant in UTC. list<string> (including None and an empty list), nulls in bool / int32 / double / date, NaN, a 200,000-character string and non-ASCII JSON all round-trip. A tz-naive timestamp column becomes timestamp_ntz and the table protocol 3 / 7 with features ['timestampNtz']. In pandas a nullable int32 column comes back float64 and a nullable bool as object. Statistics: by default the log has minValues / maxValues / nullCount for raw_json too, cut to 64 characters (the Parquet footer statistic is also 64 characters). delta.dataSkippingStatsColumns='meta_id,meta_dt,wiki_id,page_id,rev_id' removes them (commit file 2,319 -> 1,877 bytes for 2 data files). delta.dataSkippingNumIndexedCols counts non-partition columns: 5 excludes raw_json, 6 keeps it, 0 writes no column statistics, -1 keeps all. Set later, it applies to new files only. WriterProperties(statistics_truncate_length=32) shortens the footer statistic to 32. 3,000 events on disk: 2.65 MB with snappy, 1.17 MB with ZSTD level 3. |
| T15 Documented limitations that matter here (deletion vectors, liquid clustering, generated columns, column mapping, streaming, change data feed, in-commit timestamps) | partial | READ + RAN; details and file:line citations in the section 'Documented limitations (T15)'. Supported and tested: change data feed (must be enabled at creation per d_usage_read-cdf.md:5), generated columns (d_feature-table.md:53; DataFusion semantics per d_usage_writing_index.md:37-48), column mapping (d_feature-table.md:54). Not available: writing deletion vectors (d_usage_delta-lake-best-practices.md:67 'delta-rs doesn't support deletion vectors yet'; RAN: delete still rewrites the file), liquid clustering (not in d_feature-table.md; property rejected), in-commit timestamps (not in the docs; property rejected), row tracking (property rejected), identity columns (d_feature-table.md:55), any streaming API (no hits in the docs). Since 1.0, delta-rs raises an error on tables with unsupported features (d_upgrade-guides_guide-1.0.0.md:216-220). |
| Extra: DeltaTable.scan(columns, predicate) as the default reader | works | RAN (t_final.py F1, patterns.py). Signature in 1.6.6: scan(self, columns=None, predicate=None) -> RecordBatchReader. Works with a string predicate on files rewritten by MERGE (50 rows), with a date partition predicate written as a string literal, on an old version (DeltaTable(path, version=1).scan(...)) and on a column-mapped table. String columns come back as string_view: .to_pandas() gives object columns, but pc.count_distinct fails on string_view, so cast to string first. |
| Extra: partition overwrite with a predicate (replaceWhere) for rebuildable partitions | works | RAN (t_final.py F6). write_deltalake(mode='overwrite', predicate="event_date = '2026-09-01'") replaced that partition only (table 164 rows, 60 in the partition) and gave the same counts on a second run. Rows outside the predicate are rejected: 'Invalid data found: 5 rows failed validation check.' Each run makes a commit; with CDF on it writes delete + insert change rows (96 delete + 60 insert, then 60 + 60). On an appendOnly table it is refused (T3). |
| Extra: generated column event_date = CAST(meta_dt AS DATE) | works | RAN (t_extra.py X3, t_final.py F3). A Field with metadata {'delta.generationExpression': 'CAST(meta_dt AS DATE)'} gives protocol 1 / 4. Appending without the column filled it correctly (23:59 UTC -> 2026-09-08, 00:01 UTC -> 2026-09-09); an insert-only MERGE without the column also filled it (0 nulls in 100 rows); supplying wrong values is rejected ('Invalid data found: 2 rows failed validation check.'). |
| Extra: in-commit timestamps (delta.enableInCommitTimestamps) | fails | RAN (t08.py, t_extra.py X3). At create and at alter: "_internal.DeltaError: Kernel: Generic delta kernel error: Error parsing property 'delta.enableInCommitTimestamps':'true'". Forced with raise_if_not_exists=False the key is stored in the configuration but ignored: protocol stays 1 / 2 and the next commit's commitInfo has no inCommitTimestamp. Do not force it. |
| Extra: duckdb delta_scan | untested | RAN: INSTALL delta and delta_scan both fail because the extension cannot be downloaded in this container: '_duckdb.IOException: IO Error: Failed to download extension "delta" at URL "http://extensions.duckdb.org/v2.0.0/linux_amd64/delta.duckdb_extension.gz" ... (ERROR Could not establish connection)'. Behaviour of delta_scan on these tables is UNVERIFIED. |

## Tested snippets

### T1 Create a partitioned table with explicit schema and table properties, at creation and later; read back properties and protocol

```text
t = DeltaTable.create(path, schema=EVENT_SCHEMA, partition_by=["event_date"], name="bronze_page_change",
    description="raw page_change events, append only", mode="ignore",
    configuration={"delta.appendOnly": "true", "delta.enableChangeDataFeed": "true",
                   "delta.logRetentionDuration": "interval 3650 days",
                   "delta.deletedFileRetentionDuration": "interval 3650 days",
                   "delta.checkpointInterval": "10"})
t.alter.set_table_properties({"delta.checkpointInterval": "10"})                      # later
t.alter.set_table_properties({"truthlag.layer": "bronze"}, raise_if_not_exists=False)  # custom key
md = t.metadata(); print(md.name, md.partition_columns, md.configuration)
p = t.protocol(); print(p.min_reader_version, p.min_writer_version, p.reader_features, p.writer_features)
```

### T2 Idempotent append with CommitProperties(app_transactions=[Transaction(app_id, version)])

```python
def bronze_append(path, data, app_id, version, meta=None, retries=3):
    for _ in range(retries):
        t = DeltaTable(path)
        last = t.transaction_version(app_id)
        if last is not None and last >= version:
            return "skipped"
        try:
            write_deltalake(t, data, mode="append",   # pass t, not the path
                commit_properties=CommitProperties(
                    app_transactions=[Transaction(app_id=app_id, version=version)],
                    custom_metadata=meta))
            return "written"
        except CommitFailedError:
            continue
    raise RuntimeError("gave up")
```

### T3 delta.appendOnly enforcement

```text
DeltaTable.create(path, schema=EVENT_SCHEMA, partition_by=["event_date"], configuration={"delta.appendOnly": "true"})
write_deltalake(path, batch, mode="append")     # ok
DeltaTable(path).delete("rev_id < 1000100")    # CommitFailedError: ... Delta table is append-only
```

### T4 Schema enforcement on append; schema_mode='merge'

```text
tbl = pa.Table.from_pandas(pdf, schema=EVENT_SCHEMA, preserve_index=False)   # declared schema, NOT NULL kept
write_deltalake(path, tbl, mode="append")                                    # strict: same column set
DeltaTable(path).alter.add_columns(Field("ingest_run", "string"))            # explicit way to add a column
write_deltalake(path, with_extra_col, mode="append", schema_mode="merge")    # works, but see side effects
```

### T5 Insert-only MERGE for dedup on meta_id: duplicate source keys, partition pruning, metrics

```text
src = pl.from_arrow(batch).unique(subset=["meta_id"], keep="first", maintain_order=True)
days = ", ".join(f"'{d}'" for d in sorted({str(d) for d in src["event_date"].to_list()}))
m = (DeltaTable(path)
     .merge(src, f"t.meta_id = s.meta_id AND t.event_date IN ({days})", source_alias="s", target_alias="t")
     .when_not_matched_insert_all()
     .execute())
m["num_target_rows_inserted"], m["num_target_files_skipped_during_scan"]
```

### T6 Upsert MERGE on the label table with Change Data Feed; load_cdf; no-op updates

```text
CHANGED = "(t.is_reverted IS DISTINCT FROM s.is_reverted) OR (t.reverting_rev_id IS DISTINCT FROM s.reverting_rev_id)"
m = (DeltaTable(path)
     .merge(src, "t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id", source_alias="s", target_alias="t")
     .when_matched_update_all(predicate=CHANGED)
     .when_not_matched_insert_all()
     .execute())
cdf = pa.table(DeltaTable(path).load_cdf(starting_version=2, ending_version=2,
               columns=["rev_id", "is_reverted", "_change_type", "_commit_version"],
               predicate="_change_type = 'update_postimage' AND is_reverted = true"))
```

### T7 SCD Type 2 for dim_page: (a) two merges, (b) one merge with a staged source and NULL merge key

```text
# (b) one merge; staged = every incoming row with merge_key = page_id, plus the CHANGED rows again with merge_key = NULL
(DeltaTable(path)
 .merge(staged, "t.page_id = s.merge_key AND t.is_current = true", source_alias="s", target_alias="t")
 .when_matched_update(updates={"valid_to": "s.valid_from", "is_current": "false"},
      predicate="((t.title IS DISTINCT FROM s.title) OR (t.namespace IS DISTINCT FROM s.namespace))")
 .when_not_matched_insert(updates={"page_id": "s.page_id", "title": "s.title", "namespace": "s.namespace",
      "valid_from": "s.valid_from", "valid_to": "s.valid_to", "is_current": "true"})
 .execute())
# full function scd2_merge() is in the Recommended patterns section
```

### T8 Time travel by version and by timestamp; which timestamp; copies; history() fields

```python
t = DeltaTable(path, version=3)                 # or: t = DeltaTable(path); t.load_as_version(3)
rows = pa.table(t.scan(columns=["rev_id"]))

def version_at(path, ts):                        # copy-safe: uses commitInfo timestamps, not file mtimes
    ms = int(ts.timestamp() * 1000)
    ok = [h["version"] for h in DeltaTable(path).history() if h["timestamp"] <= ms]
    return max(ok) if ok else None

write_deltalake(path, data, mode="append",
    commit_properties=CommitProperties(custom_metadata={"run_id": "run-4", "source_file": "f4.ndjson.gz"}))
[(h["version"], h["timestamp"], h["operation"], h.get("run_id")) for h in DeltaTable(path).history()]
```

### T9 Maintenance: optimize.compact, optimize.z_order, vacuum, create_checkpoint, cleanup_metadata

```text
t = DeltaTable(path)
t.optimize.compact(partition_filters=[("event_date", "=", "2026-09-01")])
t.optimize.z_order(["rev_id"])
t.create_checkpoint()
t.cleanup_metadata()            # deletes commits older than delta.logRetentionDuration
t.vacuum()                      # dry run: returns the files it would delete
t.vacuum(retention_hours=0, enforce_retention_duration=False, dry_run=False)   # deletes; breaks time travel and CDF
```

### T10 CHECK constraints via alter.add_constraint

```text
DeltaTable(path).alter.add_constraint({"rev_id_positive": "rev_id > 0"})
DeltaTable(path).alter.add_constraint({"reverted_has_reverter": "is_reverted = false OR reverting_rev_id IS NOT NULL"})
DeltaTable(path).metadata().configuration        # {'delta.constraints.rev_id_positive': 'rev_id > 0', ...}
DeltaTable(path).alter.drop_constraint("rev_id_positive")
```

### T11 Two writers on the same version: append vs append, merge vs merge, append vs merge

```python
for attempt in range(5):
    try:
        result = run_merge(DeltaTable(path))    # build the whole operation again on a fresh snapshot
        break
    except CommitFailedError:
        continue
else:
    raise RuntimeError("merge kept conflicting")
```

### T12 Readers: pandas with partition filters, polars, duckdb, deltalake SQL (QueryBuilder), DeltaTable.scan

```text
pdf = DeltaTable(path).to_pandas(filters=[("event_date", "=", dt.date(2026, 9, 2))], columns=["meta_id", "rev_id"])
lf = pl.scan_delta(path).filter(pl.col("event_date") == dt.date(2026, 9, 2)).select("meta_id", "rev_id")
old = pl.read_delta(path, version=1, columns=["rev_id"])
tbl = pa.table(DeltaTable(path).scan(columns=["rev_id"], predicate="event_date = '2026-09-02' AND rev_id < 10010"))
agg = pa.table(QueryBuilder().register("bronze", DeltaTable(path)).execute(
    "select event_date, count(*) as c from bronze group by event_date order by event_date"))
con = duckdb.connect(); con.register("bronze_ds", DeltaTable(path).to_pyarrow_dataset())
con.execute("select event_date, count(*) from bronze_ds group by 1").fetchall()
```

### T13 Scale sanity: 5M-row slim-shaped table, MERGE of 300k label updates, z-order, filtered read, 500k raw-JSON events

```text
m = (DeltaTable(path)
     .merge(src, "t.revision_id = s.revision_id AND t.event_date BETWEEN DATE '2026-09-08' AND DATE '2026-09-10'",
            source_alias="s", target_alias="t")
     .when_matched_update(
         updates={"revision_is_identity_reverted": "s.revision_is_identity_reverted",
                  "revision_first_identity_reverting_revision_id": "s.revision_first_identity_reverting_revision_id",
                  "revision_seconds_to_identity_revert": "s.revision_seconds_to_identity_revert"},
         predicate="(t.revision_is_identity_reverted IS DISTINCT FROM s.revision_is_identity_reverted) OR "
                   "(t.revision_first_identity_reverting_revision_id IS DISTINCT FROM s.revision_first_identity_reverting_revision_id)")
     .execute())
DeltaTable(path).optimize.z_order(["page_id"])
```

### T14 Types and statistics: UTC timestamps, list<string>, nulls, long strings, min/max on raw_json

```text
DeltaTable.create(path, schema=EVENT_SCHEMA, partition_by=["event_date"],
    configuration={"delta.dataSkippingStatsColumns": "meta_id,meta_dt,wiki_id,page_id,rev_id"})
write_deltalake(path, data, mode="append",
    writer_properties=WriterProperties(compression="ZSTD", compression_level=3))
# stats written per file: json.loads(add_action["stats"])["minValues"].keys()
```

### Extra: DeltaTable.scan(columns, predicate) as the default reader

```text
tbl = pa.table(DeltaTable(path, version=None).scan(columns=["rev_id", "snapshot"], predicate="snapshot = 'b'"))
tbl = tbl.cast(pa.schema([pa.field(f.name, pa.string() if pa.types.is_string_view(f.type) else f.type, f.nullable) for f in tbl.schema]))
```

### Extra: partition overwrite with a predicate (replaceWhere) for rebuildable partitions

```text
write_deltalake(path, day_rows, mode="overwrite", predicate="event_date = '2026-09-01'")
```

### Extra: generated column event_date = CAST(meta_dt AS DATE)

```text
sch = Schema([Field("meta_id", "string", nullable=False), Field("meta_dt", "timestamp", nullable=False),
              Field("event_date", "date", nullable=True, metadata={"delta.generationExpression": "CAST(meta_dt AS DATE)"}),
              Field("rev_id", "long")])
DeltaTable.create(path, schema=sch, partition_by=["event_date"])
```

### Extra: duckdb delta_scan

```text
con = duckdb.connect(); con.register("t", DeltaTable(path).to_pyarrow_dataset())   # works here instead
```

## Open questions

- Spark interop was not tested in this lab: can delta-spark 4.4.1 read and write the tables delta-rs creates (protocol 1/2 to 1/4, _change_data files, constraints stored in DataFusion form such as arrow_cast(meta_dt, 'Date32')), and does delta-rs 1.6.6 refuse a table once Spark enables deletion vectors, row tracking or in-commit timestamps on it?
- string_view: pyarrow 17.0.0 reads the files rewritten by MERGE / UPDATE / DELETE as string and pyarrow 26.0.1 as string_view. Which pyarrow release changed this, and whether a newer deltalake writes these files differently, is unverified. The plan has to choose: read through DeltaTable.scan / QueryBuilder / polars (tested), or pin pyarrow.
- The exit abort (exit code 134 right after to_pyarrow_table) has no confirmed root cause; the evidence is only that a pause or a non-pyarrow read path made it disappear in 8 of 8 runs each.
- Only the local filesystem was tested. Concurrency and commit behaviour on an object store (the docs describe a locking provider for S3) are unverified.
- Timestamp time travel depends on file modification times. Whether the project's copy step from the VPS keeps them is not known to me; version-based travel avoids the question.
- load_as_version with a tz-naive datetime gave the same result as the UTC-aware one, but this machine's time zone is UTC, so whether naive values are read as UTC or as local time is unverified.
- Real page_change events may compress differently from the synthetic JSON (2,000 template bodies plus a random tail), so the 441.8 MB (snappy) and 187.0 MB (ZSTD) figures for 500k events are indicative only.
- Label upserts larger than 300k rows and merges with a source too big for memory (max_spill_size, max_temp_directory_size) were not measured.
- The duckdb delta extension could not be downloaded here, so delta_scan is untested.
- Python 3.13 (the machine default) was not tested; the lab used a Python 3.12 venv as instructed.
