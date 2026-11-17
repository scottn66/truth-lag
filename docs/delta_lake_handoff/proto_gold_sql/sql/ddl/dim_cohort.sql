-- dim_cohort: one row per cohort. Values come from config.py (HISTORY_WINDOW, LIVE_WINDOW, *_FOLLOWUP_DAYS).
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_cohort` (
  cohort_id      STRING NOT NULL,
  source         STRING,
  window_start   TIMESTAMP,
  window_end     TIMESTAMP,
  followup_days  INT
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
