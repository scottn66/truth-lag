// Comparison query (spec 5): the top 20 contested pages, in Cypher
// Question: which pages have the most revert actions per human edit?
// The shared definition (DATA_MODEL.md section 7), computed here from the EDITED
// relationships, NOT from the counts stored on the Page nodes:
//   revert_actions   = count(DISTINCT reverting_rev_id) of the EDITED relationships
//                      with within_followup AND reverted_by_other
//   reverted_editors = distinct editors with such EDITED relationships
//   edits            = EDITED relationships from non-bot editors
//   Keep pages with reverted_editors >= 2 and edits >= 10.
//   score = toFloat(revert_actions) / edits.
//   Order: score desc, revert_actions desc, edits desc, page_id asc; top 20.
//   contested = revert_actions >= 2, reverted_editors >= 2 and score >= 0.2.
// The steps are the same in MongoDB (Mongo Q2), Cypher and SQL, so the 3 engines do the
// same work: (1) the first MATCH takes the EDITED relationships with the revert flags and
// keeps the pages with 2 or more reverted editors; (2) the second MATCH counts the human
// edits only for those pages; (3) score, filter, order and limit.
// There is no rank column: run_cypher.py adds it in Python, as run_mongo.py does for Mongo Q2.
// It must give the same 20 page_ids and scores (rounded to 6 digits) as Mongo Q2
// (results/mongo_q2_top_contested_pages.csv) and the SQL query. run_cypher.py checks this.
// Note: the 3 history revisions without an editor key (the dump hides the name)
// have no EDITED relationship; Mongo Q2 counts them as human edits. None of their
// 3 pages is near the top 20 (data-v1).
// Output columns: page_id, page_title, edits, revert_actions, reverted_editors, score,
//   contested.
// Neo4j Browser: first run  :params {top_n: 20, contested_min_edits: 10, contested_min_editors: 2, contested_min_actions: 2, contested_min_score: 0.2}

// result: main
MATCH (ed:Editor)-[e:EDITED]->(p:Page)
WHERE e.within_followup AND e.reverted_by_other
WITH p, count(DISTINCT e.reverting_rev_id) AS revert_actions,
     count(DISTINCT ed) AS reverted_editors
WHERE reverted_editors >= $contested_min_editors
MATCH (x:Editor)-[:EDITED]->(p)
WITH p, revert_actions, reverted_editors,
     count(CASE WHEN x.kind <> 'bot' THEN 1 END) AS edits
WHERE edits >= $contested_min_edits
WITH p, edits, revert_actions, reverted_editors,
     toFloat(revert_actions) / edits AS score
ORDER BY score DESC, revert_actions DESC, edits DESC, p.id ASC
LIMIT $top_n
RETURN p.id AS page_id, p.title AS page_title, edits, revert_actions, reverted_editors, score,
       (revert_actions >= $contested_min_actions
        AND reverted_editors >= $contested_min_editors
        AND score >= $contested_min_score) AS contested
ORDER BY score DESC, revert_actions DESC, edits DESC, page_id ASC;
