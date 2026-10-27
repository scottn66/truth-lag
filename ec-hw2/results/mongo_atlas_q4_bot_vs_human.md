# Mongo Q4: bot vs human share of reverts (history cohort)

Mongo Q4 (spec 3.4): bot vs human share of reverts in the history cohort, with one $facet. Input: revert_links with within_followup and by_other (self-reverts removed). made_by_reverter_kind: revert actions (distinct reverting_rev_id) made by each reverter kind, and their share. received_by_author_kind: reverted revisions by author kind, and their share. edit_revert_rate: from revisions (an uncorrelated $lookup), the revert rate of bot edits vs human edits (human = not a bot, so it includes the few 'unknown' editors); reverted = history.reverted (within 20 days, any reverter) and reverted_by_other. The result is one document with three arrays.

Rows: 8. Median time: 1,347.7 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_mongo.py` on 2026-10-27 21:43 UTC (data-v2). Full table: `mongo_atlas_q4_bot_vs_human.csv`.

| part                    | kind       | revert_actions   | reverted_revisions   | share                | edits   | reverted   | reverted_by_other   | revert_rate         | revert_rate_by_other   |
|-------------------------|------------|------------------|----------------------|----------------------|---------|------------|---------------------|---------------------|------------------------|
| made_by_reverter_kind   | registered | 11886            | 16105                | 0.8888058027368578   | <NA>    | <NA>       | <NA>                | <NA>                | <NA>                   |
| made_by_reverter_kind   | temporary  | 815              | 1024                 | 0.06094369251476856  | <NA>    | <NA>       | <NA>                | <NA>                | <NA>                   |
| made_by_reverter_kind   | bot        | 672              | 739                  | 0.05025050474837359  | <NA>    | <NA>       | <NA>                | <NA>                | <NA>                   |
| received_by_author_kind | temporary  | 7861             | 9946                 | 0.5566375643608686   | <NA>    | <NA>       | <NA>                | <NA>                | <NA>                   |
| received_by_author_kind | registered | 5563             | 7749                 | 0.43368032236400267  | <NA>    | <NA>       | <NA>                | <NA>                | <NA>                   |
| received_by_author_kind | bot        | 171              | 173                  | 0.009682113275128721 | <NA>    | <NA>       | <NA>                | <NA>                | <NA>                   |
| edit_revert_rate        | bot        | <NA>             | <NA>                 | <NA>                 | 33483   | 271        | 173                 | 0.00809365946898426 | 0.005166801063226115   |
| edit_revert_rate        | human      | <NA>             | <NA>                 | <NA>                 | 261533  | 19429      | 17695               | 0.07428890426829501 | 0.0676587658154038     |

