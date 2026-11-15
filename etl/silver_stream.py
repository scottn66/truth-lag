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
