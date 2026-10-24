"""Turn the raw EventStreams capture into three Parquet tables and a list of capture gaps.

Purpose
    Read every raw part file of the 3 captured streams, drop repeated events
    (same meta.id), flatten the fields we need, and save typed Parquet tables.
    It also lists the holes in the capture (more than 120 s without an event).

Inputs
    data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-*.ndjson.gz for every stream in
    config.STREAM_DIRS. One gzip file per capture session and partition.
    A file that is still being written has no gzip end marker. We skip files that
    changed in the last config.OPEN_FILE_GRACE_S seconds (unless --include-open).
    A file that is cut short keeps every complete line read before the error.

Outputs (in data/parsed/, see DATA_MODEL.md section 2)
    page_change.parquet   one row per page_change event, all namespaces, all kinds
    revert_risk.parquet   one row per rev_id (the earliest score)
    tag_events.parquet    one row per tags-change event (with added / removed tags)
    capture_gaps.csv      holes longer than 120 s between two kept events of a stream
    _SUCCESS_parsed.json  row counts, file counts, first and last meta.dt per stream

Run (from the repo root)
    .venv/bin/python ec-hw2/ingest/parse_stream.py
    .venv/bin/python ec-hw2/ingest/parse_stream.py --include-open   # also read files that may still be open
"""
from __future__ import annotations

import argparse
import gzip
import json
import logging
import os
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

log = logging.getLogger("parse_stream")

# The 120 s gap rule is written in DATA_MODEL.md. It is not in config.py yet,
# so we read it from there when it is added (see the shared change request).
GAP_MIN_S = getattr(config, "CAPTURE_GAP_S", 120)
BATCH_ROWS = 200_000          # rows per Arrow batch: keeps memory low
GZIP_ERRORS = (EOFError, zlib.error, gzip.BadGzipFile)

TS = pa.timestamp("us", tz="UTC")
STR_LIST = pa.list_(pa.string())

PAGE_CHANGE_SCHEMA = pa.schema([
    ("meta_id", pa.string()), ("meta_dt", TS), ("topic", pa.string()),
    ("partition", pa.int32()), ("offset", pa.int64()), ("wiki_id", pa.string()),
    ("kind", pa.string()), ("page_id", pa.int64()), ("page_title", pa.string()),
    ("ns", pa.int32()), ("rev_id", pa.int64()), ("parent_id", pa.int64()), ("rev_dt", TS),
    ("rev_size", pa.int64()), ("sha1", pa.string()), ("comment", pa.string()),
    ("prior_rev_id", pa.int64()), ("prior_rev_dt", TS), ("prior_rev_size", pa.int64()),
    ("prior_sha1", pa.string()), ("user_id", pa.int64()), ("user_name", pa.string()),
    ("is_bot", pa.bool_()), ("is_temp", pa.bool_()), ("edit_count", pa.int64()),
    ("revert_method", pa.string()), ("revert_is_exact", pa.bool_()),
    ("revert_original_id", pa.int64()), ("revert_original_dt", TS),
    ("revert_oldest_id", pa.int64()), ("revert_newest_id", pa.int64()),
])
# meta_id, topic and partition are only needed for the dedupe and the gap list.
REVERT_RISK_SCHEMA = pa.schema([
    ("meta_id", pa.string()), ("topic", pa.string()), ("partition", pa.int32()),
    ("rev_id", pa.int64()), ("page_id", pa.int64()), ("meta_dt", TS), ("rev_dt", TS),
    ("prob_true", pa.float64()), ("model_name", pa.string()), ("model_version", pa.string()),
])
REVERT_RISK_COLUMNS = ["rev_id", "page_id", "meta_dt", "rev_dt", "prob_true",
                       "model_name", "model_version"]
TAG_SCHEMA = pa.schema([
    ("meta_id", pa.string()), ("meta_dt", TS), ("topic", pa.string()), ("partition", pa.int32()),
    ("rev_id", pa.int64()), ("page_id", pa.int64()), ("ns", pa.int32()),
    ("rev_timestamp", TS), ("tags", STR_LIST), ("prior_tags", STR_LIST),
    ("added", STR_LIST), ("removed", STR_LIST), ("mw_reverted_added", pa.bool_()),
])
TAG_COLUMNS = ["meta_id", "meta_dt", "rev_id", "page_id", "ns", "rev_timestamp", "tags",
               "prior_tags", "added", "removed", "mw_reverted_added"]


# --------------------------------------------------------------------------
# Reading the raw files
# --------------------------------------------------------------------------
def list_part_files(stream_dir: Path, now: float, include_open: bool):
    """Return (files to read, files skipped because they may still be open)."""
    files, skipped = [], []
    for p in sorted(stream_dir.glob(config.RAW_GLOB)):
        age_s = now - p.stat().st_mtime
        if age_s < config.OPEN_FILE_GRACE_S and not include_open:
            skipped.append(p)
        else:
            files.append(p)
    return files, skipped


def read_lines(path: Path, problems: list):
    """Yield the lines of one gzip part file.

    A file that is cut short (no end marker, or broken data) raises an error at
    the end. We keep every complete line read before the error and note the file
    in `problems`. The last, half-written line is never yielded as a full line.
    """
    n = 0
    try:
        with gzip.open(path, "rb") as f:
            for line in f:
                n += 1
                yield line
    except GZIP_ERRORS as e:
        problems.append({"file": str(path), "error": f"{type(e).__name__}: {e}", "lines_kept": n})
        log.warning("cut-short gzip file, kept %d complete lines: %s (%s)",
                    n, path, type(e).__name__)


# --------------------------------------------------------------------------
# Flattening one event into one row
# --------------------------------------------------------------------------
def _meta(ev: dict) -> dict:
    return ev.get("meta") or {}


def flat_page_change(ev: dict) -> dict:
    meta, page = _meta(ev), ev.get("page") or {}
    rev = ev.get("revision") or {}
    prior = (ev.get("prior_state") or {}).get("revision") or {}
    perf = ev.get("performer") or {}
    rv = rev.get("revert") or {}
    return {
        "meta_id": meta.get("id"), "meta_dt": meta.get("dt"), "topic": meta.get("topic"),
        "partition": meta.get("partition"), "offset": meta.get("offset"),
        "wiki_id": ev.get("wiki_id"), "kind": ev.get("page_change_kind"),
        "page_id": page.get("page_id"), "page_title": page.get("page_title"),
        "ns": page.get("namespace_id"),
        "rev_id": rev.get("rev_id"), "parent_id": rev.get("rev_parent_id"),
        "rev_dt": rev.get("rev_dt"), "rev_size": rev.get("rev_size"),
        "sha1": rev.get("rev_sha1"), "comment": rev.get("comment"),
        "prior_rev_id": prior.get("rev_id"), "prior_rev_dt": prior.get("rev_dt"),
        "prior_rev_size": prior.get("rev_size"), "prior_sha1": prior.get("rev_sha1"),
        "user_id": perf.get("user_id"), "user_name": perf.get("user_text"),
        "is_bot": perf.get("is_bot"), "is_temp": perf.get("is_temp"),
        "edit_count": perf.get("edit_count"),
        "revert_method": rv.get("method"), "revert_is_exact": rv.get("is_exact"),
        "revert_original_id": rv.get("rev_original_id"),
        "revert_original_dt": rv.get("rev_original_dt"),
        "revert_oldest_id": rv.get("rev_reverted_oldest_id"),
        "revert_newest_id": rv.get("rev_reverted_newest_id"),
    }


def flat_revert_risk(ev: dict) -> dict:
    meta, page = _meta(ev), ev.get("page") or {}
    rev = ev.get("revision") or {}
    pred = ev.get("predicted_classification") or {}
    probs = pred.get("probabilities") or {}
    prob = probs.get("true")
    return {
        "meta_id": meta.get("id"), "topic": meta.get("topic"), "partition": meta.get("partition"),
        "rev_id": rev.get("rev_id"), "page_id": page.get("page_id"),
        "meta_dt": meta.get("dt"), "rev_dt": rev.get("rev_dt"),
        "prob_true": float(prob) if prob is not None else None,
        "model_name": pred.get("model_name"),
        "model_version": None if pred.get("model_version") is None else str(pred.get("model_version")),
    }


def flat_tags(ev: dict) -> dict:
    meta = _meta(ev)
    tags = sorted(set(ev.get("tags") or []))
    prior = sorted(set((ev.get("prior_state") or {}).get("tags") or []))
    added = sorted(set(tags) - set(prior))
    removed = sorted(set(prior) - set(tags))
    return {
        "meta_id": meta.get("id"), "meta_dt": meta.get("dt"), "topic": meta.get("topic"),
        "partition": meta.get("partition"), "rev_id": ev.get("rev_id"),
        "page_id": ev.get("page_id"), "ns": ev.get("page_namespace"),
        "rev_timestamp": ev.get("rev_timestamp"), "tags": tags, "prior_tags": prior,
        "added": added, "removed": removed,
        "mw_reverted_added": config.MW_REVERTED_TAG in added,
    }


def _wiki(ev: dict):
    return ev.get("wiki_id") or ev.get("database")


STREAMS = {
    config.STREAM_PAGE_CHANGE: ("page_change", PAGE_CHANGE_SCHEMA, flat_page_change),
    config.STREAM_REVERT_RISK: ("revert_risk", REVERT_RISK_SCHEMA, flat_revert_risk),
    config.STREAM_TAGS: ("tag_events", TAG_SCHEMA, flat_tags),
}


class TableBuilder:
    """Collect rows column by column and turn them into Arrow batches."""

    def __init__(self, schema: pa.Schema, batch_rows: int = BATCH_ROWS):
        self.schema, self.batch_rows = schema, batch_rows
        self.cols = {f.name: [] for f in schema}
        self.batches: list[pa.Table] = []
        self.rows = 0

    def add(self, row: dict) -> None:
        for name, values in self.cols.items():
            values.append(row[name])
        self.rows += 1
        if self.rows % self.batch_rows == 0:
            self.flush()

    def flush(self) -> None:
        if not self.cols[self.schema[0].name]:
            return
        arrays = []
        for f in self.schema:
            values = self.cols[f.name]
            if pa.types.is_timestamp(f.type):
                # Arrow reads ISO 8601 text like "2026-10-20T00:00:00.973Z" directly.
                arrays.append(pc.cast(pa.array(values, pa.string()), f.type))
            else:
                arrays.append(pa.array(values, f.type))
        self.batches.append(pa.Table.from_arrays(arrays, schema=self.schema))
        self.cols = {f.name: [] for f in self.schema}

    def table(self) -> pa.Table:
        self.flush()
        if not self.batches:
            return self.schema.empty_table()
        return pa.concat_tables(self.batches)


def parse_stream_dir(stream: str, stream_dir: Path, now: float, include_open: bool) -> tuple[pa.Table, dict]:
    """Read all part files of one stream, file by file. Return (table, stats)."""
    _, schema, flatten = STREAMS[stream]
    files, skipped = list_part_files(stream_dir, now, include_open)
    stats = {"files_read": len(files), "files_skipped_open": [str(p) for p in skipped],
             "cut_short_files": [], "lines": 0, "bad_json": 0, "canary": 0, "other_wiki": 0,
             "no_meta": 0, "duplicate_meta_id": 0, "rows": 0}
    builder = TableBuilder(schema)
    seen: set[str] = set()
    for path in files:
        for line in read_lines(path, stats["cut_short_files"]):
            stats["lines"] += 1
            try:
                ev = json.loads(line)
            except ValueError:
                stats["bad_json"] += 1
                continue
            meta = _meta(ev)
            if meta.get("domain") == "canary":
                stats["canary"] += 1
                continue
            if _wiki(ev) != "enwiki":
                stats["other_wiki"] += 1
                continue
            mid = meta.get("id")
            if not mid or not meta.get("dt"):
                stats["no_meta"] += 1
                continue
            if mid in seen:            # the capture can repeat events after a reconnect
                stats["duplicate_meta_id"] += 1
                continue
            seen.add(mid)
            builder.add(flatten(ev))
    table = builder.table()
    stats["rows"] = table.num_rows
    return table, stats


# --------------------------------------------------------------------------
# Gaps, revert-risk dedupe and summaries
# --------------------------------------------------------------------------
def find_gaps(stream: str, df: pd.DataFrame, min_gap_s: float = GAP_MIN_S) -> pd.DataFrame:
    """Holes longer than min_gap_s between consecutive kept events of one stream.

    Kafka offsets are shared with other wikis in the same partition, so an offset
    jump is normal. We only use time. topic/partition are those of the first
    event after the hole, as context.
    """
    cols = ["stream", "topic", "partition", "gap_start", "gap_end", "gap_s"]
    if len(df) < 2:
        return pd.DataFrame(columns=cols)
    d = df[["meta_dt", "topic", "partition"]].sort_values("meta_dt", kind="stable").reset_index(drop=True)
    gap_s = d["meta_dt"].diff().dt.total_seconds()
    idx = gap_s.index[gap_s > min_gap_s]
    out = pd.DataFrame({
        "stream": stream,
        "topic": d.loc[idx, "topic"].to_numpy(),
        "partition": d.loc[idx, "partition"].to_numpy(),
        "gap_start": d["meta_dt"].shift(1).loc[idx].to_numpy(),
        "gap_end": d.loc[idx, "meta_dt"].to_numpy(),
        "gap_s": gap_s.loc[idx].round(3).to_numpy(),
    })
    return out[cols]


def dedupe_revert_risk(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Keep the earliest score (by meta_dt) for each rev_id."""
    d = df.sort_values(["rev_id", "meta_dt"], kind="stable")
    dup = d.duplicated("rev_id", keep="first")
    return d.loc[~dup, REVERT_RISK_COLUMNS].reset_index(drop=True), int(dup.sum())


def iso(ts) -> str | None:
    if ts is None or pd.isna(ts):
        return None
    return pd.Timestamp(ts).tz_convert("UTC").isoformat().replace("+00:00", "Z")


def rows_per_day(s: pd.Series) -> dict:
    if s.empty:
        return {}
    return {str(k): int(v) for k, v in s.dt.strftime("%Y-%m-%d").value_counts().sort_index().items()}


def write_parquet(table: pa.Table, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    pq.write_table(table, tmp, compression="zstd")
    os.replace(tmp, path)


def write_json(obj: dict, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str) + "\n")
    os.replace(tmp, path)


def run(raw_dir: Path, out_dir: Path, include_open: bool = False, now: float | None = None) -> dict:
    """Parse every stream in config.STREAM_DIRS and write the outputs. Returns the summary."""
    now = time.time() if now is None else now
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"step": "parsed", "data_version": config.DATA_VERSION,
               "created_at": iso(pd.Timestamp(datetime.now(timezone.utc))),
               "include_open": include_open, "open_file_grace_s": config.OPEN_FILE_GRACE_S,
               "gap_min_s": GAP_MIN_S, "streams": {}, "row_counts": {}}
    gaps = []
    for stream in config.STREAM_DIRS:
        name = STREAMS[stream][0]
        t0 = time.time()
        table, stats = parse_stream_dir(stream, raw_dir / stream, now, include_open)
        df_time = table.select(["meta_dt", "topic", "partition"]).to_pandas()
        if name == "revert_risk":
            df, n_dup = dedupe_revert_risk(table.to_pandas())
            stats["duplicate_rev_id"] = n_dup
            out_table = pa.Table.from_pandas(df, schema=pa.schema(
                [REVERT_RISK_SCHEMA.field(c) for c in REVERT_RISK_COLUMNS]), preserve_index=False)
        elif name == "tag_events":
            out_table = table.select(TAG_COLUMNS)
        else:
            out_table = table
        del table
        write_parquet(out_table, out_dir / f"{name}.parquet")
        gaps.append(find_gaps(stream, df_time))
        stats.update({
            "table": f"{name}.parquet", "rows_written": out_table.num_rows,
            "first_meta_dt": iso(df_time["meta_dt"].min()) if len(df_time) else None,
            "last_meta_dt": iso(df_time["meta_dt"].max()) if len(df_time) else None,
            "rows_per_day": rows_per_day(df_time["meta_dt"]),
            "gaps": int(len(gaps[-1])), "seconds": round(time.time() - t0, 1),
            "cut_short_file_count": len(stats["cut_short_files"]),
            "files_skipped_open_count": len(stats["files_skipped_open"]),
        })
        if name == "tag_events":
            stats["mw_reverted_additions"] = int(pc.sum(out_table.column("mw_reverted_added")).as_py() or 0)
        if name == "page_change":
            kinds = out_table.column("kind").value_counts().to_pylist()
            stats["kinds"] = {k["values"]: int(k["counts"]) for k in kinds}
            stats["revert_events"] = int(out_table.num_rows - out_table.column("revert_method").null_count)
        summary["streams"][stream] = stats
        summary["row_counts"][f"{name}.parquet"] = out_table.num_rows
        log.info("%s: %d rows (%d lines, %d duplicate meta.id, %d canary, %d bad json) "
                 "first meta.dt %s, last meta.dt %s, %d cut-short files, %d skipped open files",
                 stream, out_table.num_rows, stats["lines"], stats["duplicate_meta_id"],
                 stats["canary"], stats["bad_json"], stats["first_meta_dt"], stats["last_meta_dt"],
                 stats["cut_short_file_count"], stats["files_skipped_open_count"])
        for day, n in stats["rows_per_day"].items():
            log.info("    %s  %s rows (by meta.dt, UTC)", day, f"{n:,}")
        del out_table, df_time

    found = [g for g in gaps if len(g)]
    gap_df = pd.concat(found, ignore_index=True) if found else gaps[0].iloc[0:0]
    for c in ("gap_start", "gap_end"):
        gap_df[c] = gap_df[c].map(iso)
    tmp = out_dir / "capture_gaps.csv.tmp"
    gap_df.to_csv(tmp, index=False)
    os.replace(tmp, out_dir / "capture_gaps.csv")
    summary["row_counts"]["capture_gaps.csv"] = int(len(gap_df))
    log.info("capture gaps longer than %s s: %d", GAP_MIN_S, len(gap_df))
    for r in gap_df.itertuples():
        log.info("    gap %s  %s -> %s  (%.0f s)", r.stream, r.gap_start, r.gap_end, r.gap_s)
    write_json(summary, out_dir / "_SUCCESS_parsed.json")
    return summary


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--include-open", action="store_true",
                    help="also read part files changed in the last OPEN_FILE_GRACE_S seconds")
    ap.add_argument("--raw-dir", type=Path, default=config.RAW_STREAM_DIR, help=argparse.SUPPRESS)
    ap.add_argument("--out-dir", type=Path, default=config.PARSED_DIR, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        stream=sys.stdout)
    t0 = time.time()
    s = run(args.raw_dir, args.out_dir, include_open=args.include_open)
    log.info("done in %.0f s. Row counts: %s", time.time() - t0, s["row_counts"])


if __name__ == "__main__":
    main()
