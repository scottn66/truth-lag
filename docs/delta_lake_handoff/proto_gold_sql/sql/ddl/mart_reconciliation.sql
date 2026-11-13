-- mart_reconciliation: stream label against dump label, counts per class, per cohort and snapshot.
CREATE TABLE IF NOT EXISTS delta.`{gold}/mart_reconciliation` (
  cohort_id      STRING NOT NULL,
  snapshot       STRING NOT NULL,
  label_version  BIGINT,
  recon_class    STRING NOT NULL,
  n_revisions    BIGINT,
  share          DOUBLE
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
