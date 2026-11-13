-- fact_edit: one row per cohort revision with ts <= {as_of}; live labels known up to {as_of}.
-- page_key is the dim_page version valid at the edit time (as-of join). MERGE on (wiki_db, rev_id),
-- pre-filtered to new or changed rows, so a re-run writes no commit and the change feed holds real changes only.
MERGE INTO delta.`{gold}/fact_edit` t
USING (
  WITH revs AS (
    SELECT cohort, wiki_db, rev_id, parent_id, page_id, user_key, ts, seen_ts, size_delta, is_bot,
           revert_risk, page_edits_prev_1h
    FROM delta.`{silver}/history_revisions` WHERE ts <= TIMESTAMP '{as_of}'
    UNION ALL
    SELECT cohort, wiki_db, rev_id, parent_id, page_id, user_key, ts, seen_ts, size_delta, is_bot,
           revert_risk, page_edits_prev_1h
    FROM delta.`{silver}/live_revisions` WHERE ts <= TIMESTAMP '{as_of}'
  ),
  links AS (
    SELECT reverted_rev_id, reverting_ts, known_at
    FROM delta.`{silver}/live_revert_links`
    WHERE within_followup AND known_at <= TIMESTAMP '{as_of}'
  ),
  src AS (
    SELECT r.wiki_db, r.rev_id, r.parent_id AS parent_rev_id, p.page_key,
           coalesce(r.user_key, 'unknown') AS user_key,
           CAST(date_format(r.ts, 'yyyyMMddHHmm') AS BIGINT) AS time_key,
           r.ts AS event_dt, r.seen_ts AS seen_dt, r.size_delta AS bytes_diff, r.is_bot,
           CASE WHEN r.cohort = 'live' THEN l.reverted_rev_id IS NOT NULL END AS live_revert_flag,
           l.reverting_ts AS live_revert_dt, l.known_at AS live_known_dt,
           r.revert_risk AS revert_risk_score, r.page_edits_prev_1h, r.cohort AS cohort_id
    FROM revs r
    LEFT JOIN delta.`{gold}/dim_page` p
      ON p.wiki_db = r.wiki_db AND p.page_id = r.page_id
     AND r.ts >= p.valid_from AND (p.valid_to IS NULL OR r.ts < p.valid_to)
    LEFT JOIN links l ON r.cohort = 'live' AND l.reverted_rev_id = r.rev_id
  )
  SELECT s.*
  FROM src s
  LEFT JOIN delta.`{gold}/fact_edit` f ON f.wiki_db = s.wiki_db AND f.rev_id = s.rev_id
  WHERE f.rev_id IS NULL
     OR NOT (f.parent_rev_id <=> s.parent_rev_id AND f.page_key <=> s.page_key AND f.user_key <=> s.user_key
             AND f.time_key <=> s.time_key AND f.event_dt <=> s.event_dt AND f.seen_dt <=> s.seen_dt
             AND f.bytes_diff <=> s.bytes_diff AND f.is_bot <=> s.is_bot
             AND f.live_revert_flag <=> s.live_revert_flag AND f.live_revert_dt <=> s.live_revert_dt
             AND f.live_known_dt <=> s.live_known_dt AND f.revert_risk_score <=> s.revert_risk_score
             AND f.page_edits_prev_1h <=> s.page_edits_prev_1h AND f.cohort_id <=> s.cohort_id)
) s
ON t.wiki_db = s.wiki_db AND t.rev_id = s.rev_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
