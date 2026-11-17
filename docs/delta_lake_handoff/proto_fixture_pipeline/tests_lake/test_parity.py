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
