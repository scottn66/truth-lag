-- dim_time: insert-only. One row per UTC minute of a cohort revision (the same minutes as fact_edit.time_key).
MERGE INTO delta.`{gold}/dim_time` t
USING (
  SELECT DISTINCT CAST(date_format(ts, 'yyyyMMddHHmm') AS BIGINT) AS time_key,
                  date_trunc('minute', ts) AS minute_start
  FROM (
    SELECT ts FROM delta.`{silver}/history_revisions` WHERE ts <= TIMESTAMP '{as_of}'
    UNION ALL
    SELECT ts FROM delta.`{silver}/live_revisions` WHERE ts <= TIMESTAMP '{as_of}'
    UNION ALL
    SELECT ts FROM delta.`{silver}/live_ext_revisions` WHERE ts <= TIMESTAMP '{as_of}'
  )
) s
ON t.time_key = s.time_key
WHEN NOT MATCHED THEN INSERT (time_key, minute_start, hour, date, day_of_week)
VALUES (s.time_key, s.minute_start, hour(s.minute_start), CAST(s.minute_start AS DATE), weekday(s.minute_start) + 1)
