-- dim_page: SCD Type 2. {dim_page} is the table folder (dim_page, or dim_page_classic for the comparison).
CREATE TABLE IF NOT EXISTS delta.`{gold}/{dim_page}` (
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
