# Mongo Q2: top 20 contested pages (history cohort)

Mongo Q2 (spec 3.2), also the 'top contested pages' comparison query: the top 20 contested pages of the history cohort, with the shared definition of DATA_MODEL.md section 7. revert_actions = distinct reverting_rev_id among revert_links with within_followup and by_other on the page; reverted_editors = distinct author_key among those links; edits = non-bot history revisions on the page (from revisions, with $lookup on page.id). Pages need edits >= 10 and reverted_editors >= 2. score = revert_actions / edits (a float). Order: score desc, revert_actions desc, edits desc, page_id asc. contested = revert_actions >= 2 and score >= 0.2. It starts from revert_links, because only pages with reverts can qualify, and the $lookup then uses the {page.id, ts} index.

Rows: 20. Median time: 488.7 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_mongo.py` on 2026-10-24 10:10 UTC (data-v1). Full table: `mongo_atlas_q2_top_contested_pages.csv`.

|   rank |   page_id | page_title                               |   edits |   revert_actions |   reverted_editors |    score | contested   |
|--------|-----------|------------------------------------------|---------|------------------|--------------------|----------|-------------|
|      1 |  11383948 | Personality_and_image_of_Elizabeth_II    |      14 |               13 |                  5 | 0.928571 | True        |
|      2 |     52382 | Watergate_scandal                        |      32 |               28 |                 14 | 0.875    | True        |
|      3 |   3146234 | PB&J_Otter                               |      39 |               34 |                 13 | 0.871795 | True        |
|      4 |  82920850 | Jim_Queen                                |      14 |               12 |                  8 | 0.857143 | True        |
|      5 |   3040638 | Pororo_the_Little_Penguin                |      13 |               11 |                  3 | 0.846154 | True        |
|      6 |  32988783 | Head_shake                               |      11 |                9 |                  3 | 0.818182 | True        |
|      7 |  15903588 | Gabre_Heard                              |      10 |                8 |                  4 | 0.8      | True        |
|      8 |    229356 | World_Figure_Skating_Championships       |      12 |                9 |                  3 | 0.75     | True        |
|      9 |  84135854 | GPT-6                                    |      23 |               17 |                  7 | 0.73913  | True        |
|     10 |  70526372 | Styropyro                                |      14 |               10 |                  3 | 0.714286 | True        |
|     11 |  78604276 | Sonic_Racing:_CrossWorlds                |      14 |               10 |                  3 | 0.714286 | True        |
|     12 |    458248 | List_of_companies_named_after_people     |      34 |               24 |                  6 | 0.705882 | True        |
|     13 |  72291474 | 2026_Pennsylvania_gubernatorial_election |      14 |                9 |                  5 | 0.642857 | True        |
|     14 |   6150221 | I_Spy_(book_series)                      |      11 |                7 |                  4 | 0.636364 | True        |
|     15 |  18247344 | Far-left_politics                        |      13 |                8 |                  4 | 0.615385 | True        |
|     16 |     42709 | Pendulum                                 |      18 |               11 |                  5 | 0.611111 | True        |
|     17 |  76375756 | Anis_Hadj_Moussa                         |      15 |                9 |                  3 | 0.6      | True        |
|     18 |  25828477 | Jamil                                    |      10 |                6 |                  2 | 0.6      | True        |
|     19 |  81060680 | IPad_kid                                 |      10 |                6 |                  7 | 0.6      | True        |
|     20 |  41749517 | Rodrigo_De_Paul                          |      12 |                7 |                  5 | 0.583333 | True        |

