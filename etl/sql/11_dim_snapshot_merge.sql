-- dim_snapshot: one row per loaded snapshot. The cutoff (the snapshot's last revision time) and the published
-- time (Last-Modified of its month files) are passed in by the runner: 2026-09 from config.HISTORY_DUMP_LAST_REVISION
-- (published time unknown), 2026-10 from the newest revision of its 2026-11 file and data/history_raw/2026-10/LAST_MODIFIED.txt.
-- loaded_at is not compared, so a re-run writes nothing.
MERGE INTO delta.`{gold}/dim_snapshot` t
USING (
  SELECT s.*
  FROM (
    SELECT snapshot, TIMESTAMP '{snapshot_cutoff}' AS snapshot_cutoff, current_timestamp() AS loaded_at,
           count(*) AS revision_rows, try_cast('{snapshot_published_at}' AS TIMESTAMP) AS snapshot_published_at
    FROM delta.`{silver}/history_slim`
    WHERE snapshot = '{snapshot}'
    GROUP BY snapshot
  ) s
  LEFT JOIN delta.`{gold}/dim_snapshot` d ON d.snapshot = s.snapshot
  WHERE d.snapshot IS NULL
     OR NOT (d.snapshot_cutoff <=> s.snapshot_cutoff AND d.revision_rows <=> s.revision_rows
             AND d.snapshot_published_at <=> s.snapshot_published_at)
) s
ON t.snapshot = s.snapshot
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
