-- Every observation of a page's title, namespace and deleted state, up to {as_of}.
-- observed_dt = when the state is true: the revision time for history rows and for edit / create / move
-- events; meta_dt for delete / undelete events (they make no revision). visibility_change events are left
-- out: they change no title, namespace or deleted state, and carry the time of an older revision.
-- Stream rows are kept only when their publish time meta_dt is also <= {as_of} (repeatable builds).
-- Branch 2: the dump's current title of every history-cohort page, observed at the snapshot cutoff
-- {dump_cutoff}. A version made from it starts when the new title was first seen, not when the page moved.
CREATE OR REPLACE TEMP VIEW v_page_obs AS
SELECT wiki_db, page_id, page_title_historical AS title, CAST(page_ns AS INT) AS namespace,
       false AS is_deleted, ts AS observed_dt, rev_id AS seq_id
FROM delta.`{silver}/history_revisions`
WHERE ts <= TIMESTAMP '{as_of}'
UNION ALL
SELECT wiki_db, page_id, cur_title, CAST(cur_ns AS INT), false, TIMESTAMP '{dump_cutoff}', 0L
FROM (
  SELECT wiki_db, page_id, max_by(page_title, ts) AS cur_title, max_by(page_ns, ts) AS cur_ns
  FROM delta.`{silver}/history_revisions`
  WHERE page_title IS NOT NULL
  GROUP BY wiki_db, page_id
)
WHERE TIMESTAMP '{dump_cutoff}' <= TIMESTAMP '{as_of}'
UNION ALL
SELECT wiki_id AS wiki_db, page_id, page_title AS title, ns AS namespace,
       kind = 'delete' AS is_deleted,
       CASE WHEN kind IN ('delete', 'undelete') THEN meta_dt ELSE rev_dt END AS observed_dt,
       coalesce(rev_id, 0) AS seq_id
FROM delta.`{silver}/page_change`
WHERE page_id IS NOT NULL AND kind <> 'visibility_change' AND meta_dt <= TIMESTAMP '{as_of}'
