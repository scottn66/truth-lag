-- Comparison query (spec 5): mutual reverts per page (edit wars), in SQL (SQLite)
-- Question: which pairs of editors reverted EACH OTHER on the same page?
-- The shared definition (DATA_MODEL.md section 7), history cohort:
--   From revert_links with within_followup = 1 and by_other = 1 (both keys not null),
--   make the triples (reverter_key, author_key, page_id), each with its number of
--   distinct reverting revisions. A pair {a, b} on page p is mutual when both
--   (a, b, p) and (b, a, p) exist. The self-join of "triples" finds the reverse direction.
--   One row per page and unordered pair (a < b), ordered by page_id, a, b.
-- It must give the same ordered list as queries/mongo/compare_mutual_reverts.json and
-- queries/cypher/q1_mutual_reverts.cypher. comparison/compare.py checks this.
-- Output columns: page_id, a, b, a_reverted_b, b_reverted_a (distinct revert actions in
--   each direction). The output shows editor keys: the files in results/ replace human
--   keys with pseudonyms.
-- DB Browser for SQLite: open data/tables/truthlag.sqlite, paste this file into the
-- "Execute SQL" tab and run it.

WITH triples AS (
  SELECT reverter_key AS a, author_key AS b, page_id,
         COUNT(DISTINCT reverting_rev_id) AS n
  FROM revert_links
  WHERE cohort = 'history' AND within_followup = 1 AND by_other = 1
    AND reverter_key IS NOT NULL AND author_key IS NOT NULL
  GROUP BY reverter_key, author_key, page_id
)
SELECT f.page_id, f.a, f.b, f.n AS a_reverted_b, r.n AS b_reverted_a
FROM triples AS f
JOIN triples AS r ON r.page_id = f.page_id AND r.a = f.b AND r.b = f.a
WHERE f.a < f.b
ORDER BY f.page_id, f.a, f.b;
