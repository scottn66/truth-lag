# Cypher Q4 (spec 4.4): the pages with the most distinct warring editors

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

Rows: 20. Median time: 26.2 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-24 09:56 UTC (data-v1). Query: `queries/cypher/q4_pages_most_warring_editors.cypher`. Full table: `cypher_q4_pages_most_warring_editors.csv`.

|   page_id | page_title                               |   warring_editors |   mutual_pairs |   editors_in_any_revert |   revert_actions |   edits |
|-----------|------------------------------------------|-------------------|----------------|-------------------------|------------------|---------|
|   3146234 | PB&J_Otter                               |                10 |              9 |                      13 |               34 |      39 |
|     52382 | Watergate_scandal                        |                 9 |              7 |                      15 |               28 |      32 |
|  84135854 | GPT-6                                    |                 6 |              4 |                       8 |               17 |      23 |
|   2484700 | Zoe_Slater                               |                 5 |              4 |                       8 |               10 |      45 |
|     66069 | Harald_V                                 |                 4 |              2 |                       8 |                8 |      15 |
|    137070 | South_Salt_Lake,_Utah                    |                 4 |              2 |                       4 |                7 |       8 |
|    155868 | Lumen                                    |                 4 |              3 |                       5 |               11 |      20 |
|    165909 | Gladys_Knight                            |                 4 |              2 |                       4 |                4 |       9 |
|    300257 | Sonic_the_Hedgehog_(1991_video_game)     |                 4 |              2 |                       7 |                7 |       9 |
|    458248 | List_of_companies_named_after_people     |                 4 |              3 |                       7 |               24 |      34 |
|   6150221 | I_Spy_(book_series)                      |                 4 |              3 |                       4 |                7 |      11 |
|  11383948 | Personality_and_image_of_Elizabeth_II    |                 4 |              3 |                       5 |               13 |      14 |
|  18247344 | Far-left_politics                        |                 4 |              3 |                       4 |                8 |      13 |
|  72291474 | 2026_Pennsylvania_gubernatorial_election |                 4 |              3 |                       6 |                9 |      14 |
|  82920850 | Jim_Queen                                |                 4 |              3 |                       9 |               12 |      14 |
|  84184840 | IPhone_Duo                               |                 4 |              3 |                      22 |               19 |     255 |
|     98262 | Queen_Sonja_of_Norway                    |                 3 |              2 |                       4 |                5 |       6 |
|    229356 | World_Figure_Skating_Championships       |                 3 |              2 |                       3 |                9 |      12 |
|    442916 | Avian_influenza                          |                 3 |              2 |                       4 |                6 |       9 |
|    786732 | Arnaldo_Tamayo_Méndez                    |                 3 |              2 |                       4 |                5 |       8 |

