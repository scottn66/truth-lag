-- dim_time: one row per UTC minute that occurs in fact_edit. day_of_week: 1 = Monday .. 7 = Sunday.
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_time` (
  time_key      BIGINT NOT NULL,
  minute_start  TIMESTAMP,
  hour          INT,
  date          DATE,
  day_of_week   INT
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
