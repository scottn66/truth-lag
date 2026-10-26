// Cypher Q5 (spec 4.5): 2-hop, editors linked through shared contested pages
// Question: which pairs of human editors meet on the most contested pages?
// The 2-hop pattern is editor -EDITED-> contested page <-EDITED- editor. A page is
// contested when Page.contested = true (export_graph.py sets it with the shared rule:
// edits >= 10, reverted_editors >= 2, revert_actions >= 2 and score >= 0.2).
// Bots are left out. Each unordered pair is listed once (a.key < b.key).
// a_reverted_b / b_reverted_a: revert actions between the two, on ANY page, so we
// see whether the pair also fought directly.
// Why the query starts from the pages: the index page_contested (load.cypher) finds the
// few contested pages first, and only their EDITED relationships are expanded. Without
// "USING INDEX" the planner starts from the editors and expands every EDITED relationship.
// Output columns: editor_a, editor_b, shared_contested_pages, a_reverted_b,
//   b_reverted_a, example_pages (up to 3 page titles, by page id).
// Top 20 by shared_contested_pages, then a.key, b.key. Editors are shown by alias.
// Neo4j Browser: first run  :params {top_n: 20, contested_min_edits: 10, contested_min_editors: 2, contested_min_actions: 2, contested_min_score: 0.2}

// result: main
MATCH (p:Page {contested: true})
USING INDEX p:Page(contested)
MATCH (a:Editor)-[:EDITED]->(p)<-[:EDITED]-(b:Editor)
WHERE a.key < b.key AND a.kind <> 'bot' AND b.kind <> 'bot'
WITH DISTINCT a, b, p
ORDER BY p.id
WITH a, b, count(p) AS shared_contested_pages, collect(p.title)[0..3] AS example_pages
ORDER BY shared_contested_pages DESC, a.key ASC, b.key ASC
LIMIT $top_n
CALL (a, b) {
  OPTIONAL MATCH (a)-[r:REVERTED]->(b)
  RETURN coalesce(sum(r.count), 0) AS a_reverted_b
}
CALL (a, b) {
  OPTIONAL MATCH (b)-[r:REVERTED]->(a)
  RETURN coalesce(sum(r.count), 0) AS b_reverted_a
}
RETURN a.alias AS editor_a, b.alias AS editor_b, shared_contested_pages,
       a_reverted_b, b_reverted_a, example_pages
ORDER BY shared_contested_pages DESC, a.key ASC, b.key ASC;
