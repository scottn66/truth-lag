-- recon_mismatch: the revisions where the two labels disagree, plus the revisions the dump does not hold.
INSERT INTO delta.`{gold}/recon_mismatch`
REPLACE WHERE cohort_id = '{cohort_id}' AND snapshot = '{snapshot}'
SELECT wiki_db, rev_id, cohort_id, snapshot, recon_class, event_dt, stream_reverted, stream_revert_dt,
       stream_known_dt, stream_seconds_to_revert, dump_reverted, dump_is_identity_reverted, dump_label_dt,
       dump_seconds_to_revert, dump_reverting_rev_id
FROM v_recon
WHERE recon_class IN ('stream_only', 'dump_only', 'not_in_dump')
