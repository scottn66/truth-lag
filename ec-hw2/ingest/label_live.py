"""Build the live cohort and its revert labels from the parsed stream tables.

Purpose
    1. Make the live cohort: page_change edits and page creations in namespace 0
       with rev_dt in config.LIVE_WINDOW (null revisions dropped).
    2. Find which captured revisions each revert event covers ("range cover",
       DATA_MODEL.md section 3), for all methods and all namespaces.
    3. For each live cohort revision, keep its first covering EXACT revert.
    4. For each revert, range_size = the number of CAPTURED revisions it covers, and
       range_complete = the revert's range starts inside the capture. When
       range_complete is false, the range reaches back before the capture, so
       range_size is only a lower bound.
    The labels are PROVISIONAL until the capture is past config.LIVE_FINAL_AFTER.

Inputs (made by ingest/parse_stream.py)
    data/parsed/page_change.parquet, tag_events.parquet, revert_risk.parquet, _SUCCESS_parsed.json

Outputs (in data/tables/)
    live_revisions.parquet          one row per live cohort revision (no labels)
    live_revert_links.parquet       one row per reverted live cohort revision (first exact revert)
    live_revert_links_all.parquet   every (reverted, reverting) pair, all methods, all namespaces
    live_summary.json               the numbers printed at the end
    _SUCCESS_live.json              row counts, provisional flag, newest meta_dt

Run (from the repo root)
    .venv/bin/python ec-hw2/ingest/label_live.py
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
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from ingest.history_columns import sha1_base36_to_hex  # noqa: E402

log = logging.getLogger("label_live")

EDIT_KINDS = ("create", "edit")
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
ID_BITS = 32                      # rev_id < 2**32; the (time, id) key packs both in one int64
# mw-reverted is only added when a revert covers at most 15 revisions (MediaWiki
# $wgRevertedTagMaxDepth). Not in config.py yet, see the shared change request.
MW_REVERTED_MAX_DEPTH = getattr(config, "MW_REVERTED_MAX_DEPTH", 15)

# Same types as the history tables (ns times, int64 numbers), so both cohorts stack cleanly.
TS = pa.timestamp("ns", tz="UTC")
LIVE_REVISIONS_SCHEMA = pa.schema([
    ("cohort", pa.string()), ("wiki_db", pa.string()), ("rev_id", pa.int64()),
    ("parent_id", pa.int64()), ("page_id", pa.int64()), ("page_title", pa.string()),
    ("page_title_historical", pa.string()), ("page_ns", pa.int64()), ("ts", TS),
    ("seen_ts", TS), ("hour_utc", pa.int64()),
    ("size", pa.int64()), ("size_delta", pa.int64()), ("comment", pa.string()),
    ("tags", pa.list_(pa.string())), ("mw_reverted_tag", pa.bool_()), ("mw_reverted_at", TS),
    ("is_revert", pa.bool_()), ("revert_method", pa.string()), ("user_id", pa.int64()),
    ("user_name", pa.string()), ("user_kind", pa.string()), ("user_key", pa.string()),
    ("is_bot", pa.bool_()), ("is_temp", pa.bool_()), ("is_anon", pa.bool_()),
    ("edit_count", pa.int64()), ("sha1", pa.string()), ("revert_risk", pa.float64()),
    ("page_edits_prev_1h", pa.int64()), ("followup_s", pa.int64()),
])
LINK_FIELDS = [
    ("cohort", pa.string()), ("source", pa.string()), ("reverted_rev_id", pa.int64()),
    ("page_id", pa.int64()), ("reverted_ts", TS), ("author_key", pa.string()),
    ("author_kind", pa.string()), ("reverting_rev_id", pa.int64()), ("reverting_ts", TS),
    ("reverter_key", pa.string()), ("reverter_name", pa.string()), ("reverter_kind", pa.string()),
    ("T_s", pa.int64()), ("known_at", TS), ("K_s", pa.float64()), ("method", pa.string()),
    ("is_exact", pa.bool_()), ("by_other", pa.bool_()), ("within_followup", pa.bool_()),
    ("range_size", pa.int64()), ("range_complete", pa.bool_()), ("confirmed_by_tag", pa.bool_()),
]
LINKS_SCHEMA = pa.schema(LINK_FIELDS)
# links_all also covers revisions outside the cohort (other namespaces, other days).
# beyond_newest: the pair lies after E.revert_newest_id. Only an exact undo of an older
# edit can have it (see range_cover); MediaWiki does not add mw-reverted to these pairs.
LINKS_ALL_SCHEMA = pa.schema(LINK_FIELDS + [("page_ns", pa.int64()), ("in_cohort", pa.bool_()),
                                            ("beyond_newest", pa.bool_())])


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _none(v):
    """NaN / NA / None -> None; numpy scalars -> Python values."""
    if v is None or (not isinstance(v, (str, list, np.ndarray)) and pd.isna(v)):
        return None
    return v.item() if isinstance(v, np.generic) else v


def _bool_or_none(v):
    v = _none(v)
    return None if v is None else bool(v)


def add_user_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add user_kind and user_key with the shared rules in config.

    The flags are turned into plain Python bools first: config.user_kind checks
    isinstance(flag, bool), and a numpy bool would fail that check.
    """
    kinds, keys = [], []
    for name, bot, temp, uid in zip(df["user_name"], df["is_bot"], df["is_temp"], df["user_id"]):
        name = _none(name)
        kind = config.user_kind(name, _bool_or_none(bot), _bool_or_none(temp))
        uid = _none(uid)
        kinds.append(kind)
        keys.append(config.editor_key(kind, None if uid is None else int(uid), name))
    out = df.copy()
    out["user_kind"] = kinds
    out["user_key"] = keys
    return out


def _utc_us(s: pd.Series) -> np.ndarray:
    """A UTC time column as numpy datetime64[us] (no time zone, still UTC)."""
    return s.dt.tz_convert("UTC").dt.tz_localize(None).to_numpy(dtype="datetime64[us]")


def secs(s: pd.Series) -> np.ndarray:
    """Whole seconds since 1970 as float (NaN for a missing time)."""
    v = _utc_us(s)
    out = (v.astype("int64") // 10**6).astype("float64")
    out[np.isnat(v)] = np.nan
    return out


def micros(s: pd.Series) -> np.ndarray:
    """Microseconds since 1970. The column must have no missing time."""
    v = _utc_us(s)
    assert not np.isnat(v).any(), "missing time"
    return v.astype("int64")


def seconds_between(later: pd.Series, earlier: pd.Series) -> pd.Series:
    """later - earlier in seconds (float)."""
    return (later - earlier).dt.total_seconds()


def pair_key(t_secs: np.ndarray, rev_ids: np.ndarray) -> np.ndarray:
    """Pack (time in whole seconds, rev_id) into one int64 that sorts the same way."""
    t = np.asarray(t_secs, dtype="int64")
    i = np.asarray(rev_ids, dtype="int64")
    assert (i >= 0).all() and (i < 2**ID_BITS).all(), "rev_id does not fit in 32 bits"
    assert (t >= 0).all() and (t < 2**31).all(), "time out of range for the packed key"
    return t * 2**ID_BITS + i


BIG_ID = 2**62     # "no limit" value for a missing id (exact as a float, larger than any rev_id)


def ids(s: pd.Series, fill: int = 0) -> np.ndarray:
    """An id column as int64, with `fill` where the id is missing."""
    return pd.to_numeric(s, errors="coerce").astype("float64").fillna(fill).to_numpy(dtype="int64")


def to_int(s: pd.Series, fill=None) -> np.ndarray:
    if fill is not None:
        s = s.fillna(fill)
    return s.to_numpy(dtype="int64")


# --------------------------------------------------------------------------
# Revisions R and revert events E
# --------------------------------------------------------------------------
def load_page_change(path: Path) -> pd.DataFrame:
    # numpy_nullable keeps int columns with gaps as Int64 (not float).
    return pd.read_parquet(path, dtype_backend="numpy_nullable")


def edit_events(pc: pd.DataFrame) -> tuple[pd.DataFrame, int, list]:
    """All captured edits and page creations (all namespaces), one row per rev_id.

    After the meta.id dedupe a rev_id should appear once. If not, we keep the
    earliest meta_dt and report how many rows we dropped.
    """
    ed = pc[pc["kind"].isin(EDIT_KINDS) & pc["rev_id"].notna()]
    ed = ed.sort_values(["rev_id", "meta_dt"], kind="stable")
    dup = ed.duplicated("rev_id", keep="first").to_numpy()
    examples = ed.loc[dup, "rev_id"].head(5).astype("int64").tolist()
    return ed[~dup].reset_index(drop=True), int(dup.sum()), examples


def revert_events(pc: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Every page_change event with a revert, any namespace, one row per rev_id."""
    e = pc[pc["revert_method"].notna() & pc["rev_id"].notna()]
    e = e.sort_values(["rev_id", "meta_dt"], kind="stable")
    dup = e.duplicated("rev_id", keep="first").to_numpy()
    return e[~dup].reset_index(drop=True), int(dup.sum())


def check_newest_parent(E: pd.DataFrame) -> dict:
    """Check E.revert_newest_id == E.parent_id. Return the count and 5 examples."""
    newest = E["revert_newest_id"]
    parent = E["parent_id"]
    bad = (newest.isna() | parent.isna() | (newest != parent)).fillna(True).to_numpy()
    ex = E.loc[bad, ["rev_id", "page_id", "revert_method", "revert_is_exact",
                     "revert_newest_id", "parent_id"]].head(5)
    examples = [{k: _none(v) for k, v in row.items()} for row in ex.to_dict("records")]
    return {"revert_events": int(len(E)), "exceptions": int(bad.sum()), "examples": examples}


def range_cover(R: pd.DataFrame, E: pd.DataFrame) -> pd.DataFrame:
    """Return every (R, E) pair where revert event E covers revision R.

    The rule (DATA_MODEL.md section 3, "Range cover (live)"), on the same page:
      - E exact (the content after E equals the content of the original revision):
            (E.revert_original_dt, E.revert_original_id) < (R.rev_dt, R.rev_id)
                                                        <= (E.prior_rev_dt, E.parent_id)
        so every revision between the original and E is covered, as in the dump's
        identity revert. This includes an exact undo of an OLDER edit
        (revert_newest_id < parent_id): the edits saved after newest_id (typically an
        edit Y and the revert of Y) are also undone by E.
      - E not exact (an inexact undo of an older edit):
            R.rev_id >= E.revert_oldest_id  and  R.rev_id <= E.revert_newest_id
            and (R.rev_dt, R.rev_id) <= (E.prior_rev_dt, E.revert_newest_id)
        The later edits are NOT covered: E kept their content.
        (2026-10-24: the newest_id bound was first added for all reverts; it now
        applies to inexact reverts only.)
      - R.rev_dt < E.rev_dt
    R needs page_id, rev_id, rev_dt. E needs page_id, rev_id, rev_dt, prior_rev_dt,
    parent_id, revert_is_exact, revert_original_id, revert_original_dt,
    revert_oldest_id, revert_newest_id. Times are whole seconds (true for the stream
    and the dump). A missing parent_id falls back to revert_newest_id.

    How: sort R by (page_id, rev_dt, rev_id) once. For each E, binary search inside
    its page's block. This costs O(|E| log |R|) plus the number of pairs.
    Output: r_row, e_row (row positions in R and E) and range_size (pairs per E).
    range_size counts the revisions in R (the CAPTURED revisions), so it is a lower
    bound when the range starts before the capture (range_complete false).
    """
    out_cols = ["r_row", "e_row", "range_size"]
    if len(R) == 0 or len(E) == 0:
        return pd.DataFrame({c: pd.Series(dtype="int64") for c in out_cols})
    R = R.reset_index(drop=True)
    E = E.reset_index(drop=True)
    r_page = to_int(R["page_id"])
    r_key = pair_key(secs(R["rev_dt"]), to_int(R["rev_id"]))
    order = np.lexsort((r_key, r_page))
    r_page, r_key = r_page[order], r_key[order]
    r_ids = to_int(R["rev_id"])[order]
    pages, starts = np.unique(r_page, return_index=True)
    ends = np.append(starts[1:], len(r_page))

    exact = E["revert_is_exact"].fillna(False).to_numpy(dtype=bool)
    usable = (E["page_id"].notna() & E["rev_dt"].notna() & E["prior_rev_dt"].notna()
              & E["revert_newest_id"].notna()).to_numpy(dtype=bool)
    usable &= ~exact | (E["revert_original_dt"].notna() & E["revert_original_id"].notna()).to_numpy(dtype=bool)
    usable &= exact | E["revert_oldest_id"].notna().to_numpy(dtype=bool)

    e_page = to_int(E["page_id"], fill=-1)
    pos = np.searchsorted(pages, e_page)
    pos_c = np.minimum(pos, len(pages) - 1)
    usable &= pages[pos_c] == e_page

    def key_or_zero(t_col, id_col):
        t = secs(E[t_col])
        i = ids(E[id_col])
        t = np.where(np.isnan(t), 0, t)
        return pair_key(t, i)

    # Inclusive upper end: the prior revision (= parent) for exact reverts, newest_id otherwise.
    newest_key = key_or_zero("prior_rev_dt", "revert_newest_id")
    if "parent_id" in E:
        has_parent = E["parent_id"].notna().to_numpy(dtype=bool)
        e_upper = np.where(exact & has_parent, key_or_zero("prior_rev_dt", "parent_id"), newest_key)
    else:
        e_upper = newest_key
    e_lower = key_or_zero("revert_original_dt", "revert_original_id")  # exclusive (exact only)
    e_before = np.where(np.isnan(secs(E["rev_dt"])), 0, secs(E["rev_dt"])).astype("int64") * 2**ID_BITS
    oldest = ids(E["revert_oldest_id"])
    newest = ids(E["revert_newest_id"])

    r_parts, e_parts = [], []
    for i in np.flatnonzero(usable):
        s, t = starts[pos_c[i]], ends[pos_c[i]]
        keys = r_key[s:t]
        hi = min(np.searchsorted(keys, e_upper[i], "right"),
                 np.searchsorted(keys, e_before[i], "left"))     # R.rev_dt < E.rev_dt
        if exact[i]:
            lo = np.searchsorted(keys, e_lower[i], "right")
            idx = np.arange(s + lo, s + hi) if hi > lo else np.empty(0, dtype="int64")
        else:
            idx = np.arange(s, s + hi)
            idx = idx[(r_ids[idx] >= oldest[i]) & (r_ids[idx] <= newest[i])]
        if len(idx):
            r_parts.append(order[idx])
            e_parts.append(np.full(len(idx), i, dtype="int64"))
    if not r_parts:
        return pd.DataFrame({c: pd.Series(dtype="int64") for c in out_cols})
    pairs = pd.DataFrame({"r_row": np.concatenate(r_parts), "e_row": np.concatenate(e_parts)})
    pairs["range_size"] = pairs.groupby("e_row")["r_row"].transform("size").astype("int64")
    return pairs


def range_complete_flags(E: pd.DataFrame, captured: pd.DataFrame) -> pd.Series:
    """For each revert event E: does its range start inside the capture?

    True when E.revert_oldest_id is a captured revision on E's page, or when
    oldest_id >= the first captured rev_id of that page (rev_ids grow with time, so
    every revision of the range was saved after the page's first captured edit).
    False means the revert reaches back before the capture: range_size, which counts
    captured revisions only, is then a lower bound of the true size.
    captured needs page_id and rev_id (all captured edits, all namespaces).
    """
    oldest = pd.to_numeric(E["revert_oldest_id"], errors="coerce")
    page = pd.to_numeric(E["page_id"], errors="coerce")
    cap = captured[["page_id", "rev_id"]].dropna().astype("int64")
    page_of_rev = cap.drop_duplicates("rev_id").set_index("rev_id")["page_id"]
    first_rev = cap.groupby("page_id")["rev_id"].min()
    on_page = (oldest.map(page_of_rev) == page).fillna(False).astype(bool)
    after_first = (oldest >= page.map(first_rev)).fillna(False).astype(bool)
    return (on_page | after_first).rename("range_complete")


# --------------------------------------------------------------------------
# Live cohort columns
# --------------------------------------------------------------------------
def save_time_tags(revs: pd.DataFrame, tags: pd.DataFrame,
                   window_s: int = config.SAVE_TIME_TAG_WINDOW_S) -> pd.Series:
    """Union of tags from tag events with meta_dt <= rev ts + window, without mw-reverted.

    revs needs rev_id and ts. Returns a Series rev_id -> sorted list of tags.
    """
    t = tags[["rev_id", "meta_dt", "tags"]].merge(revs[["rev_id", "ts"]], on="rev_id")
    t = t[micros(t["meta_dt"]) <= micros(t["ts"]) + window_s * 10**6]
    ex = t[["rev_id", "tags"]].explode("tags").dropna(subset=["tags"])
    ex = ex[ex["tags"] != config.MW_REVERTED_TAG].drop_duplicates()
    ex = ex.sort_values(["rev_id", "tags"], kind="stable")
    return ex.groupby("rev_id")["tags"].agg(list)


def first_mw_reverted(tags: pd.DataFrame) -> pd.Series:
    """rev_id -> meta_dt of the first mw-reverted addition (any time in the capture)."""
    m = tags[tags["mw_reverted_added"].fillna(False).astype(bool)]
    return m.groupby("rev_id")["meta_dt"].min()


def count_in_window(ev_page, ev_t, q_page, q_lo, q_hi) -> np.ndarray:
    """For each query, count events with page == q_page and q_lo <= t < q_hi (ints)."""
    ev_page, ev_t = np.asarray(ev_page, "int64"), np.asarray(ev_t, "int64")
    q_page, q_lo, q_hi = (np.asarray(x, "int64") for x in (q_page, q_lo, q_hi))
    if len(q_page) == 0:
        return np.zeros(0, dtype="int64")
    if len(ev_page) == 0:
        return np.zeros(len(q_page), dtype="int64")
    pages, codes = np.unique(ev_page, return_inverse=True)
    pos = np.searchsorted(pages, q_page)
    pos_c = np.minimum(pos, len(pages) - 1)
    known = pages[pos_c] == q_page
    t0 = min(ev_t.min(), q_lo.min())
    span = max(ev_t.max(), q_hi.max()) - t0 + 1
    bits_t = int(span).bit_length()
    assert bits_t + int(len(pages)).bit_length() <= 62, "packed key too large"
    ev_key = np.sort((codes.astype("int64") << bits_t) | (ev_t - t0))
    lo_key = (pos_c.astype("int64") << bits_t) | (np.maximum(q_lo, t0) - t0)
    hi_key = (pos_c.astype("int64") << bits_t) | (np.maximum(q_hi, t0) - t0)
    n = np.searchsorted(ev_key, hi_key, "left") - np.searchsorted(ev_key, lo_key, "left")
    return np.where(known, n, 0).astype("int64")


def build_cohort(ed: pd.DataFrame, n_dup_rev: int) -> tuple[pd.DataFrame, dict]:
    """Apply the live cohort rules to the edit events. Returns (cohort rows, drop counts)."""
    drops = {"duplicate_rev_id": n_dup_rev}
    c = ed[ed["ns"] == 0]
    drops["namespace_not_0"] = int(len(ed) - len(c))
    w0, w1 = config.LIVE_WINDOW
    inside = (c["rev_dt"] >= w0) & (c["rev_dt"] < w1)
    drops["outside_window"] = int((~inside).sum())
    c = c[inside]
    null_rev = ((c["kind"] == "edit") & c["sha1"].notna() & (c["sha1"] == c["prior_sha1"])).fillna(False)
    drops["null_revision"] = int(null_rev.sum())
    c = c[~null_rev.to_numpy(dtype=bool)]
    return c.reset_index(drop=True), drops


def live_revisions(c: pd.DataFrame, ed: pd.DataFrame, tags: pd.DataFrame, risk: pd.DataFrame,
                   newest_meta_dt: pd.Timestamp) -> pd.DataFrame:
    """Make the columns of DATA_MODEL.md section 3 for the live cohort rows c."""
    out = pd.DataFrame({
        "cohort": config.COHORT_LIVE,
        "wiki_db": c["wiki_id"].astype(object),
        "rev_id": c["rev_id"].astype("int64"),
        "parent_id": c["parent_id"].astype("Int64"),
        "page_id": c["page_id"].astype("int64"),
        "page_title": c["page_title"].astype(object),
        # The stream only has the title at edit time, so both title columns are equal.
        "page_title_historical": c["page_title"].astype(object),
        "page_ns": c["ns"].astype("int64"),
        "ts": c["rev_dt"],
        "seen_ts": c["meta_dt"],
    })
    out["hour_utc"] = out["ts"].dt.hour.astype("int64")
    out["size"] = c["rev_size"].astype("Int64")
    is_create = (c["kind"] == "create").to_numpy(dtype=bool)
    delta = c["rev_size"].astype("Int64") - c["prior_rev_size"].astype("Int64")
    out["size_delta"] = delta.where(~is_create, c["rev_size"].astype("Int64"))
    out["comment"] = c["comment"].astype(object)
    tag_lists = save_time_tags(out[["rev_id", "ts"]], tags)
    out["tags"] = [list(x) if isinstance(x, list) else [] for x in out["rev_id"].map(tag_lists)]
    mw_at = first_mw_reverted(tags)
    out["mw_reverted_at"] = out["rev_id"].map(mw_at)
    out["mw_reverted_tag"] = out["mw_reverted_at"].notna()
    out["is_revert"] = c["revert_method"].notna().to_numpy(dtype=bool)
    out["revert_method"] = c["revert_method"].astype(object)
    out["user_id"] = c["user_id"].astype("Int64")
    out["user_name"] = c["user_name"].astype(object)
    out["user_kind"] = c["user_kind"].to_numpy()
    out["user_key"] = c["user_key"].to_numpy()
    out["is_bot"] = out["user_kind"] == "bot"
    out["is_temp"] = out["user_kind"] == "temporary"
    out["is_anon"] = out["is_temp"]          # the spec's is_anon = logged out = temporary
    out["edit_count"] = c["edit_count"].astype("Int64")
    # The stream sends sha1 in base 36 (as the dump does); both tables store hex.
    out["sha1"] = [sha1_base36_to_hex(_none(s)) for s in c["sha1"]]
    out["revert_risk"] = out["rev_id"].map(risk.set_index("rev_id")["prob_true"]).astype("float64")
    out["page_edits_prev_1h"] = count_in_window(
        to_int(ed["page_id"]), micros(ed["meta_dt"]),
        out["page_id"].to_numpy(), micros(out["seen_ts"]) - 3600 * 10**6, micros(out["seen_ts"]))
    out["followup_s"] = np.floor((newest_meta_dt - out["ts"]).dt.total_seconds()).astype("int64")
    return out[[f.name for f in LIVE_REVISIONS_SCHEMA]]


# --------------------------------------------------------------------------
# Revert links
# --------------------------------------------------------------------------
def build_links_all(R: pd.DataFrame, E: pd.DataFrame, pairs: pd.DataFrame,
                    cohort_ids: set, mw_ids: set) -> pd.DataFrame:
    """One row per covering (R, E) pair, with the DATA_MODEL link columns."""
    r = R.iloc[pairs["r_row"].to_numpy()].reset_index(drop=True)
    e = E.iloc[pairs["e_row"].to_numpy()].reset_index(drop=True)
    L = pd.DataFrame({
        "reverted_rev_id": r["rev_id"].astype("int64"),
        "page_id": r["page_id"].astype("int64"),
        "reverted_ts": r["rev_dt"],
        "author_key": r["user_key"].astype(object),
        "author_kind": r["user_kind"].astype(object),
        "reverting_rev_id": e["rev_id"].astype("int64"),
        "reverting_ts": e["rev_dt"],
        "reverter_key": e["user_key"].astype(object),
        "reverter_name": e["user_name"].astype(object),
        "reverter_kind": e["user_kind"].astype(object),
        "known_at": e["meta_dt"],
        "method": e["revert_method"].astype(object),
        "is_exact": e["revert_is_exact"].fillna(False).astype(bool),
        "range_size": pairs["range_size"].to_numpy(dtype="int64"),
        "range_complete": e["range_complete"].fillna(False).astype(bool).to_numpy(),
        "page_ns": r["ns"].astype("int64"),
    })
    L["T_s"] = np.floor(seconds_between(L["reverting_ts"], L["reverted_ts"])).astype("int64")
    L["K_s"] = seconds_between(L["known_at"], L["reverting_ts"]).astype("float64")
    # An exact undo of an older edit also covers the edits saved after newest_id
    # (see range_cover). We flag these pairs: MediaWiki's own range stops at newest_id.
    L["beyond_newest"] = (L["reverted_rev_id"].to_numpy()
                          > ids(e["revert_newest_id"], fill=BIG_ID))
    L["by_other"] = (L["author_key"].notna() & L["reverter_key"].notna()
                     & (L["author_key"] != L["reverter_key"])).astype(bool)
    L["within_followup"] = L["T_s"] <= config.LIVE_FOLLOWUP_S
    L["confirmed_by_tag"] = L["reverted_rev_id"].isin(mw_ids)
    L["in_cohort"] = L["reverted_rev_id"].isin(cohort_ids)
    L["cohort"] = np.where(L["in_cohort"], config.COHORT_LIVE, None)
    L["source"] = "stream"
    return L.sort_values(["reverted_rev_id", "reverting_ts", "reverting_rev_id"],
                         kind="stable").reset_index(drop=True)


def first_exact_links(links_all: pd.DataFrame) -> pd.DataFrame:
    """For each live cohort revision, its first covering exact revert by (rev_dt, rev_id)."""
    x = links_all[links_all["in_cohort"] & links_all["is_exact"]]
    x = x.sort_values(["reverted_rev_id", "reverting_ts", "reverting_rev_id"], kind="stable")
    x = x.drop_duplicates("reverted_rev_id", keep="first")
    return x[[f.name for f in LINKS_SCHEMA]].reset_index(drop=True)


# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
def _share(k, n):
    return None if n == 0 else round(k / n, 6)


def _confirmed(links: pd.DataFrame) -> dict:
    k = int(links["confirmed_by_tag"].sum())
    return {"n": int(len(links)), "confirmed": k, "share": _share(k, len(links))}


def _pct(s: pd.Series, qs=(50, 90, 99)) -> dict:
    s = s.dropna()
    if s.empty:
        return {f"p{q}": None for q in qs} | {"n": 0}
    return {f"p{q}": round(float(np.percentile(s, q)), 3) for q in qs} | {"n": int(len(s))}


def summarize(rev: pd.DataFrame, links: pd.DataFrame, links_all: pd.DataFrame, E: pd.DataFrame,
              drops: dict, newest_check: dict, n_events_in: int, newest: pd.Timestamp) -> dict:
    n = len(rev)
    within = links[links["within_followup"]]
    rev_l = rev[["rev_id", "user_kind", "mw_reverted_tag"]].merge(
        within[["reverted_rev_id", "by_other"]], left_on="rev_id", right_on="reverted_rev_id", how="left")
    rev_l["reverted"] = rev_l["reverted_rev_id"].notna()
    rev_l["reverted_by_other"] = rev_l["reverted"] & rev_l["by_other"].eq(True)
    by_kind = {}
    for kind in config.USER_KINDS:
        g = rev_l[rev_l["user_kind"] == kind]
        by_kind[kind] = {"n": int(len(g)), "reverted": int(g["reverted"].sum()),
                         "share": _share(int(g["reverted"].sum()), len(g)),
                         "share_by_other": _share(int(g["reverted_by_other"].sum()), len(g))}
    complete = within[within["range_complete"]]
    incomplete = within[~within["range_complete"]]
    small = complete[complete["range_size"] <= MW_REVERTED_MAX_DEPTH]
    large = complete[complete["range_size"] > MW_REVERTED_MAX_DEPTH]
    tagged = rev[rev["mw_reverted_tag"]]
    any_cover = set(links_all.loc[links_all["in_cohort"], "reverted_rev_id"])
    exact_cover = set(links["reverted_rev_id"])
    edits = rev[rev["parent_id"].fillna(0) != 0]
    first_e = links.drop_duplicates("reverting_rev_id")
    e_k = seconds_between(E["meta_dt"], E["rev_dt"])
    return {
        "provisional": bool(newest < config.LIVE_FINAL_AFTER),
        "newest_meta_dt": newest.isoformat().replace("+00:00", "Z"),
        "live_final_after": config.LIVE_FINAL_AFTER.isoformat().replace("+00:00", "Z"),
        "live_window": [config.LIVE_WINDOW[0].isoformat(), config.LIVE_WINDOW[1].isoformat()],
        "cohort": {"page_change_events": n_events_in, "rows": n, "drops": drops},
        "revert_share_exact_within_followup": {
            "overall": {"n": n, "reverted": int(rev_l["reverted"].sum()),
                        "share": _share(int(rev_l["reverted"].sum()), n),
                        "share_by_other": _share(int(rev_l["reverted_by_other"].sum()), n)},
            "by_user_kind": by_kind,
            "human_share": _share(int(rev_l.loc[rev_l["user_kind"] != "bot", "reverted"].sum()),
                                  int((rev_l["user_kind"] != "bot").sum())),
        },
        "median_T_s": {"within_followup": None if within.empty else float(within["T_s"].median()),
                       "all_exact_links": None if links.empty else float(links["T_s"].median())},
        "median_T_hours_within_followup": None if within.empty else round(float(within["T_s"].median()) / 3600, 3),
        "tag_confirmed_share_of_reverted": {
            "mw_reverted_max_depth": MW_REVERTED_MAX_DEPTH,
            "complete_ranges_only": True,
            "range_size_le_max": _confirmed(small),
            "range_size_gt_max": _confirmed(large),
            "range_incomplete": _confirmed(incomplete),
            "note": ("Cohort links within the follow-up. range_size counts CAPTURED revisions. "
                     "The two range_size rows use complete ranges only (range_complete: the "
                     "revert's range starts inside the capture). range_incomplete: reverts that "
                     "reach back before the capture; their true size is unknown and range_size "
                     "is a lower bound, so they are not split by size."),
        },
        "tagged_revisions_found_by_cover": {
            "cohort_revisions_with_mw_reverted": int(len(tagged)),
            "found_by_exact_cover": int(tagged["rev_id"].isin(exact_cover).sum()),
            "found_by_any_cover": int(tagged["rev_id"].isin(any_cover).sum()),
            "share_exact": _share(int(tagged["rev_id"].isin(exact_cover).sum()), len(tagged)),
            "share_any": _share(int(tagged["rev_id"].isin(any_cover).sum()), len(tagged)),
        },
        "K_s": {"distinct_reverts_in_links": _pct(first_e["K_s"]), "all_revert_events": _pct(e_k)},
        "revert_risk_coverage": {
            "cohort_edits": int(len(edits)), "edits_with_score": int(edits["revert_risk"].notna().sum()),
            "share_edits": _share(int(edits["revert_risk"].notna().sum()), len(edits)),
            "share_all_rows": _share(int(rev["revert_risk"].notna().sum()), n),
        },
        "newest_id_equals_parent_check": newest_check | {
            "pairs_beyond_newest_all": int(links_all["beyond_newest"].sum()),
            "pairs_beyond_newest_on_cohort_revisions": int(
                (links_all["beyond_newest"] & links_all["in_cohort"]).sum()),
            "cohort_links_beyond_newest": int(len(links.merge(
                links_all.loc[links_all["beyond_newest"], ["reverted_rev_id", "reverting_rev_id"]],
                on=["reverted_rev_id", "reverting_rev_id"]))),
            "note": ("When newest_id != parent_id, the revert is an undo of an older edit. "
                     "An inexact undo covers only [oldest_id, newest_id]: it kept the later edits. "
                     "An exact undo restores the original content, so it also covers the edits "
                     "saved after newest_id up to the parent, as the dump's identity revert does; "
                     "links_all flags these pairs as beyond_newest (MediaWiki does not add "
                     "mw-reverted to them)."),
        },
        "revert_events": {"total": int(len(E)),
                          "by_method_exact": {f"{m}|{x}": int(v) for (m, x), v in
                                              E.groupby(["revert_method", "revert_is_exact"]).size().items()}},
        "links": {"all_pairs": int(len(links_all)), "pairs_with_cohort_revision": int(links_all["in_cohort"].sum()),
                  "cohort_links_first_exact": int(len(links)),
                  "cohort_links_within_followup": int(len(within)),
                  "cohort_revisions_with_any_cover": int(len(any_cover)),
                  "cohort_links_range_complete": int(links["range_complete"].sum()),
                  "cohort_links_range_incomplete": int((~links["range_complete"]).sum())},
    }


# --------------------------------------------------------------------------
# IO
# --------------------------------------------------------------------------
def write_parquet(df: pd.DataFrame, schema: pa.Schema, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    pq.write_table(pa.Table.from_pandas(df, schema=schema, preserve_index=False), tmp, compression="zstd")
    os.replace(tmp, path)


def write_json(obj: dict, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str) + "\n")
    os.replace(tmp, path)


def run(parsed_dir: Path = config.PARSED_DIR, tables_dir: Path = config.TABLES_DIR) -> dict:
    ok = parsed_dir / "_SUCCESS_parsed.json"
    if not ok.exists():
        raise SystemExit(f"Missing {ok}. Run ingest/parse_stream.py first.")
    tables_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    pc = load_page_change(parsed_dir / "page_change.parquet")
    tags = pd.read_parquet(parsed_dir / "tag_events.parquet",
                           columns=["rev_id", "meta_dt", "tags", "mw_reverted_added"])
    risk = pd.read_parquet(parsed_dir / "revert_risk.parquet", columns=["rev_id", "prob_true"])
    newest = pc["meta_dt"].max()
    n_events_in = int(len(pc))
    log.info("page_change events: %s, newest meta_dt %s", f"{len(pc):,}", newest)

    other_kinds = pc.loc[~pc["kind"].isin(EDIT_KINDS), "kind"].value_counts().to_dict()
    ed, n_dup_rev, dup_examples = edit_events(pc)
    if n_dup_rev:
        log.warning("rev_id was not unique after the meta.id dedupe: %d rows dropped (examples %s)",
                    n_dup_rev, dup_examples)
    ed = add_user_columns(ed)
    E, n_dup_e = revert_events(pc)
    E = add_user_columns(E)
    del pc

    c, drops = build_cohort(ed, n_dup_rev)
    drops = {"kind_not_create_or_edit": {k: int(v) for k, v in other_kinds.items()}} | drops
    rev = live_revisions(c, ed, tags, risk, newest)
    assert rev["rev_id"].is_unique
    log.info("live cohort: %s rows. Drops: %s", f"{len(rev):,}", drops)

    newest_check = check_newest_parent(E)
    log.log(logging.WARNING if newest_check["exceptions"] else logging.INFO,
            "revert events: %s. newest_id != parent_id: %d (examples %s)", f"{len(E):,}",
            newest_check["exceptions"], newest_check["examples"])
    pairs = range_cover(ed, E)
    E["range_complete"] = range_complete_flags(E, ed).to_numpy()
    mw_ids = set(first_mw_reverted(tags).index)
    links_all = build_links_all(ed, E, pairs, set(rev["rev_id"]), mw_ids)
    links = first_exact_links(links_all)
    links["cohort"] = config.COHORT_LIVE

    write_parquet(rev, LIVE_REVISIONS_SCHEMA, tables_dir / "live_revisions.parquet")
    write_parquet(links, LINKS_SCHEMA, tables_dir / "live_revert_links.parquet")
    write_parquet(links_all[[f.name for f in LINKS_ALL_SCHEMA]], LINKS_ALL_SCHEMA,
                  tables_dir / "live_revert_links_all.parquet")

    summary = summarize(rev, links, links_all, E, drops, newest_check, n_events_in, newest)
    summary["revert_events"]["duplicate_rev_id_dropped"] = n_dup_e
    write_json(summary, tables_dir / "live_summary.json")
    success = {"step": "live", "data_version": config.DATA_VERSION,
               "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
               "provisional": summary["provisional"], "newest_meta_dt": summary["newest_meta_dt"],
               "live_final_after": summary["live_final_after"],
               "row_counts": {"live_revisions.parquet": int(len(rev)),
                              "live_revert_links.parquet": int(len(links)),
                              "live_revert_links_all.parquet": int(len(links_all))},
               "seconds": round(time.time() - t0, 1)}
    write_json(success, tables_dir / "_SUCCESS_live.json")
    print_summary(summary)
    return summary


def print_summary(s: dict) -> None:
    rs = s["revert_share_exact_within_followup"]
    print("\n=== Live cohort summary ===")
    print(f"cohort rows: {s['cohort']['rows']:,}   drops: {s['cohort']['drops']}")
    o = rs["overall"]
    print(f"reverted (first exact revert, T <= {config.LIVE_FOLLOWUP_DAYS} d): {o['reverted']:,} of {o['n']:,}"
          f" = {o['share']}  (by another editor: {o['share_by_other']}); humans: {rs['human_share']}")
    for k, v in rs["by_user_kind"].items():
        print(f"   {k:<10} n={v['n']:>7,}  reverted={v['reverted']:>6,}  share={v['share']}  by_other={v['share_by_other']}")
    print(f"median T (within follow-up): {s['median_T_s']['within_followup']} s"
          f" = {s['median_T_hours_within_followup']} h")
    tc = s["tag_confirmed_share_of_reverted"]
    m = tc["mw_reverted_max_depth"]
    print(f"confirmed by mw-reverted tag (complete ranges): range <= {m}: "
          f"{tc['range_size_le_max']}, range > {m}: {tc['range_size_gt_max']}")
    print(f"   ranges that start before the capture (size unknown): {tc['range_incomplete']}")
    print(f"tag-confirmed cohort revisions found by the range cover: {s['tagged_revisions_found_by_cover']}")
    print(f"K_s (stream delay of the reverting event): {s['K_s']}")
    print(f"revert_risk coverage: {s['revert_risk_coverage']}")
    nc = s["newest_id_equals_parent_check"]
    print(f"newest_id == parent_id check: {nc['exceptions']} exceptions of "
          f"{nc['revert_events']:,} revert events; pairs beyond newest_id (exact undos of an "
          f"older edit): {nc['pairs_beyond_newest_all']:,}")
    print(f"links: {s['links']}")
    if s["provisional"]:
        print(f"\nWARNING: these stream labels (live cohort) are PROVISIONAL. The newest captured meta.dt is "
              f"{s['newest_meta_dt']}; labels are final only after {s['live_final_after']}.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    run()


if __name__ == "__main__":
    main()
