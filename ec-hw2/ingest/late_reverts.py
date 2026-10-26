"""Late reverts (case study): September revisions that the dump calls "not reverted",
but that the October stream shows being reverted.

Purpose
    Step 1. Expand every captured page_change revert (all methods) to the September
            revisions it covers on the same page (same range-cover rule as
            label_live.py; here R.rev_dt = the dump's event_timestamp).
    Step 2. Take mw-reverted tag additions on September revisions and link each one
            to a covering page_change revert on the same page with meta_dt in
            [tag meta_dt - config.LATE_TAG_LINK_WINDOW_S, tag meta_dt].
    Step 3. Keep one row per September rev_id (DATA_MODEL.md section 3, late_reverts).
    All counts are LOWER BOUNDS: nobody watched the stream from the dump's last
    revision (2026-10-01 01:38 UTC) until the capture started.
    The slim file has every namespace, so the rows do too. page_ns is the page's
    CURRENT namespace (slim column page_namespace). The summary gives the counts for
    all namespaces and, next to them, for namespace 0 only (keys ending in _ns0),
    which is the namespace of the history cohort.

Inputs
    data/history/enwiki_rev_all_2026-09_slim.parquet   (all strings; cast with history_columns)
    data/parsed/page_change.parquet, tag_events.parquet (from ingest/parse_stream.py)
    data/tables/live_revert_links_all.parquet          (from ingest/label_live.py)
    data/tables/history_revisions.parquet              (optional; else the cohort window is used)

Outputs (in data/tables/)
    late_reverts.parquet, late_reverts_summary.json, _SUCCESS_late_reverts.json

Run (from the repo root, after label_live.py)
    .venv/bin/python ec-hw2/ingest/late_reverts.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from ingest.history_columns import cast_history_frame  # noqa: E402
from ingest.label_live import BIG_ID, ids, load_page_change, range_cover, revert_events  # noqa: E402

log = logging.getLogger("late_reverts")

SLIM_COLUMNS = ["revision_id", "page_id", "event_timestamp", "revision_is_identity_reverted",
                "page_namespace"]
TS = pa.timestamp("ns", tz="UTC")   # same as the other data/tables files
LATE_SCHEMA = pa.schema([
    ("rev_id", pa.int64()), ("page_id", pa.int64()), ("page_ns", pa.int64()), ("rev_ts", TS),
    ("first_signal_at", TS), ("via", pa.list_(pa.string())), ("class", pa.string()),
    ("reverting_rev_id", pa.int64()), ("method", pa.string()), ("age_days", pa.float64()),
    ("age_upper_bound", pa.bool_()), ("restored_later", pa.bool_()), ("in_history_cohort", pa.bool_()),
])


def iso(ts) -> str | None:
    if ts is None or pd.isna(ts):
        return None
    return pd.Timestamp(ts).tz_convert("UTC").isoformat().replace("+00:00", "Z")


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
def load_september(slim_path: Path, page_ids, rev_ids) -> tuple[pd.DataFrame, dict]:
    """September revisions on the given pages (or with the given rev_ids), NOT reverted in the dump.

    We filter on the text columns first, so we only cast the rows we need.
    """
    t = pq.read_table(slim_path, columns=SLIM_COLUMNS)
    vc = {d["values"]: int(d["counts"]) for d in t.column("revision_is_identity_reverted").value_counts().to_pylist()}
    stats = {"slim_rows": t.num_rows, "slim_identity_reverted_values": {str(k): v for k, v in vc.items()}}
    pages = pa.array(sorted({str(int(p)) for p in page_ids}), pa.string())
    revs = pa.array(sorted({str(int(r)) for r in rev_ids}), pa.string())
    mask = pc.or_(pc.is_in(t.column("page_id"), value_set=pages),
                  pc.is_in(t.column("revision_id"), value_set=revs))
    sub = cast_history_frame(t.filter(mask).to_pandas())
    del t
    stats["slim_rows_on_candidate_pages"] = int(len(sub))
    not_rev = ~sub["revision_is_identity_reverted"].fillna(False).astype(bool)
    sub = sub[not_rev.to_numpy()]
    stats["candidate_rows_not_reverted"] = int(len(sub))
    out = pd.DataFrame({"rev_id": sub["revision_id"].astype("int64").to_numpy(),
                        "page_id": sub["page_id"].astype("int64").to_numpy(),
                        "rev_dt": sub["event_timestamp"].to_numpy(),
                        "page_namespace": sub["page_namespace"].to_numpy()})
    out["rev_dt"] = pd.to_datetime(out["rev_dt"], utc=True)
    return out.reset_index(drop=True), stats


def history_cohort_ids(tables_dir: Path, sept: pd.DataFrame) -> tuple[np.ndarray, str]:
    """Return a bool array 'in the history cohort' for the September rows, and the method used."""
    path = tables_dir / "history_revisions.parquet"
    if path.exists():
        ids = set(pd.read_parquet(path, columns=["rev_id"])["rev_id"].astype("int64"))
        return sept["rev_id"].isin(ids).to_numpy(), "history_revisions.parquet"
    w0, w1 = config.HISTORY_WINDOW
    # Fallback: the window and the current namespace from the slim file. The real
    # cohort also needs page_namespace_historical == 0 and drops null revisions.
    inside = (sept["rev_dt"] >= w0) & (sept["rev_dt"] < w1) & (sept["page_namespace"] == 0)
    return inside.fillna(False).to_numpy(dtype=bool), "window_fallback (HISTORY_WINDOW + current ns 0)"


# --------------------------------------------------------------------------
# Steps 1 to 3
# --------------------------------------------------------------------------
def cover_pairs(sept: pd.DataFrame, E: pd.DataFrame) -> pd.DataFrame:
    """Step 1: every (September revision, October revert) covering pair."""
    pairs = range_cover(sept[["page_id", "rev_id", "rev_dt"]], E)
    r = sept.iloc[pairs["r_row"].to_numpy()].reset_index(drop=True)
    e = E.iloc[pairs["e_row"].to_numpy()].reset_index(drop=True)
    return pd.DataFrame({
        "rev_id": r["rev_id"].to_numpy(), "page_id": r["page_id"].to_numpy(), "rev_ts": r["rev_dt"],
        "e_rev_id": e["rev_id"].astype("int64").to_numpy(), "e_page_id": e["page_id"].astype("int64").to_numpy(),
        "e_rev_dt": e["rev_dt"], "e_meta_dt": e["meta_dt"],
        "e_exact": e["revert_is_exact"].fillna(False).astype(bool).to_numpy(),
        "e_method": e["revert_method"].astype(object).to_numpy(),
        "beyond_newest": r["rev_id"].to_numpy() > ids(e["revert_newest_id"], fill=BIG_ID),
    })


def link_tags(tags: pd.DataFrame, P: pd.DataFrame,
              window_s: int = config.LATE_TAG_LINK_WINDOW_S) -> pd.DataFrame:
    """Step 2: for each mw-reverted addition, is there a covering revert on the same
    page with meta_dt in [tag meta_dt - window, tag meta_dt]? Adds column 'linked'."""
    t = tags[["meta_id", "rev_id", "page_id", "meta_dt"]].reset_index(drop=True)
    m = t.merge(P[["rev_id", "e_page_id", "e_meta_dt", "e_rev_id"]], on="rev_id")
    ok = ((m["e_page_id"] == m["page_id"])
          & (m["e_meta_dt"] >= m["meta_dt"] - pd.to_timedelta(window_s, unit="s"))
          & (m["e_meta_dt"] <= m["meta_dt"]))
    linked_ids = set(m.loc[ok, "meta_id"])
    t["linked"] = t["meta_id"].isin(linked_ids)
    return t


def late_rows(sept: pd.DataFrame, P: pd.DataFrame, T: pd.DataFrame, restored_ids: set,
              in_cohort: np.ndarray) -> pd.DataFrame:
    """Step 3: one row per September rev_id with a stream signal."""
    info = sept[["rev_id", "page_id", "rev_dt", "page_namespace"]].assign(
        in_history_cohort=in_cohort)
    info = info.rename(columns={"rev_dt": "rev_ts"}).drop_duplicates("rev_id").set_index("rev_id")
    # The chosen revert: the first exact one by (rev_dt, rev_id), else the first one.
    chosen = P.sort_values(["rev_id", "e_exact", "e_rev_dt", "e_rev_id"],
                           ascending=[True, False, True, True], kind="stable")
    chosen = chosen.drop_duplicates("rev_id").set_index("rev_id")
    pc_first = P.groupby("rev_id")["e_meta_dt"].min()
    tag_first = T.groupby("rev_id")["meta_dt"].min()
    ids = sorted(set(P["rev_id"]) | set(T["rev_id"]))
    out = pd.DataFrame({"rev_id": np.asarray(ids, dtype="int64")})
    out["page_id"] = out["rev_id"].map(info["page_id"]).astype("int64")
    out["page_ns"] = out["rev_id"].map(info["page_namespace"]).astype("Int64")
    out["rev_ts"] = out["rev_id"].map(info["rev_ts"])
    s_pc = out["rev_id"].map(pc_first)
    s_tag = out["rev_id"].map(tag_first)
    out["first_signal_at"] = pd.concat([s_pc, s_tag], axis=1).min(axis=1)
    has_pc = s_pc.notna().to_numpy()
    has_tag = s_tag.notna().to_numpy()
    out["via"] = [[x for x, flag in (("page_change", a), ("tag", b)) if flag] for a, b in zip(has_pc, has_tag)]
    exact = out["rev_id"].map(chosen["e_exact"]).eq(True).to_numpy()
    out["class"] = np.where(~has_pc, "method_unknown", np.where(exact, "exact", "inexact_undo"))
    out["reverting_rev_id"] = out["rev_id"].map(chosen["e_rev_id"]).astype("Int64")
    out["method"] = out["rev_id"].map(chosen["e_method"]).astype(object)
    rev_ts_s = out["rev_ts"]
    age_pc = (out["rev_id"].map(chosen["e_rev_dt"]) - rev_ts_s).dt.total_seconds() / 86400
    age_tag = (s_tag - rev_ts_s).dt.total_seconds() / 86400
    out["age_days"] = np.where(has_pc, age_pc, age_tag)
    out["age_upper_bound"] = ~has_pc        # tag-only: the tag time is later than the revert
    restored = out["reverting_rev_id"].isin(restored_ids).astype(object)
    restored[~has_pc] = None
    out["restored_later"] = restored
    out["in_history_cohort"] = out["rev_id"].map(info["in_history_cohort"]).astype(bool)
    assert set(out["class"]) <= set(config.LATE_CLASSES)
    return out[[f.name for f in LATE_SCHEMA]]


# --------------------------------------------------------------------------
# Summary and IO
# --------------------------------------------------------------------------
def summarize(rows: pd.DataFrame, P: pd.DataFrame, T: pd.DataFrame, E: pd.DataFrame, titles: pd.Series,
              sept_stats: dict, cohort_method: str, capture_starts: dict) -> dict:
    by_class = rows["class"].value_counts().reindex(config.LATE_CLASSES, fill_value=0)
    top = rows.groupby("page_id").agg(rows=("rev_id", "size"),
                                      exact=("class", lambda s: int((s == "exact").sum())),
                                      inexact_undo=("class", lambda s: int((s == "inexact_undo").sum())),
                                      method_unknown=("class", lambda s: int((s == "method_unknown").sum())))
    top = top.sort_values(["rows"], ascending=False, kind="stable").head(5).reset_index()
    top["page_title"] = top["page_id"].map(titles)
    # Rows whose every covering pair lies after newest_id: only exact undos of an older
    # edit make such pairs (see label_live.range_cover and beyond_newest).
    only_beyond = P.groupby("rev_id")["beyond_newest"].all()
    rows_only_beyond = rows["rev_id"].map(only_beyond).eq(True)
    age = {c: (None if g.empty else round(float(g["age_days"].median()), 2))
           for c, g in rows.groupby("class")}
    # A tag-only row should come from a time when page_change was not captured.
    mu = rows.loc[rows["class"] == "method_unknown", "first_signal_at"]
    pc_first = pd.Timestamp(capture_starts["page_change"])
    pc_last = pd.Timestamp(capture_starts["page_change_newest"])
    tag_only_period = {"before_page_change_capture": int((mu < pc_first).sum()),
                       "during_page_change_capture": int(((mu >= pc_first) & (mu <= pc_last)).sum()),
                       "after_newest_page_change": int((mu > pc_last).sum())}
    ns0 = rows[rows["page_ns"].eq(0).fillna(False).astype(bool)]
    by_class_ns0 = ns0["class"].value_counts().reindex(config.LATE_CLASSES, fill_value=0)
    return {
        "rows": int(len(rows)),
        "rows_ns0": int(len(ns0)),
        "by_class": {k: int(v) for k, v in by_class.items()},
        "by_class_ns0": {k: int(v) for k, v in by_class_ns0.items()},
        "namespace_note": ("rows and by_class count all namespaces (the slim file has every "
                           "September revision). The _ns0 keys count namespace 0 only (page_ns = "
                           "the page's current namespace), like the history cohort."),
        "by_namespace": {str(k): int(v) for k, v in
                         rows["page_ns"].value_counts(dropna=False).sort_index().items()},
        "distinct_reverting_actions": int(rows["reverting_rev_id"].dropna().nunique()),
        "distinct_reverting_actions_ns0": int(ns0["reverting_rev_id"].dropna().nunique()),
        "distinct_pages": int(rows["page_id"].nunique()),
        "distinct_pages_ns0": int(ns0["page_id"].nunique()),
        "top5_pages": top.to_dict("records"),
        "via": {"+".join(k): int(v) for k, v in rows["via"].map(tuple).value_counts().items()},
        "restored_later": {str(k): int(v) for k, v in rows["restored_later"].value_counts(dropna=False).items()},
        "method_unknown_by_period": tag_only_period,
        "in_history_cohort": int(rows["in_history_cohort"].sum()),   # namespace 0 by definition
        "in_history_cohort_by_class": {k: int(v) for k, v in rows[rows["in_history_cohort"]]["class"].value_counts().items()},
        "in_history_cohort_method": cohort_method,
        "median_age_days_by_class": age,
        "age_note": "age is from the reverting rev_dt; for method_unknown rows it uses the tag time (an upper bound).",
        "rows_where_every_cover_is_beyond_newest": {k: int(v) for k, v in rows.loc[rows_only_beyond, "class"].value_counts().items()},
        "step1": {"revert_events": int(len(E)), "covering_pairs": int(len(P)),
                  "pairs_by_method": {f"{m}|{x}": int(v) for (m, x), v in P.groupby(["e_method", "e_exact"]).size().items()}},
        "step2": {"mw_reverted_additions_on_sept_not_reverted": int(len(T)),
                  "linked_within_window": int(T["linked"].sum()),
                  "not_linked": int((~T["linked"]).sum()),
                  "window_s": config.LATE_TAG_LINK_WINDOW_S},
        "september_input": sept_stats,
        "lower_bound_note": (f"All counts are lower bounds: nobody watched the stream from "
                             f"{iso(config.HISTORY_DUMP_LAST_REVISION)} (the dump's last revision) until the "
                             f"capture started (page_change: {capture_starts.get('page_change')}, "
                             f"tags: {capture_starts.get('tags')})."),
        "capture_starts": capture_starts,
    }


def write_json(obj: dict, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str) + "\n")
    os.replace(tmp, path)


def run(parsed_dir: Path = config.PARSED_DIR, tables_dir: Path = config.TABLES_DIR,
        history_dir: Path = config.HISTORY_DIR) -> dict:
    for need in (parsed_dir / "_SUCCESS_parsed.json", tables_dir / "_SUCCESS_live.json"):
        if not need.exists():
            raise SystemExit(f"Missing {need}. Run parse_stream.py and label_live.py first.")
    t0 = time.time()
    pcdf = load_page_change(parsed_dir / "page_change.parquet")
    capture_starts = {"page_change": iso(pcdf["meta_dt"].min()),
                      "page_change_newest": iso(pcdf["meta_dt"].max())}
    E, _ = revert_events(pcdf)
    titles = pcdf.sort_values("meta_dt").drop_duplicates("page_id", keep="last").set_index("page_id")["page_title"]
    del pcdf
    tags = pd.read_parquet(parsed_dir / "tag_events.parquet",
                           columns=["meta_id", "meta_dt", "rev_id", "page_id", "mw_reverted_added"])
    capture_starts["tags"] = iso(tags["meta_dt"].min())
    mw = tags[tags["mw_reverted_added"]].reset_index(drop=True)
    del tags
    log.info("revert events: %s, mw-reverted additions: %s", f"{len(E):,}", f"{len(mw):,}")

    sept, sept_stats = load_september(history_dir / config.HISTORY_SLIM_FILE,
                                      E["page_id"].dropna().astype("int64"), mw["rev_id"])
    log.info("September rows on candidate pages, not reverted in the dump: %s", f"{len(sept):,}")
    P = cover_pairs(sept, E)
    T = link_tags(mw[mw["rev_id"].isin(set(sept["rev_id"]))], P)
    links_all = pd.read_parquet(tables_dir / "live_revert_links_all.parquet", columns=["reverted_rev_id"])
    restored_ids = set(links_all["reverted_rev_id"])
    in_cohort, cohort_method = history_cohort_ids(tables_dir, sept)
    rows = late_rows(sept, P, T, restored_ids, in_cohort)

    tmp = tables_dir / "late_reverts.parquet.tmp"
    pq.write_table(pa.Table.from_pandas(rows, schema=LATE_SCHEMA, preserve_index=False), tmp, compression="zstd")
    os.replace(tmp, tables_dir / "late_reverts.parquet")
    summary = summarize(rows, P, T, E, titles, sept_stats, cohort_method, capture_starts)
    write_json(summary, tables_dir / "late_reverts_summary.json")
    write_json({"step": "late_reverts", "data_version": config.DATA_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "row_counts": {"late_reverts.parquet": int(len(rows))},
                "lower_bound": True, "seconds": round(time.time() - t0, 1)},
               tables_dir / "_SUCCESS_late_reverts.json")
    print_summary(summary)
    return summary


def print_summary(s: dict) -> None:
    print("\n=== Late reverts (September revisions reverted in October) ===")
    print(f"rows (all namespaces): {s['rows']:,}   by class: {s['by_class']}")
    print(f"rows (namespace 0):    {s['rows_ns0']:,}   by class: {s['by_class_ns0']}")
    print(f"rows by namespace: {s['by_namespace']}")
    print(f"distinct reverting actions: {s['distinct_reverting_actions']:,}   distinct pages: {s['distinct_pages']:,}")
    print("top 5 pages by rows:")
    for p in s["top5_pages"]:
        print(f"   {p['page_id']:>10}  {p['page_title']!s:<50} rows={p['rows']}  exact={p['exact']}"
              f"  inexact_undo={p['inexact_undo']}  method_unknown={p['method_unknown']}")
    print(f"via: {s['via']}   restored_later: {s['restored_later']}")
    print(f"in history cohort (Sep 8-10): {s['in_history_cohort']} {s['in_history_cohort_by_class']}"
          f"  [{s['in_history_cohort_method']}]")
    print(f"median age (days) by class: {s['median_age_days_by_class']}")
    print(f"rows where every cover is beyond newest_id: {s['rows_where_every_cover_is_beyond_newest']}")
    print(f"tag link (step 2): {s['step2']}")
    print(f"tag-only rows by capture period: {s['method_unknown_by_period']}")
    print(f"\nNOTE: {s['lower_bound_note']}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    run()


if __name__ == "__main__":
    main()
