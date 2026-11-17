"""Time travel demos, "then vs now" (rubric: warehouse / new tool), on two knowledge axes. Versions are always found
by their commit metadata (D9), never by timestamp.

  Snapshot axis (etl/sql/80_time_travel_then_and_now.sql, the kit's query): gold/fact_revert_label as loaded from the
  2026-09 History snapshot and from the 2026-10 snapshot; reverted history-cohort revisions as known then and now.
  Stream axis (etl/sql/81_time_travel_as_of.sql): gold/fact_edit at the three build as_of values; the live cohort's
  reverts as known then and now, with the change feed between the early and the parity version.

Run
    python -m etl.time_travel          # prints five short tables; writes data/lake/_runs/time_travel.json

What the terminal shows (each part is one query on older versions of a Delta table)
    1. Snapshot axis: reverts known from the 2026-09 monthly snapshot against the 2026-10 one.
    2. Stream axis: reverts of the live cohort as known on three dates.
    3. Change data feed: the rows Delta recorded as changed between those versions.
    4. The updated rows: what changed in them.
    5. Silver: the revert-link table at each version.
Spark's start-up output goes to a log file (TRUTHLAG_SPARK_VERBOSE=1 shows it on the terminal).
"""
from __future__ import annotations

import json

from . import lake_config
from .gold_run import BASE, base_params, find_version, render
from .spark_session import get_spark


def table(headers: list[str], rows: list[list]) -> None:
    """Print rows as an aligned text table; integers get thousands separators."""
    cells = [[f"{c:,}" if isinstance(c, int) and not isinstance(c, bool) else str(c) for c in r] for r in rows]
    widths = [max(len(h), *(len(r[i]) for r in cells)) if cells else len(h) for i, h in enumerate(headers)]
    print("   " + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("   " + "  ".join("-" * w for w in widths))
    for r in cells:
        print("   " + "  ".join(c.rjust(w) if c.replace(",", "").replace(".", "").isdigit() else c.ljust(w)
                                 for c, w in zip(r, widths)))
    print(flush=True)


def main() -> None:
    BASE.update(base_params())
    print("TruthLag time travel: the same question, asked of older versions of the lake.")
    print("Every Delta table keeps its past versions. A version is found by the as_of date or snapshot name")
    print("stored in its commit, never by a timestamp.\n", flush=True)
    spark = get_spark("truthlag_time_travel", quiet=True)
    G, S = BASE["gold"], BASE["silver"]
    v = {k: find_version(spark, f"{G}/fact_edit", step="fact_edit", as_of=a) for k, a in
         (("early", lake_config.EARLY_AS_OF), ("parity", lake_config.PARITY_AS_OF), ("ext", lake_config.EXT_AS_OF))}
    lv = {s_: find_version(spark, f"{G}/fact_revert_label", step="fact_revert_label", snapshot=s_) for s_ in ("2026-09", "2026-10")}
    snap_rows = [r.asDict() for r in spark.sql(render("80_time_travel_then_and_now.sql",
                 {**BASE, "v_2026_09": lv["2026-09"], "v_2026_10": lv["2026-10"]})).collect()]
    print("1. Monthly History snapshots (table gold/fact_revert_label, SQL in etl/sql/80_time_travel_then_and_now.sql)")
    print("   Question: how many revisions of the history cohort are known to be reverted?")
    table(["snapshot", "table version", "known then", "known now"],
          [[r["snapshot"], r["label_version"], r["reverted_as_known_then"], r["reverted_now"]] for r in snap_rows])
    if len(snap_rows) >= 2:
        gain = snap_rows[-1]["reverted_as_known_then"] - snap_rows[0]["reverted_as_known_then"]
        print(f"   -> For the same revisions, the later snapshot knows {gain:,} more reverts than the earlier one.\n", flush=True)
    sql = render("81_time_travel_as_of.sql", {**BASE, "v_early": v["early"], "v_parity": v["parity"], "v_ext": v["ext"],
                                                     "as_of_early": lake_config.EARLY_AS_OF, "as_of_parity": lake_config.PARITY_AS_OF,
                                                     "as_of_ext": lake_config.EXT_AS_OF})
    rows = [r.asDict() for r in spark.sql(sql).collect()]
    print("2. Live stream at three knowledge times (table gold/fact_edit, SQL in etl/sql/81_time_travel_as_of.sql)")
    print("   Question: of the live cohort's revisions, how many were known to be reverted on each date?")
    table(["known at", "table version", "live revisions", "known reverted", "% reverted", "newest revert known"],
          [[r["known_at"], r["fact_edit_version"], r["live_revisions"], r["reverted_as_known"], r["pct_reverted"],
            str(r["newest_known_dt"])[:19]] for r in rows])
    if len(rows) >= 2:
        print(f"   -> Between the first two versions {rows[1]['reverted_as_known'] - rows[0]['reverted_as_known']:,} "
              "more reverts became known. The revisions are the same; only our knowledge changed.\n", flush=True)
    cdf = spark.sql(f"""SELECT _commit_version, _change_type, cohort_id, count(*) n,
                               count_if(live_revert_flag) AS flag_true
                        FROM table_changes_by_path('{G}/fact_edit', {v['early'] + 1}, {v['ext']})
                        GROUP BY _commit_version, _change_type, cohort_id ORDER BY 1, 2, 3""").collect()
    cdf = [r.asDict() for r in cdf]
    print("3. Change data feed of gold/fact_edit (what Delta recorded as changed between the versions above)")
    table(["version", "change type", "cohort", "rows", "rows flagged reverted"],
          [[r["_commit_version"], r["_change_type"], r["cohort_id"], r["n"], r["flag_true"]] for r in cdf])
    print("   -> update_preimage / update_postimage are the same rows before and after an update;")
    print("      insert rows are a cohort added later. The feed accounts for the difference row by row.\n", flush=True)
    # what changed for the revisions that were updated between early and parity: flag flipped, and how late
    flips = spark.sql(f"""
      SELECT count(*) AS updated_rows,
             count_if(NOT coalesce(pre.live_revert_flag, false) AND post.live_revert_flag) AS became_reverted,
             count_if(NOT (pre.page_key <=> post.page_key)) AS page_key_changed,
             percentile_approx(unix_seconds(post.live_known_dt) - unix_seconds(post.event_dt), 0.5) AS median_known_after_s
      FROM table_changes_by_path('{G}/fact_edit', {v['parity']}, {v['parity']}) post
      JOIN table_changes_by_path('{G}/fact_edit', {v['parity']}, {v['parity']}) pre
        ON pre.cohort_id = post.cohort_id AND pre.rev_id = post.rev_id
      WHERE post._change_type = 'update_postimage' AND pre._change_type = 'update_preimage'""").first().asDict()
    print("4. The rows updated between the first and the second version")
    days = (flips["median_known_after_s"] or 0) / 86400
    table(["updated rows", "became reverted", "page key changed", "median time from edit to known revert"],
          [[flips["updated_rows"], flips["became_reverted"], flips["page_key_changed"],
            f"{flips['median_known_after_s']:,} s (about {days:.1f} days)"]])
    # Silver by version: the live link table as built at each as_of
    hist = spark.sql(f"DESCRIBE HISTORY delta.`{S}/live_revert_links`").select("version", "userMetadata").collect()
    silver = []
    for h in sorted(hist, key=lambda r: r["version"]):
        meta = json.loads(h["userMetadata"] or "{}")
        if meta.get("as_of"):
            n = spark.sql(f"SELECT count(*) n, count_if(within_followup) w FROM delta.`{S}/live_revert_links` VERSION AS OF {h['version']}").first()
            silver.append({"version": h["version"], "as_of": meta["as_of"], "links": n["n"], "within_followup": n["w"]})
    print("5. Silver: the revert-link table as built at each as_of (table silver/live_revert_links)")
    table(["table version", "as of", "revert links", "inside the 4-day follow-up"],
          [[r["version"], r["as_of"], r["links"], r["within_followup"]] for r in silver])
    print("   -> Links keep arriving, but those inside the follow-up window stop growing: later ones are late reverts.\n")
    out = {"snapshot_axis": {"fact_revert_label_versions": lv, "then_and_now": snap_rows},
           "fact_edit_versions": v, "then_and_now": rows, "change_feed": cdf, "early_to_parity_updates": flips,
           "silver_live_revert_links_by_version": silver}
    path = lake_config.lake_root() / "_runs" / "time_travel.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    print(f"Saved the same numbers to {path}")
    spark.stop()


if __name__ == "__main__":
    main()
