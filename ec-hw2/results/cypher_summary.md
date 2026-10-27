# Neo4j (Cypher) query timings

Target: local Neo4j 2026.10.1. Each read-only result ran 7 warm times after 1 warm-up (unless --runs says otherwise); median_ms is the median of those runs. Statements that write (gds.louvain.write) ran once. Checks: PageRank converged ('cypher_q2_reverse', {relationshipWeightProperty: 'count', concurrency: 4, maxIterations: 200, tolerance: 1e-7}): OK; compare_top_contested = Mongo Q2 (same 20 page_ids, scores rounded to 6): OK; Cypher Q1 total = number of Cypher Q1 rows: OK; Cypher Q1 = Mongo compare_mutual_reverts (full ordered list): OK; Louvain wrote communityId on every Editor: OK; WCC component sizes add up to all Editor nodes: OK; community_sizes: same total as louvain_stats, and 2+ editors + 1 editor = total: OK; Editor.reverts_made = sum of outgoing REVERTED.count: OK; Editor.reverts_received = sum of incoming REVERTED.count: OK; Page.revert_actions = distinct reverting_rev_id on its EDITED relationships: OK; values have real types (Page.score FLOAT, EDITED.ts ZONED DATETIME, REVERTED.count INTEGER): OK; every human Editor.alias = the shared pseudonym (ingest/build_documents.py): OK.

Rows: 14.
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-27 21:27 UTC (data-v2). Full table: `cypher_summary.csv`.

| query                         | result          | file                                                   |   result_rows |   median_ms |   min_ms |   max_ms |   runs |
|-------------------------------|-----------------|--------------------------------------------------------|---------------|-------------|----------|----------|--------|
| q1_mutual_reverts             | main            | cypher_q1_mutual_reverts.csv                           |           462 |       261.2 |    228.7 |    276.5 |      7 |
| q1_mutual_reverts             | total           | cypher_q1_mutual_reverts_total.csv                     |             1 |       169.1 |    157.5 |    236.4 |      7 |
| q2_central_reverters          | main            | cypher_q2_central_reverters.csv                        |            20 |       206.1 |    166.8 |   1156.9 |      7 |
| q2_central_reverters          | humans          | cypher_q2_central_reverters_humans.csv                 |            20 |       174.7 |    159.6 |    317.9 |      7 |
| q2_central_reverters          | by_degree       | cypher_q2_central_reverters_by_degree.csv              |            20 |        21.9 |     18.9 |     36.2 |      7 |
| q3_conflict_communities       | louvain_stats   | cypher_q3_conflict_communities_louvain_stats.csv       |             1 |       536.9 |    536.9 |    536.9 |      1 |
| q3_conflict_communities       | community_sizes | cypher_q3_conflict_communities_community_sizes.csv     |             1 |        34.5 |     27.1 |     37.9 |      7 |
| q3_conflict_communities       | main            | cypher_q3_conflict_communities.csv                     |            10 |       115.8 |    106.2 |    216.2 |      7 |
| q3_conflict_communities       | wcc_sizes       | cypher_q3_conflict_communities_wcc_sizes.csv           |             6 |        13.7 |     11.5 |     16.9 |      7 |
| q3_conflict_communities       | wcc_largest     | cypher_q3_conflict_communities_wcc_largest.csv         |             5 |        58.6 |     42.4 |     84.4 |      7 |
| q4_pages_most_warring_editors | main            | cypher_q4_pages_most_warring_editors.csv               |            20 |        32   |     29.7 |     43.7 |      7 |
| q4_pages_most_warring_editors | by_any_revert   | cypher_q4_pages_most_warring_editors_by_any_revert.csv |            20 |        27.5 |     25.2 |     28.8 |      7 |
| q5_two_hop_contested          | main            | cypher_q5_two_hop_contested.csv                        |            20 |        21.8 |     20.3 |     25.3 |      7 |
| compare_top_contested         | main            | cypher_compare_top_contested.csv                       |            20 |       119.4 |    115.5 |    126.2 |      7 |

