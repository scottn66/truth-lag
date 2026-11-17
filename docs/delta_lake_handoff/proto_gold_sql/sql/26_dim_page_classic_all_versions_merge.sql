-- Demo of the classic form's limit: feed EVERY new version (not one row per page). Expected to FAIL when
-- a page has two or more new versions, because two source rows then match the one current target row.
MERGE INTO delta.`{gold}/dim_page_classic` t
USING (
  SELECT n.page_id AS merge_key, n.*
  FROM v_page_versions n
  JOIN (SELECT * FROM delta.`{gold}/dim_page_classic` WHERE is_current) d
    ON d.wiki_db = n.wiki_db AND d.page_id = n.page_id AND n.valid_from > d.valid_from
  UNION ALL
  SELECT CAST(NULL AS BIGINT) AS merge_key, n.*
  FROM v_page_versions n
  JOIN (SELECT * FROM delta.`{gold}/dim_page_classic` WHERE is_current) d
    ON d.wiki_db = n.wiki_db AND d.page_id = n.page_id AND n.valid_from > d.valid_from
) s
ON t.wiki_db = s.wiki_db AND t.page_id = s.merge_key AND t.is_current = true
WHEN MATCHED THEN UPDATE SET t.is_current = false, t.valid_to = s.valid_from
WHEN NOT MATCHED THEN INSERT (page_key, wiki_db, page_id, title, namespace, is_deleted, valid_from, valid_to, is_current)
VALUES (s.page_key, s.wiki_db, s.page_id, s.title, s.namespace, s.is_deleted, s.valid_from, s.valid_to, s.is_current)
