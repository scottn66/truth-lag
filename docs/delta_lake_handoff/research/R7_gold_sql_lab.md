# R7 — Prototype: Gold SQL with Spark on made-up tables

> **Research report, not yet reviewed.** Output of the research agent `gold_sql_lab` in a cloud Claude Code session on Nov 13, 2026, as returned. Evidence labels: RAN = executed in that session on made-up data; READ = read at the cited file and line; DERIVED = arithmetic on values that were read; UNVERIFIED = not checked. Paths that start with /tmp/claude-0/ or /home/user/ are on that session's machine and cannot be opened from elsewhere. Repository state read: scottn66/truth-lag at 8e28012.

## Summary

The whole Gold step ran on made-up Silver tables: 78 of 78 runner checks and 18 of 18 independent pandas checks passed (RAN, full rebuild twice with the same numbers). SCD2 by full recompute + pre-filter + one MERGE on page_key works: run 2 closed 120 rows and inserted 181, run 3 with the same as_of wrote no commit, and all 80,000 fact rows join to exactly one version with the title of the edit time. The classic NULL-merge-key form ends with different rows for the 207 pages that have two or more new versions in one run (4,210 fact rows find no version), and fails with DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE when fed every version. fact_revert_label: snapshot 2026-10 loaded as one MERGE commit with 700 updates and 150,000 inserts; the change feed gives 700 / 700 / 150,000; mart_label_change is 600 / 60 / 40; re-runs of either snapshot write no commit. Time travel works by version found through userMetadata (then 4,051, now 4,231 reverted history-cohort revisions). mart_el_curve (135 rows) equals the pandas computation exactly; reconciliation classes equal the planted 2,804 / 120 / 80 / 36,946 / 50. Three things failed and need a decision in the plan: named parameters are not bound when the Delta SQL extension is on (UNBOUND_SQL_PARAMETER, fixed by spark.sql.legacy.parameterSubstitution.constantsOnly=true, or use {placeholders} / session variables); SELECT ... FROM (DESCRIBE HISTORY ...) is a ParseException; a run with an older as_of is not a no-op (it would re-open 120 closed versions), so the runner now refuses it. dim_user is Type 1, so user_kind for E(L) must come from the Silver revision (424 history revisions have another kind in dim_user). delta-rs 1.6.6 reads all 12 Gold tables with the same row counts; protocol is reader 1 / writer 2, and writer 7 with changeDataFeed on the two facts. Cost: 255 s for the whole runner (159 s in write statements, 3 to 11 s each even on tiny tables), driver peak RSS 3.5 GB. The repo is untouched (git status --porcelain is empty).

## Versions and session

All RAN in `/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/gold_sql_lab` (called `<lab>` below).

| Item | Value |
|---|---|
| Spark venv (reused, nothing installed) | Python 3.12.3, pyspark 4.2.0, delta-spark 4.4.1 (`io.delta:delta-spark_4.2_2.13:4.4.1` from the existing Ivy cache: `0 artifacts copied, 33 already retrieved`) |
| Java | OpenJDK 21.0.12.1 |
| Session | `local[2]`, `spark.driver.memory=4g`, `spark.sql.session.timeZone=UTC`, `spark.sql.shuffle.partitions=4`, `PYSPARK_PYTHON=sys.executable`; start 5.5 s |
| delta-rs venv (reused) | deltalake 1.6.6, pandas 2.3.3, pyarrow 26.0.1, polars 2.1.0, numpy 2.5.4 |
| Lake | `<lab>/lake/silver/<table>/` written by delta-rs, `<lab>/lake/gold/<table>/` written by Spark SQL. One engine writes each table. |

Run order (each command from `<lab>`, with `PYTHONDONTWRITEBYTECODE=1`):

```bash
<deltars venv>/bin/python gen_silver.py      # 0.6 s  -> lake/silver + planted.json
<spark venv>/bin/python   run_gold.py        # 255 s  -> lake/gold + out/run_gold.json (78 checks)
<deltars venv>/bin/python verify_gold.py     # 1.9 s  -> out/verify_gold.json (18 checks, no Spark)
```

Start the runner with `bash`, not `sh` (see Pitfalls). `run_gold.py` expects an empty `lake/gold` for the two-run scenario of this lab.

**Session factory (`spark_session.py`, RAN in every run):**

```python
"""SparkSession factory for the Gold SQL lab (copy of spark_lab/scripts/lab.py get_spark, folders changed).

Every side folder (warehouse, shuffle files, Derby home) is under the lab folder. The Ivy cache is the
one the spark_lab already filled, so nothing is downloaded.
"""
import os
import sys

LAB = os.environ.get(
    "GOLD_LAB",
    "/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/gold_sql_lab",
)
IVY = os.environ.get(
    "GOLD_IVY",
    "/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/spark_lab/ivy",
)


def get_spark(app="truthlag_gold", extra=None, driver_mem="4g", master="local[2]"):
    # Python workers must be the SAME interpreter as the driver (PATH python3 can be another minor version).
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    b = (SparkSession.builder.master(master).appName(app)
         .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
         .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
         .config("spark.driver.memory", driver_mem)
         .config("spark.sql.shuffle.partitions", "4")
         .config("spark.ui.enabled", "false")
         .config("spark.ui.showConsoleProgress", "false")
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.sql.warehouse.dir", LAB + "/warehouse")
         .config("spark.local.dir", LAB + "/sparktmp")
         .config("spark.jars.ivy", IVY)
         .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={LAB}/derby -Duser.timezone=UTC"))
    for k, v in (extra or {}).items():
        b = b.config(k, v)
    spark = configure_spark_with_delta_pip(b).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark
```

Optional addition if the plan wants `:named` parameters (RAN in `probe_params2.py`, not used in the main run): `.config("spark.sql.legacy.parameterSubstitution.constantsOnly", "true")`.

## Made-up data

Generator: `<lab>/gen_silver.py`, delta-rs writer, seed 20261113. RAN three times; `planted.json` was identical each time (compared in Python: `True`). All six Silver tables are version 0, reader 1 / writer 2, with `delta.logRetentionDuration` and `delta.deletedFileRetentionDuration` = `interval 3650 days` and `delta.enableExpiredLogCleanup` = `false` (read back with delta-rs). `history_slim` is partitioned by `snapshot`. Timestamps are `timestamp[us, UTC]`.

| Silver table | Rows | What is planted |
|---|---|---|
| page_change | 57,665 (edit 57,343, move 224, create 45, delete 35, undelete 18) on 1,945 pages | moves, namespace changes 0 -> 118 and 118 -> 0, deletes, undeletes, pages with 2 or 3 changes after as_of 1, 25 pages first seen after as_of 1, 20 creates inside the live window, 6 pairs of edits in the same second. Delete / undelete events carry the rev_id and rev_dt of the page's newest (older) revision and a meta_dt with milliseconds |
| live_revisions | 40,000 | 40 revisions by 'unknown' editors; 10 editors renamed since September, 5 became bots, 3 renamed inside the live window |
| history_revisions | 40,000 on 1,800 pages | 30 pages moved once inside the history window, 5 moved there and back; 40 pages moved between the cohorts |
| live_revert_links | 3,023 (2,932 within_followup) | T_s from 0 s to about 4.9 days; 36 links with T_s exactly on a wait point and K_s = 0; 36 with K_s = 1.25; 40 with T_s = wait - 2 and K_s = 3.5; 5 with T_s = 0, K_s = 2.0; 3 with T_s = 345,601; 3 with T_s = 345,599, K_s = 3.5 |
| history_revert_links | 4,051 | T_s from 1 s to about 23 days; 45 on wait points; 3 with T_s = -5; 3 with T_s = 345,601 |
| history_slim | 450,000 = 150,000 (snapshot 2026-09, month 09) + 150,000 (2026-10, month 09 restated) + 150,000 (2026-10, month 10) | exactly 700 label changes; 50 live revisions left out of the dump; 120 stream_only and 80 dump_only disagreements |

**Planted counts (`<lab>/planted.json`, RAN):**

```json
{
 "seed": 20261113, "as_of_1": "2026-10-23 00:00:00+00:00", "as_of_2": "2026-10-27 21:00:00+00:00", "as_of_users_1": "2026-10-01 00:00:00+00:00",
 "sizes": {"page_change_rows": 57665, "page_change_by_kind": {"edit": 57343, "move": 224, "create": 45, "delete": 35, "undelete": 18},
   "pages_in_page_change": 1945, "pages_in_history": 1800, "pages_total": 2145, "pages_first_seen_after_as_of_1": 25,
   "pages_created_inside_live_window": 20, "same_second_edit_pairs": 6, "live_revisions": 40000, "history_revisions": 40000,
   "live_revert_links": 3023, "live_links_within_followup": 2932, "history_revert_links": 4051,
   "history_slim": {"2026-09/2026-09": 150000, "2026-10/2026-09": 150000, "2026-10/2026-10": 150000}},
 "pages_per_category": {"sep_move_once": 30, "sep_move_there_and_back": 5, "gap_move": 40, "m1_before": 60, "m1_after": 50, "m2_after": 20,
   "m2_before": 15, "m_before_after": 10, "ns_after": 10, "ns_before": 5, "del_after": 12, "del_undel_after": 8,
   "del_before_undel_after": 6, "del_before": 5, "mv_del_undel_after": 4, "ns_to_main_before": 5},
 "label_changes": {"total": 700, "became_reverted": 600, "became_unreverted": 60, "reverter_or_time_changed": 40,
   "reverter_only": 20, "seconds_only": 15, "reverter_and_seconds": 5,
   "split": {"became_reverted": {"history_cohort": 200, "other": 400}, "became_unreverted": {"history_cohort": 20, "other": 40},
             "reverter_or_time_changed": {"history_cohort": 15, "other": 25}}},
 "fact_revert_label": {"rows_after_2026-09": 150000, "rows_after_2026-10": 300000, "updated_by_2026-10": 700, "inserted_by_2026-10": 150000,
   "history_cohort_reverted_any_as_of_2026-09": 4051, "history_cohort_reverted_any_as_of_2026-10": 4231},
 "reconciliation_live_vs_2026-10": {"both_reverted": 2804, "stream_only": 120, "dump_only": 80, "neither": 36946, "not_in_dump": 50,
   "recon_mismatch_rows": 250,
   "split": {"not_in_dump": {"with_stream_link_within_followup": 8, "without_stream_link": 42},
             "stream_only": {"dump_not_reverted": 90, "dump_reverted_after_horizon": 30},
             "dump_only": {"no_stream_link": 60, "stream_link_after_horizon": 20}, "both_reverted_but_other_seconds": 100}},
 "fact_edit": {"rows": 80000, "live_flag_true_at_as_of_1": 2641, "live_flag_true_at_as_of_2": 2932, "rows_updated_by_run_2": 291,
   "user_key_unknown_rows": 80},
 "dim_user": {"rows_run_1": 369, "rows_run_2": 399, "inserted_by_run_2": 30, "updated_by_run_2": 18,
   "planted_renamed_between": 10, "planted_became_bot": 5, "planted_renamed_within_live": 3},
 "dim_time": {"rows": 8640},
 "el_special_links": {"live_T_on_wait_point_K0": 36, "live_T_on_wait_point_K1.25": 36, "live_T_2s_before_wait_point_K3.5": 40, "live_T0_K2": 5,
   "live_T_horizon_plus_1": 3, "live_T_horizon_minus_1_K3.5": 3, "history_T_on_wait_point": 45, "history_T_minus_5": 3, "history_T_horizon_plus_1": 3}
}
```

Note: `pages_per_category` counts planted pages, not visible versions. 6 of the 40 gap-move pages have no September observation, so their move makes no version. The expected version list is therefore computed by an independent Python loop in `verify_gold.py`, not from these counts.

**Generator in full (`gen_silver.py`, RAN):**

```python
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
```

## Gold SQL

All files are under `<lab>/sql/`. One statement per file. `{silver}` and `{gold}` are the layer folders; other `{placeholders}` are filled by the runner (values are checked against `^[A-Za-z0-9_ :./\-]*$`). Every statement below RAN in the final rebuild.

Run order: `ddl/*.sql` (12 tables; `ddl/dim_page.sql` twice, for `dim_page` and `dim_page_classic`), `10`, `20`, then for as_of 1: `21`, `22`, `23`, (`21`, `24`, `25`), `13`, `12`, `30`; for as_of 2: `21`, `22`, `23`, `26` (expected failure), (`21`, `24`, `25`), `13`, `12`, `30`; then per snapshot `11`, `40`; then `50`, `80`, `60`, `69`, `70`, `71`.

Design choices the plan should know:
- `dim_page` observations: `observed_dt` is the revision time for history rows and for edit / create / move events, and `meta_dt` for delete / undelete events. One state per page and second (the last one wins), so that `page_key` (seconds) cannot collide.
- `fact_edit.user_key` and `dim_user.user_key` use the member `'unknown'` where Silver has a NULL key, so every fact row has a dim_user row.
- `fact_edit.live_revert_flag` is NULL for history-cohort rows (no live observation), true / false for live rows.
- `fact_revert_label`: `'{snapshot}' >= last_changed_snapshot` stops an older snapshot from overwriting a newer label.
- The three marts `mart_el_curve`, `mart_reconciliation`, `recon_mismatch` are full or partial replaces (they write a commit on every run). All dims, facts and `mart_label_change` are pre-filtered MERGEs (a re-run writes no commit).
- `mart_el_curve` takes `user_kind` from the Silver revision (kind at edit time), not from `dim_user`.

### ddl/dim_cohort.sql
```sql
-- dim_cohort: one row per cohort. Values come from config.py (HISTORY_WINDOW, LIVE_WINDOW, *_FOLLOWUP_DAYS).
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_cohort` (
  cohort_id      STRING NOT NULL,
  source         STRING,
  window_start   TIMESTAMP,
  window_end     TIMESTAMP,
  followup_days  INT
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### ddl/dim_snapshot.sql
```sql
-- dim_snapshot: one row per MediaWiki History snapshot loaded into fact_revert_label.
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_snapshot` (
  snapshot         STRING NOT NULL,
  snapshot_cutoff  TIMESTAMP,
  loaded_at        TIMESTAMP,
  revision_rows    BIGINT
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### ddl/dim_time.sql
```sql
-- dim_time: one row per UTC minute that occurs in fact_edit. day_of_week: 1 = Monday .. 7 = Sunday.
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_time` (
  time_key      BIGINT NOT NULL,
  minute_start  TIMESTAMP,
  hour          INT,
  date          DATE,
  day_of_week   INT
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### ddl/dim_user.sql
```sql
-- dim_user: Type 1 (latest values win). user_key 'unknown' stands for editors whose name the source hides.
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_user` (
  user_key      STRING NOT NULL,
  user_id       BIGINT,
  user_text     STRING,
  user_kind     STRING,
  is_bot        BOOLEAN,
  is_temporary  BOOLEAN
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### ddl/dim_page.sql
```sql
-- dim_page: SCD Type 2. {dim_page} is the table folder (dim_page, or dim_page_classic for the comparison).
CREATE TABLE IF NOT EXISTS delta.`{gold}/{dim_page}` (
  page_key    STRING NOT NULL,
  wiki_db     STRING,
  page_id     BIGINT,
  title       STRING,
  namespace   INT,
  is_deleted  BOOLEAN,
  valid_from  TIMESTAMP,
  valid_to    TIMESTAMP,
  is_current  BOOLEAN
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### ddl/fact_edit.sql
```sql
-- fact_edit: one row per cohort revision (both cohorts). Change Data Feed on.
CREATE TABLE IF NOT EXISTS delta.`{gold}/fact_edit` (
  wiki_db             STRING NOT NULL,
  rev_id              BIGINT NOT NULL,
  parent_rev_id       BIGINT,
  page_key            STRING,
  user_key            STRING,
  time_key            BIGINT,
  event_dt            TIMESTAMP,
  seen_dt             TIMESTAMP,
  bytes_diff          BIGINT,
  is_bot              BOOLEAN,
  live_revert_flag    BOOLEAN,
  live_revert_dt      TIMESTAMP,
  live_known_dt       TIMESTAMP,
  revert_risk_score   DOUBLE,
  page_edits_prev_1h  BIGINT,
  cohort_id           STRING
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false',
  'delta.enableChangeDataFeed' = 'true'
)
```

### ddl/fact_revert_label.sql
```sql
-- fact_revert_label: the dump label of every revision of every loaded snapshot. Change Data Feed on.
CREATE TABLE IF NOT EXISTS delta.`{gold}/fact_revert_label` (
  wiki_db                     STRING NOT NULL,
  rev_id                      BIGINT NOT NULL,
  is_identity_reverted        BOOLEAN,
  reverting_rev_id            BIGINT,
  seconds_to_identity_revert  BIGINT,
  label_dt                    TIMESTAMP,
  first_reverted_snapshot     STRING,
  last_changed_snapshot       STRING
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false',
  'delta.enableChangeDataFeed' = 'true'
)
```

### ddl/mart_label_change.sql
```sql
-- mart_label_change: one row per revision whose dump label changed in a snapshot load (from the change feed).
CREATE TABLE IF NOT EXISTS delta.`{gold}/mart_label_change` (
  wiki_db         STRING NOT NULL,
  rev_id          BIGINT NOT NULL,
  from_snapshot   STRING,
  to_snapshot     STRING,
  was_reverted    BOOLEAN,
  is_reverted     BOOLEAN,
  change_class    STRING,
  commit_version  BIGINT NOT NULL
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### ddl/mart_el_curve.sql
```sql
-- mart_el_curve: E(L) = share of eventual reverts not yet known after waiting L.
CREATE TABLE IF NOT EXISTS delta.`{gold}/mart_el_curve` (
  cohort_id     STRING NOT NULL,
  label_source  STRING NOT NULL,
  user_kind     STRING NOT NULL,
  wait_label    STRING NOT NULL,
  wait_s        BIGINT NOT NULL,
  n_eventual    BIGINT,
  n_known       BIGINT,
  share_known   DOUBLE,
  e_l           DOUBLE,
  small_group   BOOLEAN
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### ddl/mart_reconciliation.sql
```sql
-- mart_reconciliation: stream label against dump label, counts per class, per cohort and snapshot.
CREATE TABLE IF NOT EXISTS delta.`{gold}/mart_reconciliation` (
  cohort_id      STRING NOT NULL,
  snapshot       STRING NOT NULL,
  label_version  BIGINT,
  recon_class    STRING NOT NULL,
  n_revisions    BIGINT,
  share          DOUBLE
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### ddl/recon_mismatch.sql
```sql
-- recon_mismatch: the revisions where stream and dump disagree, or that the dump does not hold.
CREATE TABLE IF NOT EXISTS delta.`{gold}/recon_mismatch` (
  wiki_db                    STRING NOT NULL,
  rev_id                     BIGINT NOT NULL,
  cohort_id                  STRING NOT NULL,
  snapshot                   STRING NOT NULL,
  recon_class                STRING,
  event_dt                   TIMESTAMP,
  stream_reverted            BOOLEAN,
  stream_revert_dt           TIMESTAMP,
  stream_known_dt            TIMESTAMP,
  stream_seconds_to_revert   BIGINT,
  dump_reverted              BOOLEAN,
  dump_is_identity_reverted  BOOLEAN,
  dump_label_dt              TIMESTAMP,
  dump_seconds_to_revert     BIGINT,
  dump_reverting_rev_id      BIGINT
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
```

### 10_dim_cohort_merge.sql
```sql
-- dim_cohort: Type 1 upsert, changed rows only. The values are the cohort rules of config.py.
-- (Named parameters, :name with spark.sql(text, args=...), are NOT bound inside MERGE here: see Pitfalls.)
MERGE INTO delta.`{gold}/dim_cohort` t
USING (
  SELECT s.*
  FROM (
    SELECT 'history' AS cohort_id, 'dump' AS source,
           TIMESTAMP '{history_start}' AS window_start, TIMESTAMP '{history_end}' AS window_end,
           CAST({history_followup_days} AS INT) AS followup_days
    UNION ALL
    SELECT 'live', 'stream',
           TIMESTAMP '{live_start}', TIMESTAMP '{live_end}', CAST({live_followup_days} AS INT)
  ) s
  LEFT JOIN delta.`{gold}/dim_cohort` d ON d.cohort_id = s.cohort_id
  WHERE d.cohort_id IS NULL
     OR NOT (d.source <=> s.source AND d.window_start <=> s.window_start
             AND d.window_end <=> s.window_end AND d.followup_days <=> s.followup_days)
) s
ON t.cohort_id = s.cohort_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
```

### 11_dim_snapshot_merge.sql
```sql
-- dim_snapshot: one row per loaded snapshot. loaded_at is not compared, so a re-run writes nothing.
MERGE INTO delta.`{gold}/dim_snapshot` t
USING (
  SELECT s.*
  FROM (
    SELECT snapshot, max(event_timestamp) AS snapshot_cutoff, current_timestamp() AS loaded_at,
           count(*) AS revision_rows
    FROM delta.`{silver}/history_slim`
    WHERE snapshot = '{snapshot}'
    GROUP BY snapshot
  ) s
  LEFT JOIN delta.`{gold}/dim_snapshot` d ON d.snapshot = s.snapshot
  WHERE d.snapshot IS NULL
     OR NOT (d.snapshot_cutoff <=> s.snapshot_cutoff AND d.revision_rows <=> s.revision_rows)
) s
ON t.snapshot = s.snapshot
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
```

### 12_dim_time_merge.sql
```sql
-- dim_time: insert-only. One row per UTC minute of a cohort revision (the same minutes as fact_edit.time_key).
MERGE INTO delta.`{gold}/dim_time` t
USING (
  SELECT DISTINCT CAST(date_format(ts, 'yyyyMMddHHmm') AS BIGINT) AS time_key,
                  date_trunc('minute', ts) AS minute_start
  FROM (
    SELECT ts FROM delta.`{silver}/history_revisions` WHERE ts <= TIMESTAMP '{as_of}'
    UNION ALL
    SELECT ts FROM delta.`{silver}/live_revisions` WHERE ts <= TIMESTAMP '{as_of}'
  )
) s
ON t.time_key = s.time_key
WHEN NOT MATCHED THEN INSERT (time_key, minute_start, hour, date, day_of_week)
VALUES (s.time_key, s.minute_start, hour(s.minute_start), CAST(s.minute_start AS DATE), weekday(s.minute_start) + 1)
```

### 13_dim_user_merge.sql
```sql
-- dim_user: Type 1. Per user_key the values of the newest cohort revision (ts, then rev_id) win.
-- Only new keys and keys whose values changed reach the MERGE, so a re-run writes no commit.
MERGE INTO delta.`{gold}/dim_user` t
USING (
  WITH revs AS (
    SELECT user_key, user_id, user_name, user_kind, is_bot, is_temp, ts, rev_id
    FROM delta.`{silver}/history_revisions` WHERE ts <= TIMESTAMP '{as_of}'
    UNION ALL
    SELECT user_key, user_id, user_name, user_kind, is_bot, is_temp, ts, rev_id
    FROM delta.`{silver}/live_revisions` WHERE ts <= TIMESTAMP '{as_of}'
  ),
  latest AS (
    SELECT coalesce(user_key, 'unknown') AS user_key,
           max_by(named_struct('user_id', user_id, 'user_text', user_name, 'user_kind', user_kind,
                               'is_bot', is_bot, 'is_temporary', is_temp),
                  named_struct('ts', ts, 'rev_id', rev_id)) AS v
    FROM revs
    GROUP BY coalesce(user_key, 'unknown')
  )
  SELECT l.user_key, l.v.user_id AS user_id, l.v.user_text AS user_text, l.v.user_kind AS user_kind,
         l.v.is_bot AS is_bot, l.v.is_temporary AS is_temporary
  FROM latest l
  LEFT JOIN delta.`{gold}/dim_user` d ON d.user_key = l.user_key
  WHERE d.user_key IS NULL
     OR NOT (d.user_id <=> l.v.user_id AND d.user_text <=> l.v.user_text AND d.user_kind <=> l.v.user_kind
             AND d.is_bot <=> l.v.is_bot AND d.is_temporary <=> l.v.is_temporary)
) s
ON t.user_key = s.user_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
```

### 20_page_obs_view.sql
```sql
-- Every observation of a page's title, namespace and deleted state, from both sources.
-- observed_dt = when the state is true: the revision time for history rows and for edit / create / move
-- events; meta_dt for delete / undelete events (they make no revision: their rev_dt is the page's
-- newest revision, which is older than the delete).
CREATE OR REPLACE TEMP VIEW v_page_obs AS
SELECT wiki_db, page_id, page_title_historical AS title, CAST(page_ns AS INT) AS namespace,
       false AS is_deleted, ts AS observed_dt, rev_id AS seq_id
FROM delta.`{silver}/history_revisions`
UNION ALL
SELECT wiki_id AS wiki_db, page_id, page_title AS title, ns AS namespace,
       kind = 'delete' AS is_deleted,
       CASE WHEN kind IN ('delete', 'undelete') THEN meta_dt ELSE rev_dt END AS observed_dt,
       coalesce(rev_id, 0) AS seq_id
FROM delta.`{silver}/page_change`
WHERE page_id IS NOT NULL
```

### 21_page_versions_view.sql
```sql
-- SCD2 step 1: the FULL list of versions of every page, from all observations up to {as_of}.
-- One state per page and second (the last one wins), LAG finds the changes, LEAD gives valid_to.
-- The first version of a page starts at the sentinel 1900-01-01 so that earlier facts still join.
CREATE OR REPLACE TEMP VIEW v_page_versions AS
WITH per_second AS (
  SELECT wiki_db, page_id, date_trunc('second', observed_dt) AS obs_dt,
         max_by(named_struct('title', title, 'namespace', namespace, 'is_deleted', is_deleted),
                named_struct('observed_dt', observed_dt, 'seq_id', seq_id)) AS st
  FROM v_page_obs
  WHERE observed_dt <= TIMESTAMP '{as_of}'
  GROUP BY wiki_db, page_id, date_trunc('second', observed_dt)
),
marked AS (
  SELECT wiki_db, page_id, obs_dt, st.title AS title, st.namespace AS namespace, st.is_deleted AS is_deleted,
         lag(st) OVER w AS prev,
         row_number() OVER w AS rn
  FROM per_second
  WINDOW w AS (PARTITION BY wiki_db, page_id ORDER BY obs_dt)
),
starts AS (
  SELECT wiki_db, page_id, title, namespace, is_deleted,
         CASE WHEN rn = 1 THEN TIMESTAMP '1900-01-01 00:00:00' ELSE obs_dt END AS valid_from
  FROM marked
  WHERE rn = 1
     OR NOT (title <=> prev.title AND namespace <=> prev.namespace AND is_deleted <=> prev.is_deleted)
)
SELECT concat(page_id, '-', date_format(valid_from, 'yyyyMMddHHmmss')) AS page_key,
       wiki_db, page_id, title, namespace, is_deleted, valid_from,
       lead(valid_from) OVER (PARTITION BY wiki_db, page_id ORDER BY valid_from) AS valid_to,
       lead(valid_from) OVER (PARTITION BY wiki_db, page_id ORDER BY valid_from) IS NULL AS is_current
FROM starts
```

### 22_page_changes_view.sql
```sql
-- SCD2 step 2: keep only the versions that are new, or whose valid_to / is_current changed.
CREATE OR REPLACE TEMP VIEW v_page_changes AS
SELECT n.*
FROM v_page_versions n
LEFT JOIN delta.`{gold}/dim_page` d ON d.page_key = n.page_key
WHERE d.page_key IS NULL
   OR NOT (d.valid_to <=> n.valid_to)
   OR NOT (d.is_current <=> n.is_current)
```

### 23_dim_page_merge.sql
```sql
-- SCD2 step 3: one MERGE on page_key. Matched = close the version; not matched = new version.
MERGE INTO delta.`{gold}/dim_page` t
USING v_page_changes s
ON t.page_key = s.page_key
WHEN MATCHED THEN UPDATE SET t.valid_to = s.valid_to, t.is_current = s.is_current
WHEN NOT MATCHED THEN INSERT (page_key, wiki_db, page_id, title, namespace, is_deleted, valid_from, valid_to, is_current)
VALUES (s.page_key, s.wiki_db, s.page_id, s.title, s.namespace, s.is_deleted, s.valid_from, s.valid_to, s.is_current)
```

### 24_page_classic_changed_view.sql
```sql
-- Classic SCD2 (for comparison only): ONE incoming row per page = its current state in v_page_versions.
CREATE OR REPLACE TEMP VIEW v_page_classic_changed AS
SELECT u.*, d.page_id IS NOT NULL AS has_current
FROM (SELECT * FROM v_page_versions WHERE is_current) u
LEFT JOIN (SELECT * FROM delta.`{gold}/dim_page_classic` WHERE is_current) d
  ON d.wiki_db = u.wiki_db AND d.page_id = u.page_id
WHERE d.page_id IS NULL
   OR (NOT (d.title <=> u.title AND d.namespace <=> u.namespace AND d.is_deleted <=> u.is_deleted)
       AND u.valid_from > d.valid_from)
```

### 25_dim_page_classic_merge.sql
```sql
-- Classic staged-source SCD2 MERGE (NULL merge key), as in the spark_lab report.
-- Row with merge_key = page_id closes the old current row; row with merge_key NULL never matches and is inserted.
MERGE INTO delta.`{gold}/dim_page_classic` t
USING (
  SELECT page_id AS merge_key, * FROM v_page_classic_changed WHERE has_current
  UNION ALL
  SELECT CAST(NULL AS BIGINT) AS merge_key, * FROM v_page_classic_changed
) s
ON t.wiki_db = s.wiki_db AND t.page_id = s.merge_key AND t.is_current = true
WHEN MATCHED THEN UPDATE SET t.is_current = false, t.valid_to = s.valid_from
WHEN NOT MATCHED THEN INSERT (page_key, wiki_db, page_id, title, namespace, is_deleted, valid_from, valid_to, is_current)
VALUES (s.page_key, s.wiki_db, s.page_id, s.title, s.namespace, s.is_deleted, s.valid_from, CAST(NULL AS TIMESTAMP), true)
```

### 26_dim_page_classic_all_versions_merge.sql
```sql
-- Demo of the classic form's limit: feed EVERY new version (not one row per page). Expected to FAIL when
-- a page has two or more new versions, because two source rows then match the one current target row.
MERGE INTO delta.`{gold}/dim_page_classic` t
USING (
  SELECT n.page_id AS merge_key, n.*
  FROM v_page_versions n
  JOIN (SELECT * FROM delta.`{gold}/dim_page_classic` WHERE is_current) d
    ON d.wiki_db = n.wiki_db AND d.page_id = n.page_id AND n.valid_from > d.valid_from
  UNION ALL
  SELECT CAST(NULL AS BIGINT) AS merge_key, n.*
  FROM v_page_versions n
  JOIN (SELECT * FROM delta.`{gold}/dim_page_classic` WHERE is_current) d
    ON d.wiki_db = n.wiki_db AND d.page_id = n.page_id AND n.valid_from > d.valid_from
) s
ON t.wiki_db = s.wiki_db AND t.page_id = s.merge_key AND t.is_current = true
WHEN MATCHED THEN UPDATE SET t.is_current = false, t.valid_to = s.valid_from
WHEN NOT MATCHED THEN INSERT (page_key, wiki_db, page_id, title, namespace, is_deleted, valid_from, valid_to, is_current)
VALUES (s.page_key, s.wiki_db, s.page_id, s.title, s.namespace, s.is_deleted, s.valid_from, s.valid_to, s.is_current)
```

### 30_fact_edit_merge.sql
```sql
-- fact_edit: one row per cohort revision with ts <= {as_of}; live labels known up to {as_of}.
-- page_key is the dim_page version valid at the edit time (as-of join). MERGE on (wiki_db, rev_id),
-- pre-filtered to new or changed rows, so a re-run writes no commit and the change feed holds real changes only.
MERGE INTO delta.`{gold}/fact_edit` t
USING (
  WITH revs AS (
    SELECT cohort, wiki_db, rev_id, parent_id, page_id, user_key, ts, seen_ts, size_delta, is_bot,
           revert_risk, page_edits_prev_1h
    FROM delta.`{silver}/history_revisions` WHERE ts <= TIMESTAMP '{as_of}'
    UNION ALL
    SELECT cohort, wiki_db, rev_id, parent_id, page_id, user_key, ts, seen_ts, size_delta, is_bot,
           revert_risk, page_edits_prev_1h
    FROM delta.`{silver}/live_revisions` WHERE ts <= TIMESTAMP '{as_of}'
  ),
  links AS (
    SELECT reverted_rev_id, reverting_ts, known_at
    FROM delta.`{silver}/live_revert_links`
    WHERE within_followup AND known_at <= TIMESTAMP '{as_of}'
  ),
  src AS (
    SELECT r.wiki_db, r.rev_id, r.parent_id AS parent_rev_id, p.page_key,
           coalesce(r.user_key, 'unknown') AS user_key,
           CAST(date_format(r.ts, 'yyyyMMddHHmm') AS BIGINT) AS time_key,
           r.ts AS event_dt, r.seen_ts AS seen_dt, r.size_delta AS bytes_diff, r.is_bot,
           CASE WHEN r.cohort = 'live' THEN l.reverted_rev_id IS NOT NULL END AS live_revert_flag,
           l.reverting_ts AS live_revert_dt, l.known_at AS live_known_dt,
           r.revert_risk AS revert_risk_score, r.page_edits_prev_1h, r.cohort AS cohort_id
    FROM revs r
    LEFT JOIN delta.`{gold}/dim_page` p
      ON p.wiki_db = r.wiki_db AND p.page_id = r.page_id
     AND r.ts >= p.valid_from AND (p.valid_to IS NULL OR r.ts < p.valid_to)
    LEFT JOIN links l ON r.cohort = 'live' AND l.reverted_rev_id = r.rev_id
  )
  SELECT s.*
  FROM src s
  LEFT JOIN delta.`{gold}/fact_edit` f ON f.wiki_db = s.wiki_db AND f.rev_id = s.rev_id
  WHERE f.rev_id IS NULL
     OR NOT (f.parent_rev_id <=> s.parent_rev_id AND f.page_key <=> s.page_key AND f.user_key <=> s.user_key
             AND f.time_key <=> s.time_key AND f.event_dt <=> s.event_dt AND f.seen_dt <=> s.seen_dt
             AND f.bytes_diff <=> s.bytes_diff AND f.is_bot <=> s.is_bot
             AND f.live_revert_flag <=> s.live_revert_flag AND f.live_revert_dt <=> s.live_revert_dt
             AND f.live_known_dt <=> s.live_known_dt AND f.revert_risk_score <=> s.revert_risk_score
             AND f.page_edits_prev_1h <=> s.page_edits_prev_1h AND f.cohort_id <=> s.cohort_id)
) s
ON t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
```

### 40_fact_revert_label_merge.sql
```sql
-- fact_revert_label: load ONE snapshot as ONE commit. Updates only rows whose label columns changed,
-- inserts the revisions not seen before. An older snapshot can never overwrite a newer label
-- ('{snapshot}' >= last_changed_snapshot), so re-running any load writes no commit.
MERGE INTO delta.`{gold}/fact_revert_label` t
USING (
  WITH snap AS (
    SELECT 'enwiki' AS wiki_db, revision_id AS rev_id,
           coalesce(revision_is_identity_reverted, false) AS is_identity_reverted,
           revision_first_identity_reverting_revision_id AS reverting_rev_id,
           revision_seconds_to_identity_revert AS seconds_to_identity_revert,
           CASE WHEN coalesce(revision_is_identity_reverted, false)
                THEN timestamp_micros(unix_micros(event_timestamp) + revision_seconds_to_identity_revert * 1000000)
           END AS label_dt
    FROM delta.`{silver}/history_slim`
    WHERE snapshot = '{snapshot}'
  )
  SELECT s.*,
         CASE WHEN s.is_identity_reverted THEN '{snapshot}' END AS first_reverted_snapshot,
         '{snapshot}' AS last_changed_snapshot
  FROM snap s
  LEFT JOIN delta.`{gold}/fact_revert_label` f ON f.wiki_db = s.wiki_db AND f.rev_id = s.rev_id
  WHERE f.rev_id IS NULL
     OR ('{snapshot}' >= f.last_changed_snapshot
         AND NOT (f.is_identity_reverted <=> s.is_identity_reverted
                  AND f.reverting_rev_id <=> s.reverting_rev_id
                  AND f.seconds_to_identity_revert <=> s.seconds_to_identity_revert
                  AND f.label_dt <=> s.label_dt))
) s
ON t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id
WHEN MATCHED THEN UPDATE SET
  t.is_identity_reverted = s.is_identity_reverted,
  t.reverting_rev_id = s.reverting_rev_id,
  t.seconds_to_identity_revert = s.seconds_to_identity_revert,
  t.label_dt = s.label_dt,
  t.first_reverted_snapshot = coalesce(t.first_reverted_snapshot, s.first_reverted_snapshot),
  t.last_changed_snapshot = s.last_changed_snapshot
WHEN NOT MATCHED THEN INSERT (wiki_db, rev_id, is_identity_reverted, reverting_rev_id, seconds_to_identity_revert,
                              label_dt, first_reverted_snapshot, last_changed_snapshot)
VALUES (s.wiki_db, s.rev_id, s.is_identity_reverted, s.reverting_rev_id, s.seconds_to_identity_revert,
        s.label_dt, s.first_reverted_snapshot, s.last_changed_snapshot)
```

### 50_mart_label_change_merge.sql
```sql
-- mart_label_change: one row per label change, from the change feed of fact_revert_label
-- (versions {start_version} .. {end_version}). Insert-only MERGE on (wiki_db, rev_id, commit_version).
MERGE INTO delta.`{gold}/mart_label_change` t
USING (
  SELECT post.wiki_db, post.rev_id,
         pre.last_changed_snapshot AS from_snapshot, post.last_changed_snapshot AS to_snapshot,
         pre.is_identity_reverted AS was_reverted, post.is_identity_reverted AS is_reverted,
         CASE WHEN NOT pre.is_identity_reverted AND post.is_identity_reverted THEN 'became_reverted'
              WHEN pre.is_identity_reverted AND NOT post.is_identity_reverted THEN 'became_unreverted'
              ELSE 'reverter_or_time_changed' END AS change_class,
         post._commit_version AS commit_version
  FROM table_changes_by_path('{gold}/fact_revert_label', {start_version}, {end_version}) post
  JOIN table_changes_by_path('{gold}/fact_revert_label', {start_version}, {end_version}) pre
    ON pre.wiki_db = post.wiki_db AND pre.rev_id = post.rev_id AND pre._commit_version = post._commit_version
  WHERE post._change_type = 'update_postimage' AND pre._change_type = 'update_preimage'
) s
ON t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id AND t.commit_version = s.commit_version
WHEN NOT MATCHED THEN INSERT *
```

### 60_mart_el_curve_overwrite.sql
```sql
-- mart_el_curve: full rebuild. An eventual revert has 0 <= T_s <= {horizon_s}; it is known by wait L
-- when T_s + coalesce(K_s, 0) <= L (inclusive). e_l = 1 - n_known / n_eventual.
-- user_kind is the kind AT EDIT TIME (Silver revisions), not dim_user (Type 1, latest kind).
INSERT OVERWRITE delta.`{gold}/mart_el_curve`
WITH waits AS (
  SELECT * FROM VALUES ('0', 0L), ('1 min', 60L), ('5 min', 300L), ('15 min', 900L), ('1 h', 3600L),
                       ('6 h', 21600L), ('1 d', 86400L), ('2 d', 172800L), ('4 d', 345600L)
       AS w(wait_label, wait_s)
),
reverts AS (
  SELECT 'live' AS cohort_id, 'stream' AS label_source, r.user_kind,
         CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0) AS known_after_s
  FROM delta.`{silver}/live_revert_links` l
  JOIN delta.`{silver}/live_revisions` r ON r.rev_id = l.reverted_rev_id
  WHERE l.T_s >= 0 AND l.T_s <= {horizon_s}
  UNION ALL
  SELECT 'history', 'dump', r.user_kind, CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0)
  FROM delta.`{silver}/history_revert_links` l
  JOIN delta.`{silver}/history_revisions` r ON r.rev_id = l.reverted_rev_id
  WHERE l.T_s >= 0 AND l.T_s <= {horizon_s}
  UNION ALL
  SELECT 'live', 'dump', r.user_kind, CAST(f.seconds_to_identity_revert AS DOUBLE)
  FROM delta.`{gold}/fact_revert_label` f
  JOIN delta.`{silver}/live_revisions` r ON r.wiki_db = f.wiki_db AND r.rev_id = f.rev_id
  WHERE f.is_identity_reverted AND f.seconds_to_identity_revert >= 0 AND f.seconds_to_identity_revert <= {horizon_s}
)
SELECT cohort_id, label_source,
       CASE WHEN grouping(user_kind) = 1 THEN 'all' ELSE user_kind END AS user_kind,
       wait_label, wait_s,
       count(*) AS n_eventual,
       count_if(known_after_s <= wait_s) AS n_known,
       count_if(known_after_s <= wait_s) / count(*) AS share_known,
       1 - count_if(known_after_s <= wait_s) / count(*) AS e_l,
       count(*) < {small_group_n} AS small_group
FROM reverts CROSS JOIN waits
GROUP BY GROUPING SETS ((cohort_id, label_source, user_kind, wait_label, wait_s),
                        (cohort_id, label_source, wait_label, wait_s))
```

### 69_recon_view.sql
```sql
-- Reconciliation of one cohort against one snapshot, on (wiki_db, rev_id).
-- Stream label = fact_edit.live_revert_flag (a within_followup link exists).
-- Dump label   = is_identity_reverted with seconds <= {horizon_s}, read from the version of
-- fact_revert_label that the load of {snapshot} wrote ({label_version}, found by its commit metadata).
CREATE OR REPLACE TEMP VIEW v_recon AS
WITH j AS (
  SELECT e.wiki_db, e.rev_id, e.cohort_id, e.event_dt,
         coalesce(e.live_revert_flag, false) AS stream_reverted,
         e.live_revert_dt AS stream_revert_dt, e.live_known_dt AS stream_known_dt,
         l.rev_id IS NOT NULL AS in_dump,
         coalesce(l.is_identity_reverted AND l.seconds_to_identity_revert <= {horizon_s}, false) AS dump_reverted_h,
         l.is_identity_reverted AS dump_is_identity_reverted, l.label_dt AS dump_label_dt,
         l.seconds_to_identity_revert AS dump_seconds_to_revert, l.reverting_rev_id AS dump_reverting_rev_id
  FROM delta.`{gold}/fact_edit` e
  LEFT JOIN delta.`{gold}/fact_revert_label` VERSION AS OF {label_version} l
    ON l.wiki_db = e.wiki_db AND l.rev_id = e.rev_id
  WHERE e.cohort_id = '{cohort_id}'
)
SELECT wiki_db, rev_id, cohort_id, '{snapshot}' AS snapshot,
       CASE WHEN NOT in_dump THEN 'not_in_dump'
            WHEN stream_reverted AND dump_reverted_h THEN 'both_reverted'
            WHEN stream_reverted THEN 'stream_only'
            WHEN dump_reverted_h THEN 'dump_only'
            ELSE 'neither' END AS recon_class,
       event_dt, stream_reverted, stream_revert_dt, stream_known_dt,
       unix_seconds(stream_revert_dt) - unix_seconds(event_dt) AS stream_seconds_to_revert,
       CASE WHEN in_dump THEN dump_reverted_h END AS dump_reverted,
       dump_is_identity_reverted, dump_label_dt, dump_seconds_to_revert, dump_reverting_rev_id
FROM j
```

### 70_mart_reconciliation_replace.sql
```sql
-- mart_reconciliation: replaces only the rows of this cohort and snapshot. All five classes always appear.
INSERT INTO delta.`{gold}/mart_reconciliation`
REPLACE WHERE cohort_id = '{cohort_id}' AND snapshot = '{snapshot}'
SELECT '{cohort_id}' AS cohort_id, '{snapshot}' AS snapshot, CAST({label_version} AS BIGINT) AS label_version,
       c.recon_class, count(v.rev_id) AS n_revisions,
       count(v.rev_id) / (SELECT count(*) FROM v_recon) AS share
FROM VALUES ('both_reverted'), ('stream_only'), ('dump_only'), ('neither'), ('not_in_dump') AS c(recon_class)
LEFT JOIN v_recon v ON v.recon_class = c.recon_class
GROUP BY c.recon_class
```

### 71_recon_mismatch_replace.sql
```sql
-- recon_mismatch: the revisions where the two labels disagree, plus the revisions the dump does not hold.
INSERT INTO delta.`{gold}/recon_mismatch`
REPLACE WHERE cohort_id = '{cohort_id}' AND snapshot = '{snapshot}'
SELECT wiki_db, rev_id, cohort_id, snapshot, recon_class, event_dt, stream_reverted, stream_revert_dt,
       stream_known_dt, stream_seconds_to_revert, dump_reverted, dump_is_identity_reverted, dump_label_dt,
       dump_seconds_to_revert, dump_reverting_rev_id
FROM v_recon
WHERE recon_class IN ('stream_only', 'dump_only', 'not_in_dump')
```

### 80_time_travel_then_and_now.sql
```sql
-- "As known then" against "now": reverted history-cohort revisions per snapshot.
-- {v_2026_09} and {v_2026_10} are the versions of fact_revert_label that the two snapshot loads wrote;
-- the runner finds them in DESCRIBE HISTORY by userMetadata (never by timestamp).
WITH hist AS (
  SELECT wiki_db, rev_id FROM delta.`{gold}/fact_edit` WHERE cohort_id = 'history'
),
then_now AS (
  SELECT '2026-09' AS snapshot, {v_2026_09} AS label_version, l.rev_id, l.is_identity_reverted
  FROM delta.`{gold}/fact_revert_label` VERSION AS OF {v_2026_09} l
  UNION ALL
  SELECT '2026-10', {v_2026_10}, l.rev_id, l.is_identity_reverted
  FROM delta.`{gold}/fact_revert_label` VERSION AS OF {v_2026_10} l
)
SELECT t.snapshot, t.label_version,
       count_if(t.is_identity_reverted) AS reverted_as_known_then,
       count_if(n.is_identity_reverted) AS reverted_now
FROM then_now t
JOIN hist h ON h.rev_id = t.rev_id
JOIN delta.`{gold}/fact_revert_label` n ON n.rev_id = t.rev_id
GROUP BY t.snapshot, t.label_version
ORDER BY t.snapshot
```

### run_gold.py (the runner, in full)
```python
"""Small runner for the Gold SQL files (one statement per .sql file under sql/).

Purpose : build the Gold layer (star schema, SCD2 dim_page, label fact with Change Data Feed, marts)
          from the Silver Delta tables with Spark SQL, record what every step did, and run the checks.
Inputs  : <lab>/lake/silver/* (made by gen_silver.py), <lab>/planted.json, <lab>/sql/*.sql
Outputs : <lab>/lake/gold/* (path-based Delta tables), <lab>/out/run_gold.json (steps, checks, protocol)
Run     : <spark venv>/bin/python run_gold.py          (local[2], spark.driver.memory=4g)

Rules the runner keeps:
- {placeholders} in a .sql file are replaced from a dict; values are checked against a safe pattern.
  Files that use :named parameters get them through spark.sql(text, args={...}).
- Before each write the commit user metadata is set to JSON {"step", "as_of", "snapshot"} and unset after.
- A table version is found through that metadata in DESCRIBE HISTORY, never through a timestamp.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

from spark_session import LAB, get_spark

SQL_DIR = os.path.join(LAB, "sql")
LAKE = os.path.join(LAB, "lake")
OUT = os.path.join(LAB, "out")
UM = "spark.databricks.delta.commitInfo.userMetadata"
PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")
SAFE_VALUE = re.compile(r"^[A-Za-z0-9_ :./\-]*$")
BASE = {"silver": LAKE + "/silver", "gold": LAKE + "/gold", "horizon_s": 345600, "small_group_n": 100}
GOLD = BASE["gold"]
# The two runs of the lab, the first dim_user run (history rows only), and the cohort rules of config.py.
A1, A2, AU1 = "2026-10-23 00:00:00", "2026-10-27 21:00:00", "2026-10-01 00:00:00"
COHORT_ARGS = {"history_start": "2026-09-08 00:00:00", "history_end": "2026-09-11 00:00:00", "history_followup_days": 20,
               "live_start": "2026-10-20 00:00:00", "live_end": "2026-10-23 00:00:00", "live_followup_days": 4}
TABLES = ["dim_cohort", "dim_snapshot", "dim_time", "dim_user", "dim_page", "dim_page_classic", "fact_edit",
          "fact_revert_label", "mart_label_change", "mart_el_curve", "mart_reconciliation", "recon_mismatch"]
METRIC_KEYS = ["numTargetRowsInserted", "numTargetRowsUpdated", "numTargetRowsDeleted", "numTargetRowsCopied",
               "numSourceRows", "numOutputRows", "numTargetFilesAdded", "numTargetFilesRemoved", "numFiles",
               "numTargetChangeFilesAdded", "executionTimeMs"]
STEPS: list[dict] = []
CHECKS: list[dict] = []


def render(name: str, params: dict) -> str:
    text = open(os.path.join(SQL_DIR, name)).read()

    def sub(m):
        key = m.group(1)
        if key not in params:
            raise KeyError(f"{name}: no value for {{{key}}}")
        val = str(params[key])
        if not SAFE_VALUE.match(val):
            raise ValueError(f"{name}: unsafe value for {{{key}}}: {val!r}")
        return val

    return PLACEHOLDER.sub(sub, text)


def table_version(spark, path: str):
    """Latest version of a path-based table, or None when it does not exist yet."""
    if not os.path.isdir(os.path.join(path, "_delta_log")):
        return None
    return spark.sql(f"DESCRIBE HISTORY delta.`{path}` LIMIT 1").first()["version"]


def find_version(spark, path: str, **match) -> int:
    """Newest version whose commit user metadata (JSON) has all the given values. No timestamps involved."""
    hits = []
    for h in spark.sql(f"DESCRIBE HISTORY delta.`{path}`").collect():
        try:
            meta = json.loads(h["userMetadata"] or "{}")
        except ValueError:
            continue
        if all(meta.get(k) == v for k, v in match.items()):
            hits.append(h["version"])
    if not hits:
        raise LookupError(f"no commit with {match} in {path}")
    return max(hits)


def newest_as_of(spark, path: str, step: str):
    """Newest as_of among the commits that this step wrote (from the commit user metadata), or None."""
    best = None
    if table_version(spark, path) is None:
        return None
    for h in spark.sql(f"DESCRIBE HISTORY delta.`{path}`").collect():
        try:
            meta = json.loads(h["userMetadata"] or "{}")
        except ValueError:
            continue
        if meta.get("step") == step and meta.get("as_of") and (best is None or meta["as_of"] > best):
            best = meta["as_of"]
    return best


def run_sql(spark, name: str, params: dict | None = None, meta: dict | None = None, args: dict | None = None):
    """Run one .sql file. meta is given for a statement that writes: it becomes the commit user metadata."""
    sql = render(name, {**BASE, **(params or {})})
    if meta is not None:
        spark.conf.set(UM, json.dumps(meta, sort_keys=True))
    try:
        df = spark.sql(sql, args=args) if args else spark.sql(sql)
        return df.collect()
    finally:
        if meta is not None:
            spark.conf.unset(UM)


def write_step(spark, label: str, sql_name: str, table: str, as_of=None, snapshot=None, params=None, args=None,
               step=None) -> dict:
    """Run a writing statement and record: seconds, version before / after, operation metrics, error."""
    path = f"{GOLD}/{table}"
    v0 = table_version(spark, path)
    meta = {"step": step or table, "as_of": as_of, "snapshot": snapshot}
    p = dict(params or {})
    if as_of is not None:
        p["as_of"] = as_of
    if snapshot is not None:
        p["snapshot"] = snapshot
    t0, err, rows = time.time(), None, None
    try:
        # The MERGE statements move a table to its state "as of" a time. An older as_of would move it back
        # (dim_page: closed versions would be opened again), so it is refused.
        newest = newest_as_of(spark, path, meta["step"]) if as_of is not None else None
        if newest is not None and as_of < newest:
            raise RuntimeError(f"refused: as_of {as_of} is older than the newest committed as_of {newest} of {table}")
        rows = run_sql(spark, sql_name, p, meta=meta, args=args)
    except Exception as e:  # recorded, the run goes on (some failures are expected and wanted)
        err = f"{type(e).__name__}: {str(e)[:900]}"
    rec = {"label": label, "sql": sql_name, "table": table, "as_of": as_of, "snapshot": snapshot,
           "seconds": round(time.time() - t0, 2), "version_before": v0, "version_after": table_version(spark, path),
           "error": err}
    rec["wrote_commit"] = rec["version_after"] != v0
    if rec["wrote_commit"]:
        h = spark.sql(f"DESCRIBE HISTORY delta.`{path}` LIMIT 1").first()
        om = h["operationMetrics"] or {}
        rec.update(operation=h["operation"], userMetadata=h["userMetadata"],
                   metrics={k: om[k] for k in METRIC_KEYS if k in om})
    if rows and len(rows) == 1:
        rec["result"] = rows[0].asDict()
    STEPS.append(rec)
    print("STEP", json.dumps(rec, default=str), flush=True)
    return rec


def view_step(spark, sql_name: str, **params):
    t0 = time.time()
    run_sql(spark, sql_name, params)
    print(f"VIEW {sql_name} {params} {time.time() - t0:.2f}s", flush=True)


def check(name: str, got, want, note: str = "") -> bool:
    ok = got == want
    CHECKS.append({"check": name, "got": got, "want": want, "ok": ok, "note": note})
    print(("PASS " if ok else "FAIL ") + f"{name}: got={got} want={want} {note}", flush=True)
    return ok


def one(spark, sql: str):
    """First column of the first row of a query (placeholders are filled from BASE)."""
    return spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), sql)).first()[0]


def jvm_peak_rss_mb():
    """Peak resident memory (VmHWM) of the Spark driver JVM: the java process below this Python process."""
    out = subprocess.run(["ps", "-eo", "pid,ppid,comm"], capture_output=True, text=True).stdout.splitlines()[1:]
    rows = [ln.split(None, 2) for ln in out]
    kids, todo = set(), [str(os.getpid())]
    while todo:
        cur = todo.pop()
        for pid, ppid, _ in rows:
            if ppid == cur and pid not in kids:
                kids.add(pid)
                todo.append(pid)
    best = None
    for pid, _, comm in rows:
        if pid in kids and comm.strip().startswith("java"):
            for ln in open(f"/proc/{pid}/status"):
                if ln.startswith("VmHWM"):
                    best = max(best or 0, int(ln.split()[1]) / 1024)
    return None if best is None else round(best, 1)


def dim_page_run(spark, label: str, as_of: str) -> dict:
    view_step(spark, "21_page_versions_view.sql", as_of=as_of)
    view_step(spark, "22_page_changes_view.sql")
    return write_step(spark, label, "23_dim_page_merge.sql", "dim_page", as_of=as_of)


def dim_page_classic_run(spark, label: str, as_of: str) -> dict:
    view_step(spark, "21_page_versions_view.sql", as_of=as_of)
    view_step(spark, "24_page_classic_changed_view.sql")
    return write_step(spark, label, "25_dim_page_classic_merge.sql", "dim_page_classic", as_of=as_of)


FACT_JOIN_SQL = """
WITH r AS (
  SELECT wiki_db, rev_id, page_id, ts, page_title_historical AS title_at_edit FROM delta.`{silver}/history_revisions`
  UNION ALL
  SELECT wiki_db, rev_id, page_id, ts, page_title AS title_at_edit FROM delta.`{silver}/live_revisions`
),
j AS (
  SELECT r.rev_id, count(p.page_key) AS n_match, max(p.page_key) AS page_key,
         max(p.title) AS title, max(r.title_at_edit) AS title_at_edit
  FROM r LEFT JOIN delta.`{gold}/%s` p
    ON p.wiki_db = r.wiki_db AND p.page_id = r.page_id AND r.ts >= p.valid_from AND (p.valid_to IS NULL OR r.ts < p.valid_to)
  GROUP BY r.rev_id
)
SELECT count(*) AS facts, count_if(j.n_match = 1) AS exactly_one, count_if(j.n_match = 0) AS no_version,
       count_if(j.n_match > 1) AS many_versions, count_if(NOT (j.title <=> j.title_at_edit)) AS title_differs,
       count_if(j.page_key <=> f.page_key) AS same_key_as_fact_edit
FROM j JOIN delta.`{gold}/fact_edit` f ON f.rev_id = j.rev_id
"""


def main() -> None:
    t_all = time.time()
    planted = json.load(open(os.path.join(LAB, "planted.json")))
    spark = get_spark()
    info = {"spark": spark.version, "python": sys.version.split()[0], "delta": None,
            "session_timezone": spark.conf.get("spark.sql.session.timeZone"), "master": spark.sparkContext.master,
            "driver_memory": spark.conf.get("spark.driver.memory"), "start_seconds": round(time.time() - t_all, 1)}
    try:
        from importlib.metadata import version
        info["delta"] = version("delta-spark")
        info["pyspark"] = version("pyspark")
    except Exception as e:
        info["delta"] = f"unknown ({e})"
    print("INFO", json.dumps(info), flush=True)

    # ---- 0. DDL: CREATE TABLE IF NOT EXISTS, path-based ------------------------------------------------
    for t in TABLES:
        ddl = "dim_page" if t.startswith("dim_page") else t
        write_step(spark, f"ddl {t}", f"ddl/{ddl}.sql", t, params={"dim_page": t}, step=f"ddl:{t}")

    # ---- 1. dim_cohort ---------------------------------------------------------------------------------
    r = write_step(spark, "dim_cohort", "10_dim_cohort_merge.sql", "dim_cohort", params=COHORT_ARGS)
    check("dim_cohort written", r["error"], None)
    r = write_step(spark, "dim_cohort re-run", "10_dim_cohort_merge.sql", "dim_cohort", params=COHORT_ARGS)
    check("dim_cohort re-run writes no commit", r["wrote_commit"], False)
    check("dim_cohort rows", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_cohort`"), 2)

    # ---- 2. first run, as_of 1 ---------------------------------------------------------------------------
    view_step(spark, "20_page_obs_view.sql")
    r1 = dim_page_run(spark, "dim_page run 1", A1)
    n1 = one(spark, "SELECT count(*) FROM delta.`{gold}/dim_page`")
    check("dim_page run 1: distinct pages", one(spark, "SELECT count(DISTINCT page_id) FROM delta.`{gold}/dim_page`"),
          planted["sizes"]["pages_total"] - planted["sizes"]["pages_first_seen_after_as_of_1"])
    check("dim_page run 1: pages without exactly one current row",
          one(spark, "SELECT count(*) FROM (SELECT page_id, count_if(is_current) AS c FROM delta.`{gold}/dim_page` GROUP BY wiki_db, page_id) WHERE c <> 1"), 0)
    dim_page_classic_run(spark, "dim_page_classic run 1", A1)
    ru1 = write_step(spark, "dim_user run 1 (history rows only)", "13_dim_user_merge.sql", "dim_user", as_of=AU1)
    check("dim_user run 1 inserted", int(ru1["metrics"]["numTargetRowsInserted"]), planted["dim_user"]["rows_run_1"])
    write_step(spark, "dim_time run 1", "12_dim_time_merge.sql", "dim_time", as_of=A1)
    rf1 = write_step(spark, "fact_edit run 1", "30_fact_edit_merge.sql", "fact_edit", as_of=A1)
    check("fact_edit run 1 inserted", int(rf1["metrics"]["numTargetRowsInserted"]), planted["fact_edit"]["rows"])
    check("fact_edit live_revert_flag true after run 1",
          one(spark, "SELECT count_if(live_revert_flag) FROM delta.`{gold}/fact_edit`"), planted["fact_edit"]["live_flag_true_at_as_of_1"])

    # ---- 3. second run, as_of 2 --------------------------------------------------------------------------
    r2 = dim_page_run(spark, "dim_page run 2", A2)
    n2 = one(spark, "SELECT count(*) FROM delta.`{gold}/dim_page`")
    check("dim_page run 2 closed some rows and inserted new versions",
          int(r2["metrics"]["numTargetRowsUpdated"]) > 0 and int(r2["metrics"]["numTargetRowsInserted"]) > 0, True,
          f"updated={r2['metrics']['numTargetRowsUpdated']} inserted={r2['metrics']['numTargetRowsInserted']} rows {n1} -> {n2}")
    r3 = dim_page_run(spark, "dim_page run 3 (same as_of)", A2)
    check("dim_page run 3 with the same as_of writes no commit", r3["wrote_commit"], False,
          f"version stays {r3['version_after']}")
    # classic form: first the 'all versions' demo (expected to fail), then the one-row-per-page run
    view_step(spark, "21_page_versions_view.sql", as_of=A2)
    rdemo = write_step(spark, "dim_page_classic all-versions demo (expected to fail)",
                       "26_dim_page_classic_all_versions_merge.sql", "dim_page_classic", as_of=A2)
    check("classic MERGE fed with several versions per page fails", rdemo["error"] is not None and not rdemo["wrote_commit"], True,
          (rdemo["error"] or "")[:160])
    dim_page_classic_run(spark, "dim_page_classic run 2", A2)
    rc3 = dim_page_classic_run(spark, "dim_page_classic run 3 (same as_of)", A2)
    check("dim_page_classic run 3 writes no commit", rc3["wrote_commit"], False)

    ru2 = write_step(spark, "dim_user run 2", "13_dim_user_merge.sql", "dim_user", as_of=A2)
    check("dim_user run 2 updated", int(ru2["metrics"]["numTargetRowsUpdated"]), planted["dim_user"]["updated_by_run_2"])
    check("dim_user run 2 inserted", int(ru2["metrics"]["numTargetRowsInserted"]), planted["dim_user"]["inserted_by_run_2"])
    r = write_step(spark, "dim_user re-run", "13_dim_user_merge.sql", "dim_user", as_of=A2)
    check("dim_user re-run writes no commit", r["wrote_commit"], False)
    r = write_step(spark, "dim_time run 2", "12_dim_time_merge.sql", "dim_time", as_of=A2)
    check("dim_time run 2 (no new minute) writes no commit", r["wrote_commit"], False)
    rf2 = write_step(spark, "fact_edit run 2", "30_fact_edit_merge.sql", "fact_edit", as_of=A2)
    check("fact_edit run 2 updated", int(rf2["metrics"]["numTargetRowsUpdated"]), planted["fact_edit"]["rows_updated_by_run_2"])
    check("fact_edit run 2 inserted", int(rf2["metrics"]["numTargetRowsInserted"]), 0)
    r = write_step(spark, "fact_edit re-run", "30_fact_edit_merge.sql", "fact_edit", as_of=A2)
    check("fact_edit re-run writes no commit", r["wrote_commit"], False)

    # ---- 4. label fact: two snapshots ---------------------------------------------------------------------
    rl = {}
    for snap in ("2026-09", "2026-10"):
        write_step(spark, f"dim_snapshot {snap}", "11_dim_snapshot_merge.sql", "dim_snapshot", snapshot=snap)
        rl[snap] = write_step(spark, f"fact_revert_label {snap}", "40_fact_revert_label_merge.sql", "fact_revert_label", snapshot=snap)
    fl = planted["fact_revert_label"]
    check("fact_revert_label 2026-09 inserted", int(rl["2026-09"]["metrics"]["numTargetRowsInserted"]), fl["rows_after_2026-09"])
    check("fact_revert_label 2026-10 is ONE commit", rl["2026-10"]["version_after"] - rl["2026-10"]["version_before"], 1)
    check("fact_revert_label 2026-10 updated", int(rl["2026-10"]["metrics"]["numTargetRowsUpdated"]), fl["updated_by_2026-10"])
    check("fact_revert_label 2026-10 inserted", int(rl["2026-10"]["metrics"]["numTargetRowsInserted"]), fl["inserted_by_2026-10"])
    r = write_step(spark, "fact_revert_label 2026-10 re-run", "40_fact_revert_label_merge.sql", "fact_revert_label", snapshot="2026-10")
    check("fact_revert_label re-run of 2026-10 writes no commit", r["wrote_commit"], False)
    r = write_step(spark, "fact_revert_label 2026-09 re-run after 2026-10", "40_fact_revert_label_merge.sql", "fact_revert_label", snapshot="2026-09")
    check("fact_revert_label re-run of the OLDER snapshot 2026-09 writes no commit", r["wrote_commit"], False)
    r = write_step(spark, "dim_snapshot 2026-10 re-run", "11_dim_snapshot_merge.sql", "dim_snapshot", snapshot="2026-10")
    check("dim_snapshot re-run writes no commit", r["wrote_commit"], False)

    # versions through commit user metadata
    label_path = f"{GOLD}/fact_revert_label"
    v09 = find_version(spark, label_path, step="fact_revert_label", snapshot="2026-09")
    v10 = find_version(spark, label_path, step="fact_revert_label", snapshot="2026-10")
    check("versions found by userMetadata", [v09, v10], [rl["2026-09"]["version_after"], rl["2026-10"]["version_after"]])
    sql_only = None
    try:
        sql_only = spark.sql(
            f"SELECT max(version) FROM (DESCRIBE HISTORY delta.`{label_path}`) "
            "WHERE get_json_object(userMetadata, '$.step') = 'fact_revert_label' "
            "AND get_json_object(userMetadata, '$.snapshot') = '2026-09'").first()[0]
    except Exception as e:
        sql_only = f"{type(e).__name__}: {str(e)[:300]}"
    check("probe: SELECT ... FROM (DESCRIBE HISTORY ...) is NOT supported (ParseException), so the lookup stays in Python",
          str(sql_only).startswith("ParseException"), True, str(sql_only)[:120].replace("\n", " "))

    # Change Data Feed between the two versions, two ways, by path
    cdf_sql = {r["_change_type"]: r["n"] for r in spark.sql(
        f"SELECT _change_type, count(*) AS n FROM table_changes_by_path('{label_path}', {v09 + 1}, {v10}) GROUP BY _change_type").collect()}
    cdf_opt = {r["_change_type"]: r["count"] for r in (
        spark.read.format("delta").option("readChangeFeed", "true").option("startingVersion", v09 + 1)
        .option("endingVersion", v10).load(label_path).groupBy("_change_type").count().collect())}
    want_cdf = {"insert": fl["inserted_by_2026-10"], "update_postimage": 700, "update_preimage": 700}
    check("CDF table_changes_by_path between the two label versions", dict(sorted(cdf_sql.items())), want_cdf)
    check("CDF readChangeFeed option by path", dict(sorted(cdf_opt.items())), want_cdf)

    # ---- 5. mart_label_change from the change feed ---------------------------------------------------------
    def label_change_run(label: str, start=None):
        last = one(spark, "SELECT coalesce(max(commit_version), 0) FROM delta.`{gold}/mart_label_change`")
        start_v = last + 1 if start is None else start
        end_v = table_version(spark, label_path)
        if start_v > end_v:
            print(f"SKIP {label}: change feed already read up to version {last}", flush=True)
            return None
        return write_step(spark, label, "50_mart_label_change_merge.sql", "mart_label_change",
                          params={"start_version": start_v, "end_version": end_v})

    rm = label_change_run("mart_label_change")
    check("mart_label_change inserted", int(rm["metrics"]["numTargetRowsInserted"]), 700)
    check("mart_label_change second run is skipped (nothing new in the feed)", label_change_run("mart_label_change re-run"), None)
    r = label_change_run("mart_label_change forced re-read from version 1", start=1)
    check("mart_label_change forced re-read writes no commit", r["wrote_commit"], False)
    got = {r["change_class"]: r["n"] for r in spark.sql(
        f"SELECT change_class, count(*) AS n FROM delta.`{GOLD}/mart_label_change` GROUP BY change_class").collect()}
    lc = planted["label_changes"]
    check("mart_label_change classes", dict(sorted(got.items())),
          {"became_reverted": lc["became_reverted"], "became_unreverted": lc["became_unreverted"],
           "reverter_or_time_changed": lc["reverter_or_time_changed"]})
    check("mart_label_change from/to snapshot", [tuple(r) for r in spark.sql(
        f"SELECT DISTINCT from_snapshot, to_snapshot, commit_version FROM delta.`{GOLD}/mart_label_change`").collect()],
        [("2026-09", "2026-10", v10)])

    # ---- 6. time travel: as known then against now ---------------------------------------------------------
    tt = [r.asDict() for r in run_sql(spark, "80_time_travel_then_and_now.sql", {"v_2026_09": v09, "v_2026_10": v10})]
    print("TIME TRAVEL", json.dumps(tt), flush=True)
    check("time travel: history-cohort reverted, then and now",
          [(r["snapshot"], r["label_version"], r["reverted_as_known_then"], r["reverted_now"]) for r in tt],
          [("2026-09", v09, fl["history_cohort_reverted_any_as_of_2026-09"], fl["history_cohort_reverted_any_as_of_2026-10"]),
           ("2026-10", v10, fl["history_cohort_reverted_any_as_of_2026-10"], fl["history_cohort_reverted_any_as_of_2026-10"])])
    check("VERSION AS OF reads the 2026-09 load", one(spark, f"SELECT count(*) FROM delta.`{label_path}` VERSION AS OF {v09} WHERE last_changed_snapshot = '2026-09'"),
          fl["rows_after_2026-09"])

    # ---- 7. marts ------------------------------------------------------------------------------------------
    r = write_step(spark, "mart_el_curve", "60_mart_el_curve_overwrite.sql", "mart_el_curve", as_of=A2, snapshot="2026-10")
    check("mart_el_curve written", r["error"], None)
    rp = {"cohort_id": "live", "label_version": v10}
    view_step(spark, "69_recon_view.sql", snapshot="2026-10", **rp)
    r = write_step(spark, "mart_reconciliation", "70_mart_reconciliation_replace.sql", "mart_reconciliation", snapshot="2026-10", params=rp)
    check("mart_reconciliation written (INSERT INTO ... REPLACE WHERE)", r["error"], None)
    r = write_step(spark, "recon_mismatch", "71_recon_mismatch_replace.sql", "recon_mismatch", snapshot="2026-10", params=rp)
    check("recon_mismatch written (INSERT INTO ... REPLACE WHERE)", r["error"], None)
    rec = planted["reconciliation_live_vs_2026-10"]
    got = {r["recon_class"]: r["n_revisions"] for r in spark.sql(f"SELECT recon_class, n_revisions FROM delta.`{GOLD}/mart_reconciliation`").collect()}
    check("mart_reconciliation class counts", dict(sorted(got.items())),
          {k: rec[k] for k in sorted(["both_reverted", "dump_only", "neither", "not_in_dump", "stream_only"])})
    got = {r["recon_class"]: r["n"] for r in spark.sql(f"SELECT recon_class, count(*) AS n FROM delta.`{GOLD}/recon_mismatch` GROUP BY recon_class").collect()}
    check("recon_mismatch rows per class", dict(sorted(got.items())), {"dump_only": rec["dump_only"], "not_in_dump": rec["not_in_dump"], "stream_only": rec["stream_only"]})

    # ---- 8. checks on the finished tables ------------------------------------------------------------------
    view_step(spark, "21_page_versions_view.sql", as_of=A2)
    check("dim_page: distinct pages", one(spark, "SELECT count(DISTINCT page_id) FROM delta.`{gold}/dim_page`"), planted["sizes"]["pages_total"])
    check("dim_page: pages without exactly one current row",
          one(spark, "SELECT count(*) FROM (SELECT page_id, count_if(is_current) AS c FROM delta.`{gold}/dim_page` GROUP BY wiki_db, page_id) WHERE c <> 1"), 0)
    check("dim_page: gaps or overlaps (valid_to <> next valid_from)",
          one(spark, "SELECT count(*) FROM (SELECT valid_to, lead(valid_from) OVER (PARTITION BY wiki_db, page_id ORDER BY valid_from) AS nf "
                     "FROM delta.`{gold}/dim_page`) WHERE NOT (valid_to <=> nf)"), 0)
    check("dim_page: empty or negative intervals", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_page` WHERE valid_to <= valid_from"), 0)
    check("dim_page: pages whose first version does not start at the sentinel",
          one(spark, "SELECT count(*) FROM (SELECT min(valid_from) AS m FROM delta.`{gold}/dim_page` GROUP BY wiki_db, page_id) WHERE m <> TIMESTAMP '1900-01-01 00:00:00'"), 0)
    check("dim_page: is_current <> (valid_to IS NULL)", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_page` WHERE is_current <> (valid_to IS NULL)"), 0)
    check("dim_page: duplicate page_key", one(spark, "SELECT count(*) - count(DISTINCT page_key) FROM delta.`{gold}/dim_page`"), 0)
    check("dim_page: rows that differ from the computed version list (both directions)",
          one(spark, "SELECT (SELECT count(*) FROM (SELECT * FROM delta.`{gold}/dim_page` EXCEPT SELECT * FROM v_page_versions)) + "
                     "(SELECT count(*) FROM (SELECT * FROM v_page_versions EXCEPT SELECT * FROM delta.`{gold}/dim_page`))"), 0)
    fj = spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), FACT_JOIN_SQL % "dim_page")).first().asDict()
    check("fact_edit as-of join to dim_page", fj, {"facts": 80000, "exactly_one": 80000, "no_version": 0, "many_versions": 0,
                                                    "title_differs": 0, "same_key_as_fact_edit": 80000})
    fjc = spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), FACT_JOIN_SQL % "dim_page_classic")).first().asDict()
    print("CLASSIC FACT JOIN", json.dumps(fjc), flush=True)
    cmp_sql = ("SELECT (SELECT count(*) FROM delta.`{gold}/dim_page`) AS rows_method_1, (SELECT count(*) FROM delta.`{gold}/dim_page_classic`) AS rows_classic, "
               "(SELECT count(*) FROM (SELECT * FROM delta.`{gold}/dim_page` EXCEPT SELECT * FROM delta.`{gold}/dim_page_classic`)) AS only_in_method_1, "
               "(SELECT count(*) FROM (SELECT * FROM delta.`{gold}/dim_page_classic` EXCEPT SELECT * FROM delta.`{gold}/dim_page`)) AS only_in_classic, "
               "(SELECT count(DISTINCT page_id) FROM (SELECT * FROM delta.`{gold}/dim_page` EXCEPT SELECT * FROM delta.`{gold}/dim_page_classic`)) AS pages_that_differ, "
               "(SELECT count(*) FROM (SELECT page_id FROM delta.`{gold}/dim_page_classic` GROUP BY page_id HAVING count_if(is_current) <> 1)) AS classic_pages_not_one_current")
    scd_cmp = spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), cmp_sql)).first().asDict()
    print("SCD2 COMPARISON", json.dumps(scd_cmp), flush=True)
    # which pages differ: pages with 2 or more new versions inside one run
    multi = spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), f"""
        SELECT count_if(v_run1 >= 2) AS pages_2plus_versions_in_run_1, count_if(v_run2 >= 2) AS pages_2plus_new_versions_in_run_2,
               count_if(v_run1 >= 2 OR v_run2 >= 2) AS pages_2plus_in_any_run
        FROM (SELECT page_id, count_if(valid_from <= TIMESTAMP '{A1}') AS v_run1, count_if(valid_from > TIMESTAMP '{A1}') AS v_run2
              FROM delta.`{{gold}}/dim_page` GROUP BY page_id)""")).first().asDict()
    print("SCD2 MULTI-CHANGE PAGES", json.dumps(multi), flush=True)
    check("SCD2: pages that differ between the methods = pages with 2+ new versions in one run",
          scd_cmp["pages_that_differ"], multi["pages_2plus_in_any_run"])

    check("dim_user rows", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_user`"), planted["dim_user"]["rows_run_2"])
    check("dim_user: duplicate user_key", one(spark, "SELECT count(*) - count(DISTINCT user_key) FROM delta.`{gold}/dim_user`"), 0)
    check("fact_edit rows without a dim_user row", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` f LEFT ANTI JOIN delta.`{gold}/dim_user` u ON u.user_key = f.user_key"), 0)
    check("fact_edit rows with user_key 'unknown'", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` WHERE user_key = 'unknown'"), planted["fact_edit"]["user_key_unknown_rows"])
    check("dim_time rows", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_time`"), planted["dim_time"]["rows"])
    check("fact_edit rows without a dim_time row", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` f LEFT ANTI JOIN delta.`{gold}/dim_time` d ON d.time_key = f.time_key"), 0)
    check("dim_time rows not used by fact_edit", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_time` d LEFT ANTI JOIN delta.`{gold}/fact_edit` f ON d.time_key = f.time_key"), 0)
    check("dim_time: minute_start matches time_key, Monday = 1",
          one(spark, "SELECT count(*) FROM delta.`{gold}/dim_time` WHERE time_key <> CAST(date_format(minute_start, 'yyyyMMddHHmm') AS BIGINT) "
                     "OR hour <> hour(minute_start) OR date <> CAST(minute_start AS DATE) OR day_of_week <> dayofweek(minute_start - INTERVAL 1 DAY)"), 0)
    check("fact_edit rows", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit`"), planted["fact_edit"]["rows"])
    check("fact_edit: duplicate (wiki_db, rev_id)", one(spark, "SELECT count(*) - count(DISTINCT wiki_db, rev_id) FROM delta.`{gold}/fact_edit`"), 0)
    check("fact_edit rows per cohort", {r[0]: r[1] for r in spark.sql(f"SELECT cohort_id, count(*) FROM delta.`{GOLD}/fact_edit` GROUP BY cohort_id ORDER BY 1").collect()},
          {"history": 40000, "live": 40000})
    check("fact_edit live_revert_flag true after run 2", one(spark, "SELECT count_if(live_revert_flag) FROM delta.`{gold}/fact_edit`"), planted["fact_edit"]["live_flag_true_at_as_of_2"])
    check("fact_edit history rows have a NULL live flag", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` WHERE cohort_id = 'history' AND live_revert_flag IS NOT NULL"), 0)
    check("fact_edit rows whose page_key is not in dim_page", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` f LEFT ANTI JOIN delta.`{gold}/dim_page` p ON p.page_key = f.page_key"), 0)
    fe_path = f"{GOLD}/fact_edit"
    cdf_fe = {r["_change_type"]: r["n"] for r in spark.sql(
        f"SELECT _change_type, count(*) AS n FROM table_changes_by_path('{fe_path}', {rf2['version_after']}, {rf2['version_after']}) GROUP BY _change_type").collect()}
    check("fact_edit CDF of run 2", dict(sorted(cdf_fe.items())), {"update_postimage": planted["fact_edit"]["rows_updated_by_run_2"], "update_preimage": planted["fact_edit"]["rows_updated_by_run_2"]})
    check("fact_revert_label rows", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label`"), fl["rows_after_2026-10"])
    check("fact_revert_label: duplicate (wiki_db, rev_id)", one(spark, "SELECT count(*) - count(DISTINCT wiki_db, rev_id) FROM delta.`{gold}/fact_revert_label`"), 0)
    check("fact_revert_label: reverted rows without label_dt, or not reverted rows with one",
          one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label` WHERE is_identity_reverted <> (label_dt IS NOT NULL)"), 0)
    check("fact_revert_label: first_reverted_snapshot kept for rows that became unreverted",
          one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label` WHERE NOT is_identity_reverted AND first_reverted_snapshot = '2026-09'"), lc["became_unreverted"])
    check("fact_revert_label: September revisions first reverted in 2026-10",
          one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label` f JOIN delta.`{silver}/history_slim` s ON s.snapshot = '2026-09' AND s.revision_id = f.rev_id "
                     "WHERE f.first_reverted_snapshot = '2026-10'"), lc["became_reverted"])
    check("fact_revert_label: rows of the 2026-09 load with last_changed_snapshot 2026-10",
          one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label` f JOIN delta.`{silver}/history_slim` s ON s.snapshot = '2026-09' AND s.revision_id = f.rev_id "
                     "WHERE f.last_changed_snapshot = '2026-10'"), 700)
    check("dim_snapshot rows", [tuple(r) for r in spark.sql(f"SELECT snapshot, revision_rows FROM delta.`{GOLD}/dim_snapshot` ORDER BY snapshot").collect()],
          [("2026-09", 150000), ("2026-10", 300000)])
    check("mart_el_curve rows (3 series x 5 user kinds x 9 waits)", one(spark, "SELECT count(*) FROM delta.`{gold}/mart_el_curve`"), 135)
    check("commits without the JSON user metadata, all Gold tables", sum(
        sum(1 for h in spark.sql(f"DESCRIBE HISTORY delta.`{GOLD}/{t}`").collect() if not (h["userMetadata"] or "").startswith("{"))
        for t in TABLES), 0)
    check("user metadata conf is unset after the run", spark.conf.get(UM, None) in (None, ""), True)
    r = write_step(spark, "dim_page with an OLDER as_of (must be refused)", "23_dim_page_merge.sql", "dim_page", as_of=A1)
    check("a run with an older as_of is refused and writes no commit", (r["error"] or "").startswith("RuntimeError: refused") and not r["wrote_commit"], True,
          (r["error"] or "")[:140])

    # ---- 9. protocol, counts, memory ------------------------------------------------------------------------
    protocol, counts = {}, {}
    for t in TABLES:
        d = spark.sql(f"DESCRIBE DETAIL delta.`{GOLD}/{t}`").first().asDict()
        protocol[t] = {"minReaderVersion": d["minReaderVersion"], "minWriterVersion": d["minWriterVersion"],
                       "tableFeatures": sorted(d["tableFeatures"] or []), "properties": dict(d["properties"] or {}),
                       "numFiles": d["numFiles"], "sizeInBytes": d["sizeInBytes"], "partitionColumns": d["partitionColumns"],
                       "clusteringColumns": d.get("clusteringColumns"), "version": table_version(spark, f"{GOLD}/{t}")}
        counts[t] = spark.sql(f"SELECT count(*) FROM delta.`{GOLD}/{t}`").first()[0]
        print("PROTOCOL", t, json.dumps(protocol[t]), flush=True)
    # small samples for the report
    for title, q in [
        ("EL CURVE (user_kind = all)", "SELECT * FROM delta.`{gold}/mart_el_curve` WHERE user_kind = 'all' ORDER BY cohort_id, label_source, wait_s"),
        ("EL CURVE (small groups, 1 h)", "SELECT * FROM delta.`{gold}/mart_el_curve` WHERE wait_s = 3600 ORDER BY cohort_id, label_source, user_kind"),
        ("RECONCILIATION", "SELECT * FROM delta.`{gold}/mart_reconciliation` ORDER BY n_revisions DESC"),
        ("RECON MISMATCH sample", "SELECT * FROM delta.`{gold}/recon_mismatch` ORDER BY recon_class, rev_id LIMIT 6"),
        ("DIM_PAGE sample (page with most versions)", "SELECT * FROM delta.`{gold}/dim_page` WHERE page_id = (SELECT page_id FROM delta.`{gold}/dim_page` GROUP BY page_id ORDER BY count(*) DESC, page_id LIMIT 1) ORDER BY valid_from"),
        ("DIM_PAGE versions per page", "SELECT n_versions, count(*) AS pages FROM (SELECT page_id, count(*) AS n_versions FROM delta.`{gold}/dim_page` GROUP BY page_id) GROUP BY n_versions ORDER BY n_versions"),
        ("DIM_PAGE current rows", "SELECT is_deleted, namespace, count(*) AS n FROM delta.`{gold}/dim_page` WHERE is_current GROUP BY is_deleted, namespace ORDER BY 1, 2"),
        ("LABEL CHANGE sample", "SELECT * FROM delta.`{gold}/mart_label_change` ORDER BY change_class, rev_id LIMIT 5"),
        ("DIM tables", "SELECT * FROM delta.`{gold}/dim_cohort` ORDER BY cohort_id"),
        ("DIM snapshot", "SELECT * FROM delta.`{gold}/dim_snapshot` ORDER BY snapshot"),
    ]:
        print(f"\n--- {title}", flush=True)
        spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), q)).show(60, truncate=False)
    peak = jvm_peak_rss_mb()
    rt = spark._jvm.java.lang.Runtime.getRuntime()
    mem = {"jvm_peak_rss_mb": peak, "jvm_heap_max_mb": round(rt.maxMemory() / 2**20), "jvm_heap_total_mb": round(rt.totalMemory() / 2**20)}
    result = {"info": info, "steps": STEPS, "checks": CHECKS, "protocol": protocol, "counts": counts, "memory": mem,
              "time_travel": tt, "scd2_comparison": scd_cmp, "scd2_multi_change": multi, "classic_fact_join": fjc,
              "fact_join": fj, "versions": {"fact_revert_label_2026-09": v09, "fact_revert_label_2026-10": v10},
              "total_seconds": round(time.time() - t_all, 1)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "run_gold.json"), "w") as f:
        json.dump(result, f, indent=1, default=str)
    n_fail = sum(1 for c in CHECKS if not c["ok"])
    print(f"\nMEMORY {json.dumps(mem)}")
    print(f"CHECKS {len(CHECKS) - n_fail} passed, {n_fail} failed; total {result['total_seconds']} s", flush=True)
    spark.stop()


if __name__ == "__main__":
    main()
```

The independent pandas checker `verify_gold.py` (E(L), a plain Python loop for the dim_page versions, reconciliation classes, both facts, dim_user, and the delta-rs read of every Gold table) is in the zip; it is not needed to build Gold.

## Results

All numbers RAN in the final rebuild (`out/run_gold_3.log`, `out/run_gold.json`: 78 passed, 0 failed) and in `verify_gold.py` (`out/verify_gold_2.log`: 18 passed, 0 failed). An earlier full rebuild (`out/run_gold_2.log`) gave the same value for all 76 checks the two runs share.

| Table | Rows | Checks (seen = planted unless said) |
|---|---|---|
| dim_cohort | 2 | re-run: no commit |
| dim_snapshot | 2 (150,000 and 300,000 revision_rows) | re-run: no commit |
| dim_time | 8,640 = planted | run 2 (no new minute): no commit; 0 fact rows without a minute; 0 unused minutes; 0 rows where hour / date / Monday = 1 are wrong |
| dim_user | 369 after run 1, 399 after run 2 | run 2: updated 18, inserted 30 (planted 18 and 30); re-run: no commit; 399 of 399 rows equal to pandas |
| dim_page | 2,315 after run 1 (2,120 pages), 2,496 after run 2 (2,145 pages) | see below |
| fact_edit | 80,000 (40,000 per cohort) | run 1 inserted 80,000, live flag true 2,641; run 2 updated 291, inserted 0, copied 39,709, flag true 2,932; change feed of run 2: 291 update_preimage + 291 update_postimage; re-run: no commit; 0 duplicate keys; 80,000 of 80,000 rows equal to pandas in every column |
| fact_revert_label | 150,000 after 2026-09, 300,000 after 2026-10 | see below |
| mart_label_change | 700 | became_reverted 600, became_unreverted 60, reverter_or_time_changed 40; from 2026-09 to 2026-10, commit_version 2 |
| mart_el_curve | 135 | 135 of 135 rows equal to pandas |
| mart_reconciliation | 5 | both_reverted 2,804, stream_only 120, dump_only 80, neither 36,946, not_in_dump 50; shares sum to 1.0 |
| recon_mismatch | 250 | stream_only 120, dump_only 80, not_in_dump 50; same (rev_id, class) rows as pandas; times and dump values equal to Silver |

**dim_page (SCD2, method 1).**
- Run 1 (as_of 2026-10-23 00:00:00): 2,315 rows inserted, one current row per page.
- Run 2 (as_of 2026-10-27 21:00:00): `numTargetRowsUpdated` 120, `numTargetRowsInserted` 181, `numTargetRowsCopied` 2,195, source rows 301. The 120 equals the planted pages with a change after as_of 1 (50 + 20 + 10 + 10 + 12 + 8 + 6 + 4). The 181 equals 156 new versions of those pages plus 25 new pages.
- Run 3 (same as_of): no commit, version stays 2 (3.3 s).
- 0 pages without exactly one current row; 0 gaps or overlaps (`valid_to <=> next valid_from`); 0 empty intervals; every page's first version starts at 1900-01-01; 0 duplicate page_key; the table equals the computed list in both directions (EXCEPT = 0).
- Independent Python loop over the observations: 2,496 of 2,496 rows equal in every column; versions per page {1: 1,866, 2: 211, 3: 64, 4: 4}.
- Fact join with `event_dt >= valid_from AND (valid_to IS NULL OR event_dt < valid_to)`: 80,000 facts, 80,000 with exactly one version, 0 with none, 0 with several, 0 where the version's title differs from the title at edit time, 80,000 equal to the stored `fact_edit.page_key`.
- Current rows: 2,018 in namespace 0, 40 in 1, 30 in 4, 40 in 118, and 17 deleted.

**fact_revert_label.**
- 2026-09: version 0 -> 1, 150,000 inserted. 2026-10: ONE commit, version 1 -> 2, `numTargetRowsUpdated` 700, `numTargetRowsInserted` 150,000, copied 149,300, source rows 150,700.
- Change feed between version 2 and 2 (start = version of 2026-09 + 1): `table_changes_by_path` and the `readChangeFeed` option both give insert 150,000, update_preimage 700, update_postimage 700.
- Re-run of 2026-10: no commit. Re-run of the older 2026-09 after 2026-10: no commit.
- 300,000 of 300,000 rows equal to pandas (labels of snapshot 2026-10, label_dt = event time + seconds, first_reverted_snapshot, last_changed_snapshot). 60 rows that became unreverted keep first_reverted_snapshot 2026-09; 600 September revisions have first_reverted_snapshot 2026-10.

**Time travel.** Versions found in DESCRIBE HISTORY by userMetadata: 1 (snapshot 2026-09) and 2 (2026-10). The one query (`80_time_travel_then_and_now.sql`) returned:

| snapshot | label_version | reverted_as_known_then | reverted_now |
|---|---|---|---|
| 2026-09 | 1 | 4,051 | 4,231 |
| 2026-10 | 2 | 4,231 | 4,231 |

Planted: 4,051 then, 4,051 + 200 - 20 = 4,231 now.

**mart_el_curve, user_kind = 'all'** (n_known at each wait; pandas gives the same integers):

| series | n_eventual | 0 | 1 min | 5 min | 15 min | 1 h | 6 h | 1 d | 2 d | 4 d | e_l at 1 h |
|---|---|---|---|---|---|---|---|---|---|---|---|
| live / stream | 2,932 | 4 | 881 | 1,294 | 1,517 | 1,852 | 2,270 | 2,587 | 2,769 | 2,920 | 0.3683 |
| history / dump | 3,563 | 5 | 1,134 | 1,564 | 1,892 | 2,295 | 2,746 | 3,146 | 3,374 | 3,563 | 0.3559 |
| live / dump | 2,884 | 13 | 897 | 1,288 | 1,503 | 1,821 | 2,221 | 2,535 | 2,713 | 2,884 | 0.3686 |

Edge cases that the numbers confirm: live / stream at wait 0 is 4 (only T = 0 with K = 0; the 9 links with T = 0 and K > 0 are not known). Live / stream at 4 d is 2,920 of 2,932: the 12 missing are 3 (T = 345,599, K = 3.5), 4 (T = 345,600, K = 1.25) and 5 (T = 345,598, K = 3.5). T = 345,601 and T = -5 are not eventual. Live / dump n_eventual 2,884 = both_reverted 2,804 + dump_only 80. Small groups (n_eventual < 100): 'unknown' with 9, 3 and 9.

**Cross-engine.** delta-rs 1.6.6 read all 12 Gold tables into pandas and polars with the Spark row counts; string columns arrive as `string` (not `string_view`), also from files that a Spark MERGE rewrote.

## SCD2: two methods compared

Both ran for the same two steps (as_of 2026-10-23 00:00:00, then 2026-10-27 21:00:00), on `dim_page` (method 1) and `dim_page_classic` (classic staged source with a NULL merge key). The classic source is one row per page: its current version from the same `v_page_versions` view.

| | Method 1: full recompute + pre-filter + MERGE on page_key | Classic: one row per page, NULL merge key |
|---|---|---|
| Run 1 | inserted 2,315 | inserted 2,120 |
| Run 2 | updated 120, inserted 181 | updated 112, inserted 137 |
| Run 3, same as_of | no commit | no commit |
| Final rows | 2,496 | 2,257 |
| One current row per page | yes (0 violations) | yes (0 violations) |
| Fact rows with exactly one version | 80,000 of 80,000 | 75,790 of 80,000 (4,210 find no version) |

**Do both end with the same rows? No (RAN).** 271 rows are only in method 1, 32 rows are only in the classic table, and 207 pages differ. Those 207 pages are exactly the pages with two or more new versions inside one run: 175 in run 1 and 32 in run 2 (the check `pages_that_differ = pages_2plus_in_any_run` passed, 207 = 207). For every page with at most one new version per run the two tables hold identical rows, including page_key.

**The classic form's limit when a page changes more than once in one run.**
1. With one source row per page (the usual rule), only the last state reaches the table. The versions in between are lost, and the old current row is closed at the start of the LAST new version instead of the first. In run 2 this hit 32 pages (20 moved twice, 8 deleted and undeleted, 4 moved, deleted and undeleted). A page that went A -> B -> A inside one run shows no change at all.
2. The first load is the same case: the classic table only gets the state at as_of 1, so the 175 pages that already had two or more versions lose their earlier ones. Their first row starts at the current version's start, so 4,210 earlier fact rows join to nothing. Starting that row at the sentinel instead would make them join, but to the wrong title.
3. Feeding every new version instead (`26_dim_page_classic_all_versions_merge.sql`) fails, and nothing is written: `UnsupportedOperationException: [DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE] Cannot perform Merge as multiple source rows matched and attempted to modify the same target row in the Delta table in possibly conflicting ways. By SQL semantics of Merge, when multiple source rows match on the same target row, the result may be ambiguous as it is unclear which source row should be used to update or delete the ma...`

Method 1 has none of these limits because the version list is rebuilt from all observations each run and the MERGE key is the version (page_key), not the page. Its price: the window pass reads every observation each run (about 97,000 here), and its as_of must never go backwards (see Pitfalls).

## Pitfalls met

Every item RAN unless marked UNVERIFIED. Error texts are exact.

1. **Named parameters are not bound when the Delta SQL extension is on.** `spark.sql(text, args={...})` failed for the dim_cohort MERGE: `AnalysisException: [UNBOUND_SQL_PARAMETER] Found the unbound parameter: history_start. Please, fix `args` and provide a mapping of the parameter to either a SQL literal or collection constructor functions such as `map()`, `array()`, `struct()`. SQLSTATE: 42P02; line 7 pos 16;`. Probe (`probe_params.py`, `probe_params2.py`): the same error for a plain SELECT, INSERT ... SELECT, UPDATE, MERGE (parameter in ON / SET or in the USING subquery), positional `?` (`unbound parameter: _7`) and EXECUTE IMMEDIATE ... USING. In a session WITHOUT `io.delta.sql.DeltaSparkSessionExtension` both `:n` and `?` work. Fix that worked: build the session with `spark.sql.legacy.parameterSubstitution.constantsOnly=true`; then SELECT, `?` and a MERGE with a parameter in the USING subquery all ran (`num_updated_rows=1`). The main run uses `{placeholders}` with a value whitelist instead.
2. **No parameter markers in views:** `ParseException: [UNSUPPORTED_FEATURE.PARAMETER_MARKER_IN_UNEXPECTED_STATEMENT] The feature is not supported: Parameter markers are not allowed in the query of CREATE VIEW. SQLSTATE: 0A000`. SQL session variables are a working alternative: `DECLARE OR REPLACE VARIABLE v_as_of TIMESTAMP DEFAULT ...` worked in a SELECT, inside a MERGE source and in a temp view, and the view reads the variable when it is queried (count 2,340 before and 2,496 after `SET VAR`).
3. **`SELECT ... FROM (DESCRIBE HISTORY ...)` does not parse:** `ParseException: [PARSE_SYNTAX_ERROR] Syntax error at or near 'delta': missing ')'. SQLSTATE: 42601`. The version lookup by userMetadata therefore lives in Python (`find_version`): `spark.sql("DESCRIBE HISTORY ...").collect()` and `json.loads(userMetadata)`. `DESCRIBE HISTORY ... LIMIT 1` works.
4. **An older as_of is not a no-op.** The pre-filter at as_of 1 against the finished dim_page returns 120 rows, all with `valid_to` NULL: the MERGE would open 120 closed versions again and leave the 156 newer versions in place (two current rows per page; this consequence is derived, the MERGE itself was not run). At as_of 2 the pre-filter returns 0 rows. The same holds by construction for fact_edit (labels known after the older as_of would be removed; UNVERIFIED). Fix in the runner (RAN): `newest_as_of()` reads the newest committed as_of from the commit metadata and `write_step` refuses an older one: `RuntimeError: refused: as_of 2026-10-23 00:00:00 is older than the newest committed as_of 2026-10-27 21:00:00 of dim_page`. A no-op run writes no commit, so its as_of is not recorded.
5. **dim_user is Type 1, so it must not supply user_kind at edit time.** 424 history-cohort revisions (by the 5 editors who became bots) have another kind in dim_user than in Silver. `mart_el_curve` therefore joins the Silver revision tables. A plan that wants a pure Gold-to-Gold mart needs user_kind on fact_edit.
6. **`{name}` inside a SQL comment is also a placeholder for the runner:** `KeyError: '24_page_classic_changed_view.sql: no value for {as_of}'`. Fix: keep braces out of comments unless the file gets that value.
7. **Classic SCD2 with several versions per page fails** with `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` (full text in the SCD2 section).
8. **Delete and undelete events.** In the made-up data they carry the rev_id and rev_dt of the page's newest, older revision. With rev_dt as the observation time the deleted version would start at the last edit, so the view uses meta_dt for these two kinds. UNVERIFIED whether real page_change delete events look like this.
9. **Seconds in page_key.** `date_format(valid_from, 'yyyyMMddHHmmss')` would give two versions the same key if a page changed twice inside one second, and meta_dt has milliseconds. The view keeps one state per page and second (`max_by` over observed_dt, then rev_id). The 6 planted same-second edit pairs and the delete events with +250 ms went through; 0 duplicate page_key.
10. **Planted page categories are not visible versions.** 6 of the 40 pages moved between the cohorts have no September observation, so the move makes no version (run 1 has 195 extra versions, not 201). Verify SCD2 with an independent loop over the observations, not with planted counts.
11. **`operationMetrics.numSourceRows` can be wrong:** the dim_snapshot 2026-10 commit shows numSourceRows 0 with numTargetRowsInserted 1 (both rebuilds). Use the inserted / updated metrics for checks.
12. **Every MERGE costs seconds, even on 2 rows:** 3.1 to 10.8 s per statement here, and 1.8 to 6.3 s for a pre-filtered re-run that writes nothing. See Timings.
13. **`sh -c 'time ...'` failed:** `sh: 1: time: not found` (`time` is a bash keyword). The background rebuild did nothing until it was started with `bash -c`.
14. **Generator (pandas 2.3.3 with numpy 2.5.4), four errors and fixes.** `TypeError: can't compare offset-naive and offset-aware datetimes` (a tz-aware column's `to_numpy()` against `Timestamp.to_datetime64()`): compare the Series with the tz-aware Timestamp. `AttributeError: 'Index' object has no attribute 'total_seconds'` (DatetimeIndex minus an object array): wrap the right side in `pd.DatetimeIndex`. `TypeError: Invalid value '<null>' for dtype 'Int64'` (`fillna` with a string on an Int64 column): use `astype(str)`. `TypeError: keys must be str, int, float, bool or None, not tuple` (json.dump of a groupby size dict): build string keys. Also `DeprecationWarning: The 'generic' unit for NumPy timedelta is deprecated` on every `pd.Timedelta` arithmetic (silenced).
15. **The marts written with INSERT OVERWRITE and INSERT INTO ... REPLACE WHERE write a commit on every run.** Both forms worked on path-based tables. Their re-run on an existing table was not executed (UNVERIFIED); the two full rebuilds gave the same contents.
16. **`git status` touches `.git`.** After the required `git -C /home/user/truth-lag status --porcelain` (empty output), the only path under the repo newer than the start of this work is the `.git` folder itself. No file, `__pycache__`, `.pytest_cache`, `spark-warehouse`, `metastore_db` or `derby.log` appeared in the repo or in `/home/user/delta-io`.

## Timings and protocol

Timings are from the final rebuild (RAN). The machine was shared with other agents, so read them as indicative.

| Step | Seconds | Version | Commit | Inserted | Updated | Copied | Source rows |
|---|---|---|---|---|---|---|---|
| 12 x CREATE TABLE | 5.6 total | - -> 0 | yes | | | | |
| dim_cohort | 7.3 | 0 -> 1 | yes | 2 | 0 | 0 | 2 |
| dim_cohort re-run | 4.4 | 1 -> 1 | no | | | | |
| dim_page run 1 | 10.8 | 0 -> 1 | yes | 2,315 | 0 | 0 | 2,315 |
| dim_page_classic run 1 | 6.7 | 0 -> 1 | yes | 2,120 | 0 | 0 | 2,120 |
| dim_user run 1 (history rows only) | 7.7 | 0 -> 1 | yes | 369 | 0 | 0 | 369 |
| dim_time run 1 | 4.8 | 0 -> 1 | yes | 8,640 | 0 | 0 | 8,640 |
| fact_edit run 1 | 9.0 | 0 -> 1 | yes | 80,000 | 0 | 0 | 80,000 |
| dim_page run 2 | 3.1 | 1 -> 2 | yes | 181 | 120 | 2,195 | 301 |
| dim_page run 3 (same as_of) | 3.3 | 2 -> 2 | no | | | | |
| dim_page_classic all-versions demo (fails) | 5.8 | 1 -> 1 | no | | | | |
| dim_page_classic run 2 | 4.2 | 1 -> 2 | yes | 137 | 112 | 2,008 | 249 |
| dim_page_classic run 3 | 6.3 | 2 -> 2 | no | | | | |
| dim_user run 2 | 5.1 | 1 -> 2 | yes | 30 | 18 | 351 | 48 |
| dim_user re-run | 4.9 | 2 -> 2 | no | | | | |
| dim_time run 2 | 4.3 | 1 -> 1 | no | | | | |
| fact_edit run 2 | 4.7 | 1 -> 2 | yes | 0 | 291 | 39,709 | 291 |
| fact_edit re-run | 5.9 | 2 -> 2 | no | | | | |
| dim_snapshot 2026-09 | 6.6 | 0 -> 1 | yes | 1 | 0 | 0 | 1 |
| fact_revert_label 2026-09 | 5.3 | 0 -> 1 | yes | 150,000 | 0 | 0 | 150,000 |
| dim_snapshot 2026-10 | 3.9 | 1 -> 2 | yes | 1 | 0 | 0 | 0 (metric, see Pitfalls) |
| fact_revert_label 2026-10 | 6.6 | 1 -> 2 | yes | 150,000 | 700 | 149,300 | 150,700 |
| fact_revert_label 2026-10 re-run | 4.8 | 2 -> 2 | no | | | | |
| fact_revert_label 2026-09 re-run after 2026-10 | 1.8 | 2 -> 2 | no | | | | |
| dim_snapshot 2026-10 re-run | 4.3 | 2 -> 2 | no | | | | |
| mart_label_change | 1.1 | 0 -> 1 | yes | 700 | 0 | 0 | 700 |
| mart_label_change forced re-read from version 1 | 1.0 | 1 -> 1 | no | | | | |
| mart_el_curve (INSERT OVERWRITE) | 10.0 | 0 -> 1 | yes | | | | |
| mart_reconciliation (REPLACE WHERE) | 5.1 | 0 -> 1 | yes | | | | |
| recon_mismatch (REPLACE WHERE) | 4.4 | 0 -> 1 | yes | | | | |
| dim_page with an older as_of (refused) | 0.2 | 2 -> 2 | no | | | | |

- Whole runner: 255.4 s wall (first rebuild 252.7 s). Write statements: 159.0 s. Session start: 5.5 s. The rest is the temp views, about 80 check queries, DESCRIBE HISTORY calls and the sample prints.
- Each step time since the guard was added also holds one DESCRIBE HISTORY read.
- Spark driver JVM peak resident memory (VmHWM from `/proc/<pid>/status`): 3,525.9 MB (first rebuild 3,326.7 MB); heap limit 4,096 MB. This is under the 5 GB limit.
- Other tools: `gen_silver.py` 0.6 s (2.2 s with imports), `verify_gold.py` 1.9 s (3.0 s with imports).
- Sizes: `lake/silver` 16 MB, `lake/gold` 9 MB (fact_edit 4.4 MB, fact_revert_label 3.7 MB with change files and old files).

**Protocol and table features (DESCRIBE DETAIL, RAN; the same values read back with delta-rs):**

| Gold table | minReader | minWriter | tableFeatures | Files | Latest version |
|---|---|---|---|---|---|
| dim_cohort | 1 | 2 | appendOnly, invariants | 2 | 1 |
| dim_snapshot | 1 | 2 | appendOnly, invariants | 2 | 2 |
| dim_time | 1 | 2 | appendOnly, invariants | 1 | 1 |
| dim_user | 1 | 2 | appendOnly, invariants | 1 | 2 |
| dim_page | 1 | 2 | appendOnly, invariants | 1 | 2 |
| dim_page_classic | 1 | 2 | appendOnly, invariants | 1 | 2 |
| fact_edit | 1 | 7 | appendOnly, changeDataFeed, invariants | 3 | 2 |
| fact_revert_label | 1 | 7 | appendOnly, changeDataFeed, invariants | 2 | 2 |
| mart_label_change | 1 | 2 | appendOnly, invariants | 1 | 1 |
| mart_el_curve | 1 | 2 | appendOnly, invariants | 1 | 1 |
| mart_reconciliation | 1 | 2 | appendOnly, invariants | 1 | 1 |
| recon_mismatch | 1 | 2 | appendOnly, invariants | 2 | 1 |

No table has deletion vectors, liquid clustering, identity columns, generated columns, VARIANT, column mapping or in-commit timestamps. No table is partitioned. Every table has the three retention properties; `delta.enableChangeDataFeed=true` is only on the two facts. Every commit of every Gold table carries the JSON user metadata (0 commits without it), and the conf is unset after the run.

**delta-rs read of every Gold table (RAN, `verify_gold.py`):** 12 of 12 tables read with `DeltaTable.to_pandas()` and `polars.read_delta()`, row counts equal to Spark: 2, 2, 8,640, 399, 2,496, 2,257, 80,000, 300,000, 700, 135, 5, 250. No table failed. delta-rs reports writer features `invariants, changeDataFeed, appendOnly` for the two facts and none for the others.

## Not covered

- **Real data and scale.** Only made-up data: 80,000 fact rows, 300,000 label rows, about 97,000 page observations. The real slim file has about 5.27 million rows per month. An unpartitioned `fact_revert_label` MERGE rewrites every file it touches (149,300 rows copied for 700 updates here), and the full window pass for dim_page reads all observations each run. Neither was measured at real size. No partitioning or Z-order was tested for Gold.
- **Late observations for dim_page.** The as_of filter is on the time the state is true (rev_dt, or meta_dt for delete / undelete), not on arrival time. An event that arrives after a run but is dated before it could move an existing version's start, which changes its page_key. The MERGE then inserts the new key and leaves the old row (no delete clause), and fact_edit would need the new key. Not tested.
- **Running an older as_of.** Only the refusal and the pre-filter count (120 rows) were run, not the damaging MERGE itself. The guard was tested on dim_page only.
- **Re-run of the three replace-style marts** on existing tables, and REPLACE WHERE with a second cohort or snapshot in the same table.
- **A third snapshot.** `from_snapshot` in mart_label_change is the snapshot in which the old label was written (`last_changed_snapshot` of the pre-image), which is the previous snapshot only when two are loaded. first_reverted_snapshot and the older-snapshot guard were exercised with two snapshots only.
- **Censoring.** fact_revert_label has no `is_censored` column (the star-schema draft lists one), and the live / dump E(L) series does not remove revisions whose 4-day window ends after the snapshot cutoff.
- **Columns of the draft that were not asked for:** dim_page.is_redirect, dim_user.groups, fact_edit.ingested_at.
- **Null titles.** Titles are compared null-safe, but no carry-forward of the last known title was built, and no NULL title was planted.
- **Several wikis.** page_key holds page_id only; with more than one wiki it needs wiki_db in the key.
- **Named parameters in the main run.** The legacy conf was only run in the probe (SELECT, `?`, one MERGE), not with the full statement set.
- **Other things not run:** Python UDFs or `createDataFrame` (so Python workers were never started), concurrent writers, object storage, OPTIMIZE / VACUUM / checkpoints on Gold, RESTORE, a streaming read of the change feed, TIMESTAMP AS OF (avoided on purpose), delta-rs writing to a Gold table, and reading the change feed of the Spark-written facts with delta-rs `load_cdf`.

## Test matrix

| Feature | Status | Evidence |
| --- | --- | --- |
| Silver tables written by delta-rs with the three retention properties | works | RAN. 6 tables at version 0, reader 1 / writer 2: page_change 57,665, live_revisions 40,000, history_revisions 40,000, live_revert_links 3,023, history_revert_links 4,051, history_slim 450,000 rows. Properties read back with delta-rs. Three generator runs gave an identical planted.json. |
| Gold DDL by Spark SQL: path-based, retention properties, CDF only on fact_edit and fact_revert_label | works | RAN. 12 CREATE TABLE IF NOT EXISTS in 5.6 s. DESCRIBE DETAIL shows the three properties on every table and delta.enableChangeDataFeed=true only on the two facts. |
| No forbidden table features on Gold | works | RAN. tableFeatures are appendOnly, invariants on 10 tables and appendOnly, changeDataFeed, invariants on the 2 facts. minReaderVersion 1 everywhere; minWriterVersion 2, and 7 on the 2 facts. No partition or clustering columns. |
| Commit user metadata JSON {step, as_of, snapshot} set before each write and unset after | works | RAN. 0 commits without JSON user metadata over all 12 Gold tables; the conf is unset at the end of the run. |
| Named parameters (:name) with spark.sql(text, args=...) under the Delta extension | fails | RAN. [UNBOUND_SQL_PARAMETER] Found the unbound parameter: history_start ... SQLSTATE: 42P02, for SELECT, INSERT, UPDATE, MERGE, positional ? and EXECUTE IMMEDIATE. Works without the Delta extension. Works with spark.sql.legacy.parameterSubstitution.constantsOnly=true (SELECT, ?, MERGE with num_updated_rows=1). Main run uses {placeholders}. |
| SQL session variables as an alternative to placeholders | works | RAN in the probes. DECLARE OR REPLACE VARIABLE worked in a SELECT (count 1), inside a MERGE source and in a temp view; the view reads the variable at query time (2,340 before, 2,496 after SET VAR). Not used in the main run. |
| dim_cohort MERGE and re-run | works | RAN. 2 rows inserted (7.3 s); re-run wrote no commit, version stays 1. |
| dim_snapshot MERGE and re-run | works | RAN. Rows (2026-09, 150,000) and (2026-10, 300,000); re-run wrote no commit. numSourceRows metric showed 0 for the 2026-10 commit although 1 row was inserted. |
| dim_time: one row per minute that occurs in the facts | works | RAN. 8,640 rows = planted. 0 fact rows without a dim_time row, 0 dim_time rows not used, 0 rows with wrong hour / date / day_of_week (Monday = 1). Run 2 with no new minute wrote no commit. |
| dim_user Type 1: MERGE on user_key, latest values win, changed rows only | works | RAN. Run 1 (history rows) inserted 369. Run 2 updated 18 and inserted 30 (planted 18 and 30), copied 351. 399 rows; 0 duplicate keys; re-run wrote no commit; 399 of 399 rows equal to the pandas computation. |
| dim_page SCD2 method 1, run 1 (window functions, sentinel start, deterministic page_key) | works | RAN. 2,315 rows for 2,120 pages (planted 2,145 - 25); 0 pages without exactly one current row; 10.8 s. |
| dim_page run 2 closes rows and inserts new versions | works | RAN. numTargetRowsUpdated 120, numTargetRowsInserted 181, numTargetRowsCopied 2,195, source rows 301; 2,315 -> 2,496 rows, 2,145 pages. 120 = planted pages changed after as_of 1; 181 = 156 new versions + 25 new pages. |
| dim_page third run with the same as_of writes no commit | works | RAN. Version stays 2 (3.3 s). |
| dim_page: exactly one current row per page | works | RAN. 0 violating pages after run 1 and after run 2; is_current always equals (valid_to IS NULL). |
| dim_page: no overlapping and no gapped intervals | works | RAN. 0 rows where valid_to differs from the next valid_from; 0 empty or negative intervals; every page starts at 1900-01-01 00:00:00; 0 duplicate page_key. |
| dim_page equals an independent computation | works | RAN. EXCEPT against the computed list in both directions = 0. Plain Python loop over the Silver observations: 2,496 of 2,496 rows equal in every column; versions per page {1: 1,866, 2: 211, 3: 64, 4: 4}. |
| Every fact row joins to exactly one page_key with the as-of condition | works | RAN. 80,000 facts: exactly one version 80,000, none 0, several 0, title differs from the title at edit time 0, same key as fact_edit.page_key 80,000. pandas merge_asof against the Python version list: 80,000 of 80,000 equal. |
| Classic staged-source SCD2 MERGE (NULL merge key) on a second copy, same two steps | partial | RAN. It runs (inserted 2,120; then updated 112, inserted 137; third run no commit; one current row per page) but ends with 2,257 rows against 2,496: 271 rows only in method 1, 32 only in classic, 207 pages differ = the 175 + 32 pages with two or more new versions in one run. 4,210 of 80,000 fact rows find no version. |
| Classic MERGE fed with every new version of a page | fails | RAN, expected. UnsupportedOperationException: [DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE] Cannot perform Merge as multiple source rows matched and attempted to modify the same target row in the Delta table in possibly conflicting ways. No commit was written. |
| Guard against a run with an older as_of | works | RAN. Pre-filter at the older as_of returns 120 rows that would be set current again (0 rows at the newest as_of). The runner refuses: RuntimeError: refused: as_of 2026-10-23 00:00:00 is older than the newest committed as_of 2026-10-27 21:00:00 of dim_page; no commit. Tested on dim_page only. |
| fact_edit run 1: one row per cohort revision of both cohorts | works | RAN. 80,000 inserted (40,000 per cohort), 0 duplicate (wiki_db, rev_id), live_revert_flag true 2,641 = planted; history rows have a NULL flag (0 exceptions). |
| fact_edit run 2: MERGE on (wiki_db, rev_id), changed rows only | works | RAN. Updated 291 = planted, inserted 0, copied 39,709, source rows 291; flag true 2,932 = planted. Change feed of that commit: 291 update_preimage + 291 update_postimage. |
| fact_edit re-run writes no commit | works | RAN. Version stays 2 (5.9 s). |
| fact_edit content and keys | works | RAN. 80,000 of 80,000 rows equal to pandas in every column except page_key (checked separately). 0 rows without a dim_user row, 0 without a dim_time row, 0 with a page_key missing from dim_page; 80 rows with user_key 'unknown' = planted. |
| fact_revert_label load of snapshot 2026-09 | works | RAN. Version 0 -> 1, 150,000 inserted (5.3 s). |
| fact_revert_label load of snapshot 2026-10 as ONE MERGE commit | works | RAN. Version 1 -> 2 (one commit), numTargetRowsUpdated 700 = planted, numTargetRowsInserted 150,000, copied 149,300, source rows 150,700 (6.6 s). 300,000 rows, 0 duplicate keys. |
| Change Data Feed between the two label versions, by path | works | RAN. table_changes_by_path(path, 2, 2) and the readChangeFeed option both give update_preimage 700, update_postimage 700, insert 150,000. |
| Re-run of the 2026-10 load, and of the older 2026-09 load after it | works | RAN. Both wrote no commit (version stays 2; 4.8 s and 1.8 s). |
| fact_revert_label content | works | RAN. 300,000 of 300,000 rows equal to pandas (labels of 2026-10, label_dt, first_reverted_snapshot, last_changed_snapshot). 60 rows that became unreverted keep first_reverted_snapshot 2026-09; 600 September revisions first reverted in 2026-10; 700 rows of the first load have last_changed_snapshot 2026-10; label_dt is set exactly for reverted rows. |
| mart_label_change from the change feed | works | RAN. 700 rows: became_reverted 600, became_unreverted 60, reverter_or_time_changed 40; from_snapshot 2026-09, to_snapshot 2026-10, commit_version 2. A second run is skipped (nothing new in the feed) and a forced re-read from version 1 wrote no commit. |
| Time travel: version found in DESCRIBE HISTORY by userMetadata, read with VERSION AS OF | works | RAN. Versions 1 (2026-09) and 2 (2026-10) found without timestamps. One query: 2026-09 then 4,051, now 4,231; 2026-10 then 4,231, now 4,231 (planted 4,051 and 4,231). VERSION AS OF 1 returns 150,000 rows. |
| SQL-only version lookup: SELECT ... FROM (DESCRIBE HISTORY ...) | fails | RAN. ParseException: [PARSE_SYNTAX_ERROR] Syntax error at or near 'delta': missing ')'. SQLSTATE: 42601. The lookup is done in Python over DESCRIBE HISTORY rows. |
| mart_el_curve against an independent pandas computation | works | RAN. 135 rows (3 series x 5 user kinds x 9 waits) compared: same key set, n_eventual and n_known equal as exact integers in 135 of 135 rows, wait_label and small_group equal, share_known and e_l within 1e-12. |
| E(L) definition edge cases (horizon, inclusive wait, K_s crossing a wait point) | works | RAN. live / stream: n_eventual 2,932, known at wait 0 = 4, at 4 d = 2,920 (12 missing = 3 + 4 + 5 planted crossers). history / dump: 3,563 eventual, 5 at wait 0, 3,563 at 4 d. live / dump: 2,884 = 2,804 + 80. Every wait point has known reverts in all 3 series. Small groups: 'unknown' with 9, 3, 9. |
| mart_reconciliation for the live cohort and snapshot 2026-10 | works | RAN. both_reverted 2,804, stream_only 120, dump_only 80, neither 36,946, not_in_dump 50 = planted = pandas; shares sum to 1.0. The dump label is read at the version the 2026-10 load wrote (VERSION AS OF inside a temp view worked). |
| recon_mismatch | works | RAN. 250 rows: stream_only 120, dump_only 80, not_in_dump 50; the (rev_id, class) set equals pandas; stream times, T, dump seconds and dump reverting id equal to Silver (620 of 620 comparisons). |
| INSERT OVERWRITE and INSERT INTO ... REPLACE WHERE on path-based tables | partial | RAN: both forms wrote the marts (10.0 s, 5.1 s, 4.4 s). They write a commit on every run by design. UNVERIFIED: a re-run on an existing table and a second cohort or snapshot in the same table. |
| delta-rs reads every Gold table | works | RAN. 12 of 12 tables read with to_pandas and polars.read_delta; row counts equal to Spark (2, 2, 8,640, 399, 2,496, 2,257, 80,000, 300,000, 700, 135, 5, 250). String columns arrive as string, not string_view. No table failed. |
| Wall time and peak memory | works | RAN. Whole runner 255.4 s (252.7 s in the first rebuild); write statements 159.0 s; 3.1 to 10.8 s per MERGE even on tiny tables. Spark driver JVM peak RSS 3,525.9 MB (3,326.7 MB), heap limit 4,096 MB. |
| Full rebuild gives the same numbers | works | RAN. Two full rebuilds of Gold: all 76 shared checks have equal values, row counts equal, time-travel and SCD2 comparison numbers equal. Final run: 78 runner checks and 18 pandas checks passed, 0 failed. |
| Repository left untouched | works | RAN. git -C /home/user/truth-lag status --porcelain printed nothing. Only the .git folder's own modification time changed (git status). No __pycache__, .pytest_cache, spark-warehouse, metastore_db or derby.log in the repo; nothing changed in /home/user/delta-io. |

## Tested snippets

### Silver tables written by delta-rs with the three retention properties

```text
write_deltalake(path, tbl, mode="error", configuration=KEEP_HISTORY, partition_by=["snapshot"] if name == "history_slim" else None)
```

### Commit user metadata JSON {step, as_of, snapshot} set before each write and unset after

```text
spark.conf.set("spark.databricks.delta.commitInfo.userMetadata", json.dumps(meta, sort_keys=True)); ...; spark.conf.unset(...)
```

### Named parameters (:name) with spark.sql(text, args=...) under the Delta extension

```text
.config("spark.sql.legacy.parameterSubstitution.constantsOnly", "true")
```

### Every fact row joins to exactly one page_key with the as-of condition

```text
event_dt >= valid_from AND (valid_to IS NULL OR event_dt < valid_to)
```

### Change Data Feed between the two label versions, by path

```sql
SELECT _change_type, count(*) FROM table_changes_by_path('<gold>/fact_revert_label', 2, 2) GROUP BY _change_type
```

## Open questions

- Parameters: should the plan use {placeholders} with the value whitelist (tested in the full run), SQL session variables (tested in a probe), or named parameters with spark.sql.legacy.parameterSubstitution.constantsOnly=true (tested in a probe with SELECT, ? and one MERGE only)? Without that conf, named parameters fail under the Delta extension.
- What do real page_change delete and undelete events hold in revision.rev_dt? The view uses meta_dt for these two kinds because the made-up events carry the older newest revision. If the real events differ, 20_page_obs_view.sql must change.
- Which clock should the dim_page as_of filter use on real data: the time the state is true (used here) or arrival time (meta_dt)? With late events the first can move a version start and so change a page_key that fact_edit already stores; this case was not tested.
- Should dim_page MERGE also delete versions that are no longer in the computed list (a full sync), and should fact_edit then be re-keyed in the same run? Method 1 as tested only inserts and closes.
- Is a full recompute of the page version list per run acceptable at real size (all page_change events of the capture plus the history cohort)? It was measured only on about 97,000 observations.
- Should fact_revert_label be partitioned (for example by month of the revision) so that a snapshot MERGE does not rewrite the whole table? Here 700 updates copied 149,300 rows; the real slim month has about 5.27 million rows.
- Should fact_edit carry user_kind at edit time, so that marts by user kind can be built from Gold alone? dim_user is Type 1 and differs for 424 history revisions in this data.
- Is NULL the right live_revert_flag for history-cohort rows, and is the 'unknown' member the right key for editors without a user_key?
- What should from_snapshot in mart_label_change mean once three snapshots are loaded: the snapshot in which the old label was written (as built) or the snapshot loaded just before?
- Should fact_revert_label get is_censored, and should the live / dump E(L) series drop revisions whose 4-day window ends after the snapshot cutoff? Neither was built.
- Should the three replace-style marts stay full or partial replaces (one commit per run), or become pre-filtered MERGEs like the dims and facts?
- The made-up lake (25 MB) is still in the scratch folder for inspection. It can be removed with: rm -rf /tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/gold_sql_lab/lake
