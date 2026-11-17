"""Checks of the second History snapshot (2026-10) in Gold (PLAN.md Phase 5, "Checks").

  * fact_revert_label at the 2026-09 load: history cohort 19,858 reverted, 19,700 within 20 d, 17,646 within 4 d
  * change feed of the 2026-10 load: update pre-images = post-images = rows of mart_label_change
  * label changes by class; follow-up of the live cohorts before the 2026-10 cutoff
  * EC HW2 cross-check: late_reverts class 'exact' (stream saw a September revert after the 2026-09 dump) against
    mart_label_change 'became_reverted'
  * the five reconciliation classes for the live cohort; E(L) of the live cohort with dump labels next to stream labels

Run (after python -m etl.gold_run --snapshot 2026-10 ...)
    python -m etl.snapshot_checks          # writes data/lake/_runs/snapshot_checks.json
"""
from __future__ import annotations

import json

from . import lake_config
from .gold_run import BASE, base_params, find_version
from .spark_session import get_spark


def main() -> None:
    BASE.update(base_params())
    spark = get_spark("truthlag_snapshot_checks")
    G, S = BASE["gold"], BASE["silver"]
    q = lambda s: [r.asDict() for r in spark.sql(s).collect()]
    checks = []

    def check(name, got, want=None):
        ok = None if want is None else got == want
        checks.append({"check": name, "got": got, "want": want, "ok": ok})
        print(("INFO " if ok is None else "PASS " if ok else "FAIL ") + f"{name}: got={got}" + ("" if want is None else f" want={want}"), flush=True)

    v09 = find_version(spark, f"{G}/fact_revert_label", step="fact_revert_label", snapshot="2026-09")
    v10 = find_version(spark, f"{G}/fact_revert_label", step="fact_revert_label", snapshot="2026-10")
    check("fact_revert_label versions (2026-09 load, 2026-10 load)", [v09, v10])
    h = q(f"""SELECT count_if(l.is_identity_reverted) a, count_if(l.is_identity_reverted AND l.seconds_to_identity_revert <= 1728000) b,
                     count_if(l.is_identity_reverted AND l.seconds_to_identity_revert <= 345600) c
              FROM delta.`{G}/fact_edit` f JOIN delta.`{G}/fact_revert_label` VERSION AS OF {v09} l
                ON l.wiki_db = f.wiki_db AND l.rev_id = f.rev_id WHERE f.cohort_id = 'history'""")[0]
    check("history cohort at the 2026-09 load: reverted / within 20 d / within 4 d", [h["a"], h["b"], h["c"]], [19858, 19700, 17646])
    h2 = q(f"""SELECT count_if(l.is_identity_reverted) a, count_if(l.is_identity_reverted AND l.seconds_to_identity_revert <= 1728000) b,
                      count_if(l.is_identity_reverted AND l.seconds_to_identity_revert <= 345600) c
               FROM delta.`{G}/fact_edit` f JOIN delta.`{G}/fact_revert_label` VERSION AS OF {v10} l
                 ON l.wiki_db = f.wiki_db AND l.rev_id = f.rev_id WHERE f.cohort_id = 'history'""")[0]
    check("history cohort at the 2026-10 load: reverted / within 20 d / within 4 d", [h2["a"], h2["b"], h2["c"]])
    cdf = {r["_change_type"]: r["n"] for r in q(f"""SELECT _change_type, count(*) n
            FROM table_changes_by_path('{G}/fact_revert_label', {v10}, {v10}) GROUP BY 1""")}
    n_mart = q(f"SELECT count(*) n FROM delta.`{G}/mart_label_change` WHERE commit_version = {v10}")[0]["n"]
    check("change feed of the 2026-10 load: insert / update_preimage / update_postimage", cdf)
    check("update pre-images = post-images = mart_label_change rows",
          [cdf.get("update_preimage"), cdf.get("update_postimage")], [n_mart, n_mart])
    classes = {r["change_class"]: r["n"] for r in q(f"SELECT change_class, count(*) n FROM delta.`{G}/mart_label_change` GROUP BY 1")}
    check("mart_label_change rows by class", classes)
    in_hist = {r["change_class"]: r["n"] for r in q(f"""SELECT m.change_class, count(*) n FROM delta.`{G}/mart_label_change` m
            JOIN delta.`{G}/fact_edit` f ON f.rev_id = m.rev_id AND f.cohort_id = 'history' GROUP BY 1""")}
    check("label changes among history-cohort revisions, by class", in_hist)
    snap = q(f"SELECT snapshot, snapshot_cutoff, revision_rows, snapshot_published_at FROM delta.`{G}/dim_snapshot` ORDER BY 1")
    check("dim_snapshot", [{k: str(v) for k, v in r.items()} for r in snap])
    cut = [r for r in snap if r["snapshot"] == "2026-10"][0]["snapshot_cutoff"]
    for c in ("live", "live_ext"):
        r = q(f"""SELECT count(*) n, count_if(event_dt + INTERVAL 4 DAYS > TIMESTAMP '{cut}') short
                  FROM delta.`{G}/fact_edit` WHERE cohort_id = '{c}'""")[0]
        check(f"{c}: revisions with less than 4 days between edit and the 2026-10 cutoff (of all)", [r["short"], r["n"]])
    # EC HW2 cross-check: late_reverts as published (silver version built at the parity as_of) and now
    for label, as_of in (("parity", lake_config.PARITY_AS_OF), ("ext", lake_config.EXT_AS_OF)):
        v = find_version(spark, f"{S}/late_reverts", step="cohorts", as_of=as_of)
        r = q(f"""SELECT lr.class, count(*) n, count(m.rev_id) became_reverted,
                         count(l.rev_id) in_2026_10, count_if(l.is_identity_reverted) reverted_in_2026_10
                  FROM delta.`{S}/late_reverts` VERSION AS OF {v} lr
                  LEFT JOIN delta.`{G}/mart_label_change` m ON m.rev_id = lr.rev_id AND m.change_class = 'became_reverted'
                  LEFT JOIN delta.`{G}/fact_revert_label` VERSION AS OF {v10} l ON l.rev_id = lr.rev_id
                  GROUP BY lr.class ORDER BY lr.class""")
        check(f"late_reverts ({label} as_of, silver v{v}) vs the 2026-10 dump, by class", r)
    rec = q(f"SELECT cohort_id, snapshot, label_version, recon_class, n_revisions, round(share, 6) share FROM delta.`{G}/mart_reconciliation` ORDER BY recon_class")
    check("mart_reconciliation (live vs 2026-10)", rec)
    mm = q(f"""SELECT recon_class, count(*) n, percentile_approx(stream_seconds_to_revert, 0.5) med_stream_T,
                      percentile_approx(dump_seconds_to_revert, 0.5) med_dump_T
               FROM delta.`{G}/recon_mismatch` GROUP BY 1 ORDER BY 1""")
    check("recon_mismatch by class (median T in s)", mm)
    el = q(f"""SELECT label_source, wait_label, n_eventual, n_known, round(e_l, 4) e_l FROM delta.`{G}/mart_el_curve`
               WHERE cohort_id = 'live' AND user_kind = 'all' ORDER BY label_source, wait_s""")
    check("E(L) live cohort: stream labels and dump labels", el)
    out = {"label_versions": {"2026-09": v09, "2026-10": v10}, "checks": checks,
           "passed": sum(1 for c in checks if c["ok"]), "failed": sum(1 for c in checks if c["ok"] is False)}
    (lake_config.lake_root() / "_runs" / "snapshot_checks.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"{out['passed']} passed, {out['failed']} failed, {len(checks)} checks")
    spark.stop()


if __name__ == "__main__":
    main()
