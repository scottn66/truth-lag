# Neo4j (Cypher) query timings

Target: local Neo4j 2026.10.1. Each read-only result ran 7 warm times after 1 warm-up (unless --runs says otherwise); median_ms is the median of those runs. Statements that write (gds.louvain.write) ran once. Checks: PageRank converged ('cypher_q2_reverse', {relationshipWeightProperty: 'count', concurrency: 4, maxIterations: 200, tolerance: 1e-7}): OK; compare_top_contested = Mongo Q2 (same 20 page_ids, scores rounded to 6): OK; Cypher Q1 total = number of Cypher Q1 rows: OK; Cypher Q1 = Mongo compare_mutual_reverts (full ordered list): OK; Louvain wrote communityId on every Editor: OK; WCC component sizes add up to all Editor nodes: OK; community_sizes: same total as louvain_stats, and 2+ editors + 1 editor = total: OK; Editor.reverts_made = sum of outgoing REVERTED.count: OK; Editor.reverts_received = sum of incoming REVERTED.count: OK; Page.revert_actions = distinct reverting_rev_id on its EDITED relationships: OK; values have real types (Page.score FLOAT, EDITED.ts ZONED DATETIME, REVERTED.count INTEGER): OK; every human Editor.alias = the shared pseudonym (ingest/build_documents.py): OK.

Rows: 14.
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-24 09:56 UTC (data-v1). Full table: `cypher_summary.csv`.

| query                         | result          | file                                                   |   result_rows |   median_ms |   min_ms |   max_ms |   runs |
|-------------------------------|-----------------|--------------------------------------------------------|---------------|-------------|----------|----------|--------|
| q1_mutual_reverts             | main            | cypher_q1_mutual_reverts.csv                           |           462 |        53   |     47.3 |     77.9 |      7 |
| q1_mutual_reverts             | total           | cypher_q1_mutual_reverts_total.csv                     |             1 |        38.7 |     34.6 |     40.8 |      7 |
| q2_central_reverters          | main            | cypher_q2_central_reverters.csv                        |            20 |       193.3 |    161.7 |    269.9 |      7 |
| q2_central_reverters          | humans          | cypher_q2_central_reverters_humans.csv                 |            20 |       185.6 |    167.1 |    194.3 |      7 |
| q2_central_reverters          | by_degree       | cypher_q2_central_reverters_by_degree.csv              |            20 |        17.2 |     16   |     19.1 |      7 |
| q3_conflict_communities       | louvain_stats   | cypher_q3_conflict_communities_louvain_stats.csv       |             1 |       412.7 |    412.7 |    412.7 |      1 |
| q3_conflict_communities       | community_sizes | cypher_q3_conflict_communities_community_sizes.csv     |             1 |        19.2 |     16.8 |     20.8 |      7 |
| q3_conflict_communities       | main            | cypher_q3_conflict_communities.csv                     |            10 |       106.9 |    100.6 |    166.1 |      7 |
| q3_conflict_communities       | wcc_sizes       | cypher_q3_conflict_communities_wcc_sizes.csv           |             6 |         8.7 |      8.1 |     18.4 |      7 |
| q3_conflict_communities       | wcc_largest     | cypher_q3_conflict_communities_wcc_largest.csv         |             5 |        39.6 |     38.7 |     60.7 |      7 |
| q4_pages_most_warring_editors | main            | cypher_q4_pages_most_warring_editors.csv               |            20 |        26.2 |     24.1 |     39.3 |      7 |
| q4_pages_most_warring_editors | by_any_revert   | cypher_q4_pages_most_warring_editors_by_any_revert.csv |            20 |        23.1 |     21.2 |     25.5 |      7 |
| q5_two_hop_contested          | main            | cypher_q5_two_hop_contested.csv                        |            20 |        17.9 |     17.3 |     19.4 |      7 |
| compare_top_contested         | main            | cypher_compare_top_contested.csv                       |            20 |       112.9 |    107.7 |    123.5 |      7 |

