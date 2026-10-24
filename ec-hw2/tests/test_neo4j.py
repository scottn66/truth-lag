"""Tests for the Neo4j part: export_graph.py, load_neo4j.py, queries/run_cypher.py, queries/cypher/.

Run (from the repo root):
    .venv/bin/python -m pytest ec-hw2/tests/test_neo4j.py -q

The fixture is a tiny made-up history cohort: MongoDB documents with the same fields
and types as the real revisions and revert_links documents. A pure-Python stand-in
for each aggregation pipeline feeds the export logic, and the expected rows are
worked out by hand below. One test runs the REAL pipelines on the local MongoDB, in
the separate database 'truthlag_test_graph' (dropped at the end); it is skipped when
MongoDB is not running. No test connects to Neo4j, so the main graph is never touched.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

HW2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW2))
import config  # noqa: E402
import export_graph as eg  # noqa: E402
import load_neo4j as ln  # noqa: E402
from ingest import build_documents as bd  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_cypher", HW2 / "queries" / "run_cypher.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

CYPHER_DIR = HW2 / "queries" / "cypher"
TEST_DB = "truthlag_test_graph"
T0 = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)     # inside the history window
H = config.COHORT_HISTORY

# Editors: (key, kind, name)
A = ("u:1", "registered", "Alice")
B = ("u:2", "registered", "Bob")
C = ("t:~2026-10001-01", "temporary", "~2026-10001-01")
X = ("u:9", "bot", "TestBot")
D = ("u:4", "registered", "Dave")          # only seen as a reverter
U = (None, "unknown", None)                # the dump hides the name
TITLES = {100: "War_Page", 200: "Calm_Page", 300: "Live_Page"}
LATE = config.HISTORY_FOLLOWUP_S + 86400    # reverted after the 20-day window

# (rev_id, page_id, author, minute, revert) with revert = (reverting_rev_id, reverter, T_s)
FIXTURE = [
    (1001, 100, A, 0, (2001, B, 60)),
    (1002, 100, B, 1, (2002, A, 60)),
    (1003, 100, A, 2, (2003, B, 120)),
    (1004, 100, A, 3, (2003, B, 60)),       # the same revert undid 1003 and 1004
    (1005, 100, C, 5, (2004, C, 30)),       # self-revert: not by another editor
    (1006, 100, X, 6, None),                # a bot edit
    (1007, 100, A, 7, (2005, X, 10)),       # reverted by a bot
    (1008, 100, B, 8, (2006, A, LATE)),     # reverted too late (not within_followup)
    (1009, 100, U, 9, (2008, A, 60)),       # unknown author: no editor key
    (1010, 100, C, 10, (2007, D, 90)),      # D never edited in the cohort
    (1011, 200, A, 11, None),
]


# --------------------------------------------------------------------------
# Fixture documents (same fields as the real MongoDB documents)
# --------------------------------------------------------------------------
def user_doc(ed):
    key, kind, name = ed
    return {"id": int(key[2:]) if key and key.startswith("u:") else None, "name": name, "kind": kind,
            "key": key, "is_bot": kind == "bot", "is_anon": kind == "temporary",
            "is_temp": kind == "temporary", "edit_count": 10}


def make_docs():
    revs, links = [], []
    for rev_id, page_id, author, minute, revert in FIXTURE:
        ts = T0 + timedelta(minutes=minute)
        hist = {"snapshot": "2026-09", "reverted": False, "reverted_any": False, "secs_to_revert": None,
                "reverting_rev_id": None, "reverter": None, "reverted_by_other": False,
                "followup_s": 1_900_000, "page_edits_prev_1h": 0}
        if revert:
            rr, reverter, t_s = revert
            by_other = author[0] is not None and reverter[0] is not None and author[0] != reverter[0]
            within = t_s <= config.HISTORY_FOLLOWUP_S
            hist.update({"reverted": within, "reverted_any": True, "secs_to_revert": t_s,
                         "reverting_rev_id": rr, "reverted_by_other": by_other,
                         "reverter": {"key": reverter[0], "name": reverter[2], "kind": reverter[1]}})
            links.append({"_id": f"history:{rev_id}", "cohort": H, "source": "dump",
                          "reverted_rev_id": rev_id, "page_id": page_id, "reverted_ts": ts,
                          "author_key": author[0], "author_kind": author[1],
                          "reverting_rev_id": rr, "reverting_ts": ts + timedelta(seconds=t_s),
                          "reverter_key": reverter[0], "reverter_name": reverter[2],
                          "reverter_kind": reverter[1], "T_s": t_s, "known_at": None, "K_s": None,
                          "method": None, "is_exact": True, "by_other": by_other,
                          "within_followup": within, "range_size": None, "confirmed_by_tag": False})
        revs.append({"_id": f"enwiki:{rev_id}", "wiki_db": "enwiki", "rev_id": rev_id,
                     "parent_id": rev_id - 1, "cohort": H,
                     "page": {"id": page_id, "title": TITLES[page_id], "ns": 0},
                     "user": user_doc(author), "ts": ts, "hour_utc": ts.hour, "size": 100,
                     "size_delta": 1, "comment": "c", "tags": [], "mw_reverted_tag": False,
                     "is_revert": False, "revert_method": None, "history": hist})
    # one live document: its key counts for the alias length, but it is not in the graph
    revs.append({"_id": "enwiki:5001", "wiki_db": "enwiki", "rev_id": 5001, "parent_id": 5000,
                 "cohort": config.COHORT_LIVE, "page": {"id": 300, "title": TITLES[300], "ns": 0},
                 "user": user_doc(("u:77", "registered", "Live")), "ts": T0 + timedelta(days=42),
                 "hour_utc": 12, "size": 1, "size_delta": 1, "comment": "", "tags": [],
                 "mw_reverted_tag": False, "is_revert": False, "revert_method": None,
                 "live": {"seen_ts": None, "revert_risk": 0.1, "page_edits_prev_1h": 0}})
    return revs, links


# Pure-Python stand-ins for the pipelines (they must give what MongoDB gives)
def ref_rows(revs, links):
    hist = sorted((d for d in revs if d["cohort"] == H), key=lambda d: (d["ts"], d["rev_id"]))
    keys = {d["user"]["key"] for d in revs} | {l["author_key"] for l in links} | {l["reverter_key"] for l in links}
    pages = {}
    for d in hist:
        p = pages.setdefault(d["page"]["id"], {"_id": d["page"]["id"], "edits": 0, "revisions": 0})
        p["title"] = d["page"]["title"]
        p["edits"] += 0 if d["user"]["is_bot"] else 1
        p["revisions"] += 1
    ok = [l for l in links if l["cohort"] == H and l["within_followup"] and l["by_other"]]
    acts, eds = defaultdict(set), defaultdict(set)
    for l in ok:
        acts[l["page_id"]].add(l["reverting_rev_id"])
        eds[l["page_id"]].add(l["author_key"])
    page_links = [{"_id": p, "revert_actions": len(acts[p]), "reverted_editors": len(eds[p])} for p in acts]
    editors = {}
    for d in hist:
        if d["user"]["key"] is None:
            continue
        e = editors.setdefault(d["user"]["key"], {"_id": d["user"]["key"], "edits": 0, "kinds": []})
        e.update(kind=d["user"]["kind"], name=d["user"]["name"])
        e["edits"] += 1
        if d["user"]["kind"] not in e["kinds"]:
            e["kinds"].append(d["user"]["kind"])
    by_rev = {l["reverted_rev_id"]: l for l in links if l["cohort"] == H}
    edited = []
    for d in hist:
        if d["user"]["key"] is None:
            continue
        l = by_rev.get(d["rev_id"])
        row = {"editor_key": d["user"]["key"], "page_id": d["page"]["id"], "rev_id": d["rev_id"],
               "ts": d["ts"], "reverted": d["history"]["reverted"],
               "reverted_by_other": l["by_other"] if l else False,
               "within_followup": l["within_followup"] if l else False}
        if l:
            row["reverting_rev_id"] = l["reverting_rev_id"]
        edited.append(row)
    trip = {}
    for l in sorted(ok, key=lambda l: (l["reverting_ts"], l["reverting_rev_id"])):
        if l["reverter_key"] is None or l["author_key"] is None:
            continue
        k = (l["reverter_key"], l["author_key"], l["page_id"])
        t = trip.setdefault(k, {"reverter_key": k[0], "author_key": k[1], "page_id": k[2],
                                "actions": set(), "n_revisions": 0, "ts": l["reverting_ts"]})
        t["actions"].add(l["reverting_rev_id"])
        t["n_revisions"] += 1
        t["last_ts"] = l["reverting_ts"]
        t.update(reverter_kind=l["reverter_kind"], reverter_name=l["reverter_name"],
                 author_kind=l["author_kind"])
    reverted = [{**{k: v for k, v in t.items() if k != "actions"}, "count": len(t["actions"])}
                for t in trip.values()]
    return {"keys": [k for k in keys if k], "pages": list(pages.values()), "page_links": page_links,
            "editors": list(editors.values()), "edited": edited, "reverted": reverted}


def build_from(rows, unknown_pages=(100,)):
    n_hex = bd.alias_length(rows["keys"])
    pages, orphans = eg.build_pages(rows["pages"], rows["page_links"])
    reverted = eg.build_reverted(rows["reverted"])
    editors, _ = eg.build_editors(rows["editors"], reverted, n_hex)
    edited = eg.build_edited(rows["edited"])
    return {"editors": editors, "pages": pages, "edited": edited, "reverted": reverted, "n_hex": n_hex,
            "stats": {"skipped_unknown_editor": len(unknown_pages),
                      "unknown_editor_pages": list(unknown_pages)}}


@pytest.fixture(scope="module")
def graph():
    return build_from(ref_rows(*make_docs()))


def alias(key, n_hex):
    """The shared pseudonym rule (ingest/build_documents.py); the tests keep no copy of it."""
    return bd.editor_alias(key, n_hex)


# --------------------------------------------------------------------------
# export_graph.py: the rows, worked out by hand
# --------------------------------------------------------------------------
def test_reverted_rows(graph):
    got = [(r["reverter_key"], r["author_key"], r["page_id"], r["count"], r["n_revisions"],
            r["ts"], r["last_ts"]) for r in graph["reverted"]]
    m = lambda x, s=0: T0 + timedelta(minutes=x, seconds=s)  # noqa: E731
    assert got == [
        ("u:1", "u:2", 100, 1, 1, m(2), m(2)),                       # A reverted B once
        ("u:2", "u:1", 100, 2, 3, m(1), m(4)),                       # B undid 3 revisions of A in 2 reverts
        ("u:4", C[0], 100, 1, 1, m(11, 30), m(11, 30)),               # D reverted C
        ("u:9", "u:1", 100, 1, 1, m(7, 10), m(7, 10)),                # the bot reverted A
    ]   # no self-revert (1005), no late revert (1008), no unknown author (1009)


def test_editor_rows(graph):
    n = graph["n_hex"]
    got = {e["key"]: (e["alias"], e["kind"], e["edits"], e["reverts_made"], e["reverts_received"])
           for e in graph["editors"]}
    assert got == {
        C[0]: (alias(C[0], n), "temporary", 2, 0, 1),
        "u:1": (alias("u:1", n), "registered", 5, 1, 3),
        "u:2": (alias("u:2", n), "registered", 2, 2, 1),
        "u:4": (alias("u:4", n), "registered", 0, 1, 0),             # reverter only: still a node
        "u:9": ("TestBot", "bot", 1, 1, 0),                          # bots keep their name
    }
    assert [e["key"] for e in graph["editors"]] == sorted(got)
    humans = [e["alias"] for e in graph["editors"] if e["kind"] != "bot"]
    assert all(re.fullmatch(r"editor_[0-9a-f]+", a) for a in humans) and len(set(humans)) == len(humans)
    for e in graph["editors"]:               # the export uses public_name(), as Mongo and SQL do
        assert e["alias"] == bd.public_name(e["kind"], e["key"], "TestBot" if e["kind"] == "bot" else None, n)


def test_no_private_alias_rule():
    """export_graph.py, run_cypher.py and compare.py call ingest/build_documents.py; none hashes keys itself."""
    for path in (HW2 / "export_graph.py", HW2 / "queries" / "run_cypher.py", HW2 / "comparison" / "compare.py"):
        text = path.read_text(encoding="utf-8")
        assert "hashlib" not in text and "hmac" not in text.lower() and "sha1(" not in text, path.name


def test_page_rows(graph):
    p100, p200 = graph["pages"]
    # 9 human edits (the bot edit 1006 is out, the unknown editor 1009 is in, as in Mongo Q2)
    assert (p100["id"], p100["title"], p100["edits"], p100["revert_actions"],
            p100["reverted_editors"]) == (100, "War_Page", 9, 5, 3)
    assert p100["score"] == pytest.approx(5 / 9) and p100["contested"] is False   # edits < 10
    assert (p200["id"], p200["edits"], p200["revert_actions"], p200["score"], p200["contested"]) == \
        (200, 1, 0, 0.0, False)


def test_edited_rows(graph):
    rows = {e["rev_id"]: e for e in graph["edited"]}
    assert sorted(rows) == [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1010, 1011]   # no 1009
    flags = lambda r: (r["reverted"], r["reverted_by_other"], r["within_followup"], r["reverting_rev_id"])  # noqa: E731
    assert flags(rows[1001]) == (True, True, True, 2001)
    assert flags(rows[1004]) == (True, True, True, 2003)
    assert flags(rows[1005]) == (True, False, True, 2004)     # self-revert
    assert flags(rows[1008]) == (False, True, False, 2006)    # late revert
    assert flags(rows[1006]) == (False, False, False, None)   # never reverted
    assert [e["rev_id"] for e in graph["edited"]] == sorted(rows)


def test_checks_pass_and_edges_give_page_counts(graph):
    checks = eg.check_graph(graph)
    assert all(c["ok"] for c in checks), checks
    # the comparison query counts from EDITED rows: same revert_actions as the Page row
    acts = {e["reverting_rev_id"] for e in graph["edited"]
            if e["page_id"] == 100 and e["within_followup"] and e["reverted_by_other"]}
    assert len(acts) == graph["pages"][0]["revert_actions"]


def test_check_graph_finds_a_dangling_edge(graph):
    bad = {**graph, "reverted": graph["reverted"] + [
        {"reverter_key": "u:404", "author_key": "u:1", "page_id": 100, "count": 1, "n_revisions": 1,
         "ts": T0, "last_ts": T0}]}
    checks = {c["name"]: c["ok"] for c in eg.check_graph(bad)}
    assert checks["every REVERTED row has its two Editors and its Page"] is False


def test_contested_rule_boundaries():
    assert eg.is_contested(10, 2, 2, 0.2) is True                # every bound is inclusive
    assert eg.is_contested(9, 2, 2, 2 / 9) is False              # too few human edits
    assert eg.is_contested(10, 1, 2, 0.1) is False               # one revert action
    assert eg.is_contested(10, 2, 1, 0.2) is False               # one reverted editor
    assert eg.is_contested(20, 3, 2, 0.15) is False              # score below 0.2
    assert eg.page_score(0, 3) is None and eg.page_score(4, 1) == 0.25
    pages, orphans = eg.build_pages([{"_id": 1, "title": "P", "edits": 10}, {"_id": 2, "title": "Q", "edits": 0}],
                                    [{"_id": 1, "revert_actions": 2, "reverted_editors": 2},
                                     {"_id": 2, "revert_actions": 1, "reverted_editors": 1},
                                     {"_id": 3, "revert_actions": 1, "reverted_editors": 1}])
    assert [(p["id"], p["score"], p["contested"]) for p in pages] == [(1, 0.2, True), (2, None, False)]
    assert orphans == 1


def test_top_contested_order():
    pages = [{"id": i, "edits": e, "revert_actions": a, "reverted_editors": 2, "score": a / e}
             for i, e, a in [(5, 10, 5), (4, 20, 10), (3, 20, 10), (2, 12, 6), (1, 9, 9)]]
    # score desc, revert_actions desc, edits desc, page_id asc; page 1 has < 10 edits
    assert [p["id"] for p in eg.top_contested(pages)] == [3, 4, 2, 5]


def test_csv_values():
    assert eg.csv_value(True) == "true" and eg.csv_value(False) == "false"
    assert eg.csv_value(None) == ""
    assert eg.csv_value(datetime(2026, 9, 8, 1, 2, 3, tzinfo=timezone.utc)) == "2026-09-08T01:02:03Z"
    assert eg.csv_value(datetime(2026, 9, 8, 3, 2, 3, tzinfo=timezone(timedelta(hours=2)))) == \
        "2026-09-08T01:02:03Z"
    with pytest.raises(ValueError):
        eg.csv_value(datetime(2026, 9, 8))                       # naive times are refused
    assert float(eg.csv_value(5 / 9)) == 5 / 9                    # no precision lost
    assert eg.csv_value(7) == "7"


def test_legacy_escape_guard():
    assert eg.legacy_escape_risk('A \\"B\\"')                     # backslash + quote
    assert eg.legacy_escape_risk("a,b\\")                         # quoted field ending with backslash
    assert not eg.legacy_escape_risk("\\x09")                     # the real data-v1 title: safe
    assert not eg.legacy_escape_risk('This "quoted" title, ok')
    with pytest.raises(ValueError):
        eg.csv_text([{"id": 1, "title": 'bad\\"'}], ["id", "title"])


def test_write_graph_round_trip(graph, tmp_path):
    counts = eg.write_graph(graph, tmp_path)
    assert counts == {"editors.csv": 5, "pages.csv": 2, "edited.csv": 10, "reverted.csv": 4}
    assert not list(tmp_path.glob("*.tmp"))
    for name, (fname, columns) in eg.FILES.items():
        with open(tmp_path / fname, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert list(rows[0].keys()) == columns
    pages = ln.read_csv_rows(tmp_path / "pages.csv")
    assert pages[0]["contested"] == "false" and float(pages[0]["score"]) == 5 / 9
    edited = {r["rev_id"]: r for r in ln.read_csv_rows(tmp_path / "edited.csv")}
    assert edited["1006"]["reverting_rev_id"] is None and edited["1001"]["ts"] == "2026-09-08T12:00:00Z"


def test_compare_with_mongo_q2(tmp_path):
    pages = [{"id": 7, "edits": 10, "revert_actions": 5, "reverted_editors": 2, "score": 0.5}]
    path = tmp_path / "mongo_q2.csv"
    pd.DataFrame([{"rank": 1, "page_id": 7, "score": 0.5000000001}]).to_csv(path, index=False)
    assert eg.compare_with_mongo_q2(pages, path)["ok"] is True
    pd.DataFrame([{"rank": 1, "page_id": 8, "score": 0.5}]).to_csv(path, index=False)
    assert eg.compare_with_mongo_q2(pages, path)["ok"] is False


def test_real_pipelines_on_mongo_match_the_stand_in():
    """The real aggregation pipelines give the same tables as the pure-Python stand-in."""
    pymongo = pytest.importorskip("pymongo")
    try:
        client = eg.connect(config.MONGO_URI, timeout_ms=1500)
    except pymongo.errors.PyMongoError:
        pytest.skip("MongoDB is not running")
    try:
        client.drop_database(TEST_DB)
        db = client[TEST_DB]
        revs, links = make_docs()
        db[config.COL_REVISIONS].insert_many(revs)
        db[config.COL_REVERT_LINKS].insert_many(links)
        assert eg.check_inputs(db) == {config.COL_REVISIONS: 11, config.COL_REVERT_LINKS: 9}
        got = eg.read_graph(db)
        want = build_from(ref_rows(revs, links))
        assert got["n_hex"] == want["n_hex"]
        assert got["stats"]["alias_keys_both_cohorts"] == 6          # 5 history keys + 1 live key
        assert got["stats"]["skipped_unknown_editor"] == 1
        assert got["stats"]["unknown_editor_pages"] == [100]
        assert got["stats"]["editors_only_as_reverter"] == 1
        assert got["stats"]["pages_with_several_titles"] == 0        # one title per fixture page
        for name in ("editors", "pages", "edited", "reverted"):
            assert got[name] == want[name], name
    finally:
        client.drop_database(TEST_DB)
        client.close()


# --------------------------------------------------------------------------
# load_neo4j.py and load.cypher
# --------------------------------------------------------------------------
def test_split_statements():
    text = ("// header; with a semicolon in a comment;\n\n"
            "// result: main\nMATCH (n)\nRETURN n;\n"
            "// only a comment;\n"
            "RETURN 1 AS x ;  \n"
            "RETURN 2;\n"
            "// a comment-only part at the end is skipped\n")
    st = ln.split_statements(text)
    assert [ln.code_of(s) for s in st] == ["MATCH (n)\nRETURN n", "RETURN 1 AS x", "RETURN 2"]
    assert ln.split_statements("RETURN 3") == ["RETURN 3"]           # the last ';' is optional
    assert "// result: main" in st[0]


def test_load_cypher_statements():
    sts = ln.load_statements()
    assert sts[0].startswith("MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS")
    assert "CREATE CONSTRAINT editor_key IF NOT EXISTS FOR (e:Editor) REQUIRE e.key IS UNIQUE" in sts
    assert "CREATE CONSTRAINT page_id IF NOT EXISTS FOR (p:Page) REQUIRE p.id IS UNIQUE" in sts
    files = [ln.csv_file_of(s) for s in sts if ln.csv_file_of(s)]
    assert files == ["editors.csv", "pages.csv", "edited.csv", "reverted.csv"]   # nodes before edges
    for s in sts:
        if ln.csv_file_of(s):
            assert "CALL (row) {" in s and s.rstrip().endswith("} IN TRANSACTIONS OF 10000 ROWS")


def test_load_cypher_reads_exactly_the_export_columns():
    """Every column the export writes is loaded, and load.cypher reads no other column."""
    cols = {fname: c for fname, c in eg.FILES.values()}
    for s in ln.load_statements():
        fname = ln.csv_file_of(s)
        if fname:
            assert set(re.findall(r"row\.(\w+)", s)) == set(cols[fname]), fname


def test_load_cypher_casts_every_typed_value():
    text = " ".join(ln.load_statements())
    for expr in ["toInteger(row.edits)", "toFloat(row.score)", "toBoolean(row.contested)",
                 "datetime(row.ts)", "datetime(row.last_ts)", "toInteger(row.count)",
                 "toBoolean(row.within_followup)", "toInteger(row.reverting_rev_id)",
                 "toInteger(row.page_id)"]:
        assert expr in text, expr


def test_cypher_files_use_current_syntax_only():
    for path in CYPHER_DIR.glob("*.cypher"):
        code = " ".join(ln.code_of(s) for s in ln.split_statements(path.read_text(encoding="utf-8")))
        assert not re.search(r"CALL\s*\{\s*WITH", code), path.name
        assert "ASSERT" not in code, path.name
        assert not re.search(r"CREATE CONSTRAINT\s+(\w+\s+)?(IF NOT EXISTS\s+)?ON\b", code), path.name
        assert "gds.graph.project.cypher" not in code and "apoc.load.csv" not in code, path.name


def test_to_unwind():
    st = next(s for s in ln.load_statements() if ln.csv_file_of(s) == "edited.csv")
    q = ln.to_unwind(st)
    assert q.startswith("UNWIND $rows AS row\nCALL (row) {")
    assert "IN TRANSACTIONS" not in q and "LOAD CSV" not in q and q.rstrip().endswith("}")
    with pytest.raises(ValueError):
        ln.to_unwind("CREATE CONSTRAINT x IF NOT EXISTS FOR (e:Editor) REQUIRE e.key IS UNIQUE")


def test_contested_subset():
    tables = {
        "pages": [{"id": "1", "contested": "true"}, {"id": "2", "contested": "false"}],
        "editors": [{"key": k} for k in ("u:1", "u:2", "u:3", "u:4")],
        "edited": [{"editor_key": "u:1", "page_id": "1"}, {"editor_key": "u:3", "page_id": "2"}],
        "reverted": [{"reverter_key": "u:2", "author_key": "u:1", "page_id": "1"},
                     {"reverter_key": "u:4", "author_key": "u:3", "page_id": "2"}],
    }
    sub = ln.contested_subset(tables)
    assert [p["id"] for p in sub["pages"]] == ["1"]
    assert [e["key"] for e in sub["editors"]] == ["u:1", "u:2"]      # u:2 only reverted on page 1
    assert len(sub["edited"]) == 1 and len(sub["reverted"]) == 1
    assert ln.expected_counts(sub) == {"Editor": 2, "Page": 1, "EDITED": 1, "REVERTED": 1}


def test_batches_and_csv_row_count(tmp_path):
    assert [len(b) for b in ln.batches(list(range(12)), 5)] == [5, 5, 2]
    p = tmp_path / "x.csv"
    p.write_text('id,title\n1,"two\nlines"\n2,b\n', encoding="utf-8")
    assert ln.csv_row_count(p) == 2


# --------------------------------------------------------------------------
# run_cypher.py and the query files
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", rc.QUERY_FILES)
def test_query_file_headers(name):
    q = rc.parse_file(CYPHER_DIR / f"{name}.cypher")
    head = " ".join(q["header"])
    assert q["header"][0].startswith(("Cypher Q", "Comparison query"))
    assert "Output columns" in head and "spec" in head.lower()
    assert q["params"] == rc.PARAMS                       # the Browser line matches config.py
    labels = [s["label"] for s in q["statements"] if s["label"]]
    assert "main" in labels
    used = set(re.findall(r"\$(\w+)", " ".join(s["code"] for s in q["statements"])))
    assert used <= set(rc.PARAMS), used - set(rc.PARAMS)


def test_queries_never_return_keys_or_names():
    """Result statements show aliases: no RETURN of .key or .name."""
    for name in rc.QUERY_FILES:
        for s in rc.parse_file(CYPHER_DIR / f"{name}.cypher")["statements"]:
            ret = s["code"].split("RETURN")[-1]
            assert not re.search(r"\.(key|name)\s+AS\b", ret), (name, s["label"])


def test_read_only_detection():
    assert rc.is_read_only("MATCH (n) RETURN n")
    assert rc.is_read_only("CALL gds.pageRank.stream('g', {}) YIELD nodeId RETURN nodeId")
    assert not rc.is_read_only("CALL gds.louvain.write('g', {writeProperty: 'c'}) YIELD modularity RETURN 1")
    assert not rc.is_read_only("CALL gds.graph.project('g', 'Editor', 'REVERTED') YIELD graphName RETURN 1")
    assert not rc.is_read_only("CALL gds.graph.drop('g', false) YIELD graphName RETURN graphName")
    assert rc.is_read_only("// CREATE in a comment\nMATCH (n) RETURN n")


def test_output_stem_and_plain_values():
    assert rc.output_stem("q1_mutual_reverts", "main") == "cypher_q1_mutual_reverts"
    assert rc.output_stem("q1_mutual_reverts", "total") == "cypher_q1_mutual_reverts_total"
    assert rc.plain(["a", "b"]) == "a | b" and rc.plain(3) == 3


def test_check_privacy():
    allowed = {"editor_1a2b3c4d", "ClueBot NG"}
    rc.check_privacy(pd.DataFrame({"editor": ["editor_1a2b3c4d", "ClueBot NG"]}), allowed, "t")
    rc.check_privacy(pd.DataFrame({"top_reverters": ["ClueBot NG | editor_1a2b3c4d"]}), allowed, "t")
    with pytest.raises(SystemExit):
        rc.check_privacy(pd.DataFrame({"x": ["u:123"]}), allowed, "t")                  # a key
    with pytest.raises(SystemExit):
        rc.check_privacy(pd.DataFrame({"editor_a": ["Alice"]}), allowed, "t")           # a real name


def test_check_top_contested_and_mutual(tmp_path):
    cy = pd.DataFrame({"page_id": [7, 8], "score": [0.5, 0.25], "edits": [10, 12],
                       "revert_actions": [5, 3], "reverted_editors": [2, 3]})
    path = tmp_path / "m.csv"
    cy.to_csv(path, index=False)
    assert rc.check_top_contested(cy, path)["ok"] is True
    swapped = cy.iloc[::-1]
    swapped.to_csv(path, index=False)
    assert rc.check_top_contested(cy, path)["ok"] is False             # order matters
    pairs = pd.DataFrame({"page_id": [1], "page_title": ["P"], "editor_a": ["editor_aa"],
                          "editor_b": ["editor_bb"], "a_reverted_b": [1], "b_reverted_a": [2]})
    pairs.to_csv(path, index=False)
    res = rc.check_mutual(pairs, pd.DataFrame({"mutual_pairs": [1]}), path)
    assert all(c["ok"] for c in res) and len(res) == 2


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def single(self):
        return self.rows[0] if self.rows else None

    def data(self):
        return self.rows


class FakeSession:
    """Answers session.run() with the first canned rows whose text is in the query."""

    def __init__(self, answers):
        self.answers, self.queries = answers, []

    def run(self, query, *args, **kwargs):
        self.queries.append(query)
        for part, rows in self.answers.items():
            if part in query:
                return FakeResult(rows)
        raise AssertionError(f"unexpected query: {query[:80]}")


def test_q2_pagerank_settings_converge_and_match():
    """Both PageRank calls use the same settings, with maxIterations 200 and tolerance 1e-7."""
    q = rc.parse_file(CYPHER_DIR / "q2_central_reverters.cypher")
    calls = [c for s in q["statements"] for c in rc.pagerank_calls(s["code"])]
    assert len(calls) == 2 and len(set(calls)) == 1
    graph, settings = calls[0]
    assert graph == "cypher_q2_reverse"
    assert "maxIterations: 200" in settings and "tolerance: 1e-7" in settings
    assert "relationshipWeightProperty: 'count'" in settings
    by_label = {s["label"]: s for s in q["statements"] if s["label"]}
    assert set(by_label) == {"main", "humans", "by_degree"}
    assert not rc.pagerank_calls(by_label["by_degree"]["code"])


def test_check_pagerank_converged_stops_when_not_converged():
    ok = FakeSession({"gds.pageRank.stats('g', {maxIterations: 200})": [{"converged": True, "iterations": 111}]})
    c = rc.check_pagerank_converged(ok, "g", "{maxIterations: 200}")
    assert c["ok"] and c["iterations"] == 111
    assert ok.queries[0].startswith("CALL gds.pageRank.stats('g', {maxIterations: 200})")
    bad = FakeSession({"gds.pageRank.stats": [{"converged": False, "iterations": 20}]})
    with pytest.raises(SystemExit):
        rc.check_pagerank_converged(bad, "g", "{}")


def test_compare_top_contested_cypher_filters_links_before_counting_edits():
    """The same steps as Mongo Q2: revert links first, keep 2+ reverted editors, then count edits."""
    code = rc.parse_file(CYPHER_DIR / "compare_top_contested.cypher")["statements"][0]["code"]
    first, second = [m.start() for m in re.finditer(r"\bMATCH\b", code)]
    keep = code.index("WHERE reverted_editors >= $contested_min_editors")
    assert code.index("WHERE e.within_followup AND e.reverted_by_other") < keep < second
    assert "count(CASE WHEN x.kind <> 'bot' THEN 1 END) AS edits" in code[second:]
    ret = code.split("RETURN")[-1]
    assert "rank" not in ret and "collect(" not in code and "UNWIND" not in code   # rank is added in Python
    cols = re.findall(r"AS (\w+)", ret) + ["edits", "revert_actions", "reverted_editors", "score"]
    assert set(cols) == {"page_id", "page_title", "edits", "revert_actions", "reverted_editors", "score",
                         "contested"}


def test_with_rank_adds_rank_in_row_order():
    df = pd.DataFrame({"page_id": [9, 3, 5]})
    out = rc.with_rank(df)
    assert list(out.columns) == ["rank", "page_id"] and list(out["rank"]) == [1, 2, 3]
    assert ("compare_top_contested", "main") in rc.ADD_RANK and "rank" not in df.columns


def test_q5_starts_from_the_contested_page_index():
    code = rc.parse_file(CYPHER_DIR / "q5_two_hop_contested.cypher")["statements"][0]["code"]
    lines = code.splitlines()
    assert lines[0] == "MATCH (p:Page {contested: true})" and lines[1] == "USING INDEX p:Page(contested)"
    assert lines[2].startswith("MATCH (a:Editor)-[:EDITED]->(p)<-[:EDITED]-(b:Editor)")
    # the index the hint needs is created by load.cypher
    assert "CREATE INDEX page_contested IF NOT EXISTS FOR (p:Page) ON (p.contested)" in ln.load_statements()


def test_q3_reports_community_sizes_star_share_and_page_share():
    q = rc.parse_file(CYPHER_DIR / "q3_conflict_communities.cypher")
    by_label = {s["label"]: s for s in q["statements"] if s["label"]}
    assert {"louvain_stats", "community_sizes", "main"} <= set(by_label)
    assert by_label["community_sizes"]["read_only"] and not by_label["louvain_stats"]["read_only"]
    labels = [s["label"] for s in q["statements"]]
    assert labels.index("louvain_stats") < labels.index("community_sizes") < labels.index("main")
    for col in ("communities", "communities_2plus", "communities_1", "editors_without_revert"):
        assert f"AS {col}" in by_label["community_sizes"]["code"]
    main = by_label["main"]["code"]
    for col in ("star_share", "reverted_edges", "top_page", "top_page_reverts", "top_page_share",
                "top_reverters"):
        assert f"AS {col}" in main, col


def test_check_q3_compares_community_totals():
    session = FakeSession({"WHERE e.communityId IS NOT NULL": [{"n": 5}], "MATCH (e:Editor) RETURN": [{"n": 5}]})
    frames = {"louvain_stats": pd.DataFrame({"communities": [3]}),
              "community_sizes": pd.DataFrame({"communities": [3], "communities_2plus": [1],
                                               "communities_1": [2]}),
              "wcc_sizes": pd.DataFrame({"editors": [2, 3]})}
    checks = rc.check_q3(session, frames)
    assert all(c["ok"] for c in checks) and len(checks) == 3
    frames["community_sizes"].loc[0, "communities"] = 4
    assert not all(c["ok"] for c in rc.check_q3(session, frames))


def test_check_aliases_uses_the_shared_rule(monkeypatch):
    keys = ["u:1", "u:2", C[0]]
    monkeypatch.setattr(bd, "all_editor_keys", lambda: set(keys))
    n = bd.alias_length(keys)
    good = [{"key": k, "kind": "registered", "alias": bd.editor_alias(k, n)} for k in keys]
    assert rc.check_aliases(FakeSession({"MATCH (e:Editor)": good}))["ok"] is True
    stale = good[:2] + [{"key": C[0], "kind": "temporary", "alias": "editor_0000"}]
    res = rc.check_aliases(FakeSession({"MATCH (e:Editor)": stale}))
    assert res["ok"] is False and res["different"] == 1


def test_circle_order_removes_crossings():
    pairs = {frozenset(p) for p in [("a", "c"), ("c", "b"), ("b", "d"), ("d", "a")]}
    assert rc.crossings(["a", "b", "c", "d"], pairs) == 1                # key order: a-c crosses b-d
    assert rc.crossings(rc.circle_order(["a", "b", "c", "d"], pairs), pairs) == 0
    big = [f"k{i:02d}" for i in range(11)]                                 # greedy path: still a full order
    order = rc.circle_order(big, {frozenset((big[i], big[i + 1])) for i in range(10)})
    assert sorted(order) == big


def test_pick_page_and_draw_figure(tmp_path):
    q4 = pd.DataFrame({"page_id": [1, 2, 3], "warring_editors": [9, 4, 4], "mutual_pairs": [7, 2, 3],
                       "editors_in_any_revert": [25, 6, 5]})
    assert rc.pick_war_page(q4) == 3                                      # page 1 is too big to draw
    edges = pd.DataFrame([
        {"src_key": "u:1", "src": "editor_aaaa1111", "src_kind": "registered",
         "dst_key": "u:2", "dst": "editor_bbbb2222", "dst_kind": "registered", "n": 2},
        {"src_key": "u:2", "src": "editor_bbbb2222", "src_kind": "registered",
         "dst_key": "u:1", "dst": "editor_aaaa1111", "dst_kind": "registered", "n": 1},
        {"src_key": "u:9", "src": "TestBot", "src_kind": "bot",
         "dst_key": "u:1", "dst": "editor_aaaa1111", "dst_kind": "registered", "n": 1},
    ])
    out = rc.draw_edit_war("Test_Page", edges, tmp_path / "war.png")
    assert out.exists() and out.stat().st_size > 10_000
    assert not list(tmp_path.glob("*.tmp*"))
