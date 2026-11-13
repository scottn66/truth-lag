-- recon_mismatch: the revisions where stream and dump disagree, or that the dump does not hold.
CREATE TABLE IF NOT EXISTS delta.`{gold}/recon_mismatch` (
  wiki_db                    STRING NOT NULL,
  rev_id                     BIGINT NOT NULL,
  cohort_id                  STRING NOT NULL,
  snapshot                   STRING NOT NULL,
  recon_class                STRING,
  event_dt                   TIMESTAMP,
  stream_reverted            BOOLEAN,
  stream_revert_dt           TIMESTAMP,
  stream_known_dt            TIMESTAMP,
  stream_seconds_to_revert   BIGINT,
  dump_reverted              BOOLEAN,
  dump_is_identity_reverted  BOOLEAN,
  dump_label_dt              TIMESTAMP,
  dump_seconds_to_revert     BIGINT,
  dump_reverting_rev_id      BIGINT
) USING DELTA
TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 3650 days',
  'delta.deletedFileRetentionDuration' = 'interval 3650 days',
  'delta.enableExpiredLogCleanup' = 'false'
)
