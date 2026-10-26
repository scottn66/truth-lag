"""Load the cohort tables into MongoDB: the local database, Atlas, or the sharded demo.

Purpose
    --target local    Drop and reload the collections revisions, revert_links,
                      tag_events (mw-reverted additions only) and late_reverts in the
                      local database (config.MONGO_URI, config.MONGO_DB). Then create
                      the indexes. Documents come from ingest/build_documents.py and
                      are inserted with insert_many, 5,000 at a time (ordered=False).
    --target atlas    The Atlas free tier copy: the history documents WITHOUT comment,
                      the history revert_links, and the chart collections (copied from
                      the local database; run queries/run_mongo.py first). Before it
                      loads, it estimates the size and refuses if the estimate is over
                      config.ATLAS_BUDGET_MB. Needs --confirm-overwrite, because it
                      replaces what is on Atlas (without it, the script stops before it
                      reads or connects to anything). --estimate-only prints the estimate
                      and does not connect to Atlas. Every human editor on Atlas is a
                      pseudonym made with the shared rule of ingest/build_documents.py
                      (HMAC-SHA256 with config.ALIAS_SECRET), so Atlas shows the same
                      aliases as the local results.
    --target sharded  Only checks the connection to the sharded demo cluster
                      (config.SHARDED_URI). The scale-out part copies the data.
    page_hour is not loaded here: speed_layer.py builds it.

Inputs
    data/tables/*.parquet and data/parsed/tag_events.parquet (see ingest/build_documents.py),
    and their _SUCCESS_*.json files. ec-hw2/.env for the connection strings.

Outputs
    MongoDB collections (see DATA_MODEL.md section 4).
    data/tables/_SUCCESS_mongo_local.json (or _SUCCESS_mongo_atlas.json) with the counts.

Run (from the repo root)
    .venv/bin/python ec-hw2/load_mongo.py --target local
    .venv/bin/python ec-hw2/load_mongo.py --target atlas --estimate-only
    .venv/bin/python ec-hw2/load_mongo.py --target atlas --confirm-overwrite
    .venv/bin/python ec-hw2/load_mongo.py --target sharded
"""
from __future__ import annotations

import argparse
import itertools
import sys
import time
from pathlib import Path
from typing import Iterable

import bson
from pymongo import MongoClient
from pymongo.errors import BulkWriteError, PyMongoError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from ingest import build_documents as bd  # noqa: E402

INSERT_BATCH = 5_000

# DATA_MODEL.md section 4. The first three are the spec's indexes.
REVISION_INDEXES = [
    [("page.id", 1), ("ts", 1)],
    [("user.id", 1)],
    [("history.reverted", 1)],
    [("cohort", 1), ("ts", 1)],
]
# reverted_rev_id: the equality $lookup of Mongo Q1 and Q5.
# page_id: the self-$lookup of compare_mutual_reverts (without it, every lookup reads
# the whole collection).
# cohort + page_id: the history-only queries (Mongo Q2, Q4 and the comparison queries)
# start with {cohort: "history"}, so they do not scan the live documents.
REVERT_LINK_INDEXES = [
    [("reverted_rev_id", 1)],
    [("page_id", 1)],
    [("cohort", 1), ("page_id", 1)],
]
LOCAL_COLLECTIONS = [config.COL_REVISIONS, config.COL_REVERT_LINKS,
                     config.COL_TAG_EVENTS, config.COL_LATE_REVERTS]
SAMPLE_EVERY = 100        # size estimate: one document in 100 is encoded and measured
INDEX_ENTRY_OVERHEAD = 16  # bytes per index entry on top of the key (record id + slack)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def connect(uri: str, timeout_ms: int = 5000) -> MongoClient:
    """Connect and ping. Never prints the URI (it can hold a password)."""
    client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms, tz_aware=True)
    client.admin.command("ping")
    return client


def insert_batches(coll, docs: Iterable[dict], batch_size: int = INSERT_BATCH) -> int:
    """insert_many in batches (ordered=False, so one bad document does not stop the rest)."""
    n = 0
    it = iter(docs)
    while True:
        batch = list(itertools.islice(it, batch_size))
        if not batch:
            return n
        try:
            res = coll.insert_many(batch, ordered=False)
            n += len(res.inserted_ids)
        except BulkWriteError as e:
            errs = e.details.get("writeErrors", [])
            n += e.details.get("nInserted", 0)
            first = errs[0]["errmsg"] if errs else str(e)
            raise SystemExit(f"STOP: {len(errs)} insert errors in {coll.name}; first: {first}")


def create_indexes(db) -> list[str]:
    names = []
    for keys in REVISION_INDEXES:
        names.append(f"{config.COL_REVISIONS}.{db[config.COL_REVISIONS].create_index(keys)}")
    for keys in REVERT_LINK_INDEXES:
        names.append(f"{config.COL_REVERT_LINKS}."
                     f"{db[config.COL_REVERT_LINKS].create_index(keys)}")
    return names


def mb(n_bytes: float) -> float:
    return n_bytes / 1024 / 1024


# --------------------------------------------------------------------------
# --target local
# --------------------------------------------------------------------------
def load_local(args) -> dict:
    success = bd.check_inputs()
    if bd.live_is_provisional(success):
        print("NOTE: the stream labels of the live cohort are PROVISIONAL until the capture is past "
              f"{config.LIVE_FINAL_AFTER.isoformat()}.")
    client = connect(config.MONGO_URI)
    db = client[config.MONGO_DB]
    t0 = time.time()
    for name in LOCAL_COLLECTIONS:
        db[name].drop()
    counts = {}
    for cohort in (config.COHORT_HISTORY, config.COHORT_LIVE):
        t = time.time()
        n = insert_batches(db[config.COL_REVISIONS], bd.iter_revision_documents(cohort))
        counts[f"revisions_{cohort}"] = n
        print(f"revisions ({cohort}): {n:,} documents in {time.time() - t:.1f} s")
        n = insert_batches(db[config.COL_REVERT_LINKS], bd.iter_revert_link_documents(cohort))
        counts[f"revert_links_{cohort}"] = n
        print(f"revert_links ({cohort}): {n:,} documents")
    n = insert_batches(db[config.COL_TAG_EVENTS], bd.iter_tag_event_documents())
    counts["tag_events"] = n
    print(f"tag_events (mw-reverted additions): {n:,} documents")
    n = insert_batches(db[config.COL_LATE_REVERTS], bd.iter_late_revert_documents())
    counts["late_reverts"] = n
    print(f"late_reverts: {n:,} documents")
    t = time.time()
    names = create_indexes(db)
    print(f"indexes ({time.time() - t:.1f} s): {', '.join(names)}")

    # Every Parquet row must be one document.
    expected = {
        "revisions_history": bd.parquet_rows(bd.TABLE_FILES["history_revisions"]),
        "revisions_live": bd.parquet_rows(bd.TABLE_FILES["live_revisions"]),
        "revert_links_history": bd.parquet_rows(bd.TABLE_FILES["history_revert_links"]),
        "revert_links_live": bd.parquet_rows(bd.TABLE_FILES["live_revert_links"]),
        "tag_events": bd.count_mw_reverted_additions(),
        "late_reverts": bd.parquet_rows(bd.TABLE_FILES["late_reverts"]),
    }
    bad = {k: (counts[k], expected[k]) for k in expected if counts[k] != expected[k]}
    if bad:
        raise SystemExit(f"STOP: document counts differ from the Parquet rows: {bad}")
    in_db = {c: db[c].count_documents({}) for c in LOCAL_COLLECTIONS}
    print("collections now:", ", ".join(f"{c}={n:,}" for c, n in in_db.items()))
    print(f"done in {time.time() - t0:.1f} s; the counts match the Parquet files")
    bd.write_success("mongo_local", in_db, config.TABLES_DIR,
                     {"database": config.MONGO_DB, "indexes": names,
                      "live_provisional": bd.live_is_provisional(success),
                      "seconds": round(time.time() - t0, 1)})
    return in_db


# --------------------------------------------------------------------------
# --target atlas
# --------------------------------------------------------------------------
def _index_key_bytes(doc: dict, keys: list[tuple[str, int]]) -> int:
    """Bytes of one index entry: the BSON of the key values plus a fixed overhead."""
    vals = {}
    for i, (path, _) in enumerate(keys):
        v = doc
        for part in path.split("."):
            v = v.get(part) if isinstance(v, dict) else None
        vals[str(i)] = v
    return len(bson.encode(vals)) + INDEX_ENTRY_OVERHEAD


def estimate_collection(docs: Iterable[dict], n_total: int, index_specs: list,
                        every: int = SAMPLE_EVERY) -> dict:
    """Estimate data and index size from every `every`-th document.

    data = average BSON size of the sample x n_total.
    index = for each index (and _id), average key bytes x n_total.
    This is the uncompressed size, which is what the Atlas free tier counts.
    """
    sizes, idx = [], [[] for _ in range(len(index_specs) + 1)]
    for i, d in enumerate(docs):
        if i % every:
            continue
        sizes.append(len(bson.encode(d)))
        idx[0].append(_index_key_bytes(d, [("_id", 1)]))
        for j, keys in enumerate(index_specs, start=1):
            idx[j].append(_index_key_bytes(d, keys))
    if not sizes:
        return {"n": n_total, "sampled": 0, "avg_bson_bytes": 0, "data_mb": 0.0, "index_mb": 0.0}
    avg = sum(sizes) / len(sizes)
    index_bytes = sum(n_total * sum(col) / len(col) for col in idx)
    return {"n": n_total, "sampled": len(sizes), "avg_bson_bytes": round(avg, 1),
            "data_mb": round(mb(avg * n_total), 2), "index_mb": round(mb(index_bytes), 2)}


def _pseudonymize_link(doc: dict, n_hex: int) -> dict:
    """A revert_links document without human names, ids or keys (bots keep their names)."""
    out = dict(doc)
    if out.get("reverter_kind") != "bot":
        out["reverter_name"] = bd.public_name(out.get("reverter_kind"), out.get("reverter_key"),
                                              out.get("reverter_name"), n_hex)
    if out.get("reverter_key"):
        out["reverter_key"] = (out["reverter_key"] if out.get("reverter_kind") == "bot"
                               else bd.editor_alias(out["reverter_key"], n_hex))
    if out.get("author_key") and out.get("author_kind") != "bot":
        out["author_key"] = bd.editor_alias(out["author_key"], n_hex)
    return out


def atlas_documents():
    """The parts that go to Atlas, as document streams.

    Atlas is shared with the whole team and shows documents in Data Explorer, so every
    human editor is replaced by the same pseudonym the results use ('editor_<hex>').
    Keys stay unique (alias_length checks this and stops on a collision or an empty
    ALIAS_SECRET), so distinct counts (Mongo Q2, Q4) give the same numbers as locally.
    """
    n_hex = bd.alias_length(bd.all_editor_keys())
    return {
        config.COL_REVISIONS: lambda: (bd.pseudonymize_revision(d, n_hex) for d in
                                       bd.iter_revision_documents(config.COHORT_HISTORY, lean=True)),
        config.COL_REVERT_LINKS: lambda: (_pseudonymize_link(d, n_hex) for d in
                                          bd.iter_revert_link_documents(config.COHORT_HISTORY)),
    }


def local_chart_documents() -> dict[str, list[dict]]:
    """The chart collections from the local database (made by queries/run_mongo.py)."""
    try:
        db = connect(config.MONGO_URI, 3000)[config.MONGO_DB]
    except PyMongoError:
        return {}
    return {c: list(db[c].find({})) for c in config.CHART_COLLECTIONS}


def estimate_atlas_size(chart_docs: dict[str, list[dict]] | None = None) -> dict:
    """The size estimate for the Atlas copy, in MB, with one line per collection."""
    bd.check_inputs(["history_revisions", "history_revert_links"])
    parts = {}
    parts[config.COL_REVISIONS] = estimate_collection(
        bd.iter_revision_documents(config.COHORT_HISTORY, lean=True),
        bd.parquet_rows(bd.TABLE_FILES["history_revisions"]), REVISION_INDEXES)
    parts[config.COL_REVERT_LINKS] = estimate_collection(
        bd.iter_revert_link_documents(config.COHORT_HISTORY),
        bd.parquet_rows(bd.TABLE_FILES["history_revert_links"]), REVERT_LINK_INDEXES)
    for name, docs in (chart_docs or {}).items():
        parts[name] = estimate_collection(docs, len(docs), [], every=1)
    total = sum(p["data_mb"] + p["index_mb"] for p in parts.values())
    return {"parts": parts, "total_mb": round(total, 2), "budget_mb": config.ATLAS_BUDGET_MB,
            "fits": total <= config.ATLAS_BUDGET_MB}


def print_estimate(est: dict) -> None:
    print(f"{'collection':26s} {'documents':>10s} {'avg bytes':>10s} {'data MB':>9s} {'index MB':>9s}")
    for name, p in est["parts"].items():
        print(f"{name:26s} {p['n']:>10,} {p['avg_bson_bytes']:>10.1f} "
              f"{p['data_mb']:>9.2f} {p['index_mb']:>9.2f}")
    print(f"estimated total {est['total_mb']:.1f} MB; budget {est['budget_mb']} MB "
          f"(the free tier limit is 512 MB) -> {'fits' if est['fits'] else 'TOO BIG'}")


def load_atlas(args) -> dict:
    if not args.estimate_only and not args.confirm_overwrite:
        raise SystemExit("STOP: --target atlas replaces the Atlas collections. "
                         "Add --confirm-overwrite if that is what you want "
                         "(or use --estimate-only to see the size first).")
    charts = local_chart_documents()
    missing = [c for c in config.CHART_COLLECTIONS if not charts.get(c)]
    if missing:
        print("WARNING: these chart collections are empty or missing in the local database "
              f"(run queries/run_mongo.py first): {', '.join(missing)}")
    est = estimate_atlas_size(charts)
    print_estimate(est)
    if args.estimate_only:
        return {"estimate_mb": est["total_mb"]}
    if not est["fits"]:
        raise SystemExit(f"STOP: the estimate ({est['total_mb']:.1f} MB) is over "
                         f"config.ATLAS_BUDGET_MB ({config.ATLAS_BUDGET_MB} MB). Nothing loaded.")
    if not config.ATLAS_URI:
        raise SystemExit("STOP: ATLAS_URI is empty. Put it in ec-hw2/.env (see .env.example).")
    client = connect(config.ATLAS_URI, 15000)
    db = client[config.ATLAS_DB]
    print(f"connected to Atlas, database {config.ATLAS_DB}")
    counts = {}
    for name, docs in atlas_documents().items():
        db[name].drop()
        t = time.time()
        counts[name] = insert_batches(db[name], docs())
        print(f"{name}: {counts[name]:,} documents in {time.time() - t:.1f} s")
    print("indexes:", ", ".join(create_indexes(db)))
    # Atlas Charts point at these collections by name, so we empty them and refill
    # them instead of dropping them.
    for name in config.CHART_COLLECTIONS:
        db[name].delete_many({})
        docs = charts.get(name) or []
        counts[name] = insert_batches(db[name], docs) if docs else 0
        print(f"{name}: {counts[name]:,} documents")
    try:
        s = db.command("dbStats")
        print(f"Atlas dbStats: dataSize {mb(s.get('dataSize', 0)):.1f} MB, "
              f"storageSize {mb(s.get('storageSize', 0)):.1f} MB, "
              f"indexSize {mb(s.get('indexSize', 0)):.1f} MB, "
              f"objects {s.get('objects', 0):,}, collections {s.get('collections', 0)}")
    except PyMongoError as e:
        print(f"dbStats is not available: {type(e).__name__}")
    bd.write_success("mongo_atlas", counts, config.TABLES_DIR,
                     {"database": config.ATLAS_DB, "estimate_mb": est["total_mb"]})
    return counts


# --------------------------------------------------------------------------
# --target sharded
# --------------------------------------------------------------------------
def check_sharded(args) -> dict:
    try:
        client = connect(config.SHARDED_URI, 4000)
    except PyMongoError as e:
        raise SystemExit("STOP: cannot reach the sharded demo cluster at config.SHARDED_URI "
                         f"({type(e).__name__}). Start it first (the scale-out part: "
                         "ec-hw2/scaleout/docker-compose.sharded.yml).")
    hello = client.admin.command("hello")
    info = {"version": client.server_info().get("version"), "mongos": hello.get("msg") == "isdbgrid"}
    print(f"connected: MongoDB {info['version']}, "
          f"{'mongos (sharded cluster)' if info['mongos'] else 'NOT a mongos'}")
    if info["mongos"]:
        shards = client.admin.command("listShards").get("shards", [])
        info["shards"] = [s.get("_id") for s in shards]
        print(f"shards: {', '.join(info['shards']) or '(none yet)'}")
    return info


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--target", choices=["local", "atlas", "sharded"], required=True)
    p.add_argument("--confirm-overwrite", action="store_true",
                   help="needed for --target atlas: replace the Atlas collections")
    p.add_argument("--estimate-only", action="store_true",
                   help="--target atlas: print the size estimate only; do not connect to Atlas")
    args = p.parse_args(argv)
    {"local": load_local, "atlas": load_atlas, "sharded": check_sharded}[args.target](args)


if __name__ == "__main__":
    main()
