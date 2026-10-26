# Comparison query (spec 5): mutual reverts per page (edit wars), in SQL (SQLite)

```text
Question: which pairs of editors reverted EACH OTHER on the same page?
The shared definition (DATA_MODEL.md section 7), history cohort:
  From revert_links with within_followup = 1 and by_other = 1 (both keys not null),
  make the triples (reverter_key, author_key, page_id), each with its number of
  distinct reverting revisions. A pair {a, b} on page p is mutual when both
  (a, b, p) and (b, a, p) exist. The self-join of "triples" finds the reverse direction.
  One row per page and unordered pair (a < b), ordered by page_id, a, b.
It must give the same ordered list as queries/mongo/compare_mutual_reverts.json and
queries/cypher/q1_mutual_reverts.cypher. comparison/compare.py checks this.
Output columns: page_id, a, b, a_reverted_b, b_reverted_a (distinct revert actions in
  each direction). The output shows editor keys: the files in results/ replace human
  keys with pseudonyms.
```

Rows: 462. Median time: 17.6 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_sql.py` on 2026-10-24 09:56 UTC (data-v1, SQLite 3.53.1). Query: `queries/sql/compare_mutual_reverts.sql`. Full table: `sql_compare_mutual_reverts.csv`.

|   page_id | page_title                            | editor_a          | editor_b          |   a_reverted_b |   b_reverted_a |
|-----------|---------------------------------------|-------------------|-------------------|----------------|----------------|
|      1921 | Al-Qaeda                              | editor_9eb8ef10a7 | editor_0d0cfcfbf9 |              1 |              1 |
|      6443 | Ceuta                                 | editor_36d2f02780 | editor_3b58b3c064 |              1 |              2 |
|      8691 | Divination                            | editor_37519a19ee | editor_2a2c1d5e4e |              1 |              2 |
|     11642 | General_Dynamics_F-16_Fighting_Falcon | editor_87b8cee2d3 | editor_6ce3a652ad |              1 |              1 |
|     12861 | Governor_of_New_York                  | editor_47e86b5cd9 | editor_487db86817 |              1 |              1 |
|     14653 | Iran                                  | editor_cc48647e40 | editor_c76338f65c |              1 |              1 |
|     15800 | June_26                               | editor_7628bfe60d | editor_7ca4a5a591 |              1 |              1 |
|     21216 | Nevada                                | editor_3e752ffcba | editor_dd4c69c7ef |              1 |              1 |
|     21711 | Neon_Genesis_Evangelion               | editor_ed3b936f81 | editor_a11552f42d |              1 |              1 |
|     25412 | Rock_and_roll                         | editor_71e32ee367 | editor_6990c735a3 |              1 |              1 |
|     26769 | South_America                         | editor_07a4f411ef | editor_8811ab609d |              1 |              1 |
|     28588 | Coat_of_arms_of_South_Africa          | editor_740863da11 | editor_4deed9c19b |              1 |              1 |
|     28849 | Shiva                                 | editor_56450988a7 | editor_bdb60908b2 |              1 |              1 |
|     31924 | University_of_California,_Davis       | editor_bbbf6dbde4 | editor_a2afead7f9 |              1 |              2 |
|     33299 | William_Henry_Harrison                | editor_b61b267917 | editor_1b2c1e3586 |              1 |              1 |
|     37653 | CBS                                   | editor_5c0348929b | editor_96ab052746 |              2 |              1 |
|     46252 | Fox_Broadcasting_Company              | editor_149df512e8 | editor_f3ddbfb21b |              2 |              1 |
|     46764 | Artiodactyla                          | editor_e84ed8f72e | editor_d5a2b9dbd5 |              1 |              1 |
|     50884 | Chelicerata                           | editor_aec5a64ebf | editor_d77156726d |              1 |              1 |
|     52382 | Watergate_scandal                     | editor_3710546463 | ClueBot NG        |              1 |              1 |
|     52382 | Watergate_scandal                     | editor_3710546463 | editor_dd4c69c7ef |              2 |              3 |
|     52382 | Watergate_scandal                     | editor_f70885dc34 | editor_2fdc778846 |              2 |              2 |
|     52382 | Watergate_scandal                     | editor_2fdc778846 | editor_c8c6ac1305 |              1 |              1 |
|     52382 | Watergate_scandal                     | editor_c8c6ac1305 | editor_bfe10b76eb |              1 |              1 |
|     52382 | Watergate_scandal                     | editor_26780f3de3 | editor_bfe10b76eb |              1 |              1 |
|     52382 | Watergate_scandal                     | editor_88ce220359 | editor_dd4c69c7ef |              2 |              2 |
|     53307 | Lepidoptera                           | editor_aec5a64ebf | editor_7df58ece29 |              1 |              2 |
|     60585 | Social_Democratic_Party_of_Germany    | editor_ad6cd81354 | editor_8f36f41c8c |              1 |              1 |
|     66069 | Harald_V                              | editor_47caafd596 | editor_edd7e230da |              1 |              1 |
|     66069 | Harald_V                              | editor_8f621ec0db | editor_78e3c56467 |              1 |              1 |

(first 30 of 462 rows)
