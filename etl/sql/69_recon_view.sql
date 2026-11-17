-- Reconciliation of one cohort against one snapshot, on (wiki_db, rev_id).
-- Stream label = fact_edit.live_revert_flag (a within_followup link exists).
-- Dump label   = is_identity_reverted with seconds <= {horizon_s}, read from the version of
-- fact_revert_label that the load of {snapshot} wrote ({label_version}, found by its commit metadata).
CREATE OR REPLACE TEMP VIEW v_recon AS
WITH j AS (
  SELECT e.wiki_db, e.rev_id, e.cohort_id, e.event_dt,
         coalesce(e.live_revert_flag, false) AS stream_reverted,
         e.live_revert_dt AS stream_revert_dt, e.live_known_dt AS stream_known_dt,
         l.rev_id IS NOT NULL AS in_dump,
         coalesce(l.is_identity_reverted AND l.seconds_to_identity_revert <= {horizon_s}, false) AS dump_reverted_h,
         l.is_identity_reverted AS dump_is_identity_reverted, l.label_dt AS dump_label_dt,
         l.seconds_to_identity_revert AS dump_seconds_to_revert, l.reverting_rev_id AS dump_reverting_rev_id
  FROM delta.`{gold}/fact_edit` e
  LEFT JOIN delta.`{gold}/fact_revert_label` VERSION AS OF {label_version} l
    ON l.wiki_db = e.wiki_db AND l.rev_id = e.rev_id
  WHERE e.cohort_id = '{cohort_id}'
)
SELECT wiki_db, rev_id, cohort_id, '{snapshot}' AS snapshot,
       CASE WHEN NOT in_dump THEN 'not_in_dump'
            WHEN stream_reverted AND dump_reverted_h THEN 'both_reverted'
            WHEN stream_reverted THEN 'stream_only'
            WHEN dump_reverted_h THEN 'dump_only'
            ELSE 'neither' END AS recon_class,
       event_dt, stream_reverted, stream_revert_dt, stream_known_dt,
       unix_seconds(stream_revert_dt) - unix_seconds(event_dt) AS stream_seconds_to_revert,
       CASE WHEN in_dump THEN dump_reverted_h END AS dump_reverted,
       dump_is_identity_reverted, dump_label_dt, dump_seconds_to_revert, dump_reverting_rev_id
FROM j
