"""Checks of Gold against the published EC HW2 numbers (PLAN.md, "Numbers the build must reproduce").

Run (after python -m etl.gold_run at the parity as_of)
    python -m etl.gold_checks [--cohort live] [--out data/lake/_runs/gold_checks_parity.json]
"""
from __future__ import annotations

import argparse
import json

from deltalake import DeltaTable

from . import lake_config
from .spark_session import get_spark

# Known reverts by wait, all editors, 4-day horizon (PLAN.md; ec-hw2/report/FACTS.md)
EXPECTED_KNOWN = {
    "history": {"0": 0, "1 min": 3506, "5 min": 6204, "15 min": 7737, "1 h": 9822, "6 h": 12900, "1 d": 15697,
                "2 d": 16725, "4 d": 17646},
    "live": {"0": 0, "1 min": 3986, "5 min": 6958, "15 min": 8398, "1 h": 10326, "6 h": 13405, "1 d": 15936,
             "2 d": 16699, "4 d": 17818},
}
EXPECTED_KIND_1H = {("history", "temporary"): (6157, 9863), ("history", "registered"): (3622, 7623),
                    ("live", "temporary"): (6358, 9772), ("live", "registered"): (3928, 7905)}
EXPECTED_BURST_REVS = {"history": [202410, 42155, 32697, 11888, 5866], "live": [190392, 39277, 30782, 11929, 7086]}
EXPECTED_BURST_10_REVERTS = {"history": 343, "live": 439}
EXPECTED_KINDS = {"history": {"bot": 33483, "temporary": 38164, "registered": 223366, "unknown": 3},
                  "live": {"bot": 31973, "temporary": 36314, "registered": 211179}}


def run(out_path: str | None = None) -> dict:
    spark = get_spark("truthlag_gold_checks")
    G = str(lake_config.lake_root() / "gold")
    checks = []

    def check(name, got, want):
        ok = got == want
        checks.append({"check": name, "got": got, "want": want, "ok": ok})
        print(("PASS " if ok else "FAIL ") + f"{name}: got={got} want={want}", flush=True)

    q = lambda s: spark.sql(s.replace("{G}", G)).collect()
    # fact_edit rows
    rows = {r["cohort_id"]: r["n"] for r in q("SELECT cohort_id, count(*) n FROM delta.`{G}/fact_edit` GROUP BY cohort_id")}
    check("fact_edit history rows", rows.get("history"), 295016)
    check("fact_edit live rows", rows.get("live"), 279466)
    # editor kinds at edit time
    for c, want in EXPECTED_KINDS.items():
        got = {r["user_kind"]: r["n"] for r in q(f"SELECT user_kind, count(*) n FROM delta.`{{G}}/fact_edit` WHERE cohort_id = '{c}' GROUP BY user_kind")}
        check(f"fact_edit {c} rows by user_kind", got, want)
    # E(L) curve, all editors
    curve = {}
    for r in q("SELECT cohort_id, wait_label, n_known, n_eventual, e_l FROM delta.`{G}/mart_el_curve` WHERE user_kind = 'all'"):
        curve.setdefault(r["cohort_id"], {})[r["wait_label"]] = (r["n_known"], r["n_eventual"], r["e_l"])
    for c, want in EXPECTED_KNOWN.items():
        check(f"mart_el_curve {c} known by wait (all editors)", {k: curve[c][k][0] for k in want}, want)
    check("live E(1 h) = 0.4205", round(curve["live"]["1 h"][2], 4), 0.4205)
    check("history E(1 h) = 0.4434", round(curve["history"]["1 h"][2], 4), 0.4434)
    check("live share known at 1 h = 57.95%", round(100 * curve["live"]["1 h"][0] / curve["live"]["1 h"][1], 2), 57.95)
    # by kind at 1 h
    for (c, k), want in EXPECTED_KIND_1H.items():
        r = q(f"SELECT n_known, n_eventual FROM delta.`{{G}}/mart_el_curve` WHERE cohort_id = '{c}' AND user_kind = '{k}' AND wait_label = '1 h'")[0]
        check(f"mart_el_curve {c} {k} at 1 h (known, eventual)", (r["n_known"], r["n_eventual"]), want)
    # burst groups: revisions per group
    for c, want in EXPECTED_BURST_REVS.items():
        got = q(f"""SELECT count_if(page_edits_prev_1h = 0) a, count_if(page_edits_prev_1h = 1) b,
                    count_if(page_edits_prev_1h BETWEEN 2 AND 4) c, count_if(page_edits_prev_1h BETWEEN 5 AND 9) d,
                    count_if(page_edits_prev_1h >= 10) e FROM delta.`{{G}}/fact_edit` WHERE cohort_id = '{c}'""")[0]
        check(f"fact_edit {c} revisions per burst group (0,1,2-4,5-9,10+)", list(got), want)
        r = q(f"SELECT n_eventual FROM delta.`{{G}}/mart_el_by_burst` WHERE cohort_id = '{c}' AND burst_group = '10+' AND wait_label = '1 h'")[0]
        check(f"mart_el_by_burst {c} eventual reverts in 10+", r["n_eventual"], EXPECTED_BURST_10_REVERTS[c])
    # dim_page integrity
    check("dim_page: pages without exactly one current row",
          q("SELECT count(*) n FROM (SELECT page_id, count_if(is_current) c FROM delta.`{G}/dim_page` GROUP BY wiki_db, page_id) WHERE c <> 1")[0]["n"], 0)
    check("dim_page: gaps or overlaps between consecutive versions",
          q("""SELECT count(*) n FROM (SELECT valid_to, lead(valid_from) OVER (PARTITION BY wiki_db, page_id ORDER BY valid_from) nxt
               FROM delta.`{G}/dim_page`) WHERE nxt IS NOT NULL AND NOT (valid_to <=> nxt)""")[0]["n"], 0)
    check("fact_edit rows with no page_key", q("SELECT count(*) n FROM delta.`{G}/fact_edit` WHERE page_key IS NULL")[0]["n"], 0)
    check("fact_edit rows that join to other than exactly one dim_page version",
          q("""SELECT count(*) n FROM (SELECT f.cohort_id, f.rev_id, count(p.page_key) k FROM delta.`{G}/fact_edit` f
               JOIN delta.`{G}/dim_page` d0 ON d0.page_key = f.page_key
               LEFT JOIN delta.`{G}/dim_page` p ON p.wiki_db = d0.wiki_db AND p.page_id = d0.page_id
                 AND f.event_dt >= p.valid_from AND (p.valid_to IS NULL OR f.event_dt < p.valid_to)
               GROUP BY f.cohort_id, f.rev_id) WHERE k <> 1""")[0]["n"], 0)
    # delta-rs reads every Gold table with the same row counts
    for t in ["dim_cohort", "dim_snapshot", "dim_time", "dim_user", "dim_page", "fact_edit", "fact_revert_label",
              "mart_el_curve", "mart_el_by_burst"]:
        spark_n = q(f"SELECT count(*) n FROM delta.`{{G}}/{t}`")[0]["n"]
        rs = DeltaTable(f"{G}/{t}")
        rs_n = sum(a.num_rows for a in rs.to_pyarrow_dataset().to_batches(columns=[rs.schema().to_arrow().names[0]]))
        check(f"delta-rs row count of gold/{t} equals Spark's", rs_n, spark_n)
    versions = {t: spark.sql(f"DESCRIBE HISTORY delta.`{G}/{t}` LIMIT 1").first()["version"]
                for t in ["dim_page", "fact_edit", "fact_revert_label", "mart_el_curve", "mart_el_by_burst"]}
    res = {"passed": sum(c["ok"] for c in checks), "total": len(checks), "versions": versions, "checks": checks,
           "curve": {c: {w: list(v) for w, v in d.items()} for c, d in curve.items()}}
    print(f"{res['passed']} of {res['total']} checks passed; versions {versions}")
    if out_path:
        with open(out_path, "w") as f:
            json.dump(res, f, indent=1, default=str)
    spark.stop()
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(lake_config.lake_root() / "_runs" / "gold_checks.json"))
    run(ap.parse_args().out)
