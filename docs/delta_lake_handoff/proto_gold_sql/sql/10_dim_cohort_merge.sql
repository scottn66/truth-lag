-- dim_cohort: Type 1 upsert, changed rows only. The values are the cohort rules of config.py.
-- (Named parameters, :name with spark.sql(text, args=...), are NOT bound inside MERGE here: see Pitfalls.)
MERGE INTO delta.`{gold}/dim_cohort` t
USING (
  SELECT s.*
  FROM (
    SELECT 'history' AS cohort_id, 'dump' AS source,
           TIMESTAMP '{history_start}' AS window_start, TIMESTAMP '{history_end}' AS window_end,
           CAST({history_followup_days} AS INT) AS followup_days
    UNION ALL
    SELECT 'live', 'stream',
           TIMESTAMP '{live_start}', TIMESTAMP '{live_end}', CAST({live_followup_days} AS INT)
  ) s
  LEFT JOIN delta.`{gold}/dim_cohort` d ON d.cohort_id = s.cohort_id
  WHERE d.cohort_id IS NULL
     OR NOT (d.source <=> s.source AND d.window_start <=> s.window_start
             AND d.window_end <=> s.window_end AND d.followup_days <=> s.followup_days)
) s
ON t.cohort_id = s.cohort_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
