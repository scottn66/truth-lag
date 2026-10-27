# Comparison query (spec 5): the top 20 contested pages, in SQL (SQLite)

```text
Question: which pages have the most revert actions per human edit?
The shared definition (DATA_MODEL.md section 7), history cohort:
  revert_actions   = distinct reverting_rev_id among revert_links with
                     within_followup = 1 and by_other = 1 on the page
  reverted_editors = distinct author_key among those links
  edits            = non-bot revisions on the page (table revisions, is_bot = 0)
  Keep pages with reverted_editors >= 2 and edits >= 10.
  score = 1.0 * revert_actions / edits (a float; plain a / b would be whole-number division).
  Order: score desc, revert_actions desc, edits desc, page_id asc; top 20.
  contested = revert_actions >= 2, reverted_editors >= 2 and score >= 0.2.
  page_title = the title of the newest history revision of the page.
The steps are the same in MongoDB (Mongo Q2), Cypher and SQL, so the 3 engines do the
same work: (1) group the revert links per page and keep the pages with 2 or more
reverted editors (HAVING); (2) count the human edits only for those pages ("edits":
one COUNT per kept page, which uses the page_id index, like the $lookup of Mongo Q2;
a plain JOIN + GROUP BY made SQLite scan all revisions instead); (3) compute the
score, filter, order and limit.
There is no rank column: run_sql.py adds it in Python, as run_mongo.py does for Mongo Q2.
The numbers in "params" must equal config.py: run_sql.py and compare.py stop if they differ.
It must give the same 20 page_ids and scores (rounded to 6 digits) as Mongo Q2 and
queries/cypher/compare_top_contested.cypher. comparison/compare.py checks this.
Output columns: page_id, page_title, edits, revert_actions, reverted_editors, score,
  contested (1 = true).
```

Rows: 20. Median time: 27.6 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_sql.py` on 2026-10-27 21:28 UTC (data-v2, SQLite 3.53.1). Query: `queries/sql/compare_top_contested.sql`. Full table: `sql_compare_top_contested.csv`.

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

