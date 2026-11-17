"""History (dump) side of the lake: Bronze landing, typed Silver slim table, and the history cohort.

Purpose
    1. bronze_history(): land the two filtered 2026-09 History files from data/history/ unchanged
       (all text columns) in bronze/history_slim and bronze/history_full. Each row gets snapshot,
       dump_month, source_file (path below data/), source_row (1-based) and loaded_at. The loader
       reads the highest source_row per source_file from the table and appends only later rows,
       so a load that stopped half way is finished by the next run, and a re-run adds nothing.
    2. build_silver_slim(): silver/history_slim = the Bronze slim rows of one snapshot, typed with
       the old history_columns.cast_history_frame. Replaced only when the rows changed.
    3. build_history_cohort(): the history cohort with the old code, unchanged:
       parse_history.run(cohort_file, slim_file, tmp_dir) on the files in data/history/, then
       silver/history_revisions and silver/history_revert_links (replaced only when changed).
       The history_revisions.parquet that the old code wrote is kept in <lake>/_runs/history/
       for the late_reverts step of the stream cohort build.

Run
    python -m etl.history bronze | silver | cohort | all  [--snapshot 2026-10]
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from deltalake import DeltaTable

from . import delta_io, lake_config
from .hw2 import config, history_columns, parse_history

log = logging.getLogger("history")

SNAPSHOT = "2026-09"
DUMP_MONTH = "2026-09"
BATCH_ROWS = 500_000
DATA_DIR = lake_config.REPO_DIR / "data"
TS = pa.timestamp("us", tz="UTC")

BRONZE_FILES = {   # table -> source file in data/history/
    "bronze/history_slim": config.HISTORY_DIR / config.HISTORY_SLIM_FILE,
    "bronze/history_full": config.HISTORY_DIR / config.HISTORY_COHORT_FILE,
}
EXTRA = [("snapshot", pa.string()), ("dump_month", pa.string()), ("source_file", pa.string()),
         ("source_row", pa.int64()), ("loaded_at", TS)]


def _path(name: str, lake=None) -> str:
    return str(lake_config.lake_root(lake) / name)


def _micro(schema: pa.Schema) -> pa.Schema:
    return pa.schema([pa.field(f.name, pa.timestamp("us", tz=f.type.tz) if pa.types.is_timestamp(f.type) else f.type)
                      for f in schema])


# ---------------------------------------------------------------- Bronze
def snapshot_files(snapshot: str) -> list[tuple[str, Path, str]]:
    """(table, source file, dump_month) for one snapshot. 2026-09: the VPS-filtered files in data/history/.
    Later snapshots: the slim files that etl/history_slim.py wrote to data/history_slim/<snapshot>/."""
    if snapshot == SNAPSHOT:
        return [(name, src, DUMP_MONTH) for name, src in BRONZE_FILES.items()]
    files = sorted((lake_config.HISTORY_SLIM_DIR / snapshot).glob("*_rev_all_*_slim.parquet"))
    if not files:
        raise SystemExit(f"no slim files in {lake_config.HISTORY_SLIM_DIR / snapshot}; run python -m etl.history_slim first")
    return [("bronze/history_slim", f, f.name.split("_rev_all_")[1].split("_slim")[0]) for f in files]


def bronze_history(lake=None, snapshot: str = SNAPSHOT) -> dict:
    out = {}
    for name, src, dump_month in snapshot_files(snapshot):
        t0 = time.time()
        pf = pq.ParquetFile(src)
        src_schema = pf.schema_arrow
        schema = pa.schema([pa.field(f.name, pa.string()) for f in src_schema] + [pa.field(n, t) for n, t in EXTRA])
        path = _path(name, lake)
        delta_io.ensure_table(path, schema, {**lake_config.KEEP_HISTORY, "delta.appendOnly": "true"}, ("snapshot",))
        table = DeltaTable(path)
        rel = src.resolve().relative_to(DATA_DIR).as_posix()
        got = delta_io.sql(table, f"SELECT max(source_row) AS n FROM t WHERE source_file = '{rel}'")
        done = got.column("n")[0].as_py() or 0
        loaded_at = datetime.now(timezone.utc)
        row0, rows, commits = 0, 0, []
        for batch in pf.iter_batches(batch_size=BATCH_ROWS):
            n = batch.num_rows
            first = row0 + 1
            row0 += n
            if row0 <= done:
                continue
            tbl = pa.Table.from_batches([batch])
            skip = max(0, done - (first - 1))
            if skip:
                tbl = tbl.slice(skip)
                first += skip
            m = tbl.num_rows
            tbl = tbl.cast(pa.schema([pa.field(f.name, pa.string()) for f in src_schema]))
            tbl = (tbl.append_column("snapshot", pa.array([snapshot] * m))
                      .append_column("dump_month", pa.array([dump_month] * m))
                      .append_column("source_file", pa.array([rel] * m))
                      .append_column("source_row", pa.array(range(first, first + m), pa.int64()))
                      .append_column("loaded_at", pa.array([loaded_at] * m, TS)))
            v = delta_io.append(table, tbl.cast(schema), {"step": "bronze_history", "table": name, "snapshot": snapshot,
                                                         "source_file": rel, "first_row": first, "rows": m})
            commits.append(v)
            rows += m
        total = delta_io.sql(DeltaTable(path), f"SELECT count(*) AS n, max(source_row) AS m FROM t WHERE source_file = '{rel}'")
        out[f"{name} <- {rel}"] = {"source_file": rel, "dump_month": dump_month, "file_rows": pf.metadata.num_rows, "new_rows": rows, "commits": commits,
                     "table_rows_for_file": total.column("n")[0].as_py(), "max_source_row": total.column("m")[0].as_py(),
                     "version": delta_io.version(path), "seconds": round(time.time() - t0, 1)}
        log.info("%s <- %s: %s", name, rel, out[f"{name} <- {rel}"])
    return out


# ---------------------------------------------------------------- Silver slim (typed)
def build_silver_slim(lake=None, snapshot: str = SNAPSHOT) -> dict:
    """Typed copy of the Bronze slim rows of one snapshot (cast_history_frame), partition snapshot."""
    t0 = time.time()
    bronze = _path("bronze/history_slim", lake)
    path = _path("silver/history_slim", lake)
    bver = delta_io.version(bronze)
    ds = DeltaTable(bronze, version=bver).to_pyarrow_dataset()
    cols = [c for c in config.HISTORY_SLIM_COLUMNS]
    parts, schema = [], None
    for batch in ds.to_batches(columns=cols + ["dump_month"], filter=pc.field("snapshot") == snapshot,
                               batch_size=BATCH_ROWS):
        df = delta_io.to_plain(pa.Table.from_batches([batch])).to_pandas()
        dump_month = df.pop("dump_month")
        df = history_columns.cast_history_frame(df[cols])
        df.insert(0, "snapshot", snapshot)
        df.insert(1, "dump_month", dump_month.to_numpy())
        t = pa.Table.from_pandas(df, preserve_index=False)
        schema = schema or _micro(t.schema)
        parts.append(t.cast(schema))
    new = pa.concat_tables(parts)
    if not delta_io.exists(path):
        delta_io.ensure_table(path, new.schema, lake_config.SILVER_PROPS, ("snapshot",))
    cur_n = delta_io.sql(path, f"SELECT count(*) AS n FROM t WHERE snapshot = '{snapshot}'").column("n")[0].as_py()
    meta = {"step": "silver_history_slim", "snapshot": snapshot, "bronze_version": bver, "rows": new.num_rows}
    if cur_n == new.num_rows:
        log.info("silver/history_slim %s already holds %d rows: no write", snapshot, cur_n)
        return {"wrote": False, "rows": new.num_rows, "version": delta_io.version(path)}
    from deltalake import write_deltalake
    from deltalake import CommitProperties
    write_deltalake(path, new, mode="overwrite", predicate=f"snapshot = '{snapshot}'",
                    commit_properties=delta_io._commit(meta))
    res = {"wrote": True, "rows": new.num_rows, "version": delta_io.version(path), "seconds": round(time.time() - t0, 1)}
    log.info("silver/history_slim: %s", res)
    return res


# ---------------------------------------------------------------- History cohort (old code)
def kept_revisions_file(lake=None) -> Path:
    return lake_config.lake_root(lake) / "_runs" / "history" / parse_history.OUT_REVISIONS


def build_history_cohort(lake=None, history_dir: Path = config.HISTORY_DIR, snapshot: str = SNAPSHOT) -> dict:
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="truthlag_history_"))
    try:
        summary = parse_history.run(history_dir / config.HISTORY_COHORT_FILE, history_dir / config.HISTORY_SLIM_FILE,
                                    tmp, quiet=True)
        keep = kept_revisions_file(lake)
        keep.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp / parse_history.OUT_REVISIONS, keep)
        shutil.copyfile(tmp / parse_history.OUT_SUMMARY, keep.parent / parse_history.OUT_SUMMARY)
        out = {"seconds_old_code": summary.get("seconds")}
        for name, fname, key in (("silver/history_revisions", parse_history.OUT_REVISIONS, ("rev_id",)),
                                 ("silver/history_revert_links", parse_history.OUT_LINKS, ("reverted_rev_id",))):
            t = pq.read_table(tmp / fname)
            t = t.cast(_micro(t.schema))
            path = _path(name, lake)
            delta_io.ensure_table(path, t.schema, lake_config.SILVER_PROPS)
            meta = {"step": "history", "table": name, "snapshot": snapshot, "rows": t.num_rows,
                    "data_version": config.DATA_VERSION}
            out[name] = delta_io.replace_if_changed(path, t, key, meta) | {"rows": t.num_rows}
        out["seconds"] = round(time.time() - t0, 1)
        log.info("history cohort: %s", out)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m etl.history")
    ap.add_argument("step", choices=["bronze", "silver", "cohort", "all"])
    ap.add_argument("--lake", default=None)
    ap.add_argument("--snapshot", default=SNAPSHOT, help="2026-09 (data/history) or a later one (data/history_slim/<snapshot>)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", stream=sys.stdout)
    res = {}
    if args.step in ("bronze", "all"):
        res["bronze"] = bronze_history(args.lake, args.snapshot)
    if args.step in ("silver", "all"):
        res["silver_slim"] = build_silver_slim(args.lake, args.snapshot)
    if args.step in ("cohort", "all") and args.snapshot == SNAPSHOT:      # the history cohort is built from 2026-09 only
        res["cohort"] = build_history_cohort(args.lake)
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
