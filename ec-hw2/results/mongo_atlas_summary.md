# MongoDB query timings

Target: atlas. MongoDB 8.0.34. Each query ran 7 warm times after 1 warm-up; median_ms is the median of those runs. The risk deciles ran once. Checks: Q1 = pandas (every cohort x hour x user kind): OK; Q2 = pandas (same 20 page_ids, scores rounded to 6): OK; Q3 default bucket 'over_20d' is empty: OK; Q3 bucket counts = pandas (history, history_4d): OK; Q5 known-by shares = pandas (every cohort, kind and wait): OK; mutual pairs = pandas (page, editor pair and counts; no order): OK; no editor key or human name in the result files: OK.

Rows: 7.
Made by `ec-hw2/queries/run_mongo.py` on 2026-10-27 21:43 UTC (data-v2). Full table: `mongo_atlas_summary.csv`.

| query                  | collection   |   result_rows |   median_ms |   min_ms |   max_ms |   runs |
|------------------------|--------------|---------------|-------------|----------|----------|--------|
| q1_revert_rate_by_hour | revisions    |            75 |      1414.3 |   1394.2 |   1460   |      7 |
| q2_top_contested_pages | revert_links |            20 |       467   |    459.2 |    472.4 |      7 |
| q3_time_to_revert      | revert_links |            19 |       179.8 |    175.3 |    191.6 |      7 |
| q4_bot_vs_human        | revert_links |             8 |      1347.7 |   1310.3 |   1412.2 |      7 |
| q5_truth_lag_preview   | revisions    |            36 |     57899.9 |  57229   |  59332.7 |      7 |
| compare_mutual_reverts | revert_links |           462 |      1465.2 |   1441.3 |   1538.7 |      7 |
| q5_risk_deciles        | revisions    |             0 |        46.8 |     46.8 |     46.8 |      1 |

