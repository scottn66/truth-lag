"""Build the history cohort tables from the VPS-filtered MediaWiki History dump.

Purpose:
    Turn the dump rows for 2026-09-08 to 2026-09-10 (namespace 0) into one clean
    row per revision, with revert labels, the reverter (from a self-join on the
    slim September file) and the page activity in the hour before the edit.
    The columns follow DATA_MODEL.md section 3 exactly.

Inputs (all columns are strings; we cast them with ingest/history_columns.py):
    data/history/enwiki_rev_ns0_2026-09-08_10.parquet  (config.HISTORY_COHORT_FILE, 78 columns)
    data/history/enwiki_rev_all_2026-09_slim.parquet   (config.HISTORY_SLIM_FILE, 12 columns)

Outputs (in config.TABLES_DIR = data/tables/):
    history_revisions.parquet     one row per kept cohort revision
    history_revert_links.parquet  one row per cohort revision with reverted_any = true
    history_summary.json          row counts, drop reasons, revert rates, T, tag agreement
    _SUCCESS_history.json         row counts; written last, only when all else worked

Rules used here (the windows and thresholds come from config.py):
    1. Keep event_entity == revision, event_type == create, ts in config.HISTORY_WINDOW,
       page_namespace_historical == 0.
    2. Drop null revisions (same text as the parent revision):
       (a) the parent revision is in the cohort file and both sha1 values are known:
           compare revision_text_sha1;
       (b) otherwise: revision_text_bytes_diff == 0 AND the comment starts with a
           MediaWiki null-action text (see NULL_REV_COMMENT_PREFIXES). MediaWiki writes
           page moves as "<user name> moved page [[A]] to [[B]]", so we first remove
           the editor's own name from the start of the comment.
    3. reverted = revision_is_identity_reverted AND seconds <= config.HISTORY_FOLLOWUP_S.
    4. page_edits_prev_1h = slim-file revisions on the same page in [ts - 1 h, ts).
    5. page_title = the dump's CURRENT title (column page_title, the same for every
       revision of a page), or page_title_historical when it is null. A vandal can
       move a page to a new title for a few edits; the title at edit time then shows
       the vandal's text, so we keep it only in page_title_historical.

Run (from the repo root; takes about 10 seconds and about 2.5 GB of memory):
    .venv/bin/python ec-hw2/ingest/parse_history.py > data/logs/parse_history.log 2>&1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from ingest.history_columns import (  # noqa: E402
    cast_history_frame,
    sha1_base36_to_hex,
    split_list,
)

STEP = "history"
OUT_REVISIONS = "history_revisions.parquet"
OUT_LINKS = "history_revert_links.parquet"
OUT_SUMMARY = "history_summary.json"
OUT_SUCCESS = f"_SUCCESS_{STEP}.json"

# Rule (b) prefixes and the 1-hour window live in config.py (one place for every rule).
NULL_REV_COMMENT_PREFIXES = config.NULL_REV_COMMENT_PREFIXES
PREV_WINDOW_S = config.PAGE_PREV_WINDOW_S
TOP_PAGES = 5

# Slim-file columns we need. We read only these, to save memory.
SLIM_TIME_COLS = ["page_id", "event_timestamp"]
SLIM_REVERTER_COLS = ["revision_id", "page_id", "event_timestamp", "event_user_id",
                      "event_user_text_historical", "event_user_is_bot_by"]

# Time-to-revert buckets for the tag check. Lower edge included, upper edge not,
# like config.LAG_GRID_S, so "7-20 d" ends at 20 days + 1 s.
T_BUCKETS = [
    ("<1 h", 0, 3600),
    ("1 h-1 d", 3600, 86400),
    ("1-7 d", 86400, 7 * 86400),
    ("7-20 d", 7 * 86400, config.HISTORY_FOLLOWUP_S + 1),
    (">20 d", config.HISTORY_FOLLOWUP_S + 1, None),
]

# Final column order of history_revisions.parquet (DATA_MODEL.md section 3).
REVISION_COLUMNS = [
    "cohort", "wiki_db", "rev_id", "parent_id", "page_id", "page_title",
    "page_title_historical", "page_ns", "ts", "seen_ts", "hour_utc", "size", "size_delta",
    "comment", "tags",
    "mw_reverted_tag", "mw_reverted_at", "is_revert", "revert_method",
    "user_id", "user_name", "user_kind", "user_key", "is_bot", "is_temp", "is_anon",
    "edit_count", "sha1", "revert_risk", "page_edits_prev_1h", "followup_s",
    "reverted", "reverted_any", "secs_to_revert", "reverting_rev_id",
    "reverter_key", "reverter_name", "reverter_kind", "reverted_by_other",
]
LINK_COLUMNS = [
    "cohort", "source", "reverted_rev_id", "page_id", "reverted_ts", "author_key",
    "author_kind", "reverting_rev_id", "reverting_ts", "reverter_key", "reverter_name",
    "reverter_kind", "T_s", "known_at", "K_s", "method", "is_exact", "by_other",
    "within_followup", "range_size", "range_complete", "confirmed_by_tag",
]

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
ONE_S = pd.Timedelta(1, unit="s")


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _py(x):
    """Turn a pandas missing value (NA, NaN, NaT) into None.

    The config helpers test "is None"; pd.NA is not None and bool(pd.NA) fails.
    """
    if x is None or x is pd.NA:
        return None
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def _to_seconds(ts: pd.Series) -> np.ndarray:
    """UTC times to whole seconds since 1970 (int64). The dump has whole seconds."""
    return ((ts - EPOCH) // ONE_S).to_numpy(dtype="int64")


def _null_times(n: int, index) -> pd.Series:
    return pd.Series(pd.NaT, index=index, dtype="datetime64[ns, UTC]")


def _write_parquet_safe(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def _write_json_safe(obj, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)
        f.write("\n")
    os.replace(tmp, path)


def _log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------
# Step 1: filters and null revisions
# --------------------------------------------------------------------------
def filter_cohort(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply the entity, window and namespace filters. Return (kept rows, drops)."""
    drops = {}
    start, end = config.HISTORY_WINDOW

    keep = (df["event_entity"] == "revision") & (df["event_type"] == "create")
    keep = keep.fillna(False).astype(bool)
    drops["not_revision_create"] = int((~keep).sum())
    df = df[keep]

    ts = df["event_timestamp"]
    keep = ((ts >= start) & (ts < end)).fillna(False).astype(bool)
    drops["outside_window"] = int((~keep).sum())
    df = df[keep]

    keep = (df["page_namespace_historical"] == 0).fillna(False).astype(bool)
    drops["namespace_historical_not_0"] = int((~keep).sum())
    df = df[keep]
    return df, drops


def comment_null_prefix(comment: pd.Series, user_name: pd.Series) -> pd.Series:
    """Return the null-action prefix that the comment starts with, or None.

    The check is case-insensitive. A leading "<user name> " is removed first,
    because page moves read "<user name> moved page [[A]] to [[B]]".
    """
    c = comment.astype("string").fillna("").str.lower().tolist()
    n = user_name.astype("string").fillna("").str.lower().tolist()
    found = []
    for text, name in zip(c, n):
        if name and text.startswith(name + " "):
            text = text[len(name) + 1:]
        hit = None
        for p in NULL_REV_COMMENT_PREFIXES:
            if text.startswith(p):
                hit = p
                break
        found.append(hit)
    return pd.Series(found, index=comment.index, dtype="object")


def null_revision_masks(df: pd.DataFrame, full: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (rule_a, rule_b, rule_b_prefix) for the rows of df.

    full is the whole cast cohort file; we look up parent sha1 values there,
    so a parent in another namespace (for example a draft) still counts.
    """
    sha_by_rev = full.set_index("revision_id")["revision_text_sha1"]
    parent_in = df["revision_parent_id"].isin(full["revision_id"]).fillna(False).astype(bool)
    parent_sha = df["revision_parent_id"].map(sha_by_rev)
    own_sha = df["revision_text_sha1"]
    a_applies = parent_in & own_sha.notna() & parent_sha.notna()
    rule_a = a_applies & (own_sha.astype("string") == parent_sha.astype("string")).fillna(False)
    rule_a = rule_a.astype(bool)

    prefix = comment_null_prefix(df["event_comment"], df["event_user_text_historical"])
    zero_diff = (df["revision_text_bytes_diff"] == 0).fillna(False).astype(bool)
    rule_b = (~a_applies) & zero_diff & prefix.notna()
    rule_b = rule_b.astype(bool)
    return rule_a, rule_b, prefix.where(rule_b)


# --------------------------------------------------------------------------
# Steps 2-3: user fields and labels
# --------------------------------------------------------------------------
def add_user_fields(df: pd.DataFrame) -> pd.DataFrame:
    names = df["event_user_text_historical"].astype(object).tolist()
    bots = df["event_user_is_bot_by"].astype(object).tolist()
    temps = df["event_user_is_temporary"].astype(object).tolist()
    ids = df["event_user_id"].astype(object).tolist()
    kinds, keys = [], []
    for name, bot, temp, uid in zip(names, bots, temps, ids):
        kind = config.user_kind(_py(name), _py(bot), _py(temp))
        kinds.append(kind)
        keys.append(config.editor_key(kind, _py(uid), _py(name)))
    df = df.copy()
    df["user_kind"] = pd.Series(kinds, index=df.index, dtype="string")
    df["user_key"] = pd.Series(keys, index=df.index, dtype="string")
    df["is_bot"] = (df["user_kind"] == "bot").astype(bool)
    df["is_temp"] = (df["user_kind"] == "temporary").astype(bool)
    df["is_anon"] = df["is_temp"]
    return df


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["reverted_any"] = df["revision_is_identity_reverted"].fillna(False).astype(bool)
    df["secs_to_revert"] = df["revision_seconds_to_identity_revert"].astype("Int64")
    df["reverting_rev_id"] = df["revision_first_identity_reverting_revision_id"].astype("Int64")
    within = (df["secs_to_revert"] <= config.HISTORY_FOLLOWUP_S).fillna(False).astype(bool)
    df["reverted"] = df["reverted_any"] & within
    return df


# --------------------------------------------------------------------------
# Step 4: reverter self-join
# --------------------------------------------------------------------------
def read_slim_reverters(slim_path: Path, rev_ids) -> pd.DataFrame:
    """Read only the slim rows whose revision_id is in rev_ids, then cast them."""
    ids = sorted({str(int(x)) for x in rev_ids if _py(x) is not None})
    if not ids:
        empty = pd.DataFrame({c: pd.Series([], dtype="object") for c in SLIM_REVERTER_COLS})
        return cast_history_frame(empty)
    tbl = pq.read_table(slim_path, columns=SLIM_REVERTER_COLS,
                        filters=[("revision_id", "in", ids)])
    return cast_history_frame(tbl.to_pandas())


def join_reverters(df: pd.DataFrame, slim_rev: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Add reverter_name / kind / key and reverted_by_other. Return (df, check counts)."""
    if slim_rev["revision_id"].duplicated().any():
        raise ValueError("slim file has duplicate revision_id values")
    right = slim_rev.rename(columns={
        "revision_id": "reverting_rev_id",
        "page_id": "_r_page_id",
        "event_timestamp": "_r_ts",
        "event_user_id": "_r_user_id",
        "event_user_text_historical": "_r_name",
        "event_user_is_bot_by": "_r_bot_by",
    })
    right["_r_found"] = True
    out = df.merge(right, on="reverting_rev_id", how="left", validate="many_to_one")
    out.index = df.index
    found = out["_r_found"].notna()

    kinds, keys = [], []
    for ok, name, bot, uid in zip(found.tolist(), out["_r_name"].astype(object).tolist(),
                                  out["_r_bot_by"].astype(object).tolist(),
                                  out["_r_user_id"].astype(object).tolist()):
        if not ok:
            kinds.append(None)
            keys.append(None)
            continue
        # The slim file has no temporary-account flag: user_kind uses the "~2" name prefix.
        kind = config.user_kind(_py(name), _py(bot))
        kinds.append(kind)
        keys.append(config.editor_key(kind, _py(uid), _py(name)))
    out["reverter_name"] = out["_r_name"].astype("string").where(found)
    out["reverter_kind"] = pd.Series(kinds, index=out.index, dtype="string")
    out["reverter_key"] = pd.Series(keys, index=out.index, dtype="string")
    both = out["user_key"].notna() & out["reverter_key"].notna()
    out["reverted_by_other"] = (both & (out["user_key"] != out["reverter_key"]).fillna(False)).astype(bool)

    has_id = out["reverting_rev_id"].notna()
    expect_ts = out["event_timestamp"] + pd.to_timedelta(out["secs_to_revert"].astype("float64"), unit="s")
    checks = {
        "reverting_ids": int(has_id.sum()),
        "distinct_reverting_ids": int(out.loc[has_id, "reverting_rev_id"].nunique()),
        "not_found_in_slim": int((has_id & ~found).sum()),
        "not_found_with_T_le_20d": int((has_id & ~found & out["reverted"]).sum()),
        "page_id_differs": int((found & (out["_r_page_id"] != out["page_id"]).fillna(False)).sum()),
        "reverting_ts_differs_from_ts_plus_T": int((found & (out["_r_ts"] != expect_ts).fillna(False)).sum()),
    }
    out = out.drop(columns=[c for c in out.columns if c.startswith("_r_")])
    return out, checks


# --------------------------------------------------------------------------
# Step 5: page activity in the hour before each edit
# --------------------------------------------------------------------------
def count_prev_window(page: np.ndarray, ts_s: np.ndarray, slim_page: np.ndarray,
                      slim_ts_s: np.ndarray, window_s: int = PREV_WINDOW_S) -> np.ndarray:
    """For each (page, ts), count slim rows on the same page with time in [ts - window, ts).

    Vectorised: we build one sorted int64 key = page * span + (seconds - base),
    so all rows of one page sit together in time order. Two binary searches
    per cohort row give the count. The edit itself has time ts, so it is
    never counted (the window ends before ts).
    """
    page = np.asarray(page, dtype="int64")
    ts_s = np.asarray(ts_s, dtype="int64")
    slim_page = np.asarray(slim_page, dtype="int64")
    slim_ts_s = np.asarray(slim_ts_s, dtype="int64")
    if len(page) == 0:
        return np.zeros(0, dtype="int64")
    if len(slim_page) == 0:
        return np.zeros(len(page), dtype="int64")
    base = int(min(slim_ts_s.min(), (ts_s - window_s).min()))
    span = int(max(slim_ts_s.max(), ts_s.max()) - base + 1)
    max_page = int(max(slim_page.max(), page.max()))
    if min(slim_page.min(), page.min()) < 0 or (max_page + 1) * span >= 2**62:
        raise ValueError("page_id or time range too large for the int64 key")
    keys = np.sort(slim_page * span + (slim_ts_s - base))
    hi = np.searchsorted(keys, page * span + (ts_s - base), side="left")
    lo = np.searchsorted(keys, page * span + (ts_s - window_s - base), side="left")
    return (hi - lo).astype("int64")


def read_slim_page_times(slim_path: Path) -> pd.DataFrame:
    tbl = pq.read_table(slim_path, columns=SLIM_TIME_COLS)
    return cast_history_frame(tbl.to_pandas())


# --------------------------------------------------------------------------
# Steps 6-7: the output tables
# --------------------------------------------------------------------------
def build_revisions(df: pd.DataFrame, prev_1h: np.ndarray) -> pd.DataFrame:
    idx = df.index
    tag_lists = [split_list(_py(v)) for v in df["revision_tags"].astype(object).tolist()]
    out = pd.DataFrame(index=idx)
    out["cohort"] = pd.Series(config.COHORT_HISTORY, index=idx, dtype="string")
    out["wiki_db"] = df["wiki_db"].astype("string")
    out["rev_id"] = df["revision_id"].astype("int64")
    out["parent_id"] = df["revision_parent_id"].astype("Int64")
    out["page_id"] = df["page_id"].astype("int64")
    # Display title: the current one (rule 5), so vandal page-move titles are not shown.
    out["page_title"] = df["page_title"].fillna(df["page_title_historical"]).astype("string")
    out["page_title_historical"] = df["page_title_historical"].astype("string")
    out["page_ns"] = df["page_namespace_historical"].astype("int64")
    out["ts"] = df["event_timestamp"]
    out["seen_ts"] = _null_times(len(df), idx)
    out["hour_utc"] = df["event_timestamp"].dt.hour.astype("int64")
    out["size"] = df["revision_text_bytes"].astype("Int64")
    out["size_delta"] = df["revision_text_bytes_diff"].astype("Int64")
    out["comment"] = df["event_comment"].astype("string")
    out["tags"] = pd.Series([[t for t in tl if t != config.MW_REVERTED_TAG] for tl in tag_lists],
                            index=idx, dtype="object")
    out["mw_reverted_tag"] = pd.Series([config.MW_REVERTED_TAG in tl for tl in tag_lists],
                                       index=idx, dtype=bool)
    out["mw_reverted_at"] = _null_times(len(df), idx)
    out["is_revert"] = df["revision_is_identity_revert"].fillna(False).astype(bool)
    out["revert_method"] = pd.Series(pd.NA, index=idx, dtype="string")
    out["user_id"] = df["event_user_id"].astype("Int64")
    out["user_name"] = df["event_user_text_historical"].astype("string")
    out["user_kind"] = df["user_kind"]
    out["user_key"] = df["user_key"]
    out["is_bot"] = df["is_bot"]
    out["is_temp"] = df["is_temp"]
    out["is_anon"] = df["is_anon"]
    out["edit_count"] = df["event_user_revision_count"].astype("Int64")
    out["sha1"] = pd.Series([sha1_base36_to_hex(_py(s)) for s in df["revision_text_sha1"].astype(object)],
                            index=idx, dtype="string")
    out["revert_risk"] = pd.Series(pd.NA, index=idx, dtype="Float64")
    out["page_edits_prev_1h"] = pd.Series(prev_1h, index=idx, dtype="int64")
    last = pd.Timestamp(config.HISTORY_DUMP_LAST_REVISION)
    out["followup_s"] = ((last - df["event_timestamp"]) // ONE_S).astype("int64")
    for col in ["reverted", "reverted_any", "secs_to_revert", "reverting_rev_id",
                "reverter_key", "reverter_name", "reverter_kind", "reverted_by_other"]:
        out[col] = df[col]
    out = out[REVISION_COLUMNS].reset_index(drop=True)
    return out


def build_revert_links(rev: pd.DataFrame) -> pd.DataFrame:
    r = rev[rev["reverted_any"]].reset_index(drop=True)
    idx = r.index
    links = pd.DataFrame(index=idx)
    links["cohort"] = pd.Series(config.COHORT_HISTORY, index=idx, dtype="string")
    links["source"] = pd.Series("dump", index=idx, dtype="string")
    links["reverted_rev_id"] = r["rev_id"].astype("int64")
    links["page_id"] = r["page_id"].astype("int64")
    links["reverted_ts"] = r["ts"]
    links["author_key"] = r["user_key"]
    links["author_kind"] = r["user_kind"]
    links["reverting_rev_id"] = r["reverting_rev_id"].astype("Int64")
    links["reverting_ts"] = r["ts"] + pd.to_timedelta(r["secs_to_revert"].astype("float64"), unit="s")
    links["reverter_key"] = r["reverter_key"]
    links["reverter_name"] = r["reverter_name"]
    links["reverter_kind"] = r["reverter_kind"]
    links["T_s"] = r["secs_to_revert"].astype("Int64")
    links["known_at"] = _null_times(len(r), idx)
    links["K_s"] = pd.Series(pd.NA, index=idx, dtype="Int64")
    links["method"] = pd.Series(pd.NA, index=idx, dtype="string")
    links["is_exact"] = pd.Series(True, index=idx, dtype=bool)
    links["by_other"] = r["reverted_by_other"].astype(bool)
    links["within_followup"] = r["reverted"].astype(bool)
    links["range_size"] = pd.Series(pd.NA, index=idx, dtype="Int64")
    links["range_complete"] = pd.Series(pd.NA, index=idx, dtype="boolean")   # live only
    links["confirmed_by_tag"] = r["mw_reverted_tag"].astype(bool)
    return links[LINK_COLUMNS]


# --------------------------------------------------------------------------
# Step 8: summary (no editor names in it: only kinds, counts and page titles)
# --------------------------------------------------------------------------
def _rate(mask: pd.Series, label: pd.Series) -> dict:
    n = int(mask.sum())
    k = int((mask & label).sum())
    return {"n": n, "reverted": k, "rate": round(k / n, 6) if n else None}


def _t_stats(t: pd.Series) -> dict:
    t = t.dropna().astype("int64").to_numpy()
    if len(t) == 0:
        return {"n": 0}
    med, p90 = np.percentile(t, [50, 90])
    return {
        "n": int(len(t)),
        "median_s": float(med), "median_h": round(float(med) / 3600, 3),
        "p90_s": float(p90), "p90_h": round(float(p90) / 3600, 3), "p90_d": round(float(p90) / 86400, 3),
        "share_T_lt_1h": round(float((t < 3600).mean()), 6),
        "share_T_lt_1d": round(float((t < 86400).mean()), 6),
        "share_T_gt_7d": round(float((t > 7 * 86400).mean()), 6),
    }


def t_bucket(t: pd.Series) -> pd.Series:
    out = pd.Series("not reverted", index=t.index, dtype="object")
    for name, lo, hi in T_BUCKETS:
        m = (t >= lo) if hi is None else ((t >= lo) & (t < hi))
        out[m.fillna(False).astype(bool)] = name
    return out


def summarize(rev: pd.DataFrame, links: pd.DataFrame, rows: dict, join_checks: dict) -> dict:
    s: dict = {
        "step": STEP,
        "made_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_version": config.DATA_VERSION,
        "snapshot": config.HISTORY_SNAPSHOT,
        "window_utc": [config.HISTORY_WINDOW[0].isoformat(), config.HISTORY_WINDOW[1].isoformat()],
        "followup_days": config.HISTORY_FOLLOWUP_DAYS,
        "rows": rows,
        "reverter_join": join_checks,
    }
    s["user_kind_counts"] = {k: int(v) for k, v in rev["user_kind"].value_counts().items()}
    everyone = pd.Series(True, index=rev.index)
    non_bot = rev["user_kind"] != "bot"
    for label in ["reverted", "reverted_any"]:
        lab = rev[label]
        s[f"revert_rate_{label}"] = {
            "all": _rate(everyone, lab),
            "non_bot": _rate(non_bot, lab),
            "by_user_kind": {k: _rate(rev["user_kind"] == k, lab) for k in config.USER_KINDS},
        }
    s["time_to_revert"] = {
        "reverted_le_20d_all": _t_stats(rev.loc[rev["reverted"], "secs_to_revert"]),
        "reverted_le_20d_non_bot": _t_stats(rev.loc[rev["reverted"] & non_bot, "secs_to_revert"]),
        "reverted_any_all": _t_stats(rev.loc[rev["reverted_any"], "secs_to_revert"]),
        "reverted_le_20d_by_author_kind": {
            k: _t_stats(rev.loc[rev["reverted"] & (rev["user_kind"] == k), "secs_to_revert"])
            for k in config.USER_KINDS},
        "note":"within 1 h means T < 3600 s and within 1 d means T < 86400 s (same edges as config.LAG_GRID_S)",
    }
    # Self-reverts: reverter and author are the same editor (both keys known).
    self_rev = {}
    for kind in config.USER_KINDS + ["all"]:
        m = rev["reverted"] & ((rev["user_kind"] == kind) if kind != "all" else True)
        known = m & rev["user_key"].notna() & rev["reverter_key"].notna()
        same = known & (rev["user_key"] == rev["reverter_key"]).fillna(False)
        n_known = int(known.sum())
        self_rev[kind] = {"reverted": int(m.sum()), "reverter_known": n_known, "self": int(same.sum()),
                          "by_other": int((m & rev["reverted_by_other"]).sum()),
                          "self_share": round(int(same.sum()) / n_known, 6) if n_known else None}
    s["self_revert_le_20d_by_author_kind"] = self_rev
    s["reverter_kind_counts_le_20d"] = {
        k: int(v) for k, v in rev.loc[rev["reverted"], "reverter_kind"].fillna("not found").value_counts().items()}
    # Agreement between the dump label and the mw-reverted tag.
    d, t = rev["reverted_any"], rev["mw_reverted_tag"]
    s["tag_agreement"] = {
        "dump_yes_tag_yes": int((d & t).sum()), "dump_yes_tag_no": int((d & ~t).sum()),
        "dump_no_tag_yes": int((~d & t).sum()), "dump_no_tag_no": int((~d & ~t).sum()),
        "agreement_share": round(float((d == t).mean()), 6) if len(rev) else None,
    }
    buckets = t_bucket(rev["secs_to_revert"])
    by_b = {}
    for name in [b[0] for b in T_BUCKETS] + ["not reverted"]:
        m = buckets == name
        n = int(m.sum())
        k = int((m & t).sum())
        by_b[name] = {"n": n, "tag_yes": k, "tag_no": n - k, "tag_share": round(k / n, 6) if n else None}
    s["tag_agreement"]["by_T_bucket"] = by_b
    # Pages with the most reverted (<= 20 d) revisions.
    g = rev.groupby("page_id").agg(title=("page_title", "first"), edits=("rev_id", "size"),
                                   reverted=("reverted", "sum"))
    g = g.reset_index().sort_values(["reverted", "edits", "page_id"], ascending=[False, False, True])
    s["top_pages_by_reverted_le_20d"] = [
        {"page_id": int(r.page_id), "title": str(r.title), "reverted": int(r.reverted), "edits": int(r.edits)}
        for r in g.head(TOP_PAGES).itertuples()]
    p = rev["page_edits_prev_1h"]
    s["page_edits_prev_1h"] = {"mean": round(float(p.mean()), 4) if len(p) else None,
                               "median": float(p.median()) if len(p) else None,
                               "p90": float(p.quantile(0.9)) if len(p) else None,
                               "max": int(p.max()) if len(p) else None,
                               "share_zero": round(float((p == 0).mean()), 6) if len(p) else None}
    s["links"] = {"rows": int(len(links)), "within_followup": int(links["within_followup"].sum()),
                  "by_other": int(links["by_other"].sum()),
                  "within_followup_and_by_other": int((links["within_followup"] & links["by_other"]).sum())}
    s["other_counts"] = {"is_revert": int(rev["is_revert"].sum()),
                         "page_creations_parent_0": int((rev["parent_id"] == 0).fillna(False).sum()),
                         "size_null": int(rev["size"].isna().sum()),
                         "size_delta_null": int(rev["size_delta"].isna().sum()),
                         "pages": int(rev["page_id"].nunique()),
                         "editors_with_key": int(rev["user_key"].nunique())}
    return s


def print_summary(s: dict) -> None:
    _log("== history summary ==")
    r = s["rows"]
    _log(f"cohort file rows: {r['cohort_file_rows']:,}")
    for k, v in r["dropped"].items():
        _log(f"  dropped {k}: {v:,}")
    for k, v in r["null_revision_comment_by_prefix"].items():
        _log(f"    rule (b) prefix '{k}': {v:,}")
    _log(f"rows out: {r['rows_out']:,}; revert links: {s['links']['rows']:,}")
    _log(f"reverter join: {s['reverter_join']}")
    _log(f"user kinds: {s['user_kind_counts']}")
    for label in ["reverted", "reverted_any"]:
        rr = s[f"revert_rate_{label}"]
        _log(f"revert rate ({label}): all {rr['all']['rate']:.4%} of {rr['all']['n']:,}, "
             f"non-bot {rr['non_bot']['rate']:.4%} of {rr['non_bot']['n']:,}")
        for k, v in rr["by_user_kind"].items():
            if v["n"]:
                _log(f"    {k}: {v['rate']:.4%} ({v['reverted']:,} of {v['n']:,})")
    tt = dict(s["time_to_revert"])
    tt.update({f"reverted_le_20d_{k}": v for k, v in tt.pop("reverted_le_20d_by_author_kind").items()})
    for k, v in tt.items():
        if isinstance(v, dict) and v.get("n"):
            _log(f"T {k}: n={v['n']:,} median {v['median_h']} h, p90 {v['p90_h']} h, "
                 f"<1 h {v['share_T_lt_1h']:.2%}, <1 d {v['share_T_lt_1d']:.2%}, >7 d {v['share_T_gt_7d']:.2%}")
    for k, v in s["self_revert_le_20d_by_author_kind"].items():
        _log(f"self-reverts ({k}): {v}")
    _log(f"reverter kinds (<= 20 d): {s['reverter_kind_counts_le_20d']}")
    ta = s["tag_agreement"]
    _log(f"tag agreement: dump yes/tag yes {ta['dump_yes_tag_yes']:,}, dump yes/tag no {ta['dump_yes_tag_no']:,}, "
         f"dump no/tag yes {ta['dump_no_tag_yes']:,}, dump no/tag no {ta['dump_no_tag_no']:,}")
    for k, v in ta["by_T_bucket"].items():
        _log(f"    T {k}: {v}")
    for p in s["top_pages_by_reverted_le_20d"]:
        _log(f"top page: {p['title']} (page_id {p['page_id']}): {p['reverted']} reverted of {p['edits']} edits")
    _log(f"page_edits_prev_1h: {s['page_edits_prev_1h']}")
    _log(f"links: {s['links']}")
    _log(f"other: {s['other_counts']}")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def run(cohort_path: Path, slim_path: Path, out_dir: Path, quiet: bool = False) -> dict:
    t0 = time.time()
    say = (lambda m: None) if quiet else _log
    out_dir.mkdir(parents=True, exist_ok=True)

    say(f"reading {cohort_path.name}")
    full = cast_history_frame(pd.read_parquet(cohort_path))
    n_in = len(full)
    if full["revision_id"].duplicated().any():
        raise ValueError("cohort file has duplicate revision_id values")
    df, drops = filter_cohort(full)
    say(f"after filters: {len(df):,} rows; drops so far {drops}")

    rule_a, rule_b, prefix = null_revision_masks(df, full)
    drops["null_revision_same_sha1"] = int(rule_a.sum())
    drops["null_revision_comment"] = int(rule_b.sum())
    by_prefix = {p: int((prefix == p).sum()) for p in NULL_REV_COMMENT_PREFIXES}
    df = df[~(rule_a | rule_b)]
    say(f"null revisions: rule (a) {int(rule_a.sum()):,}, rule (b) {int(rule_b.sum()):,}; rows left {len(df):,}")
    del full

    df = add_user_fields(df)
    df = add_labels(df)

    say("reading reverter rows from the slim file")
    slim_rev = read_slim_reverters(slim_path, df["reverting_rev_id"].dropna().unique())
    df, join_checks = join_reverters(df, slim_rev)
    say(f"reverter join: {join_checks}")

    say("reading page times from the slim file")
    slim_t = read_slim_page_times(slim_path)
    n_slim = len(slim_t)
    if (slim_t["event_timestamp"].dt.microsecond != 0).any() or (df["event_timestamp"].dt.microsecond != 0).any():
        raise ValueError("times with parts of a second: the prev-1h key needs whole seconds")
    ok = slim_t["page_id"].notna() & slim_t["event_timestamp"].notna()
    prev = count_prev_window(df["page_id"].to_numpy(dtype="int64"), _to_seconds(df["event_timestamp"]),
                             slim_t.loc[ok, "page_id"].to_numpy(dtype="int64"),
                             _to_seconds(slim_t.loc[ok, "event_timestamp"]))
    del slim_t

    rev = build_revisions(df, prev)
    links = build_revert_links(rev)
    if rev["rev_id"].duplicated().any():
        raise ValueError("duplicate rev_id in history_revisions")

    rows = {"cohort_file_rows": n_in, "slim_file_rows": n_slim, "dropped": drops,
            "null_revision_comment_by_prefix": by_prefix, "rows_out": int(len(rev))}
    summary = summarize(rev, links, rows, join_checks)
    summary["seconds"] = round(time.time() - t0, 1)

    _write_parquet_safe(rev, out_dir / OUT_REVISIONS)
    _write_parquet_safe(links, out_dir / OUT_LINKS)
    _write_json_safe(summary, out_dir / OUT_SUMMARY)
    success = {
        "step": STEP,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_version": config.DATA_VERSION,
        "inputs": {cohort_path.name: n_in, slim_path.name: n_slim},
        "rows": {OUT_REVISIONS: int(len(rev)), OUT_LINKS: int(len(links))},
    }
    _write_json_safe(success, out_dir / OUT_SUCCESS)
    if not quiet:
        print_summary(summary)
        say(f"wrote {out_dir / OUT_REVISIONS} ({len(rev):,} rows), {out_dir / OUT_LINKS} ({len(links):,} rows)")
        say(f"done in {summary['seconds']} s")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cohort", type=Path, default=config.HISTORY_DIR / config.HISTORY_COHORT_FILE)
    ap.add_argument("--slim", type=Path, default=config.HISTORY_DIR / config.HISTORY_SLIM_FILE)
    ap.add_argument("--out-dir", type=Path, default=config.TABLES_DIR)
    args = ap.parse_args()
    run(args.cohort, args.slim, args.out_dir)


if __name__ == "__main__":
    main()
