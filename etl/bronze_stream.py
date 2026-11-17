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
