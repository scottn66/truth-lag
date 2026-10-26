# Cypher Q1 (spec 4.1): mutual-revert pairs on the same page (edit wars) (result total)

Question: which pairs of editors reverted EACH OTHER on the same page?
A pair {a, b} on page p is mutual when a reverted b on p AND b reverted a on p
(reverts by another editor within 20 days, history cohort; DATA_MODEL.md section 7).
Each unordered pair is listed once (a.key < b.key). This is also the "mutual
reverts" comparison query (spec 5): Mongo and SQL give the same ordered list.
Output columns (result main): page_id, page_title, editor_a, editor_b,
a_reverted_b, b_reverted_a (distinct revert actions in each direction).
Output columns (result total): mutual_pairs, pages, editors, pairs_with_bot.
Editors are shown by alias (a pseudonym for humans; bots keep their name).

Rows: 1. Median time: 38.7 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-24 09:56 UTC (data-v1). Query: `queries/cypher/q1_mutual_reverts.cypher`. Full table: `cypher_q1_mutual_reverts_total.csv`.

|   mutual_pairs |   pages |   editors |   pairs_with_bot |
|----------------|---------|-----------|------------------|
|            462 |     397 |       631 |               25 |

