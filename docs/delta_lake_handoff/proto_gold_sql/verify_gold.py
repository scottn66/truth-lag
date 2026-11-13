"""Independent checks of the Gold tables with delta-rs + pandas (no Spark), and the cross-engine read.

Purpose : recompute E(L), the dim_page versions, the reconciliation classes, the label fact and the
          fact_edit columns from the Silver tables with plain pandas, and compare with what Spark SQL wrote.
          Also: read every Gold table with delta-rs (pandas and polars) and compare the row counts.
Inputs  : <lab>/lake/silver/*, <lab>/lake/gold/*, <lab>/planted.json, <lab>/out/run_gold.json
Outputs : <lab>/out/verify_gold.json and a printed PASS / FAIL list
Run     : <deltars venv>/bin/python verify_gold.py        (about 15 s)
"""
from __future__ import annotations

import json
import os
import time
import warnings

import numpy as np
import pandas as pd
import polars as pl
from deltalake import DeltaTable

warnings.filterwarnings("ignore")
LAB = os.environ.get(
    "GOLD_LAB",
    "/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/gold_sql_lab",
)
SILVER, GOLD = LAB + "/lake/silver", LAB + "/lake/gold"
HORIZON_S = 345_600
WAITS = [("0", 0), ("1 min", 60), ("5 min", 300), ("15 min", 900), ("1 h", 3600), ("6 h", 21600),
         ("1 d", 86400), ("2 d", 172800), ("4 d", 345600)]
SENTINEL = pd.Timestamp("1900-01-01", tz="UTC")
A2 = pd.Timestamp("2026-10-27 21:00:00", tz="UTC")
CHECKS: list[dict] = []


def check(name, got, want, note=""):
    ok = got == want
    CHECKS.append({"check": name, "got": got, "want": want, "ok": ok, "note": note})
    print(("PASS " if ok else "FAIL ") + f"{name}: got={got} want={want} {note}", flush=True)


def silver(name, **kw):
    return DeltaTable(f"{SILVER}/{name}").to_pandas(**kw)


def gold(name, **kw):
    return DeltaTable(f"{GOLD}/{name}").to_pandas(**kw)


def same(a: pd.Series, b: pd.Series) -> pd.Series:
    """Null-safe equality of two aligned columns."""
    return ((a == b) | (a.isna() & b.isna())).fillna(False).astype(bool)


t0 = time.time()
planted = json.load(open(LAB + "/planted.json"))
run = json.load(open(LAB + "/out/run_gold.json"))

# ---- 1. cross-engine: every Gold table read by delta-rs (pandas and polars) ---------------------------------
xeng = {}
for t, n_spark in run["counts"].items():
    rec = {"spark_rows": n_spark}
    try:
        dt = DeltaTable(f"{GOLD}/{t}")
        p = dt.protocol()
        rec.update(version=dt.version(), reader=p.min_reader_version, writer=p.min_writer_version,
                   reader_features=p.reader_features, writer_features=p.writer_features)
        rec["pandas_rows"] = len(dt.to_pandas())
        rec["polars_rows"] = pl.read_delta(f"{GOLD}/{t}").height
        rec["string_types"] = sorted({str(f.type) for f in dt.to_pyarrow_table().schema if "string" in str(f.type)})
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    xeng[t] = rec
    print("XENGINE", t, json.dumps(rec), flush=True)
check("delta-rs reads every Gold table with the Spark row count (pandas and polars)",
      sorted(t for t, r in xeng.items() if r.get("pandas_rows") != r["spark_rows"] or r.get("polars_rows") != r["spark_rows"]), [])

# ---- 2. E(L): independent computation on the Silver tables -------------------------------------------------
lr = silver("live_revisions")
hr = silver("history_revisions")
ll = silver("live_revert_links")
hl = silver("history_revert_links")
slim = silver("history_slim")
slim10 = slim[slim["snapshot"] == "2026-10"]
slim09 = slim[slim["snapshot"] == "2026-09"]


def curve(df: pd.DataFrame, cohort: str, source: str) -> list[tuple]:
    """df: one row per reverted revision with user_kind, T (seconds), K (seconds, 0 when unknown)."""
    ev = df[(df["T"] >= 0) & (df["T"] <= HORIZON_S)]
    known_after = ev["T"].astype("float64") + ev["K"].astype("float64")
    rows = []
    for kind in ["all"] + sorted(ev["user_kind"].unique()):
        m = np.ones(len(ev), dtype=bool) if kind == "all" else (ev["user_kind"] == kind).to_numpy()
        n_e = int(m.sum())
        for label, w in WAITS:
            n_k = int((known_after[m] <= w).sum())
            rows.append((cohort, source, kind, label, w, n_e, n_k, n_k / n_e, 1 - n_k / n_e, n_e < 100))
    return rows


a = ll.merge(lr[["rev_id", "user_kind"]], left_on="reverted_rev_id", right_on="rev_id")
a = a.assign(T=a["T_s"], K=a["K_s"].fillna(0.0))
b = hl.merge(hr[["rev_id", "user_kind"]], left_on="reverted_rev_id", right_on="rev_id")
b = b.assign(T=b["T_s"], K=0.0)
c = slim10[slim10["revision_is_identity_reverted"]].merge(lr[["rev_id", "user_kind"]], left_on="revision_id", right_on="rev_id")
c = c.assign(T=c["revision_seconds_to_identity_revert"], K=0.0).dropna(subset=["T"])
cols = ["cohort_id", "label_source", "user_kind", "wait_label", "wait_s", "n_eventual", "n_known", "share_known", "e_l", "small_group"]
exp = pd.DataFrame(curve(a, "live", "stream") + curve(b, "history", "dump") + curve(c, "live", "dump"), columns=cols)
got = gold("mart_el_curve")
key = ["cohort_id", "label_source", "user_kind", "wait_s"]
j = exp.merge(got, on=key, how="outer", suffixes=("_py", "_sql"), indicator=True)
check("E(L): same set of rows (cohort, source, user kind, wait)", j["_merge"].value_counts().to_dict().get("both", 0), len(exp),
      f"python rows={len(exp)} sql rows={len(got)}")
jb = j[j["_merge"] == "both"]
check("E(L): rows with n_eventual AND n_known equal (exact integers)",
      int(((jb["n_eventual_py"] == jb["n_eventual_sql"]) & (jb["n_known_py"] == jb["n_known_sql"])).sum()), len(exp))
check("E(L): rows with equal wait_label and small_group",
      int(((jb["wait_label_py"] == jb["wait_label_sql"]) & (jb["small_group_py"] == jb["small_group_sql"])).sum()), len(exp))
check("E(L): rows with share_known and e_l within 1e-12",
      int((((jb["share_known_py"] - jb["share_known_sql"]).abs() < 1e-12) & ((jb["e_l_py"] - jb["e_l_sql"]).abs() < 1e-12)).sum()), len(exp))
check("E(L): every wait point has known reverts except wait 0 in small groups (series 'all', n_known > 0)",
      int((exp[(exp["user_kind"] == "all")]["n_known"] > 0).sum()), 27)
print(exp[exp["user_kind"] == "all"].to_string(index=False))
print("small groups:", exp[exp["small_group"]][["cohort_id", "label_source", "user_kind", "n_eventual"]].drop_duplicates().to_dict("records"))

# ---- 3. dim_page: independent version list (plain Python loop over the observations) -----------------------
pc = silver("page_change")
obs = pd.concat([
    pd.DataFrame({"page_id": hr["page_id"], "title": hr["page_title_historical"], "ns": hr["page_ns"], "deleted": False,
                  "t": hr["ts"], "seq": hr["rev_id"]}),
    pd.DataFrame({"page_id": pc["page_id"], "title": pc["page_title"], "ns": pc["ns"].astype("int64"), "deleted": pc["kind"] == "delete",
                  "t": pc["rev_dt"].where(~pc["kind"].isin(["delete", "undelete"]), pc["meta_dt"]),
                  "seq": pc["rev_id"].fillna(0).astype("int64")}),
], ignore_index=True)
obs = obs[obs["t"] <= A2].sort_values(["page_id", "t", "seq"])
obs["sec"] = obs["t"].dt.floor("s")
vers = []
for pid, g in obs.groupby("page_id", sort=True):
    per_sec: dict = {}
    for sec, title, ns, deleted in zip(g["sec"], g["title"], g["ns"], g["deleted"]):
        per_sec[sec] = (title, int(ns), bool(deleted))            # the last observation of a second wins
    prev, mine = None, []
    for sec in sorted(per_sec):
        st = per_sec[sec]
        if prev is None:
            mine.append([SENTINEL, st])
        elif st != prev:
            mine.append([sec, st])
        prev = st
    for i, (vf, st) in enumerate(mine):
        vt = mine[i + 1][0] if i + 1 < len(mine) else pd.NaT
        vers.append((f"{pid}-{vf:%Y%m%d%H%M%S}", int(pid), st[0], st[1], st[2], vf, vt, i + 1 == len(mine)))
expd = pd.DataFrame(vers, columns=["page_key", "page_id", "title", "namespace", "is_deleted", "valid_from", "valid_to", "is_current"])
expd["valid_to"] = pd.to_datetime(expd["valid_to"], utc=True)
dp = gold("dim_page")
j = expd.merge(dp, on="page_key", how="outer", suffixes=("_py", "_sql"), indicator=True)
check("dim_page: same page_key set as the Python loop", j["_merge"].value_counts().to_dict().get("both", 0), len(expd),
      f"python rows={len(expd)} sql rows={len(dp)}")
jb = j[j["_merge"] == "both"]
eq = np.ones(len(jb), dtype=bool)
for col in ["page_id", "title", "namespace", "is_deleted", "valid_from", "valid_to", "is_current"]:
    eq &= same(jb[col + "_py"], jb[col + "_sql"]).to_numpy()
check("dim_page: rows equal to the Python loop in every column", int(eq.sum()), len(expd))
check("dim_page: versions per page", expd.groupby("page_id").size().value_counts().sort_index().to_dict(),
      dp.groupby("page_id").size().value_counts().sort_index().to_dict())

# ---- 4. reconciliation: independent classes from Silver ---------------------------------------------------
stream = set(ll.loc[ll["within_followup"], "reverted_rev_id"])
d10 = slim10.set_index("revision_id")
in_dump = lr["rev_id"].isin(d10.index)
d_rev = lr["rev_id"].map(d10["revision_is_identity_reverted"]).fillna(False).astype(bool)
d_sec = lr["rev_id"].map(d10["revision_seconds_to_identity_revert"])
dump = d_rev & (d_sec <= HORIZON_S).fillna(False).astype(bool)
s = lr["rev_id"].isin(stream)
cls = np.where(~in_dump, "not_in_dump", np.where(s & dump, "both_reverted", np.where(s, "stream_only", np.where(dump, "dump_only", "neither"))))
py_counts = pd.Series(cls).value_counts().sort_index().to_dict()
rec = planted["reconciliation_live_vs_2026-10"]
check("reconciliation: pandas classes = planted", py_counts, {k: rec[k] for k in sorted(py_counts)})
mr = gold("mart_reconciliation")
check("reconciliation: Gold mart = pandas classes", mr.set_index("recon_class")["n_revisions"].sort_index().to_dict(), py_counts)
check("reconciliation: shares sum to 1", round(float(mr["share"].sum()), 12), 1.0)
mm = gold("recon_mismatch")
py_mis = pd.DataFrame({"rev_id": lr["rev_id"], "recon_class": cls})
py_mis = py_mis[py_mis["recon_class"].isin(["stream_only", "dump_only", "not_in_dump"])]
j = py_mis.merge(mm[["rev_id", "recon_class"]], on=["rev_id", "recon_class"], how="outer", indicator=True)
check("recon_mismatch: same (rev_id, class) rows as pandas", j["_merge"].value_counts().to_dict().get("both", 0), rec["recon_mismatch_rows"])
m2 = mm.merge(ll[["reverted_rev_id", "reverting_ts", "known_at", "T_s"]], left_on="rev_id", right_on="reverted_rev_id", how="left")
m2 = m2.merge(d10[["revision_seconds_to_identity_revert", "revision_first_identity_reverting_revision_id"]], left_on="rev_id", right_index=True, how="left")
so = m2["recon_class"] == "stream_only"
check("recon_mismatch: stream times and dump values equal to Silver",
      int((same(m2["stream_revert_dt"][so], m2["reverting_ts"][so]) & same(m2["stream_known_dt"][so], m2["known_at"][so])
           & same(m2["stream_seconds_to_revert"][so], m2["T_s"][so])).sum())
      + int(same(m2["dump_seconds_to_revert"], m2["revision_seconds_to_identity_revert"]).sum())
      + int(same(m2["dump_reverting_rev_id"], m2["revision_first_identity_reverting_revision_id"]).sum()),
      rec["stream_only"] + 2 * rec["recon_mismatch_rows"])

# ---- 5. fact_revert_label against the two Silver snapshots ------------------------------------------------
fl = gold("fact_revert_label").set_index("rev_id")
s10 = slim10.set_index("revision_id").reindex(fl.index)
s09 = slim09.set_index("revision_id").reindex(fl.index)
R, S, I = "revision_is_identity_reverted", "revision_seconds_to_identity_revert", "revision_first_identity_reverting_revision_id"
ok = (fl["is_identity_reverted"] == s10[R].astype(bool)) & same(fl["seconds_to_identity_revert"], s10[S]) & same(fl["reverting_rev_id"], s10[I])
exp_dt = (s10["event_timestamp"] + pd.to_timedelta(s10[S].astype("float64"), unit="s")).where(s10[R].astype(bool))
ok &= same(fl["label_dt"], exp_dt)
in09 = s09[R].notna()
r09 = s09[R].fillna(False).astype(bool)
first = pd.Series(np.where(r09, "2026-09", np.where(s10[R].astype(bool), "2026-10", None)), index=fl.index, dtype=object)
changed = in09 & ~((r09 == s10[R].astype(bool)) & same(s09[S], s10[S]) & same(s09[I], s10[I]))
last = pd.Series(np.where(in09 & ~changed, "2026-09", "2026-10"), index=fl.index, dtype=object)
ok &= same(fl["first_reverted_snapshot"], first) & same(fl["last_changed_snapshot"], last)
check("fact_revert_label: rows equal to pandas (labels of 2026-10, label_dt, first / last snapshot)", int(ok.sum()), planted["fact_revert_label"]["rows_after_2026-10"])

# ---- 6. fact_edit against Silver --------------------------------------------------------------------------
fe = gold("fact_edit").set_index("rev_id")
rv = pd.concat([hr, lr], ignore_index=True).set_index("rev_id").reindex(fe.index)
lk = ll[ll["within_followup"] & (ll["known_at"] <= A2)].set_index("reverted_rev_id").reindex(fe.index)
ok = same(fe["event_dt"], rv["ts"]) & same(fe["seen_dt"], rv["seen_ts"]) & same(fe["bytes_diff"], rv["size_delta"])
ok &= same(fe["parent_rev_id"], rv["parent_id"]) & (fe["user_key"] == rv["user_key"].fillna("unknown")) & (fe["cohort_id"] == rv["cohort"])
ok &= (fe["time_key"] == rv["ts"].dt.strftime("%Y%m%d%H%M").astype("int64")) & (fe["is_bot"] == rv["is_bot"])
ok &= same(fe["revert_risk_score"], rv["revert_risk"]) & (fe["page_edits_prev_1h"] == rv["page_edits_prev_1h"])
ok &= same(fe["live_revert_dt"], lk["reverting_ts"]) & same(fe["live_known_dt"], lk["known_at"])
flag = pd.Series(np.where(rv["cohort"] == "live", lk["T_s"].notna(), None), index=fe.index, dtype=object)
ok &= same(fe["live_revert_flag"].astype(object), flag)
check("fact_edit: rows equal to pandas in every column except page_key", int(ok.sum()), planted["fact_edit"]["rows"])
# page_key: the dim_page version (Python list) that holds the edit time
v = expd.sort_values("valid_from")
f2 = fe.reset_index().merge(rv[["page_id"]].reset_index(), on="rev_id").sort_values("event_dt")
f2["event_dt"] = f2["event_dt"].astype("datetime64[us, UTC]")
v["valid_from"] = v["valid_from"].astype("datetime64[us, UTC]")
m = pd.merge_asof(f2, v[["page_id", "valid_from", "page_key"]], left_on="event_dt", right_on="valid_from", by="page_id",
                  direction="backward", suffixes=("", "_py"))
check("fact_edit: page_key equal to the as-of version of the Python list", int((m["page_key"] == m["page_key_py"]).sum()), planted["fact_edit"]["rows"])

# ---- 7. dim_user against pandas ---------------------------------------------------------------------------
u = pd.concat([hr, lr], ignore_index=True)
u = u[u["ts"] <= A2].assign(user_key=lambda d: d["user_key"].fillna("unknown")).sort_values(["ts", "rev_id"]).groupby("user_key").last()
du = gold("dim_user").set_index("user_key").reindex(u.index)
ok = same(du["user_id"], u["user_id"]) & same(du["user_text"], u["user_name"]) & (du["user_kind"] == u["user_kind"]) \
    & (du["is_bot"] == u["is_bot"]) & (du["is_temporary"] == u["is_temp"])
check("dim_user: rows equal to pandas (latest values per user_key)", int(ok.sum()), planted["dim_user"]["rows_run_2"])
kind_now = lr["user_key"].fillna("unknown").map(gold("dim_user").set_index("user_key")["user_kind"])
print("NOTE revisions whose user_kind at edit time differs from dim_user (Type 1):",
      int((kind_now != lr["user_kind"]).sum()), "live,",
      int((hr["user_key"].fillna("unknown").map(gold("dim_user").set_index("user_key")["user_kind"]) != hr["user_kind"]).sum()), "history")

n_fail = sum(1 for c in CHECKS if not c["ok"])
json.dump({"checks": CHECKS, "cross_engine": xeng, "el_rows_compared": len(exp), "seconds": round(time.time() - t0, 1)},
          open(LAB + "/out/verify_gold.json", "w"), indent=1, default=str)
print(f"CHECKS {len(CHECKS) - n_fail} passed, {n_fail} failed in {time.time() - t0:.1f} s", flush=True)
time.sleep(0.5)     # delta-rs lab pitfall 7: an exit right after a pyarrow read can abort
