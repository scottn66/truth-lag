-- Classic SCD2 (for comparison only): ONE incoming row per page = its current state in v_page_versions.
CREATE OR REPLACE TEMP VIEW v_page_classic_changed AS
SELECT u.*, d.page_id IS NOT NULL AS has_current
FROM (SELECT * FROM v_page_versions WHERE is_current) u
LEFT JOIN (SELECT * FROM delta.`{gold}/dim_page_classic` WHERE is_current) d
  ON d.wiki_db = u.wiki_db AND d.page_id = u.page_id
WHERE d.page_id IS NULL
   OR (NOT (d.title <=> u.title AND d.namespace <=> u.namespace AND d.is_deleted <=> u.is_deleted)
       AND u.valid_from > d.valid_from)
