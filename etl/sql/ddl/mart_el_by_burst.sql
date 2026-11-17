-- mart_el_by_burst: E(L) by the page's edits in the hour before the edit (D20).
CREATE TABLE IF NOT EXISTS delta.`{gold}/mart_el_by_burst` (
  cohort_id     STRING NOT NULL,
  label_source  STRING NOT NULL,
  burst_group   STRING NOT NULL,
  wait_label    STRING NOT NULL,
  wait_s        BIGINT NOT NULL,
  n_eventual    BIGINT,
  n_known       BIGINT,
  share_known   DOUBLE,
  e_l           DOUBLE,
  small_group   BOOLEAN
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
