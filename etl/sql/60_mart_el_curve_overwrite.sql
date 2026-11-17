-- mart_el_curve: full rebuild. An eventual revert has 0 <= T_s <= {horizon_s}; it is known by wait L
-- when T_s + coalesce(K_s, 0) <= L (inclusive). e_l = 1 - n_known / n_eventual.
-- user_kind is the kind AT EDIT TIME (Silver revisions), not dim_user (Type 1, latest kind).
-- v_waits holds config.WAIT_POINTS_S (made by the runner). Groups under {small_group_n} reverts are flagged.
INSERT OVERWRITE delta.`{gold}/mart_el_curve`
SELECT cohort_id, label_source,
       CASE WHEN grouping(user_kind) = 1 THEN 'all' ELSE coalesce(user_kind, 'unknown') END AS user_kind,
       wait_label, wait_s,
       count(*) AS n_eventual,
       count_if(known_after_s <= wait_s) AS n_known,
       count_if(known_after_s <= wait_s) / count(*) AS share_known,
       1 - count_if(known_after_s <= wait_s) / count(*) AS e_l,
       count(*) < {small_group_n} AS small_group
FROM v_reverts CROSS JOIN v_waits
GROUP BY GROUPING SETS ((cohort_id, label_source, user_kind, wait_label, wait_s),
                        (cohort_id, label_source, wait_label, wait_s))
