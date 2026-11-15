-- dim_user: Type 1. Per user_key the values of the newest cohort revision (ts, then rev_id) win.
-- Only new keys and keys whose values changed reach the MERGE, so a re-run writes no commit.
MERGE INTO delta.`{gold}/dim_user` t
USING (
  WITH revs AS (
    SELECT user_key, user_id, user_name, user_kind, is_bot, is_temp, ts, rev_id
    FROM delta.`{silver}/history_revisions` WHERE ts <= TIMESTAMP '{as_of}'
    UNION ALL
    SELECT user_key, user_id, user_name, user_kind, is_bot, is_temp, ts, rev_id
    FROM delta.`{silver}/live_revisions` WHERE ts <= TIMESTAMP '{as_of}'
    UNION ALL
    SELECT user_key, user_id, user_name, user_kind, is_bot, is_temp, ts, rev_id
    FROM delta.`{silver}/live_ext_revisions` WHERE ts <= TIMESTAMP '{as_of}'
  ),
  latest AS (
    SELECT coalesce(user_key, 'unknown') AS user_key,
           max_by(named_struct('user_id', user_id, 'user_text', user_name, 'user_kind', user_kind,
                               'is_bot', is_bot, 'is_temporary', is_temp),
                  named_struct('ts', ts, 'rev_id', rev_id)) AS v
    FROM revs
    GROUP BY coalesce(user_key, 'unknown')
  )
  SELECT l.user_key, l.v.user_id AS user_id, l.v.user_text AS user_text, l.v.user_kind AS user_kind,
         l.v.is_bot AS is_bot, l.v.is_temporary AS is_temporary
  FROM latest l
  LEFT JOIN delta.`{gold}/dim_user` d ON d.user_key = l.user_key
  WHERE d.user_key IS NULL
     OR NOT (d.user_id <=> l.v.user_id AND d.user_text <=> l.v.user_text AND d.user_kind <=> l.v.user_kind
             AND d.is_bot <=> l.v.is_bot AND d.is_temporary <=> l.v.is_temporary)
) s
ON t.user_key = s.user_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
