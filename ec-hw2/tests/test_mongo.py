"""Tests for the MongoDB part: build_documents.py, load_mongo.py, speed_layer.py, run_mongo.py.

Run (from the repo root):
    .venv/bin/python -m pytest ec-hw2/tests/test_mongo.py -q

The fixtures are tiny made-up rows with the same columns and types as the real
cohort tables (the schemas come from ingest/label_live.py, plus the history label
columns). The database tests use the local MongoDB, database 'truthlag_test', which
is dropped at the end. They are skipped when MongoDB is not running.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bson
import pandas as pd
import pyarrow as pa
import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

HW2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW2))
import config  # noqa: E402
import load_mongo  # noqa: E402
import speed_layer  # noqa: E402
from ingest import build_documents as bd  # noqa: E402
from ingest.label_live import LINKS_SCHEMA, LIVE_REVISIONS_SCHEMA  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_mongo", HW2 / "queries" / "run_mongo.py")
run_mongo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_mongo)

TEST_DB = "truthlag_test"
T0 = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)      # inside the history window
L0 = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)    # inside the live window
TS = pa.timestamp("ns", tz="UTC")
HISTORY_SCHEMA = pa.schema(list(LIVE_REVISIONS_SCHEMA) + [
    ("reverted", pa.bool_()), ("reverted_any", pa.bool_()), ("secs_to_revert", pa.int64()),
    ("reverting_rev_id", pa.int64()), ("reverter_key", pa.string()),
    ("reverter_name", pa.string()), ("reverter_kind", pa.string()),
    ("reverted_by_other", pa.bool_()),
])

DOC_KEYS = {"_id", "wiki_db", "rev_id", "parent_id", "cohort", "page", "user", "ts", "hour_utc",
            "size", "size_delta", "comment", "tags", "mw_reverted_tag", "is_revert",
            "revert_method"}
USER_KEYS = {"id", "name", "kind", "key", "is_bot", "is_anon", "is_temp", "edit_count"}
HISTORY_KEYS = {"snapshot", "reverted", "reverted_any", "secs_to_revert", "reverting_rev_id",
                "reverter", "reverted_by_other", "followup_s", "page_edits_prev_1h"}
LIVE_KEYS = {"seen_ts", "revert_risk", "page_edits_prev_1h"}


# --------------------------------------------------------------------------
# Row factories (same columns and types as the real tables)
# --------------------------------------------------------------------------
def revision_row(cohort: str, rev_id: int, page_id: int, user_key: str | None = "u:1",
                 kind: str = "registered", ts: datetime | None = None, **over) -> dict:
    ts = ts or (T0 if cohort == config.COHORT_HISTORY else L0)
    uid = int(user_key[2:]) if user_key and user_key.startswith("u:") else None
    row = {
        "cohort": cohort, "wiki_db": "enwiki", "rev_id": rev_id, "parent_id": rev_id - 1,
        "page_id": page_id, "page_title": f"Page_{page_id}", "page_ns": 0, "ts": ts,
        "seen_ts": ts + timedelta(seconds=3) if cohort == config.COHORT_LIVE else None,
        "hour_utc": ts.hour, "size": 1000, "size_delta": 10, "comment": "x" * 200,
        "tags": ["visualeditor"], "mw_reverted_tag": False, "mw_reverted_at": None,
        "is_revert": False, "revert_method": None, "user_id": uid,
        "user_name": (user_key or "")[2:] or None, "user_kind": kind, "user_key": user_key,
        "is_bot": kind == "bot", "is_temp": kind == "temporary", "is_anon": kind == "temporary",
        "edit_count": 5, "sha1": "ab" * 20,
        "revert_risk": 0.5 if cohort == config.COHORT_LIVE else None,
        "page_edits_prev_1h": 0, "followup_s": 2_000_000,
    }
    if cohort == config.COHORT_HISTORY:
        row.update({"reverted": False, "reverted_any": False, "secs_to_revert": None,
                    "reverting_rev_id": None, "reverter_key": None, "reverter_name": None,
                    "reverter_kind": None, "reverted_by_other": False})
    row.update(over)
    return row


def link_row(cohort: str, reverted_rev_id: int, page_id: int, author: str, reverter: str,
             reverting_rev_id: int, T_s: int = 100, within: bool = True, **over) -> dict:
    hist = cohort == config.COHORT_HISTORY
    t = T0 if hist else L0
    row = {
        "cohort": cohort, "source": "dump" if hist else "stream",
        "reverted_rev_id": reverted_rev_id, "page_id": page_id, "reverted_ts": t,
        "author_key": author, "author_kind": "registered", "reverting_rev_id": reverting_rev_id,
        "reverting_ts": t + timedelta(seconds=T_s), "reverter_key": reverter,
        "reverter_name": (reverter or "")[2:] or None, "reverter_kind": "registered",
        "T_s": T_s, "known_at": None if hist else t + timedelta(seconds=T_s + 3),
        "K_s": None if hist else 3.0, "method": None if hist else "undo", "is_exact": True,
        "by_other": author is not None and reverter is not None and author != reverter,
        "within_followup": within, "range_size": None if hist else 1, "confirmed_by_tag": True,
    }
    row.update(over)
    return row


def as_rows(rows: list[dict], schema: pa.Schema) -> list[dict]:
    """Round-trip through Arrow with the real schema, as load_mongo.py reads Parquet."""
    return bd.rows_from_table(pa.Table.from_pylist(rows, schema=schema))


def rev_docs(rows: list[dict]) -> list[dict]:
    hist = [r for r in rows if r["cohort"] == config.COHORT_HISTORY]
    live = [r for r in rows if r["cohort"] == config.COHORT_LIVE]
    out = [bd.revision_document(r) for r in as_rows(hist, HISTORY_SCHEMA)] if hist else []
    out += [bd.revision_document(r) for r in as_rows(live, LIVE_REVISIONS_SCHEMA)] if live else []
    return out


def link_docs(rows: list[dict]) -> list[dict]:
    return [bd.revert_link_document(r) for r in as_rows(rows, LINKS_SCHEMA)]


# --------------------------------------------------------------------------
# Document builder (no database)
# --------------------------------------------------------------------------
def test_history_document_shape():
    d = rev_docs([revision_row("history", 101, 7, reverted=True, reverted_any=True,
                               secs_to_revert=60, reverting_rev_id=105, reverter_key="u:2",
                               reverter_name="Two", reverter_kind="registered",
                               reverted_by_other=True)])[0]
    assert set(d) == DOC_KEYS | {"history"}
    assert d["_id"] == "enwiki:101" and d["cohort"] == "history"
    assert set(d["user"]) == USER_KEYS and set(d["page"]) == {"id", "title", "ns"}
    assert set(d["history"]) == HISTORY_KEYS
    assert d["history"]["snapshot"] == config.HISTORY_SNAPSHOT
    assert d["history"]["reverter"] == {"key": "u:2", "name": "Two", "kind": "registered"}
    assert len(d["comment"]) == bd.COMMENT_MAX == 120
    assert d["ts"].tzinfo is not None and d["ts"].utcoffset() == timedelta(0)
    assert d["ts"] == T0 and isinstance(d["rev_id"], int) and d["tags"] == ["visualeditor"]


def test_live_document_shape_and_lean():
    d = rev_docs([revision_row("live", 201, 8, comment="short")])[0]
    assert set(d) == DOC_KEYS | {"live"} and "history" not in d
    assert set(d["live"]) == LIVE_KEYS
    assert d["live"]["seen_ts"] == L0 + timedelta(seconds=3)
    assert d["comment"] == "short"
    row = as_rows([revision_row("history", 102, 7)], HISTORY_SCHEMA)[0]
    lean = bd.revision_document(row, lean=True)
    assert "comment" not in lean and lean["history"]["reverter"] is None


def test_revert_link_document():
    d = link_docs([link_row("history", 101, 7, "u:1", "u:2", 105)])[0]
    assert d["_id"] == "history:101"
    assert set(d) == {"_id"} | set(bd.LINK_COLUMNS)
    assert d["K_s"] is None and d["known_at"] is None and d["by_other"] is True
    d = link_docs([link_row("live", 201, 8, "u:1", "u:1", 205)])[0]
    assert d["_id"] == "live:201" and d["by_other"] is False and d["K_s"] == 3.0


def test_empty_comment_is_null_in_both_cohorts():
    docs = rev_docs([revision_row("history", 104, 7, comment=None),
                     revision_row("live", 204, 8, comment="")])
    assert [d["comment"] for d in docs] == [None, None]


def test_pseudonyms(monkeypatch):
    monkeypatch.setattr(config, "ALIAS_SECRET", "test-secret")
    n = bd.alias_length(["u:1", "u:2", "t:~2026-1"])
    assert n == config.ALIAS_HEX == 10          # fixed length, not data-dependent
    a = bd.editor_alias("u:1", n)
    want = hmac.new(b"test-secret", b"u:1", hashlib.sha256).hexdigest()[:config.ALIAS_HEX]
    assert a == "editor_" + want
    assert a == bd.editor_alias("u:1", 4) == bd.editor_alias("u:1")    # n_hex is ignored
    assert a != bd.editor_alias("u:2", n)
    assert a != "editor_" + hashlib.sha1(b"u:1").hexdigest()[:10]     # not the old unsalted rule
    monkeypatch.setattr(config, "ALIAS_SECRET", "another-secret")
    assert bd.editor_alias("u:1") != a                                 # the secret matters
    monkeypatch.setattr(config, "ALIAS_SECRET", "test-secret")
    assert bd.public_name("bot", "u:9", "ClueBot NG", n) == "ClueBot NG"
    assert bd.public_name("registered", "u:9", "Alice", n) == bd.editor_alias("u:9", n)
    d = rev_docs([revision_row("history", 103, 7, user_key="u:42", reverted=True,
                               reverter_key="u:13286072", reverter_name="ClueBot NG",
                               reverter_kind="bot")])[0]
    p = bd.pseudonymize_revision(d, n)
    assert p["user"]["name"].startswith("editor_") and p["user"]["id"] is None
    assert p["user"]["key"].startswith("editor_") and "42" not in p["user"]["name"]
    assert p["history"]["reverter"]["name"] == "ClueBot NG"
    assert d["user"]["name"] == "42"          # the original is not changed


def test_alias_errors(monkeypatch):
    monkeypatch.setattr(config, "ALIAS_SECRET", "")
    with pytest.raises(bd.AliasError, match="ALIAS_SECRET is empty"):
        bd.editor_alias("u:1")
    with pytest.raises(bd.AliasError):
        bd.alias_length(["u:1"])
    # With 1 hex digit there are only 16 aliases, so 40 keys must collide.
    monkeypatch.setattr(config, "ALIAS_SECRET", "test-secret")
    monkeypatch.setattr(config, "ALIAS_HEX", 1)
    with pytest.raises(bd.AliasError, match="share one alias"):
        bd.alias_length([f"u:{i}" for i in range(40)])


def test_atlas_link_pseudonyms(monkeypatch):
    monkeypatch.setattr(config, "ALIAS_SECRET", "test-secret")
    d = link_docs([link_row("history", 101, 7, "u:1", "u:2", 105),
                   link_row("history", 102, 7, "u:3", "u:9", 106, reverter_name="ClueBot NG",
                            reverter_kind="bot")])
    human, bot = (load_mongo._pseudonymize_link(x, 10) for x in d)
    assert human["author_key"] == bd.editor_alias("u:1") and human["reverter_key"] == bd.editor_alias("u:2")
    assert human["reverter_name"] == bd.editor_alias("u:2")
    assert bot["reverter_key"] == "u:9" and bot["reverter_name"] == "ClueBot NG"
    assert bot["author_key"] == bd.editor_alias("u:3")


def test_atlas_refuses_without_confirm():
    # Stops before it reads a file or connects to a database.
    with pytest.raises(SystemExit, match="--confirm-overwrite"):
        load_mongo.main(["--target", "atlas"])


def test_results_show_only_aliases(monkeypatch):
    monkeypatch.setattr(config, "ALIAS_SECRET", "test-secret")
    info = {"u:1": ("registered", "Alice"), "u:9": ("bot", "ClueBot NG")}
    alias = bd.editor_alias("u:1")
    assert run_mongo.public_editor("u:1", info, 10) == alias
    assert run_mongo.public_editor(alias, info, 10) == alias          # Atlas key: not aliased again
    assert run_mongo.public_editor("u:9", info, 10) == "ClueBot NG"
    good = {"pairs": pd.DataFrame({"page_id": [1], "page_title": ["User:Someone_page"],
                                   "editor_a": [alias], "editor_b": ["ClueBot NG"]})}
    assert run_mongo.check_no_editor_identity(good, bots={"ClueBot NG"})["ok"]
    for bad in (pd.DataFrame({"editor_a": ["Alice"]}), pd.DataFrame({"kind": ["u:12345"]}),
                pd.DataFrame({"x": ["t:~2026-10001-01"]})):
        assert not run_mongo.check_no_editor_identity({"t": bad}, bots={"ClueBot NG"})["ok"]


def test_mutual_check_without_order():
    a = pd.DataFrame({"page_id": [1], "a": ["editor_b"], "b": ["editor_a"],
                      "a_reverted_b": [2], "b_reverted_a": [1]})
    b = pd.DataFrame({"page_id": [1], "a": ["editor_a"], "b": ["editor_b"],
                      "a_reverted_b": [1], "b_reverted_a": [2]})
    assert run_mongo._unordered_pairs(a) == run_mongo._unordered_pairs(b)
    b.loc[0, "a_reverted_b"] = 2          # the counts must follow their editor
    assert run_mongo._unordered_pairs(a) != run_mongo._unordered_pairs(b)


def test_atlas_size_estimate():
    docs = [{"_id": f"enwiki:{i}", "page": {"id": i}, "x": "y" * 100} for i in range(1000)]
    est = load_mongo.estimate_collection(docs, 1000, [[("page.id", 1)]], every=10)
    assert est["sampled"] == 100
    sampled = [len(bson.encode(d)) for d in docs[::10]]
    assert est["avg_bson_bytes"] == round(sum(sampled) / len(sampled), 1)
    assert est["data_mb"] == round(sum(sampled) / len(sampled) * 1000 / 1024 / 1024, 2)
    assert est["index_mb"] > 0


def test_wilson_interval():
    lo, hi = run_mongo.wilson(5, 10)
    assert round(lo, 4) == 0.2366 and round(hi, 4) == 0.7634
    lo, hi = run_mongo.wilson(0, 10)
    assert lo == 0.0 and round(hi, 4) == 0.2775
    assert run_mongo.wilson(0, 0) == (None, None)


def test_query_files_are_valid(tmp_path):
    paths = run_mongo.write_query_files(tmp_path)
    assert set(paths) == set(run_mongo.QUERY_FILES) == set(run_mongo.QUERIES) | {"q5_risk_deciles"}
    dec = run_mongo.load_query(paths["q5_risk_deciles"])
    assert dec["pipeline"] == run_mongo.risk_deciles_pipeline()
    assert "$bucketAuto" in str(dec["pipeline"]) and "$unionWith" in str(dec["pipeline"])
    assert "page creations" in dec["description"] and "Wilson" in dec["description"]
    for p in paths.values():
        spec = run_mongo.load_query(p)           # asserts the keys and the first $match on cohort
        assert spec["description"] and "Aggregations" in spec["description"]


# --------------------------------------------------------------------------
# Database tests (local MongoDB, database truthlag_test)
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def db():
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=2000, tz_aware=True)
        client.admin.command("ping")
    except PyMongoError:
        pytest.skip("local MongoDB is not running")
    client.drop_database(TEST_DB)
    yield client[TEST_DB]
    client.drop_database(TEST_DB)


def _reset(db, revisions=(), links=()):
    for c in (config.COL_REVISIONS, config.COL_REVERT_LINKS, config.COL_PAGE_HOUR):
        db[c].drop()
    if revisions:
        db[config.COL_REVISIONS].insert_many(list(revisions))
    if links:
        db[config.COL_REVERT_LINKS].insert_many(list(links))
    load_mongo.create_indexes(db)


def _run(db, builder):
    spec = builder()
    return list(db[spec["collection"]].aggregate(spec["pipeline"]))


def _page(page_id: int, n_human: int, n_bot: int = 0, start: int = 0) -> list[dict]:
    """n_human edits by u:1..u:n_human and n_bot edits by a bot on one page."""
    rows = [revision_row("history", page_id * 1000 + i, page_id, user_key=f"u:{i + 1}",
                         ts=T0 + timedelta(minutes=i)) for i in range(n_human)]
    rows += [revision_row("history", page_id * 1000 + 500 + i, page_id, user_key="u:999",
                          kind="bot", ts=T0 + timedelta(minutes=i)) for i in range(n_bot)]
    return rows


def _actions(page_id: int, n: int, editors: int = 2, first_rev: int = 0) -> list[dict]:
    """n revert actions by u:900 on the page, spread over `editors` reverted authors."""
    return [link_row("history", page_id * 1000 + i, page_id, f"u:{(i % editors) + 1}", "u:900",
                     page_id * 10_000 + i) for i in range(n)]


def test_q2_tie_order(db):
    revs, links = [], []
    for page, edits, acts in [(1, 10, 5), (2, 20, 10), (3, 10, 5), (4, 12, 6)]:
        revs += _page(page, edits)          # all score 0.5
        links += _actions(page, acts)
    revs += _page(6, 9, n_bot=5)            # 9 human edits: too few (bots do not count)
    links += _actions(6, 8)
    revs += _page(7, 10)                    # only one reverted editor
    links += _actions(7, 4, editors=1)
    revs += _page(8, 10)                    # self-reverts and late reverts do not count
    links += [link_row("history", 8000 + i, 8, "u:1", "u:1", 80_000 + i) for i in range(3)]
    links += [link_row("history", 8003 + i, 8, f"u:{i + 2}", "u:900", 80_010 + i,
                       T_s=config.HISTORY_FOLLOWUP_S + 1, within=False) for i in range(3)]
    revs += _page(9, 10)                    # one revert action that covers two editors
    links += [link_row("history", 9000 + i, 9, f"u:{i + 1}", "u:900", 90_000) for i in range(2)]
    _reset(db, rev_docs(revs), link_docs(links))
    out = _run(db, run_mongo.q2_top_contested_pages)
    assert [r["page_id"] for r in out] == [2, 4, 1, 3, 9]
    assert all(isinstance(r["score"], float) for r in out)
    by = {r["page_id"]: r for r in out}
    assert by[2]["revert_actions"] == 10 and by[2]["edits"] == 20 and by[2]["contested"] is True
    assert by[9]["revert_actions"] == 1 and by[9]["reverted_editors"] == 2
    assert by[9]["contested"] is False and by[9]["page_title"] == "Page_9"


def test_q3_bucket_edges(db):
    t_values = [0, 59, 60, 299, 300, 86_399, 86_400, 1_727_999, 1_728_000]
    links = [link_row("history", 100 + i, 1, "u:1", "u:2", 500 + i, T_s=t)
             for i, t in enumerate(t_values)]
    links.append(link_row("history", 200, 1, "u:1", "u:2", 600, T_s=1_800_000, within=False))
    links.append(link_row("live", 300, 2, "u:1", "u:2", 700, T_s=59))
    _reset(db, links=link_docs(links))
    out = _run(db, run_mongo.q3_time_to_revert)
    got = {(r["cohort"], r["bucket"]): r["n"] for r in out}
    common = {("history_4d", b): n for (c, b), n in got.items() if c == "history" and
              b in ("<1 min", "1-5 min", "5-15 min", "6-24 h", "1-2 d")}
    assert got == {("history", "<1 min"): 2, ("history", "1-5 min"): 2, ("history", "5-15 min"): 1,
                   ("history", "6-24 h"): 1, ("history", "1-2 d"): 1, ("history", "14-20 d"): 2,
                   ("live", "<1 min"): 1, **common}
    assert sum(common.values()) == 7             # history_4d: T <= 4 days only
    assert not any(r["bucket"] == config.LAG_DEFAULT_BUCKET for r in out)
    for series in ("history", "history_4d"):     # shares are computed within each series
        rows = [r for r in out if r["cohort"] == series]
        assert abs(sum(r["share"] for r in rows) - 1) < 1e-12 and rows[-1]["cum_share"] == 1.0
    assert set(out[0]) == {"cohort", "bucket", "bucket_lower_s", "bucket_order", "bucket_sorted",
                           "bucket_upper_s", "n", "share", "cum_share"}    # the frozen chart fields
    # A time past the last edge must land in the default bucket, so the assert can catch it.
    db[config.COL_REVERT_LINKS].insert_one(link_docs(
        [link_row("history", 201, 1, "u:1", "u:2", 601, T_s=1_728_001)])[0])
    assert run_mongo.default_bucket_empty(pd.DataFrame(out))
    out = _run(db, run_mongo.q3_time_to_revert)
    df = pd.DataFrame(out)
    assert (df["bucket"] == config.LAG_DEFAULT_BUCKET).sum() == 1
    assert not run_mongo.default_bucket_empty(df)


def test_mutual_revert_pairing(db):
    L_ = []
    # page 1: u:1 reverted u:2 twice (2 actions), u:2 reverted u:1 once -> one mutual row.
    L_ += [link_row("history", 11, 1, "u:2", "u:1", 101), link_row("history", 12, 1, "u:2", "u:1", 102),
           link_row("history", 13, 1, "u:1", "u:2", 103)]
    # one action that reverted two revisions counts once
    L_ += [link_row("history", 14, 1, "u:2", "u:1", 104), link_row("history", 15, 1, "u:2", "u:1", 104)]
    # page 2: one direction only -> no row
    L_ += [link_row("history", 21, 2, "u:4", "u:3", 201)]
    # pages 3 and 4: the two directions on different pages -> no row
    L_ += [link_row("history", 31, 3, "u:6", "u:5", 301), link_row("history", 41, 4, "u:5", "u:6", 401)]
    # page 5: keys where the reverter of the first link sorts after the author ("u:9" > "u:3")
    L_ += [link_row("history", 51, 5, "u:3", "u:9", 501), link_row("history", 52, 5, "u:9", "u:3", 502),
           link_row("history", 53, 5, "u:9", "u:3", 503)]
    # page 6: the reverse only outside the follow-up, and a self-revert -> no row
    L_ += [link_row("history", 61, 6, "u:8", "u:7", 601),
           link_row("history", 62, 6, "u:7", "u:8", 602, T_s=config.HISTORY_FOLLOWUP_S + 5,
                    within=False),
           link_row("history", 63, 6, "u:7", "u:7", 603)]
    # a live link is ignored (history cohort only)
    L_ += [link_row("live", 71, 1, "u:1", "u:2", 701)]
    _reset(db, links=link_docs(L_))
    out = _run(db, run_mongo.compare_mutual_reverts)
    assert out == [
        {"page_id": 1, "a": "u:1", "b": "u:2", "a_reverted_b": 3, "b_reverted_a": 1},
        {"page_id": 5, "a": "u:3", "b": "u:9", "a_reverted_b": 2, "b_reverted_a": 1},
    ]


def test_q5_known_by(db, monkeypatch):
    revs = [revision_row("live", 1000 + i, 1, user_key=f"u:{i + 1}") for i in range(3)]
    links = [link_row("live", 1000, 1, "u:1", "u:9", 2000, T_s=50, K_s=20.0),     # known at 70 s
             link_row("live", 1001, 1, "u:2", "u:9", 2001, T_s=400_000)]           # later than 4 d
    _reset(db, rev_docs(revs), link_docs(links))
    monkeypatch.setattr(config, "RISK_MIN_GROUP_N", 1)     # the fixture is tiny
    out = _run(db, run_mongo.q5_truth_lag_preview)[0]["known_by"]
    row = {r["wait"]: r for r in out if r["user_kind"] == "all"}
    assert row["1 min"]["n_reverted_4d"] == 1 and row["1 min"]["n_edits"] == 3
    assert row["1 min"]["known"] == 0 and row["5 min"]["known"] == 1
    assert row["4 d"]["share_known"] == 1.0


def test_risk_deciles_no_score_group(db, monkeypatch):
    revs = [revision_row("live", 3000 + i, 1, user_key=f"u:{i + 1}", revert_risk=0.1 * (i + 1))
            for i in range(3)]
    revs += [revision_row("live", 3100, 2, revert_risk=None, parent_id=0),       # page creation
             revision_row("live", 3101, 2, revert_risk=None, parent_id=3100)]    # score not captured
    links = [link_row("live", 3101, 2, "u:1", "u:9", 3200, T_s=60)]
    _reset(db, rev_docs(revs), link_docs(links))
    monkeypatch.setattr(config, "RISK_MIN_GROUP_N", 1)
    rows = run_mongo.decile_rows(list(db[config.COL_REVISIONS].aggregate(run_mongo.risk_deciles_pipeline())))
    no = [r for r in rows if r["group"] == "no score"][0]
    assert (no["n"], no["n_page_creations"], no["n_other_edits"], no["n_reverted_4d"]) == (2, 1, 1, 1)
    assert sum(r["n"] for r in rows if r["decile"]) == 3
    assert all(r["n_page_creations"] == 0 for r in rows if r["decile"])


def test_revert_link_indexes(db):
    _reset(db)
    names = set(db[config.COL_REVERT_LINKS].index_information())
    assert {"reverted_rev_id_1", "page_id_1", "cohort_1_page_id_1"} <= names


def test_speed_layer_batch_is_repeatable(db):
    times = lambda *hm: pd.to_datetime([f"2026-10-20T{x}:00Z" for x in hm], utc=True)  # noqa: E731
    pc = pd.DataFrame({
        "meta_id": ["a", "b", "c", "d", "e"],
        "meta_dt": times("10:05", "10:50", "11:10", "10:10", "10:20"),
        "kind": ["edit", "edit", "create", "edit", "delete"],
        "ns": [0, 0, 0, 1, 0],
        "page_id": [1, 1, 1, 2, 1],
        "page_title": ["P1", "P1", "P1", "Talk", "P1"],
        "revert_method": [None, "undo", None, None, None],
    })
    links_all = pd.DataFrame({
        "page_id": [1, 1, 2], "page_ns": [0, 0, 1],
        "known_at": times("10:50", "10:50", "10:50"),
        "reverting_rev_id": [9, 9, 8], "reverted_rev_id": [5, 6, 7],
    })
    first = speed_layer.run_batch(db, pc, links_all)
    docs1 = {d["_id"]: d for d in db[config.COL_PAGE_HOUR].find({}, {"built_at": 0})}
    second = speed_layer.run_batch(db, pc, links_all)
    docs2 = {d["_id"]: d for d in db[config.COL_PAGE_HOUR].find({}, {"built_at": 0})}
    assert docs1 == docs2
    assert first["edits_seen"] == second["edits_seen"] == 3
    assert docs1["1:2026-10-20T10"]["edits_seen"] == 2
    assert docs1["1:2026-10-20T10"]["revert_events_seen"] == 1
    assert docs1["1:2026-10-20T10"]["reverted_revs_seen"] == 2
    assert docs1["1:2026-10-20T11"]["edits_seen"] == 1
    assert set(docs1) == {"1:2026-10-20T10", "1:2026-10-20T11"}
    assert speed_layer.STAGE_EVENTS not in db.list_collection_names()


def test_follow_update_counts_each_meta_id_once():
    ev = {"meta": {"id": "m1", "dt": "2026-10-20T10:15:00Z"}, "page_change_kind": "edit",
          "page": {"page_id": 5, "namespace_id": 0}, "revision": {"revert": {"method": "undo"}}}
    seen: set = set()
    op = speed_layer.follow_update(ev, seen)
    assert op is not None and op._filter == {"_id": "5:2026-10-20T10"}
    assert op._doc["$inc"] == {"edits_seen": 1, "revert_events_seen": 1}
    assert speed_layer.follow_update(ev, seen) is None
    talk = {**ev, "meta": {"id": "m2", "dt": "2026-10-20T10:15:00Z"},
            "page": {"page_id": 6, "namespace_id": 1}}
    assert speed_layer.follow_update(talk, seen) is None


def test_exact_median_stages(db):
    db["median_probe"].drop()
    db["median_probe"].insert_many([{"g": "even", "T": t} for t in [10, 1, 3, 2]]
                                   + [{"g": "odd", "T": t} for t in [5, 1, 3]]
                                   + [{"g": "odd", "T": None}, {"g": "none", "T": None}])
    out = db["median_probe"].aggregate(
        [{"$group": {"_id": "$g", "T_list": {"$push": "$T"}}}]
        + run_mongo._exact_median("T_list", "median") + [{"$sort": {"_id": 1}}])
    got = {d["_id"]: d["median"] for d in out}
    assert got == {"even": 2.5, "odd": 3, "none": None}
    assert got["even"] == pd.Series([10, 1, 3, 2]).median()
