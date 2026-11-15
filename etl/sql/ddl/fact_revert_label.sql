-- fact_revert_label: the dump label of every revision of every loaded snapshot. Change Data Feed on.
CREATE TABLE IF NOT EXISTS delta.`{gold}/fact_revert_label` (
  wiki_db                     STRING NOT NULL,
  rev_id                      BIGINT NOT NULL,
  is_identity_reverted        BOOLEAN,
  reverting_rev_id            BIGINT,
  seconds_to_identity_revert  BIGINT,
  label_dt                    TIMESTAMP,
  first_reverted_snapshot     STRING,
  last_changed_snapshot       STRING
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false',
  'delta.enableChangeDataFeed' = 'true'
)
