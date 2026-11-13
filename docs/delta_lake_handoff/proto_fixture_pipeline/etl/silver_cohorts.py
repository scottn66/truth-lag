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
