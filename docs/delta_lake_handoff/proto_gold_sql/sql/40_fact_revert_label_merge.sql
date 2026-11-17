-- fact_revert_label: load ONE snapshot as ONE commit. Updates only rows whose label columns changed,
-- inserts the revisions not seen before. An older snapshot can never overwrite a newer label
-- ('{snapshot}' >= last_changed_snapshot), so re-running any load writes no commit.
MERGE INTO delta.`{gold}/fact_revert_label` t
USING (
  WITH snap AS (
    SELECT 'enwiki' AS wiki_db, revision_id AS rev_id,
           coalesce(revision_is_identity_reverted, false) AS is_identity_reverted,
           revision_first_identity_reverting_revision_id AS reverting_rev_id,
           revision_seconds_to_identity_revert AS seconds_to_identity_revert,
           CASE WHEN coalesce(revision_is_identity_reverted, false)
                THEN timestamp_micros(unix_micros(event_timestamp) + revision_seconds_to_identity_revert * 1000000)
           END AS label_dt
    FROM delta.`{silver}/history_slim`
    WHERE snapshot = '{snapshot}'
  )
  SELECT s.*,
         CASE WHEN s.is_identity_reverted THEN '{snapshot}' END AS first_reverted_snapshot,
         '{snapshot}' AS last_changed_snapshot
  FROM snap s
  LEFT JOIN delta.`{gold}/fact_revert_label` f ON f.wiki_db = s.wiki_db AND f.rev_id = s.rev_id
  WHERE f.rev_id IS NULL
     OR ('{snapshot}' >= f.last_changed_snapshot
         AND NOT (f.is_identity_reverted <=> s.is_identity_reverted
                  AND f.reverting_rev_id <=> s.reverting_rev_id
                  AND f.seconds_to_identity_revert <=> s.seconds_to_identity_revert
                  AND f.label_dt <=> s.label_dt))
) s
ON t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id
WHEN MATCHED THEN UPDATE SET
  t.is_identity_reverted = s.is_identity_reverted,
  t.reverting_rev_id = s.reverting_rev_id,
  t.seconds_to_identity_revert = s.seconds_to_identity_revert,
  t.label_dt = s.label_dt,
  t.first_reverted_snapshot = coalesce(t.first_reverted_snapshot, s.first_reverted_snapshot),
  t.last_changed_snapshot = s.last_changed_snapshot
WHEN NOT MATCHED THEN INSERT (wiki_db, rev_id, is_identity_reverted, reverting_rev_id, seconds_to_identity_revert,
                              label_dt, first_reverted_snapshot, last_changed_snapshot)
VALUES (s.wiki_db, s.rev_id, s.is_identity_reverted, s.reverting_rev_id, s.seconds_to_identity_revert,
        s.label_dt, s.first_reverted_snapshot, s.last_changed_snapshot)
