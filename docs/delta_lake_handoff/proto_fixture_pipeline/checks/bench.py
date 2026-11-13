"""Indicative speed of the Bronze and Silver stream steps on made-up events (fixed content, no randomness).

Run: TRUTHLAG_HW2_DIR=<ec-hw2> <venv>/bin/python step1/bench.py <proto dir> <work dir> [events]
"""
import copy
import gzip
import json
import os
import resource
import shutil
import sys
import time
from pathlib import Path

PROTO, WORK = sys.argv[1], Path(sys.argv[2]).resolve()
N = int(sys.argv[3]) if len(sys.argv) > 3 else 300_000
sys.path.insert(0, PROTO)
import pandas as pd
from etl import bronze_stream, delta_io, silver_stream, tables
from etl.hw2 import config, parse_stream
from tests import test_stream as ts

shutil.rmtree(WORK, ignore_errors=True)
raw, lake = WORK / "raw", WORK / "lake"
t0 = time.time()
base_pc = ts.pc_ev(1, 1, ts.T0, 0, (0, ts.T0, 100, "abc0"))
base_pc["revision"]["comment"] = "edit summary " + "x" * 300          # real events are longer than the fixtures
base_rr = ts.risk_ev("rr", 1, 1, ts.T0, ts.T0, 0.5)
START = pd.Timestamp("2026-10-20T00:00:00Z")
STEP_MS = int(3 * 86400 * 1000 / N)                                    # N events spread over 3 days
files = {}
def out(stream, dt_text):
    key = (stream, dt_text[:10], dt_text[11:13])
    if key not in files:
        d = raw / stream / f"dt={key[1]}" / f"hour={key[2]}"
        d.mkdir(parents=True, exist_ok=True)
        files[key] = gzip.open(d / "part-20261024T000000-aaaaaa-0.ndjson.gz", "wb", compresslevel=1)
    return files[key]
n_risk = 0
for i in range(N):
    ms = i * STEP_MS
    rev_dt = (START + pd.Timedelta(ms // 1000, unit="s")).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta_dt = (START + pd.Timedelta(ms + 2000, unit="ms")).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    ev = base_pc
    ev["revision"]["rev_id"], ev["revision"]["rev_dt"], ev["revision"]["rev_parent_id"] = 1_000_000 + i, rev_dt, 999_999 + i
    ev["page"]["page_id"] = i % 20_000
    ev["meta"]["id"], ev["meta"]["dt"], ev["meta"]["offset"] = f"pc-{i}", meta_dt, i
    out(config.STREAM_PAGE_CHANGE, meta_dt).write((json.dumps(ev) + "\n").encode())
    if i % 2 == 0:                                                      # a score for every second revision
        rr = base_rr
        rr["revision"]["rev_id"], rr["revision"]["rev_dt"] = 1_000_000 + i, rev_dt
        rr["meta"]["id"], rr["meta"]["dt"] = f"rr-{i}", meta_dt
        out(config.STREAM_REVERT_RISK, meta_dt).write((json.dumps(rr) + "\n").encode())
        n_risk += 1
        if i % 20 == 0:                                                 # and a later second score for 5 % of all
            rr["meta"]["id"] = f"rr-{i}-b"
            out(config.STREAM_REVERT_RISK, meta_dt).write((json.dumps(rr) + "\n").encode())
            n_risk += 1
for f in files.values():
    f.close()
old = time.time() - 3600
for p in raw.rglob("*.gz"):
    os.utime(p, (old, old))
gz_mb = sum(p.stat().st_size for p in raw.rglob("*.gz")) / 1e6
print(f"made {N:,} page_change and {n_risk:,} risk events in {len(files)} files, {gz_mb:.0f} MB gzip, {time.time() - t0:.0f} s")

def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

def timed(label, fn):
    t = time.time()
    res = fn()
    print(f"{label}: {time.time() - t:.1f} s, peak RSS so far {rss_mb():.0f} MB")
    return res

b = timed("bronze, first load", lambda: bronze_stream.run(raw, lake=lake))
print("   rows:", {parse_stream.STREAMS[s][0]: (st["rows"], len(st["commits"])) for s, st in b["streams"].items()})
s = timed("silver stream, first build", lambda: silver_stream.build(b["dates"], lake=lake))
print("   ", {k: (v.get("rows"), v.get("inserted"), v.get("updated"), v.get("commits"), v.get("wrote")) for k, v in s.items()})
b2 = timed("bronze, second run (nothing new)", lambda: bronze_stream.run(raw, lake=lake))
assert all(st["rows"] == 0 for st in b2["streams"].values())
s2 = timed("silver stream, nothing touched", lambda: silver_stream.build(b2["dates"], lake=lake))
s3 = timed("silver stream, full pass again (all dates)", lambda: silver_stream.build(None, lake=lake))
assert all(s3[n]["inserted"] == 0 and s3[n]["commits"] == [] for n in ("page_change", "revert_risk"))
t = time.time()
old_out = WORK / "old"
st = parse_stream.run(raw, old_out)
print(f"old parse_stream.run on the same files: {time.time() - t:.1f} s, peak RSS so far {rss_mb():.0f} MB; rows {st['row_counts']}")
for name in ("page_change", "revert_risk"):
    n_new = delta_io.read_table(tables.SILVER[name].path(lake), columns=[tables.SILVER[name].key[0]]).num_rows
    assert n_new == st["row_counts"][f"{name}.parquet"], (name, n_new)
import pyarrow.parquet as pq
new = delta_io.read_table(tables.SILVER["revert_risk"].path(lake)).sort_by("rev_id")
oldt = pq.read_table(old_out / "revert_risk.parquet").sort_by("rev_id")
assert new.cast(oldt.schema.remove_metadata()).equals(oldt.replace_schema_metadata(None))
new = delta_io.read_table(tables.SILVER["page_change"].path(lake)).drop_columns(["event_date"]).sort_by("meta_id")
oldt = pq.read_table(old_out / "page_change.parquet").sort_by("meta_id")
assert new.cast(oldt.schema.remove_metadata()).equals(oldt.replace_schema_metadata(None))
print("page_change and revert_risk equal the old parser's files at this size")
def du(p):
    return sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file()) / 1e6
print("lake MB:", {name: round(du(spec.path(lake)), 1) for name, spec in tables.ALL.items() if delta_io.exists(spec.path(lake))})
print("BENCH OK")
