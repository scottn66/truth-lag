"""Load the history cohort into SQLite, for the SQL side of the 3-engine comparison.

Purpose
    The comparison (spec section 5) asks the same two questions in MongoDB, Neo4j
    and SQL. This script puts the history cohort into one SQLite file with 2 tables:
    - revisions: one row per history revision, with the flat columns of
      history_revisions.parquet in the same order (DATA_MODEL.md section 3);
    - revert_links: one row per reverted history revision (history_revert_links.parquet).
    Types: whole numbers -> INTEGER, decimals -> REAL, true/false -> INTEGER 1/0,
    times -> ISO text in UTC ("2026-09-08T00:00:00+00:00"), lists (tags) -> comma
    text ("AWB,mobile edit"; a comma inside an item is written "\\,", as in the dump).
    Empty values stay NULL.
    Keys and indexes:
    - revisions: rev_id is the primary key; an index on page_id;
    - revert_links: indexes on page_id, reverted_rev_id (unique), author_key and
      reverter_key.
    Then it runs ANALYZE, so SQLite knows the table sizes when it plans a query.
    It builds truthlag.sqlite.tmp, checks the row counts, and only then renames it.

Inputs
    data/tables/history_revisions.parquet and data/tables/history_revert_links.parquet
    (made by ingest/parse_history.py; this script stops if _SUCCESS_history.json is
    missing or its row counts do not match the files).

Outputs
    data/tables/truthlag.sqlite (config.SQLITE_PATH) and
    data/tables/_SUCCESS_sqlite.json (row counts, indexes, file size, SQLite version).

Run (from the repo root; about 15 seconds)
    .venv/bin/python ec-hw2/load_sql.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from ingest.parse_history import LINK_COLUMNS, REVISION_COLUMNS  # noqa: E402

REVISIONS_FILE = config.TABLES_DIR / "history_revisions.parquet"
LINKS_FILE = config.TABLES_DIR / "history_revert_links.parquet"
UPSTREAM_SUCCESS = config.TABLES_DIR / "_SUCCESS_history.json"
SUCCESS_FILE = config.SQLITE_PATH.parent / "_SUCCESS_sqlite.json"

TABLES = {"revisions": REVISION_COLUMNS, "revert_links": LINK_COLUMNS}
PRIMARY_KEYS = {"revisions": "rev_id"}
# (index name, table, column, unique)
INDEXES = [
    ("idx_revisions_page_id", "revisions", "page_id", False),
    ("idx_revert_links_page_id", "revert_links", "page_id", False),
    ("idx_revert_links_reverted_rev_id", "revert_links", "reverted_rev_id", True),
    ("idx_revert_links_author_key", "revert_links", "author_key", False),
    ("idx_revert_links_reverter_key", "revert_links", "reverter_key", False),
]
INSERT_BATCH = 50_000


# --------------------------------------------------------------------------
# Arrow columns -> SQLite values
# --------------------------------------------------------------------------
def sql_type(t: pa.DataType) -> str:
    """The SQLite column type for an Arrow type."""
    if pa.types.is_integer(t) or pa.types.is_boolean(t):
        return "INTEGER"
    if pa.types.is_floating(t):
        return "REAL"
    if pa.types.is_string(t) or pa.types.is_large_string(t):
        return "TEXT"
    if pa.types.is_timestamp(t) or pa.types.is_list(t) or pa.types.is_large_list(t):
        return "TEXT"
    raise TypeError(f"no SQLite type for Arrow type {t}")


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S+00:00"            # whole seconds (all dump times)
ISO_FORMAT_US = "%Y-%m-%dT%H:%M:%S.%f+00:00"      # used for the whole column if any time has a fraction


def iso_texts(col: pa.ChunkedArray) -> list:
    """A UTC time column as ISO text, for example '2026-09-08T00:00:00+00:00'.

    Every value in a column has the same width, so text order = time order in SQL."""
    if col.type.tz not in ("UTC", "+00:00", "Etc/UTC"):
        raise ValueError(f"time column has time zone {col.type.tz!r}, not UTC")
    s = col.to_pandas()                              # keeps nanoseconds
    known = s.dropna()
    if (known.dt.nanosecond != 0).any():
        raise ValueError("time column has nanoseconds; ISO text would lose them")
    fmt = ISO_FORMAT_US if (known.dt.microsecond != 0).any() else ISO_FORMAT
    return s.dt.strftime(fmt).astype(object).where(s.notna(), None).tolist()


def comma_text(items) -> str | None:
    """A list as comma text. A comma inside an item is written '\\,' (the dump's rule),
    so ingest.history_columns.split_list() gives the list back."""
    if items is None:
        return None
    return ",".join(str(x).replace(",", "\\,") for x in items)


def column_values(col: pa.ChunkedArray) -> list:
    """The values of one Arrow column as plain Python values for SQLite."""
    t = col.type
    if pa.types.is_timestamp(t):
        return iso_texts(col)
    values = col.to_pylist()
    if pa.types.is_boolean(t):
        return [None if v is None else int(v) for v in values]
    if pa.types.is_list(t) or pa.types.is_large_list(t):
        return [comma_text(v) for v in values]
    return values


def create_table(con: sqlite3.Connection, name: str, schema: pa.Schema, columns: list[str]) -> None:
    pk = PRIMARY_KEYS.get(name)
    parts = []
    for c in columns:
        parts.append(f"{c} {sql_type(schema.field(c).type)}" + (" PRIMARY KEY" if c == pk else ""))
    con.execute(f"CREATE TABLE {name} (\n  " + ",\n  ".join(parts) + "\n)")


def insert_table(con: sqlite3.Connection, name: str, table: pa.Table, columns: list[str]) -> int:
    """Create the table and insert every row. Returns the number of rows."""
    missing = [c for c in columns if c not in table.column_names]
    extra = [c for c in table.column_names if c not in columns]
    if missing or extra:
        raise SystemExit(f"STOP: {name}: columns differ from DATA_MODEL.md "
                         f"(missing {missing}, extra {extra})")
    create_table(con, name, table.schema, columns)
    sql = f"INSERT INTO {name} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})"
    n = 0
    for start in range(0, table.num_rows, INSERT_BATCH):
        part = table.slice(start, INSERT_BATCH)
        values = [column_values(part.column(c)) for c in columns]
        con.executemany(sql, zip(*values))
        n += part.num_rows
    return n


def create_indexes(con: sqlite3.Connection) -> list[str]:
    names = []
    for name, table, column, unique in INDEXES:
        con.execute(f"CREATE {'UNIQUE ' if unique else ''}INDEX {name} ON {table} ({column})")
        names.append(f"{table}({column}){' unique' if unique else ''}")
    return names


def fill(con: sqlite3.Connection, revisions: pa.Table, links: pa.Table) -> dict:
    """Create both tables, insert the rows and add the indexes. Used by main() and the tests."""
    rows = {"revisions": insert_table(con, "revisions", revisions, REVISION_COLUMNS),
            "revert_links": insert_table(con, "revert_links", links, LINK_COLUMNS)}
    indexes = create_indexes(con)
    con.execute("ANALYZE")
    con.commit()
    return {"rows": rows, "indexes": indexes}


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def check_inputs() -> dict:
    """Stop unless the history step finished and its row counts match the files."""
    if not UPSTREAM_SUCCESS.exists():
        raise SystemExit(f"STOP: {UPSTREAM_SUCCESS.name} is missing. Run ingest/parse_history.py first.")
    done = json.loads(UPSTREAM_SUCCESS.read_text(encoding="utf-8"))
    counts = {}
    for path in (REVISIONS_FILE, LINKS_FILE):
        if not path.exists():
            raise SystemExit(f"STOP: {path} is missing.")
        n = pq.read_metadata(path).num_rows
        want = done.get("rows", {}).get(path.name)
        if want is not None and want != n:
            raise SystemExit(f"STOP: {path.name} has {n:,} rows but {UPSTREAM_SUCCESS.name} says {want:,}.")
        counts[path.name] = n
    return counts


def check_loaded(con: sqlite3.Connection, want: dict) -> None:
    for table, n in want.items():
        got = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if got != n:
            raise SystemExit(f"STOP: {table} has {got:,} rows in SQLite, {n:,} in Parquet.")
        other = con.execute(f"SELECT COUNT(*) FROM {table} WHERE cohort <> ?",
                            (config.COHORT_HISTORY,)).fetchone()[0]
        if other:
            raise SystemExit(f"STOP: {table} has {other:,} rows that are not in the history cohort.")


def write_json_safely(obj: dict, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> int:
    t0 = time.time()
    config.ensure_dirs()
    inputs = check_inputs()
    print(f"inputs: {REVISIONS_FILE.name} {inputs[REVISIONS_FILE.name]:,} rows, "
          f"{LINKS_FILE.name} {inputs[LINKS_FILE.name]:,} rows")
    revisions = pq.read_table(REVISIONS_FILE)
    links = pq.read_table(LINKS_FILE)

    final = config.SQLITE_PATH
    tmp = final.with_name(final.name + ".tmp")
    for p in (tmp, tmp.with_name(tmp.name + "-journal")):
        p.unlink(missing_ok=True)          # a left-over from a run that stopped
    con = sqlite3.connect(tmp)
    try:
        # The .tmp file is thrown away if anything fails, so we can skip the journal.
        con.execute("PRAGMA journal_mode = OFF")
        con.execute("PRAGMA synchronous = OFF")
        out = fill(con, revisions, links)
        check_loaded(con, {"revisions": revisions.num_rows, "revert_links": links.num_rows})
        bad = con.execute("PRAGMA integrity_check").fetchone()[0]
        if bad != "ok":
            raise SystemExit(f"STOP: SQLite integrity check says {bad!r}")
    finally:
        con.close()
    os.replace(tmp, final)

    size_mb = final.stat().st_size / 1e6
    for table, n in out["rows"].items():
        print(f"{table:13s} {n:>9,} rows")
    print(f"indexes: {', '.join(out['indexes'])}")
    print(f"wrote {final.relative_to(config.REPO_ROOT)} ({size_mb:.1f} MB) "
          f"in {time.time() - t0:.1f} s; SQLite {sqlite3.sqlite_version}")
    write_json_safely({
        "step": "sqlite",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_version": config.DATA_VERSION,
        "inputs": inputs,
        "rows": out["rows"],
        "indexes": out["indexes"],
        "file": final.name,
        "file_mb": round(size_mb, 1),
        "sqlite_version": sqlite3.sqlite_version,
    }, SUCCESS_FILE)
    print(f"wrote {SUCCESS_FILE.relative_to(config.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
