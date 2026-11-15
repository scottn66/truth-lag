"""Time travel demo, "then vs now" (rubric: warehouse / new tool), on gold/fact_edit and the Change Data Feed.

Finds the fact_edit versions written at the three build as_of values by their commit metadata (D9), runs
etl/sql/80_time_travel_then_and_now.sql, then reads the change feed between the early and the parity version
(the labels learned in between) and the same numbers from Silver by version.

Run
    python -m etl.time_travel          # writes data/lake/_runs/time_travel.json
"""
from __future__ import annotations

import json

from . import lake_config
from .gold_run import BASE, base_params, find_version, render
from .spark_session import get_spark


def main() -> None:
    BASE.update(base_params())
    spark = get_spark("truthlag_time_travel")
    G, S = BASE["gold"], BASE["silver"]
    v = {k: find_version(spark, f"{G}/fact_edit", step="fact_edit", as_of=a) for k, a in
         (("early", lake_config.EARLY_AS_OF), ("parity", lake_config.PARITY_AS_OF), ("ext", lake_config.EXT_AS_OF))}
    sql = render("80_time_travel_then_and_now.sql", {**BASE, "v_early": v["early"], "v_parity": v["parity"], "v_ext": v["ext"],
                                                     "as_of_early": lake_config.EARLY_AS_OF, "as_of_parity": lake_config.PARITY_AS_OF,
                                                     "as_of_ext": lake_config.EXT_AS_OF})
    rows = [r.asDict() for r in spark.sql(sql).collect()]
    for r in rows:
        print(r)
    cdf = spark.sql(f"""SELECT _commit_version, _change_type, cohort_id, count(*) n,
                               count_if(live_revert_flag) AS flag_true
                        FROM table_changes_by_path('{G}/fact_edit', {v['early'] + 1}, {v['ext']})
                        GROUP BY _commit_version, _change_type, cohort_id ORDER BY 1, 2, 3""").collect()
    cdf = [r.asDict() for r in cdf]
    for r in cdf:
        print(r)
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
    print(flips)
    # Silver by version: the live link table as built at each as_of
    hist = spark.sql(f"DESCRIBE HISTORY delta.`{S}/live_revert_links`").select("version", "userMetadata").collect()
    silver = []
    for h in sorted(hist, key=lambda r: r["version"]):
        meta = json.loads(h["userMetadata"] or "{}")
        if meta.get("as_of"):
            n = spark.sql(f"SELECT count(*) n, count_if(within_followup) w FROM delta.`{S}/live_revert_links` VERSION AS OF {h['version']}").first()
            silver.append({"version": h["version"], "as_of": meta["as_of"], "links": n["n"], "within_followup": n["w"]})
    for r in silver:
        print(r)
    out = {"fact_edit_versions": v, "then_and_now": rows, "change_feed": cdf, "early_to_parity_updates": flips,
           "silver_live_revert_links_by_version": silver}
    (lake_config.lake_root() / "_runs" / "time_travel.json").write_text(json.dumps(out, indent=1, default=str))
    spark.stop()


if __name__ == "__main__":
    main()
