-- SCD2 step 3: one MERGE on page_key. Matched = close the version; not matched = new version.
MERGE INTO delta.`{gold}/dim_page` t
USING v_page_changes s
ON t.page_key = s.page_key
WHEN MATCHED THEN UPDATE SET t.valid_to = s.valid_to, t.is_current = s.is_current
WHEN NOT MATCHED THEN INSERT (page_key, wiki_db, page_id, title, namespace, is_deleted, valid_from, valid_to, is_current)
VALUES (s.page_key, s.wiki_db, s.page_id, s.title, s.namespace, s.is_deleted, s.valid_from, s.valid_to, s.is_current)
