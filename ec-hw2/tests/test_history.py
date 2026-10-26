"""Tests for ingest/parse_history.py (the history cohort ETL).

Purpose: check casting, the filters, the null-revision rules, the user-kind order,
the reverter self-join, the 20-day label, the prev-1h count and one full run.
Inputs: tiny synthetic tables with the same column names as the real dump files.
Every value is a string (or null), as in the real Parquet copies.
Outputs: none (pytest writes its own temporary folder).
Run (from the repo root):
    .venv/bin/python -m pytest ec-hw2/tests/test_history.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from ingest import parse_history as ph  # noqa: E402
from ingest.history_columns import COLUMNS, cast_history_frame, sha1_base36_to_hex  # noqa: E402

TS = "2026-09-09 12:00:00.0"   # inside config.HISTORY_WINDOW


# --------------------------------------------------------------------------
# Fixture builders (all values are strings, like the real files)
# --------------------------------------------------------------------------
def cohort_row(**kw) -> dict:
    row = {c: None for c in COLUMNS}
    row.update({
        "wiki_db": "enwiki", "event_entity": "revision", "event_type": "create",
        "event_timestamp": TS, "event_comment": "copyedit",
        "event_user_id": "100", "event_user_text_historical": "Alice", "event_user_text": "Alice",
        "event_user_is_temporary": "false", "event_user_is_anonymous": "false",
        "event_user_revision_count": "5",
        "page_id": "1", "page_title_historical": "Page_One", "page_title": "Page_One",
        "page_namespace_historical": "0", "page_namespace": "0",
        "revision_id": "1000", "revision_parent_id": "999", "revision_minor_edit": "false",
        "revision_text_bytes": "500", "revision_text_bytes_diff": "10",
        "revision_text_sha1": "abc123",
        "revision_is_identity_reverted": "false", "revision_is_identity_revert": "false",
    })
    row.update(kw)
    return row


def slim_row(**kw) -> dict:
    row = {c: None for c in config.HISTORY_SLIM_COLUMNS}
    row.update({
        "revision_id": "5000", "page_id": "1", "event_timestamp": TS,
        "revision_is_identity_revert": "false", "revision_is_identity_reverted": "false",
        "event_user_id": "200", "event_user_text": "Bob", "event_user_text_historical": "Bob",
        "page_namespace": "0",
    })
    row.update(kw)
    return row


def string_frame(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series([r[c] for r in rows], dtype="object") for c in columns})


def write_strings(rows: list[dict], columns: list[str], path: Path) -> Path:
    """Write a Parquet file where every column is a string, like the VPS files."""
    tbl = pa.table({c: pa.array([r[c] for r in rows], type=pa.string()) for c in columns})
    pq.write_table(tbl, path)
    return path


def cast_cohort(rows: list[dict]) -> pd.DataFrame:
    return cast_history_frame(string_frame(rows, COLUMNS))


# --------------------------------------------------------------------------
# Casting and filters
# --------------------------------------------------------------------------
def test_cast_types():
    df = cast_cohort([cohort_row(revision_parent_id="", revision_is_identity_reverted="true",
                                 revision_seconds_to_identity_revert="60")])
    assert str(df["revision_id"].dtype) == "Int64"
    assert df["revision_id"].iloc[0] == 1000
    assert df["revision_parent_id"].isna().iloc[0]          # "" becomes null
    assert str(df["revision_is_identity_reverted"].dtype) == "boolean"
    assert bool(df["revision_is_identity_reverted"].iloc[0]) is True
    assert str(df["event_timestamp"].dt.tz) == "UTC"
    assert df["event_timestamp"].iloc[0] == pd.Timestamp("2026-09-09 12:00:00", tz="UTC")
    assert df["revision_seconds_to_identity_revert"].iloc[0] == 60
    assert str(df["event_comment"].dtype) == "string"


def test_filters_window_is_half_open_and_namespace_is_historical():
    rows = [
        cohort_row(revision_id="1"),                                          # kept
        cohort_row(revision_id="2", event_timestamp="2026-09-11 00:00:00.0"), # end is not included
        cohort_row(revision_id="3", event_timestamp="2026-09-07 23:59:59.0"),
        cohort_row(revision_id="4", event_timestamp="2026-09-08 00:00:00.0"), # start is included
        cohort_row(revision_id="5", page_namespace_historical="118"),        # draft at edit time
        cohort_row(revision_id="6", event_type="delete"),
    ]
    kept, drops = ph.filter_cohort(cast_cohort(rows))
    assert sorted(kept["revision_id"].tolist()) == [1, 4]
    assert drops == {"not_revision_create": 1, "outside_window": 2, "namespace_historical_not_0": 1}


# --------------------------------------------------------------------------
# Null revisions
# --------------------------------------------------------------------------
def test_null_revision_rule_a_compares_sha1_with_parent_in_file():
    rows = [
        # The parent is a draft row: it is in the file but not in the kept rows.
        cohort_row(revision_id="999", revision_parent_id="998", revision_text_sha1="abc123",
                   page_namespace_historical="118"),
        cohort_row(revision_id="1000", revision_parent_id="999", revision_text_sha1="abc123",
                   revision_text_bytes_diff="0", event_comment="Alice moved page [[Draft:A]] to [[A]]"),
        # Same parent, different text: kept even though the comment looks like a move.
        cohort_row(revision_id="1001", revision_parent_id="999", revision_text_sha1="zzz999",
                   revision_text_bytes_diff="0", event_comment="Alice moved page [[B]] to [[C]]"),
    ]
    full = cast_cohort(rows)
    kept, _ = ph.filter_cohort(full)
    rule_a, rule_b, _ = ph.null_revision_masks(kept, full)
    by_id = dict(zip(kept["revision_id"].tolist(), zip(rule_a.tolist(), rule_b.tolist())))
    assert by_id[1000] == (True, False)
    assert by_id[1001] == (False, False)


def test_null_revision_rule_b_uses_comment_and_zero_diff():
    rows = [
        cohort_row(revision_id="1", revision_text_bytes_diff="0",
                   event_comment="Alice moved page [[A]] to [[B]]: per talk"),      # dropped (name removed)
        cohort_row(revision_id="2", revision_text_bytes_diff="0",
                   event_comment='Protected "[[X]]": Persistent vandalism'),      # dropped
        cohort_row(revision_id="3", revision_text_bytes_diff="0",
                   event_comment="MOVED PAGE [[A]] to [[B]]"),                    # dropped (case)
        cohort_row(revision_id="4", revision_text_bytes_diff="0", event_comment="typo"),  # kept
        cohort_row(revision_id="5", revision_text_bytes_diff="7",
                   event_comment="Alice moved page [[A]] to [[B]]"),              # kept: text changed
        cohort_row(revision_id="6", revision_text_bytes_diff="0", event_comment=None),    # kept
        cohort_row(revision_id="7", revision_text_bytes_diff="0",
                   event_comment="Bob moved page [[A]] to [[B]]"),                # kept: not her own name
        cohort_row(revision_id="8", revision_text_bytes_diff="0",
                   event_comment="Configured pending changes settings for [[Y]]"),  # dropped
    ]
    full = cast_cohort(rows)    # no parent (999) in the file: rule (a) never applies
    kept, _ = ph.filter_cohort(full)
    rule_a, rule_b, prefix = ph.null_revision_masks(kept, full)
    assert not rule_a.any()
    dropped = sorted(kept.loc[rule_b, "revision_id"].tolist())
    assert dropped == [1, 2, 3, 8]
    assert prefix[kept["revision_id"] == 1].iloc[0] == "moved page"
    assert prefix[kept["revision_id"] == 2].iloc[0] == "protected"


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------
def test_user_kind_order_and_keys():
    rows = [
        cohort_row(revision_id="1", event_user_text_historical=None, event_user_id=None,
                   event_user_is_bot_by="group", event_user_is_temporary=None),   # unknown first
        cohort_row(revision_id="2", event_user_text_historical="~2026-12345-67", event_user_id="300",
                   event_user_is_bot_by="name,group", event_user_is_temporary="true"),  # bot before temp
        cohort_row(revision_id="3", event_user_text_historical="NameBot", event_user_id="400",
                   event_user_is_bot_by="name"),                                    # "name" only: not a bot
        cohort_row(revision_id="4", event_user_text_historical="~2026-11111-22", event_user_id="500",
                   event_user_is_temporary="true"),
        cohort_row(revision_id="5"),
    ]
    df = ph.add_user_fields(cast_cohort(rows)).set_index("revision_id")
    assert df["user_kind"].to_dict() == {1: "unknown", 2: "bot", 3: "registered", 4: "temporary", 5: "registered"}
    assert pd.isna(df.loc[1, "user_key"])
    assert df.loc[2, "user_key"] == "u:300"
    assert df.loc[4, "user_key"] == "t:~2026-11111-22"
    assert df.loc[5, "user_key"] == "u:100"
    assert df["is_bot"].to_dict() == {1: False, 2: True, 3: False, 4: False, 5: False}
    assert (df["is_anon"] == df["is_temp"]).all()
    assert df.loc[4, "is_temp"] and not df.loc[2, "is_temp"]


# --------------------------------------------------------------------------
# Labels and the reverter self-join
# --------------------------------------------------------------------------
def test_20_day_label():
    limit = config.HISTORY_FOLLOWUP_S
    rows = [
        cohort_row(revision_id="1", revision_is_identity_reverted="true",
                   revision_seconds_to_identity_revert=str(limit),
                   revision_first_identity_reverting_revision_id="11"),
        cohort_row(revision_id="2", revision_is_identity_reverted="true",
                   revision_seconds_to_identity_revert=str(limit + 1),
                   revision_first_identity_reverting_revision_id="12"),
        cohort_row(revision_id="3"),
    ]
    df = ph.add_labels(cast_cohort(rows)).set_index("revision_id")
    assert df["reverted"].to_dict() == {1: True, 2: False, 3: False}
    assert df["reverted_any"].to_dict() == {1: True, 2: True, 3: False}
    assert df.loc[2, "reverting_rev_id"] == 12
    assert pd.isna(df.loc[3, "secs_to_revert"])


def _reverted(rev_id, reverting_id, secs="600", **kw):
    return cohort_row(revision_id=rev_id, revision_is_identity_reverted="true",
                      revision_seconds_to_identity_revert=secs,
                      revision_first_identity_reverting_revision_id=reverting_id, **kw)


def test_reverter_join():
    rows = [
        _reverted("1", "5001"),     # reverted by Bob (another registered editor)
        _reverted("2", "5002"),     # self-revert by Alice
        _reverted("3", "5003"),     # reverted by a temporary account
        _reverted("4", "5004"),     # reverted by a bot
        _reverted("5", "5999"),     # reverting row missing from the slim file
        cohort_row(revision_id="6"),
    ]
    slim = [
        slim_row(revision_id="5001", event_timestamp="2026-09-09 12:10:00.0"),
        slim_row(revision_id="5002", event_user_id="100", event_user_text_historical="Alice",
                 event_timestamp="2026-09-09 12:10:00.0"),
        slim_row(revision_id="5003", event_user_id="300", event_user_text_historical="~2026-55555-1",
                 event_timestamp="2026-09-09 12:10:00.0"),
        slim_row(revision_id="5004", event_user_id="400", event_user_text_historical="ClueBot NG",
                 event_user_is_bot_by="name,group", event_timestamp="2026-09-09 12:10:00.0"),
        slim_row(revision_id="7777"),
    ]
    df = ph.add_labels(ph.add_user_fields(cast_cohort(rows)))
    slim_rev = cast_history_frame(string_frame(slim, config.HISTORY_SLIM_COLUMNS)[ph.SLIM_REVERTER_COLS])
    out, checks = ph.join_reverters(df, slim_rev)
    out = out.set_index("revision_id")
    assert out["reverter_kind"].astype(object).where(out["reverter_kind"].notna(), None).to_dict() == {
        1: "registered", 2: "registered", 3: "temporary", 4: "bot", 5: None, 6: None}
    assert out.loc[1, "reverter_key"] == "u:200"
    assert out.loc[3, "reverter_key"] == "t:~2026-55555-1"
    assert out.loc[4, "reverter_name"] == "ClueBot NG"
    assert out["reverted_by_other"].to_dict() == {1: True, 2: False, 3: True, 4: True, 5: False, 6: False}
    assert checks["reverting_ids"] == 5
    assert checks["not_found_in_slim"] == 1
    assert checks["page_id_differs"] == 0
    assert checks["reverting_ts_differs_from_ts_plus_T"] == 0


# --------------------------------------------------------------------------
# page_edits_prev_1h
# --------------------------------------------------------------------------
def test_prev_1h_count():
    t = 1_000_000
    slim_page = np.array([1, 1, 1, 1, 1, 1, 2, 3])
    slim_ts = np.array([t - 3601, t - 3600, t - 1, t, t, t + 5, t - 10, t - 100])
    # One row at t is the edit itself; the other row at t has the same second, so
    # it is also outside [t - 1 h, t). Only t - 3600 and t - 1 count on page 1.
    # For page 1 at t + 3600 the window is [t, t + 3600): the rows at t, t, t + 5.
    got = ph.count_prev_window(np.array([1, 2, 4, 1]), np.array([t, t, t, t + 3600]), slim_page, slim_ts)
    assert got.tolist() == [2, 1, 0, 3]
    assert ph.count_prev_window(np.array([1]), np.array([t]), np.array([], dtype="int64"),
                                np.array([], dtype="int64")).tolist() == [0]


def test_prev_1h_matches_slow_count():
    rng = np.random.default_rng(7)
    slim_page = rng.integers(1, 30, 3000)
    slim_ts = rng.integers(0, 20_000, 3000) + 1_000_000
    page = rng.integers(1, 30, 200)
    ts = rng.integers(4_000, 20_000, 200) + 1_000_000
    fast = ph.count_prev_window(page, ts, slim_page, slim_ts)
    slow = [int(((slim_page == p) & (slim_ts >= x - 3600) & (slim_ts < x)).sum()) for p, x in zip(page, ts)]
    assert fast.tolist() == slow


# --------------------------------------------------------------------------
# One full run on fixture files
# --------------------------------------------------------------------------
def test_full_run(tmp_path):
    cohort = [
        cohort_row(revision_id="999", revision_parent_id="0", revision_text_sha1="abc123",
                   revision_text_bytes="500", revision_text_bytes_diff="500",
                   event_timestamp="2026-09-09 11:00:00.0"),                        # page creation
        cohort_row(revision_id="1000", revision_parent_id="999", revision_text_sha1="abc124",
                   page_title_historical="Moved_by_a_vandal",                     # title at edit time
                   revision_tags="mobile edit,mw-reverted,visualeditor",
                   revision_is_identity_reverted="true", revision_seconds_to_identity_revert="600",
                   revision_first_identity_reverting_revision_id="5001"),
        cohort_row(revision_id="1001", revision_parent_id="1000", revision_text_sha1="abc124",
                   revision_text_bytes_diff="0", event_comment="Alice moved page [[A]] to [[B]]",
                   event_timestamp="2026-09-09 12:30:00.0"),                        # null revision (a)
        cohort_row(revision_id="1002", revision_parent_id="1001", revision_text_sha1="abc125",
                   page_title_historical=None, page_title="Page_Now",
                   event_user_text_historical="~2026-1-1", event_user_id="301",
                   event_user_is_temporary="true", event_timestamp="2026-09-10 23:59:59.0"),
        cohort_row(revision_id="1003", event_timestamp="2026-09-12 00:00:00.0"),   # outside window
    ]
    slim = [
        slim_row(revision_id="999", event_timestamp="2026-09-09 11:00:00.0", event_user_id="100",
                 event_user_text_historical="Alice"),
        slim_row(revision_id="998", event_timestamp="2026-09-09 11:30:00.0"),
        slim_row(revision_id="1000", event_timestamp=TS, event_user_id="100", event_user_text_historical="Alice"),
        slim_row(revision_id="5001", event_timestamp="2026-09-09 12:10:00.0"),
        slim_row(revision_id="9", page_id="2", event_timestamp="2026-09-09 11:59:00.0"),
    ]
    cohort_path = write_strings(cohort, COLUMNS, tmp_path / "cohort.parquet")
    slim_path = write_strings(slim, config.HISTORY_SLIM_COLUMNS, tmp_path / "slim.parquet")
    out_dir = tmp_path / "tables"
    summary = ph.run(cohort_path, slim_path, out_dir, quiet=True)

    rev = pd.read_parquet(out_dir / ph.OUT_REVISIONS)
    links = pd.read_parquet(out_dir / ph.OUT_LINKS)
    assert list(rev.columns) == ph.REVISION_COLUMNS
    assert list(links.columns) == ph.LINK_COLUMNS
    assert sorted(rev["rev_id"].tolist()) == [999, 1000, 1002]
    assert summary["rows"]["dropped"]["null_revision_same_sha1"] == 1
    assert summary["rows"]["dropped"]["outside_window"] == 1
    assert not list(out_dir.glob("*.tmp"))
    success = json.loads((out_dir / ph.OUT_SUCCESS).read_text())
    assert success["rows"] == {ph.OUT_REVISIONS: 3, ph.OUT_LINKS: 1}

    r = rev.set_index("rev_id")
    assert str(r["ts"].dt.tz) == "UTC"
    assert r.loc[1000, "tags"].tolist() == ["mobile edit", "visualeditor"]
    assert r.loc[1000, "mw_reverted_tag"] and not r.loc[999, "mw_reverted_tag"]
    assert r.loc[1000, "sha1"] == sha1_base36_to_hex("abc124")
    assert len(r.loc[1000, "sha1"]) == 40
    assert r.loc[1000, "cohort"] == "history"
    assert r.loc[1000, "hour_utc"] == 12
    # Page 1 in [11:00, 12:00): rows at 11:00 and 11:30 (the page-2 row does not count).
    assert r.loc[1000, "page_edits_prev_1h"] == 2
    assert r.loc[999, "page_edits_prev_1h"] == 0
    # page_title = the current title; the title at edit time stays in page_title_historical.
    assert r.loc[1000, "page_title"] == "Page_One"
    assert r.loc[1000, "page_title_historical"] == "Moved_by_a_vandal"
    assert r.loc[1002, "page_title"] == "Page_Now" and pd.isna(r.loc[1002, "page_title_historical"])
    assert r.loc[1002, "user_kind"] == "temporary" and r.loc[1002, "is_anon"]
    last = pd.Timestamp(config.HISTORY_DUMP_LAST_REVISION)
    assert r.loc[1002, "followup_s"] == int((last - pd.Timestamp("2026-09-10 23:59:59", tz="UTC")).total_seconds())
    assert r.loc[1000, "reverted"] and r.loc[1000, "reverted_by_other"]
    assert r.loc[1000, "reverter_key"] == "u:200"
    assert pd.isna(r.loc[1000, "seen_ts"]) and pd.isna(r.loc[1000, "revert_risk"])

    link = links.iloc[0]
    assert link["reverted_rev_id"] == 1000 and link["reverting_rev_id"] == 5001
    assert link["reverting_ts"] == pd.Timestamp("2026-09-09 12:10:00", tz="UTC")
    assert link["T_s"] == 600 and link["within_followup"] and link["by_other"]
    assert link["is_exact"] and link["confirmed_by_tag"]
    assert link["cohort"] == "history" and link["source"] == "dump"
    assert pd.isna(link["known_at"]) and pd.isna(link["method"])
    assert pd.isna(link["range_size"]) and pd.isna(link["range_complete"])     # live only
    # The summary must not hold editor names.
    text = (out_dir / ph.OUT_SUMMARY).read_text()
    assert "Alice" not in text and "Bob" not in text
