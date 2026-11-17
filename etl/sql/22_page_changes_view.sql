-- SCD2 step 2: keep only the versions that are new, or whose valid_to / is_current changed.
CREATE OR REPLACE TEMP VIEW v_page_changes AS
SELECT n.*
FROM v_page_versions n
LEFT JOIN delta.`{gold}/dim_page` d ON d.page_key = n.page_key
WHERE d.page_key IS NULL
   OR NOT (d.valid_to <=> n.valid_to)
   OR NOT (d.is_current <=> n.is_current)
