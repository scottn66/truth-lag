# Mongo Q5: truth-lag preview (share of eventual reverts known after a wait)

Mongo Q5 (spec 3.5), the truth-lag preview: live-stream signals vs the eventual revert label. It starts from revisions (both cohorts). An equality $lookup on rev_id = revert_links.reverted_rev_id (same cohort) gives T (time to revert) and, for the live cohort, K (stream delay). Eventual revert = T <= 345600 s (4 days, the horizon both cohorts share; self-reverts count). known_by = T + K for live (when the stream showed the revert) and T for history (the dump has no stream delay). Part 'known_by': for each cohort and user kind (and 'all'), the share of eventual reverts already known after each wait ['0', '1 min', '5 min', '15 min', '1 h', '6 h', '1 d', '2 d', '4 d']; groups with fewer than 100 eventual reverts are dropped. Part 'activity': the revert rate by the page's edits in the hour before the edit, with two measures (column source). source = 'page_hour', live only: a second $lookup reads page_hour (the speed layer) for the clock hour before the edit was seen; the edits earlier in the same clock hour are not in it. source = 'prev_1h', both cohorts: the sliding hour [t - 1 h, t) stored in the document (history.page_edits_prev_1h from the dump; live.page_edits_prev_1h from the stream). page_hour does not exist for September, so compare the cohorts with 'prev_1h' only. Groups with fewer than 100 edits are dropped. The live labels are provisional until 2026-10-27T00:05:00+00:00. Atlas holds the history cohort only.

Rows: 36. Median time: 59,088.3 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_mongo.py` on 2026-10-24 10:10 UTC (data-v1). Full table: `mongo_atlas_q5_truth_lag_preview.csv`.

| cohort   | user_kind   | wait   |   wait_s |   n_edits |   n_reverted_4d |   revert_rate_4d |   known |   share_known | wait_sorted   |
|----------|-------------|--------|----------|-----------|-----------------|------------------|---------|---------------|---------------|
| history  | all         | 0      |        0 |    295016 |           17646 |       0.0598137  |       0 |     0         | 01 0          |
| history  | all         | 1 min  |       60 |    295016 |           17646 |       0.0598137  |    3506 |     0.198685  | 02 1 min      |
| history  | all         | 5 min  |      300 |    295016 |           17646 |       0.0598137  |    6204 |     0.351581  | 03 5 min      |
| history  | all         | 15 min |      900 |    295016 |           17646 |       0.0598137  |    7737 |     0.438456  | 04 15 min     |
| history  | all         | 1 h    |     3600 |    295016 |           17646 |       0.0598137  |    9822 |     0.556613  | 05 1 h        |
| history  | all         | 6 h    |    21600 |    295016 |           17646 |       0.0598137  |   12900 |     0.731044  | 06 6 h        |
| history  | all         | 1 d    |    86400 |    295016 |           17646 |       0.0598137  |   15697 |     0.88955   | 07 1 d        |
| history  | all         | 2 d    |   172800 |    295016 |           17646 |       0.0598137  |   16725 |     0.947807  | 08 2 d        |
| history  | all         | 4 d    |   345600 |    295016 |           17646 |       0.0598137  |   17646 |     1         | 09 4 d        |
| history  | bot         | 0      |        0 |     33483 |             157 |       0.00468895 |       0 |     0         | 01 0          |
| history  | bot         | 1 min  |       60 |     33483 |             157 |       0.00468895 |      15 |     0.0955414 | 02 1 min      |
| history  | bot         | 5 min  |      300 |     33483 |             157 |       0.00468895 |      25 |     0.159236  | 03 5 min      |
| history  | bot         | 15 min |      900 |     33483 |             157 |       0.00468895 |      35 |     0.22293   | 04 15 min     |
| history  | bot         | 1 h    |     3600 |     33483 |             157 |       0.00468895 |      40 |     0.254777  | 05 1 h        |
| history  | bot         | 6 h    |    21600 |     33483 |             157 |       0.00468895 |      72 |     0.458599  | 06 6 h        |
| history  | bot         | 1 d    |    86400 |     33483 |             157 |       0.00468895 |     117 |     0.745223  | 07 1 d        |
| history  | bot         | 2 d    |   172800 |     33483 |             157 |       0.00468895 |     137 |     0.872611  | 08 2 d        |
| history  | bot         | 4 d    |   345600 |     33483 |             157 |       0.00468895 |     157 |     1         | 09 4 d        |
| history  | registered  | 0      |        0 |    223366 |            7623 |       0.0341278  |       0 |     0         | 01 0          |
| history  | registered  | 1 min  |       60 |    223366 |            7623 |       0.0341278  |    1075 |     0.141021  | 02 1 min      |
| history  | registered  | 5 min  |      300 |    223366 |            7623 |       0.0341278  |    2116 |     0.277581  | 03 5 min      |
| history  | registered  | 15 min |      900 |    223366 |            7623 |       0.0341278  |    2713 |     0.355897  | 04 15 min     |
| history  | registered  | 1 h    |     3600 |    223366 |            7623 |       0.0341278  |    3622 |     0.475141  | 05 1 h        |
| history  | registered  | 6 h    |    21600 |    223366 |            7623 |       0.0341278  |    5135 |     0.673619  | 06 6 h        |
| history  | registered  | 1 d    |    86400 |    223366 |            7623 |       0.0341278  |    6483 |     0.850453  | 07 1 d        |
| history  | registered  | 2 d    |   172800 |    223366 |            7623 |       0.0341278  |    7060 |     0.926145  | 08 2 d        |
| history  | registered  | 4 d    |   345600 |    223366 |            7623 |       0.0341278  |    7623 |     1         | 09 4 d        |
| history  | temporary   | 0      |        0 |     38164 |            9863 |       0.258437   |       0 |     0         | 01 0          |
| history  | temporary   | 1 min  |       60 |     38164 |            9863 |       0.258437   |    2414 |     0.244753  | 02 1 min      |
| history  | temporary   | 5 min  |      300 |     38164 |            9863 |       0.258437   |    4060 |     0.411639  | 03 5 min      |

(first 30 of 36 rows)
