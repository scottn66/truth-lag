-- "As known then" against "now": reverted history-cohort revisions per snapshot.
-- {v_2026_09} and {v_2026_10} are the versions of fact_revert_label that the two snapshot loads wrote;
-- the runner finds them in DESCRIBE HISTORY by userMetadata (never by timestamp).
WITH hist AS (
  SELECT wiki_db, rev_id FROM delta.`{gold}/fact_edit` WHERE cohort_id = 'history'
),
then_now AS (
  SELECT '2026-09' AS snapshot, {v_2026_09} AS label_version, l.rev_id, l.is_identity_reverted
  FROM delta.`{gold}/fact_revert_label` VERSION AS OF {v_2026_09} l
  UNION ALL
  SELECT '2026-10', {v_2026_10}, l.rev_id, l.is_identity_reverted
  FROM delta.`{gold}/fact_revert_label` VERSION AS OF {v_2026_10} l
)
SELECT t.snapshot, t.label_version,
       count_if(t.is_identity_reverted) AS reverted_as_known_then,
       count_if(n.is_identity_reverted) AS reverted_now
FROM then_now t
JOIN hist h ON h.rev_id = t.rev_id
JOIN delta.`{gold}/fact_revert_label` n ON n.rev_id = t.rev_id
GROUP BY t.snapshot, t.label_version
ORDER BY t.snapshot
