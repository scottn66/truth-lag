-- "As known then" against "now": the live cohort's reverts as the lake knew them at three build times.
-- {v_early}, {v_parity}, {v_ext} are versions of gold/fact_edit found by their commit metadata as_of (never by
-- timestamp, D9). The kit's version compared two History snapshots; no 2026-10 snapshot exists, so the knowledge
-- axis here is the stream's as_of.
WITH snap AS (
  SELECT 'then: as_of {as_of_early}' AS known_at, {v_early} AS fact_edit_version, rev_id, live_revert_flag, live_known_dt
  FROM delta.`{gold}/fact_edit` VERSION AS OF {v_early} WHERE cohort_id = 'live'
  UNION ALL
  SELECT 'parity: as_of {as_of_parity}', {v_parity}, rev_id, live_revert_flag, live_known_dt
  FROM delta.`{gold}/fact_edit` VERSION AS OF {v_parity} WHERE cohort_id = 'live'
  UNION ALL
  SELECT 'now: as_of {as_of_ext}', {v_ext}, rev_id, live_revert_flag, live_known_dt
  FROM delta.`{gold}/fact_edit` VERSION AS OF {v_ext} WHERE cohort_id = 'live'
)
SELECT known_at, fact_edit_version, count(*) AS live_revisions,
       count_if(live_revert_flag) AS reverted_as_known, round(100 * count_if(live_revert_flag) / count(*), 3) AS pct_reverted,
       max(live_known_dt) AS newest_known_dt
FROM snap
GROUP BY known_at, fact_edit_version
ORDER BY fact_edit_version
