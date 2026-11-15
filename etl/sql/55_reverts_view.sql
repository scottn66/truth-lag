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
UNION ALL
-- live cohort, labels from the newest loaded dump snapshot (fact_revert_label holds the current dump label).
-- Valid only when the snapshot's cutoff is >= 4 days after the live window (2026-10: cutoff 2026-11-01 01:30).
SELECT 'live', 'dump', r.user_kind, r.page_edits_prev_1h, r.page_id, CAST(f.seconds_to_identity_revert AS DOUBLE)
FROM delta.`{gold}/fact_revert_label` f
JOIN delta.`{silver}/live_revisions` r ON r.wiki_db = f.wiki_db AND r.rev_id = f.rev_id
WHERE f.is_identity_reverted AND f.seconds_to_identity_revert >= 0 AND f.seconds_to_identity_revert <= {horizon_s}
