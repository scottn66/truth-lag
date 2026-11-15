-- dim_snapshot: one row per MediaWiki History snapshot loaded into fact_revert_label.
CREATE TABLE IF NOT EXISTS delta.`{gold}/dim_snapshot` (
  snapshot         STRING NOT NULL,
  snapshot_cutoff  TIMESTAMP,
  loaded_at        TIMESTAMP,
  revision_rows    BIGINT,
  snapshot_published_at TIMESTAMP
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
