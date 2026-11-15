"""Hypotheses H1, H3 and H4 (docs/delta_lake_handoff/DECISIONS.md) on the Gold tables, with page-level bootstrap intervals.

H1  long-tailed lag: under 60% of eventual reverts are known within 1 h, and under 95% within 48 h.
    Falsified if either share is above its threshold. Series: live (Oct 20-22, published), live_ext (Oct 20 - Nov 8),
    live_ext restricted to October edits, history (Sep 8-10, dump labels, for comparison).
H3  bursty pages converge slowest: at a fixed L, E(L) is higher for burst edits (page had >= 10 edits in the hour
    before, D20) than for the rest. Falsified if the 95% intervals overlap. L = 1 h and 1 d.
H4  page identity matters: joining facts to the dim_page version current at event time, instead of the page's current
    title, changes page-level revert metrics for a measurable share of pages. The floor is not set in DECISIONS.md;
    this build reports the share and, as its own stated choice, uses a floor of 1% of pages.

Intervals: Poisson bootstrap over pages (each page's reverts move together), B = 2,000, seed 226.
Reads Gold at the versions given (default: current) and the Silver link tables behind the marts.

Run
    python -m etl.hypotheses        # writes data/lake/_runs/hypotheses.json
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from . import lake_config
from .hw2 import config
from .spark_session import get_spark

B = 2000
SEED = 226
H4_FLOOR_PCT = 1.0
BURST_MIN = 10


def poisson_ci(num_by_page: np.ndarray, den_by_page: np.ndarray, rng, b: int = B) -> tuple[float, float, float]:
    """Ratio sum(num)/sum(den) and its 95% Poisson-bootstrap interval over pages."""
    est = num_by_page.sum() / den_by_page.sum()
    reps = []
    for _ in range(b // 200):
        w = rng.poisson(1.0, size=(200, len(num_by_page))).astype(np.float32)
        reps.append((w @ num_by_page.astype(np.float32)) / np.maximum(w @ den_by_page.astype(np.float32), 1e-9))
    reps = np.concatenate(reps)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return float(est), float(lo), float(hi)


def poisson_diff_ci(a_num, a_den, b_num, b_den, rng, b: int = B):
    """Difference of two ratios over the SAME pages (aligned arrays), with a joint bootstrap."""
    est = a_num.sum() / a_den.sum() - b_num.sum() / b_den.sum()
    reps = []
    for _ in range(b // 200):
        w = rng.poisson(1.0, size=(200, len(a_num))).astype(np.float32)
        ra = (w @ a_num.astype(np.float32)) / np.maximum(w @ a_den.astype(np.float32), 1e-9)
        rb = (w @ b_num.astype(np.float32)) / np.maximum(w @ b_den.astype(np.float32), 1e-9)
        reps.append(ra - rb)
    reps = np.concatenate(reps)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return float(est), float(lo), float(hi)


def reverts_frame(spark, S: str) -> pd.DataFrame:
    h = config.LIVE_FOLLOWUP_S
    q = f"""
    SELECT 'live' AS series, r.page_id, r.ts, r.page_edits_prev_1h, CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0) AS known_after_s
    FROM delta.`{S}/live_revert_links` l JOIN delta.`{S}/live_revisions` r ON r.rev_id = l.reverted_rev_id
    WHERE l.T_s >= 0 AND l.T_s <= {h}
    UNION ALL
    SELECT 'live_ext', r.page_id, r.ts, r.page_edits_prev_1h, CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0)
    FROM delta.`{S}/live_ext_revert_links` l JOIN delta.`{S}/live_ext_revisions` r ON r.rev_id = l.reverted_rev_id
    WHERE l.T_s >= 0 AND l.T_s <= {h}
    UNION ALL
    SELECT 'history', r.page_id, r.ts, r.page_edits_prev_1h, CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0)
    FROM delta.`{S}/history_revert_links` l JOIN delta.`{S}/history_revisions` r ON r.rev_id = l.reverted_rev_id
    WHERE l.T_s >= 0 AND l.T_s <= {h}"""
    df = spark.sql(q).toPandas()
    octo = df[(df.series == "live_ext") & (pd.to_datetime(df.ts) < pd.Timestamp("2026-11-01"))].copy()
    octo["series"] = "live_ext_october"
    return pd.concat([df, octo], ignore_index=True)


def h1(df: pd.DataFrame, rng) -> list[dict]:
    out = []
    for series, g in df.groupby("series"):
        by_page = g.groupby("page_id").agg(n=("known_after_s", "size"),
                                           k1h=("known_after_s", lambda s: int((s <= 3600).sum())),
                                           k48=("known_after_s", lambda s: int((s <= 172800).sum())))
        r1 = poisson_ci(by_page.k1h.to_numpy(), by_page.n.to_numpy(), rng)
        r48 = poisson_ci(by_page.k48.to_numpy(), by_page.n.to_numpy(), rng)
        out.append({"series": series, "eventual_reverts": int(by_page.n.sum()), "pages": int(len(by_page)),
                    "known_1h_pct": round(100 * r1[0], 2), "known_1h_ci": [round(100 * r1[1], 2), round(100 * r1[2], 2)],
                    "known_48h_pct": round(100 * r48[0], 2), "known_48h_ci": [round(100 * r48[1], 2), round(100 * r48[2], 2)],
                    "below_60_at_1h": bool(r1[0] < 0.60), "below_95_at_48h": bool(r48[0] < 0.95),
                    "ci_1h_entirely_below_60": bool(r1[2] < 0.60), "ci_48h_entirely_below_95": bool(r48[2] < 0.95),
                    "verdict": ("not falsified" if r1[0] < 0.60 and r48[0] < 0.95 else "falsified (point estimate)")
                    + ("" if (r1[2] < 0.60 and r48[2] < 0.95) or (r1[1] > 0.60 or r48[1] > 0.95) else
                       "; an interval crosses its threshold, so the call is not robust")})
    return out


def h3(df: pd.DataFrame, rng) -> list[dict]:
    out = []
    for series, g in df.groupby("series"):
        g = g.assign(burst=g.page_edits_prev_1h.fillna(-1) >= BURST_MIN)
        for L, label in ((3600, "1 h"), (86400, "1 d")):
            agg = g.assign(unknown=(g.known_after_s > L).astype(int)).groupby(["page_id", "burst"]).agg(
                n=("unknown", "size"), u=("unknown", "sum")).unstack("burst", fill_value=0)
            nb, ub = agg[("n", True)].to_numpy(), agg[("u", True)].to_numpy()
            nr, ur = agg[("n", False)].to_numpy(), agg[("u", False)].to_numpy()
            eb = poisson_ci(ub[nb > 0], nb[nb > 0], rng)
            er = poisson_ci(ur[nr > 0], nr[nr > 0], rng)
            d = poisson_diff_ci(ub, np.maximum(nb, 0), ur, nr, rng) if nb.sum() else (np.nan,) * 3
            overlap = not (eb[1] > er[2] or eb[2] < er[1])
            out.append({"series": series, "L": label, "burst_reverts": int(nb.sum()), "rest_reverts": int(nr.sum()),
                        "burst_pages": int((nb > 0).sum()),
                        "E_burst": round(eb[0], 4), "E_burst_ci": [round(eb[1], 4), round(eb[2], 4)],
                        "E_rest": round(er[0], 4), "E_rest_ci": [round(er[1], 4), round(er[2], 4)],
                        "diff_burst_minus_rest": round(d[0], 4), "diff_ci": [round(d[1], 4), round(d[2], 4)],
                        "intervals_overlap": overlap,
                        "verdict": "falsified (intervals overlap)" if overlap else
                        ("supported: burst E(L) higher" if eb[0] > er[0] else "falsified: burst E(L) lower, intervals apart")})
    return out


def h4(spark, G: str, S: str) -> dict:
    """Page-level revert metrics keyed by title: title at event time (as-of join, SCD2) vs the page's current title."""
    h = config.LIVE_FOLLOWUP_S
    spark.sql(f"""
      CREATE OR REPLACE TEMP VIEW v_h4 AS
      WITH f AS (
        SELECT f.cohort_id, f.rev_id, f.page_key,
               CASE WHEN f.cohort_id = 'history'
                    THEN coalesce(l.is_identity_reverted AND l.seconds_to_identity_revert BETWEEN 0 AND {h}, false)
                    ELSE coalesce(f.live_revert_flag, false) END AS reverted
        FROM delta.`{G}/fact_edit` f
        LEFT JOIN delta.`{G}/fact_revert_label` l ON l.wiki_db = f.wiki_db AND l.rev_id = f.rev_id AND f.cohort_id = 'history'
        WHERE f.cohort_id IN ('history', 'live_ext')
      )
      SELECT f.cohort_id, f.rev_id, f.reverted, v.page_id, v.title AS title_then, v.namespace AS ns_then,
             c.title AS title_now, c.namespace AS ns_now
      FROM f JOIN delta.`{G}/dim_page` v ON v.page_key = f.page_key
      JOIN delta.`{G}/dim_page` c ON c.wiki_db = v.wiki_db AND c.page_id = v.page_id AND c.is_current""")
    out = {}
    for cohort in ("history", "live_ext"):
        facts = spark.sql(f"""SELECT count(*) n, count_if(NOT (title_then <=> title_now) OR NOT (ns_then <=> ns_now)) moved,
                                     count(DISTINCT page_id) pages,
                                     count(DISTINCT CASE WHEN NOT (title_then <=> title_now) OR NOT (ns_then <=> ns_now) THEN page_id END) pages_moved
                              FROM v_h4 WHERE cohort_id = '{cohort}'""").first().asDict()
        # page-level metric per title key: edits, reverted, revert rate
        m = spark.sql(f"""
          WITH a AS (SELECT title_then AS title, count(*) n, count_if(reverted) r FROM v_h4 WHERE cohort_id = '{cohort}' GROUP BY title_then),
               b AS (SELECT title_now AS title, count(*) n, count_if(reverted) r FROM v_h4 WHERE cohort_id = '{cohort}' GROUP BY title_now)
          SELECT count(*) AS titles,
                 count_if(a.title IS NULL OR b.title IS NULL OR a.n <> b.n OR a.r <> b.r) AS titles_changed,
                 count_if(a.title IS NULL OR b.title IS NULL OR a.r / a.n <> b.r / b.n) AS titles_rate_changed,
                 count_if(coalesce(a.r, 0) <> coalesce(b.r, 0)) AS titles_reverts_changed,
                 sum(abs(coalesce(a.r, 0) - coalesce(b.r, 0))) AS reverts_moved
          FROM a FULL OUTER JOIN b ON a.title = b.title""").first().asDict()
        share_pages = 100 * facts["pages_moved"] / facts["pages"]
        out[cohort] = {**facts, **m, "share_facts_title_differs_pct": round(100 * facts["moved"] / facts["n"], 3),
                       "share_pages_affected_pct": round(share_pages, 3),
                       "share_titles_metric_changed_pct": round(100 * m["titles_changed"] / m["titles"], 3),
                       "floor_pct": H4_FLOOR_PCT,
                       "verdict": "not falsified (share >= floor)" if share_pages >= H4_FLOOR_PCT else "falsified (share below floor)"}
    out["history_revisions_title_differs_from_historical"] = spark.sql(
        f"SELECT count_if(NOT (page_title <=> page_title_historical)) n FROM delta.`{S}/history_revisions`").first()["n"]
    return out


def main() -> None:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    spark = get_spark("truthlag_hypotheses")
    root = lake_config.lake_root()
    G, S = str(root / "gold"), str(root / "silver")
    versions = {t: spark.sql(f"DESCRIBE HISTORY delta.`{G}/{t}` LIMIT 1").first()["version"]
                for t in ("fact_edit", "dim_page", "fact_revert_label", "mart_el_curve")}
    df = reverts_frame(spark, S)
    res = {"gold_versions": versions, "bootstrap": {"B": B, "seed": SEED, "kind": "Poisson bootstrap over pages"},
           "H1": h1(df, rng), "H3": h3(df, rng), "H4": h4(spark, G, S)}
    res["seconds"] = round(time.time() - t0, 1)
    (root / "_runs" / "hypotheses.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))
    spark.stop()


if __name__ == "__main__":
    main()
