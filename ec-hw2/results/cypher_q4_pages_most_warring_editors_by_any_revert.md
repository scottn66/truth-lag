# Cypher Q4 (spec 4.4): the pages with the most distinct warring editors (result by_any_revert)

Question: on which pages do the most editors fight each other?
Two counts per page (both use reverts by another editor within 20 days):
- warring_editors: distinct editors who are in at least one mutual-revert pair
on the page (A reverted B AND B reverted A on this page, as in Cypher Q1).
- editors_in_any_revert: distinct editors at either end of any REVERTED
relationship on the page (they reverted someone there, or someone reverted
them there). Mutual pairs are rare, so this second count is wider.
mutual_pairs = unordered mutual pairs on the page; edits and revert_actions come
from the Page node (the shared definition of DATA_MODEL.md section 7).
Output columns (result main = top 20 by warring_editors, then page_id): page_id,
page_title, warring_editors, mutual_pairs, editors_in_any_revert, revert_actions, edits.
Output columns (result by_any_revert = top 20 by editors_in_any_revert, then
page_id): the same columns.

Rows: 20. Median time: 27.5 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-27 21:27 UTC (data-v2). Query: `queries/cypher/q4_pages_most_warring_editors.cypher`. Full table: `cypher_q4_pages_most_warring_editors_by_any_revert.csv`.

|   page_id | page_title                                             |   warring_editors |   mutual_pairs |   editors_in_any_revert |   revert_actions |   edits |
|-----------|--------------------------------------------------------|-------------------|----------------|-------------------------|------------------|---------|
|  25461352 | Jordan_Ayew                                            |                 0 |              0 |                      29 |               14 |      45 |
|   5280985 | Mike_McFarland                                         |                 3 |              2 |                      28 |               18 |      96 |
|  14486117 | Eric_Lefkofsky                                         |                 0 |              0 |                      22 |               11 |      27 |
|  84184840 | IPhone_Duo                                             |                 4 |              3 |                      22 |               19 |     255 |
|  83375714 | Hanuman_Ansh                                           |                 0 |              0 |                      18 |               12 |      96 |
|    215566 | Pink_(singer)                                          |                 0 |              0 |                      16 |                8 |      22 |
|  27599234 | Millennium_Prize_Problems                              |                 0 |              0 |                      16 |                9 |      65 |
|  84165176 | Danny_Tommo                                            |                 0 |              0 |                      16 |                9 |      36 |
|     52382 | Watergate_scandal                                      |                 9 |              7 |                      15 |               28 |      32 |
|  83118601 | 2026_Kazakh_legislative_election                       |                 2 |              1 |                      15 |                9 |      25 |
|  83401625 | The_Legend_of_Zelda:_Ocarina_of_Time_(2026_video_game) |                 2 |              1 |                      14 |                9 |     102 |
|   3146234 | PB&J_Otter                                             |                10 |              9 |                      13 |               34 |      39 |
|  51453242 | Ryōtarō_Itō                                            |                 0 |              0 |                      13 |                6 |      16 |
|    563215 | Swiss_Re                                               |                 0 |              0 |                      11 |                4 |      25 |
|  58040727 | Oliver_Tree                                            |                 0 |              0 |                      11 |                5 |      10 |
|  84083326 | Death_and_state_funeral_of_Harald_V                    |                 2 |              1 |                      11 |                8 |     119 |
|     28020 | September_10                                           |                 0 |              0 |                      10 |                7 |      19 |
|     42709 | Pendulum                                               |                 0 |              0 |                      10 |               11 |      18 |
|  16340523 | Dave_Rubin                                             |                 2 |              1 |                      10 |                7 |      17 |
|  84167596 | 2026_Yemen_offensives                                  |                 0 |              0 |                      10 |                5 |     197 |

