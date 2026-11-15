-- mart_reconciliation: replaces only the rows of this cohort and snapshot. All five classes always appear.
INSERT INTO delta.`{gold}/mart_reconciliation`
REPLACE WHERE cohort_id = '{cohort_id}' AND snapshot = '{snapshot}'
SELECT '{cohort_id}' AS cohort_id, '{snapshot}' AS snapshot, CAST({label_version} AS BIGINT) AS label_version,
       c.recon_class, count(v.rev_id) AS n_revisions,
       count(v.rev_id) / (SELECT count(*) FROM v_recon) AS share
FROM VALUES ('both_reverted'), ('stream_only'), ('dump_only'), ('neither'), ('not_in_dump') AS c(recon_class)
LEFT JOIN v_recon v ON v.recon_class = c.recon_class
GROUP BY c.recon_class
