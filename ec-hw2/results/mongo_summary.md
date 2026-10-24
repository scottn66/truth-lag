# MongoDB query timings

Target: local. MongoDB 8.0.34. Each query ran 7 warm times after 1 warm-up; median_ms is the median of those runs. The risk deciles ran once. Checks: Q1 = pandas (every cohort x hour x user kind): OK; Q2 = pandas (same 20 page_ids, scores rounded to 6): OK; Q3 default bucket 'over_20d' is empty: OK; Q3 bucket counts = pandas (history, live, history_4d): OK; Q5 known-by shares = pandas (every cohort, kind and wait): OK; mutual pairs = pandas (full ordered list): OK; no editor key or human name in the result files: OK; Q5 risk deciles = pandas (n, reverts, page creations, exact median T): OK.

Rows: 7.
Made by `ec-hw2/queries/run_mongo.py` on 2026-10-24 09:56 UTC (data-v1). Full table: `mongo_summary.csv`.

| query                  | collection   |   result_rows |   median_ms |   min_ms |   max_ms |   runs |
|------------------------|--------------|---------------|-------------|----------|----------|--------|
| q1_revert_rate_by_hour | revisions    |           147 |      5229.9 |   5184.4 |   5352.7 |      7 |
| q2_top_contested_pages | revert_links |            20 |        78.2 |     77   |    101.5 |      7 |
| q3_time_to_revert      | revert_links |            27 |        50.3 |     48.4 |     52.6 |      7 |
| q4_bot_vs_human        | revert_links |             8 |       269.5 |    268.2 |    299.8 |      7 |
| q5_truth_lag_preview   | revisions    |            72 |     15147.8 |  14599.9 |  15619.7 |      7 |
| compare_mutual_reverts | revert_links |           462 |       129.3 |    127.9 |    158.2 |      7 |
| q5_risk_deciles        | revisions    |            11 |      7780.9 |   7780.9 |   7780.9 |      1 |

