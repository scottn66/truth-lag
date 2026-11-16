"""Load the small Gold exports into MongoDB Atlas for Atlas Charts (collections named final_*).

Purpose
    Atlas Charts can only read data that is in Atlas. This copies the chart-sized files of data/exports/
    into new collections with the prefix final_, so the EC HW2 collections and their charts are untouched.

Run (from the repository root)
    .venv-lake/bin/python -m etl.atlas_charts --check     read only: sizes and what is there now
    .venv-lake/bin/python -m etl.atlas_charts             load (each final_ collection is replaced)

Rules
    The connection string comes from ec-hw2/.env.atlas or ec-hw2/.env (never committed) and is never printed.
    Not loaded: lsh_edits (edit comment text) and the full page summary (too large for the free tier).
    The load stops before writing if the database would pass the budget (config.ATLAS_BUDGET_MB).
    Re-running is safe: each collection is written under a temporary name and renamed over the old one.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import pandas as pd

from .hw2 import config
from .lake_config import EXPORTS_DIR

COLLECTIONS = {
    "final_el_curve": "mart_el_curve.csv",
    "final_el_by_burst": "mart_el_by_burst.csv",
    "final_reconciliation": "mart_reconciliation.csv",
    "final_label_change": "label_change_by_class.csv",
    "final_h1": "hypotheses_h1.csv",
    "final_h3": "hypotheses_h3.csv",
    "final_daily_counts": "daily_counts.csv",
    "final_group_sizes": "group_sizes_by_kind_hour.csv",
    "final_page_summary_top": "page_revert_summary_top.csv",
}
BSON_OVERHEAD = 1.6   # rough: BSON documents with field names against CSV bytes (used only for the budget stop)


def records(path) -> list[dict]:
    df = pd.read_csv(path)
    return json.loads(df.to_json(orient="records"))   # plain Python types, NaN becomes null


def safe(err: Exception) -> str:
    text = f"{type(err).__name__}: {err}"
    for secret in (config.ATLAS_URI,):
        if secret:
            text = text.replace(secret, "<ATLAS_URI>")
    return text[:300]


def main() -> int:
    check_only = "--check" in sys.argv
    if not config.ATLAS_URI or "<" in config.ATLAS_URI:
        print("ATLAS_URI is not set in ec-hw2/.env.atlas or ec-hw2/.env")
        return 1
    from pymongo import MongoClient
    try:
        client = MongoClient(config.ATLAS_URI, serverSelectionTimeoutMS=20000, appname="truthlag-final-charts")
        db = client[config.ATLAS_DB]
        stats = db.command("dbStats")
    except Exception as err:   # noqa: BLE001
        print("could not reach Atlas:", safe(err))
        return 1
    used_mb = (stats.get("dataSize", 0) + stats.get("indexSize", 0)) / 1e6
    existing = sorted(db.list_collection_names())
    print(f"database {config.ATLAS_DB}: {used_mb:.1f} MB used (data + indexes), {len(existing)} collections")
    for name in existing:
        print(f"  {name}: {db[name].estimated_document_count():,} documents")

    files = {name: EXPORTS_DIR / f for name, f in COLLECTIONS.items()}
    missing = [str(p) for p in files.values() if not p.exists()]
    if missing:
        print("missing export files:", missing)
        return 1
    add_mb = sum(p.stat().st_size for p in files.values()) * BSON_OVERHEAD / 1e6
    old_final_mb = sum(db.command("collStats", n).get("size", 0) for n in existing if n in COLLECTIONS) / 1e6
    after = used_mb - old_final_mb + add_mb
    print(f"load would add about {add_mb:.1f} MB (estimate) -> about {after:.1f} MB; budget {config.ATLAS_BUDGET_MB} MB")
    if after > config.ATLAS_BUDGET_MB:
        print("refused: over the budget, nothing written")
        return 1
    if check_only:
        return 0

    manifest = json.loads((EXPORTS_DIR / "manifest.json").read_text()) if (EXPORTS_DIR / "manifest.json").exists() else {}
    loaded = {}
    for name, path in files.items():
        rows = records(path)
        tmp = db[name + "__new"]
        tmp.drop()
        if rows:
            tmp.insert_many(rows, ordered=False)
        tmp.rename(name, dropTarget=True)
        loaded[name] = {"file": path.name, "rows": len(rows), "in_atlas": db[name].count_documents({})}
        print(f"loaded {name}: {len(rows):,} rows from {path.name}; in Atlas now: {loaded[name]['in_atlas']:,}")
    db["final_page_summary_top"].create_index([("cohort_id", 1), ("edits", -1)])
    db["final_el_curve"].create_index([("cohort_id", 1), ("label_source", 1), ("user_kind", 1), ("wait_s", 1)])
    db["final_meta"].replace_one({"_id": "load"}, {
        "_id": "load", "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "collections": loaded, "lake_versions": manifest.get("lake_versions"), "as_of": manifest.get("as_of"),
        "note": "cohort_id live_ext contains live: do not add them. Pick one label_source per series.",
    }, upsert=True)
    stats = db.command("dbStats")
    print(f"database now: {(stats.get('dataSize', 0) + stats.get('indexSize', 0)) / 1e6:.1f} MB used")
    ok = all(v["rows"] == v["in_atlas"] for v in loaded.values())
    print("ALL COUNTS MATCH" if ok else "COUNT MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
