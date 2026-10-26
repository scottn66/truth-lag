"""Tests for the SQL part: load_sql.py, queries/sql/*.sql, queries/run_sql.py and comparison/compare.py.

Run (from the repo root):
    .venv/bin/python -m pytest ec-hw2/tests/test_sql.py -q

The fixtures are tiny made-up rows with the same columns and types as
data/tables/history_revisions.parquet and history_revert_links.parquet. load_sql.fill()
puts them into an in-memory SQLite database, and the tests run the REAL query files
from queries/sql/ on it. No database server is needed. They check:
- the types that load_sql.py writes (ISO times, comma lists, 1/0, NULL);
- score ties and the order (score, revert_actions, edits, page_id), float division,
  the filters (bots, self-reverts, late reverts) and the top-20 limit;
- mutual pairing (a < b, the same page, the counts in both directions), also on the
  pre-aggregated input of the extra row;
- that the top-contested query counts edits only for the kept pages (query plan on the
  real file, read-only; skipped without the file);
- the helpers of compare.py (query size, equality, alias mapping, timing rounds, the
  speed rule, pain.csv, the --final load check, MongoDB plans).
"""
from __future__ import annotations

import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

HW2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW2))
import config  # noqa: E402
import load_sql  # noqa: E402
from comparison import compare  # noqa: E402
from ingest.history_columns import split_list  # noqa: E402
from ingest.label_live import LINK_FIELDS, LIVE_REVISIONS_SCHEMA  # noqa: E402
from ingest.parse_history import LINK_COLUMNS, REVISION_COLUMNS  # noqa: E402
from queries import run_sql  # noqa: E402

SQL_DIR = HW2 / "queries" / "sql"
T0 = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)      # inside the history window

# The schemas of the real history files: the live revision columns + the history labels,
# and the link columns (K_s is a whole number in the history file). The column ORDER comes
# from parse_history.py. page_title_historical (the title at edit time, next to the display
# title page_title) is the one history-only column the fixture may meet besides the labels.
HISTORY_LABELS = [
    ("reverted", pa.bool_()), ("reverted_any", pa.bool_()), ("secs_to_revert", pa.int64()),
    ("reverting_rev_id", pa.int64()), ("reverter_key", pa.string()),
    ("reverter_name", pa.string()), ("reverter_kind", pa.string()),
    ("reverted_by_other", pa.bool_()),
]
HISTORY_ONLY_EXTRA = {"page_title_historical": pa.string()}
_REV_TYPES = {f.name: f.type for f in LIVE_REVISIONS_SCHEMA} | dict(HISTORY_LABELS)
REVISIONS_SCHEMA = pa.schema([(n, _REV_TYPES.get(n, HISTORY_ONLY_EXTRA.get(n, pa.null())))
                              for n in REVISION_COLUMNS])
_LINK_TYPES = dict(LINK_FIELDS)
LINKS_SCHEMA = pa.schema([(n, pa.int64() if n == "K_s" else _LINK_TYPES.get(n, pa.null()))
                          for n in LINK_COLUMNS])


# --------------------------------------------------------------------------
# Row factories (same columns and types as the real tables)
# --------------------------------------------------------------------------
def rev(rev_id: int, page_id: int, user_key: str | None = "u:1", is_bot: bool = False,
        ts: datetime | None = None, title: str | None = None, tags=("visualeditor",)) -> dict:
    ts = ts or T0 + timedelta(seconds=rev_id)
    kind = "unknown" if user_key is None else ("bot" if is_bot else
                                               "temporary" if user_key.startswith("t:") else "registered")
    return {
        "cohort": config.COHORT_HISTORY, "wiki_db": "enwiki", "rev_id": rev_id, "parent_id": rev_id - 1,
        "page_id": page_id, "page_title": title or f"Page_{page_id}",
        "page_title_historical": title or f"Page_{page_id}", "page_ns": 0, "ts": ts,
        "seen_ts": None, "hour_utc": ts.hour, "size": 1000, "size_delta": 10, "comment": "c",
        "tags": list(tags), "mw_reverted_tag": False, "mw_reverted_at": None, "is_revert": False,
        "revert_method": None, "user_id": None if user_key is None else 1, "user_name": user_key,
        "user_kind": kind, "user_key": user_key, "is_bot": is_bot, "is_temp": kind == "temporary",
        "is_anon": kind == "temporary", "edit_count": 5, "sha1": "ab" * 20, "revert_risk": None,
        "page_edits_prev_1h": 0, "followup_s": 22 * 86400, "reverted": False, "reverted_any": False,
        "secs_to_revert": None, "reverting_rev_id": None, "reverter_key": None, "reverter_name": None,
        "reverter_kind": None, "reverted_by_other": False,
    }


def link(reverted_rev_id: int, page_id: int, author_key: str | None, reverter_key: str | None,
         reverting_rev_id: int, within: bool = True, by_other: bool | None = None) -> dict:
    if by_other is None:
        by_other = author_key is not None and reverter_key is not None and author_key != reverter_key
    t_s = 3600 if within else config.HISTORY_FOLLOWUP_S + 1
    reverted_ts = T0 + timedelta(seconds=reverted_rev_id)
    return {
        "cohort": config.COHORT_HISTORY, "source": "dump", "reverted_rev_id": reverted_rev_id,
        "page_id": page_id, "reverted_ts": reverted_ts, "author_key": author_key,
        "author_kind": "registered", "reverting_rev_id": reverting_rev_id,
        "reverting_ts": reverted_ts + timedelta(seconds=t_s), "reverter_key": reverter_key,
        "reverter_name": reverter_key, "reverter_kind": "registered", "T_s": t_s, "known_at": None,
        "K_s": None, "method": None, "is_exact": True, "by_other": by_other,
        "within_followup": within, "range_size": None, "confirmed_by_tag": False,
    }


def make_db(revs: list[dict], links: list[dict]) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    names = set(REVISIONS_SCHEMA.names)
    revs = [{k: v for k, v in r.items() if k in names} for r in revs]   # only the real columns
    load_sql.fill(con, pa.Table.from_pylist(revs, schema=REVISIONS_SCHEMA),
                  pa.Table.from_pylist(links, schema=LINKS_SCHEMA))
    return con


def run_file(con: sqlite3.Connection, name: str) -> list[dict]:
    q = run_sql.read_query(SQL_DIR / f"{name}.sql")      # the real query file
    cur = con.execute(q["text"])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def page(page_id: int, edits: int, actions: int, authors: int, bots: int = 0) -> tuple[list, list]:
    """A page with `edits` human revisions by `authors` editors; `actions` of them are reverted
    by u:900, each by its own reverting revision; plus `bots` bot revisions."""
    base = page_id * 1000
    revs = [rev(base + i, page_id, user_key=f"u:{i % authors + 1}") for i in range(edits)]
    revs += [rev(base + 500 + i, page_id, user_key="u:777", is_bot=True) for i in range(bots)]
    links = [link(base + i, page_id, f"u:{i % authors + 1}", "u:900", base + 900 + i)
             for i in range(actions)]
    return revs, links


def pages(*specs) -> tuple[list, list]:
    revs, links = [], []
    for spec in specs:
        r, lk = page(*spec)
        revs += r
        links += lk
    return revs, links


# --------------------------------------------------------------------------
# Fixture schema and load_sql.py
# --------------------------------------------------------------------------
def test_fixture_columns_follow_the_data_model():
    assert REVISIONS_SCHEMA.names == REVISION_COLUMNS
    assert LINKS_SCHEMA.names == LINK_COLUMNS
    # every column has a known type: the live revision columns, the history labels, and at
    # most the one planned history-only column; the link columns are those of label_live.py
    known = {f.name for f in LIVE_REVISIONS_SCHEMA} | {n for n, _ in HISTORY_LABELS}
    assert set(REVISION_COLUMNS) - known <= set(HISTORY_ONLY_EXTRA)
    assert set(f.name for f in LIVE_REVISIONS_SCHEMA) <= set(REVISION_COLUMNS)
    assert set(LINK_COLUMNS) <= {n for n, _ in LINK_FIELDS}


@pytest.mark.parametrize("name, schema", [("history_revisions.parquet", REVISIONS_SCHEMA),
                                          ("history_revert_links.parquet", LINKS_SCHEMA)])
def test_fixture_schema_matches_the_real_file(name, schema):
    path = config.TABLES_DIR / name
    if not path.exists():
        pytest.skip(f"{name} is not here (no data release)")
    real = pq.read_schema(path)
    assert [(f.name, f.type) for f in real] == [(f.name, f.type) for f in schema]


def test_load_types_times_lists_and_nulls():
    r = rev(5, 1, tags=("AWB", "a,b"))
    r["size"] = None
    con = make_db([r, rev(6, 1, tags=())], [link(5, 1, "u:1", "u:2", 9)])
    row = con.execute("SELECT ts, tags, is_bot, size, typeof(size), revert_risk, seen_ts "
                      "FROM revisions WHERE rev_id = 5").fetchone()
    assert row[0] == "2026-09-08T12:00:05+00:00"
    assert config.utc(row[0]) == T0 + timedelta(seconds=5)          # ISO text parses back to UTC
    assert row[1] == "AWB,a\\,b"
    assert split_list(row[1]) == ["AWB", "a,b"]                     # a comma inside an item survives
    assert row[2] == 0 and row[3] is None and row[4] == "null" and row[5] is None and row[6] is None
    assert con.execute("SELECT tags FROM revisions WHERE rev_id = 6").fetchone()[0] == ""
    lk = con.execute("SELECT by_other, within_followup, reverting_ts, known_at FROM revert_links").fetchone()
    assert lk == (1, 1, "2026-09-08T13:00:05+00:00", None)


def test_load_column_types_keys_and_indexes():
    con = make_db([rev(5, 1)], [link(5, 1, "u:1", "u:2", 9)])
    types = {r[1]: r[2] for r in con.execute("PRAGMA table_info(revisions)")}
    assert types["rev_id"] == "INTEGER" and types["ts"] == "TEXT" and types["tags"] == "TEXT"
    assert types["is_bot"] == "INTEGER" and types["revert_risk"] == "REAL"
    pk = [r[1] for r in con.execute("PRAGMA table_info(revisions)") if r[5]]
    assert pk == ["rev_id"]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
    assert {n for n, *_ in load_sql.INDEXES} <= names
    with pytest.raises(sqlite3.IntegrityError):     # one row per reverted revision
        con.execute("INSERT INTO revert_links (reverted_rev_id, page_id) VALUES (5, 1)")


def test_load_stops_on_a_missing_column():
    r = {k: v for k, v in rev(5, 1).items() if k in REVISIONS_SCHEMA.names}
    t = pa.Table.from_pylist([r], schema=REVISIONS_SCHEMA).drop_columns(["sha1"])
    with pytest.raises(SystemExit):
        load_sql.insert_table(sqlite3.connect(":memory:"), "revisions", t, REVISION_COLUMNS)


def test_iso_texts_rejects_a_non_utc_column():
    col = pa.chunked_array([pa.array([0], type=pa.timestamp("ns", tz="America/Los_Angeles"))])
    with pytest.raises(ValueError):
        load_sql.iso_texts(col)


# --------------------------------------------------------------------------
# compare_top_contested.sql
# --------------------------------------------------------------------------
def test_top_contested_score_ties_and_order():
    # pages 1-4 all have score 0.6; the order is then revert_actions desc, then page_id asc
    revs, links = pages((1, 10, 6, 3), (2, 15, 9, 3), (3, 10, 6, 3), (4, 20, 12, 3), (5, 10, 5, 2))
    out = run_file(make_db(revs, links), "compare_top_contested")
    assert [r["page_id"] for r in out] == [4, 2, 1, 3, 5]
    assert "rank" not in out[0]                                   # run_sql.py adds it in Python
    assert [r["score"] for r in out[:4]] == [0.6] * 4
    assert [r["revert_actions"] for r in out[:4]] == [12, 9, 6, 6]
    assert out[4]["score"] == 0.5


def test_top_contested_float_division_and_contested_flag():
    revs, links = pages((1, 10, 6, 2), (2, 10, 2, 2), (3, 10, 1, 1), (4, 30, 2, 2))
    con = make_db(revs, links)
    assert con.execute("SELECT 6 / 10").fetchone()[0] == 0        # why the file says 1.0 * a / b
    out = {r["page_id"]: r for r in run_file(con, "compare_top_contested")}
    assert isinstance(out[1]["score"], float) and out[1]["score"] == 0.6
    assert out[2]["score"] == 0.2 and out[2]["contested"] == 1     # score >= 0.2 and 2 actions
    assert 3 not in out                                            # 1 reverted editor: not kept
    assert out[4]["score"] == pytest.approx(2 / 30) and out[4]["contested"] == 0


def test_top_contested_filters_bots_self_and_late_reverts():
    revs, links = pages((1, 10, 4, 2, 5), (2, 9, 8, 4, 5))
    # one reverting revision that reverts 2 revisions counts once
    links[1]["reverting_rev_id"] = links[0]["reverting_rev_id"]
    # a self-revert and a revert after 20 days do not count
    links[2]["reverter_key"], links[2]["by_other"] = links[2]["author_key"], False
    links[3]["within_followup"] = False
    out = {r["page_id"]: r for r in run_file(make_db(revs, links), "compare_top_contested")}
    assert 2 not in out                       # 9 human edits (+ 5 bot edits): below 10
    assert out[1]["edits"] == 10              # the 5 bot edits are not counted
    assert out[1]["revert_actions"] == 1 and out[1]["reverted_editors"] == 2


def test_top_contested_keeps_20_rows():
    revs, links = pages(*[(p, 10 + p, 5, 2) for p in range(1, 26)])
    out = run_file(make_db(revs, links), "compare_top_contested")
    assert len(out) == config.TOP_N
    assert [r["page_id"] for r in out] == list(range(1, 21))     # 5/11 > 5/12 > ...


def test_top_contested_tie_at_the_cutoff():
    # pages 100 and 101 tie on score 0.5 for the last place: 101 has more revert actions,
    # so it must win although its page_id is larger (the tie order decides who is in the top 20)
    specs = [(p, 10, 9, 3) for p in range(1, config.TOP_N)] + [(100, 10, 5, 2), (101, 20, 10, 2)]
    out = run_file(make_db(*pages(*specs)), "compare_top_contested")
    assert [r["page_id"] for r in out] == list(range(1, config.TOP_N)) + [101]


def test_top_contested_columns_equal_mongo_q2_and_rank_in_python():
    revs, links = pages((1, 10, 6, 3), (2, 10, 3, 2))
    out = run_file(make_db(revs, links), "compare_top_contested")
    assert list(out[0]) == ["page_id", "page_title", "edits", "revert_actions", "reverted_editors",
                            "score", "contested"]
    tidy = run_sql.tidy_top(pd.DataFrame(out))
    assert list(tidy["rank"]) == [1, 2] and list(tidy["page_id"]) == [1, 2]
    assert tidy["contested"].dtype == bool


def test_top_contested_counts_edits_only_for_kept_pages():
    """The real query plan (read-only file): revisions are only searched by page_id, never scanned."""
    if not config.SQLITE_PATH.exists():
        pytest.skip("truthlag.sqlite is not here (no data release)")
    con = run_sql.connect_ro()
    try:
        sql = run_sql.read_query(SQL_DIR / "compare_top_contested.sql")["text"]
        plan = [r[3] for r in con.execute("EXPLAIN QUERY PLAN " + sql)]
    finally:
        con.close()
    on_revisions = [p for p in plan if re.match(r"(SCAN|SEARCH) r\b", p)]
    assert on_revisions and all(p.startswith("SEARCH r USING INDEX idx_revisions_page_id") for p in on_revisions), plan


def test_unknown_editor_revisions_count_as_human_edits():
    revs, links = pages((1, 9, 4, 2))
    revs.append(rev(1999, 1, user_key=None))                       # the dump hid the name
    out = run_file(make_db(revs, links), "compare_top_contested")
    assert out[0]["edits"] == 10                                   # the same rule as Mongo Q2


# --------------------------------------------------------------------------
# compare_mutual_reverts.sql
# --------------------------------------------------------------------------
def test_mutual_pairs():
    revs = [rev(i, 1) for i in range(1, 3)]
    links = [
        # page 10: u:2 reverts u:1 twice, u:1 reverts u:2 once -> one row with both counts
        link(101, 10, "u:1", "u:2", 9001), link(102, 10, "u:1", "u:2", 9002),
        link(103, 10, "u:2", "u:1", 9003),
        link(104, 10, "u:1", "u:1", 9004),                         # a self-revert: ignored
        # page 20: one direction only -> no row
        link(201, 20, "u:3", "u:4", 9101),
        # pages 30 and 31: each direction on a different page -> no row
        link(301, 30, "u:5", "u:6", 9201), link(311, 31, "u:6", "u:5", 9202),
        # page 40: a temporary account and a registered editor ('t:' < 'u:')
        link(401, 40, "t:~2026-11111-11", "u:7", 9301), link(402, 40, "u:7", "t:~2026-11111-11", 9302),
        # page 50: the reverse revert is after 20 days -> no row
        link(501, 50, "u:8", "u:9", 9401), link(502, 50, "u:9", "u:8", 9402, within=False),
        # page 60: the reverter is unknown -> no row
        link(601, 60, "u:10", None, 9501, by_other=True), link(602, 60, None, "u:10", 9502, by_other=True),
        # page 5: a second pair, listed before page 10
        link(51, 5, "u:12", "u:11", 9601), link(52, 5, "u:11", "u:12", 9602),
    ]
    out = run_file(make_db(revs, links), "compare_mutual_reverts")
    assert [(r["page_id"], r["a"], r["b"], r["a_reverted_b"], r["b_reverted_a"]) for r in out] == [
        (5, "u:11", "u:12", 1, 1),
        (10, "u:1", "u:2", 1, 2),
        (40, "t:~2026-11111-11", "u:7", 1, 1),
    ]


def test_preaggregated_variant_gives_the_same_rows():
    links = [link(101, 10, "u:1", "u:2", 9001), link(102, 10, "u:1", "u:2", 9002),
             link(103, 10, "u:2", "u:1", 9003), link(104, 10, "u:1", "u:1", 9004),
             link(201, 20, "u:3", "u:4", 9101), link(51, 5, "u:12", "u:11", 9601),
             link(52, 5, "u:11", "u:12", 9602), link(53, 5, "u:11", "u:12", 9602)]
    con = make_db([rev(1, 10)], links)
    raw = run_file(con, "compare_mutual_reverts")
    q = compare.load_extra_query()
    assert [s.split()[0].upper() for s in q["setup"]] == ["PRAGMA", "DROP", "CREATE", "INSERT"]
    for st in q["setup"]:
        con.execute(st)
    cur = con.execute(q["sql"])
    cols = [d[0] for d in cur.description]
    pre = [dict(zip(cols, r)) for r in cur.fetchall()]
    assert pre == raw and len(raw) == 2
    assert con.execute("SELECT name FROM sqlite_master WHERE name = 'revert_triples'").fetchone() is None
    assert con.execute("SELECT name FROM sqlite_temp_master WHERE name = 'revert_triples'").fetchone()


def test_mutual_counts_distinct_revert_actions():
    links = [link(101, 10, "u:1", "u:2", 9001), link(102, 10, "u:1", "u:2", 9001),   # one revert, 2 revisions
             link(103, 10, "u:2", "u:1", 9003)]
    out = run_file(make_db([rev(1, 10)], links), "compare_mutual_reverts")
    assert [(r["a_reverted_b"], r["b_reverted_a"]) for r in out] == [(1, 1)]


# --------------------------------------------------------------------------
# run_sql.py helpers
# --------------------------------------------------------------------------
def test_params_block_equals_config():
    text = (SQL_DIR / "compare_top_contested.sql").read_text(encoding="utf-8")
    assert run_sql.file_params(text) == run_sql.PARAMS
    with pytest.raises(SystemExit):
        run_sql.check_params("x", run_sql.file_params(text.replace("10 AS contested_min_edits",
                                                                   "11 AS contested_min_edits")))
    assert run_sql.file_params((SQL_DIR / "compare_mutual_reverts.sql").read_text()) == {}
    assert run_sql.file_params((SQL_DIR / "compare_mutual_reverts_preaggregated.sql").read_text()) == {}


def test_first_difference():
    assert run_sql.first_difference([1, 2], [1, 2]) is None
    assert run_sql.first_difference([1, 2], [1, 3]) == 1
    assert run_sql.first_difference([1, 2], [1, 2, 3]) == 2


# --------------------------------------------------------------------------
# compare.py helpers
# --------------------------------------------------------------------------
def test_code_lines_skip_blanks_and_comments():
    sql = "-- a comment\nSELECT 1\n\n  -- another\nFROM t;\n"
    cypher = "// result: main\nMATCH (n)\n\nRETURN n\n"
    assert compare.code_lines(sql, "--") == ["SELECT 1", "FROM t;"]
    assert compare.code_lines(cypher, "//") == ["MATCH (n)", "RETURN n"]
    assert compare.code_chars(["SELECT 1", "  FROM t;"]) == len("SELECT1FROMt;")


def test_json_array_text_takes_only_the_pipeline():
    text = ('{\n  "collection": "c",\n  "description": "a [b] } c",\n  "pipeline": [\n'
            '    {"$match": {"x": "]"}},\n\n    {"$limit": 2}\n  ]\n}\n')
    part = compare.json_array_text(text, "pipeline")
    assert part.startswith('  "pipeline": [') and part.endswith("]")
    assert len(compare.code_lines(part, None)) == 4


def test_real_query_files_load_and_count():
    qs = compare.load_queries()
    assert set(qs) == {(q, e) for q in compare.QUESTIONS for e in compare.ENGINES}
    for q in qs.values():
        assert len(q["code"]) > 0
    assert qs[(compare.MUTUAL, "MongoDB")]["stats"]["lookups"] >= 1


def _top(rows):
    return compare.norm_top([{"page_id": p, "score": s, "edits": e, "revert_actions": a,
                              "reverted_editors": 2, "contested": True} for p, s, e, a in rows])


def test_same_result_yes_and_no():
    rows = [(1, 0.6, 10, 6), (2, 0.5, 10, 5)]
    same = compare.same_result(compare.TOP, {"MongoDB": _top(rows), "Neo4j": _top(rows), "SQLite": _top(rows)})
    assert all(v["text"] == "yes" for v in same.values())
    swapped = [rows[1], rows[0]]
    same = compare.same_result(compare.TOP, {"MongoDB": _top(rows), "Neo4j": _top(swapped),
                                             "SQLite": _top(rows)})
    assert same["Neo4j"]["text"] == "no" and "row 1" in same["Neo4j"]["difference"]
    assert same["SQLite"]["text"] == "no" and "Neo4j" in same["SQLite"]["difference"]


def test_same_result_scores_rounded_and_counts_checked():
    a = _top([(1, 0.6, 10, 6)])
    b = _top([(1, 0.6 + 1e-9, 10, 6)])                  # equal after rounding to 6 digits
    c = _top([(1, 0.6, 10, 7)])                         # same page and score, other count
    same = compare.same_result(compare.TOP, {"MongoDB": a, "Neo4j": b, "SQLite": c})
    assert same["MongoDB"]["same"] and same["MongoDB"]["text"].startswith("yes (page_id + score)")


def test_norm_mutual_maps_aliases_back_to_keys():
    sql_rows = [{"page_id": 5, "a": "t:~2026-1-1", "b": "u:3", "a_reverted_b": 1, "b_reverted_a": 2}]
    neo_rows = [{"page_id": 5, "page_title": "P", "editor_a": "editor_aa", "editor_b": "SomeBot",
                 "a_reverted_b": 1, "b_reverted_a": 2}]
    m = {"editor_aa": "t:~2026-1-1", "SomeBot": "u:3"}
    assert compare.norm_mutual(sql_rows) == compare.norm_mutual(neo_rows, m)


def test_measure_times_each_engine_and_keeps_errors():
    calls = []

    def ok():
        calls.append("ok")
        return [{"x": 1}]

    def bad():
        raise RuntimeError("down")
    out = compare.measure({"A": ok, "B": bad}, runs=3)
    assert len(out["A"]["times"]) == 3 and out["A"]["rows"] == [{"x": 1}]
    assert len(calls) == 4                              # 1 warm-up + 3 timed runs
    assert out["B"]["error"].startswith("RuntimeError") and out["B"]["times"] == []


def test_measure_rounds_rotate_and_keep_round_medians():
    order = []

    def make(name):
        def run():
            order.append(name)
            return [{"x": name}]
        return run
    out = compare.measure({"A": make("A"), "B": make("B"), "C": make("C")}, runs=2, rounds=3)
    for n in "ABC":
        assert len(out[n]["times"]) == 6 and len(out[n]["round_medians"]) == 3
    assert order[:3] == ["A", "B", "C"]                          # warm-up
    assert order[3:9] == ["A", "B", "C", "B", "C", "A"]          # the order rotates after every run
    one = compare.measure({"A": make("A")}, runs=1)              # the notebook's quick check
    assert len(one["A"]["times"]) == 1 and one["A"]["round_medians"] == [one["A"]["times"][0]]


def test_faster_only_when_ranges_do_not_overlap():
    s = {"MongoDB": {"median_ms": 70.0, "min_ms": 65.0, "max_ms": 90.0},
         "Neo4j": {"median_ms": 80.0, "min_ms": 75.0, "max_ms": 120.0},
         "SQLite": {"median_ms": 20.0, "min_ms": 18.0, "max_ms": 25.0}}
    f = compare.faster_than(s)
    assert f == {"MongoDB": [], "Neo4j": [], "SQLite": ["MongoDB", "Neo4j"]}
    text = " ".join(compare.speed_sentences(s))
    assert "MongoDB and Neo4j: the ranges overlap" in text
    assert "SQLite is faster than MongoDB" in text and "SQLite is faster than Neo4j" in text
    assert compare.timing_stats({"times": [], "round_medians": [], "rows": None, "error": "x"})["median_ms"] is None


def test_pain_csv_loads_and_is_labelled_draft(tmp_path):
    pain = compare.load_pain()
    assert set(pain) == {(q, e) for q in compare.QUESTIONS for e in compare.ENGINES}
    assert all(1 <= p["score"] <= 5 for p in pain.values())
    assert all(p["scored_by"] == "draft by Claude Code; Comparison+viz owner to re-score" for p in pain.values())
    assert not any("rank" in p["reason"].lower() for p in pain.values())   # the rank reason is gone
    bad = tmp_path / "pain.csv"
    bad.write_text("question,engine,score,reason,scored_by\nmutual reverts,Neo4j,7,x,y\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        compare.load_pain(bad)


def test_final_is_refused_when_the_mac_is_busy(monkeypatch, capsys):
    monkeypatch.setattr(compare.os, "getloadavg", lambda: (3.5, 2.9, 2.8))

    def no_engines(*a, **k):
        raise AssertionError("must stop before it connects")
    monkeypatch.setattr(compare, "Engines", no_engines)
    assert compare.main(["--final"]) == 2
    out = capsys.readouterr().out
    assert "3.50" in out and str(compare.IDLE_LOAD) in out


def test_label_line_writes_the_measured_load():
    loads = ((1.25, 1.5, 1.75), (1.3, 1.4, 1.6))
    for label in ("draft", "final"):
        line = compare.label_line(label, loads)
        assert "1.25 / 1.50 / 1.75" in line and "1.30 / 1.40 / 1.60" in line
        assert "idle" not in line


def test_query_size_helpers_and_split_sql():
    assert compare.bracket_only_lines(["  },", "  {\"$limit\": 2}", "]", "  ),"]) == 3
    sts = compare.split_sql("-- c;\nPRAGMA x = 1;\n\nSELECT a,\n  b\nFROM t;\n")
    assert sts == ["PRAGMA x = 1", "SELECT a,\n  b\nFROM t"]
    extra = compare.load_extra_query()
    assert extra["sql"].startswith("SELECT f.page_id") and extra["setup_lines"] > 0


def test_first_scan_reads_the_cursor_plan():
    collscan = {"explainVersion": "2", "stages": [{"$cursor": {
        "queryPlanner": {"winningPlan": {"queryPlan": {"stage": "GROUP", "inputStage": {"stage": "COLLSCAN"}}},
                         "rejectedPlans": [{"stage": "IXSCAN", "indexName": "x"}]},
        "executionStats": {"totalDocsExamined": 37016}}}, {"$lookup": {}}]}
    assert compare.first_scan(collscan) == {"stage": "COLLSCAN", "index": None, "docs_examined": 37016}
    ixscan = {"queryPlanner": {"winningPlan": {"stage": "FETCH", "inputStage": {
        "stage": "IXSCAN", "indexName": "cohort_1_page_id_1"}}}, "executionStats": {"totalDocsExamined": 19858}}
    assert compare.first_scan(ixscan) == {"stage": "IXSCAN", "index": "cohort_1_page_id_1", "docs_examined": 19858}


def test_input_notes_say_what_is_inside_the_time():
    ctx = {"mongo_links": 37016, "mongo_links_history": 19858}
    assert "pre-aggregated" in compare.input_note(compare.MUTUAL, "Neo4j", ctx)
    assert "NOT inside the timed query" in compare.input_note(compare.MUTUAL, "Neo4j", ctx)
    assert "17,158 of the 37,016" in compare.input_note(compare.TOP, "MongoDB", ctx)
