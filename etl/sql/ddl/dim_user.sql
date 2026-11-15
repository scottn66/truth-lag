-- dim_user: Type 1 (latest values win). user_key 'unknown' stands for editors whose name the source hides.
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_user` (
  user_key      STRING NOT NULL,
  user_id       BIGINT,
  user_text     STRING,
  user_kind     STRING,
  is_bot        BOOLEAN,
  is_temporary  BOOLEAN
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
