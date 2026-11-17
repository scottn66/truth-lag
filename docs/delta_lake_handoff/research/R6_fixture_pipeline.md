# R6 — Prototype: Bronze and Silver with delta-rs on the repo fixtures

> **Research report, not yet reviewed.** Output of the research agent `fixture_pipeline` in a cloud Claude Code session on Nov 13, 2026, as returned. Evidence labels: RAN = executed in that session on made-up data; READ = read at the cited file and line; DERIVED = arithmetic on values that were read; UNVERIFIED = not checked. Paths that start with /tmp/claude-0/ or /home/user/ are on that session's machine and cannot be opened from elsewhere. Repository state read: scottn66/truth-lag at 8e28012.

## Summary

Everything asked for passed: step 1 (a, b, c) and P1 to P7; the parity test file ends with `16 passed in 11.90s`, and nothing failed. One Python 3.12 venv holds both engines with no version conflict (delta-spark 4.4.1 with pyspark 4.2.0, deltalake 1.6.6, pandas 2.3.3, pyarrow 26.0.1, polars 2.1.0); the 30 old ingest tests pass in it, and Spark and delta-rs read each other's tables. The prototype package `etl` writes 3 Bronze and 8 Silver Delta tables with delta-rs and reuses the old code through an import shim (TRUTHLAG_HW2_DIR). On the repo's fixture scenario every Silver table equals the old Parquet file in values (38, 2, 7, 32, 9, 17, 5 rows; times to the microsecond; list columns), and capture_gaps equals the old CSV (4 rows). A second run writes no commit in any table; a raw file that grew adds only its new lines (18 of 38); two arrivals, in either order, end in the one-batch tables. `build(as_of)` writes one version per cohort table; the version for as_of 10:00:45 equals the old pipeline run on only the earlier events, is found again from commit metadata, and lacks the revert link of revision 102 that the later version has. Cut-short and open gzip files behave as in the old reader (269 complete lines kept, the open file skipped, a later completed file adds only its 10 missing lines). Spark from the same venv reads all 11 tables with equal counts and values, and finds a version by as_of because the commit metadata is also stored under `userMetadata` (Spark shows no other custom key). A later session must know four things: Bronze idempotence comes from max(source_line) per source_file read from the table; capture_gaps must be computed from Bronze because the Silver tables lack the needed columns; the cohort tables store microseconds; a build that changes nothing writes no version, so the as_of to version map is also in run.json. Indicative speed on 300,000 + 165,000 made-up events: Bronze 6.4 s, Silver 7.9 s, peak memory 1.36 GB, results equal to the old parser. Not covered: real data, the history tables, Spark writes and Gold, a Silver watermark, table maintenance. The repo is untouched: `git -C /home/user/truth-lag status --porcelain` printed nothing.

## Versions

All RAN on this machine (Linux, 4 CPUs) in ONE uv venv: `SCRATCH/venv` (SCRATCH = `/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/fixture_pipeline`).

```bash
uv venv --python 3.12 SCRATCH/venv
uv pip install --python SCRATCH/venv/bin/python "delta-spark==4.4.1" "deltalake==1.6.6" "pandas>=2.3,<3" pyarrow polars pytest
# Resolved 22 packages. delta-spark 4.4.1 pulled pyspark 4.2.0.
```

`uv pip freeze` (all 22 lines):

```text
arro3-core==0.9.1
delta-spark==4.4.1
deltalake==1.6.6
deprecated==3.0.1
importlib-metadata==8.7.1
iniconfig==2.3.1
numpy==2.5.4
packaging==26.3
pandas==2.3.3
pluggy==1.7.0
polars==2.1.0
polars-runtime-32==2.1.0
py4j==0.10.9.9
pyarrow==26.0.1
pygments==2.21.0
pyspark==4.2.0
pytest==9.2.0
python-dateutil==4.0.0
pytz==2026.6
tzdata==2026.6
wrapt==2.5.2
zipp==4.1.2
```

Other: Python 3.12.3, uv 0.11.32, OpenJDK 21.0.12.1, Spark 4.2.0, Delta jar `io.delta:delta-spark_4.2_2.13:4.4.1` chosen by `configure_spark_with_delta_pip`. I copied the Ivy cache of the earlier Spark lab into my scratch folder and set `spark.jars.ivy` to the copy: Spark resolved 33 jars with 0 downloads (`0 artifacts copied, 33 already retrieved`).

**Version conflicts: none found (RAN).** `uv pip check` prints `Checked 22 packages` and `All installed packages are compatible`. polars is installed but the prototype does not use it.

**Step 1 checks (all RAN)**

| Check | Result |
|---|---|
| (a) the 30 old ingest tests, run from the scratch copy of ec-hw2 | `30 passed in 2.34s`; again at the end `30 passed in 1.95s` |
| (b) one interpreter imports pyspark, delta, deltalake, pandas, pyarrow, polars | worked; versions as in the freeze list |
| (c) Spark session with Delta from this venv | started in 5.9 s (later runs 6.7 s), session time zone UTC |
| (c) Spark reads a table that delta-rs wrote | 3 rows; times exact to the microsecond (`23:59:59.999999`, `00:00:00.000001`); date partition filter gives 2 rows; list column and nulls correct. Spark's DESCRIBE DETAIL: reader 1, writer 2, features `[appendOnly, invariants]`, all five table properties kept |
| (c) delta-rs reads a table that Spark wrote | protocol 1 / 2, 2 rows, `known_at` is `datetime64[us, UTC]` with value `2026-10-20 10:00:02.123456+00:00`, partition column `event_date` |
| side files | no `spark-warehouse`, `metastore_db` or `derby.log` in the working folder |
| extra: pandas and Spark in this venv | `spark.createDataFrame(pandas_df)` and `toPandas()` work with Arrow on and off (pyspark 4.2.0, pandas 2.3.3, pyarrow 26.0.1). A Python UDF ran in a worker with Python 3.12.3 |
| extra: Spark reads the lake that the prototype wrote | see Results |

Spark session settings that worked in every run (from the Spark lab report; the scripts are in the zip under `proto/checks/`):

```python
import os, sys
os.environ["PYSPARK_PYTHON"] = sys.executable          # else the workers start PATH python3 (3.13 here)
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
HOME = "/abs/folder/outside/the/repo"
b = (SparkSession.builder.master("local[2]").appName("truthlag")
     .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
     .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
     .config("spark.driver.memory", "4g").config("spark.sql.shuffle.partitions", "4")
     .config("spark.sql.session.timeZone", "UTC")
     .config("spark.sql.warehouse.dir", HOME + "/warehouse")
     .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={HOME}/derby -Duser.timezone=UTC")
     .config("spark.local.dir", HOME + "/sparktmp").config("spark.jars.ivy", HOME + "/ivy")
     .config("spark.ui.enabled", "false").config("spark.ui.showConsoleProgress", "false"))
spark = configure_spark_with_delta_pip(b).getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
```

## Prototype code

The package is `proto/etl/` in the zip. All of it RAN (16 tests, see "Parity test"). The text below is read from the files that ran.

How to run it on another machine:

```bash
export TRUTHLAG_HW2_DIR=/path/to/truth-lag/ec-hw2      # the old code: config.py and ingest/
export TRUTHLAG_LAKE_DIR=/path/to/lake                 # tables at <lake>/<layer>/<table>/
export PYTHONDONTWRITEBYTECODE=1
cd <folder that holds etl/>
python -m etl.run all --raw-dir data/raw --history-dir data/history                # bronze, silver, cohorts
python -m etl.run cohorts --as-of 2026-10-27T00:05:00Z --history-dir data/history    # what we knew at that time
```

Design in short:
- **Bronze** (`bronze/page_change_events`, `bronze/revert_risk_events`, `bronze/tags_events`): one row per complete captured line, 14 columns, partitioned by `event_date`, append-only, ZSTD. The loader reads `max(source_line)` per `source_file` from the table and loads only later lines.
- **Silver stream tables**: for each touched event date, all Bronze rows of that date are read again in the old order and go through the old rules and the old `flat_*` functions. `page_change` and `tag_events`: insert-only MERGE on `meta_id` with the partition literal. `revert_risk`: earliest `meta_dt` per `rev_id`. `capture_gaps`: recomputed from the Bronze envelope columns, replaced when changed.
- **Silver cohort tables**: export to a temporary folder in the old schemas, call `label_live.run` and `late_reverts.run` unchanged, load the four files with `replace_if_changed`.
- Lake tables: reader 1 / writer 2, no table features, so both engines can read and write them.

### etl/__init__.py

```python
"""TruthLag lake prototype: Bronze and Silver Delta tables written with delta-rs.

The rules stay in the old pandas pipeline (ec-hw2/config.py and ec-hw2/ingest/*.py).
This package only moves the data through Delta tables and calls the old functions.

Environment variables
    TRUTHLAG_HW2_DIR    the ec-hw2 folder (holds config.py and ingest/)
    TRUTHLAG_LAKE_DIR   the lake root; tables live at <lake>/<layer>/<table>/
"""
```

### etl/hw2.py

```python
"""Import shim for the old pandas pipeline (the ec-hw2 folder).

Purpose
    ec-hw2 has a hyphen, so it cannot be a package. Its modules expect the ec-hw2
    folder itself on sys.path (`import config`, `from ingest import parse_stream`).
    This module puts that folder on sys.path once and re-exports the modules, so
    the rest of the package writes `from .hw2 import config, parse_stream`.

Inputs
    TRUTHLAG_HW2_DIR   path of the ec-hw2 folder. If it is not set, the folder
                       `ec-hw2` next to this package is used (the repo layout).

Do not name a new package `ingest`, `config` or `tests`: the old code owns these names.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_VAR = "TRUTHLAG_HW2_DIR"


def _find_hw2_dir() -> Path:
    value = os.environ.get(ENV_VAR)
    p = Path(value).expanduser() if value else Path(__file__).resolve().parents[1] / "ec-hw2"
    p = p.resolve()
    if not (p / "config.py").is_file() or not (p / "ingest" / "parse_stream.py").is_file():
        raise ImportError(f"{p} is not the ec-hw2 folder (config.py and ingest/parse_stream.py not found). "
                          f"Set {ENV_VAR} to the ec-hw2 folder.")
    return p


HW2_DIR = _find_hw2_dir()
if str(HW2_DIR) not in sys.path:
    sys.path.insert(0, str(HW2_DIR))

import config  # noqa: E402
from ingest import history_columns, label_live, late_reverts, parse_history, parse_stream  # noqa: E402

# Another module named `config` or `ingest` earlier on sys.path would be used silently. Stop if so.
for _mod, _want in ((config, HW2_DIR), (parse_stream, HW2_DIR / "ingest")):
    if Path(_mod.__file__).resolve().parent != _want:
        raise ImportError(f"{_mod.__name__} was imported from {_mod.__file__}, not from {_want}")

__all__ = ["HW2_DIR", "config", "history_columns", "label_live", "late_reverts", "parse_history", "parse_stream"]
```

### etl/lake_config.py

```python
"""Lake settings: where the Delta tables live and which table properties they get.

The rules of the project (windows, thresholds, stream names) stay in ec-hw2/config.py.
This file only holds what is new with the lake.

Layout
    <lake>/bronze/<table>/     raw events, append-only
    <lake>/silver/<table>/     typed tables with the columns of the old Parquet files
    <lake>/_runs/<as_of>/      JSON summaries of each cohort build (plain files)
"""
from __future__ import annotations

import os
from pathlib import Path

from deltalake import WriterProperties

ENV_VAR = "TRUTHLAG_LAKE_DIR"


def lake_root(lake: str | Path | None = None) -> Path:
    """The lake folder: the argument when given, else the TRUTHLAG_LAKE_DIR variable."""
    value = lake if lake is not None else os.environ.get(ENV_VAR)
    if not value:
        raise RuntimeError(f"No lake folder. Pass lake=... or set {ENV_VAR}.")
    return Path(value).expanduser().resolve()


# Set at CREATE. The defaults delete commit files after 30 days at the next checkpoint
# (then time travel to them fails) and let VACUUM delete data files after 7 days.
KEEP_HISTORY = {
    "delta.logRetentionDuration": "interval 3650 days",
    "delta.deletedFileRetentionDuration": "interval 3650 days",
    "delta.enableExpiredLogCleanup": "false",
}

# File statistics only for the small envelope columns. raw_json is long text: no min / max for it.
BRONZE_STATS_COLUMNS = ["meta_id", "meta_dt", "stream", "wiki_id", "kafka_topic", "kafka_partition", "kafka_offset"]
BRONZE_PROPS = {**KEEP_HISTORY, "delta.appendOnly": "true",
                "delta.dataSkippingStatsColumns": ",".join(BRONZE_STATS_COLUMNS)}
SILVER_PROPS = {**KEEP_HISTORY}

BRONZE_COMPRESSION = "ZSTD"          # raw JSON text compresses much better with zstd than with snappy
BRONZE_COMPRESSION_LEVEL = 3
BRONZE_CHUNK_ROWS = 100_000          # rows per Bronze commit: keeps memory low on the first full load

# Both engines must be able to read and write every table, so these table features are forbidden.
FORBIDDEN_FEATURES = ["deletionVectors", "clustering", "identityColumns", "variantType", "inCommitTimestamp",
                      "columnMapping"]


def bronze_writer_properties() -> WriterProperties:
    return WriterProperties(compression=BRONZE_COMPRESSION, compression_level=BRONZE_COMPRESSION_LEVEL)
```

### etl/tables.py

```python
"""Registry of the lake tables: name -> path, key columns, partition columns, Arrow schema.

The Silver schemas are taken from the old code (parse_stream, label_live, late_reverts),
so a column is defined in one place only. Two differences from the old Parquet files:
    1. page_change and tag_events get an `event_date` partition column (UTC date of meta_dt).
    2. The cohort tables store microsecond times (Delta has no nanosecond type); the old
       files store nanoseconds. Every value is a whole millisecond or second, so nothing is lost.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa

from . import lake_config
from .hw2 import config, label_live, late_reverts, parse_stream

TS = pa.timestamp("us", tz="UTC")


@dataclass(frozen=True)
class TableSpec:
    name: str                 # "<layer>/<table>", also the path below the lake root
    key: tuple                # columns that identify one row
    partition_by: tuple
    schema: pa.Schema
    properties: dict

    @property
    def layer(self) -> str:
        return self.name.split("/")[0]

    def path(self, lake: str | Path | None = None) -> str:
        return str(lake_config.lake_root(lake) / self.name)


def _with_event_date(schema: pa.Schema) -> pa.Schema:
    return pa.schema(list(schema) + [pa.field("event_date", pa.date32())])


def _micro(schema: pa.Schema) -> pa.Schema:
    fields = []
    for f in schema:
        t = pa.timestamp("us", tz=f.type.tz) if pa.types.is_timestamp(f.type) else f.type
        fields.append(pa.field(f.name, t))
    return pa.schema(fields)


# ---- Bronze: one row per complete captured line ----
BRONZE_SCHEMA = pa.schema([
    ("meta_id", pa.string()), ("meta_dt", TS), ("event_date", pa.date32()), ("stream", pa.string()),
    ("wiki_id", pa.string()), ("kafka_topic", pa.string()), ("kafka_partition", pa.int32()),
    ("kafka_offset", pa.int64()), ("raw_json", pa.string()), ("source_file", pa.string()),
    ("source_line", pa.int32()), ("capture_session", pa.string()), ("batch_id", pa.string()),
    ("loaded_at", TS),
])
BRONZE_NAMES = {
    config.STREAM_PAGE_CHANGE: "page_change_events",
    config.STREAM_REVERT_RISK: "revert_risk_events",
    config.STREAM_TAGS: "tags_events",
}
BRONZE = {stream: TableSpec(f"bronze/{name}", ("source_file", "source_line"), ("event_date",), BRONZE_SCHEMA,
                            lake_config.BRONZE_PROPS)
          for stream, name in BRONZE_NAMES.items()}

# ---- Silver: the old Parquet tables ----
REVERT_RISK_OUT_SCHEMA = pa.schema([parse_stream.REVERT_RISK_SCHEMA.field(c) for c in parse_stream.REVERT_RISK_COLUMNS])
TAG_OUT_SCHEMA = pa.schema([parse_stream.TAG_SCHEMA.field(c) for c in parse_stream.TAG_COLUMNS])
CAPTURE_GAPS_SCHEMA = pa.schema([("stream", pa.string()), ("topic", pa.string()), ("partition", pa.int32()),
                                 ("gap_start", TS), ("gap_end", TS), ("gap_s", pa.float64())])
# The schemas of the files that label_live.py and late_reverts.py read (data/parsed/*.parquet).
PARSED_SCHEMAS = {"page_change": parse_stream.PAGE_CHANGE_SCHEMA, "revert_risk": REVERT_RISK_OUT_SCHEMA,
                  "tag_events": TAG_OUT_SCHEMA}

_P = lake_config.SILVER_PROPS
SILVER = {
    "page_change": TableSpec("silver/page_change", ("meta_id",), ("event_date",),
                             _with_event_date(parse_stream.PAGE_CHANGE_SCHEMA), _P),
    "revert_risk": TableSpec("silver/revert_risk", ("rev_id",), (), REVERT_RISK_OUT_SCHEMA, _P),
    "tag_events": TableSpec("silver/tag_events", ("meta_id",), ("event_date",), _with_event_date(TAG_OUT_SCHEMA), _P),
    "capture_gaps": TableSpec("silver/capture_gaps", ("stream", "gap_start"), (), CAPTURE_GAPS_SCHEMA, _P),
    "live_revisions": TableSpec("silver/live_revisions", ("rev_id",), (), _micro(label_live.LIVE_REVISIONS_SCHEMA), _P),
    "live_revert_links": TableSpec("silver/live_revert_links", ("reverted_rev_id",), (),
                                   _micro(label_live.LINKS_SCHEMA), _P),
    "live_revert_links_all": TableSpec("silver/live_revert_links_all", ("reverted_rev_id", "reverting_rev_id"), (),
                                       _micro(label_live.LINKS_ALL_SCHEMA), _P),
    "late_reverts": TableSpec("silver/late_reverts", ("rev_id",), (), _micro(late_reverts.LATE_SCHEMA), _P),
}
STREAM_TABLES = ["page_change", "revert_risk", "tag_events", "capture_gaps"]
COHORT_TABLES = ["live_revisions", "live_revert_links", "live_revert_links_all", "late_reverts"]

ALL = {spec.name: spec for spec in [*BRONZE.values(), *SILVER.values()]}


def bronze_spec(stream: str) -> TableSpec:
    return BRONZE[stream]
```

### etl/delta_io.py

```python
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
```

### etl/bronze_stream.py

```python
"""Bronze: load the raw capture files into append-only Delta tables, one row per line.

Purpose
    For each stream in config.STREAM_DIRS, read the raw part files with the old tolerant
    reader (parse_stream.list_part_files and parse_stream.read_lines) and append one row
    per complete captured line to bronze/<name>_events. The line is stored unchanged in
    raw_json. Nothing is filtered here: canary events, other wikis and broken lines are
    kept, so Silver can apply the old rules in the old order.

Idempotence (does not rely on Delta application transactions)
    Before loading, the loader reads from the Bronze table itself the highest source_line
    already loaded for each source_file. It loads only later lines. So:
      - a second run on unchanged files adds 0 rows and makes no commit;
      - a file that grew (it was read while open, or it was cut short) gets only its new lines.
    This is safe because a part file only grows at its end: old lines stay a prefix.
    Files changed in the last config.OPEN_FILE_GRACE_S seconds are skipped (include_open=False).

Inputs
    <raw_dir>/<stream>/dt=YYYY-MM-DD/hour=HH/part-<session>-<n>.ndjson.gz

Outputs
    <lake>/bronze/page_change_events, revert_risk_events, tags_events (partitioned by event_date)

Run
    python -m etl.run bronze --raw-dir data/raw
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pyarrow as pa
from deltalake import DeltaTable

from . import delta_io, lake_config, tables
from .hw2 import config, parse_stream

log = logging.getLogger("bronze_stream")

FILE_RE = re.compile(r"^part-(?P<session>.+)-(?P<n>\d+)\.ndjson\.gz$")
DT_FOLDER_RE = re.compile(r"(?:^|/)dt=(\d{4}-\d{2}-\d{2})(?:/|$)")
INT32_MAX, INT64_MAX = 2**31 - 1, 2**63 - 1
NO_DATE = date(1970, 1, 1)      # partition for a line with no meta.dt in a folder that is not dt=YYYY-MM-DD


def new_batch_id(now: float) -> str:
    """Like the capture's session id: start time plus 6 random hex digits."""
    return f"{datetime.fromtimestamp(now, timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def parse_dt(text) -> datetime | None:
    """meta.dt text -> aware UTC datetime (microseconds). None when it cannot be read."""
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        d = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _int(v, limit: int):
    return v if isinstance(v, int) and not isinstance(v, bool) and -limit - 1 <= v <= limit else None


def _text(v):
    return None if v is None else (v if isinstance(v, str) else str(v))


def envelope(raw: str) -> dict:
    """The envelope columns of one line. All None when the line is not a JSON object."""
    out = {"meta_id": None, "meta_dt": None, "wiki_id": None, "kafka_topic": None,
           "kafka_partition": None, "kafka_offset": None}
    try:
        ev = json.loads(raw)
    except ValueError:
        return out
    if not isinstance(ev, dict):
        return out
    meta = ev.get("meta")
    meta = meta if isinstance(meta, dict) else {}
    out["meta_id"] = _text(meta.get("id"))
    out["meta_dt"] = parse_dt(meta.get("dt"))
    out["wiki_id"] = _text(ev.get("wiki_id") or ev.get("database"))     # the tags stream has `database`
    out["kafka_topic"] = _text(meta.get("topic"))
    out["kafka_partition"] = _int(meta.get("partition"), INT32_MAX)
    out["kafka_offset"] = _int(meta.get("offset"), INT64_MAX)
    return out


def folder_date(rel_path: str) -> date | None:
    m = DT_FOLDER_RE.search(rel_path)
    return date.fromisoformat(m.group(1)) if m else None


def loaded_lines(table: DeltaTable) -> dict[str, int]:
    """source_file -> highest source_line already in the Bronze table (read from the table itself)."""
    got = delta_io.sql(table, "SELECT source_file, max(source_line) AS n FROM t GROUP BY source_file")
    return dict(zip(got.column("source_file").to_pylist(), got.column("n").to_pylist()))


def load_stream(stream: str, raw_dir: str | Path, lake: str | Path | None = None, now: float | None = None,
                include_open: bool = False, batch_id: str | None = None, chunk_rows: int | None = None) -> dict:
    """Append the new lines of one stream. Returns the stats and the event dates touched."""
    now = time.time() if now is None else now
    batch_id = batch_id or new_batch_id(now)
    chunk_rows = chunk_rows or lake_config.BRONZE_CHUNK_ROWS
    loaded_at = datetime.fromtimestamp(now, timezone.utc)
    raw_dir = Path(raw_dir)
    spec = tables.bronze_spec(stream)
    delta_io.ensure_table(spec.path(lake), spec.schema, spec.properties, spec.partition_by)
    table = DeltaTable(spec.path(lake))        # ONE object: the ledger read and every append use it
    ledger = loaded_lines(table)
    files, skipped = parse_stream.list_part_files(raw_dir / stream, now, include_open)
    stats = {"stream": stream, "table": spec.name, "batch_id": batch_id, "files_read": len(files),
             "files_skipped_open": [p.relative_to(raw_dir).as_posix() for p in skipped], "cut_short_files": [],
             "files_with_new_lines": 0, "files_shorter_than_loaded": [], "rows": 0, "commits": [],
             "event_dates": set()}
    cols = {f.name: [] for f in spec.schema}
    chunk = {"files": set(), "dates": set()}

    def flush() -> None:
        n = len(cols["raw_json"])
        if not n:
            return
        data = pa.Table.from_pydict(cols, schema=spec.schema)
        meta = {"step": "bronze", "stream": stream, "batch_id": batch_id, "files": len(chunk["files"]), "rows": n,
                "event_dates": ",".join(sorted(str(d) for d in chunk["dates"]))}
        v = delta_io.append(table, data, meta, app_id=f"bronze_loader:{stream}",
                            writer_properties=lake_config.bronze_writer_properties())
        stats["commits"].append(v)
        stats["rows"] += n
        stats["event_dates"] |= chunk["dates"]
        for values in cols.values():
            values.clear()
        chunk["files"], chunk["dates"] = set(), set()

    for path in files:
        rel = path.relative_to(raw_dir).as_posix()
        m = FILE_RE.match(path.name)
        session = m.group("session") if m else None
        done, n, new = ledger.get(rel, 0), 0, 0
        for line in parse_stream.read_lines(path, stats["cut_short_files"]):
            n += 1
            if n <= done:
                continue
            raw = (line[:-1] if line.endswith(b"\n") else line).decode("utf-8", errors="replace")
            env = envelope(raw)
            # No readable meta.dt (broken line, no meta block): use the date of the dt= folder.
            day = env["meta_dt"].date() if env["meta_dt"] else (folder_date(rel) or NO_DATE)
            for name, value in env.items():
                cols[name].append(value)
            cols["event_date"].append(day)
            cols["stream"].append(stream)
            cols["raw_json"].append(raw)
            cols["source_file"].append(rel)
            cols["source_line"].append(n)
            cols["capture_session"].append(session)
            cols["batch_id"].append(batch_id)
            cols["loaded_at"].append(loaded_at)
            chunk["files"].add(rel)
            chunk["dates"].add(day)
            new += 1
            if len(cols["raw_json"]) >= chunk_rows:
                flush()
        if new:
            stats["files_with_new_lines"] += 1
        if n < done:      # must not happen: a part file only grows
            stats["files_shorter_than_loaded"].append({"file": rel, "lines_now": n, "lines_loaded": done})
            log.warning("%s has %d lines now but %d are loaded", rel, n, done)
    flush()
    log.info("%s: %d new rows from %d of %d files, %d commits, %d open files skipped, %d cut-short files",
             spec.name, stats["rows"], stats["files_with_new_lines"], len(files), len(stats["commits"]),
             len(skipped), len(stats["cut_short_files"]))
    return stats


def run(raw_dir: str | Path, lake: str | Path | None = None, now: float | None = None,
        include_open: bool = False, batch_id: str | None = None) -> dict:
    """Load every stream. Returns {"batch_id", "streams": {stream: stats}, "dates": {stream: set of dates}}."""
    now = time.time() if now is None else now
    batch_id = batch_id or new_batch_id(now)
    streams = {s: load_stream(s, raw_dir, lake, now, include_open, batch_id) for s in config.STREAM_DIRS}
    return {"batch_id": batch_id, "streams": streams,
            "dates": {s: set(st["event_dates"]) for s, st in streams.items()}}
```

### etl/silver_stream.py

```python
"""Silver stream tables: page_change, revert_risk, tag_events and capture_gaps, built from Bronze.

Purpose
    Apply the old parser's rules to the Bronze rows, in the old order
    (parse_stream.parse_stream_dir): bad JSON, canary, not enwiki, no meta.id or meta.dt,
    repeated meta.id. Rows are built with the old pure functions (flat_page_change,
    flat_revert_risk, flat_tags, TableBuilder), so the columns and types are the old ones.

    Work is done per event date (the Bronze partition), only for the dates that the Bronze
    load touched. All Bronze rows of such a date are read again, in the old order
    (source_file, then source_line), so the result does not depend on how the lines arrived.

Writes
    silver/page_change   insert-only MERGE on meta_id, limited to the event_date partition
    silver/tag_events    the same
    silver/revert_risk   one row per rev_id, the earliest meta_dt wins (MERGE, update when earlier)
    silver/capture_gaps  recomputed with parse_stream.find_gaps from all kept events, replaced when changed

    A repeated event has the same meta.id and the same meta.dt, so it lands in the same
    event_date partition as its first copy. This is why the MERGE can name one partition.

Run
    python -m etl.run silver                      # every event date in Bronze
    python -m etl.run silver --dates 2026-10-20   # some dates
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
from deltalake import DeltaTable

from . import delta_io, tables
from .hw2 import config, parse_stream

log = logging.getLogger("silver_stream")

COUNTERS = ["lines", "bad_json", "canary", "other_wiki", "no_meta", "duplicate_meta_id", "rows"]


def _old_order(source_files: list, source_lines: list) -> list[int]:
    """Row positions in the order of the old parser: sorted part files, then line number.

    The old code sorts Path objects, which compare part by part, so we split the path.
    """
    return sorted(range(len(source_files)), key=lambda i: (tuple(source_files[i].split("/")), source_lines[i]))


def kept_events(stream: str, raw_lines: list[str]) -> tuple[pa.Table, dict]:
    """The old rules of parse_stream.parse_stream_dir on raw lines that are already in the old order."""
    _, schema, flatten = parse_stream.STREAMS[stream]
    stats = dict.fromkeys(COUNTERS, 0)
    builder = parse_stream.TableBuilder(schema)
    seen: set[str] = set()
    for raw in raw_lines:
        stats["lines"] += 1
        try:
            ev = json.loads(raw)
        except ValueError:
            stats["bad_json"] += 1
            continue
        if not isinstance(ev, dict):        # the old code would stop here; we count it as bad JSON
            stats["bad_json"] += 1
            continue
        meta = parse_stream._meta(ev)
        if meta.get("domain") == "canary":
            stats["canary"] += 1
            continue
        if parse_stream._wiki(ev) != "enwiki":
            stats["other_wiki"] += 1
            continue
        mid = meta.get("id")
        if not mid or not meta.get("dt"):
            stats["no_meta"] += 1
            continue
        if mid in seen:
            stats["duplicate_meta_id"] += 1
            continue
        seen.add(mid)
        builder.add(flatten(ev))
    table = builder.table()
    stats["rows"] = table.num_rows
    return table, stats


def bronze_dates(stream: str, lake=None) -> set[date]:
    """Every event date that has rows in the Bronze table of the stream."""
    path = tables.bronze_spec(stream).path(lake)
    if not delta_io.exists(path):
        return set()
    return {date.fromisoformat(p["event_date"]) for p in DeltaTable(path).partitions() if p.get("event_date")}


def build_stream(stream: str, dates, lake=None) -> dict:
    """Bronze -> Silver for one stream and the given event dates. One MERGE per date."""
    name = parse_stream.STREAMS[stream][0]
    bronze, silver = tables.bronze_spec(stream), tables.SILVER[name]
    delta_io.ensure_table(silver.path(lake), silver.schema, silver.properties, silver.partition_by)
    total = dict.fromkeys(COUNTERS, 0) | {"table": silver.name, "dates": [], "inserted": 0, "updated": 0,
                                          "commits": []}
    if name == "revert_risk":
        total["duplicate_rev_id"] = 0
    if not dates:
        return total
    bronze_version = delta_io.version(bronze.path(lake))      # every date of this run reads the same Bronze version
    for day in sorted(dates):
        rows = delta_io.read_table(bronze.path(lake), columns=["raw_json", "source_file", "source_line"],
                                   predicate=f"event_date = '{day}'", version=bronze_version)
        order = _old_order(rows.column("source_file").to_pylist(), rows.column("source_line").to_pylist())
        raw = rows.column("raw_json").to_pylist()
        table, stats = kept_events(stream, [raw[i] for i in order])
        del rows, raw
        meta = {"step": "silver_stream", "table": silver.name, "event_date": str(day),
                "bronze_version": bronze_version, "counters": stats}
        if table.num_rows:
            days = pc.unique(pc.cast(table.column("meta_dt"), pa.date32())).to_pylist()
            if days != [day]:
                raise ValueError(f"{bronze.name} partition {day} holds events of {days}: "
                                 "Bronze and Silver disagree on the event date")
        if name == "revert_risk":
            df, n_dup = parse_stream.dedupe_revert_risk(table.to_pandas())
            stats["duplicate_rev_id"] = n_dup
            out = pa.Table.from_pandas(df, schema=silver.schema, preserve_index=False)
            res = delta_io.merge_earliest(silver.path(lake), out, silver.key, "meta_dt", meta)
        else:
            out = table.select([c for c in silver.schema.names if c != "event_date"])
            out = out.append_column(pa.field("event_date", pa.date32()), pa.array([day] * out.num_rows, pa.date32()))
            res = delta_io.merge_insert_new(silver.path(lake), out.cast(silver.schema), silver.key, "event_date", meta)
        for c in stats:
            total[c] += stats[c]
        total["inserted"] += res["inserted"]
        total["updated"] += res.get("updated", 0)
        total["dates"].append(str(day))
        if res["version"] is not None:
            total["commits"].append(res["version"])
    log.info("%s: %s", silver.name, {k: v for k, v in total.items() if k != "dates"})
    return total


def kept_times(stream: str, lake=None) -> pd.DataFrame:
    """meta_dt, topic, partition of every kept event of one stream, in the old order.

    Read from the Bronze envelope columns, so the raw JSON is not parsed again. Only lines that
    hold the text "canary" are parsed, to apply the canary rule exactly.
    """
    q = """SELECT meta_id, meta_dt, kafka_topic, kafka_partition, source_file, source_line,
                  CASE WHEN raw_json LIKE '%canary%' THEN raw_json END AS maybe_canary
           FROM t
           WHERE meta_id IS NOT NULL AND meta_id <> '' AND meta_dt IS NOT NULL AND wiki_id = 'enwiki'"""
    df = delta_io.sql(tables.bronze_spec(stream).path(lake), q).to_pandas()
    if len(df):
        canary = df["maybe_canary"].map(
            lambda raw: raw is not None and parse_stream._meta(json.loads(raw)).get("domain") == "canary")
        df = df[~canary.to_numpy()]
        order = _old_order(df["source_file"].tolist(), df["source_line"].tolist())
        df = df.iloc[order].drop_duplicates("meta_id", keep="first")
    return (df.rename(columns={"kafka_topic": "topic", "kafka_partition": "partition"})
            [["meta_dt", "topic", "partition"]].reset_index(drop=True))


def build_gaps(lake=None) -> dict:
    """Recompute the capture gaps of every stream and replace the table when they changed."""
    spec = tables.SILVER["capture_gaps"]
    delta_io.ensure_table(spec.path(lake), spec.schema, spec.properties)
    gaps, kept = [], {}
    for stream in config.STREAM_DIRS:
        if not delta_io.exists(tables.bronze_spec(stream).path(lake)):
            continue
        times = kept_times(stream, lake)
        kept[stream] = int(len(times))
        gaps.append(parse_stream.find_gaps(stream, times))
    found = [g for g in gaps if len(g)]
    if found:
        df = pd.concat(found, ignore_index=True)
        for c in ("gap_start", "gap_end"):
            df[c] = pd.to_datetime(df[c], utc=True)
        table = pa.Table.from_pandas(df, schema=spec.schema, preserve_index=False)
    else:
        table = spec.schema.empty_table()
    meta = {"step": "silver_stream", "table": spec.name, "rows": table.num_rows, "kept_events": kept,
            "gap_min_s": parse_stream.GAP_MIN_S}
    res = delta_io.replace_if_changed(spec.path(lake), table, spec.key, meta)
    log.info("%s: %d gaps, wrote=%s", spec.name, table.num_rows, res["wrote"])
    return {"table": spec.name, **res}


def build(dates_by_stream: dict | None = None, lake=None) -> dict:
    """Build the four Silver stream tables.

    dates_by_stream: {stream: set of event dates}, as returned by bronze_stream.run()["dates"].
    None means every event date in Bronze (a full pass; it is idempotent).
    """
    out = {}
    for stream in config.STREAM_DIRS:
        dates = bronze_dates(stream, lake) if dates_by_stream is None else dates_by_stream.get(stream, set())
        out[parse_stream.STREAMS[stream][0]] = build_stream(stream, dates, lake)
    out["capture_gaps"] = build_gaps(lake)
    return out
```

### etl/silver_cohorts.py

```python
"""Silver cohort tables: live_revisions, live_revert_links, live_revert_links_all, late_reverts.

Purpose
    build(as_of) answers "what did we know at time as_of". It makes the cohort tables with
    the old code, unchanged:
      1. export the Silver stream tables, filtered to meta_dt <= as_of, into a temporary
         folder as page_change.parquet, revert_risk.parquet and tag_events.parquet, in
         exactly the old schemas, plus the _SUCCESS_parsed.json that label_live.run checks;
      2. call label_live.run(parsed_dir, tables_dir) and late_reverts.run(parsed_dir, tables_dir, history_dir);
      3. load the four Parquet outputs into silver/ Delta tables with replace_if_changed.
         The commit metadata holds as_of, the newest meta_dt used and the row counts.
    Each build is at most one new version per table. A build that gives the same rows as the
    current version writes nothing. An older build is read again by version; find the version
    with delta_io.find_version(path, {"step": "cohorts", "as_of": ...}) or in <lake>/_runs/<as_of>/run.json.

Inputs
    silver/page_change, silver/revert_risk, silver/tag_events
    <history_dir>/<config.HISTORY_SLIM_FILE>   the slim September file (needed for late_reverts)
    history_revisions.parquet                  optional (else late_reverts uses its window fallback)

Outputs
    silver/live_revisions, live_revert_links, live_revert_links_all, late_reverts
    <lake>/_runs/<as_of>/   the JSON summaries of the old run functions and run.json

Run
    python -m etl.run cohorts --as-of 2026-10-27T00:05:00Z --history-dir data/history
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import delta_io, lake_config, tables
from .hw2 import config, label_live, late_reverts, parse_stream

log = logging.getLogger("silver_cohorts")

STEP = "cohorts"
SUMMARY_FILES = ["_SUCCESS_parsed.json", "live_summary.json", "_SUCCESS_live.json",
                 "late_reverts_summary.json", "_SUCCESS_late_reverts.json"]
EXPORT_ORDER = {"page_change": ["meta_dt", "meta_id"], "tag_events": ["meta_dt", "meta_id"],
                "revert_risk": ["rev_id"]}


def to_utc(value) -> datetime:
    """An ISO text ('2026-10-27T00:05:00Z'), a datetime or a pandas Timestamp -> aware UTC datetime."""
    if isinstance(value, str):
        value = config.utc(value)
    elif hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    """Fixed-width UTC text with microseconds, so the text sorts like the time."""
    return None if dt is None else dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def run_dir(as_of: datetime, lake=None) -> Path:
    return lake_config.lake_root(lake) / "_runs" / as_of.strftime("%Y%m%dT%H%M%S.%fZ")


def newest_meta_dt(lake=None) -> datetime | None:
    """The newest meta_dt in the three Silver stream tables (the default as_of)."""
    best = None
    for name in tables.PARSED_SCHEMAS:
        path = tables.SILVER[name].path(lake)
        if delta_io.exists(path):
            v = delta_io.sql(path, "SELECT max(meta_dt) AS m FROM t").column("m")[0].as_py()
            best = v if best is None or (v is not None and v > best) else best
    return best


def export_parsed(as_of: datetime, parsed_dir: Path, lake=None) -> dict:
    """Write the three old parsed files with the events known at as_of. Returns counts and versions."""
    parsed_dir.mkdir(parents=True, exist_ok=True)
    limit = pa.scalar(as_of, type=tables.TS)
    info = {"row_counts": {}, "silver_versions": {}, "newest_meta_dt": {}}
    for name, schema in tables.PARSED_SCHEMAS.items():
        spec = tables.SILVER[name]
        version = delta_io.version(spec.path(lake))
        # event_date <= the date of as_of prunes whole partitions; the exact cut is done in Arrow.
        predicate = f"event_date <= '{as_of.date()}'" if spec.partition_by else None
        t = delta_io.read_table(spec.path(lake), predicate=predicate, version=version)
        t = t.filter(pc.less_equal(t.column("meta_dt"), limit)).select(schema.names).cast(schema)
        t = t.sort_by([(c, "ascending") for c in EXPORT_ORDER[name]])
        parse_stream.write_parquet(t, parsed_dir / f"{name}.parquet")
        info["row_counts"][f"{name}.parquet"] = t.num_rows
        info["silver_versions"][spec.name] = version
        info["newest_meta_dt"][name] = iso(pc.max(t.column("meta_dt")).as_py()) if t.num_rows else None
    parse_stream.write_json({"step": "parsed", "data_version": config.DATA_VERSION, "source": "delta lake export",
                             "created_at": iso(datetime.now(timezone.utc)), "as_of": iso(as_of), **info},
                            parsed_dir / "_SUCCESS_parsed.json")
    return info


def build(as_of=None, history_dir: str | Path | None = None, lake=None,
          history_revisions: str | Path | None = None, keep_dir: str | Path | None = None) -> dict:
    """Build the cohort tables as known at `as_of` (default: the newest meta_dt in Silver).

    history_dir: folder with config.HISTORY_SLIM_FILE. Without it late_reverts is skipped.
    history_revisions: optional history_revisions.parquet for late_reverts' in_history_cohort flag.
    keep_dir: keep the temporary parsed/ and tables/ folders there (for checks).
    """
    as_of = to_utc(as_of) if as_of is not None else newest_meta_dt(lake)
    if as_of is None:
        raise SystemExit("The Silver stream tables are empty. Run the bronze and silver steps first.")
    tmp = Path(tempfile.mkdtemp(prefix="truthlag_cohorts_", dir=keep_dir))
    try:
        parsed_dir, tables_dir = tmp / "parsed", tmp / "tables"
        info = export_parsed(as_of, parsed_dir, lake)
        tables_dir.mkdir()
        if history_revisions is not None:
            shutil.copyfile(history_revisions, tables_dir / "history_revisions.parquet")
        label_live.run(parsed_dir, tables_dir)
        built = ["live_revisions", "live_revert_links", "live_revert_links_all"]
        slim = Path(history_dir) / config.HISTORY_SLIM_FILE if history_dir is not None else None
        if slim is not None and slim.exists():
            late_reverts.run(parsed_dir, tables_dir, Path(history_dir))
            built.append("late_reverts")
        else:
            log.warning("late_reverts skipped: no %s", slim)

        new = {name: pq.read_table(tables_dir / f"{name}.parquet").cast(tables.SILVER[name].schema) for name in built}
        row_counts = {name: t.num_rows for name, t in new.items()}
        out = {"as_of": iso(as_of), "newest_meta_dt": info["newest_meta_dt"]["page_change"], "inputs": info,
               "row_counts": row_counts, "tables": {}}
        for name, table in new.items():
            spec = tables.SILVER[name]
            delta_io.ensure_table(spec.path(lake), spec.schema, spec.properties, spec.partition_by)
            meta = {"step": STEP, "table": spec.name, "as_of": iso(as_of),
                    "newest_meta_dt": info["newest_meta_dt"]["page_change"], "rows": table.num_rows,
                    "row_counts": row_counts, "input_rows": info["row_counts"],
                    "silver_versions": info["silver_versions"], "data_version": config.DATA_VERSION}
            out["tables"][name] = delta_io.replace_if_changed(spec.path(lake), table, spec.key, meta)

        runs = run_dir(as_of, lake)
        runs.mkdir(parents=True, exist_ok=True)
        for f in SUMMARY_FILES:
            src = (parsed_dir if f == "_SUCCESS_parsed.json" else tables_dir) / f
            if src.exists():
                shutil.copyfile(src, runs / f)
        parse_stream.write_json(out, runs / "run.json")
        out["run_dir"] = str(runs)
        log.info("cohorts as of %s: %s", iso(as_of), {n: (r["wrote"], r["version"]) for n, r in out["tables"].items()})
        return out
    finally:
        if keep_dir is None:
            shutil.rmtree(tmp, ignore_errors=True)
```

### etl/run.py

```python
"""Command line for the Bronze and Silver steps.

Run (TRUTHLAG_HW2_DIR and TRUTHLAG_LAKE_DIR must be set)
    python -m etl.run bronze  [--raw-dir DIR] [--include-open]
    python -m etl.run silver  [--dates 2026-10-20,2026-10-21]      # default: every event date in Bronze
    python -m etl.run cohorts [--as-of 2026-10-27T00:05:00Z] [--history-dir DIR] [--history-revisions FILE]
    python -m etl.run all     [--raw-dir DIR] [--as-of ISO] [--history-dir DIR]

`all` runs bronze, then silver for the event dates that bronze touched, then cohorts.
Without --as-of the cohort step uses the newest meta_dt in Silver, so a re-run without new
data writes nothing.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

from . import bronze_stream, silver_cohorts, silver_stream
from .hw2 import config


def _show(obj) -> None:
    print(json.dumps(obj, indent=2, default=lambda o: sorted(str(x) for x in o) if isinstance(o, set) else str(o)))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m etl.run", description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["bronze", "silver", "cohorts", "all"])
    ap.add_argument("--lake", type=Path, default=None, help="lake root (default: TRUTHLAG_LAKE_DIR)")
    ap.add_argument("--raw-dir", type=Path, default=config.RAW_STREAM_DIR)
    ap.add_argument("--include-open", action="store_true",
                    help="also read part files changed in the last OPEN_FILE_GRACE_S seconds")
    ap.add_argument("--dates", default=None, help="silver: comma-separated event dates (default: all)")
    ap.add_argument("--as-of", default=None, help="cohorts: use events with meta_dt <= this UTC time")
    ap.add_argument("--history-dir", type=Path, default=config.HISTORY_DIR)
    ap.add_argument("--history-revisions", type=Path, default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", stream=sys.stdout)

    dates = None
    if args.step in ("bronze", "all"):
        b = bronze_stream.run(args.raw_dir, lake=args.lake, include_open=args.include_open)
        dates = b["dates"]
        _show({"bronze": b["streams"]})
    if args.step in ("silver", "all"):
        if args.step == "silver" and args.dates:
            days = {date.fromisoformat(d) for d in args.dates.split(",")}
            dates = {s: days for s in config.STREAM_DIRS}
        _show({"silver": silver_stream.build(dates, lake=args.lake)})
    if args.step in ("cohorts", "all"):
        _show({"cohorts": silver_cohorts.build(args.as_of, history_dir=args.history_dir, lake=args.lake,
                                               history_revisions=args.history_revisions)})


if __name__ == "__main__":
    main()
```

## Parity test

File `proto/tests_lake/test_parity.py` in the zip. Command (RAN, final state of the code):

```bash
cd SCRATCH/proto
TRUTHLAG_HW2_DIR=SCRATCH/ec-hw2 PYTHONDONTWRITEBYTECODE=1 TRUTHLAG_TEST_REPORT=SCRATCH/out/test_report.json \
  SCRATCH/venv/bin/python -m pytest tests_lake/test_parity.py -v -p no:cacheprovider --basetemp=SCRATCH/pytest_tmp/final
```

Result (RAN): **`16 passed in 11.90s`**. The same file unpacked from the zip into another folder: `16 passed in 12.27s`.

```text
tests_lake/test_parity.py::test_p1_old_pipeline_row_counts PASSED
tests_lake/test_parity.py::test_p2_silver_tables_equal_old_files PASSED
tests_lake/test_parity.py::test_p2_bronze_holds_every_line_unchanged PASSED
tests_lake/test_parity.py::test_p2_table_properties_and_commit_metadata PASSED
tests_lake/test_parity.py::test_p3_second_run_makes_no_new_version PASSED
tests_lake/test_parity.py::test_p4_grown_file_adds_only_new_lines PASSED
tests_lake/test_parity.py::test_p5_two_arrivals_give_the_one_batch_tables[by_time] PASSED
tests_lake/test_parity.py::test_p5_two_arrivals_give_the_one_batch_tables[later_half_first] PASSED
tests_lake/test_parity.py::test_p5_earlier_score_that_arrives_later_replaces_the_row PASSED
tests_lake/test_parity.py::test_p6_as_of_builds_and_time_travel PASSED
tests_lake/test_parity.py::test_p7_cut_short_and_open_files PASSED
tests_lake/test_parity.py::test_the_comparison_sees_small_differences PASSED
tests_lake/test_parity.py::test_bad_lines_are_kept_in_bronze_and_dropped_in_silver_like_the_old_parser PASSED
tests_lake/test_parity.py::test_bronze_chunked_commits_and_a_crash_between_them PASSED
tests_lake/test_parity.py::test_two_loaders_on_one_snapshot_cannot_both_commit PASSED
tests_lake/test_parity.py::test_cli_all PASSED
============================= 16 passed in 11.90s ==============================
```

**How dtypes are normalised before two tables are compared** (`assert_same_table`): (1) the new table is read through `DeltaTable.scan` and string_view becomes string; (2) the new table is cast to the Arrow schema of the old Parquet file (for the cohort tables this turns Delta's microseconds into the old file's nanoseconds; the stream tables already have the same types); (3) both are sorted by the key; (4) each column is compared with Arrow equality, so null equals null, list columns are compared element by element and times are compared as integers. `test_the_comparison_sees_small_differences` proves that a shift of 1 microsecond, one extra list item, one null and one missing row each make the comparison fail. `capture_gaps` is compared in pandas against the old CSV after parsing its two time columns to `datetime64[us, UTC]`.

The numbers the tests saw are saved in `SCRATCH/out/test_report.json`.

### tests_lake/test_parity.py

```python
"""Parity proof: the delta-rs Bronze / Silver prototype (package `etl`) against the old pandas pipeline.

Run (from the folder that holds etl/ and tests_lake/)
    TRUTHLAG_HW2_DIR=<the ec-hw2 folder> PYTHONDONTWRITEBYTECODE=1 \
        <venv>/bin/python -m pytest tests_lake/test_parity.py -q -p no:cacheprovider

The raw files are built exactly as the `pipeline` fixture of ec-hw2/tests/test_stream.py does
(scenario_events, write_part, one repeated event in a second session file, the slim history frame).
Set TRUTHLAG_TEST_REPORT=<file.json> to save the numbers the tests saw.

How two tables are compared (assert_same_table)
    1. The new table is read through DeltaTable.scan; string_view becomes string.
    2. The new table is cast to the Arrow schema of the old Parquet file. For the cohort tables
       this turns Delta's microseconds into the old file's nanoseconds (no rounding possible).
    3. Both tables are sorted by the key.
    4. Every column is compared with Arrow equality: null equals null, list columns are
       compared element by element, times are compared as integers (so to the microsecond).
"""
from __future__ import annotations

import gzip
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from deltalake import DeltaTable
from deltalake.exceptions import CommitFailedError

PROTO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROTO_DIR))                                   # the folder that holds etl/
from etl import bronze_stream, delta_io, lake_config, silver_cohorts, silver_stream, tables  # noqa: E402
from etl.hw2 import HW2_DIR, config, label_live, late_reverts, parse_stream  # noqa: E402
from tests import test_stream as ts  # noqa: E402   the old fixtures (ec-hw2/tests/test_stream.py)

EXPECTED = {"page_change": 38, "revert_risk": 2, "tag_events": 7, "live_revisions": 32,
            "live_revert_links": 9, "live_revert_links_all": 17, "late_reverts": 5}
SESSION_A, SESSION_B, SESSION_C = "20261024T000000-aaaaaa", "20261024T010000-bbbbbb", "20261025T000000-cccccc"
MID = ts.T0 + 45 * ts.S            # a time in the middle of the scenario (2026-10-20T10:00:45Z)
PC, TAGS, RISK = config.STREAM_PAGE_CHANGE, config.STREAM_TAGS, config.STREAM_REVERT_RISK
SEEN: dict = {}                    # numbers for the report


@pytest.fixture(scope="session", autouse=True)
def _report():
    yield
    target = os.environ.get("TRUTHLAG_TEST_REPORT")
    if target:
        Path(target).write_text(json.dumps(SEEN, indent=2, default=str, sort_keys=True) + "\n")


# --------------------------------------------------------------------------
# Builders and runners
# --------------------------------------------------------------------------
def write_scenario(raw: Path) -> None:
    """The raw files of the old `pipeline` fixture."""
    pc, tags, risk = ts.scenario_events()
    ts.write_part(raw, PC, pc)
    ts.write_part(raw, PC, [pc[4]], session=SESSION_B)       # the capture repeats one event after a reconnect
    ts.write_part(raw, TAGS, tags)
    ts.write_part(raw, RISK, risk)


def write_slim(hist: Path) -> None:
    hist.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(ts.slim_frame(), schema=pa.schema(
        [(c, pa.string()) for c in config.HISTORY_SLIM_COLUMNS]), preserve_index=False)
    pq.write_table(table, hist / config.HISTORY_SLIM_FILE)


def run_old(raw: Path, out: Path, hist: Path, include_open: bool = False) -> dict:
    parsed, tabs = out / "parsed", out / "tables"
    parse = parse_stream.run(raw, parsed, include_open=include_open)
    live = label_live.run(parsed, tabs)
    late = late_reverts.run(parsed, tabs, hist)
    return {"parsed": parsed, "tables": tabs, "parse": parse, "live": live, "late": late}


def run_new(raw: Path, lake: Path, hist: Path, as_of=None, include_open: bool = False) -> dict:
    b = bronze_stream.run(raw, lake=lake, include_open=include_open)
    s = silver_stream.build(b["dates"], lake=lake)
    c = silver_cohorts.build(as_of, history_dir=hist, lake=lake)
    return {"bronze": b, "silver": s, "cohorts": c}


def split_by_meta_dt(events: list, cut) -> tuple[list, list]:
    first = [e for e in events if pd.Timestamp(e["meta"]["dt"]) <= cut]
    return first, [e for e in events if pd.Timestamp(e["meta"]["dt"]) > cut]


# --------------------------------------------------------------------------
# Reading and comparing
# --------------------------------------------------------------------------
def old_table(old: dict, name: str) -> pa.Table:
    folder = old["parsed"] if name in tables.PARSED_SCHEMAS else old["tables"]
    return pq.read_table(folder / f"{name}.parquet")


def new_table(lake: Path, name: str, version: int | None = None) -> pa.Table:
    spec = tables.SILVER[name]
    t = delta_io.read_table(spec.path(lake), version=version)
    for f in t.schema:
        if pa.types.is_timestamp(f.type):
            assert f.type == pa.timestamp("us", tz="UTC"), (name, f)      # Delta stores microseconds, UTC
    return t.drop_columns(list(spec.partition_by))                        # event_date is not in the old files


def assert_same_table(old: pa.Table, new: pa.Table, key, label: str) -> None:
    assert new.schema.names == old.schema.names, f"{label}: columns differ"
    new = new.cast(old.schema.remove_metadata())
    old = old.replace_schema_metadata(None)
    assert old.num_rows == new.num_rows, f"{label}: {old.num_rows} old rows, {new.num_rows} new rows"
    o, n = delta_io._nan_to_null(delta_io.canonical(old, key)), delta_io._nan_to_null(delta_io.canonical(new, key))
    for name in o.schema.names:
        a, b = o.column(name).combine_chunks(), n.column(name).combine_chunks()
        if not a.equals(b):
            bad = [(k, x, y) for k, x, y in zip(o.select(list(key)).to_pylist(), a.to_pylist(), b.to_pylist()) if x != y]
            raise AssertionError(f"{label}.{name}: {len(bad)} rows differ, first: {bad[:3]}")


def old_gaps(old: dict) -> pd.DataFrame:
    df = pd.read_csv(old["parsed"] / "capture_gaps.csv")
    for c in ("gap_start", "gap_end"):
        df[c] = pd.to_datetime(df[c], utc=True, format="ISO8601").astype("datetime64[us, UTC]")
    return df.sort_values(["stream", "gap_start"]).reset_index(drop=True)


def check_parity(old: dict, lake: Path, label: str, names=tuple(EXPECTED)) -> dict:
    """Every Silver table equals the old file. Returns the row counts."""
    counts = {}
    for name in names:
        new = new_table(lake, name)
        assert_same_table(old_table(old, name), new, tables.SILVER[name].key, f"{label}:{name}")
        counts[name] = new.num_rows
    gaps_new = delta_io.read_pandas(tables.SILVER["capture_gaps"].path(lake), sort_by=["stream", "gap_start"])
    gaps_old = old_gaps(old)
    assert str(gaps_new["gap_start"].dtype) == "datetime64[us, UTC]"
    pd.testing.assert_frame_equal(gaps_old, gaps_new, check_dtype=False)
    counts["capture_gaps"] = len(gaps_new)
    return counts


def versions(lake: Path) -> dict:
    return {name: delta_io.version(spec.path(lake)) for name, spec in tables.ALL.items()
            if delta_io.exists(spec.path(lake))}


def row_counts(lake: Path) -> dict:
    return {name: delta_io.read_table(spec.path(lake), columns=[spec.schema.names[0]]).num_rows
            for name, spec in tables.ALL.items() if delta_io.exists(spec.path(lake))}


def bronze(lake: Path, stream: str, **kw) -> pd.DataFrame:
    return delta_io.read_pandas(tables.bronze_spec(stream).path(lake), sort_by=["source_file", "source_line"], **kw)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """One raw folder; the old pipeline (P1) and the new pipeline (P2) run on it."""
    root = tmp_path_factory.mktemp("world")
    raw, hist, lake = root / "raw", root / "history", root / "lake"
    write_scenario(raw)
    write_slim(hist)
    old = run_old(raw, root / "old", hist)
    new = run_new(raw, lake, hist)
    return {"root": root, "raw": raw, "hist": hist, "lake": lake, "old": old, "new": new}


# --------------------------------------------------------------------------
# P1  the old pipeline
# --------------------------------------------------------------------------
def test_p1_old_pipeline_row_counts(world):
    got = {name: old_table(world["old"], name).num_rows for name in EXPECTED}
    SEEN["P1_old_row_counts"] = got
    assert got == EXPECTED
    assert world["old"]["parse"]["streams"][PC]["duplicate_meta_id"] == 1


# --------------------------------------------------------------------------
# P2  the new pipeline gives the same tables
# --------------------------------------------------------------------------
def test_p2_silver_tables_equal_old_files(world):
    counts = check_parity(world["old"], world["lake"], "P2")
    SEEN["P2_new_row_counts"] = counts
    assert {k: counts[k] for k in EXPECTED} == EXPECTED and counts["capture_gaps"] == 4
    s = world["new"]["silver"]
    old_stats = world["old"]["parse"]["streams"]
    for stream in config.STREAM_DIRS:                 # the counters of the old rules agree too
        name = parse_stream.STREAMS[stream][0]
        for c in silver_stream.COUNTERS:
            assert s[name][c] == old_stats[stream][c], (name, c)
    assert s["revert_risk"]["duplicate_rev_id"] == old_stats[RISK]["duplicate_rev_id"] == 1
    SEEN["P2_counters"] = {n: {c: s[n][c] for c in silver_stream.COUNTERS} for n in tables.PARSED_SCHEMAS}


def test_p2_bronze_holds_every_line_unchanged(world):
    lake, raw = world["lake"], world["raw"]
    lines = {}
    for stream, n_lines in ((PC, 39), (RISK, 3), (TAGS, 7)):
        df = bronze(lake, stream)
        assert list(df.columns) == tables.BRONZE_SCHEMA.names and len(df) == n_lines
        assert not df.duplicated(["source_file", "source_line"]).any()
        for rel, part in df.groupby("source_file"):
            with gzip.open(raw / rel, "rb") as f:
                want = [line[:-1].decode() for line in f]
            assert part["raw_json"].tolist() == want                       # the line, unchanged
            assert part["source_line"].tolist() == list(range(1, len(want) + 1))
        ev = df["raw_json"].map(json.loads)
        assert (df["meta_id"] == ev.map(lambda e: e["meta"]["id"])).all()
        assert (df["meta_dt"] == pd.to_datetime(ev.map(lambda e: e["meta"]["dt"]), utc=True)).all()
        assert (df["event_date"] == df["meta_dt"].dt.date).all()            # partition = UTC date of meta_dt
        assert (df["wiki_id"] == "enwiki").all() and (df["stream"] == stream).all()   # tags: from `database`
        assert (df["kafka_topic"] == f"eqiad.{stream}").all() and (df["kafka_partition"] == 0).all()
        assert (df["kafka_offset"] == 1).all() and df["batch_id"].nunique() == 1
        assert str(df["meta_dt"].dtype) == str(df["loaded_at"].dtype) == "datetime64[us, UTC]"
        lines[stream] = len(df)
    assert set(bronze(lake, PC)["capture_session"]) == {SESSION_A, SESSION_B}
    SEEN["P2_bronze_rows"] = lines


def test_p2_table_properties_and_commit_metadata(world):
    lake = world["lake"]
    for name, spec in tables.ALL.items():
        t = DeltaTable(spec.path(lake))
        conf = t.metadata().configuration
        for k, v in lake_config.KEEP_HISTORY.items():
            assert conf[k] == v, (name, k)
        assert t.metadata().partition_columns == list(spec.partition_by)
        p = t.protocol()
        features = set(p.reader_features or []) | set(p.writer_features or [])
        assert not features & set(lake_config.FORBIDDEN_FEATURES), (name, features)
        assert p.min_reader_version == 1 and p.min_writer_version <= 2, (name, p.min_reader_version, p.min_writer_version)
        SEEN.setdefault("P2_protocol", {})[name] = [p.min_reader_version, p.min_writer_version, sorted(features)]
    path = tables.bronze_spec(PC).path(lake)
    conf = DeltaTable(path).metadata().configuration
    assert conf["delta.appendOnly"] == "true"
    assert conf["delta.dataSkippingStatsColumns"] == ",".join(lake_config.BRONZE_STATS_COLUMNS)
    adds = [json.loads(line)["add"] for f in sorted(Path(path, "_delta_log").glob("*.json"))
            for line in f.read_text().splitlines() if '"add"' in line]
    assert adds and all(set(json.loads(a["stats"])["minValues"]) <= set(lake_config.BRONZE_STATS_COLUMNS) for a in adds)
    codecs = {pq.ParquetFile(Path(path, a["path"])).metadata.row_group(0).column(0).compression for a in adds}
    assert codecs == {"ZSTD"}
    h = delta_io.history(path)[0]                                           # the Bronze commit
    assert h["step"] == "bronze" and h["stream"] == PC and h["rows"] == "39" and h["files"] == "2"
    assert h["batch_id"] == world["new"]["bronze"]["batch_id"] and h["event_dates"] == "2026-10-19,2026-10-20"
    with pytest.raises(CommitFailedError):                                  # appendOnly is enforced by delta-rs
        DeltaTable(path).delete("meta_id = 'pc-101'")
    h = delta_io.history(tables.SILVER["live_revert_links"].path(lake))[0]  # a cohort commit
    assert h["step"] == "cohorts" and h["as_of"] == "2026-10-20T10:20:02.000000Z"
    assert h["newest_meta_dt"] == "2026-10-20T10:01:42.000000Z" and h["rows"] == "9"
    assert json.loads(h["row_counts"]) == {k: EXPECTED[k] for k in tables.COHORT_TABLES}
    runs = Path(world["new"]["cohorts"]["run_dir"])
    assert {f.name for f in runs.iterdir()} == set(silver_cohorts.SUMMARY_FILES) | {"run.json"}
    SEEN["P2_bronze_stats_columns"] = sorted(json.loads(adds[0]["stats"])["minValues"])
    SEEN["P2_cohort_commit"] = {k: h[k] for k in ("step", "as_of", "newest_meta_dt", "rows", "row_counts")}


# --------------------------------------------------------------------------
# P3  a second run changes nothing
# --------------------------------------------------------------------------
def test_p3_second_run_makes_no_new_version(world):
    lake, raw, hist = world["lake"], world["raw"], world["hist"]
    before_v, before_n = versions(lake), row_counts(lake)
    commit_files = sorted(str(p) for p in lake.rglob("_delta_log/*.json"))
    b = bronze_stream.run(raw, lake=lake)
    assert all(st["rows"] == 0 and st["commits"] == [] for st in b["streams"].values())
    assert all(d == set() for d in b["dates"].values())
    s = silver_stream.build(b["dates"], lake=lake)                 # nothing touched
    full = silver_stream.build(None, lake=lake)                    # every date again, from Bronze
    for res in (s, full):
        assert all(res[n]["inserted"] == 0 and res[n]["updated"] == 0 and res[n]["commits"] == []
                   for n in tables.PARSED_SCHEMAS)
        assert res["capture_gaps"]["wrote"] is False
    assert full["page_change"]["lines"] == 39 and full["page_change"]["rows"] == 38   # it did read Bronze again
    c = silver_cohorts.build(None, history_dir=hist, lake=lake)
    c2 = silver_cohorts.build("2026-10-20T10:20:02Z", history_dir=hist, lake=lake)
    assert all(r["wrote"] is False for res in (c, c2) for r in res["tables"].values())
    assert versions(lake) == before_v and row_counts(lake) == before_n
    assert sorted(str(p) for p in lake.rglob("_delta_log/*.json")) == commit_files
    SEEN["P3_versions"] = before_v
    SEEN["P3_row_counts"] = before_n


# --------------------------------------------------------------------------
# P4  a raw file that grew
# --------------------------------------------------------------------------
def test_p4_grown_file_adds_only_new_lines(tmp_path):
    raw, lake, hist = tmp_path / "raw", tmp_path / "lake", tmp_path / "history"
    write_slim(hist)
    pc, _, _ = ts.scenario_events()
    p = ts.write_part(raw, PC, pc[:20])
    b1 = bronze_stream.run(raw, lake=lake)
    silver_stream.build(b1["dates"], lake=lake)
    path = tables.bronze_spec(PC).path(lake)
    assert b1["streams"][PC]["rows"] == 20 and delta_io.version(path) == 1
    first = bronze(lake, PC)

    assert ts.write_part(raw, PC, pc, mtime=ts.OLD + 600) == p     # the same file, 18 more lines, newer mtime
    b2 = bronze_stream.run(raw, lake=lake)
    st = b2["streams"][PC]
    assert st["rows"] == 18 and st["commits"] == [2] and st["files_with_new_lines"] == 1
    assert b2["streams"][RISK]["rows"] == 0 and b2["streams"][TAGS]["rows"] == 0
    df = bronze(lake, PC)
    assert df["source_line"].tolist() == list(range(1, 39)) and df["source_file"].nunique() == 1
    assert df["batch_id"].tolist() == [b1["batch_id"]] * 20 + [b2["batch_id"]] * 18
    pd.testing.assert_frame_equal(df.iloc[:20].reset_index(drop=True), first)     # old rows untouched
    h = delta_io.history(path)[0]
    assert (h["version"], h["rows"], h["files"], h["batch_id"]) == (2, "18", "1", b2["batch_id"])

    silver_stream.build(b2["dates"], lake=lake)
    old = tmp_path / "old"
    parse_stream.run(raw, old / "parsed")
    assert_same_table(pq.read_table(old / "parsed" / "page_change.parquet"), new_table(lake, "page_change"),
                      ("meta_id",), "P4:page_change")
    b3 = bronze_stream.run(raw, lake=lake)
    assert b3["streams"][PC]["rows"] == 0 and delta_io.version(path) == 2
    SEEN["P4"] = {"first_load_rows": 20, "second_load_rows": st["rows"], "bronze_rows": len(df),
                  "bronze_version": delta_io.version(path), "third_load_rows": b3["streams"][PC]["rows"]}


# --------------------------------------------------------------------------
# P5  the events arrive in two batches
# --------------------------------------------------------------------------
@pytest.mark.parametrize("order", ["by_time", "later_half_first"])
def test_p5_two_arrivals_give_the_one_batch_tables(world, tmp_path, order):
    raw, lake, hist = tmp_path / "raw", tmp_path / "lake", world["hist"]
    pc, tags, risk = ts.scenario_events()
    halves = [split_by_meta_dt(events, MID) for events in (pc, tags, risk)]
    arrivals = [[h[0] for h in halves], [h[1] for h in halves]]
    if order == "later_half_first":
        arrivals.reverse()
    seen = {"arrival_rows": []}
    for i, (session, (a_pc, a_tags, a_risk)) in enumerate(zip((SESSION_A, SESSION_C), arrivals)):
        for stream, events in ((PC, a_pc), (TAGS, a_tags), (RISK, a_risk)):
            if events:
                ts.write_part(raw, stream, events, session=session)
        if i == 1:
            ts.write_part(raw, PC, [pc[4]], session=SESSION_B)             # the repeated event
        res = run_new(raw, lake, hist)
        seen["arrival_rows"].append({parse_stream.STREAMS[s][0]: st["rows"] for s, st in res["bronze"]["streams"].items()})
        seen.setdefault("risk", []).append((res["silver"]["revert_risk"]["inserted"], res["silver"]["revert_risk"]["updated"]))
    # 35 page_change + 2 tag + 3 risk events have meta_dt <= MID; 3 + 5 + 0 come later; + 1 repeated event
    assert [sum(r.values()) for r in seen["arrival_rows"]] == ([40, 9] if order == "by_time" else [8, 41])
    counts = check_parity(world["old"], lake, f"P5:{order}")               # equal to the old one-batch files
    for name in EXPECTED:                                                  # and to the one-batch lake of P2
        assert_same_table(new_table(world["lake"], name), new_table(lake, name), tables.SILVER[name].key, f"P5b:{name}")
    risk_new = delta_io.read_pandas(tables.SILVER["revert_risk"].path(lake)).set_index("rev_id")
    assert risk_new.loc[102, "prob_true"] == 0.9
    seen["final_row_counts"] = counts
    seen["versions"] = versions(lake)
    SEEN[f"P5_{order}"] = seen


def test_p5_earlier_score_that_arrives_later_replaces_the_row(tmp_path):
    """The update branch of the 'earliest wins' MERGE, and its no-op re-run."""
    raw, lake = tmp_path / "raw", tmp_path / "lake"
    _, _, risk = ts.scenario_events()
    ts.write_part(raw, RISK, [risk[1]], session=SESSION_A)                 # rr-2: rev 102, t+20 s, 0.5
    b = bronze_stream.run(raw, lake=lake)
    s1 = silver_stream.build(b["dates"], lake=lake)["revert_risk"]
    ts.write_part(raw, RISK, [risk[0], risk[2]], session=SESSION_C)        # rr-1: rev 102, t+13 s, 0.9; rr-3
    b = bronze_stream.run(raw, lake=lake)
    s2 = silver_stream.build(b["dates"], lake=lake)["revert_risk"]
    path = tables.SILVER["revert_risk"].path(lake)
    assert (s1["inserted"], s1["updated"]) == (1, 0) and (s2["inserted"], s2["updated"]) == (1, 1)
    df = delta_io.read_pandas(path, sort_by=["rev_id"])
    assert df["rev_id"].tolist() == [102, 103] and df["prob_true"].tolist() == [0.9, 0.2]
    assert df["meta_dt"].iloc[0] == ts.T0 + 13 * ts.S
    v = delta_io.version(path)
    s3 = silver_stream.build(None, lake=lake)["revert_risk"]              # again: nothing is earlier now
    assert (s3["inserted"], s3["updated"], s3["commits"]) == (0, 0, []) and delta_io.version(path) == v
    old_v1 = delta_io.read_pandas(path, version=1)                         # the earlier belief is still readable
    assert old_v1["prob_true"].tolist() == [0.5]
    SEEN["P5_update_branch"] = {"run1": (s1["inserted"], s1["updated"]), "run2": (s2["inserted"], s2["updated"]),
                                "rerun": (s3["inserted"], s3["updated"]), "version": v}


# --------------------------------------------------------------------------
# P6  as_of and time travel
# --------------------------------------------------------------------------
def test_p6_as_of_builds_and_time_travel(world, tmp_path):
    raw, hist, lake = world["raw"], world["hist"], tmp_path / "lake"
    b = bronze_stream.run(raw, lake=lake)
    silver_stream.build(b["dates"], lake=lake)
    c_mid = silver_cohorts.build(MID, history_dir=hist, lake=lake)
    c_end = silver_cohorts.build(None, history_dir=hist, lake=lake)
    assert c_mid["as_of"] == "2026-10-20T10:00:45.000000Z" and c_end["as_of"] == "2026-10-20T10:20:02.000000Z"
    for name in tables.COHORT_TABLES:                                      # each build is one version per table
        assert c_mid["tables"][name] == {"wrote": True, "version": 1, "rows": c_mid["row_counts"][name]}
        assert c_end["tables"][name] == {"wrote": True, "version": 2, "rows": EXPECTED[name]}
        assert delta_io.version(tables.SILVER[name].path(lake)) == 2

    # the old pipeline, run only on the events with meta_dt <= MID
    raw_mid = tmp_path / "raw_mid"
    pc, tags, risk = ts.scenario_events()
    for stream, events in ((PC, pc), (TAGS, tags), (RISK, risk)):
        ts.write_part(raw_mid, stream, split_by_meta_dt(events, MID)[0])
    old_mid = run_old(raw_mid, tmp_path / "old_mid", hist)

    found = {}
    for name in tables.COHORT_TABLES:
        path = tables.SILVER[name].path(lake)
        v_mid = delta_io.find_version(path, {"step": "cohorts", "as_of": c_mid["as_of"]})
        v_end = delta_io.find_version(path, {"step": "cohorts", "as_of": c_end["as_of"]})
        assert (v_mid, v_end) == (1, 2)
        found[name] = {"as_of_mid": v_mid, "as_of_end": v_end}
        assert_same_table(old_table(old_mid, name), new_table(lake, name, version=v_mid),
                          tables.SILVER[name].key, f"P6:mid:{name}")
        assert_same_table(old_table(world["old"], name), new_table(lake, name, version=v_end),
                          tables.SILVER[name].key, f"P6:end:{name}")
    assert delta_io.find_version(tables.SILVER["live_revert_links"].path(lake), {"as_of": "2026-10-20T10:00:46.000000Z"}) is None
    assert json.loads((Path(c_mid["run_dir"]) / "run.json").read_text())["tables"]["live_revert_links"]["version"] == 1

    # what did we know at MID? Revision 102 was not known to be reverted yet (104 was published at 10:01:02).
    links = tables.SILVER["live_revert_links"].path(lake)
    at_mid = delta_io.read_pandas(links, version=found["live_revert_links"]["as_of_mid"]).set_index("reverted_rev_id")
    at_end = delta_io.read_pandas(links, version=found["live_revert_links"]["as_of_end"]).set_index("reverted_rev_id")
    later_only = sorted(set(at_end.index) - set(at_mid.index))
    assert 102 in later_only and 103 in later_only and 302 in at_mid.index
    assert at_end.loc[102, "reverting_rev_id"] == 104 and at_end.loc[102, "known_at"] == ts.T0 + 62 * ts.S
    assert at_end.loc[102, "known_at"] > MID and (at_mid["known_at"] <= MID).all()
    h = {x["version"]: x for x in delta_io.history(links)}
    assert h[1]["newest_meta_dt"] == "2026-10-20T10:00:42.000000Z" and h[2]["newest_meta_dt"] == "2026-10-20T10:01:42.000000Z"
    SEEN["P6"] = {"as_of_mid": c_mid["as_of"], "as_of_end": c_end["as_of"], "versions_found": found,
                  "rows_at_mid": c_mid["row_counts"], "rows_at_end": c_end["row_counts"],
                  "old_pipeline_rows_at_mid": {n: old_table(old_mid, n).num_rows for n in tables.COHORT_TABLES},
                  "reverted_known_at_mid": sorted(int(x) for x in at_mid.index),
                  "reverted_known_only_at_end": [int(x) for x in later_only]}


# --------------------------------------------------------------------------
# P7  a cut-short gzip file and a file that is still open
# --------------------------------------------------------------------------
def _lines(n: int, start: int) -> list[bytes]:
    return [(json.dumps(ts.pc_ev(start + i, 1, ts.T0 + i * ts.S)) + "\n").encode() for i in range(n)]


def test_p7_cut_short_and_open_files(tmp_path):
    raw, lake = tmp_path / "raw", tmp_path / "lake"
    # (a) no gzip end marker: 40 lines sync-flushed, 10 more still in the compressor
    a_lines = _lines(50, 10_000)
    buf = io.BytesIO()
    gz = gzip.GzipFile(fileobj=buf, mode="wb")
    for line in a_lines[:40]:
        gz.write(line)
    gz.flush()
    a = ts.part_path(raw, PC, ts.T0, session="20261024T000000-aaaaaa")
    a.write_bytes(buf.getvalue())
    os.utime(a, (ts.OLD, ts.OLD))
    # (b) a complete file cut at 60 % of its bytes
    full = gzip.compress(b"".join(_lines(400, 20_000)))
    b = ts.part_path(raw, PC, ts.T0, session="20261024T000001-bbbbbb")
    b.write_bytes(full[: int(len(full) * 0.6)])
    os.utime(b, (ts.OLD, ts.OLD))
    # (c) a file changed just now: it may still be open
    c = ts.part_path(raw, PC, ts.T0, session="20261024T000002-cccccc")
    c.write_bytes(gzip.compress(b"".join(_lines(5, 30_000))))
    os.utime(c, (time.time(), time.time()))

    def both(include_open: bool, tag: str):
        old = parse_stream.run(raw, tmp_path / f"old_{tag}", include_open=include_open)["streams"][PC]
        res = bronze_stream.run(raw, lake=lake, include_open=include_open)
        silver_stream.build(res["dates"], lake=lake)
        assert_same_table(pq.read_table(tmp_path / f"old_{tag}" / "page_change.parquet"),
                          new_table(lake, "page_change"), ("meta_id",), f"P7:{tag}")
        return old, res["streams"][PC]

    old, new = both(False, "closed")
    kept_b = old["lines"] - 40
    assert 0 < kept_b < 400 and old["cut_short_file_count"] == 2 and old["files_skipped_open_count"] == 1
    assert new["rows"] == old["lines"] == old["rows"]                       # the complete lines, like the old reader
    assert sorted(x["lines_kept"] for x in new["cut_short_files"]) == sorted([40, kept_b])
    assert new["files_skipped_open"] == [c.relative_to(raw).as_posix()]
    df = bronze(lake, PC)
    assert df.groupby("source_file")["source_line"].max().to_dict() == {
        a.relative_to(raw).as_posix(): 40, b.relative_to(raw).as_posix(): kept_b}
    assert df["raw_json"].map(json.loads).map(lambda e: e["revision"]["rev_id"]).tolist() == \
        list(range(10_000, 10_040)) + list(range(20_000, 20_000 + kept_b))  # clean prefixes

    old2, new2 = both(True, "open")                                          # now the open file is read too
    assert new2["rows"] == 5 and old2["lines"] == old["lines"] + 5 and new2["files_skipped_open"] == []

    a.write_bytes(gzip.compress(b"".join(a_lines)))                          # the capture closed file (a)
    os.utime(a, (ts.OLD + 600, ts.OLD + 600))
    old3, new3 = both(True, "completed")
    assert new3["rows"] == 10 and old3["lines"] == old2["lines"] + 10        # only lines 41..50 are new
    df = bronze(lake, PC)
    assert len(df) == old3["lines"] and not df.duplicated(["source_file", "source_line"]).any()
    SEEN["P7"] = {"old_lines_closed": old["lines"], "bronze_rows_closed": new["rows"], "kept_of_truncated_400": kept_b,
                  "cut_short_files": len(new["cut_short_files"]), "skipped_open": len(new["files_skipped_open"]),
                  "rows_added_with_include_open": new2["rows"], "rows_added_after_file_completed": new3["rows"],
                  "bronze_rows_final": len(df)}


# --------------------------------------------------------------------------
# Extras
# --------------------------------------------------------------------------
def test_the_comparison_sees_small_differences(world):
    """assert_same_table must fail on one microsecond, one list item, one null and one missing row."""
    old = old_table(world["old"], "tag_events")
    new = new_table(world["lake"], "tag_events")
    key = ("meta_id",)
    assert_same_table(old, new, key, "same")
    i = new.schema.get_field_index("meta_dt")
    shifted = pa.array([v + (1 if n == 0 else 0) for n, v in enumerate(new.column(i).cast(pa.int64()).to_pylist())],
                       pa.int64()).cast(new.schema.field(i).type)
    j = new.schema.get_field_index("tags")
    tags = new.column(j).to_pylist()
    other_tags = pa.array([tags[0] + ["x"]] + tags[1:], new.schema.field(j).type)
    k = new.schema.get_field_index("rev_id")
    with_null = pa.array([None] + new.column(k).to_pylist()[1:], pa.int64())
    for bad in (new.set_column(i, new.schema.field(i), shifted), new.set_column(j, new.schema.field(j), other_tags),
                new.set_column(k, new.schema.field(k), with_null), new.slice(1)):
        with pytest.raises(AssertionError):
            assert_same_table(old, bad, key, "changed")


def test_bad_lines_are_kept_in_bronze_and_dropped_in_silver_like_the_old_parser(tmp_path):
    raw, lake = tmp_path / "raw", tmp_path / "lake"
    good, canary = ts.pc_ev(1, 1, ts.T0), ts.pc_ev(3, 1, ts.T0 + 2 * ts.S, domain="canary")
    other = ts.pc_ev(4, 1, ts.T0 + 3 * ts.S)
    other["wiki_id"] = "dewiki"
    no_meta = ts.pc_ev(5, 1, ts.T0 + 4 * ts.S)
    del no_meta["meta"]["dt"]
    late = ts.pc_ev(6, 1, ts.T0 + 400 * ts.S)                               # makes one capture gap
    p = ts.part_path(raw, PC, ts.T0)
    with gzip.open(p, "wb") as f:
        for item in (good, "this is not json {", canary, other, no_meta, good, late):
            f.write(((item if isinstance(item, str) else json.dumps(item)) + "\n").encode())
    os.utime(p, (ts.OLD, ts.OLD))
    old = parse_stream.run(raw, tmp_path / "old")
    res = bronze_stream.run(raw, lake=lake)
    s = silver_stream.build(res["dates"], lake=lake)
    df = bronze(lake, PC)
    assert len(df) == 7 and df["meta_id"].isna().sum() == 1                 # Bronze keeps all 7 lines
    assert df["meta_dt"].isna().sum() == 2 and (df["event_date"] == pd.Timestamp("2026-10-20").date()).all()
    got = {c: s["page_change"][c] for c in silver_stream.COUNTERS}
    assert got == {c: old["streams"][PC][c] for c in silver_stream.COUNTERS}
    assert got == {"lines": 7, "bad_json": 1, "canary": 1, "other_wiki": 1, "no_meta": 1, "duplicate_meta_id": 1, "rows": 2}
    assert_same_table(pq.read_table(tmp_path / "old" / "page_change.parquet"), new_table(lake, "page_change"),
                      ("meta_id",), "bad_lines:page_change")
    gaps = delta_io.read_pandas(tables.SILVER["capture_gaps"].path(lake))
    pd.testing.assert_frame_equal(old_gaps({"parsed": tmp_path / "old"}), gaps, check_dtype=False)
    assert len(gaps) == 1 and gaps["gap_s"].iloc[0] == 400.0                # the canary at +2 s does not count
    SEEN["bad_lines"] = got


def test_bronze_chunked_commits_and_a_crash_between_them(world, tmp_path, monkeypatch):
    """A big load is cut into several commits. A crash between two commits loses nothing and repeats nothing."""
    raw, lake = world["raw"], tmp_path / "lake"
    real_append, calls = delta_io.append, {"n": 0}

    def crash_on_third_commit(*args, **kw):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("simulated crash")
        return real_append(*args, **kw)

    monkeypatch.setattr(delta_io, "append", crash_on_third_commit)
    with pytest.raises(RuntimeError, match="simulated crash"):
        bronze_stream.load_stream(PC, raw, lake=lake, chunk_rows=10)
    monkeypatch.setattr(delta_io, "append", real_append)
    path = tables.bronze_spec(PC).path(lake)
    assert delta_io.read_table(path).num_rows == 20 and delta_io.version(path) == 2     # two commits of 10 rows
    st = bronze_stream.load_stream(PC, raw, lake=lake, chunk_rows=10)                   # the next run finishes the job
    assert st["rows"] == 19 and st["commits"] == [3, 4]
    df = bronze(lake, PC)
    cols = ["meta_id", "meta_dt", "event_date", "raw_json", "source_file", "source_line", "capture_session"]
    pd.testing.assert_frame_equal(df[cols], bronze(world["lake"], PC)[cols])            # = the one-commit load of P2
    assert [h["rows"] for h in reversed(delta_io.history(path)[:4])] == ["10", "10", "10", "9"]
    SEEN["bronze_chunks"] = {"rows_after_crash": 20, "rows_loaded_by_next_run": st["rows"], "commits": st["commits"]}


def test_two_loaders_on_one_snapshot_cannot_both_commit(tmp_path):
    """The app transaction on the Bronze append is a guard against concurrent loaders."""
    spec = tables.bronze_spec(PC)
    path = str(tmp_path / "t")
    delta_io.ensure_table(path, spec.schema, spec.properties, spec.partition_by)
    one, two = DeltaTable(path), DeltaTable(path)                           # both read the ledger at version 0
    row = pa.Table.from_pylist([{"raw_json": "{}", "source_file": "f", "source_line": 1,
                                 "event_date": pd.Timestamp("2026-10-20").date()}], schema=spec.schema)
    assert delta_io.append(one, row, {"step": "bronze"}, app_id="bronze_loader:x") == 1
    with pytest.raises(CommitFailedError):
        delta_io.append(two, row, {"step": "bronze"}, app_id="bronze_loader:x")
    assert delta_io.read_table(path).num_rows == 1


def test_cli_all(world, tmp_path):
    lake = tmp_path / "lake"
    env = {**os.environ, "TRUTHLAG_HW2_DIR": str(HW2_DIR), "TRUTHLAG_LAKE_DIR": str(lake), "PYTHONDONTWRITEBYTECODE": "1"}
    cmd = [sys.executable, "-m", "etl.run", "all", "--raw-dir", str(world["raw"]), "--history-dir", str(world["hist"])]
    for _ in range(2):                                                      # the second call must change nothing
        done = subprocess.run(cmd, cwd=PROTO_DIR, env=env, capture_output=True, text=True)
        assert done.returncode == 0, done.stderr[-2000:]
    assert check_parity(world["old"], lake, "cli")["live_revert_links"] == 9
    assert versions(lake) == versions(world["lake"])
```

## Results

All RAN. Numbers are from `SCRATCH/out/test_report.json` and the script outputs in `SCRATCH/step1/*.out`.

**P1 old pipeline.** Row counts: page_change 38, revert_risk 2, tag_events 7, live_revisions 32, live_revert_links 9, live_revert_links_all 17, late_reverts 5. They equal the expected counts. `duplicate_meta_id` = 1.

**P2 new pipeline, same raw folder.**
- Bronze rows: page_change 39 (the repeated line is kept), revert risk 3, tags 7. `raw_json` equals every gzip line. `event_date` is the UTC date of `meta_dt`: the page_change rows land in 2026-10-19 and 2026-10-20 and the tag rows in 2026-10-18 and 2026-10-20, although every file sits in a `dt=2026-10-20` folder.
- Silver equals the old files in values for all 7 tables (38, 2, 7, 32, 9, 17, 5 rows), and `capture_gaps` (4 rows) equals `capture_gaps.csv`. The counters of the old rules agree too (lines 39 / 3 / 7, duplicate_meta_id 1 / 0 / 0, duplicate_rev_id 1).
- All 11 tables: protocol reader 1 / writer 2, no table features, the three KEEP_HISTORY properties set. Bronze: `delta.appendOnly=true`; the file statistics hold only the 7 envelope columns (`kafka_offset, kafka_partition, kafka_topic, meta_dt, meta_id, stream, wiki_id`), so delta-rs honours `delta.dataSkippingStatsColumns`; the Parquet codec is ZSTD; a `delete` on Bronze raises `CommitFailedError`.
- Commit metadata. Bronze: `step=bronze, stream, batch_id, files=2, rows=39, event_dates=2026-10-19,2026-10-20`. Cohort table: `step=cohorts, as_of=2026-10-20T10:20:02.000000Z, newest_meta_dt=2026-10-20T10:01:42.000000Z, rows=9, row_counts={"late_reverts": 5, "live_revert_links": 9, "live_revert_links_all": 17, "live_revisions": 32}`.
- Versions after the first run: Bronze 1 / 1 / 1; silver/page_change 2 and silver/tag_events 2 (one commit per event date); revert_risk 1; capture_gaps 1; the four cohort tables 1.
- `<lake>/_runs/20261020T102002.000000Z/` holds 5 JSON files (the 4 summaries that the old run functions write and the export's `_SUCCESS_parsed.json`) and `run.json`.

**P3 second run.** Bronze: 0 rows, 0 commits, no dates. Silver with the (empty) touched dates and a full pass over every date (39 lines read again, 38 kept, 0 inserted): no commit. `capture_gaps` and the four cohort tables: `wrote=False`, also when the same as_of is passed as text. Versions and row counts are identical before and after, and the list of `_delta_log/*.json` files is identical. So an insert-only MERGE that inserts nothing writes no commit in delta-rs 1.6.6. The CLI `python -m etl.run all` run twice: exit code 0 both times, same versions as the lake of P2.

**P4 growth.** First load: 20 lines, version 1. The same gzip file rewritten with 38 lines and an mtime 600 s newer: the second run added 18 rows in one commit (version 2, `files=1, rows=18`). `source_line` is 1..38 once each; the first 20 rows are unchanged and keep the first batch_id. A third run adds 0 rows. Silver page_change equals the old parser's file for the full raw file.

**P5 two arrivals** (split at meta.dt <= 2026-10-20T10:00:45Z; the second arrival is written as new session files).
- By time: Bronze loaded 40 rows (35 + 3 + 2), then 9 (3 page_change + the repeated event + 5 tags). Later half first: 8, then 41.
- In both orders the final Silver tables equal the old one-batch files and the one-batch lake of P2 (38, 2, 7, 32, 9, 17, 5, and 4 gaps).
- Versions at the end, by time: Bronze 2 / 1 / 2; page_change 3, tag_events 3, revert_risk 1, capture_gaps 2, cohort tables 2. With the later half first, live_revert_links and live_revert_links_all are at version 1 only: the first build gave 0 links, the same as the empty table, so nothing was written.
- Update branch of "earliest wins" (own test): the later score rr-2 (0.5) arrives first: inserted 1. Then rr-1 (0.9, 7 s earlier) and rr-3 arrive: inserted 1, updated 1. The table holds rev 102 with 0.9 and meta_dt T0 + 13 s. A full re-run: 0 / 0 and no commit. Version 1 of the table still reads 0.5.

**P6 as_of and time travel.**
- `build(2026-10-20T10:00:45Z)` wrote version 1 of each of the four tables (29, 6, 14, 5 rows). `build(None)` = as_of 2026-10-20T10:20:02.000000Z wrote version 2 (32, 9, 17, 5 rows).
- The old pipeline, run only on the events with meta_dt <= 10:00:45, gives 29, 6, 14, 5 rows; all four tables equal version 1 in values. Version 2 equals the old full output.
- `find_version(path, {"step": "cohorts", "as_of": ...})` returned 1 and 2 for every table; an as_of that was never built returns None. `run.json` holds the same versions.
- What did we know at 10:00:45? Reverted revisions with a link: `[302, 303, 1502, 1503, 1504, 1601]`. Known only at the later version: `[102, 103, 9001]`. Revision 102: reverted by 104, `known_at` 2026-10-20T10:01:02Z, which is after the first as_of. `newest_meta_dt` in the commit metadata: 10:00:42 (version 1) and 10:01:42 (version 2).
- The same from Spark SQL: `SELECT ... VERSION AS OF 1` gives the same six revisions, and the version is found with `DESCRIBE HISTORY` plus `get_json_object(userMetadata, '$.as_of')`.

**P7 cut-short and open files.** Three page_change files: (a) 40 sync-flushed lines and no gzip end marker; (b) 400 lines cut at 60 % of the bytes; (c) 5 lines, changed just now.
- Old reader: 269 lines (40 + 229), 2 cut-short files, 1 open file skipped. Bronze: 269 rows, the same 2 cut-short files (`lines_kept` 40 and 229), the same skipped file; the rev_ids are clean prefixes.
- `include_open=True`: 5 more rows. After file (a) is completed to 50 lines: 10 more rows (lines 41 to 50 only). Final: 284 rows, no repeated (source_file, source_line).
- Silver page_change equals the old parser's file at each of the three stages.

**Extra checks (RAN).**
- Bad lines: a file with 7 lines (1 not JSON, 1 canary, 1 dewiki, 1 without meta.dt, 1 repeated). Bronze keeps 7 rows; Silver counts `bad_json 1, canary 1, other_wiki 1, no_meta 1, duplicate_meta_id 1, rows 2`, the same as the old parser; one gap of 400.0 s (the canary event does not count).
- Chunked Bronze commits with a simulated crash at the third commit: 20 rows survive; the next run loads the other 19 in commits 3 and 4; the table equals the one-commit load.
- Two loaders that read the same snapshot: the second append raises `CommitFailedError` (application transaction plus the same DeltaTable object).
- **Spark reads the lake that delta-rs wrote** (`proto/checks/spark_reads_lake.py`): row counts equal in all 11 tables; values equal (times, lists, raw_json, dates) for silver/page_change (38 rows, after two delta-rs MERGE commits), silver/tag_events, silver/live_revert_links and bronze/page_change_events (ZSTD); the column names `partition`, `offset` and `class` work in Spark SQL without backticks; `WHERE event_date = DATE'2026-10-19'` gives 1 row; reading changed no version.
- **Speed, indicative** (`proto/checks/bench.py`, other agents were using the machine): 300,000 page_change and 165,000 revert-risk events in 146 part files. Bronze first load 6.4 s (5 commits), Silver first build 7.9 s, Bronze re-run with nothing new 0.6 s, Silver with nothing touched 1.1 s, Silver full pass again 7.0 s, old `parse_stream.run` on the same files 7.0 s. Peak memory of the process 1,359 MB. page_change (300,000 rows) and revert_risk (150,000 rows) equal the old parser's files. The made-up events compress much better than real ones (13 MB gzip), so the sizes mean nothing.

**Read-only check.** `git --no-optional-locks -C /home/user/truth-lag status --porcelain` printed nothing (0 lines) at the end, and so did the plain `git -C /home/user/truth-lag status --porcelain` run after it. No `__pycache__` was written in the scratch copy of ec-hw2 or in proto/.

## Pitfalls met

The package passed every test at its first run. The only change to the package after that is point 3. These are the errors I hit and the findings that shaped the code. RAN unless marked.

1. **pandas and mixed ISO texts (my check script).** `pd.to_datetime(["2026-10-20T10:00:02.123456Z", "2026-10-21T00:00:00Z", None], utc=True)` failed: `ValueError: time data "2026-10-21T00:00:00Z" doesn't match format "%Y-%m-%dT%H:%M:%S.%f%z", at position 1.` Fix: `format="ISO8601"`. meta.dt has milliseconds and rev_dt has whole seconds, so any pandas parse of both in one call needs it.
2. **pytest `--basetemp`.** After I deleted the parent folder, `--basetemp=SCRATCH/pytest_tmp/final` gave `16 errors` with `FileNotFoundError: [Errno 2]`. pytest does not create the parent. Fix: `mkdir -p` the parent first.
3. **Spark cannot see delta-rs custom commit metadata.** delta-rs writes each custom key at the top level of commitInfo (`history()` shows `as_of`, `step`, `rows`, ...). Spark's `DESCRIBE HISTORY` has 15 fixed columns (`version, timestamp, userId, userName, operation, operationParameters, job, notebook, clusterId, readVersion, isolationLevel, isBlindAppend, operationMetrics, userMetadata, engineInfo`). Fix in `delta_io._commit`: the whole metadata dict is also stored as JSON text under the key `userMetadata`. Spark then shows it, and `get_json_object(userMetadata, '$.as_of')` finds the version.
4. **capture_gaps cannot be built from the Silver tables.** `find_gaps` needs meta_dt, topic and partition of every kept event. The old tag_events file has no topic or partition, and revert_risk holds one row per rev_id. So `silver_stream.kept_times` reads the Bronze envelope columns with SQL. The canary rule needs `meta.domain`, which is not a Bronze column: the SQL returns `raw_json` only for lines that contain the text `canary`, and only those are parsed.
5. **The dt= folder is not the event date.** The fixture helper `write_part` puts every event into the folder of the first event (the real capture names the folder from meta.dt, so there the two should agree). `event_date` is computed from meta.dt per line; the folder date is used only for a line without a readable meta.dt. `build_stream` stops with an error if a Silver row's date differs from its Bronze partition.
6. **Delta has no nanosecond time.** The old cohort files store `timestamp[ns, UTC]`. `tables._micro` declares the Delta schemas with microseconds and the load uses a safe Arrow cast, which raises if a value would be cut. It did not raise: all values are whole milliseconds or seconds. The test casts back to nanoseconds to compare.
7. **`replace_if_changed` and as_of.** A build whose rows equal the current version writes nothing, so its as_of is not in that table's history. Seen in P5 (later half first): two builds, but live_revert_links is at version 1. `build()` therefore returns the version that holds the content and writes it to `<lake>/_runs/<as_of>/run.json`.
8. **The default as_of.** The newest meta_dt over the three Silver stream tables was the tags stream's (10:20:02), later than the newest page_change event (10:01:42). `label_live` uses the newest page_change meta_dt for `followup_s` and the provisional flag. Both values are stored in the commit metadata (`as_of`, `newest_meta_dt`).
9. **Old order.** The old parser keeps the first copy of a repeated meta.id in sorted file order. Silver does not hold source_file or source_line, so the dedupe is done while reading Bronze (`_old_order`: path parts, then line number), before the MERGE. The export for the old cohort code is sorted by (meta_dt, meta_id), which is not the old file order; the cohort tables were still equal on the fixture.
10. **Known lab pitfalls, designed around and confirmed here.** (a) Application transactions alone do not stop a repeat: the loader checks the table content; the transaction is only a guard against a second loader (second commit refused, RAN). (b) MERGE does not dedup its source: `dedupe_first` and the old `seen` set run first. (c) No-op MERGE: the earliest-wins source is pre-filtered and an empty source is not sent; the insert-only MERGE with nothing new made no commit (RAN). (d) string_view after MERGE: every read goes through `DeltaTable.scan` or `QueryBuilder` plus `to_plain`; reading silver/revert_risk after its update MERGE and at version 1 worked (RAN). (e) Time travel is by version number, found through commit metadata; timestamp time travel is not used anywhere. (f) No forbidden table feature: all tables are reader 1 / writer 2 (RAN).
11. **`git status`.** A plain `git status` may refresh `.git/index`. I ran the plain command, as the task asks, and also `git --no-optional-locks`; both printed nothing.
12. UNVERIFIED cause, harmless fix: Parquet files written by pyarrow may name the list item field `element` while `pa.list_(pa.string())` names it `item`. The cohort load casts every file to the registry schema before it compares or writes, so I never saw an error from this.

## Not covered

- **Real data.** Nothing ran on real data. Largest run: 300,000 + 165,000 made-up events. UNVERIFIED on the real capture (about 1.2 M page_change, 0.8 M risk, 1.6 M tag events, 751 gzip files, 1 GB).
- **Bronze reads every part file on every run** to count its lines (0.6 s for 146 small files here). On the real capture this is a full gunzip pass per run: UNVERIFIED, likely tens of seconds. A file ledger with size and mtime would let the loader skip unchanged files; the task fixed the Bronze columns, so I did not add one.
- **`kept_times` loads the envelope columns of a whole stream into pandas** on every Silver run (6 small columns). Fine at 300,000 rows; UNVERIFIED at 1.6 M.
- **History side.** `parse_history` and the history tables are not ported. `late_reverts` ran with its window fallback, as in the old fixture. The `history_revisions=` argument and the CLI options `--history-revisions` and `silver --dates` were not run.
- **Spark writes.** Spark only read the lake. Gold tables, Spark MERGE into these tables and both engines writing one table were not tested.
- **Silver watermark.** The Silver step gets the touched dates from the Bronze run in the same process. If Silver fails after Bronze committed, the dates are lost; `python -m etl.run silver` (all dates) repairs it and is idempotent. An automatic "which dates are pending" check is not built.
- **Rare inputs** (the fixture has none; behaviour on real data UNVERIFIED): a repeated meta.id with a different meta.dt on another date would be inserted twice, because the MERGE names one partition; a risk event with a null rev_id is dropped by `merge_earliest` and counted (the old code keeps one such row); a line that is not valid UTF-8 is stored with replacement characters; a JSON line that is not an object is counted as bad JSON (the old code would stop); a meta.dt that Python can read and Arrow cannot (or the other way) is not handled; a part file that got shorter is only reported (`files_shorter_than_loaded`), and a file whose already loaded lines changed is not noticed.
- **Cohort step cost.** `build(as_of)` is a full rebuild with the old code for each as_of, plus an export of the three Silver tables. Its runtime on real data is not known here.
- **Maintenance.** No optimize, checkpoint or vacuum was run. Each commit writes one file per partition, so many small files will collect. KEEP_HISTORY makes old versions stay; disk use over time was not measured.
- **macOS.** Everything ran on Linux only. The `TRUTHLAG_HW2_DIR` fallback (an `ec-hw2` folder next to `etl/`) was not run.
- **Exit-time abort seen in the delta-rs lab** (exit code 134 after `to_pyarrow_table`): the package never calls `to_pyarrow_table`; 10 of 10 CLI calls exited with 0 (2 calls in each of 5 runs of the test file), which is a small sample.
- **Error texts not captured.** The tests assert `CommitFailedError` for the append-only delete and for the second loader; I did not record the message texts in this run.

## Test matrix

| Feature | Status | Evidence |
| --- | --- | --- |
| Step 1 (a): the 30 old ingest tests pass in the one venv | works | RAN from the scratch copy of ec-hw2: `30 passed in 2.34s`; again after all other work: `30 passed in 1.95s`. Python 3.12.3, pandas 2.3.3, pyarrow 26.0.1. |
| Step 1 (b): one interpreter imports pyspark, delta, deltalake, pandas, pyarrow, polars | works | RAN: pyspark 4.2.0, delta-spark 4.4.1, deltalake 1.6.6, pandas 2.3.3, pyarrow 26.0.1, polars 2.1.0, numpy 2.5.4, py4j 0.10.9.9. |
| Step 1 (c): a Spark session with Delta starts from this venv | works | RAN: Spark 4.2.0 started in 5.9 s through configure_spark_with_delta_pip; 33 jars from the copied Ivy cache, 0 downloads; session time zone UTC; no spark-warehouse, metastore_db or derby.log in the working folder. |
| Step 1 (c): Spark reads a table that delta-rs wrote | works | RAN: 3 rows equal, times 23:59:59.999999 and 00:00:00.000001 exact, date partition filter gives 2 rows, list column and nulls correct; DESCRIBE DETAIL reader 1 / writer 2, features [appendOnly, invariants], 5 properties kept. |
| Step 1 (c): delta-rs reads a table that Spark wrote | works | RAN: protocol 1 / 2; 2 rows; known_at is datetime64[us, UTC] = 2026-10-20 10:00:02.123456+00:00; partition_columns ['event_date']. |
| Step 1: version conflicts between the packages | works | RAN: uv resolved 22 packages; `uv pip check` prints `All installed packages are compatible`. createDataFrame(pandas) and toPandas() work with Arrow on and off; a Python UDF ran in a worker with Python 3.12.3 (PYSPARK_PYTHON=sys.executable). |
| Step 1 extra: Spark reads the lake that the delta-rs prototype wrote | works | RAN: row counts equal in all 11 tables; values equal for silver/page_change (38), silver/tag_events (7), silver/live_revert_links (9), bronze/page_change_events (39, ZSTD); columns partition, offset, class need no backticks; DESCRIBE HISTORY shows userMetadata; VERSION AS OF 1 works. |
| P1 old pipeline row counts | works | RAN: page_change 38, revert_risk 2, tag_events 7, live_revisions 32, live_revert_links 9, live_revert_links_all 17, late_reverts 5 (equal to the expected counts); duplicate_meta_id 1. |
| P2 new Silver tables equal the old files | works | RAN: all 7 tables equal in values after sorting by key (38, 2, 7, 32, 9, 17, 5 rows), times equal as integers, list columns equal; capture_gaps 4 rows equal the old CSV; the old parser's counters equal (lines 39 / 3 / 7, duplicate_meta_id 1, duplicate_rev_id 1). |
| P2 Bronze content, table properties and commit metadata | works | RAN: Bronze 39 / 3 / 7 rows, raw_json equals each gzip line, event_date = UTC date of meta_dt; all 11 tables reader 1 / writer 2 with no table features and the KEEP_HISTORY properties; Bronze appendOnly, stats only for the 7 envelope columns, ZSTD, delete refused; commits carry step, batch_id, files, rows (Bronze) and as_of, newest_meta_dt, row counts (cohorts). |
| P3 idempotence: a second run of Bronze, Silver and cohorts | works | RAN: Bronze 0 rows and 0 commits; Silver full pass re-read 39 lines and inserted 0 with no commit; capture_gaps and 4 cohort tables wrote=False; versions, row counts and the list of _delta_log/*.json files unchanged; CLI `all` twice with exit code 0. |
| P4 growth: a raw file that got more lines | works | RAN: 20 lines loaded (version 1); the file rewritten with 38 lines and a newer mtime; second run added 18 rows in one commit (version 2); source_line 1..38 once each; first 20 rows unchanged; third run 0 rows; Silver page_change equals the old parser's file. |
| P5 two arrivals split by meta.dt, in both orders | works | RAN: by time 40 then 9 Bronze rows, later half first 8 then 41; in both orders the final Silver tables equal the old one-batch files and the one-batch lake (38, 2, 7, 32, 9, 17, 5, 4 gaps). |
| P5 extra: earliest wins when the earlier score arrives later | works | RAN: run 1 inserted 1 (score 0.5); run 2 inserted 1 and updated 1; rev 102 holds 0.9 with meta_dt T0 + 13 s; re-run 0 / 0 and no commit; version 1 still reads 0.5. |
| P6 as_of builds and time travel | works | RAN: as_of 10:00:45 wrote version 1 (29, 6, 14, 5 rows), as_of 10:20:02 wrote version 2 (32, 9, 17, 5); version 1 equals the old pipeline run on only the events with meta_dt <= 10:00:45 (all 4 tables); find_version returned 1 and 2 for every table; revert links of revisions 102, 103, 9001 exist only at version 2. |
| P7 cut-short gzip files and an open file | works | RAN: old reader 269 lines (40 + 229 of 400), 2 cut-short files, 1 open file skipped; Bronze 269 rows with the same files reported; include_open adds 5 rows; completing the 40-line file adds 10 rows (lines 41 to 50); final 284 rows, no repeated (source_file, source_line); Silver equals the old file at each stage. |
| Extra: bad lines (not JSON, canary, other wiki, no meta.dt, repeated id) | works | RAN: Bronze keeps 7 of 7 lines; Silver counters equal the old parser (bad_json 1, canary 1, other_wiki 1, no_meta 1, duplicate_meta_id 1, rows 2); one gap of 400.0 s, the canary event not counted. |
| Extra: chunked Bronze commits and a crash between commits | works | RAN: crash at the third of four commits (chunk of 10 rows): 20 rows survive; the next run loads 19 rows in commits 3 and 4; the table equals the one-commit load. |
| Extra: two loaders on one snapshot | works | RAN: the second append with the same app_id from a DeltaTable object at the old version raises CommitFailedError; the table holds 1 row. Message text not recorded. |
| Extra: the table comparison detects small differences | works | RAN: a shift of 1 microsecond, one extra list item, one null and one missing row each raise AssertionError in assert_same_table. |
| Extra: CLI `python -m etl.run all` | works | RAN: two calls in a row, exit code 0 both; tables equal the old files; versions equal the lake built through the Python functions. |
| Extra: speed on 300,000 + 165,000 made-up events | works | RAN, indicative only: Bronze first load 6.4 s, Silver first build 7.9 s, Bronze re-run 0.6 s, Silver full pass again 7.0 s, old parse_stream.run 7.0 s, peak memory 1,359 MB; page_change (300,000) and revert_risk (150,000) equal the old parser's files. |
| Read-only rule on /home/user/truth-lag | works | RAN at the end: `git -C /home/user/truth-lag status --porcelain` printed nothing (0 lines); the same with --no-optional-locks. |
| The pipeline on real capture data | untested | UNVERIFIED: the real data is not on this machine. |
| Spark writing to these tables, Gold tables, history tables | untested | UNVERIFIED: Spark only read the lake; parse_history was not ported; late_reverts ran with its window fallback. |

## Tested snippets

### Step 1 (a): the 30 old ingest tests pass in the one venv

```text
SCRATCH/venv/bin/python -m pytest SCRATCH/ec-hw2/tests/test_stream.py SCRATCH/ec-hw2/tests/test_history.py -q -p no:cacheprovider
```

### Step 1 extra: Spark reads the lake that the delta-rs prototype wrote

```text
spark.sql(f"DESCRIBE HISTORY delta.`{path}`").where("get_json_object(userMetadata, '$.as_of') = '2026-10-20T10:00:45.000000Z'").selectExpr("max(version) AS v")
```

### P4 growth: a raw file that got more lines

```sql
SELECT source_file, max(source_line) AS n FROM t GROUP BY source_file
```

### P5 extra: earliest wins when the earlier score arrives later

```text
.when_matched_update_all(predicate="s.meta_dt < t.meta_dt").when_not_matched_insert_all()
```

### P6 as_of builds and time travel

```text
delta_io.find_version(path, {"step": "cohorts", "as_of": "2026-10-20T10:00:45.000000Z"})  # -> 1
```

## Open questions

- Bronze table names: I used bronze/page_change_events, bronze/revert_risk_events and bronze/tags_events. The task text said bronze/<name>_events without fixing the tags name. It is one dict (BRONZE_NAMES in etl/tables.py). Which names does the plan want?
- Cohort versions: with replace_if_changed a build whose rows equal the current version writes no commit, so that as_of is missing from the table's history and only <lake>/_runs/<as_of>/run.json maps it to a version. Should every build write a version instead, so Spark SQL can always find an as_of in DESCRIBE HISTORY?
- Default as_of: I used the newest meta_dt over the three Silver stream tables (on the fixture this is the tags stream, 18 minutes after the newest page_change event). label_live takes followup_s and the provisional flag from the newest page_change meta_dt. Should the default as_of be the newest page_change meta_dt?
- capture_gaps needs topic and partition of every kept event of every stream. The Silver tables keep the old columns, so tag_events and revert_risk cannot give them, and I compute the gaps from Bronze. Should Silver get an event-grain revert_risk table and topic / partition on tag_events, so Gold can work from Silver only?
- The Bronze loader gunzips every part file on every run to count lines. Is a small file ledger (source_file, size, mtime, lines) allowed, as a table or as extra Bronze columns, so unchanged files can be skipped? Note that mtime alone is not safe, because rsync keeps the VPS mtime.
- Silver watermark: the touched event dates pass from Bronze to Silver in one process. Does the plan want a stored watermark (for example a control table) so a failed Silver step is picked up by the next run without a full pass?
- The export for the old cohort code is sorted by (meta_dt, meta_id), not by the old file order. The cohort tables were equal on the fixture. Is there any tie in the real data where the old file order decides a result (same rev_id with the same meta_dt, or two exact reverts at the same second with the same rev_id)?
- Where should build_facts.py find the _SUCCESS_*.json and summary files? I copy them to <lake>/_runs/<as_of>/; the old code reads data/parsed and data/tables.
- Real data: do the 3 repeated meta.id in page_change carry the same meta.dt as their first copy? If not, the partition-limited MERGE would insert both copies.
