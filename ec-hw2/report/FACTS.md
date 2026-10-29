# FACTS: the key numbers of EC HW2

Made by `ec-hw2/report/build_facts.py` on 2026-10-29 08:59 UTC (data-v2). Do not edit by hand: run the script again.

- Use these numbers in the report. Each notebook checks its numbers against this table in its last cell.
- **FINAL**: the number will not change. **PROVISIONAL**: it depends on the live cohort, whose stream labels are final after 2026-10-27T00:05:00Z (Mon 2026-10-26 5:05 PM PT); or it is a comparison timing that `results/comparison.csv` labels draft; or it is a modeling-pain score that is still a draft by Claude Code (`comparison/pain.csv`). Live cohort now: **FINAL** (newest parsed event: 2026-10-27T20:59:59Z).
- Horizons: history keys count reverts within 20 days, unless the key ends in `_4d` (within 4 days). Live keys count reverts within 4 days, and the live follow-up is still short. Compare the live cohort only with the `_4d` history keys.
- Comparison timings come only from `results/comparison.csv` (`cmp_ms_*`: median, min and max). The `mongo_ms_*` and `cypher_ms_*` times of the same queries are single-engine runs: do not compare them.
- Percent values are in percent (7.43 means 7.43%). Times are UTC. Human editors appear only as pseudonyms.
- Where each number is shown: `history_`, `wikistats_`, `live_`, `capture_` and `example_` in notebook 01; `mongo_` and `atlas_` in notebook 02; `neo4j_`, `cypher_`, `contested_` and `top20_` in notebook 03; `cmp_` and `shard_` in notebook 04; `late_` and `risk_` in notebook 05. `example_` is for the Motivation. Numbers in the notebook text carry a fact marker; `report/sync_notebook_text.py` copies them from here.

| key | value | unit | source file | status |
|---|---|---|---|---|
| history_file_rows | 300,564 | rows | data/tables/_SUCCESS_history.json | FINAL |
| history_slim_file_rows | 5,266,843 | rows | data/tables/_SUCCESS_history.json | FINAL |
| history_dropped_namespace_not_0 | 4,265 | rows | data/tables/history_summary.json | FINAL |
| history_dropped_null_same_sha1 | 568 | rows | data/tables/history_summary.json | FINAL |
| history_dropped_null_comment | 715 | rows | data/tables/history_summary.json | FINAL |
| history_revisions | 295,016 | revisions | data/tables/_SUCCESS_history.json | FINAL |
| history_pages | 165,415 | pages | data/tables/history_summary.json | FINAL |
| history_editors | 37,177 | editors | data/tables/history_summary.json | FINAL |
| history_edits_bot | 33,483 | revisions | data/tables/history_summary.json | FINAL |
| history_edits_temporary | 38,164 | revisions | data/tables/history_summary.json | FINAL |
| history_edits_registered | 223,366 | revisions | data/tables/history_summary.json | FINAL |
| history_edits_unknown | 3 | revisions | data/tables/history_summary.json | FINAL |
| wikistats_content_edits | 298,802 | edits | Wikistats (stats.wikimedia.org), content edits 2026-09-08..10; plan, checked 2026-10-24 | FINAL |
| history_file_vs_wikistats_pct | +0.59 | % | data/tables/_SUCCESS_history.json | FINAL |
| history_revisions_vs_wikistats_pct | -1.27 | % | data/tables/_SUCCESS_history.json | FINAL |
| history_reverted_20d | 19,700 | revisions (reverted within 20 days) | data/tables/history_summary.json | FINAL |
| history_revert_rate_pct | 6.68 | % (reverted within 20 days) | data/tables/history_summary.json | FINAL |
| history_revert_rate_non_bot_pct | 7.43 | % (reverted within 20 days) | data/tables/history_summary.json | FINAL |
| history_revert_rate_temporary_pct | 27.32 | % (reverted within 20 days) | data/tables/history_summary.json | FINAL |
| history_revert_rate_registered_pct | 4.03 | % (reverted within 20 days) | data/tables/history_summary.json | FINAL |
| history_revert_rate_bot_pct | 0.81 | % (reverted within 20 days) | data/tables/history_summary.json | FINAL |
| history_reverted_any_time | 19,858 | revisions (reverted at any time before the snapshot) | data/tables/history_summary.json | FINAL |
| history_median_T_s | 3,660 | s (history reverts within 20 days) | data/tables/history_summary.json | FINAL |
| history_median_T_h | 1.02 | h (history reverts within 20 days) | data/tables/history_summary.json | FINAL |
| history_median_T_non_bot_h | 0.96 | h (history reverts within 20 days, non-bot authors) | data/tables/history_summary.json | FINAL |
| history_median_T_temporary_h | 0.33 | h (history reverts within 20 days) | data/tables/history_summary.json | FINAL |
| history_median_T_registered_h | 3.03 | h (history reverts within 20 days) | data/tables/history_summary.json | FINAL |
| history_median_T_bot_h | 47.23 | h (history reverts within 20 days) | data/tables/history_summary.json | FINAL |
| history_T_within_1h_pct | 49.86 | % of history reverts within 20 days | data/tables/history_summary.json | FINAL |
| history_T_within_1d_pct | 79.68 | % of history reverts within 20 days | data/tables/history_summary.json | FINAL |
| history_T_over_7d_pct | 6.32 | % of history reverts within 20 days | data/tables/history_summary.json | FINAL |
| history_T_p90_d | 4.21 | days (history reverts within 20 days) | data/tables/history_summary.json | FINAL |
| history_self_revert_pct | 9.29 | % of history reverts within 20 days | data/tables/history_summary.json | FINAL |
| history_reverted_4d | 17,646 | revisions (reverted within 4 days) | data/tables/history_revert_links.parquet | FINAL |
| history_median_T_4d_s | 1,942 | s (history reverts within 4 days, the live horizon) | data/tables/history_revert_links.parquet | FINAL |
| history_median_T_4d_h | 0.54 | h (history reverts within 4 days, the live horizon) | data/tables/history_revert_links.parquet | FINAL |
| history_T_within_1h_4d_pct | 55.66 | % of history reverts within 4 days, the live horizon | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| history_T_within_1d_4d_pct | 88.96 | % of history reverts within 4 days, the live horizon | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| history_revert_links | 19,858 | rows | data/tables/history_summary.json | FINAL |
| history_links_by_other_20d | 17,868 | rows | data/tables/history_summary.json | FINAL |
| history_tag_agreement_pct | 99.52 | % of revisions | data/tables/history_summary.json | FINAL |
| history_tag_share_T_lt_1h_pct | 98.15 | % with mw-reverted tag | data/tables/history_summary.json | FINAL |
| history_tag_share_T_1h_1d_pct | 96.26 | % with mw-reverted tag | data/tables/history_summary.json | FINAL |
| history_tag_share_T_1d_7d_pct | 90.35 | % with mw-reverted tag | data/tables/history_summary.json | FINAL |
| history_tag_share_T_7d_20d_pct | 79.37 | % with mw-reverted tag | data/tables/history_summary.json | FINAL |
| history_tag_share_T_gt_20d_pct | 58.23 | % with mw-reverted tag | data/tables/history_summary.json | FINAL |
| history_tag_share_T_not_reverted_pct | 0.16 | % with mw-reverted tag | data/tables/history_summary.json | FINAL |
| live_page_change_events | 1,231,427 | events | data/tables/live_summary.json | FINAL |
| live_revisions | 279,466 | revisions | data/tables/_SUCCESS_live.json | FINAL |
| live_dropped_namespace_not_0 | 379,956 | events | data/tables/live_summary.json | FINAL |
| live_dropped_outside_window | 538,090 | events | data/tables/live_summary.json | FINAL |
| live_dropped_not_edit | 33,915 | events | data/tables/live_summary.json | FINAL |
| live_reverted_4d | 17,818 | revisions (reverted within 4 days) | data/tables/live_summary.json | FINAL |
| live_revert_rate_pct | 6.38 | % (reverted within 4 days) | data/tables/live_summary.json | FINAL |
| live_revert_rate_human_pct | 7.14 | % (reverted within 4 days) | data/tables/live_summary.json | FINAL |
| live_revert_rate_temporary_pct | 26.91 | % (reverted within 4 days) | data/tables/live_summary.json | FINAL |
| live_revert_rate_registered_pct | 3.74 | % (reverted within 4 days) | data/tables/live_summary.json | FINAL |
| live_revert_rate_bot_pct | 0.44 | % (reverted within 4 days) | data/tables/live_summary.json | FINAL |
| live_median_T_s | 1,344 | s (live reverts within 4 days; the follow-up is still short) | data/tables/live_summary.json | FINAL |
| live_median_T_h | 0.37 | h (live reverts within 4 days; the follow-up is still short) | data/tables/live_summary.json | FINAL |
| live_T_within_1h_pct | 57.97 | % of live reverts within 4 days; the follow-up is still short | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| live_T_within_1d_pct | 89.44 | % of live reverts within 4 days; the follow-up is still short | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| live_K_median_s | 3.44 | s | data/tables/live_summary.json | FINAL |
| live_K_p90_s | 8.57 | s | data/tables/live_summary.json | FINAL |
| live_K_p99_s | 17.78 | s | data/tables/live_summary.json | FINAL |
| live_revert_risk_coverage_pct | 98.15 | % of edits | data/tables/live_summary.json | FINAL |
| live_tag_confirmed_range_le_15_pct | 99.42 | % of reverted revisions (complete ranges only) | data/tables/live_summary.json | FINAL |
| live_tag_confirmed_range_le_15_n | 16,761 | reverted revisions (complete ranges only) | data/tables/live_summary.json | FINAL |
| live_tag_confirmed_range_gt_15_pct | 0.00 | % of reverted revisions (complete ranges only) | data/tables/live_summary.json | FINAL |
| live_tag_confirmed_range_gt_15_n | 284 | reverted revisions (complete ranges only) | data/tables/live_summary.json | FINAL |
| live_tag_confirmed_range_incomplete_pct | 67.27 | % of reverted revisions whose revert range starts before the capture (size unknown) | data/tables/live_summary.json | FINAL |
| live_tag_confirmed_range_incomplete_n | 773 | reverted revisions (range starts before the capture; range_size is a lower bound) | data/tables/live_summary.json | FINAL |
| live_revert_events | 52,112 | revert events (all namespaces) | data/tables/live_summary.json | FINAL |
| live_revert_events_newest_not_parent | 2,209 | revert events | data/tables/live_summary.json | FINAL |
| live_newest_meta_dt | 2026-10-27T20:59:59Z | UTC (newest parsed event) | data/tables/_SUCCESS_live.json | FINAL |
| live_final_after | 2026-10-27T00:05:00Z | UTC | ec-hw2/config.py | FINAL |
| live_followup_max_d | 7.87 | days | data/tables/live_revisions.parquet | FINAL |
| live_followup_min_d | 4.88 | days | data/tables/live_revisions.parquet | FINAL |
| live_followup_ge_4d_pct | 100.00 | % of live edits followed for 4 days or more | data/tables/live_revisions.parquet | FINAL |
| capture_page_change_first_utc | 2026-10-19T23:00:00Z | UTC | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_page_change_last_utc | 2026-10-27T20:59:59Z | UTC (newest parsed event) | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_page_change_events | 1,231,427 | events | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_page_change_gaps | 0 | gaps over 120 s | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_page_change_files_cut_short | 27 | of 232 files | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_page_change_gap_s_total | 0 | s | data/parsed/capture_gaps.csv | FINAL |
| capture_revert_risk_first_utc | 2026-10-19T23:00:00Z | UTC | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_revert_risk_last_utc | 2026-10-27T20:59:58Z | UTC (newest parsed event) | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_revert_risk_events | 789,634 | events | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_revert_risk_gaps | 3 | gaps over 120 s | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_revert_risk_files_cut_short | 28 | of 230 files | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_revert_risk_gap_s_total | 850 | s | data/parsed/capture_gaps.csv | FINAL |
| capture_tags_first_utc | 2026-10-17T01:30:18Z | UTC | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_tags_last_utc | 2026-10-27T20:59:59Z | UTC (newest parsed event) | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_tags_events | 1,603,253 | events | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_tags_gaps | 0 | gaps over 120 s | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_tags_files_cut_short | 50 | of 286 files | data/parsed/_SUCCESS_parsed.json | FINAL |
| capture_tags_gap_s_total | 0 | s | data/parsed/capture_gaps.csv | FINAL |
| mongo_revisions_docs | 574,482 | documents | data/tables/_SUCCESS_mongo_local.json | FINAL |
| mongo_revert_links_docs | 38,216 | documents | data/tables/_SUCCESS_mongo_local.json | FINAL |
| mongo_tag_events_docs | 99,606 | documents | data/tables/_SUCCESS_mongo_local.json | FINAL |
| mongo_late_reverts_docs | 4,350 | documents | data/tables/_SUCCESS_mongo_local.json | FINAL |
| mongo_page_hour_docs | 605,017 | documents | data/tables/_SUCCESS_page_hour.json | FINAL |
| mongo_indexes | 7 | indexes | data/tables/_SUCCESS_mongo_local.json | FINAL |
| mongo_index_list | revisions.page.id_1_ts_1; revisions.user.id_1; revisions.history.reverted_1; revisions.cohort_1_ts_1; revert_links.reverted_rev_id_1; revert_links.page_id_1; revert_links.cohort_1_page_id_1 |  | data/tables/_SUCCESS_mongo_local.json | FINAL |
| mongo_q1_history_temporary_hourly_min_pct | 22.24 | % | ec-hw2/results/mongo_q1_revert_rate_by_hour.csv | FINAL |
| mongo_q1_history_temporary_hourly_max_pct | 30.41 | % | ec-hw2/results/mongo_q1_revert_rate_by_hour.csv | FINAL |
| mongo_q1_history_temporary_peak_hour_utc | 19 | hour (UTC) | ec-hw2/results/mongo_q1_revert_rate_by_hour.csv | FINAL |
| mongo_q1_history_registered_hourly_min_pct | 3.23 | % | ec-hw2/results/mongo_q1_revert_rate_by_hour.csv | FINAL |
| mongo_q1_history_registered_hourly_max_pct | 5.71 | % | ec-hw2/results/mongo_q1_revert_rate_by_hour.csv | FINAL |
| mongo_q1_history_registered_peak_hour_utc | 11 | hour (UTC) | ec-hw2/results/mongo_q1_revert_rate_by_hour.csv | FINAL |
| mongo_q1_history_temporary_vs_registered_ratio | 6.8 | times | ec-hw2/results/mongo_q1_revert_rate_by_hour.csv | FINAL |
| mongo_q2_top_page_title | Personality_and_image_of_Elizabeth_II |  | ec-hw2/results/mongo_q2_top_contested_pages.csv | FINAL |
| mongo_q2_top_page_id | 11383948 |  | ec-hw2/results/mongo_q2_top_contested_pages.csv | FINAL |
| mongo_q2_top_page_score | 0.928571 | revert actions per human edit | ec-hw2/results/mongo_q2_top_contested_pages.csv | FINAL |
| mongo_q2_top_page_revert_actions | 13 | revert actions | ec-hw2/results/mongo_q2_top_contested_pages.csv | FINAL |
| mongo_q2_top_page_edits | 14 | human edits | ec-hw2/results/mongo_q2_top_contested_pages.csv | FINAL |
| mongo_q2_top5_titles | Personality_and_image_of_Elizabeth_II; Watergate_scandal; PB&J_Otter; Jim_Queen; Pororo_the_Little_Penguin |  | ec-hw2/results/mongo_q2_top_contested_pages.csv | FINAL |
| mongo_q2_contested_in_top20 | 20 | pages | ec-hw2/results/mongo_q2_top_contested_pages.csv | FINAL |
| mongo_q3_history_lt_1min_pct | 17.61 | % of history reverts within 20 days | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| mongo_q3_history_buckets | 11 | non-empty buckets (history reverts within 20 days) | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| mongo_q3_history_4d_lt_1min_pct | 19.66 | % of history reverts within 4 days; compare with live | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| mongo_q3_history_4d_buckets | 8 | non-empty buckets (history reverts within 4 days; compare with live) | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| mongo_q3_live_lt_1min_pct | 23.28 | % of live reverts within 4 days; the follow-up is still short | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| mongo_q3_live_buckets | 8 | non-empty buckets (live reverts within 4 days; the follow-up is still short) | ec-hw2/results/mongo_q3_time_to_revert.csv | FINAL |
| mongo_q4_revert_actions_total | 13,373 | revert actions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_reverted_revisions_total | 17,868 | revisions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_made_by_bot_pct | 5.03 | % of revert actions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_made_by_bot_revisions_pct | 4.14 | % of reverted revisions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_received_by_bot_pct | 0.97 | % of reverted revisions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_made_by_registered_pct | 88.88 | % of revert actions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_made_by_registered_revisions_pct | 90.13 | % of reverted revisions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_received_by_registered_pct | 43.37 | % of reverted revisions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_made_by_temporary_pct | 6.09 | % of revert actions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_made_by_temporary_revisions_pct | 5.73 | % of reverted revisions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_received_by_temporary_pct | 55.66 | % of reverted revisions | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_bot_edit_revert_rate_pct | 0.81 | % | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q4_human_edit_revert_rate_pct | 7.43 | % | ec-hw2/results/mongo_q4_bot_vs_human.csv | FINAL |
| mongo_q5_history_reverts_4d | 17,646 | revisions | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_history_revert_rate_4d_pct | 5.98 | % | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_history_known_1min_pct | 19.87 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_history_known_1h_pct | 55.66 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_history_known_1d_pct | 88.96 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_history_known_1h_temporary_pct | 62.43 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_history_known_1h_registered_pct | 47.51 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_live_reverts_4d | 17,818 | revisions | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_live_revert_rate_4d_pct | 6.38 | % | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_live_known_1min_pct | 22.37 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_live_known_1h_pct | 57.95 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_live_known_1d_pct | 89.44 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_live_known_1h_temporary_pct | 65.06 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_q5_live_known_1h_registered_pct | 49.69 | % of 4-day reverts | ec-hw2/results/mongo_q5_truth_lag_preview.csv | FINAL |
| mongo_ms_q1_revert_rate_by_hour | 5,362.2 | ms (median of 7) | ec-hw2/results/mongo_summary.csv | FINAL |
| mongo_ms_q2_top_contested_pages | 76.9 | ms (median of 7; single-engine run, not for the comparison: use cmp_ms_*) | ec-hw2/results/mongo_summary.csv | FINAL |
| mongo_ms_q3_time_to_revert | 50.5 | ms (median of 7) | ec-hw2/results/mongo_summary.csv | FINAL |
| mongo_ms_q4_bot_vs_human | 270.8 | ms (median of 7) | ec-hw2/results/mongo_summary.csv | FINAL |
| mongo_ms_q5_truth_lag_preview | 15,541.7 | ms (median of 7) | ec-hw2/results/mongo_summary.csv | FINAL |
| mongo_ms_compare_mutual_reverts | 128.5 | ms (median of 7; single-engine run, not for the comparison: use cmp_ms_*) | ec-hw2/results/mongo_summary.csv | FINAL |
| mongo_ms_q5_risk_deciles | 7,908.1 | ms (median of 1) | ec-hw2/results/mongo_summary.csv | FINAL |
| atlas_estimate_mb | 229.7 | MB (budget 400, limit 512) | ec-hw2/load_mongo.py --target atlas --estimate-only | FINAL |
| neo4j_editor_count | 37,546 | nodes | data/neo4j/_SUCCESS_load_neo4j_local.json | FINAL |
| neo4j_page_count | 165,415 | nodes | data/neo4j/_SUCCESS_load_neo4j_local.json | FINAL |
| neo4j_edited_count | 295,013 | relationships | data/neo4j/_SUCCESS_load_neo4j_local.json | FINAL |
| neo4j_reverted_count | 13,269 | relationships | data/neo4j/_SUCCESS_load_neo4j_local.json | FINAL |
| contested_pages_total | 126 | pages | data/neo4j/_SUCCESS_load_neo4j_local.json | FINAL |
| cypher_q1_mutual_pairs | 462 | pairs | ec-hw2/results/cypher_q1_mutual_reverts_total.csv | FINAL |
| cypher_q1_pages | 397 | pages | ec-hw2/results/cypher_q1_mutual_reverts_total.csv | FINAL |
| cypher_q1_editors | 631 | editors | ec-hw2/results/cypher_q1_mutual_reverts_total.csv | FINAL |
| cypher_q1_pairs_with_bot | 25 | pairs | ec-hw2/results/cypher_q1_mutual_reverts_total.csv | FINAL |
| top20_pages_with_mutual_pair | 18 | of 20 pages | ec-hw2/results/cypher_q1_mutual_reverts.csv + mongo_q2_top_contested_pages.csv | FINAL |
| top20_mutual_pairs | 51 | of 462 pairs | ec-hw2/results/cypher_q1_mutual_reverts.csv + mongo_q2_top_contested_pages.csv | FINAL |
| top20_mutual_pairs_pct | 11.04 | % of mutual pairs | ec-hw2/results/cypher_q1_mutual_reverts.csv + mongo_q2_top_contested_pages.csv | FINAL |
| cypher_q2_pagerank_iterations | 111 | iterations until PageRank converged | ec-hw2/results/_SUCCESS_cypher_queries.json | FINAL |
| cypher_q2_top_pagerank_editor | ClueBot NG | (bot) | ec-hw2/results/cypher_q2_central_reverters.csv | FINAL |
| cypher_q2_top_pagerank | 87.58 | PageRank score (REVERSE projection, converged after 111 iterations) | ec-hw2/results/cypher_q2_central_reverters.csv | FINAL |
| cypher_q2_top_reverts_made | 592 | revert actions | ec-hw2/results/cypher_q2_central_reverters.csv | FINAL |
| cypher_q2_bots_in_top20 | 2 | of 20 (by PageRank) | ec-hw2/results/cypher_q2_central_reverters.csv | FINAL |
| cypher_q2_pagerank_fewest_reverts_editor | editor_350d99a245 | (temporary), in the PageRank top 20 | ec-hw2/results/cypher_q2_central_reverters.csv | FINAL |
| cypher_q2_pagerank_fewest_reverts_rank | 20 | rank by PageRank | ec-hw2/results/cypher_q2_central_reverters.csv | FINAL |
| cypher_q2_pagerank_fewest_reverts_made | 1 | revert actions | ec-hw2/results/cypher_q2_central_reverters.csv | FINAL |
| cypher_q2_top_human_pagerank | 38.66 | PageRank score (REVERSE projection, converged after 111 iterations), editor_5d9d202d8d | ec-hw2/results/cypher_q2_central_reverters_humans.csv | FINAL |
| cypher_q2_top_by_degree_editor | ClueBot NG | (bot), who reverts the most | ec-hw2/results/cypher_q2_central_reverters_by_degree.csv | FINAL |
| cypher_q2_top_by_degree_out_degree | 591 | REVERTED relationships out (one per reverted editor and page) | ec-hw2/results/cypher_q2_central_reverters_by_degree.csv | FINAL |
| cypher_q2_top_by_degree_reverts_made | 592 | revert actions | ec-hw2/results/cypher_q2_central_reverters_by_degree.csv | FINAL |
| cypher_q3_louvain_communities | 28,615 | communities (all; most are 1 editor with no revert) | ec-hw2/results/cypher_q3_conflict_communities_louvain_stats.csv | FINAL |
| cypher_q3_louvain_modularity | 0.9142 |  | ec-hw2/results/cypher_q3_conflict_communities_louvain_stats.csv | FINAL |
| cypher_q3_communities_2plus | 1,191 | communities with 2 or more editors | ec-hw2/results/cypher_q3_conflict_communities_community_sizes.csv | FINAL |
| cypher_q3_communities_1 | 27,424 | communities of 1 editor (no revert) | ec-hw2/results/cypher_q3_conflict_communities_community_sizes.csv | FINAL |
| cypher_q3_largest_community_editors | 564 | editors | ec-hw2/results/cypher_q3_conflict_communities.csv | FINAL |
| cypher_q3_largest_community_reverts | 661 | revert actions inside the community | ec-hw2/results/cypher_q3_conflict_communities.csv | FINAL |
| cypher_q3_largest_community_top_reverter | ClueBot NG | the editor with the most revert actions in the community | ec-hw2/results/cypher_q3_conflict_communities.csv | FINAL |
| cypher_q3_largest_community_star_share_pct | 69.1 | % of the community's REVERTED relationships that touch its top reverter | ec-hw2/results/cypher_q3_conflict_communities.csv | FINAL |
| cypher_q3_top10_star_share_min_pct | 9.6 | % (star share, lowest of the top 10 communities) | ec-hw2/results/cypher_q3_conflict_communities.csv | FINAL |
| cypher_q3_top10_star_share_max_pct | 81.8 | % (star share, highest of the top 10 communities) | ec-hw2/results/cypher_q3_conflict_communities.csv | FINAL |
| cypher_q3_largest_community_top_page | Désiré_Doué | the page with the most revert actions in the community (see the share) | ec-hw2/results/cypher_q3_conflict_communities.csv | FINAL |
| cypher_q3_largest_community_top_page_share_pct | 1.36 | % of the community's revert actions | ec-hw2/results/cypher_q3_conflict_communities.csv | FINAL |
| cypher_q3_largest_wcc_editors | 7,081 | editors | ec-hw2/results/cypher_q3_conflict_communities_wcc_largest.csv | FINAL |
| cypher_q3_editors_without_revert_pct | 73.04 | % of editors | ec-hw2/results/cypher_q3_conflict_communities_wcc_sizes.csv | FINAL |
| cypher_q3_largest_wcc_pct | 18.86 | % of editors | ec-hw2/results/cypher_q3_conflict_communities_wcc_sizes.csv | FINAL |
| cypher_q4_top_page_title | PB&J_Otter |  | ec-hw2/results/cypher_q4_pages_most_warring_editors.csv | FINAL |
| cypher_q4_top_page_warring_editors | 10 | editors | ec-hw2/results/cypher_q4_pages_most_warring_editors.csv | FINAL |
| cypher_q4_top_page_mutual_pairs | 9 | pairs | ec-hw2/results/cypher_q4_pages_most_warring_editors.csv | FINAL |
| cypher_q5_top_pair_shared_pages | 4 | contested pages | ec-hw2/results/cypher_q5_two_hop_contested.csv | FINAL |
| cypher_ms_q1_mutual_reverts | 261.2 | ms (median of 7; single-engine run, not for the comparison: use cmp_ms_*) | ec-hw2/results/cypher_summary.csv | FINAL |
| cypher_ms_q2_central_reverters | 206.1 | ms (median of 7) | ec-hw2/results/cypher_summary.csv | FINAL |
| cypher_ms_q3_conflict_communities | 115.8 | ms (median of 7) | ec-hw2/results/cypher_summary.csv | FINAL |
| cypher_ms_q4_pages_most_warring_editors | 32.0 | ms (median of 7) | ec-hw2/results/cypher_summary.csv | FINAL |
| cypher_ms_q5_two_hop_contested | 21.8 | ms (median of 7) | ec-hw2/results/cypher_summary.csv | FINAL |
| cypher_ms_compare_top_contested | 119.4 | ms (median of 7; single-engine run, not for the comparison: use cmp_ms_*) | ec-hw2/results/cypher_summary.csv | FINAL |
| cmp_loc_top_mongodb | 62 | lines (non-blank, non-comment) | ec-hw2/results/comparison.csv | FINAL |
| cmp_chars_top_mongodb | 1,040 | characters of query code | ec-hw2/results/comparison.csv | FINAL |
| cmp_bracket_lines_top_mongodb | 22 | lines with only brackets or commas | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_top_mongodb | 71.5 | ms (final, median of 21 runs in 3 rounds) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_min_top_mongodb | 67.7 | ms (fastest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_max_top_mongodb | 73.3 | ms (slowest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_faster_than_top_mongodb | Neo4j | engines it beats: its slowest run is faster than their fastest | ec-hw2/results/comparison.csv | FINAL |
| cmp_pain_top_mongodb | 3 | of 5 (draft by Claude Code; the Comparison+viz owner re-scores it) | ec-hw2/comparison/pain.csv | PROVISIONAL |
| cmp_rows_top_mongodb | 20 | rows | ec-hw2/results/comparison.csv | FINAL |
| cmp_loc_top_neo4j | 18 | lines (non-blank, non-comment) | ec-hw2/results/comparison.csv | FINAL |
| cmp_chars_top_neo4j | 768 | characters of query code | ec-hw2/results/comparison.csv | FINAL |
| cmp_bracket_lines_top_neo4j | 0 | lines with only brackets or commas | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_top_neo4j | 106.2 | ms (final, median of 21 runs in 3 rounds) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_min_top_neo4j | 100.4 | ms (fastest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_max_top_neo4j | 130.9 | ms (slowest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_faster_than_top_neo4j | none | engines it beats: its slowest run is faster than their fastest | ec-hw2/results/comparison.csv | FINAL |
| cmp_pain_top_neo4j | 3 | of 5 (draft by Claude Code; the Comparison+viz owner re-scores it) | ec-hw2/comparison/pain.csv | PROVISIONAL |
| cmp_rows_top_neo4j | 20 | rows | ec-hw2/results/comparison.csv | FINAL |
| cmp_loc_top_sqlite | 38 | lines (non-blank, non-comment) | ec-hw2/results/comparison.csv | FINAL |
| cmp_chars_top_sqlite | 1,224 | characters of query code | ec-hw2/results/comparison.csv | FINAL |
| cmp_bracket_lines_top_sqlite | 4 | lines with only brackets or commas | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_top_sqlite | 33.4 | ms (final, median of 21 runs in 3 rounds) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_min_top_sqlite | 28.8 | ms (fastest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_max_top_sqlite | 53.7 | ms (slowest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_faster_than_top_sqlite | MongoDB; Neo4j | engines it beats: its slowest run is faster than their fastest | ec-hw2/results/comparison.csv | FINAL |
| cmp_pain_top_sqlite | 2 | of 5 (draft by Claude Code; the Comparison+viz owner re-scores it) | ec-hw2/comparison/pain.csv | PROVISIONAL |
| cmp_rows_top_sqlite | 20 | rows | ec-hw2/results/comparison.csv | FINAL |
| cmp_loc_mutual_mongodb | 52 | lines (non-blank, non-comment) | ec-hw2/results/comparison.csv | FINAL |
| cmp_chars_mutual_mongodb | 884 | characters of query code | ec-hw2/results/comparison.csv | FINAL |
| cmp_bracket_lines_mutual_mongodb | 18 | lines with only brackets or commas | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_mutual_mongodb | 127.2 | ms (final, median of 21 runs in 3 rounds) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_min_mutual_mongodb | 121.7 | ms (fastest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_max_mutual_mongodb | 133.6 | ms (slowest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_faster_than_mutual_mongodb | none | engines it beats: its slowest run is faster than their fastest | ec-hw2/results/comparison.csv | FINAL |
| cmp_pain_mutual_mongodb | 4 | of 5 (draft by Claude Code; the Comparison+viz owner re-scores it) | ec-hw2/comparison/pain.csv | PROVISIONAL |
| cmp_rows_mutual_mongodb | 462 | rows | ec-hw2/results/comparison.csv | FINAL |
| cmp_loc_mutual_neo4j | 6 | lines (non-blank, non-comment) | ec-hw2/results/comparison.csv | FINAL |
| cmp_chars_mutual_neo4j | 275 | characters of query code | ec-hw2/results/comparison.csv | FINAL |
| cmp_bracket_lines_mutual_neo4j | 0 | lines with only brackets or commas | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_mutual_neo4j | 41.0 | ms (final, median of 21 runs in 3 rounds) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_min_mutual_neo4j | 33.9 | ms (fastest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_max_mutual_neo4j | 64.1 | ms (slowest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_faster_than_mutual_neo4j | MongoDB | engines it beats: its slowest run is faster than their fastest | ec-hw2/results/comparison.csv | FINAL |
| cmp_pain_mutual_neo4j | 2 | of 5 (draft by Claude Code; the Comparison+viz owner re-scores it) | ec-hw2/comparison/pain.csv | PROVISIONAL |
| cmp_rows_mutual_neo4j | 462 | rows | ec-hw2/results/comparison.csv | FINAL |
| cmp_loc_mutual_sqlite | 13 | lines (non-blank, non-comment) | ec-hw2/results/comparison.csv | FINAL |
| cmp_chars_mutual_sqlite | 412 | characters of query code | ec-hw2/results/comparison.csv | FINAL |
| cmp_bracket_lines_mutual_sqlite | 1 | lines with only brackets or commas | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_mutual_sqlite | 23.1 | ms (final, median of 21 runs in 3 rounds) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_min_mutual_sqlite | 17.9 | ms (fastest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_max_mutual_sqlite | 26.8 | ms (slowest of 21 runs) | ec-hw2/results/comparison.csv | FINAL |
| cmp_faster_than_mutual_sqlite | MongoDB; Neo4j | engines it beats: its slowest run is faster than their fastest | ec-hw2/results/comparison.csv | FINAL |
| cmp_pain_mutual_sqlite | 2 | of 5 (draft by Claude Code; the Comparison+viz owner re-scores it) | ec-hw2/comparison/pain.csv | PROVISIONAL |
| cmp_rows_mutual_sqlite | 462 | rows | ec-hw2/results/comparison.csv | FINAL |
| cmp_pain_scored_by | draft by Claude Code; Comparison+viz owner to re-score | who scored the modeling pain | ec-hw2/comparison/pain.csv | PROVISIONAL |
| cmp_runs_per_query | 21 | timed runs per query | ec-hw2/results/comparison.csv | FINAL |
| cmp_rounds | 3 | rounds (the engines take turns) | ec-hw2/results/comparison.csv | FINAL |
| cmp_load_average_start | 1.91 | 1-minute load average when the timing started (idle below 2.0) | ec-hw2/results/_SUCCESS_comparison.json | FINAL |
| cmp_all_identical | yes |  | ec-hw2/results/_SUCCESS_comparison.json | FINAL |
| cmp_timing_label | final | draft timings are PROVISIONAL | ec-hw2/results/comparison.csv | FINAL |
| cmp_ms_mutual_sqlite_preagg | 1.7 | ms (final, median of 21; extra row, not compared) | ec-hw2/results/comparison_extra.csv | FINAL |
| cmp_ms_min_mutual_sqlite_preagg | 1.5 | ms (fastest run; extra row) | ec-hw2/results/comparison_extra.csv | FINAL |
| cmp_ms_max_mutual_sqlite_preagg | 3.5 | ms (slowest run; extra row) | ec-hw2/results/comparison_extra.csv | FINAL |
| cmp_setup_ms_mutual_sqlite_preagg | 19.0 | ms to build the TEMP table of grouped triples (not timed in the median) | ec-hw2/results/comparison_extra.csv | FINAL |
| cmp_loc_mutual_sqlite_preagg | 5 | lines (the timed query only) | ec-hw2/results/comparison_extra.csv | FINAL |
| shard_key | {"page.id": "hashed"} |  | ec-hw2/scaleout/SHARDING.md | FINAL |
| shard_documents | 295,016 | documents | ec-hw2/results/_SUCCESS_sharding.json | FINAL |
| shard_shard1rs_docs | 147,462 | documents | ec-hw2/results/_SUCCESS_sharding.json | FINAL |
| shard_shard1rs_pct | 49.98 | % of documents | ec-hw2/results/_SUCCESS_sharding.json | FINAL |
| shard_shard2rs_docs | 147,554 | documents | ec-hw2/results/_SUCCESS_sharding.json | FINAL |
| shard_shard2rs_pct | 50.02 | % of documents | ec-hw2/results/_SUCCESS_sharding.json | FINAL |
| shard_route_one_page | SINGLE_SHARD |  | ec-hw2/results/_SUCCESS_sharding.json | FINAL |
| shard_route_one_editor | SHARD_MERGE |  | ec-hw2/results/_SUCCESS_sharding.json | FINAL |
| shard_checks_ok | 12 of 12 | checks | ec-hw2/results/_SUCCESS_sharding.json | FINAL |
| shard_biggest_page_title | List_of_2018_albums |  | data/tables/history_revisions.parquet | FINAL |
| shard_biggest_page_revisions | 261 | revisions | data/tables/history_revisions.parquet | FINAL |
| late_reverts_rows | 4,350 | September revisions, all namespaces (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_rows_ns0 | 3,591 | September revisions, namespace 0 only, like the history cohort (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_exact | 2,970 | revisions, all namespaces (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_exact_ns0 | 2,472 | revisions, namespace 0 only, like the history cohort (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_in_history_cohort_exact | 121 | revisions in the history cohort (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_inexact_undo | 198 | revisions, all namespaces (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_inexact_undo_ns0 | 194 | revisions, namespace 0 only, like the history cohort (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_in_history_cohort_inexact_undo | 16 | revisions in the history cohort (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_method_unknown | 1,182 | revisions, all namespaces (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_method_unknown_ns0 | 925 | revisions, namespace 0 only, like the history cohort (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_in_history_cohort_method_unknown | 80 | revisions in the history cohort (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_in_history_cohort | 217 | revisions in the history cohort (lower bound) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_pages | 2,437 | pages, all namespaces | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_pages_ns0 | 2,022 | pages, namespace 0 only, like the history cohort | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_reverting_actions | 1,684 | revert actions, all namespaces | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_reverting_actions_ns0 | 1,414 | revert actions, namespace 0 only, like the history cohort | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_median_age_exact_d | 33.1 | days (all namespaces) | data/tables/late_reverts_summary.json | FINAL |
| late_reverts_restored_later | 206 | revisions (all namespaces) | data/tables/late_reverts_summary.json | FINAL |
| risk_top_decile_score_min | 0.83 | revert-risk score | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_edits | 26,898 | edits | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_revert_rate_pct | 32.18 | % reverted within 4 days | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_bottom_decile_revert_rate_pct | 0.07 | % reverted within 4 days | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_visible_1h_pct | 68.13 | % of 4-day reverts | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_visible_1h_ci | 67.14-69.11 | % (Wilson 95%) | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_later_1h_pct | 13.13 | % of edits still clean at the wait | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_later_1h_ci | 12.68-13.60 | % (Wilson 95%) | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_bottom_decile_later_1h_pct | 0.030 | % of edits still clean at the wait | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_visible_1d_pct | 93.78 | % of 4-day reverts | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_visible_1d_ci | 93.26-94.27 | % (Wilson 95%) | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_later_1d_pct | 2.86 | % of edits still clean at the wait | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top_decile_later_1d_ci | 2.64-3.11 | % (Wilson 95%) | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_bottom_decile_later_1d_pct | 0.004 | % of edits still clean at the wait | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_top2_deciles_share_of_reverts_pct | 72.41 | % of 4-day reverts (scored edits) | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_no_score_edits | 10,450 | edits with no revert-risk score | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_no_score_revert_rate_pct | 1.63 | % reverted within 4 days (page creations and edits without a captured score, mixed) | ec-hw2/results/mongo_q5_risk_deciles.csv | FINAL |
| risk_no_score_page_creations | 5,392 | page creations (no page creation has a score) | data/tables/live_revisions.parquet + live_revert_links.parquet | FINAL |
| risk_no_score_page_creations_reverted | 0 | page creations reverted within 4 days | data/tables/live_revisions.parquet + live_revert_links.parquet | FINAL |
| risk_no_score_not_captured | 5,058 | edits whose score event was not captured | data/tables/live_revisions.parquet + live_revert_links.parquet | FINAL |
| risk_no_score_not_captured_reverted | 170 | of those edits, reverted within 4 days | data/tables/live_revisions.parquet + live_revert_links.parquet | FINAL |
| risk_no_score_not_captured_revert_rate_pct | 3.36 | % reverted within 4 days (edits whose score event was not captured) | data/tables/live_revisions.parquet + live_revert_links.parquet | FINAL |
| example_slow_page_title | World_Figure_Skating_Championships |  | data/tables/history_revisions.parquet | FINAL |
| example_slow_page_id | 229356 |  | data/tables/history_revisions.parquet | FINAL |
| example_slow_edits | 12 | revisions (history cohort) | data/tables/history_revisions.parquet | FINAL |
| example_slow_editor_kinds | registered 12 | revisions per user kind | data/tables/history_revisions.parquet | FINAL |
| example_slow_reverted | 9 | revisions reverted within 20 d | data/tables/history_revisions.parquet | FINAL |
| example_slow_T_min_s | 358 | s | data/tables/history_revisions.parquet | FINAL |
| example_slow_T_median_s | 10,268 | s | data/tables/history_revisions.parquet | FINAL |
| example_slow_T_max_s | 48,397 | s | data/tables/history_revisions.parquet | FINAL |
| example_slow_first_edit_utc | 2026-09-08 04:36 UTC |  | data/tables/history_revisions.parquet | FINAL |
| example_slow_last_revert_utc | 2026-09-09 19:52 UTC |  | data/tables/history_revisions.parquet | FINAL |
| example_slow_span_h | 39.3 | h (first edit to last revert) | data/tables/history_revisions.parquet | FINAL |
| example_slow_first_steps | 2026-09-08 04:36 UTC editor_bdbff746bb -17 bytes, reverted after 4.0 h; 2026-09-08 08:37 UTC editor_4e584fa272 +17 bytes (a revert), reverted after 13.4 h; 2026-09-08 22:04 UTC editor_bdbff746bb -17 bytes (a revert), reverted after 2.9 h | timeline (pseudonyms) | data/tables/history_revisions.parquet | FINAL |
| example_fast_page_title | Pendulum |  | data/tables/history_revisions.parquet | FINAL |
| example_fast_page_id | 42709 |  | data/tables/history_revisions.parquet | FINAL |
| example_fast_edits | 20 | revisions (history cohort) | data/tables/history_revisions.parquet | FINAL |
| example_fast_editor_kinds | temporary 10, registered 8, bot 2 | revisions per user kind | data/tables/history_revisions.parquet | FINAL |
| example_fast_reverted | 11 | revisions reverted within 20 d | data/tables/history_revisions.parquet | FINAL |
| example_fast_T_min_s | 6 | s | data/tables/history_revisions.parquet | FINAL |
| example_fast_T_median_s | 27 | s | data/tables/history_revisions.parquet | FINAL |
| example_fast_T_max_s | 1,097 | s | data/tables/history_revisions.parquet | FINAL |
| example_fast_first_edit_utc | 2026-09-08 17:12 UTC |  | data/tables/history_revisions.parquet | FINAL |
| example_fast_last_revert_utc | 2026-09-10 19:21 UTC |  | data/tables/history_revisions.parquet | FINAL |
| example_fast_span_h | 50.1 | h (first edit to last revert) | data/tables/history_revisions.parquet | FINAL |
| example_fast_first_steps | 2026-09-08 17:12 UTC editor_f7c8159972 +1 bytes, reverted after 41 s; 2026-09-08 17:13 UTC editor_88cf442cc1 -1 bytes (a revert); 2026-09-08 17:29 UTC editor_f7c8159972 +4 bytes, reverted after 29 s | timeline (pseudonyms) | data/tables/history_revisions.parquet | FINAL |
