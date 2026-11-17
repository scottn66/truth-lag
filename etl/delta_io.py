"""Small delta-rs helpers. Every write to the lake goes through this file.

Rules that these helpers enforce (each one was a real failure in the lab runs):
    1. Reads go through DeltaTable.scan or SQL (DataFusion), never through the pyarrow
       reader: files rewritten by MERGE come back as string_view with pyarrow 26.
       `to_plain` turns string_view into string before the data reaches pandas.
    2. MERGE does not dedup its source: the helpers dedup first.
    3. A MERGE that would change nothing is not sent, so a re-run makes no commit.
    4. Versions are found by commit metadata (find_version), not by timestamp: timestamp
       time travel follows file modification times and breaks after a copy.
    5. One writer per table at a time.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
from deltalake import CommitProperties, DeltaTable, QueryBuilder, Transaction, WriterProperties, write_deltalake


# --------------------------------------------------------------------------
# Tables, versions, commit metadata
# --------------------------------------------------------------------------
def exists(path: str | Path) -> bool:
    return DeltaTable.is_deltatable(str(path))


def ensure_table(path: str | Path, schema: pa.Schema, properties: Mapping[str, str],
                 partition_by: Sequence[str] | None = None) -> DeltaTable:
    """Create the table when it is missing (version 0, no rows). An existing table is not changed."""
    return DeltaTable.create(str(path), schema=schema, partition_by=list(partition_by) if partition_by else None,
                             configuration=dict(properties), mode="ignore")


def version(path: str | Path) -> int:
    return DeltaTable(str(path)).version()


def _text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, default=str, sort_keys=True)


def _commit(metadata: Mapping[str, Any] | None, app: Transaction | None = None) -> CommitProperties:
    """Custom commit metadata. Values are stored as text; dicts and lists as JSON text.

    delta-rs writes each key at the top level of commitInfo; history() shows them there.
    Spark's DESCRIBE HISTORY shows only the `userMetadata` key, so the whole dict is also
    stored there as one JSON text (read it in Spark with get_json_object(userMetadata, '$.as_of')).
    """
    meta = {k: _text(v) for k, v in (metadata or {}).items()}
    if meta:
        meta["userMetadata"] = json.dumps(meta, sort_keys=True)
    return CommitProperties(custom_metadata=meta or None, app_transactions=[app] if app else None)


def history(path: str | Path) -> list[dict]:
    """Commits, newest first. Custom metadata keys are at the top level of each entry."""
    return sorted(DeltaTable(str(path)).history(), key=lambda h: h["version"], reverse=True)


def find_version(path: str | Path, where: Mapping[str, Any]) -> int | None:
    """The newest version whose commit metadata holds every (key, value) of `where`.

    Example: find_version(path, {"step": "cohorts", "as_of": "2026-10-20T10:00:45.000000Z"}).
    Values are compared as text. Returns None when no commit matches.
    """
    want = {k: _text(v) for k, v in where.items()}
    for h in history(path):
        if all(h.get(k) == v for k, v in want.items()):
            return h["version"]
    return None


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------
def _plain_type(t: pa.DataType) -> pa.DataType:
    if pa.types.is_string_view(t) or pa.types.is_large_string(t):
        return pa.string()
    if pa.types.is_binary_view(t) or pa.types.is_large_binary(t):
        return pa.binary()
    if pa.types.is_list(t) or pa.types.is_large_list(t) or pa.types.is_list_view(t):
        return pa.list_(_plain_type(t.value_type))
    return t


def to_plain(tbl: pa.Table) -> pa.Table:
    """string_view / large_string -> string (also inside lists). Other types stay."""
    types = [_plain_type(f.type) for f in tbl.schema]
    if all(t == f.type for t, f in zip(types, tbl.schema)):
        return tbl
    return tbl.cast(pa.schema([pa.field(f.name, t, f.nullable) for f, t in zip(tbl.schema, types)]))


def read_table(path: str | Path, columns: Sequence[str] | None = None, predicate: str | None = None,
               version: int | None = None) -> pa.Table:
    """Read a Delta table (or one version of it) into an Arrow table with plain string columns."""
    table = DeltaTable(str(path), version=version)
    reader = table.scan(columns=list(columns) if columns else None, predicate=predicate)
    return to_plain(pa.table(reader))


def read_pandas(path: str | Path, columns: Sequence[str] | None = None, predicate: str | None = None,
                version: int | None = None, sort_by: Sequence[str] | None = None) -> pd.DataFrame:
    """Read into pandas with plain dtypes (object strings, datetime64[us, UTC], numpy numbers)."""
    df = read_table(path, columns, predicate, version).to_pandas()
    if sort_by:
        df = df.sort_values(list(sort_by), kind="stable").reset_index(drop=True)
    return df


def sql(table: DeltaTable | str | Path, query: str) -> pa.Table:
    """Run one SELECT on a table, registered as `t`. Pass a DeltaTable object to read ITS snapshot."""
    dt = table if isinstance(table, DeltaTable) else DeltaTable(str(table))
    return to_plain(pa.table(QueryBuilder().register("t", dt).execute(query)))


# --------------------------------------------------------------------------
# Writes
# --------------------------------------------------------------------------
def append(table: DeltaTable, data: pa.Table, metadata: Mapping[str, Any] | None = None,
           app_id: str | None = None, writer_properties: WriterProperties | None = None) -> int:
    """Append `data` in one commit and return the new version.

    Pass the DeltaTable object that the caller used to decide WHAT to load. With app_id set,
    the commit carries an application transaction, and delta-rs then refuses the commit when
    another writer with the same app_id committed after this object's snapshot. This is a
    guard against two loaders running at once. It is NOT what makes a re-run safe: the
    caller must check the table content first (see bronze_stream.loaded_lines).
    """
    app = None
    if app_id:
        app = Transaction(app_id=app_id, version=(table.transaction_version(app_id) or 0) + 1)
    write_deltalake(table, data, mode="append", commit_properties=_commit(metadata, app),
                    writer_properties=writer_properties)
    return table.version()


def dedupe_first(data: pa.Table, key_columns: Sequence[str]) -> pa.Table:
    """Keep the first row of each key, in the order of `data`."""
    keys = list(zip(*[data.column(k).to_pylist() for k in key_columns]))
    seen, keep = set(), []
    for i, k in enumerate(keys):
        if k not in seen:
            seen.add(k)
            keep.append(i)
    return data if len(keep) == data.num_rows else data.take(pa.array(keep, pa.int64()))


def merge_insert_new(path: str | Path, data: pa.Table, key_columns: Sequence[str],
                     partition_column: str | None = None, metadata: Mapping[str, Any] | None = None) -> dict:
    """Insert the rows of `data` whose key is not in the table yet. Existing rows are never changed.

    With partition_column, the ON clause names the partitions of the batch as literals, so only
    those partitions are read (this needs the same key to always land in the same partition).
    Nothing new -> no commit.
    """
    src = dedupe_first(data, key_columns)
    out = {"source_rows": data.num_rows, "inserted": 0, "version": None}
    if src.num_rows == 0:
        return out
    on = " AND ".join(f"t.{k} = s.{k}" for k in key_columns)
    if partition_column:
        values = src.column(partition_column).unique().to_pylist()
        if any(v is None for v in values):
            raise ValueError(f"{partition_column} is null in the batch for {path}")
        literals = ", ".join(f"'{v}'" for v in sorted(str(v) for v in values))
        on += f" AND t.{partition_column} IN ({literals})"
    table = DeltaTable(str(path))
    before = table.version()
    metrics = (table.merge(src, on, source_alias="s", target_alias="t", commit_properties=_commit(metadata))
               .when_not_matched_insert_all().execute())
    after = DeltaTable(str(path)).version()
    out.update(inserted=int(metrics["num_target_rows_inserted"]), version=after if after != before else None)
    return out


def merge_earliest(path: str | Path, data: pa.Table, key_columns: Sequence[str], order_column: str,
                   metadata: Mapping[str, Any] | None = None) -> dict:
    """One row per key, the smallest `order_column` wins ("earliest wins").

    Step 1: inside the batch keep the earliest row per key (the first row on a tie).
    Step 2: drop the batch rows that would change nothing (the table already holds a row
            for the key that is not later). An empty rest -> no MERGE, no commit.
    Step 3: MERGE: insert new keys, update only when the source row is earlier.
    Rows with a null key are dropped and counted (a null never matches in the ON clause).
    """
    key_columns = list(key_columns)
    k = data.select(key_columns + [order_column]).to_pandas()
    not_null = k[key_columns].notna().all(axis=1).to_numpy()
    k = k[not_null].sort_values(key_columns + [order_column], kind="stable")
    first = k.index[~k.duplicated(key_columns, keep="first").to_numpy()]
    src = data.take(pa.array(sorted(first), pa.int64()))
    out = {"source_rows": data.num_rows, "null_key_rows": int((~not_null).sum()), "inserted": 0, "updated": 0,
           "version": None}
    if src.num_rows:
        cur = read_table(path, columns=key_columns + [order_column]).to_pandas()
        cur = cur.rename(columns={order_column: "_current"})
        j = src.select(key_columns + [order_column]).to_pandas().merge(cur, on=key_columns, how="left")
        changes = (j["_current"].isna() | (j[order_column] < j["_current"])).to_numpy()
        src = src.filter(pa.array(changes))
    if src.num_rows == 0:
        return out
    table = DeltaTable(str(path))
    before = table.version()
    on = " AND ".join(f"t.{c} = s.{c}" for c in key_columns)
    metrics = (table.merge(src, on, source_alias="s", target_alias="t", commit_properties=_commit(metadata))
               .when_matched_update_all(predicate=f"s.{order_column} < t.{order_column}")
               .when_not_matched_insert_all().execute())
    after = DeltaTable(str(path)).version()
    out.update(inserted=int(metrics["num_target_rows_inserted"]), updated=int(metrics["num_target_rows_updated"]),
               version=after if after != before else None)
    return out


# --------------------------------------------------------------------------
# Whole-table replace, only when the content changed
# --------------------------------------------------------------------------
def canonical(tbl: pa.Table, key_columns: Sequence[str]) -> pa.Table:
    """Sort by the key, then by every other column that can be sorted (list columns cannot)."""
    rest = [f.name for f in tbl.schema if f.name not in key_columns and not pa.types.is_nested(f.type)]
    return tbl.sort_by([(c, "ascending") for c in [*key_columns, *rest]])


def _nan_to_null(tbl: pa.Table) -> pa.Table:
    for i, f in enumerate(tbl.schema):
        if pa.types.is_floating(f.type):
            col = tbl.column(i)
            tbl = tbl.set_column(i, f, pc.if_else(pc.is_nan(col), pa.scalar(None, f.type), col))
    return tbl


def same_content(a: pa.Table, b: pa.Table, key_columns: Sequence[str]) -> bool:
    """True when both tables hold the same rows (row order does not matter). b is cast to a's types."""
    if a.num_rows != b.num_rows or a.schema.names != b.schema.names:
        return False
    a = a.replace_schema_metadata(None)
    try:
        b = b.cast(a.schema)
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
        return False
    return _nan_to_null(canonical(a, key_columns)).equals(_nan_to_null(canonical(b, key_columns)))


def replace_if_changed(path: str | Path, new_table: pa.Table, key_columns: Sequence[str],
                       metadata: Mapping[str, Any] | None = None) -> dict:
    """Overwrite the whole table with `new_table`, but only when the sorted content differs.

    Returns {"wrote": bool, "version": the version that now holds this content, "rows": n}.
    The old files stay (no vacuum), so the previous content is still readable by version.
    The table must exist (ensure_table) and `new_table` must have the table's schema.
    """
    table = DeltaTable(str(path))
    new_table = to_plain(new_table)
    current = to_plain(pa.table(table.scan()))
    if same_content(new_table, current, key_columns):
        return {"wrote": False, "version": table.version(), "rows": new_table.num_rows}
    write_deltalake(table, new_table, mode="overwrite", commit_properties=_commit(metadata))
    return {"wrote": True, "version": table.version(), "rows": new_table.num_rows}
