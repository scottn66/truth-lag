"""Export the revert graph of the history cohort from MongoDB to CSV files for Neo4j.

Purpose
    This is the spec's "CSV export from Mongo" (spec section 4). Aggregation pipelines
    read the history cohort from MongoDB. The script writes the four CSV files of
    DATA_MODEL.md section 5. Then load_neo4j.py (or queries/cypher/load.cypher in
    Neo4j Desktop) loads them with LOAD CSV.
    - editors.csv   one row per Editor node: key, alias, kind, edits, reverts_made,
                    reverts_received
    - pages.csv     one row per Page node: id, title, edits, revert_actions,
                    reverted_editors, score, contested
    - edited.csv    one row per history revision with a known editor (EDITED)
    - reverted.csv  one row per (reverter, reverted editor, page) (REVERTED)

    Rules (all thresholds come from config.py):
    - alias: the shared pseudonym rule. This script does not make its own aliases: it
      calls public_name() and alias_length() in ingest/build_documents.py, the same
      functions that the MongoDB, SQL and Atlas results use, so an editor has the same
      alias everywhere (see config.ALIAS_HEX and config.ALIAS_SECRET for the rule).
      alias_length() gets every editor key of BOTH cohorts, so it can check that no two
      keys share an alias. Bots keep their real name as the alias.
    - Page.title: the page_title of the page's newest history revision (by ts, then
      rev_id), read from MongoDB as Mongo Q2 and the SQL query read it. This script does
      not choose a title itself: page_title comes from ingest/parse_history.py, which sets
      the display title rule for every engine. The log shows how many pages have more
      than one title in the cohort.
    - Page counts use the shared definition of DATA_MODEL.md section 7, so they match
      Mongo Q2: edits = non-bot history revisions; revert_actions = distinct
      reverting_rev_id of links with within_followup and by_other; reverted_editors =
      distinct author_key of those links; score = revert_actions / edits (empty when
      edits = 0). contested = edits >= 10, reverted_editors >= 2, revert_actions >= 2
      and score >= 0.2.
    - EDITED rows carry reverting_rev_id, reverted_by_other and within_followup from
      the revision's revert link, so Cypher can count DISTINCT reverting revisions.
    - REVERTED rows come from history links with within_followup and by_other and
      both keys set: count = distinct reverting_rev_id, n_revisions = reverted
      revisions, ts = first reverting time, last_ts = last reverting time.
    - Editor.edits = history revisions of the editor (bots included).
      Editor.reverts_made = sum of count on its outgoing REVERTED rows (a revert that
      undid two editors counts once for each). Editor.reverts_received = sum of count
      on its incoming REVERTED rows (= distinct revert actions by others against it).
    - Revisions without an editor key (user kind "unknown", the dump hides the name)
      get no EDITED row. The script prints how many (3 in data-v1).

Inputs
    The local MongoDB (config.MONGO_URI, config.MONGO_DB): the collections revisions
    and revert_links, built by load_mongo.py. Only the history cohort goes into the
    graph; the alias check also gets the live cohort keys.

Outputs
    data/neo4j/import/{editors,pages,edited,reverted}.csv (UTF-8, header row, times as
    ISO 8601 UTC with "Z", booleans as true/false, empty field = no value) and
    data/neo4j/import/_SUCCESS_export_graph.json with the row counts and checks.
    These files hold editor keys (user ids, temporary account names): they stay in
    data/ and are never committed.

Run (from the repo root)
    .venv/bin/python ec-hw2/export_graph.py
    It takes about 15 seconds and prints the row count of each file.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from ingest import build_documents as bd  # noqa: E402  (the pseudonym rule)

H = config.COHORT_HISTORY

EDITOR_COLUMNS = ["key", "alias", "kind", "edits", "reverts_made", "reverts_received"]
PAGE_COLUMNS = ["id", "title", "edits", "revert_actions", "reverted_editors", "score", "contested"]
EDITED_COLUMNS = ["editor_key", "page_id", "rev_id", "ts", "reverted", "reverted_by_other",
                  "within_followup", "reverting_rev_id"]
REVERTED_COLUMNS = ["reverter_key", "author_key", "page_id", "count", "n_revisions", "ts",
                    "last_ts"]
FILES = {"editors": ("editors.csv", EDITOR_COLUMNS),
         "pages": ("pages.csv", PAGE_COLUMNS),
         "edited": ("edited.csv", EDITED_COLUMNS),
         "reverted": ("reverted.csv", REVERTED_COLUMNS)}
SUCCESS_NAME = "_SUCCESS_export_graph.json"
MONGO_Q2_FILE = config.RESULTS_DIR / "mongo_q2_top_contested_pages.csv"


# --------------------------------------------------------------------------
# Aggregation pipelines (MongoDB does the grouping)
# --------------------------------------------------------------------------
def alias_keys_pipeline() -> list[dict]:
    """On revisions: every editor key of both cohorts (authors and reverters).

    This is the same key set as ingest/build_documents.all_editor_keys(), so the
    alias length is the same as in the Mongo results.
    """
    return [
        {"$group": {"_id": "$user.key"}},
        {"$unionWith": {"coll": config.COL_REVERT_LINKS, "pipeline": [
            {"$project": {"k": ["$author_key", "$reverter_key"]}},
            {"$unwind": "$k"},
            {"$group": {"_id": "$k"}},
        ]}},
        {"$match": {"_id": {"$ne": None}}},
        {"$group": {"_id": "$_id"}},
    ]


def pages_pipeline() -> list[dict]:
    """On revisions: one row per history page with its title and non-bot edits.

    The title is page.title of the page's last revision (by ts, then rev_id), as in
    Mongo Q2; page.title itself comes from the history table (parse_history.py).
    n_titles = how many different titles the page has in the cohort (for the log).
    Revisions of unknown editors count as non-bot edits, as in Mongo Q2.
    """
    return [
        {"$match": {"cohort": H}},
        {"$sort": {"ts": 1, "rev_id": 1}},
        {"$group": {"_id": "$page.id",
                    "title": {"$last": "$page.title"},
                    "titles": {"$addToSet": "$page.title"},
                    "edits": {"$sum": {"$cond": ["$user.is_bot", 0, 1]}},
                    "revisions": {"$sum": 1}}},
        {"$addFields": {"n_titles": {"$size": "$titles"}}},
        {"$project": {"titles": 0}},
    ]


def page_links_pipeline() -> list[dict]:
    """On revert_links: revert_actions and reverted_editors per page (the first stages of Mongo Q2)."""
    return [
        {"$match": {"cohort": H, "within_followup": True, "by_other": True}},
        {"$group": {"_id": "$page_id",
                    "actions": {"$addToSet": "$reverting_rev_id"},
                    "editors": {"$addToSet": "$author_key"}}},
        {"$project": {"revert_actions": {"$size": "$actions"},
                      "reverted_editors": {"$size": "$editors"}}},
    ]


def editors_pipeline() -> list[dict]:
    """On revisions: one row per history editor key with kind, last name and edit count."""
    return [
        {"$match": {"cohort": H, "user.key": {"$ne": None}}},
        {"$sort": {"ts": 1, "rev_id": 1}},
        {"$group": {"_id": "$user.key",
                    "kind": {"$last": "$user.kind"},
                    "kinds": {"$addToSet": "$user.kind"},
                    "name": {"$last": "$user.name"},
                    "edits": {"$sum": 1}}},
    ]


def edited_pipeline() -> list[dict]:
    """On revisions: one row per history revision with a known editor, plus its revert link."""
    return [
        {"$match": {"cohort": H, "user.key": {"$ne": None}}},
        {"$lookup": {"from": config.COL_REVERT_LINKS, "localField": "rev_id",
                     "foreignField": "reverted_rev_id",
                     "pipeline": [{"$match": {"cohort": H}},
                                  {"$project": {"_id": 0, "reverting_rev_id": 1, "by_other": 1,
                                                "within_followup": 1}}],
                     "as": "link"}},
        {"$project": {"_id": 0, "editor_key": "$user.key", "page_id": "$page.id", "rev_id": 1,
                      "ts": 1, "reverted": "$history.reverted",
                      "reverted_by_other": {"$ifNull": [{"$first": "$link.by_other"}, False]},
                      "within_followup": {"$ifNull": [{"$first": "$link.within_followup"}, False]},
                      "reverting_rev_id": {"$first": "$link.reverting_rev_id"}}},
    ]


def reverted_pipeline() -> list[dict]:
    """On revert_links: one row per (reverter, reverted editor, page), reverts by others within 20 days."""
    return [
        {"$match": {"cohort": H, "within_followup": True, "by_other": True,
                    "reverter_key": {"$ne": None}, "author_key": {"$ne": None}}},
        {"$sort": {"reverting_ts": 1, "reverting_rev_id": 1}},
        {"$group": {"_id": {"reverter_key": "$reverter_key", "author_key": "$author_key",
                            "page_id": "$page_id"},
                    "actions": {"$addToSet": "$reverting_rev_id"},
                    "n_revisions": {"$sum": 1},
                    "ts": {"$min": "$reverting_ts"},
                    "last_ts": {"$max": "$reverting_ts"},
                    "reverter_kind": {"$last": "$reverter_kind"},
                    "reverter_name": {"$last": "$reverter_name"},
                    "author_kind": {"$last": "$author_kind"}}},
        {"$project": {"_id": 0, "reverter_key": "$_id.reverter_key",
                      "author_key": "$_id.author_key", "page_id": "$_id.page_id",
                      "count": {"$size": "$actions"}, "n_revisions": 1, "ts": 1, "last_ts": 1,
                      "reverter_kind": 1, "reverter_name": 1, "author_kind": 1}},
    ]


# --------------------------------------------------------------------------
# Pure Python: from pipeline rows to CSV rows (tested in tests/test_neo4j.py)
# --------------------------------------------------------------------------
def page_score(edits: int, revert_actions: int) -> float | None:
    """score = revert_actions / edits, a float; no score when the page has no human edit."""
    return revert_actions / edits if edits > 0 else None


def is_contested(edits: int, revert_actions: int, reverted_editors: int,
                 score: float | None) -> bool:
    """The shared 'contested page' rule (config.py section 4, DATA_MODEL.md section 7)."""
    return (edits >= config.CONTESTED_MIN_EDITS
            and reverted_editors >= config.CONTESTED_MIN_EDITORS
            and revert_actions >= config.CONTESTED_MIN_ACTIONS
            and score is not None and score >= config.CONTESTED_MIN_SCORE)


def build_pages(page_rows: Iterable[dict], link_rows: Iterable[dict]) -> tuple[list[dict], int]:
    """Page rows for pages.csv, sorted by id. Also returns the number of link pages without revisions."""
    links = {int(r["_id"]): r for r in link_rows}
    out, seen = [], set()
    for r in page_rows:
        pid = int(r["_id"])
        seen.add(pid)
        lk = links.get(pid, {})
        edits = int(r["edits"])
        actions = int(lk.get("revert_actions", 0))
        editors = int(lk.get("reverted_editors", 0))
        score = page_score(edits, actions)
        out.append({"id": pid, "title": r.get("title"), "edits": edits,
                    "revert_actions": actions, "reverted_editors": editors, "score": score,
                    "contested": is_contested(edits, actions, editors, score)})
    out.sort(key=lambda p: p["id"])
    return out, len(set(links) - seen)


def build_reverted(rows: Iterable[dict]) -> list[dict]:
    """REVERTED rows, sorted by (reverter_key, author_key, page_id). Keeps the kind/name helpers."""
    out = []
    for r in rows:
        if not r.get("reverter_key") or not r.get("author_key"):
            continue   # null keys get no edge (the pipeline already drops them)
        out.append({"reverter_key": r["reverter_key"], "author_key": r["author_key"],
                    "page_id": int(r["page_id"]), "count": int(r["count"]),
                    "n_revisions": int(r["n_revisions"]), "ts": r["ts"], "last_ts": r["last_ts"],
                    "reverter_kind": r.get("reverter_kind"), "reverter_name": r.get("reverter_name"),
                    "author_kind": r.get("author_kind")})
    out.sort(key=lambda e: (e["reverter_key"], e["author_key"], e["page_id"]))
    return out


def build_edited(rows: Iterable[dict]) -> list[dict]:
    """EDITED rows, sorted by rev_id. A revision without a revert link gets false/false/empty."""
    out = []
    for r in rows:
        if not r.get("editor_key"):
            continue
        rr = r.get("reverting_rev_id")
        out.append({"editor_key": r["editor_key"], "page_id": int(r["page_id"]),
                    "rev_id": int(r["rev_id"]), "ts": r["ts"],
                    "reverted": bool(r.get("reverted")),
                    "reverted_by_other": bool(r.get("reverted_by_other")),
                    "within_followup": bool(r.get("within_followup")),
                    "reverting_rev_id": None if rr is None else int(rr)})
    out.sort(key=lambda e: e["rev_id"])
    return out


def build_editors(editor_rows: Iterable[dict], reverted: list[dict],
                  n_hex: int) -> tuple[list[dict], dict]:
    """Editor rows for editors.csv, sorted by key, and a few counts for the log.

    Every editor has at least one edge: the history authors (EDITED) and the
    reverters of REVERTED rows (a reverter may have no history revision).
    The kind from revisions wins over the kind from revert_links.
    """
    info: dict[str, dict] = {}
    multi_kind = set()
    for r in editor_rows:
        info[r["_id"]] = {"kind": r["kind"], "name": r.get("name"), "edits": int(r["edits"])}
        if len(r.get("kinds") or [r["kind"]]) > 1:
            multi_kind.add(r["_id"])
    made, received = Counter(), Counter()
    reverter_only = set()
    for e in reverted:
        made[e["reverter_key"]] += e["count"]
        received[e["author_key"]] += e["count"]
        for key, kind, name in ((e["reverter_key"], e.get("reverter_kind"), e.get("reverter_name")),
                                (e["author_key"], e.get("author_kind"), None)):
            if key not in info:
                info[key] = {"kind": kind, "name": name, "edits": 0}
                reverter_only.add(key)
            elif kind and info[key]["kind"] != kind:
                multi_kind.add(key)
            if not info[key]["name"] and name:
                info[key]["name"] = name
    out = []
    for key in sorted(info):
        i = info[key]
        out.append({"key": key, "alias": bd.public_name(i["kind"], key, i["name"], n_hex),
                    "kind": i["kind"], "edits": i["edits"], "reverts_made": made[key],
                    "reverts_received": received[key]})
    return out, {"editors_only_as_reverter": len(reverter_only), "editors_with_two_kinds": len(multi_kind)}


def top_contested(pages: list[dict], n: int = config.TOP_N) -> list[dict]:
    """The top-n contested pages from page rows (filter, order and limit of DATA_MODEL.md section 7)."""
    keep = [p for p in pages if p["edits"] >= config.CONTESTED_MIN_EDITS
            and p["reverted_editors"] >= config.CONTESTED_MIN_EDITORS]
    keep.sort(key=lambda p: (-p["score"], -p["revert_actions"], -p["edits"], p["id"]))
    return keep[:n]


def check_graph(g: dict) -> list[dict]:
    """Checks that the four tables fit together. Each check: name, ok, detail."""
    editors = {e["key"] for e in g["editors"]}
    pages = {p["id"]: p for p in g["pages"]}
    aliases = [e["alias"] for e in g["editors"]]
    checks = [
        {"name": "aliases are unique", "ok": len(set(aliases)) == len(aliases)},
        {"name": "every EDITED row has its Editor and Page",
         "ok": all(e["editor_key"] in editors and e["page_id"] in pages for e in g["edited"])},
        {"name": "every REVERTED row has its two Editors and its Page",
         "ok": all(e["reverter_key"] in editors and e["author_key"] in editors
                   and e["page_id"] in pages for e in g["reverted"])},
        {"name": "no REVERTED self-loop", "ok": all(e["reverter_key"] != e["author_key"]
                                                    for e in g["reverted"])},
    ]
    # The comparison query counts from EDITED rows: they must give the Page counts.
    actions, eds, human = defaultdict(set), defaultdict(set), Counter()
    kinds = {e["key"]: e["kind"] for e in g["editors"]}
    for e in g["edited"]:
        if kinds[e["editor_key"]] != "bot":
            human[e["page_id"]] += 1
        if e["within_followup"] and e["reverted_by_other"]:
            actions[e["page_id"]].add(e["reverting_rev_id"])
            eds[e["page_id"]].add(e["editor_key"])
    bad_counts = [pid for pid, p in pages.items()
                  if len(actions[pid]) != p["revert_actions"] or len(eds[pid]) != p["reverted_editors"]]
    checks.append({"name": "EDITED rows give Page.revert_actions and Page.reverted_editors",
                   "ok": not bad_counts, "detail": f"{len(bad_counts)} pages differ"})
    diff_edits = [pid for pid, p in pages.items() if human[pid] != p["edits"]]
    checks.append({"name": "EDITED rows give Page.edits, except pages with unknown editors",
                   "ok": set(diff_edits) <= set(g["stats"]["unknown_editor_pages"]),
                   "detail": f"{len(diff_edits)} pages differ: {diff_edits[:10]}"})
    sum_made = sum(e["reverts_made"] for e in g["editors"])
    sum_recv = sum(e["reverts_received"] for e in g["editors"])
    sum_count = sum(e["count"] for e in g["reverted"])
    checks.append({"name": "sum of reverts_made = sum of reverts_received = sum of REVERTED.count",
                   "ok": sum_made == sum_recv == sum_count, "detail": f"{sum_count:,}"})
    return checks


# --------------------------------------------------------------------------
# CSV writing
# --------------------------------------------------------------------------
def csv_value(v) -> str:
    """One CSV field: true/false, ISO UTC time with Z, full float precision, empty for None."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, datetime):
        if v.tzinfo is None:
            raise ValueError(f"naive datetime {v!r}: all times must be timezone-aware UTC")
        return v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(v, float):
        return repr(v)
    return str(v)


def legacy_escape_risk(text: str) -> bool:
    """True if Neo4j's LOAD CSV could misread this field.

    The Neo4j setting db.import.csv.legacy_quote_escaping (true by default) reads
    backslash + quote as an escaped quote. That breaks a field that contains \\" or
    a quoted field that ends with a backslash.
    """
    needs_quotes = any(c in text for c in ',"\r\n')
    return '\\"' in text or (needs_quotes and text.endswith("\\"))


def csv_text(rows: Iterable[dict], columns: list[str]) -> tuple[str, int]:
    """The whole CSV file as text, and the number of data rows."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(columns)
    n = 0
    for r in rows:
        values = [csv_value(r.get(c)) for c in columns]
        bad = [v for v in values if legacy_escape_risk(v)]
        if bad:
            raise ValueError(f"field that LOAD CSV would misread: {bad[0][:80]!r}")
        w.writerow(values)
        n += 1
    return buf.getvalue(), n


def write_safely(text: str, path: Path) -> None:
    """Write name.tmp, then rename it to the final name."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def write_graph(g: dict, out_dir: Path) -> dict[str, int]:
    counts = {}
    for name, (fname, columns) in FILES.items():
        text, n = csv_text(g[name], columns)
        write_safely(text, out_dir / fname)
        counts[fname] = n
    return counts


# --------------------------------------------------------------------------
# MongoDB
# --------------------------------------------------------------------------
def connect(uri: str = config.MONGO_URI, timeout_ms: int = 5000) -> MongoClient:
    """Connect and ping. Never prints the URI (it can hold a password)."""
    client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms, tz_aware=True)
    client.admin.command("ping")
    return client


def check_inputs(db) -> dict[str, int]:
    """Both collections must exist and hold history documents (load_mongo.py makes them)."""
    names = set(db.list_collection_names())
    counts = {}
    for coll in (config.COL_REVISIONS, config.COL_REVERT_LINKS):
        if coll not in names:
            raise SystemExit(f"MongoDB collection '{coll}' is missing. Run first: "
                             ".venv/bin/python ec-hw2/load_mongo.py --target local")
        counts[coll] = db[coll].count_documents({"cohort": H})
        if counts[coll] == 0:
            raise SystemExit(f"'{coll}' has no history documents. Run load_mongo.py --target local.")
    return counts


def read_graph(db) -> dict:
    """Run the pipelines and build the four tables. Returns a dict with the tables and stats."""
    revs, links = db[config.COL_REVISIONS], db[config.COL_REVERT_LINKS]
    timings = {}

    def agg(coll, name, pipeline):
        t = time.perf_counter()
        rows = list(coll.aggregate(pipeline, allowDiskUse=True))
        timings[name] = round(time.perf_counter() - t, 2)
        return rows

    keys = [r["_id"] for r in agg(revs, "alias_keys", alias_keys_pipeline())]
    n_hex = bd.alias_length(keys)          # the shared rule; it also checks for collisions
    page_rows = agg(revs, "pages", pages_pipeline())
    pages, orphan_link_pages = build_pages(page_rows, agg(links, "page_links", page_links_pipeline()))
    reverted = build_reverted(agg(links, "reverted", reverted_pipeline()))
    editors, editor_stats = build_editors(agg(revs, "editors", editors_pipeline()), reverted, n_hex)
    edited = build_edited(agg(revs, "edited", edited_pipeline()))
    unknown = revs.count_documents({"cohort": H, "user.key": None})
    unknown_pages = sorted({d["page"]["id"] for d in revs.find({"cohort": H, "user.key": None},
                                                               {"page.id": 1})})
    stats = {"alias_keys_both_cohorts": len(keys), "alias_hex_digits": n_hex,
             "skipped_unknown_editor": unknown, "unknown_editor_pages": unknown_pages,
             "link_pages_without_revisions": orphan_link_pages,
             "pages_with_several_titles": sum(int(r.get("n_titles") or 1) > 1 for r in page_rows),
             "contested_pages": sum(p["contested"] for p in pages),
             "bots": sum(e["kind"] == "bot" for e in editors),
             "pipeline_seconds": timings, **editor_stats}
    return {"editors": editors, "pages": pages, "edited": edited, "reverted": reverted,
            "n_hex": n_hex, "stats": stats}


def compare_with_mongo_q2(pages: list[dict], path: Path = MONGO_Q2_FILE) -> dict | None:
    """Early check: the top 20 from pages.csv = results/mongo_q2_top_contested_pages.csv."""
    if not path.exists():
        print(f"  (no {path.name} yet: skipped the Mongo Q2 check)")
        return None
    with open(path, encoding="utf-8") as f:
        mongo = [(int(r["page_id"]), round(float(r["score"]), config.SCORE_ROUND))
                 for r in csv.DictReader(f)]
    ours = [(p["id"], round(p["score"], config.SCORE_ROUND)) for p in top_contested(pages)]
    return {"name": "Page counts give the Mongo Q2 top 20 (page_id, score rounded to 6)",
            "ok": ours == mongo}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Export the history revert graph from MongoDB to CSV.")
    p.add_argument("--out-dir", type=Path, default=config.NEO4J_IMPORT_DIR,
                   help="folder for the CSV files (default: data/neo4j/import)")
    args = p.parse_args(argv)
    t0 = time.time()
    config.ensure_dirs()
    client = connect()
    db = client[config.MONGO_DB]
    inputs = check_inputs(db)
    print(f"MongoDB '{config.MONGO_DB}', history cohort: {inputs[config.COL_REVISIONS]:,} revisions, "
          f"{inputs[config.COL_REVERT_LINKS]:,} revert links")
    g = read_graph(db)
    client.close()
    s = g["stats"]
    print(f"Alias: 'editor_' + {s['alias_hex_digits']} hex digits, from ingest/build_documents.py "
          f"({s['alias_keys_both_cohorts']:,} editor keys in both cohorts)")
    print(f"Pages with more than one page_title in the cohort: {s['pages_with_several_titles']:,} "
          "(Page.title = the title of the newest revision)")
    print(f"Skipped {s['skipped_unknown_editor']} revisions without an editor key "
          f"(pages {s['unknown_editor_pages']})")
    print(f"Editors only seen as reverters: {s['editors_only_as_reverter']:,}; "
          f"editors with two kinds: {s['editors_with_two_kinds']}; bots: {s['bots']}")
    print(f"Contested pages: {s['contested_pages']:,}")

    checks = check_graph(g)
    mq2 = compare_with_mongo_q2(g["pages"])
    if mq2:
        checks.append(mq2)
    for c in checks:
        print(f"  check: {c['name']}: {'OK' if c['ok'] else 'DIFFERENT'}"
              + (f" ({c['detail']})" if c.get("detail") else ""))
    hard = [c for c in checks[:4] if not c["ok"]]
    if hard:
        print("ERROR: the graph tables do not fit together; nothing written.")
        return 1

    counts = write_graph(g, args.out_dir)
    for fname, n in counts.items():
        print(f"  wrote {args.out_dir / fname}: {n:,} rows")
    success = {"step": "export_graph", "data_version": config.DATA_VERSION,
               "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "source": f"MongoDB {config.MONGO_DB} (history cohort)",
               "rows": counts, "stats": s, "checks": checks,
               "seconds": round(time.time() - t0, 1)}
    write_safely(json.dumps(success, indent=2, default=str) + "\n", args.out_dir / SUCCESS_NAME)
    print(f"Done in {time.time() - t0:.1f} s. Next: .venv/bin/python ec-hw2/load_neo4j.py --target local")
    return 0 if all(c["ok"] for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
