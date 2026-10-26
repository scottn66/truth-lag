"""Build report/FACTS.md: the key numbers of EC HW2 in one table.

Purpose
    Every number a teammate needs for the report, read from the outputs of the
    other scripts. Nothing is typed by hand, except the Wikistats count (an
    outside fact) and the two example pages for the Motivation (an editorial choice).
    One row per number: key | value | unit | source file | FINAL or PROVISIONAL.
    PROVISIONAL means one of three things:
      - the number depends on the live cohort, whose stream labels are final only
        after config.LIVE_FINAL_AFTER (2026-10-27 00:05 UTC); or
      - it is a comparison timing that results/comparison.csv labels "draft"; or
      - it is a modeling-pain score that is still a draft by Claude Code
        (comparison/pain.csv, column scored_by).
    Horizons: history keys count reverts within 20 days, unless the key ends in
    _4d (reverts within 4 days, the horizon of the live cohort). Live keys count
    reverts within 4 days. Compare the live cohort only with the _4d history keys.
    Timings of the comparison queries come only from results/comparison.csv
    (cmp_ms_*: median, min and max); the per-engine mongo_ms_* / cypher_ms_* of the
    same queries are single-engine runs and say so in their unit.
    The same file is a small library for the notebooks (they import it):
      - check({key: value}) compares notebook numbers with FACTS.md and prints
        OK or DIFFERENT for each key;
      - page_timeline(), decision_table() and late_examples() make the tables of
        notebooks 01 and 05. Human editors appear only as pseudonyms.

Inputs
    data/tables/: _SUCCESS_*.json, history_summary.json, live_summary.json,
        late_reverts_summary.json, history_revisions.parquet, live_revisions.parquet,
        history_revert_links.parquet, live_revert_links.parquet, late_reverts.parquet
    data/parsed/: _SUCCESS_parsed.json, capture_gaps.csv, page_change.parquet
    data/neo4j/_SUCCESS_load_neo4j_local.json
    ec-hw2/results/: mongo_*.csv, cypher_*.csv, comparison.csv, comparison_extra.csv,
        _SUCCESS_*.json
    ec-hw2/comparison/pain.csv (the modeling-pain scores and who scored them)
    The local MongoDB (only for the Atlas size estimate; skipped if it is down).

Outputs
    ec-hw2/report/FACTS.md and ec-hw2/report/_SUCCESS_facts.json.

Run (from the repo root; about 10 seconds)
    .venv/bin/python ec-hw2/report/build_facts.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

REPORT_DIR = config.HW2_DIR / "report"
FACTS_PATH = REPORT_DIR / "FACTS.md"
SUCCESS_PATH = REPORT_DIR / "_SUCCESS_facts.json"
T = config.TABLES_DIR
R = config.RESULTS_DIR
P = config.PARSED_DIR

# An outside fact: Wikistats shows 298,802 content edits on English Wikipedia for
# 2026-09-08 to 2026-09-10 (checked during planning, 2026-10-24 UTC).
WIKISTATS_CONTENT_EDITS = 298_802
WIKISTATS_SOURCE = "Wikistats (stats.wikimedia.org), content edits 2026-09-08..10; plan, checked 2026-10-24"

# The two example pages for the Motivation. We chose them because they are not
# sensitive (a sports event and a physics article), both are in the top 20 contested
# pages (Mongo Q2), and they show a slow revert chain and fast vandalism repair.
EXAMPLE_SLOW_PAGE_ID = 229356     # World_Figure_Skating_Championships
EXAMPLE_FAST_PAGE_ID = 42709      # Pendulum

FINAL = "FINAL"
PROVISIONAL = "PROVISIONAL"


@dataclass
class Fact:
    key: str
    value: str
    unit: str
    source: str
    status: str


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def rel(path: Path) -> str:
    """A path as the teammates see it: relative to the repo root."""
    try:
        return str(Path(path).resolve().relative_to(config.REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def n(x) -> str:
    """A whole number with thousands separators: 295016 -> '295,016'."""
    return f"{int(round(float(x))):,}"


def dec(x, d: int) -> str:
    return f"{float(x):,.{d}f}"


def pct(fraction, d: int = 2, sign: bool = False) -> str:
    """A fraction as a percent number: 0.074289 -> '7.43'."""
    v = 100 * float(fraction)
    return f"{v:+.{d}f}" if sign else f"{v:.{d}f}"


def utc_text(ts) -> str:
    """'2026-10-23T13:52:21Z' style text for a time (aware UTC)."""
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def hours_text(seconds) -> str:
    """A short duration for a timeline: 41 s, 6 min, 4.0 h, 2.1 d."""
    s = float(seconds)
    if s < 60:
        return f"{s:.0f} s"
    if s < 3600:
        return f"{s / 60:.0f} min"
    if s < 86400:
        return f"{s / 3600:.1f} h"
    return f"{s / 86400:.1f} d"


def live_status() -> str:
    s = read_json(T / "_SUCCESS_live.json")
    return PROVISIONAL if s.get("provisional", True) else FINAL


def alias_hex() -> int:
    """The pseudonym length: 'editor_' + config.ALIAS_HEX hex digits (fixed in config.py)."""
    return config.ALIAS_HEX


def comparison_query_names() -> set[str]:
    """The Mongo and Cypher query files that results/comparison.csv times (file stems).

    Their per-engine timings (mongo_ms_*, cypher_ms_*) are single-engine runs: the
    comparison uses only comparison.csv.
    """
    cmp = pd.read_csv(R / "comparison.csv")
    return {Path(str(f)).stem for f in cmp["query_file"]}


SINGLE_ENGINE_NOTE = "single-engine run, not for the comparison: use cmp_ms_*"


def pain_is_draft(scored_by) -> bool:
    """A pain score is a draft until a named person (not Claude Code) has re-scored it."""
    s = "" if scored_by is None or (isinstance(scored_by, float) and pd.isna(scored_by)) else str(scored_by)
    s = s.strip().lower()
    return s == "" or "draft" in s or "claude" in s


def _none(x):
    """pandas missing values (NA, NaN) become None."""
    return None if x is None or pd.isna(x) else x


def public(kind, key, name, n_hex: int) -> str | None:
    """Bots keep their name; humans get the pseudonym (the rule of ingest/build_documents.py)."""
    from ingest import build_documents as bd
    kind, key, name = _none(kind), _none(key), _none(name)
    if key is None:
        return name if kind == "bot" else "editor_unknown"
    return bd.public_name(kind, key, name, n_hex)


# --------------------------------------------------------------------------
# Tables for the notebooks (also used for some facts)
# --------------------------------------------------------------------------
def page_timeline(page_id: int, n_hex: int | None = None) -> pd.DataFrame:
    """Every history-cohort revision of one page, in time order, with pseudonyms."""
    n_hex = n_hex or alias_hex()
    rev = pd.read_parquet(T / "history_revisions.parquet",
                          filters=[("page_id", "==", int(page_id))])
    rev = rev.sort_values(["ts", "rev_id"]).reset_index(drop=True)
    out = pd.DataFrame({
        "time_utc": rev["ts"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "page_title": rev["page_title"],
        "editor": [public(k, key, nm, n_hex) for k, key, nm in
                   zip(rev["user_kind"], rev["user_key"], rev["user_name"])],
        "editor_kind": rev["user_kind"],
        "size_delta": rev["size_delta"],
        "is_revert": rev["is_revert"],
        "reverted_20d": rev["reverted"],
        "time_to_revert_s": rev["secs_to_revert"].where(rev["reverted"]),
        "reverted_by": [public(k, key, nm, n_hex) if r else None for k, key, nm, r in
                        zip(rev["reverter_kind"], rev["reverter_key"], rev["reverter_name"],
                            rev["reverted"])],
    })
    out["time_to_revert"] = [hours_text(s) if pd.notna(s) else "" for s in out["time_to_revert_s"]]
    return out


def timeline_summary(tl: pd.DataFrame) -> dict:
    """Counts for the facts table, from page_timeline()."""
    rv = tl[tl["reverted_20d"]]
    tsec = rv["time_to_revert_s"].astype(float)
    ts = pd.to_datetime(tl["time_utc"], utc=True)
    end = (pd.to_datetime(rv["time_utc"], utc=True)
           + pd.to_timedelta(tsec, unit="s")).max() if len(rv) else ts.max()
    steps = []
    for _, r in tl.head(3).iterrows():
        what = f"{r['editor']} {'+' if r['size_delta'] >= 0 else '-'}{abs(int(r['size_delta']))} bytes"
        if r["is_revert"]:
            what += " (a revert)"
        if r["reverted_20d"]:
            what += f", reverted after {r['time_to_revert']}"
        steps.append(f"{r['time_utc'][:16]} UTC {what}")
    return {
        "title": tl["page_title"].iloc[0],
        "edits": len(tl),
        "editors": tl["editor"].nunique(),
        "reverted": len(rv),
        "T_min_s": float(tsec.min()), "T_median_s": float(tsec.median()),
        "T_max_s": float(tsec.max()),
        "first_utc": ts.min().strftime("%Y-%m-%d %H:%M UTC"),
        "last_revert_utc": end.strftime("%Y-%m-%d %H:%M UTC"),
        "span_h": (end - ts.min()).total_seconds() / 3600,
        "first_steps": "; ".join(steps),
        "editor_kinds": ", ".join(f"{k} {v}" for k, v in tl["editor_kind"].value_counts().items()),
    }


def decision_table(deciles: pd.DataFrame | None = None) -> pd.DataFrame:
    """The RAG-crawler table: per revert-risk decile, what a wait buys you.

    Input: results/mongo_q5_risk_deciles.csv (Mongo Q5 risk deciles, live cohort).
    For each wait w in config.DECISION_WAITS_S (after the edit was saved):
      - visible_<w>: the share of the eventual reverts (within 4 days) that already
        happened by w. k = reverts with T <= w, n = all eventual reverts of the group.
      - later_<w>: of the edits NOT reverted by w, the share that is still reverted
        later (within 4 days). This is p_<w> of the Mongo Q5 risk deciles.
    Both have a Wilson 95% interval (queries/run_mongo.py wilson()).
    Like the risk-decile pipeline, this uses T (time to revert), not T + K.
    """
    from queries import run_mongo
    if deciles is None:
        deciles = pd.read_csv(R / "mongo_q5_risk_deciles.csv")
    rows = []
    for _, r in deciles.iterrows():
        has_range = pd.notna(r["risk_min"])
        row = {"group": r["group"],
               "risk_score": f"{r['risk_min']:.2f}-{r['risk_max']:.2f}" if has_range else "none",
               "edits": int(r["n"]), "reverts_4d": int(r["n_reverted_4d"]),
               "revert_rate_4d_pct": 100 * r["revert_rate_4d"]}
        n_rev = int(r["n_reverted_4d"])
        for wait in config.DECISION_WAITS_S:
            tag = wait.replace(" ", "")
            if config.DECISION_WAITS_S[wait] > 0:
                k = n_rev - int(r[f"reverted_after_{tag}"])
                lo, hi = run_mongo.wilson(k, n_rev)
                row[f"visible_{tag}_pct"] = 100 * k / n_rev if n_rev else None
                row[f"visible_{tag}_lo"] = 100 * lo if lo is not None else None
                row[f"visible_{tag}_hi"] = 100 * hi if hi is not None else None
                row[f"later_{tag}_pct"] = 100 * r[f"p_{tag}"]
                row[f"later_{tag}_lo"] = 100 * r[f"ci_lo_{tag}"]
                row[f"later_{tag}_hi"] = 100 * r[f"ci_hi_{tag}"]
                row[f"clean_at_{tag}"] = int(r[f"at_risk_{tag}"])
        rows.append(row)
    return pd.DataFrame(rows)


def decision_table_text(dt: pd.DataFrame) -> pd.DataFrame:
    """decision_table() as short text cells: '70.7% (69.7-71.7)'."""
    def cell(row, name, d=1):
        return f"{row[name + '_pct']:.{d}f}% ({row[name + '_lo']:.{d}f}-{row[name + '_hi']:.{d}f})"
    waits = [w for w, s in config.DECISION_WAITS_S.items() if s > 0]
    out = []
    for _, r in dt.iterrows():
        o = {"risk group": r["group"], "risk score": r["risk_score"], "edits (n)": f"{r['edits']:,}",
             "reverts in 4 d (n)": f"{r['reverts_4d']:,}",
             "revert rate": f"{r['revert_rate_4d_pct']:.2f}%"}
        for w in waits:
            tag = w.replace(" ", "")
            o[f"visible after {w} [95% CI]"] = cell(r, f"visible_{tag}")
        for w in waits:
            tag = w.replace(" ", "")
            o[f"reverted later if clean at {w} [95% CI]"] = cell(r, f"later_{tag}", 2)
        out.append(o)
    return pd.DataFrame(out)


def late_examples(n_hex: int | None = None) -> pd.DataFrame:
    """One late revert of each class, from the history cohort (lowest rev_id), with pseudonyms."""
    n_hex = n_hex or alias_hex()
    late = pd.read_parquet(T / "late_reverts.parquet")
    late = late[late["in_history_cohort"]].sort_values("rev_id")
    picks = [late[late["class"] == c].head(1) for c in config.LATE_CLASSES]
    picks = pd.concat([p for p in picks if len(p)], ignore_index=True)
    hist = pd.read_parquet(T / "history_revisions.parquet",
                           columns=["rev_id", "page_title", "user_kind", "user_key", "user_name",
                                    "reverted_any"],
                           filters=[("rev_id", "in", picks["rev_id"].tolist())])
    ids = [int(x) for x in picks["reverting_rev_id"].dropna()]
    pc = pd.read_parquet(P / "page_change.parquet",
                         columns=["rev_id", "rev_dt", "user_id", "user_name", "is_bot", "is_temp"],
                         filters=[("rev_id", "in", ids)]) if ids else pd.DataFrame(columns=["rev_id"])
    pc = pc.drop_duplicates("rev_id").set_index("rev_id")
    m = picks.merge(hist, on="rev_id", how="left")
    rows = []
    for _, r in m.iterrows():
        rv = None
        if pd.notna(r["reverting_rev_id"]) and int(r["reverting_rev_id"]) in pc.index:
            e = pc.loc[int(r["reverting_rev_id"])]
            kind = config.user_kind(e["user_name"], bool(e["is_bot"]), bool(e["is_temp"]))
            key = config.editor_key(kind, e["user_id"], e["user_name"])
            rv = f"{public(kind, key, e['user_name'], n_hex)} ({kind})"
        rows.append({
            "class": r["class"], "page_title": r["page_title"],
            "edit_utc": utc_text(r["rev_ts"]),
            "dump_says_reverted": bool(r["reverted_any"]),
            "first_stream_signal_utc": utc_text(r["first_signal_at"]),
            "age_days": round(float(r["age_days"]), 1),
            "author": f"{public(r['user_kind'], r['user_key'], r['user_name'], n_hex)} ({r['user_kind']})",
            "reverter": rv or "not known (tag only)",
            "method": r["method"] if isinstance(r["method"], str) else "not known",
            "via": " + ".join(r["via"]) if r["via"] is not None else "",
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# The facts, section by section
# --------------------------------------------------------------------------
def facts_data() -> list[Fact]:
    """Section 1: the two cohorts, the filters, sanity checks (notebook 01)."""
    out: list[Fact] = []
    hs = read_json(T / "history_summary.json")
    sh = read_json(T / "_SUCCESS_history.json")
    src_h = rel(T / "history_summary.json")
    src_sh = rel(T / "_SUCCESS_history.json")
    file_rows = sh["inputs"][config.HISTORY_COHORT_FILE]
    rows_out = sh["rows"]["history_revisions.parquet"]
    dr = hs["rows"]["dropped"]
    add = out.append
    add(Fact("history_file_rows", n(file_rows), "rows", src_sh, FINAL))
    add(Fact("history_slim_file_rows", n(sh["inputs"][config.HISTORY_SLIM_FILE]), "rows", src_sh, FINAL))
    add(Fact("history_dropped_namespace_not_0", n(dr["namespace_historical_not_0"]), "rows", src_h, FINAL))
    add(Fact("history_dropped_null_same_sha1", n(dr["null_revision_same_sha1"]), "rows", src_h, FINAL))
    add(Fact("history_dropped_null_comment", n(dr["null_revision_comment"]), "rows", src_h, FINAL))
    add(Fact("history_revisions", n(rows_out), "revisions", src_sh, FINAL))
    add(Fact("history_pages", n(hs["other_counts"]["pages"]), "pages", src_h, FINAL))
    add(Fact("history_editors", n(hs["other_counts"]["editors_with_key"]), "editors", src_h, FINAL))
    for k in config.USER_KINDS:
        add(Fact(f"history_edits_{k}", n(hs["user_kind_counts"].get(k, 0)), "revisions", src_h, FINAL))
    add(Fact("wikistats_content_edits", n(WIKISTATS_CONTENT_EDITS), "edits", WIKISTATS_SOURCE, FINAL))
    add(Fact("history_file_vs_wikistats_pct",
             pct((file_rows - WIKISTATS_CONTENT_EDITS) / WIKISTATS_CONTENT_EDITS, sign=True), "%",
             src_sh, FINAL))
    add(Fact("history_revisions_vs_wikistats_pct",
             pct((rows_out - WIKISTATS_CONTENT_EDITS) / WIKISTATS_CONTENT_EDITS, sign=True), "%",
             src_sh, FINAL))
    rr = hs["revert_rate_reverted"]
    h20 = "history reverts within 20 days"
    add(Fact("history_reverted_20d", n(rr["all"]["reverted"]), "revisions (reverted within 20 days)", src_h, FINAL))
    add(Fact("history_revert_rate_pct", pct(rr["all"]["rate"]), "% (reverted within 20 days)", src_h, FINAL))
    add(Fact("history_revert_rate_non_bot_pct", pct(rr["non_bot"]["rate"]), "% (reverted within 20 days)",
             src_h, FINAL))
    for k in ("temporary", "registered", "bot"):
        add(Fact(f"history_revert_rate_{k}_pct", pct(rr["by_user_kind"][k]["rate"]), "% (reverted within 20 days)",
                 src_h, FINAL))
    add(Fact("history_reverted_any_time", n(hs["revert_rate_reverted_any"]["all"]["reverted"]),
             "revisions (reverted at any time before the snapshot)", src_h, FINAL))
    tt = hs["time_to_revert"]
    a, nb = tt["reverted_le_20d_all"], tt["reverted_le_20d_non_bot"]
    add(Fact("history_median_T_s", n(a["median_s"]), f"s ({h20})", src_h, FINAL))
    add(Fact("history_median_T_h", dec(a["median_s"] / 3600, 2), f"h ({h20})", src_h, FINAL))
    add(Fact("history_median_T_non_bot_h", dec(nb["median_s"] / 3600, 2), f"h ({h20}, non-bot authors)",
             src_h, FINAL))
    for k in ("temporary", "registered", "bot"):
        add(Fact(f"history_median_T_{k}_h",
                 dec(tt["reverted_le_20d_by_author_kind"][k]["median_s"] / 3600, 2), f"h ({h20})", src_h, FINAL))
    add(Fact("history_T_within_1h_pct", pct(a["share_T_lt_1h"]), f"% of {h20}", src_h, FINAL))
    add(Fact("history_T_within_1d_pct", pct(a["share_T_lt_1d"]), f"% of {h20}", src_h, FINAL))
    add(Fact("history_T_over_7d_pct", pct(a["share_T_gt_7d"]), f"% of {h20}", src_h, FINAL))
    add(Fact("history_T_p90_d", dec(a["p90_s"] / 86400, 2), f"days ({h20})", src_h, FINAL))
    add(Fact("history_self_revert_pct", pct(hs["self_revert_le_20d_by_author_kind"]["all"]["self_share"]),
             f"% of {h20}", src_h, FINAL))
    out.extend(facts_history_4d())
    add(Fact("history_revert_links", n(hs["links"]["rows"]), "rows", src_h, FINAL))
    add(Fact("history_links_by_other_20d", n(hs["links"]["within_followup_and_by_other"]), "rows",
             src_h, FINAL))
    ta = hs["tag_agreement"]
    add(Fact("history_tag_agreement_pct", pct(ta["agreement_share"]), "% of revisions", src_h, FINAL))
    names = {"<1 h": "lt_1h", "1 h-1 d": "1h_1d", "1-7 d": "1d_7d", "7-20 d": "7d_20d", ">20 d": "gt_20d",
             "not reverted": "not_reverted"}
    for b, key in names.items():
        add(Fact(f"history_tag_share_T_{key}_pct", pct(ta["by_T_bucket"][b]["tag_share"]),
                 "% with mw-reverted tag", src_h, FINAL))
    return out


def facts_history_4d() -> list[Fact]:
    """The history cohort on the live horizon: reverts with T <= 4 days (config.LIVE_FOLLOWUP_S).

    The shares come from the 'history_4d' rows of Mongo Q3; the median and a recount
    come from data/tables/history_revert_links.parquet (the same links Mongo Q3 reads).
    """
    out: list[Fact] = []
    unit = "history reverts within 4 days, the live horizon"
    q3 = pd.read_csv(R / "mongo_q3_time_to_revert.csv")
    h4 = q3[q3["cohort"] == "history_4d"]
    if h4.empty:
        raise SystemExit("STOP: results/mongo_q3_time_to_revert.csv has no 'history_4d' rows; "
                         "run queries/run_mongo.py first")
    links = pd.read_parquet(T / "history_revert_links.parquet", columns=["T_s", "within_followup"])
    t4 = links.loc[links["within_followup"] & (links["T_s"] <= config.LIVE_FOLLOWUP_S), "T_s"].astype(float)
    if len(t4) != int(h4["n"].sum()):
        raise SystemExit(f"STOP: history_revert_links has {len(t4):,} reverts within 4 days, but Mongo Q3 "
                         f"history_4d has {int(h4['n'].sum()):,}; rebuild the results first")
    s3 = rel(R / "mongo_q3_time_to_revert.csv")
    sl = rel(T / "history_revert_links.parquet")
    out.append(Fact("history_reverted_4d", n(len(t4)), "revisions (reverted within 4 days)", sl, FINAL))
    out.append(Fact("history_median_T_4d_s", n(t4.median()), f"s ({unit})", sl, FINAL))
    out.append(Fact("history_median_T_4d_h", dec(t4.median() / 3600, 2), f"h ({unit})", sl, FINAL))
    for edge, key in ((3600, "1h"), (86400, "1d")):
        cum = h4.loc[h4["bucket_upper_s"] == edge, "cum_share"]
        out.append(Fact(f"history_T_within_{key}_4d_pct", pct(cum.iloc[0]), f"% of {unit}", s3, FINAL))
    return out


def facts_live() -> list[Fact]:
    """Section 2: the live cohort and the capture (notebook 01)."""
    out: list[Fact] = []
    st = live_status()
    ls = read_json(T / "live_summary.json")
    sl = read_json(T / "_SUCCESS_live.json")
    sp = read_json(P / "_SUCCESS_parsed.json")
    src = rel(T / "live_summary.json")
    src_p = rel(P / "_SUCCESS_parsed.json")
    add = out.append
    c = ls["cohort"]
    add(Fact("live_page_change_events", n(c["page_change_events"]), "events", src, st))
    add(Fact("live_revisions", n(sl["row_counts"]["live_revisions.parquet"]), "revisions",
             rel(T / "_SUCCESS_live.json"), st))
    add(Fact("live_dropped_namespace_not_0", n(c["drops"]["namespace_not_0"]), "events", src, st))
    add(Fact("live_dropped_outside_window", n(c["drops"]["outside_window"]), "events", src, st))
    add(Fact("live_dropped_not_edit", n(sum(c["drops"]["kind_not_create_or_edit"].values())), "events",
             src, st))
    rs = ls["revert_share_exact_within_followup"]
    l4 = "live reverts within 4 days; the follow-up is still short"
    add(Fact("live_reverted_4d", n(rs["overall"]["reverted"]), "revisions (reverted within 4 days)", src, st))
    add(Fact("live_revert_rate_pct", pct(rs["overall"]["share"]), "% (reverted within 4 days)", src, st))
    add(Fact("live_revert_rate_human_pct", pct(rs["human_share"]), "% (reverted within 4 days)", src, st))
    for k in ("temporary", "registered", "bot"):
        add(Fact(f"live_revert_rate_{k}_pct", pct(rs["by_user_kind"][k]["share"]), "% (reverted within 4 days)",
                 src, st))
    add(Fact("live_median_T_s", n(ls["median_T_s"]["within_followup"]), f"s ({l4})", src, st))
    add(Fact("live_median_T_h", dec(ls["median_T_s"]["within_followup"] / 3600, 2), f"h ({l4})", src, st))
    q3 = pd.read_csv(R / "mongo_q3_time_to_revert.csv")
    lv = q3[q3["cohort"] == config.COHORT_LIVE]
    for edge, key in ((3600, "1h"), (86400, "1d")):
        cum = lv.loc[lv["bucket_upper_s"] == edge, "cum_share"]
        if len(cum):
            add(Fact(f"live_T_within_{key}_pct", pct(cum.iloc[0]), f"% of {l4}",
                     rel(R / "mongo_q3_time_to_revert.csv"), st))
    k = ls["K_s"]["distinct_reverts_in_links"]
    add(Fact("live_K_median_s", dec(k["p50"], 2), "s", src, st))
    add(Fact("live_K_p90_s", dec(k["p90"], 2), "s", src, st))
    add(Fact("live_K_p99_s", dec(k["p99"], 2), "s", src, st))
    add(Fact("live_revert_risk_coverage_pct", pct(ls["revert_risk_coverage"]["share_edits"]),
             "% of edits", src, st))
    tc = ls["tag_confirmed_share_of_reverted"]
    if not tc.get("complete_ranges_only"):
        raise SystemExit("STOP: live_summary.json does not split the tag confirmation by complete ranges; "
                         "run ingest/label_live.py again")
    which = "complete ranges only"
    for part, key in (("range_size_le_max", "le_15"), ("range_size_gt_max", "gt_15")):
        add(Fact(f"live_tag_confirmed_range_{key}_pct", pct(tc[part]["share"]),
                 f"% of reverted revisions ({which})", src, st))
        add(Fact(f"live_tag_confirmed_range_{key}_n", n(tc[part]["n"]), f"reverted revisions ({which})",
                 src, st))
    inc = tc["range_incomplete"]
    add(Fact("live_tag_confirmed_range_incomplete_pct", pct(inc["share"]),
             "% of reverted revisions whose revert range starts before the capture (size unknown)", src, st))
    add(Fact("live_tag_confirmed_range_incomplete_n", n(inc["n"]),
             "reverted revisions (range starts before the capture; range_size is a lower bound)", src, st))
    nb = ls["newest_id_equals_parent_check"]
    add(Fact("live_revert_events", n(nb["revert_events"]), "revert events (all namespaces)", src, st))
    add(Fact("live_revert_events_newest_not_parent", n(nb["exceptions"]), "revert events", src, st))
    add(Fact("live_newest_meta_dt", utc_text(sl["newest_meta_dt"]), "UTC (newest parsed event)",
             rel(T / "_SUCCESS_live.json"), st))
    add(Fact("live_final_after", utc_text(config.LIVE_FINAL_AFTER), "UTC", "ec-hw2/config.py", FINAL))
    fu = pd.read_parquet(T / "live_revisions.parquet", columns=["followup_s"])["followup_s"]
    add(Fact("live_followup_max_d", dec(fu.max() / 86400, 2), "days", rel(T / "live_revisions.parquet"), st))
    add(Fact("live_followup_min_d", dec(fu.min() / 86400, 2), "days", rel(T / "live_revisions.parquet"), st))
    add(Fact("live_followup_ge_4d_pct", pct((fu >= config.LIVE_FOLLOWUP_S).mean()),
             "% of live edits followed for 4 days or more", rel(T / "live_revisions.parquet"), st))
    streams = sp["streams"]
    short = {config.STREAM_PAGE_CHANGE: "page_change", config.STREAM_REVERT_RISK: "revert_risk",
             config.STREAM_TAGS: "tags"}
    gaps = pd.read_csv(P / "capture_gaps.csv")
    for name, s in streams.items():
        tag = short.get(name, name)
        add(Fact(f"capture_{tag}_first_utc", utc_text(s["first_meta_dt"]), "UTC", src_p, FINAL))
        add(Fact(f"capture_{tag}_last_utc", utc_text(s["last_meta_dt"]), "UTC (newest parsed event)", src_p, st))
        add(Fact(f"capture_{tag}_events", n(s["rows"]), "events", src_p, st))
        add(Fact(f"capture_{tag}_gaps", n(s["gaps"]), "gaps over 120 s", src_p, st))
        add(Fact(f"capture_{tag}_files_cut_short", n(s["cut_short_file_count"]), f"of {s['files_read']} files",
                 src_p, st))
        g = gaps[gaps["stream"] == name]
        add(Fact(f"capture_{tag}_gap_s_total", dec(g["gap_s"].sum(), 0), "s", rel(P / "capture_gaps.csv"), st))
    return out


def facts_mongo() -> list[Fact]:
    """Section 3: MongoDB, Mongo Q1-Q5 and Atlas (notebook 02)."""
    out: list[Fact] = []
    st = live_status()
    add = out.append
    sm = read_json(T / "_SUCCESS_mongo_local.json")
    src = rel(T / "_SUCCESS_mongo_local.json")
    for coll, cnt in sm["rows"].items():
        add(Fact(f"mongo_{coll}_docs", n(cnt), "documents", src, st))
    ph = read_json(T / "_SUCCESS_page_hour.json")
    add(Fact("mongo_page_hour_docs", n(ph["rows"]["page_hour"]), "documents",
             rel(T / "_SUCCESS_page_hour.json"), st))
    add(Fact("mongo_indexes", n(len(sm["indexes"])), "indexes", src, FINAL))
    add(Fact("mongo_index_list", "; ".join(sm["indexes"]), "", src, FINAL))
    # Mongo Q1
    q1 = pd.read_csv(R / "mongo_q1_revert_rate_by_hour.csv")
    s1 = rel(R / "mongo_q1_revert_rate_by_hour.csv")
    h1 = q1[q1["cohort"] == config.COHORT_HISTORY]
    for k in ("temporary", "registered"):
        d = h1[h1["user_kind"] == k]
        add(Fact(f"mongo_q1_history_{k}_hourly_min_pct", pct(d["revert_rate"].min()), "%", s1, FINAL))
        add(Fact(f"mongo_q1_history_{k}_hourly_max_pct", pct(d["revert_rate"].max()), "%", s1, FINAL))
        peak = d.sort_values(["revert_rate", "hour_utc"], ascending=[False, True]).iloc[0]
        add(Fact(f"mongo_q1_history_{k}_peak_hour_utc", str(int(peak["hour_utc"])), "hour (UTC)", s1, FINAL))
    g = h1.groupby("user_kind")[["edits", "reverted"]].sum()
    ratio = (g.loc["temporary", "reverted"] / g.loc["temporary", "edits"]) / (
        g.loc["registered", "reverted"] / g.loc["registered", "edits"])
    add(Fact("mongo_q1_history_temporary_vs_registered_ratio", dec(ratio, 1), "times", s1, FINAL))
    # Mongo Q2
    q2 = pd.read_csv(R / "mongo_q2_top_contested_pages.csv")
    s2 = rel(R / "mongo_q2_top_contested_pages.csv")
    top = q2.iloc[0]
    add(Fact("mongo_q2_top_page_title", top["page_title"], "", s2, FINAL))
    add(Fact("mongo_q2_top_page_id", str(int(top["page_id"])), "", s2, FINAL))
    add(Fact("mongo_q2_top_page_score", f"{top['score']:.6f}", "revert actions per human edit", s2, FINAL))
    add(Fact("mongo_q2_top_page_revert_actions", n(top["revert_actions"]), "revert actions", s2, FINAL))
    add(Fact("mongo_q2_top_page_edits", n(top["edits"]), "human edits", s2, FINAL))
    add(Fact("mongo_q2_top5_titles", "; ".join(q2["page_title"].head(5)), "", s2, FINAL))
    add(Fact("mongo_q2_contested_in_top20", n(q2["contested"].astype(str).str.lower().eq("true").sum()),
             "pages", s2, FINAL))
    # Mongo Q3: three series with their own horizon. Compare 'live' only with 'history_4d'.
    q3 = pd.read_csv(R / "mongo_q3_time_to_revert.csv")
    s3 = rel(R / "mongo_q3_time_to_revert.csv")
    series = ((config.COHORT_HISTORY, FINAL, "history reverts within 20 days"),
              ("history_4d", FINAL, "history reverts within 4 days; compare with live"),
              (config.COHORT_LIVE, st, "live reverts within 4 days; the follow-up is still short"))
    for cohort, status, what in series:
        d = q3[q3["cohort"] == cohort].set_index("bucket")
        add(Fact(f"mongo_q3_{cohort}_lt_1min_pct", pct(d.loc["<1 min", "share"]), f"% of {what}", s3, status))
        add(Fact(f"mongo_q3_{cohort}_buckets", n(len(d)), f"non-empty buckets ({what})", s3, status))
    # Mongo Q4
    q4 = pd.read_csv(R / "mongo_q4_bot_vs_human.csv")
    s4 = rel(R / "mongo_q4_bot_vs_human.csv")
    made = q4[q4["part"] == "made_by_reverter_kind"].set_index("kind")
    recv = q4[q4["part"] == "received_by_author_kind"].set_index("kind")
    rate = q4[q4["part"] == "edit_revert_rate"].set_index("kind")
    add(Fact("mongo_q4_revert_actions_total", n(made["revert_actions"].sum()), "revert actions", s4, FINAL))
    add(Fact("mongo_q4_reverted_revisions_total", n(recv["reverted_revisions"].sum()), "revisions", s4, FINAL))
    for k in ("bot", "registered", "temporary"):
        add(Fact(f"mongo_q4_made_by_{k}_pct", pct(made.loc[k, "share"]), "% of revert actions", s4, FINAL))
        add(Fact(f"mongo_q4_made_by_{k}_revisions_pct",
                 pct(made.loc[k, "reverted_revisions"] / made["reverted_revisions"].sum()),
                 "% of reverted revisions", s4, FINAL))
        add(Fact(f"mongo_q4_received_by_{k}_pct", pct(recv.loc[k, "share"]), "% of reverted revisions",
                 s4, FINAL))
    add(Fact("mongo_q4_bot_edit_revert_rate_pct", pct(rate.loc["bot", "revert_rate"]), "%", s4, FINAL))
    add(Fact("mongo_q4_human_edit_revert_rate_pct", pct(rate.loc["human", "revert_rate"]), "%", s4, FINAL))
    # Mongo Q5 (known-by)
    q5 = pd.read_csv(R / "mongo_q5_truth_lag_preview.csv")
    s5 = rel(R / "mongo_q5_truth_lag_preview.csv")
    for cohort, status in ((config.COHORT_HISTORY, FINAL), (config.COHORT_LIVE, st)):
        d = q5[(q5["cohort"] == cohort) & (q5["user_kind"] == "all")].set_index("wait")
        add(Fact(f"mongo_q5_{cohort}_reverts_4d", n(d["n_reverted_4d"].iloc[0]), "revisions", s5, status))
        add(Fact(f"mongo_q5_{cohort}_revert_rate_4d_pct", pct(d["revert_rate_4d"].iloc[0]), "%", s5, status))
        for w, key in (("1 min", "1min"), ("1 h", "1h"), ("1 d", "1d")):
            add(Fact(f"mongo_q5_{cohort}_known_{key}_pct", pct(d.loc[w, "share_known"]),
                     "% of 4-day reverts", s5, status))
        for k in ("temporary", "registered"):
            dk = q5[(q5["cohort"] == cohort) & (q5["user_kind"] == k) & (q5["wait"] == "1 h")]
            if len(dk):
                add(Fact(f"mongo_q5_{cohort}_known_1h_{k}_pct", pct(dk["share_known"].iloc[0]),
                         "% of 4-day reverts", s5, status))
    # Timings
    ms = pd.read_csv(R / "mongo_summary.csv")
    live_based = {"q1_revert_rate_by_hour", "q5_truth_lag_preview", "q5_risk_deciles"}
    in_cmp = comparison_query_names()
    for _, r in ms.iterrows():
        unit = f"ms (median of {int(r['runs'])}" + (f"; {SINGLE_ENGINE_NOTE})" if r["query"] in in_cmp else ")")
        add(Fact(f"mongo_ms_{r['query']}", dec(r["median_ms"], 1), unit,
                 rel(R / "mongo_summary.csv"), st if r["query"] in live_based else FINAL))
    # Atlas size estimate (history cohort only, without comment)
    try:
        import load_mongo
        est = load_mongo.estimate_atlas_size(load_mongo.local_chart_documents())
        add(Fact("atlas_estimate_mb", dec(est["total_mb"], 1), "MB (budget 400, limit 512)",
                 "ec-hw2/load_mongo.py --target atlas --estimate-only", FINAL))
    except Exception as exc:     # the estimate is nice to have; report and go on
        print(f"skipped the Atlas estimate: {type(exc).__name__}: {exc}")
    return out


def facts_neo4j() -> list[Fact]:
    """Section 4: the graph and Cypher Q1-Q5 (notebook 03)."""
    out: list[Fact] = []
    add = out.append
    neo_path = config.DATA_DIR / "neo4j" / "_SUCCESS_load_neo4j_local.json"
    neo = read_json(neo_path)
    for label in ("Editor", "Page", "EDITED", "REVERTED"):
        add(Fact(f"neo4j_{label.lower()}_count", n(neo["counts"][label]),
                 "nodes" if label[0].isupper() and label[1].islower() else "relationships",
                 rel(neo_path), FINAL))
    add(Fact("contested_pages_total", n(neo["counts"]["contested Page"]), "pages", rel(neo_path), FINAL))
    t1 = pd.read_csv(R / "cypher_q1_mutual_reverts_total.csv").iloc[0]
    s1 = rel(R / "cypher_q1_mutual_reverts_total.csv")
    add(Fact("cypher_q1_mutual_pairs", n(t1["mutual_pairs"]), "pairs", s1, FINAL))
    add(Fact("cypher_q1_pages", n(t1["pages"]), "pages", s1, FINAL))
    add(Fact("cypher_q1_editors", n(t1["editors"]), "editors", s1, FINAL))
    add(Fact("cypher_q1_pairs_with_bot", n(t1["pairs_with_bot"]), "pairs", s1, FINAL))
    pairs = pd.read_csv(R / "cypher_q1_mutual_reverts.csv")
    top20 = pd.read_csv(R / "mongo_q2_top_contested_pages.csv")["page_id"]
    on_top = pairs[pairs["page_id"].isin(top20)]
    add(Fact("top20_pages_with_mutual_pair", n(on_top["page_id"].nunique()), "of 20 pages",
             "ec-hw2/results/cypher_q1_mutual_reverts.csv + mongo_q2_top_contested_pages.csv", FINAL))
    add(Fact("top20_mutual_pairs", n(len(on_top)), f"of {len(pairs)} pairs",
             "ec-hw2/results/cypher_q1_mutual_reverts.csv + mongo_q2_top_contested_pages.csv", FINAL))
    add(Fact("top20_mutual_pairs_pct", pct(len(on_top) / len(pairs)), "% of mutual pairs",
             "ec-hw2/results/cypher_q1_mutual_reverts.csv + mongo_q2_top_contested_pages.csv", FINAL))
    # Cypher Q2. PageRank values only from a converged run (run_cypher.py checks didConverge).
    sq = read_json(R / "_SUCCESS_cypher_queries.json")
    conv = [c for c in sq.get("checks", []) if str(c.get("name", "")).startswith("PageRank converged")]
    if not conv or not all(c.get("ok") for c in conv):
        raise SystemExit("STOP: results/_SUCCESS_cypher_queries.json does not show a converged PageRank; "
                         "run queries/run_cypher.py again before you build FACTS.md")
    iters = max(int(c.get("iterations", 0)) for c in conv)
    pr_unit = f"PageRank score (REVERSE projection, converged after {iters} iterations)"
    q2 = pd.read_csv(R / "cypher_q2_central_reverters.csv")
    s2 = rel(R / "cypher_q2_central_reverters.csv")
    add(Fact("cypher_q2_pagerank_iterations", n(iters), "iterations until PageRank converged",
             rel(R / "_SUCCESS_cypher_queries.json"), FINAL))
    add(Fact("cypher_q2_top_pagerank_editor", q2.iloc[0]["editor"], f"({q2.iloc[0]['kind']})", s2, FINAL))
    add(Fact("cypher_q2_top_pagerank", dec(q2.iloc[0]["pagerank"], 2), pr_unit, s2, FINAL))
    add(Fact("cypher_q2_top_reverts_made", n(q2.iloc[0]["reverts_made"]), "revert actions", s2, FINAL))
    add(Fact("cypher_q2_bots_in_top20", n((q2["kind"] == "bot").sum()), "of 20 (by PageRank)", s2, FINAL))
    # PageRank means "reverts editors who are themselves active reverters", not "reverts a lot":
    # the top-20 editor with the fewest revert actions shows it.
    few = q2.assign(rank=range(1, len(q2) + 1)).sort_values(["reverts_made", "rank"]).iloc[0]
    add(Fact("cypher_q2_pagerank_fewest_reverts_editor", few["editor"], f"({few['kind']}), in the PageRank top 20",
             s2, FINAL))
    add(Fact("cypher_q2_pagerank_fewest_reverts_rank", n(few["rank"]), "rank by PageRank", s2, FINAL))
    add(Fact("cypher_q2_pagerank_fewest_reverts_made", n(few["reverts_made"]), "revert actions", s2, FINAL))
    hu = pd.read_csv(R / "cypher_q2_central_reverters_humans.csv").iloc[0]
    add(Fact("cypher_q2_top_human_pagerank", dec(hu["pagerank"], 2), f"{pr_unit}, {hu['editor']}",
             rel(R / "cypher_q2_central_reverters_humans.csv"), FINAL))
    bd = pd.read_csv(R / "cypher_q2_central_reverters_by_degree.csv").iloc[0]
    sd = rel(R / "cypher_q2_central_reverters_by_degree.csv")
    add(Fact("cypher_q2_top_by_degree_editor", bd["editor"], f"({bd['kind']}), who reverts the most", sd, FINAL))
    add(Fact("cypher_q2_top_by_degree_out_degree", n(bd["out_degree"]),
             "REVERTED relationships out (one per reverted editor and page)", sd, FINAL))
    add(Fact("cypher_q2_top_by_degree_reverts_made", n(bd["reverts_made"]), "revert actions", sd, FINAL))
    # Cypher Q3: most Louvain communities are single editors; the large ones are mostly stars.
    ls = pd.read_csv(R / "cypher_q3_conflict_communities_louvain_stats.csv").iloc[0]
    s3 = rel(R / "cypher_q3_conflict_communities_louvain_stats.csv")
    add(Fact("cypher_q3_louvain_communities", n(ls["communities"]),
             "communities (all; most are 1 editor with no revert)", s3, FINAL))
    add(Fact("cypher_q3_louvain_modularity", dec(ls["modularity"], 4), "", s3, FINAL))
    cz = pd.read_csv(R / "cypher_q3_conflict_communities_community_sizes.csv").iloc[0]
    szs = rel(R / "cypher_q3_conflict_communities_community_sizes.csv")
    add(Fact("cypher_q3_communities_2plus", n(cz["communities_2plus"]), "communities with 2 or more editors",
             szs, FINAL))
    add(Fact("cypher_q3_communities_1", n(cz["communities_1"]), "communities of 1 editor (no revert)", szs, FINAL))
    cc = pd.read_csv(R / "cypher_q3_conflict_communities.csv")
    c1 = cc.iloc[0]
    sc = rel(R / "cypher_q3_conflict_communities.csv")
    add(Fact("cypher_q3_largest_community_editors", n(c1["editors"]), "editors", sc, FINAL))
    add(Fact("cypher_q3_largest_community_reverts", n(c1["reverts"]), "revert actions inside the community", sc,
             FINAL))
    add(Fact("cypher_q3_largest_community_top_reverter", str(c1["top_reverters"]).split(" | ")[0],
             "the editor with the most revert actions in the community", sc, FINAL))
    add(Fact("cypher_q3_largest_community_star_share_pct", dec(100 * c1["star_share"], 1),
             "% of the community's REVERTED relationships that touch its top reverter", sc, FINAL))
    add(Fact("cypher_q3_top10_star_share_min_pct", dec(100 * cc["star_share"].min(), 1),
             f"% (star share, lowest of the top {len(cc)} communities)", sc, FINAL))
    add(Fact("cypher_q3_top10_star_share_max_pct", dec(100 * cc["star_share"].max(), 1),
             f"% (star share, highest of the top {len(cc)} communities)", sc, FINAL))
    add(Fact("cypher_q3_largest_community_top_page", c1["top_page"],
             "the page with the most revert actions in the community (see the share)", sc, FINAL))
    add(Fact("cypher_q3_largest_community_top_page_share_pct", pct(c1["top_page_reverts"] / c1["reverts"]),
             "% of the community's revert actions", sc, FINAL))
    w1 = pd.read_csv(R / "cypher_q3_conflict_communities_wcc_largest.csv").iloc[0]
    add(Fact("cypher_q3_largest_wcc_editors", n(w1["editors"]), "editors",
             rel(R / "cypher_q3_conflict_communities_wcc_largest.csv"), FINAL))
    ws = pd.read_csv(R / "cypher_q3_conflict_communities_wcc_sizes.csv")
    sw = rel(R / "cypher_q3_conflict_communities_wcc_sizes.csv")
    alone = ws[ws["component_size"].str.startswith("1 ")].iloc[0]
    big = ws.iloc[-1]
    add(Fact("cypher_q3_editors_without_revert_pct", pct(alone["share_of_editors"]), "% of editors", sw, FINAL))
    add(Fact("cypher_q3_largest_wcc_pct", pct(big["share_of_editors"]), "% of editors", sw, FINAL))
    q4 = pd.read_csv(R / "cypher_q4_pages_most_warring_editors.csv").iloc[0]
    s4 = rel(R / "cypher_q4_pages_most_warring_editors.csv")
    add(Fact("cypher_q4_top_page_title", q4["page_title"], "", s4, FINAL))
    add(Fact("cypher_q4_top_page_warring_editors", n(q4["warring_editors"]), "editors", s4, FINAL))
    add(Fact("cypher_q4_top_page_mutual_pairs", n(q4["mutual_pairs"]), "pairs", s4, FINAL))
    q5 = pd.read_csv(R / "cypher_q5_two_hop_contested.csv").iloc[0]
    add(Fact("cypher_q5_top_pair_shared_pages", n(q5["shared_contested_pages"]), "contested pages",
             rel(R / "cypher_q5_two_hop_contested.csv"), FINAL))
    cs = pd.read_csv(R / "cypher_summary.csv")
    in_cmp = comparison_query_names()
    for _, r in cs[cs["result"] == "main"].iterrows():
        unit = f"ms (median of {int(r['runs'])}" + (f"; {SINGLE_ENGINE_NOTE})" if r["query"] in in_cmp else ")")
        add(Fact(f"cypher_ms_{r['query']}", dec(r["median_ms"], 1), unit, rel(R / "cypher_summary.csv"), FINAL))
    return out


def facts_comparison() -> list[Fact]:
    """Section 5: the 3-engine comparison and the sharding demo (notebook 04)."""
    out: list[Fact] = []
    add = out.append
    cmp = pd.read_csv(R / "comparison.csv")
    sc = read_json(R / "_SUCCESS_comparison.json")
    src = rel(R / "comparison.csv")
    # Timings come from comparison.csv only. They are FINAL only when every row says 'final'.
    labels = set(cmp["timing_label"].astype(str))
    label = labels.pop() if len(labels) == 1 else "mixed"
    t_status = FINAL if label == "final" else PROVISIONAL
    pain = pd.read_csv(config.HW2_DIR / "comparison" / "pain.csv")
    pain = pain.set_index(["question", "engine"])
    src_pain = "ec-hw2/comparison/pain.csv"
    qkey = {"top contested pages": "top", "mutual reverts": "mutual"}
    runs = sorted({int(x) for x in cmp["runs"]})
    rounds = sorted({int(x) for x in cmp["rounds"]})
    for _, r in cmp.iterrows():
        k = f"{qkey[r['question']]}_{r['engine'].lower()}"
        add(Fact(f"cmp_loc_{k}", n(r["lines_of_code"]), "lines (non-blank, non-comment)", src, FINAL))
        add(Fact(f"cmp_chars_{k}", n(r["code_chars"]), "characters of query code", src, FINAL))
        add(Fact(f"cmp_bracket_lines_{k}", n(r["bracket_only_lines"]), "lines with only brackets or commas", src,
                 FINAL))
        add(Fact(f"cmp_ms_{k}", dec(r["median_ms"], 1),
                 f"ms ({r['timing_label']}, median of {int(r['runs'])} runs in {int(r['rounds'])} rounds)",
                 src, t_status))
        add(Fact(f"cmp_ms_min_{k}", dec(r["min_ms"], 1), f"ms (fastest of {int(r['runs'])} runs)", src, t_status))
        add(Fact(f"cmp_ms_max_{k}", dec(r["max_ms"], 1), f"ms (slowest of {int(r['runs'])} runs)", src, t_status))
        fast = r["faster_than"] if isinstance(r["faster_than"], str) and r["faster_than"].strip() else "none"
        add(Fact(f"cmp_faster_than_{k}", fast, "engines it beats: its slowest run is faster than their fastest",
                 src, t_status))
        p = pain.loc[(r["question"], r["engine"])]
        draft = pain_is_draft(p["scored_by"])
        add(Fact(f"cmp_pain_{k}", n(p["score"]),
                 "of 5 (draft by Claude Code; the Comparison+viz owner re-scores it)" if draft
                 else f"of 5 (scored by {p['scored_by']})", src_pain, PROVISIONAL if draft else FINAL))
        add(Fact(f"cmp_rows_{k}", n(r["result_rows"]), "rows", src, FINAL))
    scorers = sorted({str(s) for s in pain["scored_by"].fillna("")})
    any_draft = any(pain_is_draft(s) for s in pain["scored_by"])
    add(Fact("cmp_pain_scored_by", "; ".join(scorers), "who scored the modeling pain", src_pain,
             PROVISIONAL if any_draft else FINAL))
    add(Fact("cmp_runs_per_query", " / ".join(str(x) for x in runs), "timed runs per query", src, FINAL))
    add(Fact("cmp_rounds", " / ".join(str(x) for x in rounds), "rounds (the engines take turns)", src, FINAL))
    load = sc.get("load_average_start")
    if load:
        add(Fact("cmp_load_average_start", dec(load[0], 2),
                 f"1-minute load average when the timing started (idle below {sc.get('idle_load_threshold', 2.0)})",
                 rel(R / "_SUCCESS_comparison.json"), t_status))
    add(Fact("cmp_all_identical", "yes" if sc["all_identical"] else "no", "", rel(R / "_SUCCESS_comparison.json"),
             FINAL))
    add(Fact("cmp_timing_label", label, "draft timings are PROVISIONAL", src, t_status))
    # The extra row: SQLite on a pre-aggregated TEMP table (not compared; like Neo4j's REVERTED input).
    extra_path = R / "comparison_extra.csv"
    if extra_path.exists():
        ex = pd.read_csv(extra_path).iloc[0]
        se = rel(extra_path)
        add(Fact("cmp_ms_mutual_sqlite_preagg", dec(ex["median_ms"], 1),
                 f"ms ({ex['timing_label']}, median of {int(ex['runs'])}; extra row, not compared)", se, t_status))
        add(Fact("cmp_ms_min_mutual_sqlite_preagg", dec(ex["min_ms"], 1), "ms (fastest run; extra row)", se,
                 t_status))
        add(Fact("cmp_ms_max_mutual_sqlite_preagg", dec(ex["max_ms"], 1), "ms (slowest run; extra row)", se,
                 t_status))
        add(Fact("cmp_setup_ms_mutual_sqlite_preagg", dec(ex["setup_ms"], 1),
                 "ms to build the TEMP table of grouped triples (not timed in the median)", se, t_status))
        add(Fact("cmp_loc_mutual_sqlite_preagg", n(ex["lines_of_code"]), "lines (the timed query only)", se, FINAL))
    sh = read_json(R / "_SUCCESS_sharding.json")
    ss = rel(R / "_SUCCESS_sharding.json")
    rows = sh["rows"]
    total = rows["documents_copied"]
    add(Fact("shard_key", '{"page.id": "hashed"}', "", "ec-hw2/scaleout/SHARDING.md", FINAL))
    add(Fact("shard_documents", n(total), "documents", ss, FINAL))
    for name in ("shard1rs", "shard2rs"):
        add(Fact(f"shard_{name}_docs", n(rows[f"documents_{name}"]), "documents", ss, FINAL))
        add(Fact(f"shard_{name}_pct", pct(rows[f"documents_{name}"] / total), "% of documents", ss, FINAL))
    add(Fact("shard_route_one_page", sh["routing"]["history of one page"], "", ss, FINAL))
    add(Fact("shard_route_one_editor", sh["routing"]["all edits of one editor"], "", ss, FINAL))
    add(Fact("shard_checks_ok", f"{sum(c['ok'] for c in sh['checks'])} of {len(sh['checks'])}", "checks", ss, FINAL))
    rev = pd.read_parquet(T / "history_revisions.parquet", columns=["page_id", "page_title"])
    sizes = rev.groupby("page_id").size()
    big = int(sizes.idxmax())
    add(Fact("shard_biggest_page_title", rev.loc[rev["page_id"] == big, "page_title"].iloc[0], "",
             rel(T / "history_revisions.parquet"), FINAL))
    add(Fact("shard_biggest_page_revisions", n(sizes.max()), "revisions", rel(T / "history_revisions.parquet"),
             FINAL))
    return out


def facts_truth_lag() -> list[Fact]:
    """Section 6: late reverts and the RAG-crawler decision table (notebook 05)."""
    out: list[Fact] = []
    st = live_status()
    add = out.append
    lr = read_json(T / "late_reverts_summary.json")
    src = rel(T / "late_reverts_summary.json")
    alln, ns0 = "all namespaces", "namespace 0 only, like the history cohort"
    add(Fact("late_reverts_rows", n(lr["rows"]), f"September revisions, {alln} (lower bound)", src, st))
    add(Fact("late_reverts_rows_ns0", n(lr["rows_ns0"]), f"September revisions, {ns0} (lower bound)", src, st))
    for c in config.LATE_CLASSES:
        add(Fact(f"late_reverts_{c}", n(lr["by_class"].get(c, 0)), f"revisions, {alln} (lower bound)", src, st))
        add(Fact(f"late_reverts_{c}_ns0", n(lr["by_class_ns0"].get(c, 0)), f"revisions, {ns0} (lower bound)",
                 src, st))
        add(Fact(f"late_reverts_in_history_cohort_{c}", n(lr["in_history_cohort_by_class"].get(c, 0)),
                 "revisions in the history cohort (lower bound)", src, st))
    add(Fact("late_reverts_in_history_cohort", n(lr["in_history_cohort"]),
             "revisions in the history cohort (lower bound)", src, st))
    add(Fact("late_reverts_pages", n(lr["distinct_pages"]), f"pages, {alln}", src, st))
    add(Fact("late_reverts_pages_ns0", n(lr["distinct_pages_ns0"]), f"pages, {ns0}", src, st))
    add(Fact("late_reverts_reverting_actions", n(lr["distinct_reverting_actions"]), f"revert actions, {alln}",
             src, st))
    add(Fact("late_reverts_reverting_actions_ns0", n(lr["distinct_reverting_actions_ns0"]),
             f"revert actions, {ns0}", src, st))
    add(Fact("late_reverts_median_age_exact_d", dec(lr["median_age_days_by_class"]["exact"], 1),
             f"days ({alln})", src, st))
    add(Fact("late_reverts_restored_later", n(lr["restored_later"].get("True", 0)), f"revisions ({alln})", src, st))
    dt = decision_table()
    sd = rel(R / "mongo_q5_risk_deciles.csv")
    dec_rows = dt[dt["group"] != "no score"]
    top, bottom = dec_rows.iloc[-1], dec_rows.iloc[0]
    add(Fact("risk_top_decile_score_min", dec(float(top["risk_score"].split("-")[0]), 2), "revert-risk score",
             sd, st))
    add(Fact("risk_top_decile_edits", n(top["edits"]), "edits", sd, st))
    add(Fact("risk_top_decile_revert_rate_pct", dec(top["revert_rate_4d_pct"], 2), "% reverted within 4 days",
             sd, st))
    add(Fact("risk_bottom_decile_revert_rate_pct", dec(bottom["revert_rate_4d_pct"], 2), "% reverted within 4 days",
             sd, st))
    for w in ("1h", "1d"):
        add(Fact(f"risk_top_decile_visible_{w}_pct", dec(top[f"visible_{w}_pct"], 2), "% of 4-day reverts", sd, st))
        add(Fact(f"risk_top_decile_visible_{w}_ci", f"{top[f'visible_{w}_lo']:.2f}-{top[f'visible_{w}_hi']:.2f}",
                 "% (Wilson 95%)", sd, st))
        add(Fact(f"risk_top_decile_later_{w}_pct", dec(top[f"later_{w}_pct"], 2),
                 "% of edits still clean at the wait", sd, st))
        add(Fact(f"risk_top_decile_later_{w}_ci", f"{top[f'later_{w}_lo']:.2f}-{top[f'later_{w}_hi']:.2f}",
                 "% (Wilson 95%)", sd, st))
        add(Fact(f"risk_bottom_decile_later_{w}_pct", dec(bottom[f"later_{w}_pct"], 3),
                 "% of edits still clean at the wait", sd, st))
    top2 = dec_rows.tail(2)["reverts_4d"].sum() / dec_rows["reverts_4d"].sum()
    add(Fact("risk_top2_deciles_share_of_reverts_pct", pct(top2), "% of 4-day reverts (scored edits)", sd, st))
    # The 'no score' group mixes two kinds of edits; split it (from the Parquet tables).
    ns = no_score_split()
    no = dt[dt["group"] == "no score"].iloc[0]
    if (ns["edits"], ns["reverted"]) != (int(no["edits"]), int(no["reverts_4d"])):
        raise SystemExit(f"STOP: the 'no score' split ({ns['edits']:,} edits, {ns['reverted']:,} reverted) does not "
                         f"match Mongo Q5 ({int(no['edits']):,}, {int(no['reverts_4d']):,}); rebuild the results")
    sn = rel(T / "live_revisions.parquet") + " + live_revert_links.parquet"
    add(Fact("risk_no_score_edits", n(ns["edits"]), "edits with no revert-risk score", sd, st))
    add(Fact("risk_no_score_revert_rate_pct", dec(no["revert_rate_4d_pct"], 2),
             "% reverted within 4 days (page creations and edits without a captured score, mixed)", sd, st))
    add(Fact("risk_no_score_page_creations", n(ns["creations"]),
             "page creations (no page creation has a score)", sn, st))
    add(Fact("risk_no_score_page_creations_reverted", n(ns["creations_reverted"]),
             "page creations reverted within 4 days", sn, st))
    add(Fact("risk_no_score_not_captured", n(ns["not_captured"]),
             "edits whose score event was not captured", sn, st))
    add(Fact("risk_no_score_not_captured_reverted", n(ns["not_captured_reverted"]),
             "of those edits, reverted within 4 days", sn, st))
    add(Fact("risk_no_score_not_captured_revert_rate_pct",
             pct(ns["not_captured_reverted"] / ns["not_captured"]) if ns["not_captured"] else "0.00",
             "% reverted within 4 days (edits whose score event was not captured)", sn, st))
    return out


def no_score_split() -> dict:
    """The live edits without a revert-risk score: page creations, and edits whose score was not captured.

    A page creation has parent_id 0 or null. 'reverted' = a live revert link with
    within_followup (reverted within 4 days), the label of the Mongo Q5 risk deciles.
    """
    lv = pd.read_parquet(T / "live_revisions.parquet", columns=["rev_id", "parent_id", "revert_risk"])
    links = pd.read_parquet(T / "live_revert_links.parquet", columns=["reverted_rev_id", "within_followup"])
    reverted = set(links.loc[links["within_followup"], "reverted_rev_id"])
    no = lv[lv["revert_risk"].isna()]
    creation = no["parent_id"].isna() | (no["parent_id"] == 0)
    is_rev = no["rev_id"].isin(reverted)
    return {"edits": len(no), "reverted": int(is_rev.sum()),
            "creations": int(creation.sum()), "creations_reverted": int((creation & is_rev).sum()),
            "not_captured": int((~creation).sum()), "not_captured_reverted": int((~creation & is_rev).sum())}


def facts_examples() -> list[Fact]:
    """Section 7: two example pages for the Motivation (history cohort, pseudonyms)."""
    out: list[Fact] = []
    add = out.append
    src = rel(T / "history_revisions.parquet")
    n_hex = alias_hex()
    for tag, pid in (("slow", EXAMPLE_SLOW_PAGE_ID), ("fast", EXAMPLE_FAST_PAGE_ID)):
        s = timeline_summary(page_timeline(pid, n_hex))
        add(Fact(f"example_{tag}_page_title", s["title"], "", src, FINAL))
        add(Fact(f"example_{tag}_page_id", str(pid), "", src, FINAL))
        add(Fact(f"example_{tag}_edits", n(s["edits"]), "revisions (history cohort)", src, FINAL))
        add(Fact(f"example_{tag}_editor_kinds", s["editor_kinds"], "revisions per user kind", src, FINAL))
        add(Fact(f"example_{tag}_reverted", n(s["reverted"]), "revisions reverted within 20 d", src, FINAL))
        add(Fact(f"example_{tag}_T_min_s", n(s["T_min_s"]), "s", src, FINAL))
        add(Fact(f"example_{tag}_T_median_s", n(s["T_median_s"]), "s", src, FINAL))
        add(Fact(f"example_{tag}_T_max_s", n(s["T_max_s"]), "s", src, FINAL))
        add(Fact(f"example_{tag}_first_edit_utc", s["first_utc"], "", src, FINAL))
        add(Fact(f"example_{tag}_last_revert_utc", s["last_revert_utc"], "", src, FINAL))
        add(Fact(f"example_{tag}_span_h", dec(s["span_h"], 1), "h (first edit to last revert)", src, FINAL))
        add(Fact(f"example_{tag}_first_steps", s["first_steps"], "timeline (pseudonyms)", src, FINAL))
    return out


SECTIONS = [
    ("Data and cohorts (notebook 01)", facts_data),
    ("Live cohort and capture (notebook 01)", facts_live),
    ("MongoDB (notebook 02)", facts_mongo),
    ("Neo4j (notebook 03)", facts_neo4j),
    ("Comparison and sharding (notebook 04)", facts_comparison),
    ("Truth lag: late reverts and the decision table (notebook 05)", facts_truth_lag),
    ("Example pages for the Motivation", facts_examples),
]


def all_facts() -> list[tuple[str, Fact]]:
    rows = []
    for section, fn in SECTIONS:
        for f in fn():
            rows.append((section, f))
    keys = [f.key for _, f in rows]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        raise SystemExit(f"STOP: duplicate fact keys: {sorted(dup)}")
    return rows


# --------------------------------------------------------------------------
# Writing and reading FACTS.md
# --------------------------------------------------------------------------
def md_cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(rows: list[tuple[str, Fact]]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st = live_status()
    lines = [
        "# FACTS: the key numbers of EC HW2",
        "",
        f"Made by `ec-hw2/report/build_facts.py` on {now} ({config.DATA_VERSION}). Do not edit by hand: "
        "run the script again.",
        "",
        "- Use these numbers in the report. Each notebook checks its numbers against this table in its last cell.",
        "- **FINAL**: the number will not change. **PROVISIONAL**: it depends on the live cohort, whose stream "
        f"labels are final after {utc_text(config.LIVE_FINAL_AFTER)} (Mon 2026-10-26 5:05 PM PT); or it is a "
        "comparison timing that `results/comparison.csv` labels draft; or it is a modeling-pain score that is "
        "still a draft by Claude Code (`comparison/pain.csv`). "
        f"Live cohort now: **{st}** (newest parsed event: {utc_text(read_json(T / '_SUCCESS_live.json')['newest_meta_dt'])}).",
        "- Horizons: history keys count reverts within 20 days, unless the key ends in `_4d` (within 4 days). "
        "Live keys count reverts within 4 days, and the live follow-up is still short. Compare the live cohort "
        "only with the `_4d` history keys.",
        "- Comparison timings come only from `results/comparison.csv` (`cmp_ms_*`: median, min and max). The "
        "`mongo_ms_*` and `cypher_ms_*` times of the same queries are single-engine runs: do not compare them.",
        "- Percent values are in percent (7.43 means 7.43%). Times are UTC. Human editors appear only as pseudonyms.",
        "- Where each number is shown: `history_`, `wikistats_`, `live_`, `capture_` and `example_` in notebook 01; "
        "`mongo_` and `atlas_` in notebook 02; `neo4j_`, `cypher_`, `contested_` and `top20_` in notebook 03; "
        "`cmp_` and `shard_` in notebook 04; `late_` and `risk_` in notebook 05. `example_` is for the Motivation. "
        "Numbers in the notebook text carry a fact marker; `report/sync_notebook_text.py` copies them from here.",
        "",
        "| key | value | unit | source file | status |",
        "|---|---|---|---|---|",
    ]
    for _, f in rows:
        lines.append(f"| {md_cell(f.key)} | {md_cell(f.value)} | {md_cell(f.unit)} | {md_cell(f.source)} | "
                     f"{f.status} |")
    return "\n".join(lines) + "\n"


def read_facts(path: Path = FACTS_PATH) -> dict[str, dict]:
    """FACTS.md as {key: {value, unit, source, status}}."""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| key ") or line.startswith("|---"):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) < 5:
            continue
        out[cells[0]] = {"value": cells[1], "unit": cells[2], "source": cells[3], "status": cells[4]}
    return out


_NUMBER = re.compile(r"^[+-]?\d[\d,]*(\.\d+)?$")


def same_value(fact_value: str, computed) -> tuple[bool, str]:
    """Is the notebook value equal to the FACTS value, at the precision FACTS shows?

    Numbers are rounded to the number of decimals in FACTS.md ("7.43" -> 2).
    Text must be equal. Returns (equal?, the notebook value as text).
    """
    fv = fact_value.strip()
    if _NUMBER.match(fv) and not isinstance(computed, str):
        if computed is None or (isinstance(computed, float) and pd.isna(computed)):
            return False, "missing"
        d = len(fv.split(".")[1]) if "." in fv else 0
        shown = f"{float(computed):.{d}f}"
        want = f"{float(fv.replace(',', '')):.{d}f}"
        sign = "+" if fv.startswith("+") and float(computed) >= 0 else ""
        return shown == want, sign + (f"{float(computed):,.{d}f}" if d else f"{int(round(float(computed))):,}")
    if isinstance(computed, bool):
        computed = "yes" if computed else "no"
    return str(computed).strip() == fv, str(computed)


def check(computed: dict, path: Path = FACTS_PATH) -> pd.DataFrame:
    """Compare notebook numbers with FACTS.md. Prints one line per key and a total."""
    facts = read_facts(path)
    rows = []
    for key, value in computed.items():
        f = facts.get(key)
        if f is None:
            rows.append({"key": key, "FACTS.md": "(missing)", "notebook": str(value), "status": "",
                         "result": "DIFFERENT"})
            continue
        ok, shown = same_value(f["value"], value)
        rows.append({"key": key, "FACTS.md": f["value"], "notebook": shown, "status": f["status"],
                     "result": "OK" if ok else "DIFFERENT"})
    df = pd.DataFrame(rows)
    bad = int((df["result"] != "OK").sum()) if len(df) else 0
    from tabulate import tabulate
    print(tabulate(df, headers="keys", tablefmt="github", showindex=False, disable_numparse=True))
    print()
    print("OK: all {} numbers match FACTS.md".format(len(df)) if bad == 0 else
          f"DIFFERENT: {bad} of {len(df)} numbers do not match FACTS.md")
    return df


def write_text_safely(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main() -> None:
    rows = all_facts()
    write_text_safely(render(rows), FACTS_PATH)
    by_status = {}
    for _, f in rows:
        by_status[f.status] = by_status.get(f.status, 0) + 1
    info = {"step": "facts", "data_version": config.DATA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rows": {"FACTS.md": len(rows)}, "by_status": by_status, "live_status": live_status()}
    write_text_safely(json.dumps(info, indent=2) + "\n", SUCCESS_PATH)
    print(f"wrote {rel(FACTS_PATH)}: {len(rows)} facts ({', '.join(f'{k} {v}' for k, v in by_status.items())})")


if __name__ == "__main__":
    main()
