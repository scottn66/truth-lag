"""Sharding demo: spread the history cohort over 2 shards with {"page.id": "hashed"}.

Purpose
    Show how a hashed shard key splits the revisions between 2 shards, and which
    queries use one shard and which use both. The steps:
      1. Connect to the sharded cluster (config.SHARDED_URI, a mongos router).
         Drop and recreate the database truthlag_sharded.
      2. Shard the EMPTY collection truthlag_sharded.revisions on {"page.id": "hashed"}.
         This is the same as sh.shardCollection('truthlag_sharded.revisions',
         {'page.id': 'hashed'}) in mongosh.
      3. Copy the history-cohort documents from the local MongoDB, in batches of
         5,000. Then create the same indexes as the local collection.
      4. Record the data spread ($shardedDataDistribution, $collStats, chunks per
         shard) and the explain() output of 5 queries: SINGLE_SHARD or SHARD_MERGE,
         and the shards each query used.
      5. Check the results against the local (not sharded) database, then write
         results/sharding.md.
    It only READS the local database. It is safe to re-run: step 1 starts from an
    empty database every time.

Inputs
    Local MongoDB (config.MONGO_URI, database config.MONGO_DB), collection revisions,
    the documents with cohort "history".
    The sharded cluster of ec-hw2/scaleout/docker-compose.sharded.yml, set up by
    ec-hw2/scaleout/init_sharded.sh.

Outputs
    The database truthlag_sharded on the sharded cluster.
    ec-hw2/results/sharding.md and ec-hw2/results/_SUCCESS_sharding.json.
    With --limit, the output goes to data/logs/sharding_test.md instead (or --out).

Run (from the repo root; SHARDING.md has every step with what you should see)
    docker stop truthlag-neo4j-1
    docker compose -f ec-hw2/scaleout/docker-compose.sharded.yml up -d
    bash ec-hw2/scaleout/init_sharded.sh
    .venv/bin/python ec-hw2/scaleout/demo_sharding.py
    docker start truthlag-neo4j-1
    docker compose -f ec-hw2/scaleout/docker-compose.sharded.yml stop
    A quick test with fewer documents:
    .venv/bin/python ec-hw2/scaleout/demo_sharding.py --limit 20000
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pymongo.errors import OperationFailure, PyMongoError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import load_mongo  # noqa: E402  (connect, insert_batches, REVISION_INDEXES)
from ingest import build_documents as bd  # noqa: E402  (write_success)

SHARDED_DB = "truthlag_sharded"
COLL = config.COL_REVISIONS
NAMESPACE = f"{SHARDED_DB}.{COLL}"
SHARD_KEY = {"page.id": "hashed"}
BATCH = 5_000
STEP = "sharding"
NEO4J_CONTAINER = "truthlag-neo4j-1"
EVEN_SPREAD = (0.45, 0.55)     # each of the 2 shards should own 45-55% of the documents
PAGE_RANGE = (1_000_000, 2_000_000)   # a page.id range for the range-query example
DEFAULT_OUT = config.RESULTS_DIR / "sharding.md"
TEST_OUT = config.DATA_DIR / "logs" / "sharding_test.md"
HIDDEN = "<hidden>"


# --------------------------------------------------------------------------
# Reading explain() output (pure functions, tested in tests/test_scaleout.py)
# --------------------------------------------------------------------------
def plan_stages(plan) -> list[str]:
    """Stage names of one shard's plan, from the top down, e.g. ['FETCH', 'IXSCAN'].

    MongoDB 8.0 can put the plan under 'queryPlan' (slot-based engine) and can have
    several children ('inputStages'); those are joined with '+'.
    """
    out: list[str] = []
    node = plan
    while isinstance(node, dict):
        if "queryPlan" in node and "stage" not in node:
            node = node["queryPlan"]
            continue
        if "stage" in node:
            out.append(node["stage"])
        if "inputStage" in node:
            node = node["inputStage"]
        elif "inputStages" in node:
            parts = [" > ".join(plan_stages(child)) for child in node["inputStages"]]
            out.append("(" + " + ".join(parts) + ")")
            break
        else:
            break
    return out


def plan_index(plan) -> str | None:
    """The first index name used in a plan (None for a collection scan)."""
    if isinstance(plan, dict):
        if plan.get("indexName"):
            return plan["indexName"]
        for key in ("queryPlan", "inputStage"):
            found = plan_index(plan.get(key))
            if found:
                return found
        for child in plan.get("inputStages", []):
            found = plan_index(child)
            if found:
                return found
    return None


def summarize_find_explain(exp: dict) -> dict:
    """The routing facts of a find() explain from mongos (verbosity executionStats).

    stage = SINGLE_SHARD (one shard was asked) or SHARD_MERGE (several shards were
    asked and mongos merged their answers).
    """
    wp = exp["queryPlanner"]["winningPlan"]
    plans = {s["shardName"]: s.get("winningPlan", {}) for s in wp.get("shards", [])}
    ex = exp.get("executionStats", {})
    per_shard = []
    for s in ex.get("executionStages", {}).get("shards", []):
        name = s["shardName"]
        per_shard.append({
            "shard": name,
            "n_returned": s.get("nReturned", 0),
            "docs_examined": s.get("totalDocsExamined", 0),
            "keys_examined": s.get("totalKeysExamined", 0),
            "plan": " > ".join(plan_stages(plans.get(name, {}))),
            "index": plan_index(plans.get(name, {})),
        })
    if not per_shard:   # verbosity queryPlanner: no execution numbers
        per_shard = [{"shard": n, "plan": " > ".join(plan_stages(p)), "index": plan_index(p)}
                     for n, p in plans.items()]
    return {"stage": wp.get("stage"), "shards": sorted(plans), "n_shards": len(plans),
            "n_returned": ex.get("nReturned"), "per_shard": sorted(per_shard,
                                                                   key=lambda r: r["shard"])}


def _stage_names(stages) -> list[str]:
    return [next(iter(s)) for s in (stages or []) if isinstance(s, dict) and s]


def _cursor_stats(shard_part: dict) -> dict:
    """executionStats of the shard's query: in the first $cursor stage, or at the top
    when the whole pipeline was pushed down into the query layer."""
    stages = shard_part.get("stages")
    if stages and "$cursor" in stages[0]:
        return stages[0]["$cursor"].get("executionStats", {})
    return shard_part.get("executionStats", {})


def summarize_agg_explain(exp: dict) -> dict:
    """The routing facts of an aggregate explain from mongos.

    shards = the shards that ran a part of the pipeline. shards_part = the stages
    each shard ran; merger_part = the stages that merged the shards' answers
    (empty when one shard did everything). merge_type says where the merge ran.
    """
    shards = exp.get("shards", {})
    split = exp.get("splitPipeline") or {}
    per_shard = []
    for name, part in sorted(shards.items()):
        stats = _cursor_stats(part)
        stages = _stage_names(part.get("stages"))
        if not stages:   # pushed down: the plan shows e.g. GROUP > COLLSCAN
            stages = plan_stages(part.get("queryPlanner", {}).get("winningPlan", {}))
        plan = part.get("queryPlanner", {}).get("winningPlan", {})
        if not plan and part.get("stages"):
            plan = part["stages"][0].get("$cursor", {}).get("queryPlanner", {}).get(
                "winningPlan", {})
        per_shard.append({"shard": name, "stages": stages,
                          "plan": " > ".join(plan_stages(plan)), "index": plan_index(plan),
                          "n_returned": stats.get("nReturned"),
                          "docs_examined": stats.get("totalDocsExamined")})
    return {"merge_type": exp.get("mergeType"), "shards": sorted(shards),
            "n_shards": len(shards),
            "shards_part": _stage_names(split.get("shardsPart")),
            "merger_part": _stage_names(split.get("mergerPart")),
            "per_shard": per_shard}


def routing_label(summary: dict) -> str:
    """One short label for the results table."""
    if "stage" in summary:
        return summary["stage"] or "?"
    if summary["n_shards"] == 1:
        return "one shard (no merge)"
    return f"both shards, merged by {summary.get('merge_type') or '?'}"


# --------------------------------------------------------------------------
# Talking to the databases
# --------------------------------------------------------------------------
def warn_if_neo4j_running() -> None:
    """The memory rule: Neo4j should be stopped while the sharded cluster runs."""
    try:
        out = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", NEO4J_CONTAINER],
                             capture_output=True, text=True, check=False).stdout.strip()
    except (FileNotFoundError, OSError):
        return
    if out == "true":
        print(f"WARNING: {NEO4J_CONTAINER} is running. Stop it first to save memory: "
              f"docker stop {NEO4J_CONTAINER}")


def connect_mongos():
    """Connect to config.SHARDED_URI and check that it is a mongos with 2+ shards."""
    try:
        client = load_mongo.connect(config.SHARDED_URI, 5000)
    except PyMongoError as e:
        raise SystemExit(f"STOP: cannot reach the sharded cluster at config.SHARDED_URI "
                         f"({type(e).__name__}). Start it and run init_sharded.sh first.")
    hello = client.admin.command("hello")
    if hello.get("msg") != "isdbgrid":
        # A safety stop: this script drops a database, so it must never run on a normal mongod.
        raise SystemExit("STOP: config.SHARDED_URI is not a mongos router. Nothing changed.")
    shards = client.admin.command("listShards").get("shards", [])
    if len(shards) < 2:
        raise SystemExit(f"STOP: the cluster has {len(shards)} shard(s), it needs 2. "
                         "Run: bash ec-hw2/scaleout/init_sharded.sh")
    return client, [{"id": s["_id"], "host": s["host"]} for s in shards]


def reset_database(client) -> None:
    """Drop and recreate the demo database, then shard the empty collection."""
    client.drop_database(SHARDED_DB)
    try:
        client.admin.command("enableSharding", SHARDED_DB)
    except OperationFailure as e:   # MongoDB 8.0 does not need it; older versions do
        print(f"enableSharding: {(e.details or {}).get('codeName') or e}")
    # Shard the EMPTY collection: MongoDB makes the hashed chunks on both shards
    # first, so every document goes straight to its shard and no chunk moves later.
    client.admin.command("shardCollection", NAMESPACE, key=SHARD_KEY)


def copy_history(src_db, dst_db, limit: int | None, batch: int = BATCH) -> tuple[int, float]:
    """Copy the history cohort in batches. Returns (documents, seconds)."""
    cursor = src_db[COLL].find({"cohort": config.COHORT_HISTORY}, batch_size=batch)
    if limit:
        cursor = cursor.limit(limit)
    t = time.time()
    n = load_mongo.insert_batches(dst_db[COLL], cursor, batch)
    return n, time.time() - t


def create_indexes(db) -> list[str]:
    """The same revisions indexes as the local database (DATA_MODEL.md section 4).

    Returns every index name, also _id_ and page.id_hashed (shardCollection made that one).
    """
    for keys in load_mongo.REVISION_INDEXES:
        db[COLL].create_index(keys)
    return list(db[COLL].index_information())


def data_distribution(client) -> list[dict]:
    rows = list(client.admin.aggregate([{"$shardedDataDistribution": {}},
                                        {"$match": {"ns": NAMESPACE}}]))
    out = []
    for s in (rows[0]["shards"] if rows else []):
        out.append({"shard": s["shardName"], "owned_docs": s.get("numOwnedDocuments", 0),
                    "owned_mb": round(s.get("ownedSizeBytes", 0) / 1024 / 1024, 2),
                    "orphaned_docs": s.get("numOrphanedDocs", 0)})
    return sorted(out, key=lambda r: r["shard"])


def collection_stats(db) -> list[dict]:
    out = []
    for s in db[COLL].aggregate([{"$collStats": {"storageStats": {}}}]):
        st = s.get("storageStats", {})
        out.append({"shard": s.get("shard"), "count": st.get("count", 0),
                    "data_mb": round(st.get("size", 0) / 1024 / 1024, 2),
                    "storage_mb": round(st.get("storageSize", 0) / 1024 / 1024, 2),
                    "index_mb": round(st.get("totalIndexSize", 0) / 1024 / 1024, 2)})
    return sorted(out, key=lambda r: r["shard"] or "")


def chunks_per_shard(client) -> dict[str, int]:
    meta = client.config.collections.find_one({"_id": NAMESPACE})
    if not meta:
        return {}
    rows = client.config.chunks.aggregate([{"$match": {"uuid": meta["uuid"]}},
                                           {"$group": {"_id": "$shard", "n": {"$sum": 1}}}])
    return {r["_id"]: r["n"] for r in rows}


def pick_examples(db) -> dict:
    """The page with the most revisions, and the bot with the most revisions.

    Bots keep their real names. If there is no bot, a human is used and the name
    and id are hidden (they never go into the results).
    """
    page = next(db[COLL].aggregate([
        {"$group": {"_id": "$page.id", "n": {"$sum": 1}, "title": {"$first": "$page.title"}}},
        {"$sort": {"n": -1, "_id": 1}}, {"$limit": 1}]))
    user = None
    for match in ({"user.kind": "bot", "user.id": {"$ne": None}}, {"user.id": {"$ne": None}}):
        user = next(db[COLL].aggregate([
            {"$match": match},
            {"$group": {"_id": "$user.id", "n": {"$sum": 1}, "name": {"$first": "$user.name"},
                        "kind": {"$first": "$user.kind"}}},
            {"$sort": {"n": -1, "_id": 1}}, {"$limit": 1}]), None)
        if user:
            break
    return {"page": {"id": page["_id"], "title": page["title"], "revisions": page["n"]},
            "user": example_user(user)}


def example_user(row: dict) -> dict:
    """How the editor example is shown: a bot by its real name and id; a human never
    (DATA_MODEL.md: human editors appear only as pseudonyms in committed results)."""
    is_bot = row["kind"] == "bot"
    return {"id": row["_id"], "kind": row["kind"], "revisions": row["n"],
            "shown_id": row["_id"] if is_bot else HIDDEN,
            "shown_as": f"the bot {row['name']}" if is_bot else
                        "a human editor (name and id hidden)"}


def explain_find(db, filt: dict, sort: dict | None = None) -> dict:
    cmd = {"find": COLL, "filter": filt}
    if sort:
        cmd["sort"] = sort
    return db.command({"explain": cmd, "verbosity": "executionStats"})


def explain_aggregate(db, pipeline: list) -> dict:
    return db.command({"explain": {"aggregate": COLL, "pipeline": pipeline, "cursor": {}},
                       "verbosity": "executionStats"})


def hour_pipeline() -> list:
    """Revert rate by hour of day (like Mongo Q1, history cohort only)."""
    return [{"$match": {"cohort": config.COHORT_HISTORY}},
            {"$group": {"_id": "$hour_utc", "edits": {"$sum": 1},
                        "reverted": {"$sum": {"$cond": ["$history.reverted", 1, 0]}}}},
            {"$sort": {"_id": 1}}]


def pages_pipeline() -> list:
    """The 20 pages with the most revisions (a ranking over all pages, like Mongo Q2)."""
    return [{"$group": {"_id": "$page.id", "n": {"$sum": 1}}},
            {"$sort": {"n": -1, "_id": 1}}, {"$limit": config.TOP_N}]


def run_queries(db, ex: dict) -> list[dict]:
    """explain() of the 5 example queries, with the routing we expect for each."""
    page_id, user_id = ex["page"]["id"], ex["user"]["id"]
    lo, hi = PAGE_RANGE
    out = []

    def add(name, code, expect, summary, ok):
        out.append({"name": name, "code": code, "expect": expect, "summary": summary,
                    "label": routing_label(summary), "ok": ok})

    s = summarize_find_explain(explain_find(db, {"page.id": page_id}, {"ts": 1}))
    add("history of one page",
        f'db.revisions.find({{"page.id": {page_id}}}).sort({{ts: 1}})',
        "SINGLE_SHARD", s, s["stage"] == "SINGLE_SHARD" and s["n_shards"] == 1)
    s = summarize_find_explain(explain_find(db, {"user.id": user_id}))
    add("all edits of one editor",
        f'db.revisions.find({{"user.id": {ex["user"]["shown_id"]}}})',
        "SHARD_MERGE", s, s["stage"] == "SHARD_MERGE" and s["n_shards"] == 2)
    s = summarize_find_explain(explain_find(db, {"page.id": {"$gte": lo, "$lt": hi}}))
    add("a range of page ids",
        f'db.revisions.find({{"page.id": {{$gte: {lo}, $lt: {hi}}}}})',
        "SHARD_MERGE", s, s["stage"] == "SHARD_MERGE" and s["n_shards"] == 2)
    s = summarize_agg_explain(explain_aggregate(db, hour_pipeline()))
    s["n_returned"] = len(list(db[COLL].aggregate(hour_pipeline())))   # rows in the answer
    add("revert rate by hour of day",
        'db.revisions.aggregate([{$match: {cohort: "history"}}, {$group: {_id: "$hour_utc", '
        'edits: {$sum: 1}, reverted: {$sum: {$cond: ["$history.reverted", 1, 0]}}}}, '
        '{$sort: {_id: 1}}])',
        "both shards", s, s["n_shards"] == 2)
    s = summarize_agg_explain(explain_aggregate(db, pages_pipeline()))
    s["n_returned"] = len(list(db[COLL].aggregate(pages_pipeline())))
    add("the 20 pages with the most revisions",
        'db.revisions.aggregate([{$group: {_id: "$page.id", n: {$sum: 1}}}, '
        f'{{$sort: {{n: -1, _id: 1}}}}, {{$limit: {config.TOP_N}}}])',
        "both shards", s, s["n_shards"] == 2)
    return out


# --------------------------------------------------------------------------
# Checks against the local (not sharded) database
# --------------------------------------------------------------------------
def run_checks(res: dict, src_db, dst_db) -> list[dict]:
    checks = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    n_src, n_dst = res["source_count"], dst_db[COLL].count_documents({})
    check("every copied document is in the sharded collection", n_src == n_dst,
          f"{n_dst:,} in the sharded collection, {n_src:,} read from the local database")
    dist = res["distribution"]
    owned = sum(r["owned_docs"] for r in dist)
    check("the shards own all documents ($shardedDataDistribution)", owned == n_dst,
          f"{owned:,} owned")
    orphans = sum(r["orphaned_docs"] for r in dist)
    check("no orphaned documents (no chunk moved during the load)", orphans == 0,
          f"{orphans:,} orphaned")
    if n_dst:
        shares = [r["owned_docs"] / n_dst for r in dist]
        lo, hi = EVEN_SPREAD
        check(f"even spread: each shard owns {lo:.0%}-{hi:.0%} of the documents",
              len(shares) == 2 and all(lo <= x <= hi for x in shares),
              ", ".join(f"{r['shard']} {x:.2%}" for r, x in zip(dist, shares)))
    for q in res["queries"]:
        check(f"routing of '{q['name']}' is {q['expect']}", q["ok"], q["label"])
    top = next((r for r in res["queries"] if r["name"] == "the 20 pages with the most revisions"),
               None)
    if top:
        partial = sum(p.get("n_returned") or 0 for p in top["summary"]["per_shard"])
        check("every page is on one shard only (partial rows of the top-pages query "
              "= distinct pages)", partial == res["distinct_pages"],
              f"{partial:,} partial rows, {res['distinct_pages']:,} distinct pages")
    page_id = res["examples"]["page"]["id"]
    if res["limit"] is None:
        a = src_db[COLL].count_documents({"cohort": config.COHORT_HISTORY, "page.id": page_id})
        b = dst_db[COLL].count_documents({"page.id": page_id})
        check("page history: same number of revisions as the local database", a == b,
              f"{b} sharded, {a} local")
        local = list(src_db[COLL].aggregate(hour_pipeline()))
        sharded = list(dst_db[COLL].aggregate(hour_pipeline()))
        check("revert rate by hour: the same 24 rows as the local database",
              local == sharded and len(local) == 24, f"{len(sharded)} rows")
    return checks


# --------------------------------------------------------------------------
# The results page
# --------------------------------------------------------------------------
def _n(x) -> str:
    return "" if x is None else f"{x:,}"


def render_markdown(res: dict) -> str:
    """results/sharding.md in plain English, with the numbers and the explain stages."""
    ex, dist = res["examples"], res["distribution"]
    total = sum(r["owned_docs"] for r in dist) or 1
    stats = {r["shard"]: r for r in res["collstats"]}
    q = {r["name"]: r for r in res["queries"]}
    L = []
    L.append("# Sharding demo: results")
    L.append("")
    L.append(f"Made by `ec-hw2/scaleout/demo_sharding.py` on {res['created_at_text']} "
             f"({res['data_version']}). MongoDB {res['mongo_version']}.")
    if res["limit"]:
        L.append("")
        L.append(f"**TEST RUN: only the first {res['limit']:,} history documents were copied.**")
    L.append("")
    L.append("All 4 servers run in Docker on one Mac. So the times here say nothing about "
             "real speed. The demo shows **how** MongoDB splits the data and the queries. "
             "SHARDING.md explains why we chose this shard key.")
    L.append("")
    L.append("## 1. The cluster")
    L.append("")
    L.append("| part | what it is |")
    L.append("|---|---|")
    L.append("| config server | replica set `cfgrs`, 1 member (`cfg:27019`) |")
    for s in res["shards"]:
        L.append(f"| shard `{s['id']}` | `{s['host']}`, 1 member |")
    L.append("| router | `mongos`, published on the Mac as `127.0.0.1:27020` |")
    L.append("")
    L.append(f"- Collection: `{NAMESPACE}`.")
    L.append(f"- Shard key: `{json.dumps(SHARD_KEY)}`.")
    L.append("- We sharded the collection while it was still **empty**. MongoDB then made "
             "the chunks on both shards first, and every document went straight to its shard.")
    L.append("")
    L.append("## 2. The data spread")
    L.append("")
    L.append(f"We copied **{res['copied']:,}** history-cohort documents from the local MongoDB "
             f"(database `{config.MONGO_DB}`, collection `{COLL}`) in batches of "
             f"{res['batch']:,}. The copy took {res['copy_seconds']:.1f} seconds "
             f"(about {res['copied'] / max(res['copy_seconds'], 1e-9):,.0f} documents per "
             "second). Then we built the same 4 indexes as the local collection. The "
             f"collection now has these indexes: {', '.join(f'`{i}`' for i in res['indexes'])} "
             "(shardCollection made `page.id_hashed`).")
    L.append("")
    L.append("| shard | documents | share | data (MB) | indexes (MB) | chunks | orphaned documents |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in dist:
        st = stats.get(r["shard"], {})
        L.append(f"| `{r['shard']}` | {r['owned_docs']:,} | {r['owned_docs'] / total:.2%} | "
                 f"{st.get('data_mb', 0):.1f} | {st.get('index_mb', 0):.1f} | "
                 f"{res['chunks'].get(r['shard'], 0)} | {r['orphaned_docs']:,} |")
    L.append("")
    L.append("Sources: documents and orphaned documents from `$shardedDataDistribution`; "
             "MB from `$collStats` (data = uncompressed BSON); chunks from `config.chunks`.")
    L.append("")
    L.append("## 3. Which shards a query uses")
    L.append("")
    L.append(f"- The page example is **{ex['page']['title']}** (page id {ex['page']['id']}), "
             f"the page with the most revisions: {ex['page']['revisions']:,}.")
    L.append(f"- The editor example is {ex['user']['shown_as']}, with "
             f"{ex['user']['revisions']:,} revisions.")
    L.append("")
    L.append("| query | explain shows | shards used | documents read, per shard | "
             "rows each shard sent to mongos | rows in the answer |")
    L.append("|---|---|---|---|---|---:|")
    for r in res["queries"]:
        s = r["summary"]
        read = ", ".join(f"{p['shard']}: {_n(p.get('docs_examined'))}" for p in s["per_shard"])
        sent = ", ".join(f"{p['shard']}: {_n(p.get('n_returned'))}" for p in s["per_shard"])
        answer = s.get("n_returned")
        label = f"`{r['label']}`" if "stage" in s else r["label"]
        L.append(f"| {r['name']} | {label} | {', '.join(s['shards'])} | {read} | "
                 f"{sent} | {_n(answer)} |")
    L.append("")
    L.append("\"Documents read\" is totalDocsExamined from explain('executionStats'). For a "
             "group-by, each shard sends one partial row per group to mongos.")
    L.append("")
    L.append("The queries, as you would type them in mongosh, and what explain() shows:")
    L.append("")
    for i, r in enumerate(res["queries"], start=1):
        s = r["summary"]
        L.append(f"{i}. **{r['name'].capitalize()}**: `{r['code']}`")
        plans = "; ".join(f"`{p['shard']}`: {p['plan']}"
                          + (f" (index `{p['index']}`)" if p.get("index") else "")
                          for p in s["per_shard"])
        if "stage" in s:
            L.append(f"   - Top stage `{s['stage']}`. The plan on each shard: {plans}.")
        else:
            L.append(f"   - mergeType `{s['merge_type']}`. Shard part of the pipeline: "
                     f"`{', '.join(s['shards_part']) or '(all of it)'}`. Merge part: "
                     f"`{', '.join(s['merger_part']) or '(none)'}`.")
            L.append(f"   - The plan on each shard: {plans}.")
    L.append("")
    L.append("## 4. Checks")
    L.append("")
    for c in res["checks"]:
        L.append(f"- {'OK' if c['ok'] else 'DIFFERENT'}: {c['name']} ({c['detail']}).")
    L.append("")
    L.append("## 5. What this shows")
    L.append("")
    shares = [f"{r['owned_docs'] / total:.2%}" for r in dist]
    big = ex["page"]["revisions"] / total
    L.append(f"1. Hashing `page.id` spreads the documents: {' and '.join(shares)}. "
             f"There are {res['distinct_pages']:,} distinct pages. The biggest page has "
             f"{ex['page']['revisions']:,} revisions ({big:.2%} of all documents), so no "
             "single page can make one shard much bigger than the other.")

    def said(name, claim):
        r = q[name]
        if r["ok"]:
            return claim
        return (f"We expected {r['expect']} for '{name}', but explain() shows "
                f"`{r['label']}`. Check this before you use the result.")

    page_q = q["history of one page"]["summary"]
    L.append("2. " + said("history of one page",
             f"A query for one page goes to **one shard** (`{page_q['stage']}`, "
             f"`{', '.join(page_q['shards'])}`), and that shard reads only the "
             f"{_n(page_q['n_returned'])} documents of the page. The history of a page and the "
             "score of one contested page work this way."))
    user_q = q["all edits of one editor"]["summary"]
    range_q = q["a range of page ids"]["summary"]
    L.append("3. " + said("all edits of one editor",
             f"A query for one editor goes to **both shards** (`{user_q['stage']}`). An "
             "editor edits many pages, and the pages are on both shards.") + " "
             + said("a range of page ids",
                    f"A range of page ids also goes to both shards (`{range_q['stage']}`), "
                    "because hashing mixes up the order of the ids."))
    top_q = q["the 20 pages with the most revisions"]["summary"]
    partial = sum(p.get("n_returned") or 0 for p in top_q["per_shard"])
    merge_groups = "$group" in top_q["merger_part"]
    L.append("4. " + said("the 20 pages with the most revisions",
             "A group-by over all documents (by hour, or the top pages) runs on both "
             "shards. Each shard groups its own documents, then mongos merges the partial "
             f"rows. For the top-20 pages, the shards sent "
             f"{' + '.join(_n(p.get('n_returned')) for p in top_q['per_shard'])} = "
             f"{partial:,} partial rows to mongos, and mongos kept 20.")
             + (f" {partial:,} is also the number of distinct pages, so no page is split "
                "over the 2 shards." if partial == res["distinct_pages"] else "")
             + (" Even so, mongos runs a `$group` again in the merge part: MongoDB does not "
                "use the fact that each page is on one shard." if merge_groups else ""))
    L.append("")
    L.append("## How to run it again")
    L.append("")
    L.append("See `ec-hw2/scaleout/SHARDING.md`, section \"Run the demo\". The script drops "
             "and rebuilds `truthlag_sharded` every time, so a re-run gives the same numbers "
             "(only the times change).")
    L.append("")
    return "\n".join(L)


def write_text_safely(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main(argv=None) -> dict:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--limit", type=int, default=None,
                   help="copy only this many history documents (a quick test)")
    p.add_argument("--batch-size", type=int, default=BATCH)
    p.add_argument("--out", type=Path, default=None,
                   help=f"where to write the results page (default {DEFAULT_OUT}; "
                        f"with --limit: {TEST_OUT})")
    args = p.parse_args(argv)
    out = args.out or (TEST_OUT if args.limit else DEFAULT_OUT)

    warn_if_neo4j_running()
    client, shards = connect_mongos()
    print(f"connected to mongos; shards: {', '.join(s['id'] for s in shards)}")
    src_db = load_mongo.connect(config.MONGO_URI)[config.MONGO_DB]
    dst_db = client[SHARDED_DB]

    t0 = time.time()
    reset_database(client)
    print(f"step 1-2: dropped {SHARDED_DB}; sharded {NAMESPACE} on {json.dumps(SHARD_KEY)}")
    print(f"chunks right after sharding the empty collection: {chunks_per_shard(client)}")

    n, secs = copy_history(src_db, dst_db, args.limit, args.batch_size)
    print(f"step 3: copied {n:,} history documents in {secs:.1f} s")
    t = time.time()
    names = create_indexes(dst_db)
    print(f"indexes ({time.time() - t:.1f} s): {', '.join(names)}")
    source_count = (src_db[COLL].count_documents({"cohort": config.COHORT_HISTORY})
                    if args.limit is None else n)

    res = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_version": config.DATA_VERSION,
        "mongo_version": client.server_info().get("version"),
        "shards": shards, "limit": args.limit, "batch": args.batch_size,
        "copied": n, "copy_seconds": secs, "source_count": source_count,
        "indexes": names,
    }
    res["created_at_text"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    res["distribution"] = data_distribution(client)
    res["collstats"] = collection_stats(dst_db)
    res["chunks"] = chunks_per_shard(client)
    res["distinct_pages"] = next(dst_db[COLL].aggregate(
        [{"$group": {"_id": "$page.id"}}, {"$count": "n"}]), {"n": 0})["n"]
    print("step 4: distribution", res["distribution"])
    print("        chunks", res["chunks"])
    res["examples"] = pick_examples(dst_db)
    res["queries"] = run_queries(dst_db, res["examples"])
    for r in res["queries"]:
        print(f"        {r['name']}: {r['label']} on {', '.join(r['summary']['shards'])}")
    res["checks"] = run_checks(res, src_db, dst_db)
    for c in res["checks"]:
        print(f"check: {'OK' if c['ok'] else 'DIFFERENT'}: {c['name']} ({c['detail']})")

    write_text_safely(out, render_markdown(res))
    rows = {"documents_copied": n,
            **{f"documents_{r['shard']}": r["owned_docs"] for r in res["distribution"]},
            "queries_explained": len(res["queries"])}
    extra = {"output": str(out.relative_to(config.REPO_ROOT)) if out.is_relative_to(config.REPO_ROOT)
             else out.name,
             "limit": args.limit, "chunks": res["chunks"],
             "routing": {r["name"]: r["label"] for r in res["queries"]},
             "checks": [{"name": c["name"], "ok": c["ok"]} for c in res["checks"]],
             "seconds": round(time.time() - t0, 1)}
    bd.write_success(STEP, rows, out.parent, extra)
    print(f"step 5: wrote {out} and {out.parent / f'_SUCCESS_{STEP}.json'} "
          f"in {time.time() - t0:.1f} s")
    if not all(c["ok"] for c in res["checks"]):
        print("WARNING: some checks are DIFFERENT; see the results page.")
    return res


if __name__ == "__main__":
    main()
