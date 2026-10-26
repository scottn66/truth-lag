# Cypher Q5 (spec 4.5): 2-hop, editors linked through shared contested pages

Question: which pairs of human editors meet on the most contested pages?
The 2-hop pattern is editor -EDITED-> contested page <-EDITED- editor. A page is
contested when Page.contested = true (export_graph.py sets it with the shared rule:
edits >= 10, reverted_editors >= 2, revert_actions >= 2 and score >= 0.2).
Bots are left out. Each unordered pair is listed once (a.key < b.key).
a_reverted_b / b_reverted_a: revert actions between the two, on ANY page, so we
see whether the pair also fought directly.
Why the query starts from the pages: the index page_contested (load.cypher) finds the
few contested pages first, and only their EDITED relationships are expanded. Without
"USING INDEX" the planner starts from the editors and expands every EDITED relationship.
Output columns: editor_a, editor_b, shared_contested_pages, a_reverted_b,
b_reverted_a, example_pages (up to 3 page titles, by page id).
Top 20 by shared_contested_pages, then a.key, b.key. Editors are shown by alias.

Rows: 20. Median time: 17.9 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-24 09:56 UTC (data-v1). Query: `queries/cypher/q5_two_hop_contested.cypher`. Full table: `cypher_q5_two_hop_contested.csv`.

| editor_a          | editor_b          |   shared_contested_pages |   a_reverted_b |   b_reverted_a | example_pages                                                              |
|-------------------|-------------------|--------------------------|----------------|----------------|----------------------------------------------------------------------------|
| editor_8596618215 | editor_9d6fe86bb1 |                        4 |              0 |              0 | Eric_Lefkofsky | Jewish_nose | Richarlison                                 |
| editor_3b75e7ac14 | editor_ced644389c |                        4 |              0 |              0 | GCSE | Pink_(singer) | Drake_Maye                                          |
| editor_3b75e7ac14 | editor_7ca4a5a591 |                        3 |              0 |              0 | Pink_(singer) | Rodrigo_De_Paul | Armando_González_(footballer,_born_2003) |
| editor_fc60ea14ca | editor_bfe10b76eb |                        3 |              0 |              0 | Eggnog | Greg_Sankey | Sunmarke_School                                     |
| editor_72dd7a4c2c | editor_47caafd596 |                        2 |              0 |              0 | Harald_V | 21_Air                                                          |
| editor_72dd7a4c2c | editor_d82e4dd45b |                        2 |              0 |              3 | Harald_V | 21_Air                                                          |
| editor_72dd7a4c2c | editor_edd7e230da |                        2 |              0 |              0 | Harald_V | 21_Air                                                          |
| editor_47caafd596 | editor_d82e4dd45b |                        2 |              3 |              0 | Harald_V | 21_Air                                                          |
| editor_47caafd596 | editor_edd7e230da |                        2 |              3 |              4 | Harald_V | 21_Air                                                          |
| editor_5d9d202d8d | editor_8596618215 |                        2 |              0 |              0 | Eric_Lefkofsky | Chrisean_Rock                                             |
| editor_5d9d202d8d | editor_9d6fe86bb1 |                        2 |              0 |              0 | Eric_Lefkofsky | Mike_Davis_(American_lawyer)                              |
| editor_5d9d202d8d | editor_33a6bd2024 |                        2 |              0 |              0 | Eric_Lefkofsky | Tony_Duvert                                               |
| editor_5d9d202d8d | editor_189d3af8ce |                        2 |              0 |              0 | Eric_Lefkofsky | Trinity_Tatum                                             |
| editor_d82e4dd45b | editor_edd7e230da |                        2 |              0 |              0 | Harald_V | 21_Air                                                          |
| editor_8596618215 | editor_71e32ee367 |                        2 |              0 |              0 | American_Idiot | Chrisean_Rock                                             |
| editor_8596618215 | editor_ac3a5f5d27 |                        2 |              1 |              0 | Special_Operations_Executive | Eric_Lefkofsky                              |
| editor_3b75e7ac14 | editor_b73890917c |                        2 |              0 |              0 | GCSE | 2026_Kazakh_legislative_election                                    |
| editor_3b75e7ac14 | editor_4daa5740d4 |                        2 |              0 |              0 | Pink_(singer) | List_of_Copts                                              |
| editor_a1654caf04 | editor_53d019ece1 |                        2 |              3 |              2 | Femi_Oluwole | Shola_Mos-Shogbamimu                                        |
| editor_a1654caf04 | editor_7a8514c503 |                        2 |              0 |              0 | Femi_Oluwole | Shola_Mos-Shogbamimu                                        |

