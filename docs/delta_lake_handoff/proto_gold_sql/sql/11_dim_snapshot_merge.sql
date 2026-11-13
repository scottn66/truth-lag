-- dim_snapshot: one row per loaded snapshot. loaded_at is not compared, so a re-run writes nothing.
MERGE INTO delta.`{gold}/dim_snapshot` t
USING (
  SELECT s.*
  FROM (
    SELECT snapshot, max(event_timestamp) AS snapshot_cutoff, current_timestamp() AS loaded_at,
           count(*) AS revision_rows
    FROM delta.`{silver}/history_slim`
    WHERE snapshot = '{snapshot}'
    GROUP BY snapshot
  ) s
  LEFT JOIN delta.`{gold}/dim_snapshot` d ON d.snapshot = s.snapshot
  WHERE d.snapshot IS NULL
     OR NOT (d.snapshot_cutoff <=> s.snapshot_cutoff AND d.revision_rows <=> s.revision_rows)
) s
ON t.snapshot = s.snapshot
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
