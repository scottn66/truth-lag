-- Extra timing (spec 5): mutual reverts in SQL (SQLite) on PRE-AGGREGATED input
-- Question: how much of the mutual-reverts time difference comes from the input, not the engine?
-- Why this file exists: Cypher Q1 reads the REVERTED relationships. export_graph.py built
--   them before any query runs: one per (reverter, reverted editor, page), with count =
--   the number of distinct revert actions. MongoDB and compare_mutual_reverts.sql do this
--   grouping of the raw revert links INSIDE the timed query. This file gives SQLite the
--   same head start as Neo4j, so the reader can see the effect.
-- It is NOT one of the 6 comparison queries. comparison/compare.py runs it as an extra row:
--   Step 1 (every statement before the last one, NOT timed): build the TEMP table
--     revert_triples in memory, keyed like the REVERTED relationships. TEMP tables live only
--     in this connection, so the database file is not changed (it is opened read-only).
--   Step 2 (the last statement, timed): the same self-join as compare_mutual_reverts.sql,
--     on revert_triples instead of the grouped revert_links.
-- It must give the same rows as compare_mutual_reverts.sql. comparison/compare.py checks this.
-- Output columns: page_id, a, b, a_reverted_b, b_reverted_a (editor keys).
-- DB Browser for SQLite: open data/tables/truthlag.sqlite, paste this file into the
-- "Execute SQL" tab and run it (the TEMP table goes away when you close the file).

PRAGMA temp_store = MEMORY;

DROP TABLE IF EXISTS temp.revert_triples;

CREATE TEMP TABLE revert_triples (
  a TEXT NOT NULL,
  b TEXT NOT NULL,
  page_id INTEGER NOT NULL,
  n INTEGER NOT NULL,
  PRIMARY KEY (a, b, page_id)
);

INSERT INTO temp.revert_triples (a, b, page_id, n)
SELECT reverter_key, author_key, page_id, COUNT(DISTINCT reverting_rev_id)
FROM revert_links
WHERE cohort = 'history' AND within_followup = 1 AND by_other = 1
  AND reverter_key IS NOT NULL AND author_key IS NOT NULL
GROUP BY reverter_key, author_key, page_id;

SELECT f.page_id, f.a, f.b, f.n AS a_reverted_b, r.n AS b_reverted_a
FROM temp.revert_triples AS f
JOIN temp.revert_triples AS r ON r.a = f.b AND r.b = f.a AND r.page_id = f.page_id
WHERE f.a < f.b
ORDER BY f.page_id, f.a, f.b;
