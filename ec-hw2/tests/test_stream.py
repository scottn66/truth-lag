"""Tests for the stream ETL: ingest/parse_stream.py, label_live.py and late_reverts.py.

Run (from the repo root):
    .venv/bin/python -m pytest ec-hw2/tests/test_stream.py -q

The fixtures are tiny made-up events. They use the same fields and types as the
real capture files (page_change 1.12.0, tags-change 1.0.0, revert-risk 1.3.0)
and the same string columns as the slim September dump file.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from ingest import label_live, late_reverts, parse_stream  # noqa: E402

T0 = pd.Timestamp("2026-10-20T10:00:00Z")      # inside config.LIVE_WINDOW
S = pd.Timedelta(1, unit="s")
OLD = time.time() - 3600                       # mtime for closed files


# --------------------------------------------------------------------------
# Event builders (same shapes as the real raw files)
# --------------------------------------------------------------------------
def iso(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_ms(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def meta(stream, mid, dt, domain="en.wikipedia.org"):
    dc = "eqiad"
    return {"stream": stream, "id": mid, "domain": domain, "dt": iso_ms(dt),
            "topic": f"{dc}.{stream}", "partition": 0, "offset": 1}


def person(name="Alice", uid=11, bot=False, temp=False):
    return {"user_text": name, "user_id": uid, "is_bot": bot, "is_temp": temp,
            "edit_count": 5, "groups": ["*", "user"]}


def pc_ev(rev_id, page_id, rev_dt, parent_id=0, prior=None, kind="edit", ns=0, sha1=None,
          size=100, revert=None, who=None, meta_dt=None, mid=None, domain="en.wikipedia.org"):
    """A page_change event. prior = (rev_id, rev_dt, size, sha1)."""
    rev_dt = pd.Timestamp(rev_dt)
    meta_dt = rev_dt + 2 * S if meta_dt is None else pd.Timestamp(meta_dt)
    ev = {"changelog_kind": "insert" if kind == "create" else "update", "page_change_kind": kind,
          "dt": iso(rev_dt), "wiki_id": "enwiki",
          "page": {"page_id": page_id, "page_title": f"Page_{page_id}", "namespace_id": ns,
                   "is_redirect": False, "namespace_is_content": ns == 0},
          "performer": who or person(),
          "revision": {"rev_id": rev_id, "rev_dt": iso(rev_dt), "is_minor_edit": False,
                       "rev_sha1": sha1 or f"abc{rev_id}", "rev_size": size,
                       "rev_parent_id": parent_id, "comment": "edit summary"},
          "$schema": "/mediawiki/page/change/1.12.0",
          "meta": meta(config.STREAM_PAGE_CHANGE, mid or f"pc-{rev_id}", meta_dt, domain)}
    if prior is not None:
        ev["prior_state"] = {"revision": {"rev_id": prior[0], "rev_dt": iso(prior[1]),
                                          "rev_size": prior[2], "rev_sha1": prior[3]}}
    if revert is not None:
        ev["revision"]["revert"] = revert
    return ev


def revert(method, exact, oldest, newest, original=None):
    r = {"method": method, "is_exact": exact, "rev_reverted_oldest_id": oldest,
         "rev_reverted_newest_id": newest}
    if original is not None:
        r["rev_original_id"], r["rev_original_dt"] = original[0], iso(original[1])
    return r


def tag_ev(mid, rev_id, page_id, rev_ts, meta_dt, tags, prior_tags, ns=0):
    return {"$schema": "/mediawiki/revision/tags-change/1.0.0",
            "meta": meta(config.STREAM_TAGS, mid, meta_dt), "database": "enwiki",
            "page_id": page_id, "page_title": f"Page_{page_id}", "page_namespace": ns,
            "rev_id": rev_id, "rev_timestamp": iso(rev_ts), "rev_sha1": "abc",
            "tags": tags, "prior_state": {"tags": prior_tags}}


def risk_ev(mid, rev_id, page_id, rev_dt, meta_dt, p):
    return {"$schema": "/mediawiki/page/prediction_classification_change/1.3.0",
            "page_change_kind": "edit", "wiki_id": "enwiki",
            "meta": meta(config.STREAM_REVERT_RISK, mid, meta_dt),
            "page": {"page_id": page_id, "namespace_id": 0},
            "revision": {"rev_id": rev_id, "rev_dt": iso(rev_dt)},
            "predicted_classification": {"model_name": "revertrisk-language-agnostic",
                                         "model_version": "3", "predictions": ["false"],
                                         "probabilities": {"true": p, "false": 1 - p}}}


def part_path(raw: Path, stream: str, dt, session="20261024T000000-aaaaaa", n=0) -> Path:
    dt = pd.Timestamp(dt)
    d = raw / stream / f"dt={dt:%Y-%m-%d}" / f"hour={dt:%H}"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"part-{session}-{n}.ndjson.gz"


def write_part(raw, stream, events, session="20261024T000000-aaaaaa", mtime=OLD) -> Path:
    p = part_path(raw, stream, events[0]["meta"]["dt"], session)
    with gzip.open(p, "wb") as f:
        for e in events:
            f.write((json.dumps(e) + "\n").encode())
    os.utime(p, (mtime, mtime))
    return p


# --------------------------------------------------------------------------
# One small capture that runs through all three scripts
# --------------------------------------------------------------------------
BOB = person("~2026-10001-01", 21, temp=True)
CAROL = person("Carol", 31)
DAVE = person("Dave", 41)
BOT = person("ExampleBot", 51, bot=True)


def scenario_events():
    t = T0
    pc = [
        # page 1: exact manual revert of 102..103 back to the original 101
        pc_ev(101, 1, t, kind="create", sha1="a101"),
        pc_ev(102, 1, t + 10 * S, 101, (101, t, 100, "a101"), who=BOB),
        pc_ev(103, 1, t + 20 * S, 102, (102, t + 10 * S, 100, "abc102"), who=CAROL),
        pc_ev(104, 1, t + 60 * S, 103, (103, t + 20 * S, 100, "abc103"), sha1="a101", who=DAVE,
              revert=revert("manual", True, 102, 103, original=(101, t))),
        pc_ev(105, 1, t + 100 * S, 104, (104, t + 60 * S, 100, "a101")),
        # page 2: inexact undo of 202..203 (no original; use oldest_id)
        pc_ev(201, 2, t, kind="create"),
        pc_ev(202, 2, t + 10 * S, 201, (201, t, 100, "abc201"), who=BOB),
        pc_ev(203, 2, t + 20 * S, 202, (202, t + 10 * S, 100, "abc202"), who=BOB),
        pc_ev(204, 2, t + 30 * S, 203, (203, t + 20 * S, 100, "abc203"), who=DAVE,
              revert=revert("undo", False, 202, 203)),
        # page 3: 302 is covered by an inexact undo first, then by two exact reverts
        # at the same second; the first exact one by (rev_dt, rev_id) is 304.
        pc_ev(301, 3, t, kind="create"),
        pc_ev(302, 3, t + 10 * S, 301, (301, t, 100, "abc301"), who=BOB),
        pc_ev(303, 3, t + 20 * S, 302, (302, t + 10 * S, 100, "abc302"), who=DAVE,
              revert=revert("undo", False, 302, 302)),
        pc_ev(305, 3, t + 40 * S, 303, (303, t + 20 * S, 100, "abc303"), who=CAROL,
              revert=revert("rollback", True, 302, 303, original=(301, t))),
        pc_ev(304, 3, t + 40 * S, 303, (303, t + 20 * S, 100, "abc303"), who=DAVE,
              revert=revert("manual", True, 302, 303, original=(301, t))),
        # page 4: undo of an older edit: newest_id (402) != parent_id (406)
        pc_ev(401, 4, t, kind="create"),
        pc_ev(402, 4, t + 10 * S, 401, (401, t, 100, "abc401")),
        pc_ev(403, 4, t + 20 * S, 402, (402, t + 10 * S, 100, "abc402")),
        pc_ev(406, 4, t + 25 * S, 403, (403, t + 20 * S, 100, "abc403")),
        pc_ev(407, 4, t + 30 * S, 406, (406, t + 25 * S, 100, "abc406"), who=DAVE,
              revert=revert("undo", False, 402, 402)),
        # page 5: a null revision (same sha1 as its parent) is dropped from the cohort
        pc_ev(501, 5, t, kind="create", sha1="nul1"),
        pc_ev(502, 5, t + 10 * S, 501, (501, t, 100, "nul1"), sha1="nul1"),
        # page 6 (namespace 1): not in the cohort, but its revert is still used
        pc_ev(601, 6, t, 600, (600, t - 60 * S, 100, "abc600"), ns=1),
        pc_ev(602, 6, t + 10 * S, 601, (601, t, 100, "abc601"), ns=1, who=DAVE,
              revert=revert("rollback", True, 601, 601, original=(600, t - 60 * S))),
        # outside the live window, and a bot edit
        pc_ev(701, 7, pd.Timestamp("2026-10-19T23:30:00Z"), 700, (700, t - 86400 * S, 100, "abc700")),
        pc_ev(801, 8, t, 800, (800, t - 3600 * S, 90, "abc800"), size=120, who=BOT),
        # a page move (kind 'move') is not an edit
        pc_ev(901, 9, t, 900, (900, t - 60 * S, 100, "abc900"), kind="move", sha1="abc900"),
        # October reverts of September revisions (late reverts, see test_late_revert_classes)
        pc_ev(9001, 10, t, 9000, (9000, t - 86400 * S, 100, "abc9000"), who=DAVE,
              revert=revert("undo", True, 1002, 9000, original=(1001, "2026-09-05T00:00:00Z"))),
        pc_ev(9002, 10, t + 60 * S, 9001, (9001, t, 100, "abc9001"), who=CAROL,
              revert=revert("rollback", True, 9001, 9001, original=(9000, t - 86400 * S))),
        pc_ev(9101, 11, t, 9100, (9100, t - 3600 * S, 100, "abc9100"), who=DAVE,
              revert=revert("undo", False, 1101, 1101)),
        pc_ev(9301, 13, t, 9300, (9300, t - 3600 * S, 100, "abc9300"), who=DAVE,
              revert=revert("rollback", True, 1301, 9300, original=(1300, "2026-09-24T00:00:00Z"))),
        # a late revert on a page outside namespace 0 (ns 4)
        pc_ev(9701, 17, t, 9700, (9700, t - 3600 * S, 100, "abc9700"), ns=4, who=DAVE,
              revert=revert("undo", True, 1701, 9700, original=(1700, "2026-09-02T00:00:00Z"))),
        # page 15: EXACT undo of an older edit. 1504 reverted 1503 (back to 1502's content);
        # then 1505 undoes 1502 (newest_id 1502 != parent 1504) and restores 1501 exactly,
        # so it also undoes 1503 and 1504 (identity revert).
        pc_ev(1501, 15, t, kind="create", sha1="s1501"),
        pc_ev(1502, 15, t + 10 * S, 1501, (1501, t, 100, "s1501"), sha1="s1502", who=BOB),
        pc_ev(1503, 15, t + 20 * S, 1502, (1502, t + 10 * S, 100, "s1502"), sha1="s1503", who=CAROL),
        pc_ev(1504, 15, t + 30 * S, 1503, (1503, t + 20 * S, 100, "s1503"), sha1="s1502", who=DAVE,
              revert=revert("manual", True, 1503, 1503, original=(1502, t + 10 * S))),
        pc_ev(1505, 15, t + 40 * S, 1504, (1504, t + 30 * S, 100, "s1502"), sha1="s1501",
              revert=revert("undo", True, 1502, 1502, original=(1501, t))),
        # page 16: a rollback whose range starts before the capture (oldest 1599 not captured)
        pc_ev(1601, 16, t, 1600, (1600, t - 60 * S, 100, "abc1600"), who=BOB),
        pc_ev(1602, 16, t + 10 * S, 1601, (1601, t, 100, "abc1601"), who=DAVE,
              revert=revert("rollback", True, 1599, 1601, original=(1598, t - 3600 * S))),
    ]
    tags = [
        tag_ev("tg-1", 102, 1, t + 10 * S, t + 40 * S, ["visualeditor"], []),             # +30 s: kept
        tag_ev("tg-2", 102, 1, t + 10 * S, t + 100 * S, ["late-tag", "visualeditor"], ["visualeditor"]),  # +90 s
        tag_ev("tg-3", 102, 1, t + 10 * S, t + 62 * S, ["mw-reverted", "visualeditor"], ["visualeditor"]),
        tag_ev("tg-4", 103, 1, t + 20 * S, t + 63 * S, ["mw-reverted"], []),
        # late reverts: page 12 tag only (before the page_change capture), page 13 two tags
        tag_ev("tg-5", 1201, 12, "2026-09-20T00:00:00Z", "2026-10-18T00:00:00Z", ["mw-reverted"], []),
        tag_ev("tg-6", 1301, 13, "2026-09-25T00:00:00Z", t + 302 * S, ["mw-reverted"], []),     # 300 s after E
        tag_ev("tg-7", 1301, 13, "2026-09-25T00:00:00Z", t + 1202 * S, ["mw-reverted"], []),    # 1200 s after E
    ]
    risk = [
        risk_ev("rr-1", 102, 1, t + 10 * S, t + 13 * S, 0.9),
        risk_ev("rr-2", 102, 1, t + 10 * S, t + 20 * S, 0.5),     # later score: dropped
        risk_ev("rr-3", 103, 1, t + 20 * S, t + 23 * S, 0.2),
    ]
    return pc, tags, risk


def slim_frame() -> pd.DataFrame:
    """September revisions, all strings, the 12 columns of config.HISTORY_SLIM_COLUMNS."""
    rows = [  # revision_id, page_id, event_timestamp, reverted, page_namespace
        ("1001", "10", "2026-09-05 00:00:00.0", "false", "0"),
        ("1002", "10", "2026-09-06 00:00:00.0", "false", "0"),
        ("1003", "10", "2026-09-07 00:00:00.0", "true", "0"),   # the dump already says reverted
        ("1101", "11", "2026-09-10 00:00:00.0", "false", "0"),  # inside HISTORY_WINDOW
        ("1201", "12", "2026-09-20 00:00:00.0", "false", "0"),
        ("1301", "13", "2026-09-25 00:00:00.0", None, "0"),
        ("1302", "99", "2026-09-26 00:00:00.0", "false", "0"),  # no stream signal
        ("1701", "17", "2026-09-03 00:00:00.0", "false", "4"),  # namespace 4 (Wikipedia:)
    ]
    df = pd.DataFrame({c: [None] * len(rows) for c in config.HISTORY_SLIM_COLUMNS})
    for i, (rid, pid, ts, rv, ns) in enumerate(rows):
        df.loc[i, ["revision_id", "page_id", "event_timestamp", "revision_is_identity_reverted",
                   "page_namespace"]] = [rid, pid, ts, rv, ns]
    df["revision_is_identity_revert"] = "false"
    return df.astype(object)


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    root = tmp_path_factory.mktemp("stream")
    raw, parsed, tables, hist = root / "raw", root / "parsed", root / "tables", root / "history"
    pc, tags, risk = scenario_events()
    write_part(raw, config.STREAM_PAGE_CHANGE, pc)
    # the capture repeats one event after a reconnect, in a second session file
    write_part(raw, config.STREAM_PAGE_CHANGE, [pc[4]], session="20261024T010000-bbbbbb")
    write_part(raw, config.STREAM_TAGS, tags)
    write_part(raw, config.STREAM_REVERT_RISK, risk)
    parse_summary = parse_stream.run(raw, parsed, include_open=False)
    live_summary = label_live.run(parsed, tables)
    hist.mkdir()
    table = pa.Table.from_pandas(slim_frame(), schema=pa.schema(
        [(c, pa.string()) for c in config.HISTORY_SLIM_COLUMNS]), preserve_index=False)
    pq.write_table(table, hist / config.HISTORY_SLIM_FILE)
    late_summary = late_reverts.run(parsed, tables, hist)
    return {"root": root, "parsed": parsed, "tables": tables, "parse": parse_summary,
            "live": live_summary, "late": late_summary}


# --------------------------------------------------------------------------
# parse_stream.py
# --------------------------------------------------------------------------
def _lines(n):
    return [(json.dumps(pc_ev(10_000 + i, 1, T0 + i * S)) + "\n").encode() for i in range(n)]


def test_gzip_without_end_marker_keeps_flushed_lines(tmp_path):
    """Like an open capture file: 40 lines sync-flushed, 10 more still in the compressor."""
    lines = _lines(50)
    buf = io.BytesIO()
    gz = gzip.GzipFile(fileobj=buf, mode="wb")
    for line in lines[:40]:
        gz.write(line)
    gz.flush()                       # the capture flushes like this every 500 events
    data = buf.getvalue()            # no gzip end marker yet
    for line in lines[40:]:
        gz.write(line)
    p = tmp_path / "part-x-0.ndjson.gz"
    p.write_bytes(data)
    problems = []
    got = list(parse_stream.read_lines(p, problems))
    assert len(got) == 40 and got == lines[:40]
    assert len(problems) == 1 and "EOFError" in problems[0]["error"] and problems[0]["lines_kept"] == 40


def test_truncated_part_file_keeps_complete_lines(tmp_path):
    """A file cut at a random byte: we keep only complete lines and log the file."""
    raw, out = tmp_path / "raw", tmp_path / "parsed"
    lines = _lines(400)
    full = gzip.compress(b"".join(lines))
    p = part_path(raw, config.STREAM_PAGE_CHANGE, T0)
    p.write_bytes(full[: int(len(full) * 0.6)])
    os.utime(p, (OLD, OLD))
    s = parse_stream.run(raw, out)
    st = s["streams"][config.STREAM_PAGE_CHANGE]
    assert st["cut_short_file_count"] == 1
    assert 0 < st["rows"] < 400 and st["bad_json"] == 0
    df = pd.read_parquet(out / "page_change.parquet")
    assert df["rev_id"].tolist() == list(range(10_000, 10_000 + st["rows"]))   # a clean prefix


def test_open_files_are_skipped_unless_asked(tmp_path):
    raw = tmp_path / "raw"
    write_part(raw, config.STREAM_PAGE_CHANGE, [pc_ev(1, 1, T0)], mtime=OLD)
    write_part(raw, config.STREAM_PAGE_CHANGE, [pc_ev(2, 1, T0 + S)], session="new", mtime=time.time())
    s = parse_stream.run(raw, tmp_path / "a")
    assert s["row_counts"]["page_change.parquet"] == 1
    assert s["streams"][config.STREAM_PAGE_CHANGE]["files_skipped_open_count"] == 1
    s = parse_stream.run(raw, tmp_path / "b", include_open=True)
    assert s["row_counts"]["page_change.parquet"] == 2


def test_meta_id_dedupe_and_canary(tmp_path):
    raw = tmp_path / "raw"
    a, b = pc_ev(1, 1, T0), pc_ev(2, 1, T0 + S)
    canary = pc_ev(3, 1, T0 + 2 * S, domain="canary")
    write_part(raw, config.STREAM_PAGE_CHANGE, [a, b, canary])
    write_part(raw, config.STREAM_PAGE_CHANGE, [b], session="resume")     # repeated after a reconnect
    s = parse_stream.run(raw, tmp_path / "out")
    st = s["streams"][config.STREAM_PAGE_CHANGE]
    assert st["rows"] == 2 and st["duplicate_meta_id"] == 1 and st["canary"] == 1
    df = pd.read_parquet(tmp_path / "out" / "page_change.parquet")
    assert df["meta_id"].is_unique


def test_parsed_tables(pipeline):
    parsed = pipeline["parsed"]
    pc = pd.read_parquet(parsed / "page_change.parquet")
    assert list(pc.columns) == [f.name for f in parse_stream.PAGE_CHANGE_SCHEMA]
    assert pipeline["parse"]["streams"][config.STREAM_PAGE_CHANGE]["duplicate_meta_id"] == 1
    assert str(pc["meta_dt"].dtype) == "datetime64[us, UTC]"
    r = pc.set_index("rev_id")
    assert r.loc[104, "revert_method"] == "manual" and bool(r.loc[104, "revert_is_exact"])
    assert r.loc[104, "revert_original_id"] == 101 and r.loc[104, "prior_sha1"] == "abc103"
    assert r.loc[104, "revert_original_dt"] == T0
    tg = pd.read_parquet(parsed / "tag_events.parquet").set_index("meta_id")
    assert list(tg.loc["tg-2", "added"]) == ["late-tag"] and list(tg.loc["tg-2", "removed"]) == []
    assert bool(tg.loc["tg-3", "mw_reverted_added"]) and not bool(tg.loc["tg-1", "mw_reverted_added"])
    rr = pd.read_parquet(parsed / "revert_risk.parquet")
    assert list(rr.columns) == parse_stream.REVERT_RISK_COLUMNS
    assert rr.set_index("rev_id").loc[102, "prob_true"] == 0.9      # the earliest score wins
    assert (parsed / "capture_gaps.csv").exists() and (parsed / "_SUCCESS_parsed.json").exists()


def test_find_gaps_uses_time_only():
    df = pd.DataFrame({"meta_dt": [T0, T0 + 60 * S, T0 + 300 * S],
                       "topic": ["eqiad.x", "codfw.x", "eqiad.x"], "partition": [0, 0, 0]})
    g = parse_stream.find_gaps("x", df, min_gap_s=120)
    assert len(g) == 1 and g.iloc[0]["gap_s"] == 240 and g.iloc[0]["topic"] == "eqiad.x"


# --------------------------------------------------------------------------
# label_live.py
# --------------------------------------------------------------------------
def _R(rows):
    return pd.DataFrame(rows, columns=["page_id", "rev_id", "rev_dt"]).assign(
        rev_dt=lambda d: pd.to_datetime(d["rev_dt"], utc=True))


def _E(**kw):
    base = {"page_id": 1, "rev_id": 999, "rev_dt": T0 + 100 * S, "prior_rev_dt": T0 + 30 * S,
            "parent_id": 103, "revert_is_exact": True, "revert_original_id": 101,
            "revert_original_dt": T0, "revert_oldest_id": 102, "revert_newest_id": 103,
            "revert_method": "manual"}
    base.update(kw)
    df = pd.DataFrame([base])
    for c in ("rev_dt", "prior_rev_dt", "revert_original_dt"):
        df[c] = pd.to_datetime(df[c], utc=True)
    return df


def test_range_cover_exact_uses_original():
    R = _R([(1, 100, T0 - 10 * S), (1, 101, T0), (1, 102, T0 + 10 * S), (1, 103, T0 + 30 * S),
            (1, 106, T0 + 30 * S),         # same second as the prior revision, but id > newest
            (1, 107, T0 + 200 * S),        # after the revert
            (2, 102, T0 + 10 * S)])        # another page
    p = label_live.range_cover(R, _E())
    assert sorted(R.loc[p["r_row"], "rev_id"]) == [102, 103]
    assert set(p["range_size"]) == {2}


def test_range_cover_exact_undo_of_older_edit_covers_up_to_parent():
    """An exact undo of 102 while the page is at 104 restores 101: 102, 103 and 104 are
    undone (identity revert). The same undo, if inexact, covers only [oldest, newest]."""
    R = _R([(1, 101, T0), (1, 102, T0 + 10 * S), (1, 103, T0 + 20 * S), (1, 104, T0 + 30 * S)])
    E = _E(rev_dt=T0 + 40 * S, prior_rev_dt=T0 + 30 * S, parent_id=104, revert_method="undo",
           revert_oldest_id=102, revert_newest_id=102)
    p = label_live.range_cover(R, E)
    assert sorted(R.loc[p["r_row"], "rev_id"]) == [102, 103, 104]
    E = _E(rev_dt=T0 + 40 * S, prior_rev_dt=T0 + 30 * S, parent_id=104, revert_method="undo",
           revert_oldest_id=102, revert_newest_id=102, revert_is_exact=False,
           revert_original_id=None, revert_original_dt=None)
    p = label_live.range_cover(R, E)
    assert sorted(R.loc[p["r_row"], "rev_id"]) == [102]


def test_range_complete_flags():
    captured = pd.DataFrame({"page_id": [1, 1, 2], "rev_id": [100, 102, 201]})
    E = pd.DataFrame({"page_id": [1, 1, 2, 3, 1],
                      "revert_oldest_id": pd.array([102, 50, 205, 300, None], dtype="Int64")})
    got = label_live.range_complete_flags(E, captured).tolist()
    # captured on the page / before the capture / after the first captured edit / page
    # never captured / no oldest_id
    assert got == [True, False, True, False, False]


def test_range_cover_inexact_uses_oldest():
    R = _R([(1, 101, T0), (1, 102, T0 + 10 * S), (1, 103, T0 + 30 * S)])
    E = _E(revert_is_exact=False, revert_original_id=None, revert_original_dt=None,
           revert_method="undo")
    p = label_live.range_cover(R, E)
    assert sorted(R.loc[p["r_row"], "rev_id"]) == [102, 103]


def test_newest_equals_parent_check(pipeline):
    nc = pipeline["live"]["newest_id_equals_parent_check"]
    # 407 undoes 402 while the page is at 406; 9101 (a late-revert fixture) undoes 1101;
    # 1505 undoes 1502 while the page is at 1504
    assert nc["exceptions"] == 3 and {x["rev_id"] for x in nc["examples"]} == {407, 9101, 1505}
    la = pd.read_parquet(pipeline["tables"] / "live_revert_links_all.parquet")
    p4 = la[la["reverting_rev_id"] == 407].set_index("reverted_rev_id")
    # Inexact undo: R.rev_id <= newest_id, so the undo covers only 402.
    # 403 (saved after newest_id 402, before the parent 406) and 406 are not covered.
    assert sorted(p4.index) == [402] and not bool(p4.loc[402, "beyond_newest"])
    # Exact undo of an older edit: it covers up to the parent, and flags the pairs
    # after newest_id as beyond_newest.
    p15 = la[la["reverting_rev_id"] == 1505].set_index("reverted_rev_id")
    assert sorted(p15.index) == [1502, 1503, 1504]
    assert p15["beyond_newest"].to_dict() == {1502: False, 1503: True, 1504: True}
    assert set(p15["range_size"]) == {3} and p15["range_complete"].all()
    assert nc["pairs_beyond_newest_all"] == 2 and nc["cohort_links_beyond_newest"] == 1


def test_cover_pairs_in_pipeline(pipeline):
    la = pd.read_parquet(pipeline["tables"] / "live_revert_links_all.parquet")
    pairs = set(zip(la["reverted_rev_id"], la["reverting_rev_id"]))
    assert {(102, 104), (103, 104), (202, 204), (203, 204), (601, 602)} <= pairs
    assert (101, 104) not in pairs and (105, 104) not in pairs and (201, 204) not in pairs
    ns1 = la[la["reverted_rev_id"] == 601].iloc[0]
    assert not ns1["in_cohort"] and pd.isna(ns1["cohort"]) and ns1["page_ns"] == 1


def test_first_exact_choice(pipeline):
    links = pd.read_parquet(pipeline["tables"] / "live_revert_links.parquet").set_index("reverted_rev_id")
    assert list(links.columns) == [f.name for f in label_live.LINKS_SCHEMA if f.name != "reverted_rev_id"]
    row = links.loc[302]
    # 303 (inexact undo) came first; 304 and 305 are exact at the same second: 304 wins
    assert row["reverting_rev_id"] == 304 and row["method"] == "manual" and bool(row["is_exact"])
    assert row["T_s"] == 30 and row["K_s"] == pytest.approx(2.0) and row["range_size"] == 2
    assert row["cohort"] == "live" and row["source"] == "stream" and bool(row["within_followup"])
    assert bool(row["by_other"]) and row["author_kind"] == "temporary" and row["reverter_kind"] == "registered"
    assert 202 not in links.index            # only an inexact undo covers it
    assert bool(links.loc[102, "confirmed_by_tag"]) and not bool(links.loc[302, "confirmed_by_tag"])
    # page 15: 1503 was first reverted by 1504; 1504 by the exact undo 1505
    assert links.loc[1503, "reverting_rev_id"] == 1504 and links.loc[1504, "reverting_rev_id"] == 1505


def test_range_complete_and_tag_shares(pipeline):
    links = pd.read_parquet(pipeline["tables"] / "live_revert_links.parquet").set_index("reverted_rev_id")
    assert bool(links.loc[102, "range_complete"]) and bool(links.loc[9001, "range_complete"])
    # 1602's range starts at 1599, before the page's first captured edit (1601)
    assert not bool(links.loc[1601, "range_complete"]) and links.loc[1601, "range_size"] == 1
    tc = pipeline["live"]["tag_confirmed_share_of_reverted"]
    assert tc["complete_ranges_only"] is True
    # complete ranges: 102, 103, 302, 303, 9001, 1502, 1503, 1504; only 102 and 103 have the tag
    assert tc["range_size_le_max"] == {"n": 8, "confirmed": 2, "share": 0.25}
    assert tc["range_size_gt_max"]["n"] == 0
    assert tc["range_incomplete"] == {"n": 1, "confirmed": 0, "share": 0.0}


def test_cohort_rules_and_columns(pipeline):
    flat = pd.read_parquet(pipeline["tables"] / "live_revisions.parquet")
    assert list(flat.columns) == [f.name for f in label_live.LIVE_REVISIONS_SCHEMA]
    assert flat["rev_id"].is_unique and set(flat["cohort"]) == {"live"}
    rev = flat.set_index("rev_id")
    drops = pipeline["live"]["cohort"]["drops"]
    assert drops["null_revision"] == 1 and 502 not in rev.index
    assert drops["namespace_not_0"] == 3 and drops["outside_window"] == 1
    assert drops["kind_not_create_or_edit"] == {"move": 1}
    assert 601 not in rev.index and 701 not in rev.index and 901 not in rev.index
    assert rev.loc[102, "page_title"] == rev.loc[102, "page_title_historical"] == "Page_1"
    assert rev.loc[102, "user_kind"] == "temporary" and bool(rev.loc[102, "is_anon"])
    assert rev.loc[102, "user_key"] == "t:~2026-10001-01" and rev.loc[103, "user_key"] == "u:31"
    assert rev.loc[801, "user_kind"] == "bot" and bool(rev.loc[801, "is_bot"])
    assert rev.loc[801, "size_delta"] == 30 and rev.loc[101, "size_delta"] == 100   # create: rev_size
    assert rev.loc[104, "is_revert"] and rev.loc[104, "revert_method"] == "manual"
    assert rev.loc[102, "revert_risk"] == 0.9 and pd.isna(rev.loc[101, "revert_risk"])
    assert rev.loc[101, "sha1"] == format(int("a101", 36), "040x")                  # hex, like history
    # page 1 events seen at t+2, +12, +22, +62 before 105 (seen at t+102)
    assert rev.loc[105, "page_edits_prev_1h"] == 4 and rev.loc[101, "page_edits_prev_1h"] == 0
    newest = pd.Timestamp(pipeline["live"]["newest_meta_dt"])
    assert rev.loc[101, "followup_s"] == int((newest - T0).total_seconds())


def test_save_time_tag_window(pipeline):
    rev = pd.read_parquet(pipeline["tables"] / "live_revisions.parquet").set_index("rev_id")
    # tg-1 at +30 s is kept; tg-2 at +90 s is too late; mw-reverted is never a save-time tag
    assert list(rev.loc[102, "tags"]) == ["visualeditor"]
    assert bool(rev.loc[102, "mw_reverted_tag"]) and rev.loc[102, "mw_reverted_at"] == T0 + 62 * S
    assert list(rev.loc[104, "tags"]) == [] and not bool(rev.loc[104, "mw_reverted_tag"])


def test_numpy_bool_flags_give_bot():
    df = pd.DataFrame({"user_name": ["ExampleBot", "~2026-1-1"], "is_bot": np.array([True, False]),
                       "is_temp": np.array([False, True]), "user_id": [5, 6]})
    out = label_live.add_user_columns(df)
    assert out["user_kind"].tolist() == ["bot", "temporary"]
    assert out["user_key"].tolist() == ["u:5", "t:~2026-1-1"]


def test_success_file_is_provisional(pipeline):
    ok = json.loads((pipeline["tables"] / "_SUCCESS_live.json").read_text())
    assert ok["provisional"] is True and ok["row_counts"]["live_revisions.parquet"] > 0


# --------------------------------------------------------------------------
# late_reverts.py
# --------------------------------------------------------------------------
def test_late_revert_classes(pipeline):
    lr = pd.read_parquet(pipeline["tables"] / "late_reverts.parquet").set_index("rev_id")
    assert list(lr.columns) == [f.name for f in late_reverts.LATE_SCHEMA if f.name != "rev_id"]
    assert sorted(lr.index) == [1002, 1101, 1201, 1301, 1701]     # 1003: the dump says reverted
    assert lr.loc[1002, "class"] == "exact" and lr.loc[1002, "reverting_rev_id"] == 9001
    assert lr.loc[1002, "restored_later"] is True            # 9002 reverted 9001
    assert lr.loc[1101, "class"] == "inexact_undo" and lr.loc[1101, "method"] == "undo"
    assert lr.loc[1201, "class"] == "method_unknown" and pd.isna(lr.loc[1201, "reverting_rev_id"])
    assert bool(lr.loc[1201, "age_upper_bound"]) and lr.loc[1201, "restored_later"] is None
    assert lr.loc[1201, "age_days"] == pytest.approx(28.0)  # Sep 20 -> tag on Oct 18
    assert list(lr.loc[1301, "via"]) == ["page_change", "tag"] and lr.loc[1301, "class"] == "exact"
    assert list(lr.loc[1002, "via"]) == ["page_change"]
    assert lr.loc[1301, "first_signal_at"] == T0 + 2 * S
    assert lr.loc[1701, "page_ns"] == 4 and lr.loc[1002, "page_ns"] == 0
    assert lr.loc[1701, "class"] == "exact" and lr.loc[1701, "reverting_rev_id"] == 9701
    # no history_revisions.parquet here: the cohort window is used (Sep 10 is inside)
    assert bool(lr.loc[1101, "in_history_cohort"]) and not bool(lr.loc[1002, "in_history_cohort"])
    s = pipeline["late"]
    assert s["by_class"] == {"exact": 3, "inexact_undo": 1, "method_unknown": 1} and s["rows"] == 5
    assert s["by_class_ns0"] == {"exact": 2, "inexact_undo": 1, "method_unknown": 1}
    assert s["rows_ns0"] == 4 and s["by_namespace"] == {"0": 4, "4": 1}
    assert s["in_history_cohort_method"].startswith("window_fallback")


def test_late_tag_link_window(pipeline):
    s = pipeline["late"]["step2"]
    # tg-6 is 300 s after the covering revert (linked); tg-7 is 1200 s after (not linked)
    assert s["window_s"] == config.LATE_TAG_LINK_WINDOW_S == 600
    assert s["mw_reverted_additions_on_sept_not_reverted"] == 3
    assert s["linked_within_window"] == 1 and s["not_linked"] == 2
    assert pipeline["late"]["method_unknown_by_period"]["before_page_change_capture"] == 1
