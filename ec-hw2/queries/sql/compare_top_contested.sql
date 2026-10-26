-- Comparison query (spec 5): the top 20 contested pages, in SQL (SQLite)
-- Question: which pages have the most revert actions per human edit?
-- The shared definition (DATA_MODEL.md section 7), history cohort:
--   revert_actions   = distinct reverting_rev_id among revert_links with
--                      within_followup = 1 and by_other = 1 on the page
--   reverted_editors = distinct author_key among those links
--   edits            = non-bot revisions on the page (table revisions, is_bot = 0)
--   Keep pages with reverted_editors >= 2 and edits >= 10.
--   score = 1.0 * revert_actions / edits (a float; plain a / b would be whole-number division).
--   Order: score desc, revert_actions desc, edits desc, page_id asc; top 20.
--   contested = revert_actions >= 2, reverted_editors >= 2 and score >= 0.2.
--   page_title = the title of the newest history revision of the page.
-- The steps are the same in MongoDB (Mongo Q2), Cypher and SQL, so the 3 engines do the
-- same work: (1) group the revert links per page and keep the pages with 2 or more
-- reverted editors (HAVING); (2) count the human edits only for those pages ("edits":
-- one COUNT per kept page, which uses the page_id index, like the $lookup of Mongo Q2;
-- a plain JOIN + GROUP BY made SQLite scan all revisions instead); (3) compute the
-- score, filter, order and limit.
-- There is no rank column: run_sql.py adds it in Python, as run_mongo.py does for Mongo Q2.
-- The numbers in "params" must equal config.py: run_sql.py and compare.py stop if they differ.
-- It must give the same 20 page_ids and scores (rounded to 6 digits) as Mongo Q2 and
-- queries/cypher/compare_top_contested.cypher. comparison/compare.py checks this.
-- Output columns: page_id, page_title, edits, revert_actions, reverted_editors, score,
--   contested (1 = true).
-- DB Browser for SQLite: open data/tables/truthlag.sqlite, paste this file into the
-- "Execute SQL" tab and run it. You should see 20 rows.

WITH params AS (
  SELECT 20 AS top_n, 10 AS contested_min_edits, 2 AS contested_min_editors,
         2 AS contested_min_actions, 0.2 AS contested_min_score
),
links AS (
  SELECT page_id,
         COUNT(DISTINCT reverting_rev_id) AS revert_actions,
         COUNT(DISTINCT author_key) AS reverted_editors
  FROM revert_links
  WHERE cohort = 'history' AND within_followup = 1 AND by_other = 1
  GROUP BY page_id
  HAVING COUNT(DISTINCT author_key) >= (SELECT contested_min_editors FROM params)
),
edits AS (
  SELECT l.page_id,
         (SELECT COUNT(*) FROM revisions AS r
          WHERE r.page_id = l.page_id AND r.cohort = 'history' AND r.is_bot = 0) AS edits
  FROM links AS l
),
top AS (
  SELECT l.page_id, e.edits, l.revert_actions, l.reverted_editors,
         1.0 * l.revert_actions / e.edits AS score
  FROM links AS l
  JOIN edits AS e ON e.page_id = l.page_id
  WHERE e.edits >= (SELECT contested_min_edits FROM params)
  ORDER BY score DESC, l.revert_actions DESC, e.edits DESC, l.page_id ASC
  LIMIT (SELECT top_n FROM params)
)
SELECT t.page_id,
       (SELECT r.page_title FROM revisions AS r WHERE r.page_id = t.page_id
        ORDER BY r.ts DESC, r.rev_id DESC LIMIT 1) AS page_title,
       t.edits, t.revert_actions, t.reverted_editors, t.score,
       (t.revert_actions >= p.contested_min_actions
        AND t.reverted_editors >= p.contested_min_editors
        AND t.score >= p.contested_min_score) AS contested
FROM top AS t
CROSS JOIN params AS p
ORDER BY t.score DESC, t.revert_actions DESC, t.edits DESC, t.page_id ASC;
