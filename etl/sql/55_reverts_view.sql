-- Every eventual revert (0 <= T_s <= {horizon_s}) of every cohort, with its known-after time T_s + coalesce(K_s, 0),
-- the author's kind at edit time and the page's edits in the hour before the edit. Feeds both E(L) marts.
CREATE OR REPLACE TEMP VIEW v_reverts AS
SELECT 'live' AS cohort_id, 'stream' AS label_source, r.user_kind, r.page_edits_prev_1h, r.page_id,
       CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0) AS known_after_s
FROM delta.`{silver}/live_revert_links` l
JOIN delta.`{silver}/live_revisions` r ON r.rev_id = l.reverted_rev_id
WHERE l.T_s >= 0 AND l.T_s <= {horizon_s}
UNION ALL
SELECT 'live_ext', 'stream', r.user_kind, r.page_edits_prev_1h, r.page_id, CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0)
FROM delta.`{silver}/live_ext_revert_links` l
JOIN delta.`{silver}/live_ext_revisions` r ON r.rev_id = l.reverted_rev_id
WHERE l.T_s >= 0 AND l.T_s <= {horizon_s}
UNION ALL
SELECT 'history', 'dump', r.user_kind, r.page_edits_prev_1h, r.page_id, CAST(l.T_s AS DOUBLE) + coalesce(l.K_s, 0)
FROM delta.`{silver}/history_revert_links` l
JOIN delta.`{silver}/history_revisions` r ON r.rev_id = l.reverted_rev_id
WHERE l.T_s >= 0 AND l.T_s <= {horizon_s}
