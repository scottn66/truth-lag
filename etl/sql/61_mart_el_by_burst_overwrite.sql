-- mart_el_by_burst (D20): the E(L) mart again, grouped by the page's edits in the hour before the edit.
-- Groups 0, 1, 2-4, 5-9, 10+ ; burst = 10 or more edits in the prior hour. Also an 'all' row per cohort.
INSERT OVERWRITE delta.`{gold}/mart_el_by_burst`
WITH g AS (
  SELECT *, CASE WHEN page_edits_prev_1h IS NULL THEN 'unknown'
                 WHEN page_edits_prev_1h = 0 THEN '0' WHEN page_edits_prev_1h = 1 THEN '1'
                 WHEN page_edits_prev_1h <= 4 THEN '2-4' WHEN page_edits_prev_1h <= 9 THEN '5-9'
                 ELSE '10+' END AS burst_group
  FROM v_reverts
)
SELECT cohort_id, label_source,
       CASE WHEN grouping(burst_group) = 1 THEN 'all' ELSE burst_group END AS burst_group,
       wait_label, wait_s, count(*) AS n_eventual,
       count_if(known_after_s <= wait_s) AS n_known,
       count_if(known_after_s <= wait_s) / count(*) AS share_known,
       1 - count_if(known_after_s <= wait_s) / count(*) AS e_l,
       count(*) < {small_group_n} AS small_group
FROM g CROSS JOIN v_waits
GROUP BY GROUPING SETS ((cohort_id, label_source, burst_group, wait_label, wait_s),
                        (cohort_id, label_source, wait_label, wait_s))
