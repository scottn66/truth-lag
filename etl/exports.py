"""Small Gold extracts for teammates (data/exports/, git-ignored; each file < 50 MB). Schemas in docs/final/HANDOFF_TEAM.md.

  lsh_edits.parquet / .csv     for the MinHash LSH notebook: every reverted cohort edit (label 1) and an equal-size
                               random sample of edits never reverted within 4 days (label 0), with comment and title
  mart_el_curve.csv            gold/mart_el_curve (group size n_eventual, n_known) for the privacy checks and charts
  mart_el_by_burst.csv         gold/mart_el_by_burst
  group_sizes_by_kind_hour.csv revisions and reverts per (cohort, user_kind, date, hour): a quasi-identifier grid for k-anonymity
  page_revert_summary.parquet  one row per (cohort, page): edits, distinct editors, reverts, reverts known in 1 h
  page_revert_summary_top.csv  the same for pages with >= 5 edits (CSV for MongoDB Charts / slides)
  hypotheses_h1.csv, hypotheses_h3.csv, h4.json   the hypothesis tables
  daily_counts.csv             Bronze and Silver rows per stream and event date
  mart_reconciliation.csv      live cohort: stream label vs the 2026-10 dump label, five classes
  label_change_by_class.csv    revisions whose dump label changed between snapshot 2026-09 and 2026-10, by class
  manifest.json                versions, row counts, sizes and SHA-256 of every file

Human editors appear only as pseudonyms (ec-hw2/ingest/build_documents.public_name); bots keep their names.
No user_text, user_name, user_id or editor key leaves the lake. Inside edit comments, user links become [[USER]],
temporary-account names ~TEMP and IP addresses IP (scrub_comment).

Run
    python -m etl.exports
"""
from __future__ import annotations

import hashlib
import json
import re
import time

import pandas as pd

from . import lake_config
from .hw2 import config
from .spark_session import get_spark

OUT = lake_config.EXPORTS_DIR
SEED = 226
_USER_LINK = re.compile(r"\[\[\s*:?\s*(?:[a-z]{1,3}:)?\s*(?:Users?[ _]|User:|Special:Contrib)[^\]]*\]{0,2}", re.I)
_TEMP = re.compile(r"~\d{4}-[\d-]*")
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_IPV6 = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{1,4}\b")


def scrub_comment(text):
    """Mask editor identities inside an edit summary: user links, temporary-account names, IP addresses."""
    if not isinstance(text, str):
        return text
    text = _USER_LINK.sub("[[USER]]", text)
    text = _TEMP.sub("~TEMP", text)
    text = _IPV6.sub("IP", _IPV4.sub("IP", text))
    return text


def main() -> None:
    import sys
    sys.path.insert(0, str(lake_config.REPO_DIR / "ec-hw2"))
    from ingest.build_documents import public_name

    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    spark = get_spark("truthlag_exports")
    root = lake_config.lake_root()
    G, S = str(root / "gold"), str(root / "silver")
    ver = lambda p: spark.sql(f"DESCRIBE HISTORY delta.`{p}` LIMIT 1").first()["version"]
    versions = {t: ver(f"{G}/{t}") for t in ("fact_edit", "dim_page", "fact_revert_label", "mart_el_curve", "mart_el_by_burst")}
    versions.update({f"silver/{t}": ver(f"{S}/{t}") for t in ("history_revisions", "live_revisions", "live_ext_revisions")})
    h = config.LIVE_FOLLOWUP_S
    files = {}

    # ---- LSH input: comments and titles of reverted edits (label 1) and a sample of the rest (label 0) ----
    spark.sql(f"""
      CREATE OR REPLACE TEMP VIEW v_edits AS
      SELECT 'history' AS cohort_id, r.rev_id, r.page_id, r.page_title, r.page_ns, r.ts, r.comment, r.user_kind,
             r.user_key, r.user_name, r.size_delta, r.is_revert, l.T_s, l.reverting_rev_id,
             (l.reverted_rev_id IS NOT NULL) AS label
      FROM delta.`{S}/history_revisions` r
      LEFT JOIN (SELECT * FROM delta.`{S}/history_revert_links` WHERE T_s BETWEEN 0 AND {h}) l ON l.reverted_rev_id = r.rev_id
      UNION ALL
      SELECT 'live_ext', r.rev_id, r.page_id, r.page_title, r.page_ns, r.ts, r.comment, r.user_kind, r.user_key,
             r.user_name, r.size_delta, r.is_revert, l.T_s, l.reverting_rev_id, (l.reverted_rev_id IS NOT NULL)
      FROM delta.`{S}/live_ext_revisions` r
      LEFT JOIN (SELECT * FROM delta.`{S}/live_ext_revert_links` WHERE within_followup AND T_s BETWEEN 0 AND {h}) l
        ON l.reverted_rev_id = r.rev_id""")
    pos = spark.sql("SELECT * FROM v_edits WHERE label").toPandas()
    n_pos = {c: int((pos.cohort_id == c).sum()) for c in ("history", "live_ext")}
    negs = []
    for c, n in n_pos.items():
        # A uniform sample of exactly n rows: order by a hash of the revision id and the seed, keep the first n.
        # (Until 2026-11-15 this was .sample(fraction).limit(n), which dropped the last sampled rows in file order
        # and so under-sampled the latest edits; found by notebooks/fallback/moments_reservoir.ipynb.)
        negs.append(spark.sql(f"""SELECT * FROM v_edits WHERE NOT label AND cohort_id = '{c}'
                                  ORDER BY xxhash64(rev_id, {SEED}), rev_id LIMIT {n}""").toPandas())
    lsh = pd.concat([pos, *negs], ignore_index=True)
    lsh["editor"] = [public_name(k, key, name) for k, key, name in zip(lsh.user_kind, lsh.user_key, lsh.user_name)]
    lsh = lsh.drop(columns=["user_key", "user_name"]).rename(columns={"T_s": "seconds_to_revert"})
    lsh["comment"] = lsh["comment"].map(scrub_comment)
    lsh["label"] = lsh["label"].astype(int)
    lsh = lsh.sort_values(["cohort_id", "rev_id"]).reset_index(drop=True)
    lsh.to_parquet(OUT / "lsh_edits.parquet", index=False)
    lsh.to_csv(OUT / "lsh_edits.csv", index=False)
    files["lsh_edits.parquet"] = len(lsh)
    files["lsh_edits.csv"] = len(lsh)

    # ---- marts with group sizes ----
    for t in ("mart_el_curve", "mart_el_by_burst"):
        df = spark.sql(f"SELECT * FROM delta.`{G}/{t}` ORDER BY 1, 2, 3, wait_s").toPandas()
        df.to_csv(OUT / f"{t}.csv", index=False)
        files[f"{t}.csv"] = len(df)
    g = spark.sql(f"""
      SELECT f.cohort_id, f.user_kind, CAST(f.event_dt AS DATE) AS date, hour(f.event_dt) AS hour_utc,
             count(*) AS revisions,
             count_if(CASE WHEN f.cohort_id = 'history'
                           THEN l.is_identity_reverted AND l.seconds_to_identity_revert BETWEEN 0 AND {h}
                           ELSE f.live_revert_flag END) AS reverted_4d,
             count(DISTINCT f.user_key) AS distinct_editors, count(DISTINCT f.page_key) AS distinct_page_versions
      FROM delta.`{G}/fact_edit` f
      LEFT JOIN delta.`{G}/fact_revert_label` l ON l.wiki_db = f.wiki_db AND l.rev_id = f.rev_id AND f.cohort_id = 'history'
      GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4""").toPandas()
    g.to_csv(OUT / "group_sizes_by_kind_hour.csv", index=False)
    files["group_sizes_by_kind_hour.csv"] = len(g)

    # ---- page-level summary (k-anonymity: distinct editors per published page row) ----
    spark.sql(f"""
      CREATE OR REPLACE TEMP VIEW v_known AS
      SELECT 'live' AS cohort_id, reverted_rev_id, CAST(T_s AS DOUBLE) + coalesce(K_s, 0) AS known_after_s
      FROM delta.`{S}/live_revert_links` WHERE within_followup
      UNION ALL SELECT 'live_ext', reverted_rev_id, CAST(T_s AS DOUBLE) + coalesce(K_s, 0)
      FROM delta.`{S}/live_ext_revert_links` WHERE within_followup
      UNION ALL SELECT 'history', reverted_rev_id, CAST(T_s AS DOUBLE) FROM delta.`{S}/history_revert_links` WHERE T_s BETWEEN 0 AND {h}""")
    p = spark.sql(f"""
      SELECT f.cohort_id, d.page_id, c.title AS current_title, c.namespace, count(*) AS edits,
             count(DISTINCT f.user_key) AS distinct_editors,
             count_if(k.reverted_rev_id IS NOT NULL) AS reverted_4d,
             count_if(k.known_after_s <= 3600) AS reverts_known_1h,
             count_if(f.page_edits_prev_1h >= 10) AS burst_edits
      FROM delta.`{G}/fact_edit` f
      JOIN delta.`{G}/dim_page` d ON d.page_key = f.page_key
      JOIN delta.`{G}/dim_page` c ON c.wiki_db = d.wiki_db AND c.page_id = d.page_id AND c.is_current
      LEFT JOIN v_known k ON k.cohort_id = f.cohort_id AND k.reverted_rev_id = f.rev_id
      GROUP BY 1, 2, 3, 4""").toPandas()
    p.to_parquet(OUT / "page_revert_summary.parquet", index=False)
    top = p[p.edits >= 5].sort_values(["cohort_id", "reverted_4d", "edits"], ascending=[True, False, False])
    top.to_csv(OUT / "page_revert_summary_top.csv", index=False)
    files["page_revert_summary.parquet"] = len(p)
    files["page_revert_summary_top.csv"] = len(top)

    # ---- second snapshot: reconciliation and label changes (when the 2026-10 load exists) ----
    if (root / "gold" / "mart_reconciliation" / "_delta_log").is_dir():
        r = spark.sql(f"SELECT * FROM delta.`{G}/mart_reconciliation` ORDER BY cohort_id, snapshot, recon_class").toPandas()
        r.to_csv(OUT / "mart_reconciliation.csv", index=False)
        c = spark.sql(f"""SELECT from_snapshot, to_snapshot, change_class, count(*) AS revisions
                          FROM delta.`{G}/mart_label_change` GROUP BY 1, 2, 3 ORDER BY 1, 2, 3""").toPandas()
        c.to_csv(OUT / "label_change_by_class.csv", index=False)
        files.update({"mart_reconciliation.csv": len(r), "label_change_by_class.csv": len(c)})

    # ---- hypotheses and daily counts ----
    hyp = json.loads((root / "_runs" / "hypotheses.json").read_text())
    pd.DataFrame(hyp["H1"]).to_csv(OUT / "hypotheses_h1.csv", index=False)
    pd.DataFrame(hyp["H3"]).to_csv(OUT / "hypotheses_h3.csv", index=False)
    (OUT / "hypotheses_h4.json").write_text(json.dumps(hyp["H4"], indent=1))
    files.update({"hypotheses_h1.csv": len(hyp["H1"]), "hypotheses_h3.csv": len(hyp["H3"]), "hypotheses_h4.json": 1})
    rows = []
    for layer, t in (("bronze", "page_change_events"), ("bronze", "revert_risk_events"), ("bronze", "tags_events"),
                     ("silver", "page_change"), ("silver", "tag_events")):
        for r in spark.sql(f"SELECT event_date, count(*) n FROM delta.`{root}/{layer}/{t}` GROUP BY 1 ORDER BY 1").collect():
            rows.append({"table": f"{layer}/{t}", "event_date": str(r["event_date"]), "rows": r["n"]})
    pd.DataFrame(rows).to_csv(OUT / "daily_counts.csv", index=False)
    files["daily_counts.csv"] = len(rows)

    manifest = {"made_at_utc": pd.Timestamp.now(tz="UTC").isoformat(), "lake_versions": versions, "files": {}}
    for name, n in files.items():
        f = OUT / name
        manifest["files"][name] = {"rows": n, "bytes": f.stat().st_size,
                                   "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest, indent=1))
    print("seconds", round(time.time() - t0, 1))
    spark.stop()


if __name__ == "__main__":
    main()
