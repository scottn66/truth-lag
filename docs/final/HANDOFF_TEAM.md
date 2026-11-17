# Extracts for the team: what is in data/exports/ and how to rebuild it

For Wanru (MinHash LSH), Zhenni (k-anonymity and Laplace noise) and anyone making charts or slides. The files are made from the Gold and Silver Delta tables on Scott's Mac. They are not in git (`data/` is ignored); Scott shares them. Each file is under 50 MB. `data/exports/manifest.json` lists every file with its row count, size, SHA-256 and the lake table versions it was read from.

Rules for these files:
- Human editors appear only as pseudonyms (`editor_` + 10 hex digits, keyed HMAC, the same as in EC HW2). Bots keep their names. No user name, user id or editor key is exported.
- Page titles and edit comments are public Wikipedia data. In `comment`, links to user pages and contributions become `[[USER]]`, temporary-account names `~TEMP` and IP addresses `IP` (about 36,000 links and 500 names masked). A name typed as plain text, without a link, can remain. Do not quote comments on slides without checking them.
- Times are UTC. "Reverted" means reverted within 4 days (the E(L) horizon), unless a column says otherwise.

## How to rebuild

On the Mac, from the repository root, with the lake environment (`.venv-lake`, see `docs/final/STATUS.md`):

```
TRUTHLAG_HW2_DIR=$PWD/ec-hw2 .venv-lake/bin/python -m etl.exports
```

It reads the current versions of the Gold tables (listed in `manifest.json`) and overwrites `data/exports/`. It runs in about a minute. It needs the lake built first (STATUS.md, "How to rerun").

## For Wanru: MinHash LSH on comments and titles

File: `lsh_edits.parquet` (same rows in `lsh_edits.csv`). One row per edit. It holds every cohort edit reverted within 4 days (label 1) and, per cohort, a uniform random sample of the same size of edits not reverted within 4 days (label 0, seed 226).

**Changed on 2026-11-15 12:46 UTC:** the label-0 rows were re-drawn. The first version of this file (made about 10:10 UTC) under-sampled the latest edits (its editor-kind mix was off by up to 2 points). If you got the file before that time, take the new one; the schema and the label-1 rows are the same.

A fallback version of this analysis exists in `notebooks/fallback/lsh_minhash.ipynb` (built with Claude Code for Scott). Your notebook wins: if it arrives, the report uses yours. You can reuse the fallback's cleaning and the labeled pairs in `notebooks/fallback/lsh_pair_labels.csv` (fill the `human_label` column to overrule a label). The cohorts are `history` (Sep 8-10, labels from the 2026-09 dump) and `live_ext` (Oct 20 - Nov 8, labels from the stream).

| Column | Type | Meaning |
| --- | --- | --- |
| cohort_id | string | `history` or `live_ext` |
| rev_id | int64 | revision id (unique within a cohort; join key back to `gold/fact_edit`) |
| page_id | int64 | page id |
| page_title | string | history: the title in the 2026-09 dump; live_ext: the title in the edit event |
| page_ns | int64 | namespace (always 0 in these cohorts) |
| ts | timestamp (UTC) | when the edit was saved |
| comment | string | the edit summary written by the editor, with user links, temporary-account names and IPs masked (may be empty) |
| user_kind | string | `temporary`, `registered`, `bot` or `unknown`, at edit time |
| size_delta | int64 | bytes added (negative: removed) |
| is_revert | bool | the edit itself is a revert |
| seconds_to_revert | int64 | seconds from the edit to its first exact revert (null when label 0) |
| reverting_rev_id | int64 | the revision that reverted it (null when label 0) |
| label | int | 1 = reverted within 4 days, 0 = not |
| editor | string | pseudonym (humans) or bot name |

Suggested use: shingle `comment` (or `page_title + comment`), run `pyspark.ml.feature.MinHashLSH`, and check precision on a hand-labeled sample of at least 30 candidate pairs. `label` lets you ask whether near-duplicate groups are mostly reverted edits.

## For Zhenni: k-anonymity and Laplace noise

A fallback version of this analysis exists in `notebooks/fallback/privacy.ipynb` (built with Claude Code for Scott). Your notebook wins: if it arrives, the report uses yours.

| File | One row per | Columns | Use |
| --- | --- | --- | --- |
| `mart_el_curve.csv` | cohort, label source, editor kind, wait | cohort_id, label_source, user_kind (`all` = every kind), wait_label, wait_s, n_eventual (group size: eventual reverts), n_known, share_known, e_l, small_group (n_eventual < 100) | The published E(L) mart. Laplace noise on `n_known` and `n_eventual` at 2-3 epsilons; report the error of E(L). |
| `mart_el_by_burst.csv` | cohort, label source, burst group, wait | as above with burst_group (`0`, `1`, `2-4`, `5-9`, `10+`, `all`) instead of user_kind | Second published mart; small groups in `10+`. |
| `group_sizes_by_kind_hour.csv` | cohort, editor kind, UTC date, UTC hour | revisions, reverted_4d, distinct_editors, distinct_page_versions | A quasi-identifier grid (kind x date x hour) for the k-anonymity check: which cells have fewer than k editors. |
| `page_revert_summary.parquet` | cohort, page | cohort_id, page_id, current_title, namespace, edits, distinct_editors, reverted_4d, reverts_known_1h, burst_edits | Page-level release: rows with `distinct_editors < k` could single out an editor. Suppress or generalize them. |
| `page_revert_summary_top.csv` | same, pages with 5 or more edits | same | Smaller CSV of the same table, for MongoDB Charts. |

Notes: `cohort_id` in the marts and grids is `history`, `live` (Oct 20-22, the published cohort) or `live_ext` (Oct 20 - Nov 8, which contains `live`). Do not add `live` and `live_ext` together. `label_source` is `stream` or `dump`; the `live` cohort has both (dump = History snapshot 2026-10). Pick one source per series.

## For charts and slides

| File | What |
| --- | --- |
| `hypotheses_h1.csv` | H1 shares at 1 h and 48 h with 95% intervals, per series |
| `hypotheses_h3.csv` | H3 E(L) burst vs rest at 1 h and 1 d with intervals |
| `hypotheses_h4.json` | H4 counts and shares |
| `daily_counts.csv` | Bronze and Silver rows per stream and event date |
| `mart_reconciliation.csv` | Live cohort (Oct 20-22): stream label vs the 2026-10 History dump label, five classes with counts and shares |
| `label_change_by_class.csv` | Revisions whose dump label changed between snapshot 2026-09 and 2026-10, by class |
| `mart_el_curve.csv` | E(L) curve (see above) |

Figures already drawn: `docs/final/figures/flow.png` (data flow) and `docs/final/figures/el_curve.png` (E(L) curves).

## Lake versions behind this hand-off

See `data/exports/manifest.json` (`lake_versions`). At the time of writing: gold/fact_edit v3, gold/dim_page v3, gold/fact_revert_label v2 (snapshot 2026-10 loaded), gold/mart_el_curve v3, gold/mart_el_by_burst v3, silver/live_ext_revisions v1. Built at as_of 2026-11-13T23:59:59.999999Z.
