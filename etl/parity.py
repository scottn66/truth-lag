"""Parity checks: the lake against the published EC HW2 state (data/parity_ref/, a copy of data/parsed and data/tables).

bronze_parity()   rebuilds the exact line cut of the published parse from _SUCCESS_parsed.json and counts Bronze
                  lines in it per stream (must equal `lines`). Also the Bronze rows per stream and event date.
compare_parquet() compares a lake table (or an Arrow table) with an old Parquet file after sorting by key.

Run
    python -m etl.parity bronze
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import delta_io, lake_config, tables
from .hw2 import config

PARITY_DIR = lake_config.REPO_DIR / "data" / "parity_ref"
PARSED_SUCCESS = PARITY_DIR / "parsed" / "_SUCCESS_parsed.json"
PARITY_AS_OF = "2026-10-27T20:59:59.999999Z"
SESSION_RE = re.compile(r"part-(\d{8}T\d{6})-")
HOUR_RE = re.compile(r"dt=(\d{4}-\d{2}-\d{2})/hour=(\d{2})/")


def _rel(path: str) -> str:
    """Absolute path in _SUCCESS_parsed.json -> path below data/raw/ (as Bronze stores it)."""
    return path.split("/data/raw/", 1)[1]


def parse_cut(stream: str) -> dict:
    s = json.loads(PARSED_SUCCESS.read_text())
    info = s["streams"][stream]
    created = datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
    return {"created_at": created, "lines": info["lines"], "files_read": info["files_read"],
            "skipped": {_rel(p) for p in info["files_skipped_open"]},
            "cut_short": {_rel(c["file"]): c["lines_kept"] for c in info["cut_short_files"]},
            "rows_per_day": info["rows_per_day"]}


def bronze_parity(lake=None) -> dict:
    out = {}
    for stream in config.STREAM_DIRS:
        cut = parse_cut(stream)
        path = tables.bronze_spec(stream).path(lake)
        per_file = delta_io.sql(path, "SELECT source_file, count(*) AS n, max(source_line) AS m FROM t GROUP BY source_file")
        files = dict(zip(per_file.column("source_file").to_pylist(), zip(per_file.column("n").to_pylist(),
                                                                          per_file.column("m").to_pylist())))
        chosen, lines, late_session, grown = [], 0, [], 0
        for rel, (n, m) in files.items():
            hm = HOUR_RE.search(rel)
            if not hm or (hm.group(1), hm.group(2)) > ("2026-10-27", "20"):
                continue
            sm = SESSION_RE.search(rel)
            started = datetime.strptime(sm.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc) if sm else None
            if started is not None and started >= cut["created_at"]:
                late_session.append(rel)
                continue
            if rel in cut["skipped"]:
                continue
            k = cut["cut_short"].get(rel)
            if k is not None:
                if m > k:
                    grown += 1
                n = min(n, k)
            chosen.append(rel)
            lines += n
        out[stream] = {"files_in_cut": len(chosen), "files_read_published": cut["files_read"],
                       "bronze_lines_in_cut": lines, "lines_published": cut["lines"],
                       "match": len(chosen) == cut["files_read"] and lines == cut["lines"],
                       "cut_short_files_that_grew_since": grown, "files_from_later_sessions": len(late_session)}
        by_day = delta_io.sql(path, "SELECT CAST(event_date AS VARCHAR) AS d, count(*) AS n FROM t GROUP BY event_date ORDER BY event_date")
        out[stream]["bronze_rows_per_day"] = dict(zip(by_day.column("d").to_pylist(), by_day.column("n").to_pylist()))
        out[stream]["bronze_rows"] = int(sum(by_day.column("n").to_pylist()))
    return out


def silver_parity(lake=None, as_of: str = PARITY_AS_OF) -> dict:
    """Silver stream tables cut at meta_dt <= as_of against data/parity_ref/parsed/*.parquet."""
    limit = pa.scalar(datetime.fromisoformat(as_of.replace("Z", "+00:00")), type=tables.TS)
    out = {}
    for name, key in (("page_change", ["meta_id"]), ("tag_events", ["meta_id"]), ("revert_risk", ["rev_id"])):
        spec = tables.SILVER[name]
        t = delta_io.read_table(spec.path(lake))
        t = t.filter(pc.less_equal(t.column("meta_dt"), limit))
        ref = pq.read_table(PARITY_DIR / "parsed" / f"{name}.parquet")
        out[name] = compare(t.select(ref.schema.names), ref, key)
        if "event_date" in spec.schema.names:
            days = pc.value_counts(pc.cast(pc.cast(t.column("meta_dt"), pa.date32()), pa.string())).to_pylist()
            out[name]["rows_per_day"] = {d["values"]: d["counts"] for d in sorted(days, key=lambda x: x["values"])}
    return out


def compare(a: pa.Table, ref: pa.Table, key: list[str], show: int = 5) -> dict:
    """Same keys and same values (times to the microsecond)? a is cast to ref's types."""
    a = delta_io.to_plain(a)
    ref = delta_io.to_plain(ref)
    a = a.cast(pa.schema([pa.field(f.name, _us(f.type)) for f in ref.schema]))
    ref = ref.cast(pa.schema([pa.field(f.name, _us(f.type)) for f in ref.schema]))
    res = {"rows_lake": a.num_rows, "rows_ref": ref.num_rows}
    ka = set(_keys(a, key))
    kr = set(_keys(ref, key))
    res["only_in_lake"] = len(ka - kr)
    res["only_in_ref"] = len(kr - ka)
    res["only_in_lake_examples"] = sorted(ka - kr)[:show]
    res["only_in_ref_examples"] = sorted(kr - ka)[:show]
    res["same_content"] = bool(delta_io.same_content(a, ref, key)) if not res["only_in_lake"] and not res["only_in_ref"] else False
    if not res["same_content"] and not res["only_in_lake"] and not res["only_in_ref"]:
        res["differing_columns"] = differing_columns(a, ref, key)
    return res


def _us(t: pa.DataType) -> pa.DataType:
    return pa.timestamp("us", tz=t.tz) if pa.types.is_timestamp(t) else t


def _keys(t: pa.Table, key: list[str]):
    cols = [t.column(k).to_pylist() for k in key]
    return list(zip(*cols)) if len(key) > 1 else cols[0]


def differing_columns(a: pa.Table, ref: pa.Table, key: list[str]) -> dict:
    sa = a.sort_by([(k, "ascending") for k in key])
    sr = ref.sort_by([(k, "ascending") for k in key])
    out = {}
    for c in ref.schema.names:
        x, y = sa.column(c).to_pylist(), sr.column(c).to_pylist()
        bad = [i for i, (u, v) in enumerate(zip(x, y)) if not (u == v or (u != u and v != v))]
        if bad:
            out[c] = {"rows": len(bad), "example": {"key": [sa.column(k)[bad[0]].as_py() for k in key],
                                                    "lake": x[bad[0]], "ref": y[bad[0]]}}
    return out


def main(argv=None) -> None:
    step = (argv or sys.argv[1:] or ["bronze"])[0]
    res = bronze_parity() if step == "bronze" else silver_parity()
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
