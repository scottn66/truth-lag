-- dim_page: SCD Type 2, one row per page version. Key page_key = page_id + start of the version (D8).
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_page` (
  page_key    STRING NOT NULL,
  wiki_db     STRING,
  page_id     BIGINT,
  title       STRING,
  namespace   INT,
  is_deleted  BOOLEAN,
  valid_from  TIMESTAMP,
  valid_to    TIMESTAMP,
  is_current  BOOLEAN
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
