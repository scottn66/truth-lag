# Mongo Q1: revert rate by hour of day and user kind

Mongo Q1 (spec 3.1): the revert rate by hour of day (UTC, hour of the edit) and user kind (bot, temporary = logged out, registered, unknown), for both cohorts. History cohort: reverted = history.reverted (reverted within 20 days, self-reverts included). Live cohort: reverted = a revert_links document (found with $lookup) with within_followup (within 4 days). The live half is added with $unionWith, so the $lookup runs only for live documents. Output: cohort, hour_utc, user_kind, edits, reverted, revert_rate.

Rows: 75. Median time: 1,418.9 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_mongo.py` on 2026-10-24 10:10 UTC (data-v1). Full table: `mongo_atlas_q1_revert_rate_by_hour.csv`.

| cohort   |   hour_utc | user_kind   |   edits |   reverted |   revert_rate |
|----------|------------|-------------|---------|------------|---------------|
| history  |          0 | bot         |    2432 |          8 |    0.00328947 |
| history  |          0 | registered  |    9669 |        314 |    0.0324749  |
| history  |          0 | temporary   |    1298 |        326 |    0.251156   |
| history  |          1 | bot         |    1559 |         11 |    0.00705581 |
| history  |          1 | registered  |    8726 |        282 |    0.0323172  |
| history  |          1 | temporary   |    1437 |        417 |    0.290188   |
| history  |          2 | bot         |    3900 |          4 |    0.00102564 |
| history  |          2 | registered  |    8698 |        305 |    0.0350655  |
| history  |          2 | temporary   |    1545 |        443 |    0.286731   |
| history  |          3 | bot         |    4556 |         36 |    0.00790167 |
| history  |          3 | registered  |    9043 |        321 |    0.0354971  |
| history  |          3 | temporary   |    1265 |        368 |    0.290909   |
| history  |          4 | bot         |    2271 |          9 |    0.00396301 |
| history  |          4 | registered  |    7970 |        271 |    0.0340025  |
| history  |          4 | temporary   |    1232 |        348 |    0.282468   |
| history  |          5 | bot         |    2029 |         13 |    0.0064071  |
| history  |          5 | registered  |    6779 |        281 |    0.0414515  |
| history  |          5 | temporary   |    1195 |        309 |    0.258577   |
| history  |          6 | bot         |    1531 |          5 |    0.00326584 |
| history  |          6 | registered  |    6558 |        255 |    0.0388838  |
| history  |          6 | temporary   |    1296 |        359 |    0.277006   |
| history  |          7 | bot         |    1784 |         21 |    0.0117713  |
| history  |          7 | registered  |    6700 |        296 |    0.0441791  |
| history  |          7 | temporary   |    1336 |        369 |    0.276198   |
| history  |          8 | bot         |    1694 |         28 |    0.0165289  |
| history  |          8 | registered  |    6863 |        275 |    0.0400699  |
| history  |          8 | temporary   |    1358 |        354 |    0.260677   |
| history  |          9 | bot         |     835 |         10 |    0.011976   |
| history  |          9 | registered  |    7080 |        370 |    0.0522599  |
| history  |          9 | temporary   |    1408 |        326 |    0.231534   |

(first 30 of 75 rows)
