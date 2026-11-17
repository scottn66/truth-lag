-- mart_label_change: one row per label change, from the change feed of fact_revert_label
-- (versions {start_version} .. {end_version}). Insert-only MERGE on (wiki_db, rev_id, commit_version).
MERGE INTO delta.`{gold}/mart_label_change` t
USING (
  SELECT post.wiki_db, post.rev_id,
         pre.last_changed_snapshot AS from_snapshot, post.last_changed_snapshot AS to_snapshot,
         pre.is_identity_reverted AS was_reverted, post.is_identity_reverted AS is_reverted,
         CASE WHEN NOT pre.is_identity_reverted AND post.is_identity_reverted THEN 'became_reverted'
              WHEN pre.is_identity_reverted AND NOT post.is_identity_reverted THEN 'became_unreverted'
              ELSE 'reverter_or_time_changed' END AS change_class,
         post._commit_version AS commit_version
  FROM table_changes_by_path('{gold}/fact_revert_label', {start_version}, {end_version}) post
  JOIN table_changes_by_path('{gold}/fact_revert_label', {start_version}, {end_version}) pre
    ON pre.wiki_db = post.wiki_db AND pre.rev_id = post.rev_id AND pre._commit_version = post._commit_version
  WHERE post._change_type = 'update_postimage' AND pre._change_type = 'update_preimage'
) s
ON t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id AND t.commit_version = s.commit_version
WHEN NOT MATCHED THEN INSERT *
