-- Every observation of a page's title, namespace and deleted state, from both sources.
-- observed_dt = when the state is true: the revision time for history rows and for edit / create / move
-- events; meta_dt for delete / undelete events (they make no revision: their rev_dt is the page's
-- newest revision, which is older than the delete).
CREATE OR REPLACE TEMP VIEW v_page_obs AS
SELECT wiki_db, page_id, page_title_historical AS title, CAST(page_ns AS INT) AS namespace,
       false AS is_deleted, ts AS observed_dt, rev_id AS seq_id
FROM delta.`{silver}/history_revisions`
UNION ALL
SELECT wiki_id AS wiki_db, page_id, page_title AS title, ns AS namespace,
       kind = 'delete' AS is_deleted,
       CASE WHEN kind IN ('delete', 'undelete') THEN meta_dt ELSE rev_dt END AS observed_dt,
       coalesce(rev_id, 0) AS seq_id
FROM delta.`{silver}/page_change`
WHERE page_id IS NOT NULL
