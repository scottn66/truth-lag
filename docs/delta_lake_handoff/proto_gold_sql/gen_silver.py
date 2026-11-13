"""Make the made-up Silver tables for the Gold SQL lab, with delta-rs.

Purpose : small, fully made-up Silver tables with the real column names and types
          (ec-hw2/DATA_MODEL.md sections 2 and 3), plus planted.json with every planted count.
Inputs  : none (fixed random seed, so a re-run gives the same numbers).
Outputs : <lab>/lake/silver/{page_change,live_revisions,history_revisions,live_revert_links,
          history_revert_links,history_slim}/  (path-based Delta tables) and <lab>/planted.json
Run     : <deltars venv>/bin/python gen_silver.py            (about 10 s)
"""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid
import warnings

import numpy as np
import pandas as pd
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

LAB = os.environ.get(
    "GOLD_LAB",
    "/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/gold_sql_lab",
)
SILVER = os.path.join(LAB, "lake", "silver")
warnings.filterwarnings("ignore", category=DeprecationWarning)   # numpy 2.5 + pandas 2.3 Timedelta noise
warnings.filterwarnings("ignore", category=FutureWarning)
SEED = 20261113
rng = np.random.default_rng(SEED)

KEEP_HISTORY = {
    "delta.logRetentionDuration": "interval 3650 days",
    "delta.deletedFileRetentionDuration": "interval 3650 days",
    "delta.enableExpiredLogCleanup": "false",
}
TS = pa.timestamp("us", tz="UTC")


def U(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


SPAN0, SPAN1 = U("2026-10-19 23:00:00"), U("2026-10-27 21:00:00")     # stream capture span
LIVE0, LIVE1 = U("2026-10-20"), U("2026-10-23")                       # live window, half-open
HIST0, HIST1 = U("2026-09-08"), U("2026-09-11")                       # history window, half-open
AS_OF1, AS_OF2 = U("2026-10-23 00:00:00"), U("2026-10-27 21:00:00")   # the two Gold runs
AS_OF_USERS1 = U("2026-10-01 00:00:00")                               # first dim_user run (history only)
DUMP_LAST = U("2026-10-01 01:38:27")                                  # config.HISTORY_DUMP_LAST_REVISION
HORIZON_S = 345_600
HIST_FOLLOWUP_S = 1_728_000
WAITS = [0, 60, 300, 900, 3600, 21600, 86400, 172800, 345600]
N_COHORT = 40_000
N_SLIM_MONTH = 150_000
planted: dict = {"seed": SEED, "as_of_1": str(AS_OF1), "as_of_2": str(AS_OF2), "as_of_users_1": str(AS_OF_USERS1)}

# --------------------------------------------------------------------------
# Editors (400). Kinds follow config.user_kind / config.editor_key.
# --------------------------------------------------------------------------
N_ED = 400
EID = np.arange(0, N_ED + 1)                                           # index 0 unused
ED_KIND = np.array(["" if i == 0 else "bot" if i <= 20 else "temporary" if i <= 100
                    else "registered" if i <= 398 else "unknown" for i in EID], dtype=object)
ED_NAME = np.array([None if k in ("", "unknown") else f"Bot_{i}" if k == "bot"
                    else f"~2026-{10000 + 7 * i}-{10 + i % 90}" if k == "temporary" else f"User_{i}"
                    for i, k in zip(EID, ED_KIND)], dtype=object)
RENAMED_BETWEEN = np.arange(101, 111)     # other name in October than in September
BECAME_BOT = np.arange(111, 116)          # registered in September, bot in October
RENAMED_WITHIN = np.arange(116, 119)      # renamed in the middle of the live window
RENAME_AT = U("2026-10-21 12:00:00")
LIVE_ONLY = np.arange(331, 361)           # never edit in the history cohort
HIST_ONLY = np.arange(361, 391)           # never edit in the live cohort
UNKNOWN = np.array([399, 400])
N_UNKNOWN_ROWS = 40                       # cohort revisions by 'unknown' editors, per cohort


def draw_editors(n: int, exclude: np.ndarray) -> np.ndarray:
    pool = np.setdiff1d(np.arange(1, 399), exclude)
    w = np.where(ED_KIND[pool] == "bot", 8.0, np.where(ED_KIND[pool] == "temporary", 0.5, 1.0))
    return rng.choice(pool, size=n, p=w / w.sum())


def user_cols(eids: np.ndarray, cohort: str, ts: pd.Series) -> pd.DataFrame:
    kind = pd.Series(ED_KIND[eids], dtype=object)
    name = pd.Series(ED_NAME[eids], dtype=object)
    uid = pd.Series(np.where(kind == "unknown", np.nan, 500_000 + eids)).astype("Int64")
    if cohort == "live":
        m = np.isin(eids, RENAMED_BETWEEN)
        name[m] = name[m] + "_renamed"
        kind[np.isin(eids, BECAME_BOT)] = "bot"
        m = np.isin(eids, RENAMED_WITHIN) & (pd.Series(ts) >= RENAME_AT).to_numpy()
        name[m] = name[m] + "_v2"
    key = pd.Series(np.where(kind == "unknown", None,
                             np.where(kind == "temporary", "t:" + name.fillna(""), "u:" + uid.astype("string").fillna(""))),
                    dtype=object)
    return pd.DataFrame({"user_id": uid, "user_name": name, "user_kind": kind, "user_key": key,
                         "is_bot": (kind == "bot").to_numpy(), "is_temp": (kind == "temporary").to_numpy()})


# --------------------------------------------------------------------------
# History cohort (dump, 2026-09-08 .. 2026-09-11)
# --------------------------------------------------------------------------
cand = pd.DataFrame({"page_id": rng.integers(100_001, 101_801, int(N_COHORT * 1.1)),
                     "sec": rng.integers(0, 3 * 86400, int(N_COHORT * 1.1))})
cand = cand.drop_duplicates(["page_id", "sec"]).head(N_COHORT)
assert len(cand) == N_COHORT
h = cand.sort_values(["sec", "page_id"]).reset_index(drop=True)
h["ts"] = HIST0 + pd.to_timedelta(h["sec"], unit="s")
h["rev_id"] = 1_250_000_000 + 5 * np.arange(N_COHORT)
h["rank_on_page"] = h.groupby("page_id").cumcount()
h["n_on_page"] = h.groupby("page_id")["rev_id"].transform("size")
h["page_title_historical"] = "Page_" + h["page_id"].astype(str)

# planted: 30 pages moved once inside the history window, 5 pages moved there and back (A -> B -> A)
elig = np.sort(h.loc[h["n_on_page"] >= 6, "page_id"].unique())
sep_pages = rng.choice(elig, 35, replace=False)
SEP_MOVE_ONCE, SEP_MOVE_BACK = sep_pages[:30], sep_pages[30:]
m = h["page_id"].isin(SEP_MOVE_ONCE) & (h["rank_on_page"] >= h["n_on_page"] // 2)
h.loc[m, "page_title_historical"] = h.loc[m, "page_title_historical"] + "_(moved_sep)"
m = (h["page_id"].isin(SEP_MOVE_BACK) & (h["rank_on_page"] >= h["n_on_page"] // 3)
     & (h["rank_on_page"] < 2 * h["n_on_page"] // 3))
h.loc[m, "page_title_historical"] = h.loc[m, "page_title_historical"] + "_(sep_detour)"
h["page_title"] = h.groupby("page_id")["page_title_historical"].transform("last")   # the dump's CURRENT title

eids = draw_editors(N_COHORT, LIVE_ONLY)
unk_rows = rng.choice(N_COHORT, N_UNKNOWN_ROWS, replace=False)
eids[unk_rows] = rng.choice(UNKNOWN, N_UNKNOWN_ROWS)
h = pd.concat([h, user_cols(eids, "history", h["ts"])], axis=1)

# labels: 4,000 random reverted revisions with T spread from 1 s to about 23 days, plus special values
idx_rev = rng.choice(N_COHORT, 4000, replace=False)
T = np.floor(10 ** rng.uniform(0, 6.3, 4000)).astype(np.int64)
max_t = (DUMP_LAST - h["ts"].iloc[idx_rev]).dt.total_seconds().to_numpy().astype(np.int64)
T = np.minimum(T, max_t)
special_T = [w for w in WAITS for _ in range(5)] + [-5] * 3 + [HORIZON_S + 1] * 3
rest = np.setdiff1d(np.arange(N_COHORT), idx_rev)
idx_sp = rng.choice(rest, len(special_T), replace=False)
secs = pd.Series(pd.NA, index=h.index, dtype="Int64")
secs.iloc[idx_rev] = T
secs.iloc[idx_sp] = special_T
h["secs_to_revert"] = secs
h["reverted_any"] = secs.notna().to_numpy()
h["reverted"] = (secs.notna() & (secs <= HIST_FOLLOWUP_S)).fillna(False).to_numpy()
h["reverting_rev_id"] = pd.Series(np.where(h["reverted_any"], 1_290_000_000 + np.arange(N_COHORT), np.nan)).astype("Int64")
h["hist_special"] = False
h.loc[idx_sp, "hist_special"] = True

history_revisions = pd.DataFrame({
    "cohort": "history", "wiki_db": "enwiki", "rev_id": h["rev_id"],
    "parent_id": pd.Series(np.where(h["rank_on_page"] == 0, 0, h.groupby("page_id")["rev_id"].shift(1)), dtype="Int64"),
    "page_id": h["page_id"], "page_title": h["page_title"], "page_title_historical": h["page_title_historical"],
    "page_ns": np.int64(0), "ts": h["ts"], "seen_ts": pd.Series(pd.NaT, index=h.index, dtype="datetime64[ns, UTC]"),
    "size_delta": rng.integers(-2000, 5000, N_COHORT), "user_id": h["user_id"], "user_name": h["user_name"],
    "user_kind": h["user_kind"], "user_key": h["user_key"], "is_bot": h["is_bot"], "is_temp": h["is_temp"],
    "revert_risk": pd.Series(np.nan, index=h.index, dtype="float64"),
    "page_edits_prev_1h": rng.poisson(0.4, N_COHORT).astype(np.int64),
    "followup_s": (DUMP_LAST - h["ts"]).dt.total_seconds().astype(np.int64),
    "reverted": h["reverted"], "reverted_any": h["reverted_any"], "secs_to_revert": h["secs_to_revert"],
    "reverting_rev_id": h["reverting_rev_id"],
})
r = history_revisions[history_revisions["reverted_any"]].reset_index(drop=True)
history_revert_links = pd.DataFrame({
    "cohort": "history", "source": "dump", "reverted_rev_id": r["rev_id"], "page_id": r["page_id"],
    "reverted_ts": r["ts"], "reverting_rev_id": r["reverting_rev_id"],
    "reverting_ts": r["ts"] + pd.to_timedelta(r["secs_to_revert"].astype("int64"), unit="s"),
    "T_s": r["secs_to_revert"], "known_at": pd.Series(pd.NaT, index=r.index, dtype="datetime64[ns, UTC]"),
    "K_s": pd.Series(np.nan, index=r.index, dtype="float64"), "method": pd.Series(None, index=r.index, dtype=object),
    "is_exact": True, "by_other": rng.random(len(r)) < 0.9, "within_followup": r["reverted"],
})

# --------------------------------------------------------------------------
# Stream: page timelines (moves, namespace changes, deletes, undeletes) and events
# --------------------------------------------------------------------------
LIVE_PAGES = np.arange(100_201, 102_001)                  # namespace 0; 100201..101800 are also in history
EXTRA_PAGES = np.arange(102_001, 102_101)                 # other namespaces: 1 (40), 4 (30), 118 (30)
NEW_PAGES = np.arange(102_101, 102_126)                   # created after as_of_1
WINDOW_CREATES = np.arange(102_126, 102_146)              # created inside the live window
title0 = {int(p): f"Page_{p}" for p in LIVE_PAGES}
title0.update(h.groupby("page_id")["page_title"].last().loc[lambda s: s.index >= 100_201].to_dict())
ns0 = {int(p): 0 for p in LIVE_PAGES}
for p in EXTRA_PAGES:
    n_ = 1 if p <= 102_040 else 4 if p <= 102_070 else 118
    ns0[int(p)] = n_
    title0[int(p)] = {1: "Talk:", 4: "Wikipedia:", 118: "Draft:"}[n_] + f"Page_{p}"

plain = np.setdiff1d(LIVE_PAGES, sep_pages)
perm = rng.permutation(plain)
GAP_MOVE = perm[:40]                                       # moved between the two cohorts (not seen as an event)
for p in GAP_MOVE:
    title0[int(p)] = f"Page_{p}_(moved_gap)"
CATS = {  # name: (pages, [(period, op), ...])
    "m1_before": (60, [("b", "move")]), "m1_after": (50, [("a", "move")]),
    "m2_after": (20, [("a", "move"), ("a", "move")]), "m2_before": (15, [("b", "move"), ("b", "move")]),
    "m_before_after": (10, [("b", "move"), ("a", "move")]),
    "ns_after": (10, [("a", "move_ns118")]), "ns_before": (5, [("b", "move_ns118")]),
    "del_after": (12, [("a", "delete")]), "del_undel_after": (8, [("a", "delete"), ("a", "undelete")]),
    "del_before_undel_after": (6, [("b", "delete"), ("a", "undelete")]), "del_before": (5, [("b", "delete")]),
    "mv_del_undel_after": (4, [("a", "move"), ("a", "delete"), ("a", "undelete")]),
}
B0, B_HOURS = SPAN0 + pd.Timedelta(minutes=10), 72        # "before as_of_1": SPAN0+10 min .. +72 h
A0, A_HOURS = AS_OF1 + pd.Timedelta(minutes=10), 116      # "after as_of_1" : AS_OF1+10 min .. +116 h


def draw_times(periods: list[str]) -> list[pd.Timestamp]:
    """Strictly increasing whole-second times: distinct hours inside each period."""
    out = []
    for per, base, hours in (("b", B0, B_HOURS), ("a", A0, A_HOURS)):
        k = periods.count(per)
        if k:
            hrs = np.sort(rng.choice(hours, k, replace=False))
            out += [base + pd.Timedelta(hours=int(x), seconds=int(rng.integers(0, 3600))) for x in hrs]
    return out


tl_rows, change_rows, pos = [], [], 40
planted["pages_per_category"] = {"sep_move_once": 30, "sep_move_there_and_back": 5, "gap_move": 40}
plans = []
for cat, (n, ops) in CATS.items():
    for p in perm[pos:pos + n]:
        plans.append((cat, int(p), ops))
    pos += n
    planted["pages_per_category"][cat] = n
for p in EXTRA_PAGES[-30:][:5]:                            # 5 Draft pages moved to namespace 0 before as_of_1
    plans.append(("ns_to_main_before", int(p), [("b", "move_ns0")]))
planted["pages_per_category"]["ns_to_main_before"] = 5
for p in list(LIVE_PAGES) + list(EXTRA_PAGES):
    tl_rows.append((int(p), SPAN0 - pd.Timedelta(days=1), title0[int(p)], ns0[int(p)], False))
for cat, p, ops in plans:
    title, ns, deleted, n_mv = title0[p], ns0[p], False, 0
    for (per, op), t in zip(ops, draw_times([o[0] for o in ops])):
        if op == "move":
            n_mv += 1
            title = f"Page_{p}_(mv{n_mv})"
        elif op == "move_ns118":
            title, ns = f"Draft:Page_{p}", 118
        elif op == "move_ns0":
            title, ns = f"Page_{p}_(from_draft)", 0
        elif op == "delete":
            deleted = True
        elif op == "undelete":
            deleted = False
        tl_rows.append((p, t, title, ns, deleted))
        change_rows.append((p, t, "move" if op.startswith("move") else op, title, ns, cat))
tl = pd.DataFrame(tl_rows, columns=["page_id", "t", "title", "ns", "is_deleted"])
changes = pd.DataFrame(change_rows, columns=["page_id", "t", "kind", "title", "ns", "cat"])

# edit candidates: inside the live window, and outside it (1 h before, 4 d 21 h after)
STREAM_PAGES = np.concatenate([LIVE_PAGES, EXTRA_PAGES])
n1, n2 = 46_000, 15_000
c1 = pd.DataFrame({"page_id": rng.choice(STREAM_PAGES, n1), "rev_dt": LIVE0 + pd.to_timedelta(rng.integers(0, 3 * 86400, n1), unit="s")})
after_len = int((SPAN1 - LIVE1).total_seconds()) - 1200
s2 = rng.integers(0, 3600 + after_len, n2)
c2 = pd.DataFrame({"page_id": rng.choice(STREAM_PAGES, n2),
                   "rev_dt": np.where(s2 < 3600, SPAN0.to_datetime64() + s2.astype("timedelta64[s]"),
                                      LIVE1.to_datetime64() + (s2 - 3600).astype("timedelta64[s]"))})
c2["rev_dt"] = pd.to_datetime(c2["rev_dt"], utc=True)
cand = pd.concat([c1, c2], ignore_index=True)
cand["ord"] = np.arange(len(cand))
cand = cand.drop_duplicates(["page_id", "rev_dt"])
key_change = set(zip(changes["page_id"], changes["t"]))
cand = cand[[(p, t) not in key_change for p, t in zip(cand["page_id"], cand["rev_dt"])]]
cand = pd.merge_asof(cand.sort_values("rev_dt"), tl.sort_values("t"), left_on="rev_dt", right_on="t",
                     by="page_id", direction="backward", allow_exact_matches=False)
cand = cand[~cand["is_deleted"]].sort_values("ord")
in_win = (cand["rev_dt"] >= LIVE0) & (cand["rev_dt"] < LIVE1)
N_DUP, N_WIN_CREATE = 6, len(WINDOW_CREATES)
n_cohort_edits = N_COHORT - N_DUP - N_WIN_CREATE
coh = cand[in_win & (cand["ns"] == 0)].head(n_cohort_edits)
assert len(coh) == n_cohort_edits, len(coh)
dup = coh.iloc[rng.choice(len(coh), N_DUP, replace=False)].copy()        # a second edit in the same second
other = pd.concat([cand[in_win & (cand["ns"] != 0)], cand[~in_win]])
win_create = pd.DataFrame({"page_id": WINDOW_CREATES,
                           "rev_dt": LIVE0 + pd.to_timedelta(rng.integers(0, 3 * 86400, N_WIN_CREATE), unit="s"),
                           "title": [f"New_window_page_{p}" for p in WINDOW_CREATES], "ns": 0})
new_rows = []
for p in NEW_PAGES:
    t = draw_times(["a"])[0]
    new_rows.append((int(p), t, f"New_page_{p}", 0, "create"))
    for _ in range(int(rng.integers(0, 5))):
        t = t + pd.Timedelta(seconds=int(rng.integers(60, 20_000)))
        if t < SPAN1 - pd.Timedelta(seconds=1200):
            new_rows.append((int(p), t, f"New_page_{p}", 0, "edit"))
new_ev = pd.DataFrame(new_rows, columns=["page_id", "rev_dt", "title", "ns", "kind"])
cols = ["page_id", "rev_dt", "title", "ns", "kind", "in_cohort"]
ev = pd.concat([
    coh.assign(kind="edit", in_cohort=True)[cols], dup.assign(kind="edit", in_cohort=True)[cols],
    win_create.assign(kind="create", in_cohort=True)[cols], other.assign(kind="edit", in_cohort=False)[cols],
    new_ev.assign(in_cohort=False)[cols],
    changes[changes["kind"] == "move"].rename(columns={"t": "rev_dt"}).assign(in_cohort=False)[cols],
], ignore_index=True)
ev["tie"] = rng.random(len(ev))
ev = ev.sort_values(["rev_dt", "tie"]).reset_index(drop=True)
ev["rev_id"] = 1_300_000_000 + 4 * np.arange(len(ev))
prev = ev.groupby("page_id")["rev_id"].shift(1)
ev["parent_id"] = pd.Series(np.where(ev["kind"] == "create", np.nan, prev.fillna(1_200_000_000 + ev["page_id"])), dtype="Int64")
delay = np.round(np.exp(rng.normal(np.log(3.4), 0.5, len(ev))), 3)
slow = rng.random(len(ev)) < 0.005
delay[slow] = np.round(rng.uniform(60, 900, int(slow.sum())), 3)
ev["meta_dt"] = ev["rev_dt"] + pd.to_timedelta((delay * 1000).round().astype(np.int64), unit="ms")
eids = draw_editors(len(ev), HIST_ONLY)
coh_idx = np.flatnonzero(ev["in_cohort"].to_numpy())
unk_ev = rng.choice(coh_idx, N_UNKNOWN_ROWS, replace=False)
eids[unk_ev] = rng.choice(UNKNOWN, N_UNKNOWN_ROWS)
eids[(ev["kind"] == "move").to_numpy()] = rng.choice(np.arange(200, 330), int((ev["kind"] == "move").sum()))
ev = pd.concat([ev, user_cols(eids, "live", ev["rev_dt"])], axis=1)

# delete / undelete events: no new revision. rev_id and rev_dt are those of the page's newest revision (older).
dl = changes[changes["kind"].isin(["delete", "undelete"])].sort_values("t")
dl = pd.merge_asof(dl, ev[["page_id", "rev_dt", "rev_id"]].sort_values("rev_dt"), left_on="t", right_on="rev_dt",
                   by="page_id", direction="backward")
dl["meta_dt"] = dl["t"] + pd.Timedelta(milliseconds=250)
dl_u = user_cols(rng.choice(np.arange(200, 330), len(dl)), "live", dl["t"]).set_index(dl.index)
dl = pd.concat([dl, dl_u], axis=1)
dl["parent_id"] = pd.Series(pd.NA, index=dl.index, dtype="Int64")
dl["rev_id"] = dl["rev_id"].astype("Int64")
pc_cols = ["meta_dt", "kind", "page_id", "title", "ns", "rev_id", "parent_id", "rev_dt", "user_id", "user_name", "is_bot", "is_temp"]
page_change = pd.concat([ev.assign(rev_id=ev["rev_id"].astype("Int64"))[pc_cols], dl[pc_cols]], ignore_index=True)
page_change = page_change.sort_values("meta_dt").reset_index(drop=True).rename(columns={"title": "page_title"})
page_change.insert(0, "meta_id", [str(uuid.UUID(bytes=rng.bytes(16), version=4)) for _ in range(len(page_change))])
page_change.insert(2, "wiki_id", "enwiki")
assert page_change["meta_dt"].min() >= SPAN0 and page_change["meta_dt"].max() <= SPAN1

lv = ev[ev["in_cohort"]].reset_index(drop=True)
assert len(lv) == N_COHORT and lv["rev_dt"].min() >= LIVE0 and lv["rev_dt"].max() < LIVE1 and (lv["ns"] == 0).all()
newest_meta = page_change["meta_dt"].max()
live_revisions = pd.DataFrame({
    "cohort": "live", "wiki_db": "enwiki", "rev_id": lv["rev_id"], "parent_id": lv["parent_id"],
    "page_id": lv["page_id"], "page_title": lv["title"], "page_title_historical": lv["title"],
    "page_ns": lv["ns"].astype(np.int64), "ts": lv["rev_dt"], "seen_ts": lv["meta_dt"],
    "size_delta": rng.integers(-2000, 5000, N_COHORT), "user_id": lv["user_id"], "user_name": lv["user_name"],
    "user_kind": lv["user_kind"], "user_key": lv["user_key"], "is_bot": lv["is_bot"], "is_temp": lv["is_temp"],
    "revert_risk": np.where(rng.random(N_COHORT) < 0.05, np.nan, np.round(rng.random(N_COHORT), 6)),
    "page_edits_prev_1h": rng.poisson(0.4, N_COHORT).astype(np.int64),
    "followup_s": np.floor((newest_meta - lv["rev_dt"]).dt.total_seconds()).astype(np.int64),
})

# --------------------------------------------------------------------------
# Live revert links: T from 0 s to about 4.9 days, K float seconds (ms), special wait-point cases
# --------------------------------------------------------------------------
spec = ([(w, 0.0) for w in WAITS for _ in range(4)]             # T exactly on a wait point, K = 0 (inclusive rule)
        + [(w, 1.25) for w in WAITS for _ in range(4)]          # T on a wait point, known just after it
        + [(w - 2, 3.5) for w in WAITS[1:] for _ in range(5)]   # T before the wait point, T + K after it
        + [(0, 2.0)] * 5 + [(HORIZON_S + 1, 1.0)] * 3 + [(HORIZON_S - 1, 3.5)] * 3)
N_BULK = 2900
pick = rng.choice(N_COHORT, N_BULK + len(spec), replace=False)
unk_pos = np.flatnonzero((lv["user_kind"] == "unknown").to_numpy())
unk_free = np.setdiff1d(unk_pos, pick)[:6]
pick[:len(unk_free)] = unk_free                                  # make sure some 'unknown' revisions are reverted
Tb = np.floor(10 ** rng.uniform(0, 5.75, N_BULK)).astype(np.int64)
Kb = np.round(np.exp(rng.normal(np.log(3.44), 0.6, N_BULK)), 3)
lk = lv.iloc[pick].reset_index(drop=True)
lk["T_s"] = np.concatenate([Tb, [s[0] for s in spec]]).astype(np.int64)
lk["K_s"] = np.concatenate([Kb, [s[1] for s in spec]]).astype(np.float64)
lk["special"] = np.arange(len(lk)) >= N_BULK
max_t = np.floor((SPAN1 - pd.Timedelta(seconds=120) - lk["rev_dt"]).dt.total_seconds()).astype(np.int64)
lk["T_s"] = np.minimum(lk["T_s"], max_t)
lk["reverting_ts"] = lk["rev_dt"] + pd.to_timedelta(lk["T_s"], unit="s")
lk["known_at"] = lk["reverting_ts"] + pd.to_timedelta((lk["K_s"] * 1000).round().astype(np.int64), unit="ms")
lk["within_followup"] = lk["T_s"] <= HORIZON_S
live_revert_links = pd.DataFrame({
    "cohort": "live", "source": "stream", "reverted_rev_id": lk["rev_id"], "page_id": lk["page_id"],
    "reverted_ts": lk["rev_dt"], "reverting_rev_id": pd.Series(1_390_000_000 + np.arange(len(lk)), dtype="Int64"),
    "reverting_ts": lk["reverting_ts"], "T_s": lk["T_s"].astype("Int64"), "known_at": lk["known_at"], "K_s": lk["K_s"],
    "method": rng.choice(["rollback", "undo", "manual"], len(lk)), "is_exact": True,
    "by_other": rng.random(len(lk)) < 0.9, "within_followup": lk["within_followup"],
})
assert live_revert_links["known_at"].max() <= SPAN1

# --------------------------------------------------------------------------
# history_slim: snapshot 2026-09 (month 09) and snapshot 2026-10 (month 09 restated + month 10)
# --------------------------------------------------------------------------
def slim_frame(rev_id, page_id, ts, reverted, reverting, secs, user_id, user_text, ns, is_revert):
    return pd.DataFrame({
        "revision_id": np.asarray(rev_id, dtype=np.int64), "page_id": np.asarray(page_id, dtype=np.int64),
        "event_timestamp": pd.Series(ts).reset_index(drop=True),
        "revision_is_identity_revert": np.asarray(is_revert, dtype=bool),
        "revision_is_identity_reverted": np.asarray(reverted, dtype=bool),
        "revision_first_identity_reverting_revision_id": pd.Series(reverting).reset_index(drop=True).astype("Int64"),
        "revision_seconds_to_identity_revert": pd.Series(secs).reset_index(drop=True).astype("Int64"),
        "event_user_id": pd.Series(user_id).reset_index(drop=True).astype("Int64"),
        "event_user_text": pd.Series(user_text, dtype=object).reset_index(drop=True),
        "page_namespace": np.asarray(ns, dtype=np.int64)})


def other_revisions(n: int, first_id: int, month0: pd.Timestamp, month1: pd.Timestamp, last_event: pd.Timestamp) -> pd.DataFrame:
    """Made-up revisions of one dump month outside the cohorts (all namespaces, 8% reverted)."""
    ts = month0 + pd.to_timedelta(rng.integers(0, int((month1 - month0).total_seconds()), n), unit="s")
    rev = rng.random(n) < 0.08
    t = np.floor(10 ** rng.uniform(0, 6.3, n)).astype(np.int64)
    t = np.minimum(t, np.maximum((last_event - ts).total_seconds().astype(np.int64), 0))
    e = draw_editors(n, np.array([], dtype=int))
    u = user_cols(e, "history", pd.Series(ts))
    return slim_frame(first_id + np.arange(n), rng.integers(100_001, 102_101, n), ts, rev,
                      np.where(rev, 1_190_000_000 + np.arange(n), np.nan), np.where(rev, t, np.nan),
                      u["user_id"], u["user_name"], rng.choice([0, 0, 0, 1, 2, 3, 4, 10, 14, 118], n), rng.random(n) < 0.06)


sep_coh = slim_frame(history_revisions["rev_id"], history_revisions["page_id"], history_revisions["ts"],
                     history_revisions["reverted_any"], history_revisions["reverting_rev_id"],
                     history_revisions["secs_to_revert"], history_revisions["user_id"], history_revisions["user_name"],
                     np.zeros(N_COHORT), rng.random(N_COHORT) < 0.06)
sep_oth = other_revisions(N_SLIM_MONTH - N_COHORT, 1_100_000_000, U("2026-09-01"), U("2026-10-01"), DUMP_LAST)
sep_09 = pd.concat([sep_coh.assign(in_cohort=True, special=h["hist_special"].to_numpy()),
                    sep_oth.assign(in_cohort=False, special=False)], ignore_index=True)

# planted label changes between the two snapshots (exactly 700 rows of month 2026-09)
sep_10 = sep_09.copy()
R, S, I = "revision_is_identity_reverted", "revision_seconds_to_identity_revert", "revision_first_identity_reverting_revision_id"
free = ~sep_09["special"]


def choose(mask: pd.Series, n: int) -> np.ndarray:
    return rng.choice(np.flatnonzero(mask.to_numpy()), n, replace=False)


LC = {"became_reverted": {"history_cohort": 200, "other": 400}, "became_unreverted": {"history_cohort": 20, "other": 40},
      "reverter_or_time_changed": {"history_cohort": 15, "other": 25}}
i_br = np.concatenate([choose(free & sep_09["in_cohort"] & ~sep_09[R], 200), choose(~sep_09["in_cohort"] & ~sep_09[R], 400)])
i_bu = np.concatenate([choose(free & sep_09["in_cohort"] & sep_09[R], 20), choose(~sep_09["in_cohort"] & sep_09[R], 40)])
left = sep_09[R].copy()
left.iloc[i_bu] = False
i_ch = np.concatenate([choose(free & sep_09["in_cohort"] & left, 15), choose(~sep_09["in_cohort"] & left, 25)])
late = U("2026-10-02") + pd.to_timedelta(rng.integers(0, 29 * 86400, 600), unit="s")       # reverted in October
sep_10.loc[i_br, R] = True
sep_10.loc[i_br, S] = (late - pd.DatetimeIndex(sep_09["event_timestamp"].iloc[i_br])).total_seconds().astype(np.int64)
sep_10.loc[i_br, I] = 1_395_000_000 + np.arange(600)
sep_10.loc[i_bu, R] = False
sep_10.loc[i_bu, S] = pd.NA
sep_10.loc[i_bu, I] = pd.NA
sep_10.loc[i_ch[:20], I] = sep_10.loc[i_ch[:20], I] + 1_000_000                              # 20: reverter only
sep_10.loc[i_ch[20:35], S] = sep_10.loc[i_ch[20:35], S] + 7                                  # 15: seconds only
sep_10.loc[i_ch[35:], I] = sep_10.loc[i_ch[35:], I] + 1_000_000                              # 5: both
sep_10.loc[i_ch[35:], S] = sep_10.loc[i_ch[35:], S] + 7
planted["label_changes"] = {"total": 700, **{k: sum(v.values()) for k, v in LC.items()}, "split": LC,
                            "reverter_only": 20, "seconds_only": 15, "reverter_and_seconds": 5}

# month 2026-10: every live-cohort revision except 50; dump labels agree with the stream except for planted rows
lab = live_revisions[["rev_id", "page_id", "ts", "user_id", "user_name"]].merge(
    live_revert_links[["reverted_rev_id", "T_s", "reverting_rev_id", "within_followup"]].assign(special=lk["special"].to_numpy()),
    left_on="rev_id", right_on="reverted_rev_id", how="left")
has_link = lab["reverted_rev_id"].notna()
wf = lab["within_followup"].fillna(False).astype(bool)
bulk = has_link & ~lab["special"].fillna(False).astype(bool)
lab["d_rev"] = has_link.to_numpy()
lab["d_secs"] = lab["T_s"]
lab["d_id"] = lab["reverting_rev_id"]
RC = {"not_in_dump": {"with_stream_link_within_followup": 8, "without_stream_link": 42},
      "stream_only": {"dump_not_reverted": 90, "dump_reverted_after_horizon": 30},
      "dump_only": {"no_stream_link": 60, "stream_link_after_horizon": 20},
      "both_reverted_but_other_seconds": 100}
i_out = np.concatenate([choose(bulk & wf, 8), choose(~has_link, 42)])
avail = pd.Series(True, index=lab.index)
avail.iloc[i_out] = False
i_so1 = choose(avail & bulk & wf, 90)
avail.iloc[i_so1] = False
i_so2 = choose(avail & bulk & wf, 30)
avail.iloc[i_so2] = False
i_do1 = choose(avail & ~has_link, 60)
avail.iloc[i_do1] = False
i_do2 = choose(avail & bulk & ~wf, 20)
avail.iloc[i_do2] = False
i_sec = choose(avail & bulk & wf & (lab["T_s"] > 10) & (lab["T_s"] < HORIZON_S - 10), 100)
lab.loc[i_so1, ["d_rev", "d_secs", "d_id"]] = [False, pd.NA, pd.NA]
lab.loc[i_so2, "d_secs"] = lab.loc[i_so2, "T_s"] + 400_000
lab.loc[i_do1, "d_rev"] = True
lab.loc[i_do1, "d_secs"] = np.floor(10 ** rng.uniform(0, 5.5, 60)).astype(np.int64)
lab.loc[i_do1, "d_id"] = 1_396_000_000 + np.arange(60)
lab.loc[i_do2, "d_secs"] = 300_000
lab.loc[i_sec, "d_secs"] = lab.loc[i_sec, "T_s"] + rng.choice([-3, -1, 1, 2, 5], 100)
keep = np.ones(len(lab), dtype=bool)
keep[i_out] = False
labk = lab[keep]
oct_coh = slim_frame(labk["rev_id"], labk["page_id"], labk["ts"], labk["d_rev"], labk["d_id"], labk["d_secs"],
                     labk["user_id"], labk["user_name"], np.zeros(len(labk)), rng.random(len(labk)) < 0.06)
oct_oth = other_revisions(N_SLIM_MONTH - len(labk), 1_400_000_000, U("2026-10-01"), U("2026-11-01"), U("2026-11-01 01:12:09"))
drop_cols = ["in_cohort", "special"]
history_slim = pd.concat([
    sep_09.drop(columns=drop_cols).assign(snapshot="2026-09", dump_month="2026-09"),
    sep_10.drop(columns=drop_cols).assign(snapshot="2026-10", dump_month="2026-09"),
    pd.concat([oct_coh, oct_oth], ignore_index=True).assign(snapshot="2026-10", dump_month="2026-10"),
], ignore_index=True)
history_slim = history_slim[["snapshot", "dump_month"] + [c for c in history_slim.columns if c not in ("snapshot", "dump_month")]]

# --------------------------------------------------------------------------
# Planted truth (straight from the plan above, or counted on the frames with plain pandas)
# --------------------------------------------------------------------------
n_wf = int(live_revert_links["within_followup"].sum())
stream_only, dump_only, not_in_dump = 120, 80, 50
planted["sizes"] = {
    "page_change_rows": len(page_change), "page_change_by_kind": page_change["kind"].value_counts().to_dict(),
    "pages_in_page_change": int(page_change["page_id"].nunique()), "pages_in_history": int(history_revisions["page_id"].nunique()),
    "pages_total": int(pd.concat([page_change["page_id"], history_revisions["page_id"]]).nunique()),
    "pages_first_seen_after_as_of_1": len(NEW_PAGES), "pages_created_inside_live_window": len(WINDOW_CREATES),
    "same_second_edit_pairs": N_DUP,
    "live_revisions": len(live_revisions), "history_revisions": len(history_revisions),
    "live_revert_links": len(live_revert_links), "live_links_within_followup": n_wf,
    "history_revert_links": len(history_revert_links),
    "history_slim": {f"{a}/{b}": int(n) for (a, b), n in history_slim.groupby(["snapshot", "dump_month"]).size().items()},
}
planted["reconciliation_live_vs_2026-10"] = {
    "split": RC, "not_in_dump": not_in_dump, "stream_only": stream_only, "dump_only": dump_only,
    "both_reverted": n_wf - RC["not_in_dump"]["with_stream_link_within_followup"] - stream_only,
    "neither": N_COHORT - not_in_dump - stream_only - dump_only - (n_wf - 8 - stream_only),
    "recon_mismatch_rows": not_in_dump + stream_only + dump_only,
}
h_any = int(history_revisions["reverted_any"].sum())
planted["fact_revert_label"] = {
    "rows_after_2026-09": N_SLIM_MONTH, "rows_after_2026-10": 2 * N_SLIM_MONTH, "updated_by_2026-10": 700,
    "inserted_by_2026-10": N_SLIM_MONTH,
    "history_cohort_reverted_any_as_of_2026-09": h_any,
    "history_cohort_reverted_any_as_of_2026-10": h_any + LC["became_reverted"]["history_cohort"] - LC["became_unreverted"]["history_cohort"],
}
ka = live_revert_links["known_at"]
planted["fact_edit"] = {
    "rows": 2 * N_COHORT, "live_flag_true_at_as_of_1": int((live_revert_links["within_followup"] & (ka <= AS_OF1)).sum()),
    "live_flag_true_at_as_of_2": int((live_revert_links["within_followup"] & (ka <= AS_OF2)).sum()),
    "rows_updated_by_run_2": int((live_revert_links["within_followup"] & (ka > AS_OF1) & (ka <= AS_OF2)).sum()),
    "user_key_unknown_rows": 2 * N_UNKNOWN_ROWS,
}


def latest_users(frames: list[pd.DataFrame], as_of: pd.Timestamp) -> pd.DataFrame:
    a = pd.concat([f[["user_key", "user_id", "user_name", "user_kind", "is_bot", "is_temp", "ts", "rev_id"]] for f in frames])
    a = a[a["ts"] <= as_of].assign(user_key=lambda d: d["user_key"].fillna("unknown")).sort_values(["ts", "rev_id"])
    return a.groupby("user_key").last().drop(columns=["ts", "rev_id"])


u1 = latest_users([history_revisions, live_revisions], AS_OF_USERS1)
u2 = latest_users([history_revisions, live_revisions], AS_OF2)
both = u1.index.intersection(u2.index)
neq = ~((u1.loc[both].astype(str) == u2.loc[both].astype(str)).all(axis=1))
planted["dim_user"] = {"rows_run_1": len(u1), "rows_run_2": len(u2), "inserted_by_run_2": len(u2) - len(both),
                       "updated_by_run_2": int(neq.sum()), "planted_renamed_between": len(RENAMED_BETWEEN),
                       "planted_became_bot": len(BECAME_BOT), "planted_renamed_within_live": len(RENAMED_WITHIN)}
minutes = pd.concat([history_revisions["ts"], live_revisions["ts"]]).dt.floor("min").nunique()
planted["dim_time"] = {"rows": int(minutes)}
planted["el_special_links"] = {"live_T_on_wait_point_K0": 4 * len(WAITS), "live_T_on_wait_point_K1.25": 4 * len(WAITS),
                               "live_T_2s_before_wait_point_K3.5": 5 * (len(WAITS) - 1), "live_T0_K2": 5,
                               "live_T_horizon_plus_1": 3, "live_T_horizon_minus_1_K3.5": 3,
                               "history_T_on_wait_point": 5 * len(WAITS), "history_T_minus_5": 3, "history_T_horizon_plus_1": 3}

# --------------------------------------------------------------------------
# Write the Silver tables (delta-rs), explicit Arrow schemas
# --------------------------------------------------------------------------
S, I64, B, F64, I32 = pa.string(), pa.int64(), pa.bool_(), pa.float64(), pa.int32()
REV_FIELDS = [("cohort", S), ("wiki_db", S), ("rev_id", I64), ("parent_id", I64), ("page_id", I64), ("page_title", S),
              ("page_title_historical", S), ("page_ns", I64), ("ts", TS), ("seen_ts", TS), ("size_delta", I64),
              ("user_id", I64), ("user_name", S), ("user_kind", S), ("user_key", S), ("is_bot", B), ("is_temp", B),
              ("revert_risk", F64), ("page_edits_prev_1h", I64), ("followup_s", I64)]
LINK_FIELDS = [("cohort", S), ("source", S), ("reverted_rev_id", I64), ("page_id", I64), ("reverted_ts", TS),
               ("reverting_rev_id", I64), ("reverting_ts", TS), ("T_s", I64), ("known_at", TS), ("K_s", F64),
               ("method", S), ("is_exact", B), ("by_other", B), ("within_followup", B)]
SCHEMAS = {
    "page_change": pa.schema([("meta_id", S), ("meta_dt", TS), ("wiki_id", S), ("kind", S), ("page_id", I64),
                              ("page_title", S), ("ns", I32), ("rev_id", I64), ("parent_id", I64), ("rev_dt", TS),
                              ("user_id", I64), ("user_name", S), ("is_bot", B), ("is_temp", B)]),
    "live_revisions": pa.schema(REV_FIELDS),
    "history_revisions": pa.schema(REV_FIELDS + [("reverted", B), ("reverted_any", B), ("secs_to_revert", I64), ("reverting_rev_id", I64)]),
    "live_revert_links": pa.schema(LINK_FIELDS),
    "history_revert_links": pa.schema(LINK_FIELDS),
    "history_slim": pa.schema([("snapshot", S), ("dump_month", S), ("revision_id", I64), ("page_id", I64), ("event_timestamp", TS),
                               ("revision_is_identity_revert", B), ("revision_is_identity_reverted", B),
                               ("revision_first_identity_reverting_revision_id", I64), ("revision_seconds_to_identity_revert", I64),
                               ("event_user_id", I64), ("event_user_text", S), ("page_namespace", I64)]),
}
FRAMES = {"page_change": page_change, "live_revisions": live_revisions, "history_revisions": history_revisions,
          "live_revert_links": live_revert_links, "history_revert_links": history_revert_links, "history_slim": history_slim}

if __name__ == "__main__":
    t0 = time.time()
    if os.path.isdir(SILVER):
        shutil.rmtree(SILVER)                      # made-up data only: rebuild from scratch
    for name, df in FRAMES.items():
        tbl = pa.Table.from_pandas(df[[f.name for f in SCHEMAS[name]]], schema=SCHEMAS[name], preserve_index=False)
        path = os.path.join(SILVER, name)
        write_deltalake(path, tbl, mode="error", configuration=KEEP_HISTORY,
                        partition_by=["snapshot"] if name == "history_slim" else None)
        dt = DeltaTable(path)
        p = dt.protocol()
        print(f"{name:22s} rows={tbl.num_rows:7d} version={dt.version()} reader={p.min_reader_version} writer={p.min_writer_version}")
    with open(os.path.join(LAB, "planted.json"), "w") as f:
        json.dump(planted, f, indent=1, sort_keys=True, default=str)
    print(json.dumps(planted, indent=1, sort_keys=True, default=str))
    print(f"done in {time.time() - t0:.1f} s")
