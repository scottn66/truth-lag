# Mongo Q5: truth-lag preview (share of eventual reverts known after a wait) - page activity before the edit

Mongo Q5 (spec 3.5), the truth-lag preview: live-stream signals vs the eventual revert label. It starts from revisions (both cohorts). An equality $lookup on rev_id = revert_links.reverted_rev_id (same cohort) gives T (time to revert) and, for the live cohort, K (stream delay). Eventual revert = T <= 345600 s (4 days, the horizon both cohorts share; self-reverts count). known_by = T + K for live (when the stream showed the revert) and T for history (the dump has no stream delay). Part 'known_by': for each cohort and user kind (and 'all'), the share of eventual reverts already known after each wait ['0', '1 min', '5 min', '15 min', '1 h', '6 h', '1 d', '2 d', '4 d']; groups with fewer than 100 eventual reverts are dropped. Part 'activity': the revert rate by the page's edits in the hour before the edit, with two measures (column source). source = 'page_hour', live only: a second $lookup reads page_hour (the speed layer) for the clock hour before the edit was seen; the edits earlier in the same clock hour are not in it. source = 'prev_1h', both cohorts: the sliding hour [t - 1 h, t) stored in the document (history.page_edits_prev_1h from the dump; live.page_edits_prev_1h from the stream). page_hour does not exist for September, so compare the cohorts with 'prev_1h' only. Groups with fewer than 100 edits are dropped. The stream labels of the live cohort are provisional until 2026-10-27T00:05:00+00:00. Atlas holds the history cohort only.

Rows: 15.
Made by `ec-hw2/queries/run_mongo.py` on 2026-10-27 21:27 UTC (data-v2). Full table: `mongo_q5_truth_lag_preview_activity.csv`.

| cohort   | source    | prev_hour_edits   |   prev_hour_edits_from |   n_edits |   n_reverted_4d |   revert_rate_4d |
|----------|-----------|-------------------|------------------------|-----------|-----------------|------------------|
| history  | prev_1h   | 0                 |                      0 |    202410 |           11390 |        0.0562719 |
| history  | prev_1h   | 1                 |                      1 |     42155 |            2519 |        0.0597557 |
| history  | prev_1h   | 2-4               |                      2 |     32697 |            2627 |        0.0803438 |
| history  | prev_1h   | 5-9               |                      5 |     11888 |             767 |        0.0645188 |
| history  | prev_1h   | 10+               |                     10 |      5866 |             343 |        0.0584726 |
| live     | page_hour | 0                 |                      0 |    246112 |           15601 |        0.0633898 |
| live     | page_hour | 1                 |                      1 |     13124 |             816 |        0.0621762 |
| live     | page_hour | 2-4               |                      2 |     11658 |             932 |        0.0799451 |
| live     | page_hour | 5-9               |                      5 |      5387 |             313 |        0.0581028 |
| live     | page_hour | 10+               |                     10 |      3185 |             156 |        0.0489796 |
| live     | prev_1h   | 0                 |                      0 |    190392 |           11521 |        0.060512  |
| live     | prev_1h   | 1                 |                      1 |     39277 |            2464 |        0.0627339 |
| live     | prev_1h   | 2-4               |                      2 |     30782 |            2612 |        0.0848548 |
| live     | prev_1h   | 5-9               |                      5 |     11929 |             782 |        0.0655545 |
| live     | prev_1h   | 10+               |                     10 |      7086 |             439 |        0.0619531 |

