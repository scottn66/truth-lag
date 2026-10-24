"""Build the live counters page_hour in MongoDB (the "speed layer").

Purpose
    page_hour has one document per (page, UTC hour). The hour is the hour of
    meta.dt, the time the stream published the event, so each count sits in the
    hour when it BECAME KNOWN:
      edits_seen          page_change edit/create events published in that hour
      revert_events_seen  those events that carry a revert
      reverted_revs_seen  revisions covered by a revert (live_revert_links_all, all
                          methods), counted in the hour of the reverting event's meta.dt
    _id = "<page_id>:<YYYY-MM-DDTHH>". Only namespace 0, over the whole capture.

    Batch mode (the default) gives the same counts on every re-run. Python only
    loads two staging collections with the needed fields; MongoDB does the work:
    one aggregation with $unionWith + $group + $merge (whenMatched "replace") into
    page_hour. Documents from an older build that this build did not write are
    removed. Then the staging collections are dropped. A batch build never uses $inc.

    --follow is the live demo. It tails the newest LOCAL raw files in data/raw
    (never EventStreams) and applies $inc to page_hour_live (not page_hour).
    It keeps a set of meta.id values, so it never counts an event twice. It
    counts edits_seen and revert_events_seen only (reverted_revs_seen needs the
    range cover of label_live.py). Stop it with Ctrl-C. It empties
    page_hour_live when it starts, so the counts belong to one session.

Inputs
    data/parsed/page_change.parquet (and _SUCCESS_parsed.json)
    data/tables/live_revert_links_all.parquet (and _SUCCESS_live.json)
    --follow: data/raw/mediawiki.page_change.v1/dt=*/hour=*/part-*.ndjson.gz

Outputs
    MongoDB collection page_hour (batch) or page_hour_live (--follow).
    data/tables/_SUCCESS_page_hour.json with the counts (batch).

Run (from the repo root)
    .venv/bin/python ec-hw2/speed_layer.py
    .venv/bin/python ec-hw2/speed_layer.py --follow              (Ctrl-C to stop)
    .venv/bin/python ec-hw2/speed_layer.py --follow --max-polls 1  (one pass, then stop)
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from pymongo import UpdateOne

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from ingest import build_documents as bd  # noqa: E402
from load_mongo import connect, insert_batches  # noqa: E402

STAGE_EVENTS = "page_change_min"       # staging: one document per page_change event
STAGE_COVERS = "page_change_min_cover"  # staging: one document per covered revision
EDIT_KINDS = ("edit", "create")
HOUR_FORMAT = "%Y-%m-%dT%H"             # the hour part of the page_hour _id
GZIP_ERRORS = (EOFError, OSError, zlib.error)


def page_hour_id(page_id: int, hour: datetime) -> str:
    return f"{int(page_id)}:{hour.astimezone(timezone.utc).strftime(HOUR_FORMAT)}"


# --------------------------------------------------------------------------
# Batch mode
# --------------------------------------------------------------------------
def staging_documents(page_change: pd.DataFrame, links_all: pd.DataFrame):
    """The two staging sets, with only the fields the aggregation needs."""
    pcf = page_change[(page_change["ns"] == 0) & page_change["kind"].isin(EDIT_KINDS)]
    events = pd.DataFrame({
        "_id": pcf["meta_id"].astype(str),
        "page_id": pcf["page_id"].astype("int64"),
        "meta_dt": pcf["meta_dt"],
        "is_revert": pcf["revert_method"].notna(),
    })
    lk = links_all[links_all["page_ns"] == 0]
    covers = pd.DataFrame({
        "page_id": lk["page_id"].astype("int64"),
        "known_at": lk["known_at"],
        "reverting_rev_id": lk["reverting_rev_id"].astype("int64"),
        "reverted_rev_id": lk["reverted_rev_id"].astype("int64"),
    })
    return events, covers


def _records(df: pd.DataFrame):
    """DataFrame rows as plain Python dicts (aware datetimes, Python ints and bools)."""
    cols = {}
    for c in df.columns:
        s = df[c]
        if isinstance(s.dtype, pd.DatetimeTZDtype):
            cols[c] = [x.to_pydatetime() for x in s]
        else:
            cols[c] = s.astype(object).tolist()
    keys = list(cols)
    for vals in zip(*cols.values()):
        yield dict(zip(keys, vals))


def build_pipeline() -> list[dict]:
    """$unionWith + $group + $merge: the whole speed-layer job inside MongoDB."""
    hour = lambda field: {"$dateTrunc": {"date": field, "unit": "hour", "timezone": "UTC"}}  # noqa: E731
    return [
        {"$project": {"_id": 0, "page_id": 1, "hour": hour("$meta_dt"), "e": {"$literal": 1},
                      "r": {"$cond": ["$is_revert", 1, 0]}, "c": {"$literal": 0}}},
        {"$unionWith": {"coll": STAGE_COVERS, "pipeline": [
            {"$project": {"_id": 0, "page_id": 1, "hour": hour("$known_at"), "e": {"$literal": 0},
                          "r": {"$literal": 0}, "c": {"$literal": 1}}}]}},
        {"$group": {"_id": {"page_id": "$page_id", "hour": "$hour"},
                    "edits_seen": {"$sum": "$e"}, "revert_events_seen": {"$sum": "$r"},
                    "reverted_revs_seen": {"$sum": "$c"}}},
        {"$project": {"_id": {"$concat": [
            {"$toString": "$_id.page_id"}, ":",
            {"$dateToString": {"date": "$_id.hour", "format": "%Y-%m-%dT%H", "timezone": "UTC"}}]},
            "page_id": "$_id.page_id", "hour": "$_id.hour", "edits_seen": 1,
            "revert_events_seen": 1, "reverted_revs_seen": 1}},
    ]


def run_batch(db, page_change: pd.DataFrame, links_all: pd.DataFrame) -> dict:
    """Load staging, aggregate into page_hour, remove stale documents, drop staging."""
    events, covers = staging_documents(page_change, links_all)
    for name in (STAGE_EVENTS, STAGE_COVERS):
        db[name].drop()
    t0 = time.time()
    n_ev = insert_batches(db[STAGE_EVENTS], _records(events))
    n_cv = insert_batches(db[STAGE_COVERS], _records(covers))
    t_load = time.time() - t0
    build_id = datetime.now(timezone.utc).replace(microsecond=0)
    pipeline = build_pipeline() + [
        {"$addFields": {"built_at": build_id}},
        {"$merge": {"into": config.COL_PAGE_HOUR, "on": "_id",
                    "whenMatched": "replace", "whenNotMatched": "insert"}},
    ]
    t1 = time.time()
    db[STAGE_EVENTS].aggregate(pipeline, allowDiskUse=True)
    t_agg = time.time() - t1
    stale = db[config.COL_PAGE_HOUR].delete_many({"built_at": {"$ne": build_id}}).deleted_count
    for name in (STAGE_EVENTS, STAGE_COVERS):
        db[name].drop()
    tot = list(db[config.COL_PAGE_HOUR].aggregate([{"$group": {
        "_id": None, "docs": {"$sum": 1}, "edits_seen": {"$sum": "$edits_seen"},
        "revert_events_seen": {"$sum": "$revert_events_seen"},
        "reverted_revs_seen": {"$sum": "$reverted_revs_seen"}}}]))
    tot = tot[0] if tot else {"docs": 0, "edits_seen": 0, "revert_events_seen": 0,
                              "reverted_revs_seen": 0}
    tot.pop("_id", None)
    # The totals must equal the staging rows: nothing lost, nothing counted twice.
    want = {"edits_seen": n_ev, "revert_events_seen": int(events["is_revert"].sum()),
            "reverted_revs_seen": n_cv}
    for k, v in want.items():
        if tot[k] != v:
            raise SystemExit(f"STOP: page_hour {k} = {tot[k]:,} but the input has {v:,}")
    return {**tot, "staging_events": n_ev, "staging_covers": n_cv, "stale_removed": stale,
            "load_s": round(t_load, 1), "aggregate_s": round(t_agg, 1),
            "built_at": build_id.isoformat()}


def top_page_hours(db, coll: str, titles: dict, n: int = 10) -> list[dict]:
    rows = list(db[coll].find({}, {"built_at": 0}).sort([("edits_seen", -1), ("_id", 1)]).limit(n))
    for r in rows:
        r["title"] = titles.get(r["page_id"], "")
    return rows


def print_top(rows: list[dict], header: str) -> None:
    print(header)
    print(f"  {'page_id:hour (UTC)':26s} {'edits':>6s} {'revert ev':>9s} {'reverted':>8s}  title")
    for r in rows:
        print(f"  {r['_id']:26s} {r.get('edits_seen', 0):>6} {r.get('revert_events_seen', 0):>9} "
              f"{r.get('reverted_revs_seen', 0):>8}  {r['title']}")


def page_titles(page_change: pd.DataFrame) -> dict:
    s = page_change.dropna(subset=["page_title"]).drop_duplicates("page_id", keep="last")
    return dict(zip(s["page_id"].astype("int64"), s["page_title"]))


def batch_main() -> None:
    bd.check_inputs(["page_change", "live_revert_links_all"])
    pc = pd.read_parquet(bd.TABLE_FILES["page_change"],
                         columns=["meta_id", "meta_dt", "kind", "ns", "page_id", "page_title",
                                  "revert_method"])
    links_all = pd.read_parquet(bd.TABLE_FILES["live_revert_links_all"],
                                columns=["page_id", "page_ns", "known_at", "reverting_rev_id",
                                         "reverted_rev_id"])
    db = connect(config.MONGO_URI)[config.MONGO_DB]
    info = run_batch(db, pc, links_all)
    print(f"page_hour: {info['docs']:,} page-hours; edits_seen {info['edits_seen']:,}, "
          f"revert_events_seen {info['revert_events_seen']:,}, "
          f"reverted_revs_seen {info['reverted_revs_seen']:,}")
    print(f"staging load {info['load_s']} s, $group + $merge {info['aggregate_s']} s, "
          f"stale documents removed {info['stale_removed']:,}")
    print_top(top_page_hours(db, config.COL_PAGE_HOUR, page_titles(pc)),
              "top 10 page-hours by edits_seen:")
    bd.write_success("page_hour", {config.COL_PAGE_HOUR: info["docs"]}, config.TABLES_DIR,
                     {k: info[k] for k in ("edits_seen", "revert_events_seen",
                                           "reverted_revs_seen", "built_at")})


# --------------------------------------------------------------------------
# --follow mode (live demo on the local raw files)
# --------------------------------------------------------------------------
def newest_raw_files(n: int) -> list[Path]:
    """The n newest page_change part files (by the dt/hour partition, then name)."""
    base = config.RAW_DIR / config.STREAM_PAGE_CHANGE
    files = sorted(base.glob(config.RAW_GLOB),
                   key=lambda p: (p.parent.parent.name, p.parent.name, p.name))
    return files[-n:] if n > 0 else []


def read_events(path: Path):
    """Yield the parsed JSON events of one part file. A file that is still being
    written has no gzip end marker: we keep the complete lines and stop there."""
    try:
        with gzip.open(path, "rb") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue         # a half-written last line; it is read again next time
    except GZIP_ERRORS:
        return


def follow_update(ev: dict, seen: set) -> UpdateOne | None:
    """The $inc for one raw event, or None when it does not count (or was seen)."""
    meta = ev.get("meta") or {}
    mid = meta.get("id")
    page = ev.get("page") or {}
    if (mid is None or mid in seen or page.get("namespace_id") != 0
            or ev.get("page_change_kind") not in EDIT_KINDS or page.get("page_id") is None
            or not meta.get("dt")):
        return None
    seen.add(mid)
    dt = config.utc(meta["dt"])
    hour = dt.replace(minute=0, second=0, microsecond=0)
    is_revert = 1 if (ev.get("revision") or {}).get("revert") else 0
    return UpdateOne({"_id": page_hour_id(page["page_id"], hour)},
                     {"$inc": {"edits_seen": 1, "revert_events_seen": is_revert},
                      "$setOnInsert": {"page_id": int(page["page_id"]), "hour": hour}},
                     upsert=True)


def follow_pass(db, files: list[Path], seen: set, batch: int = 1000) -> int:
    ops, n = [], 0
    for path in files:
        for ev in read_events(path):
            op = follow_update(ev, seen)
            if op is None:
                continue
            ops.append(op)
            if len(ops) >= batch:
                db[config.COL_PAGE_HOUR_LIVE].bulk_write(ops, ordered=False)
                n += len(ops)
                ops = []
    if ops:
        db[config.COL_PAGE_HOUR_LIVE].bulk_write(ops, ordered=False)
        n += len(ops)
    return n


def follow_main(args) -> None:
    db = connect(config.MONGO_URI)[config.MONGO_DB]
    db[config.COL_PAGE_HOUR_LIVE].delete_many({})
    seen: set = set()
    polls = 0
    print(f"following the {args.files} newest local raw files every {args.poll_s} s "
          "(Ctrl-C to stop). New files arrive only when someone copies them with rsync.")
    try:
        while True:
            files = newest_raw_files(args.files)
            n = follow_pass(db, files, seen)
            polls += 1
            print(f"pass {polls}: {n:,} new events counted ({len(seen):,} distinct meta.id so far); "
                  f"newest file {files[-1].relative_to(config.RAW_DIR) if files else '-'}")
            if args.max_polls and polls >= args.max_polls:
                break
            time.sleep(args.poll_s)
    except KeyboardInterrupt:
        print("stopped (Ctrl-C)")
    print_top(top_page_hours(db, config.COL_PAGE_HOUR_LIVE, {}),
              "top 10 page-hours in page_hour_live by edits_seen:")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Build the page_hour live counters in MongoDB.")
    p.add_argument("--follow", action="store_true",
                   help="tail the newest local raw files and $inc page_hour_live")
    p.add_argument("--files", type=int, default=2, help="--follow: how many newest files to read")
    p.add_argument("--poll-s", type=float, default=10.0, help="--follow: seconds between passes")
    p.add_argument("--max-polls", type=int, default=0,
                   help="--follow: stop after this many passes (0 = until Ctrl-C)")
    args = p.parse_args(argv)
    if args.follow:
        follow_main(args)
    else:
        batch_main()


if __name__ == "__main__":
    main()
