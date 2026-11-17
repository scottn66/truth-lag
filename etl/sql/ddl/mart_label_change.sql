-- mart_label_change: one row per revision whose dump label changed in a snapshot load (from the change feed).
CREATE TABLE IF NOT EXISTS delta.`{gold}/mart_label_change` (
  wiki_db         STRING NOT NULL,
  rev_id          BIGINT NOT NULL,
  from_snapshot   STRING,
  to_snapshot     STRING,
  was_reverted    BOOLEAN,
  is_reverted     BOOLEAN,
  change_class    STRING,
  commit_version  BIGINT NOT NULL
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
