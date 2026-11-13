-- SCD2 step 1: the FULL list of versions of every page, from all observations up to {as_of}.
-- One state per page and second (the last one wins), LAG finds the changes, LEAD gives valid_to.
-- The first version of a page starts at the sentinel 1900-01-01 so that earlier facts still join.
CREATE OR REPLACE TEMP VIEW v_page_versions AS
WITH per_second AS (
  SELECT wiki_db, page_id, date_trunc('second', observed_dt) AS obs_dt,
         max_by(named_struct('title', title, 'namespace', namespace, 'is_deleted', is_deleted),
                named_struct('observed_dt', observed_dt, 'seq_id', seq_id)) AS st
  FROM v_page_obs
  WHERE observed_dt <= TIMESTAMP '{as_of}'
  GROUP BY wiki_db, page_id, date_trunc('second', observed_dt)
),
marked AS (
  SELECT wiki_db, page_id, obs_dt, st.title AS title, st.namespace AS namespace, st.is_deleted AS is_deleted,
         lag(st) OVER w AS prev,
         row_number() OVER w AS rn
  FROM per_second
  WINDOW w AS (PARTITION BY wiki_db, page_id ORDER BY obs_dt)
),
starts AS (
  SELECT wiki_db, page_id, title, namespace, is_deleted,
         CASE WHEN rn = 1 THEN TIMESTAMP '1900-01-01 00:00:00' ELSE obs_dt END AS valid_from
  FROM marked
  WHERE rn = 1
     OR NOT (title <=> prev.title AND namespace <=> prev.namespace AND is_deleted <=> prev.is_deleted)
)
SELECT concat(page_id, '-', date_format(valid_from, 'yyyyMMddHHmmss')) AS page_key,
       wiki_db, page_id, title, namespace, is_deleted, valid_from,
       lead(valid_from) OVER (PARTITION BY wiki_db, page_id ORDER BY valid_from) AS valid_to,
       lead(valid_from) OVER (PARTITION BY wiki_db, page_id ORDER BY valid_from) IS NULL AS is_current
FROM starts
