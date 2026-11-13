-- fact_edit: one row per cohort revision (both cohorts). Change Data Feed on.
CREATE TABLE IF NOT EXISTS delta.`{gold}/fact_edit` (
  wiki_db             STRING NOT NULL,
  rev_id              BIGINT NOT NULL,
  parent_rev_id       BIGINT,
  page_key            STRING,
  user_key            STRING,
  time_key            BIGINT,
  event_dt            TIMESTAMP,
  seen_dt             TIMESTAMP,
  bytes_diff          BIGINT,
  is_bot              BOOLEAN,
  live_revert_flag    BOOLEAN,
  live_revert_dt      TIMESTAMP,
  live_known_dt       TIMESTAMP,
  revert_risk_score   DOUBLE,
  page_edits_prev_1h  BIGINT,
  cohort_id           STRING
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false',
  'delta.enableChangeDataFeed' = 'true'
)
