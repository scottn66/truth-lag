-- mart_el_curve: E(L) = share of eventual reverts not yet known after waiting L.
CREATE TABLE IF NOT EXISTS delta.`{gold}/mart_el_curve` (
  cohort_id     STRING NOT NULL,
  label_source  STRING NOT NULL,
  user_kind     STRING NOT NULL,
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
