-- mart_el_curve: full rebuild. An eventual revert has 0 <= T_s <= {horizon_s}; it is known by wait L
-- when T_s + coalesce(K_s, 0) <= L (inclusive). e_l = 1 - n_known / n_eventual.
-- user_kind is the kind AT EDIT TIME (Silver revisions), not dim_user (Type 1, latest kind).
INSERT OVERWRITE delta.`{gold}/mart_el_curve`
WITH waits AS (
  SELECT * FROM VALUES ('0', 0L), ('1 min', 60L), ('5 min', 300L), ('15 min', 900L), ('1 h', 3600L),
                       ('6 h', 21600L), ('1 d', 86400L), ('2 d', 172800L), ('4 d', 345600L)
       AS w(wait_label, wait_s)
),
reverts AS (
  SELECT 'live' AS cohort_id, 'stream' AS label_source, r.user_kind,
         CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0) AS known_after_s
  FROM delta.`{silver}/live_revert_links` l
  JOIN delta.`{silver}/live_revisions` r ON r.rev_id = l.reverted_rev_id
  WHERE l.T_s >= 0 AND l.T_s <= {horizon_s}
  UNION ALL
  SELECT 'history', 'dump', r.user_kind, CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0)
  FROM delta.`{silver}/history_revert_links` l
  JOIN delta.`{silver}/history_revisions` r ON r.rev_id = l.reverted_rev_id
  WHERE l.T_s >= 0 AND l.T_s <= {horizon_s}
  UNION ALL
  SELECT 'live', 'dump', r.user_kind, CAST(f.seconds_to_identity_revert AS DOUBLE)
  FROM delta.`{gold}/fact_revert_label` f
  JOIN delta.`{silver}/live_revisions` r ON r.wiki_db = f.wiki_db AND r.rev_id = f.rev_id
  WHERE f.is_identity_reverted AND f.seconds_to_identity_revert >= 0 AND f.seconds_to_identity_revert <= {horizon_s}
)
SELECT cohort_id, label_source,
       CASE WHEN grouping(user_kind) = 1 THEN 'all' ELSE user_kind END AS user_kind,
       wait_label, wait_s,
       count(*) AS n_eventual,
       count_if(known_after_s <= wait_s) AS n_known,
       count_if(known_after_s <= wait_s) / count(*) AS share_known,
       1 - count_if(known_after_s <= wait_s) / count(*) AS e_l,
       count(*) < {small_group_n} AS small_group
FROM reverts CROSS JOIN waits
GROUP BY GROUPING SETS ((cohort_id, label_source, user_kind, wait_label, wait_s),
                        (cohort_id, label_source, wait_label, wait_s))
