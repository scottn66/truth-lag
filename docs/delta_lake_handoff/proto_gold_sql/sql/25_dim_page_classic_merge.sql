-- Classic staged-source SCD2 MERGE (NULL merge key), as in the spark_lab report.
-- Row with merge_key = page_id closes the old current row; row with merge_key NULL never matches and is inserted.
MERGE INTO delta.`{gold}/dim_page_classic` t
USING (
  SELECT page_id AS merge_key, * FROM v_page_classic_changed WHERE has_current
  UNION ALL
  SELECT CAST(NULL AS BIGINT) AS merge_key, * FROM v_page_classic_changed
) s
ON t.wiki_db = s.wiki_db AND t.page_id = s.merge_key AND t.is_current = true
WHEN MATCHED THEN UPDATE SET t.is_current = false, t.valid_to = s.valid_from
WHEN NOT MATCHED THEN INSERT (page_key, wiki_db, page_id, title, namespace, is_deleted, valid_from, valid_to, is_current)
VALUES (s.page_key, s.wiki_db, s.page_id, s.title, s.namespace, s.is_deleted, s.valid_from, CAST(NULL AS TIMESTAMP), true)
