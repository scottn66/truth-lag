// Cypher Q2 (spec 4.2): the most central reverters (degree and PageRank, with GDS)
// Question: which editors revert the most, and who is most central in the revert graph?
// Two measures, which answer two different questions:
//   - degree (result by_degree) answers "who reverts the most": out_degree = REVERTED
//     relationships that go out (one per reverted editor and page); editors_reverted =
//     distinct editors reverted; reverts_made = the sum of count on those relationships
//     (revert actions; one revert that undid two editors counts once for each).
//   - PageRank (results main and humans) on a GDS projection of Editor + REVERTED with
//     REVERSE orientation, weight = count. A high score means "reverts editors who are
//     themselves active reverters", not "reverts a lot".
// Why REVERSE: (a)-[:REVERTED]->(b) means "a reverted b". PageRank moves score along
// the arrows, so with the natural direction the score piles up on editors who GET
// reverted. The projection turns every arrow around (b -> a), so each editor passes its
// score to the editors who reverted it. An editor therefore scores high when the editors
// it reverted have high scores themselves, which means they are active reverters too.
// So an editor with few reverts can rank high if it reverted a busy reverter who was
// seldom reverted by anyone else. The weight count gives more score to repeated reverts.
// Convergence: both PageRank calls use maxIterations 200 and tolerance 1e-7 (the GDS
// default stops after 20 iterations, before the scores settle). run_cypher.py first runs
// gds.pageRank.stats with the same settings and stops with an error if didConverge is false.
// In Neo4j Browser you can check it yourself after the projection step:
//   CALL gds.pageRank.stats('cypher_q2_reverse', {relationshipWeightProperty: 'count', concurrency: 4, maxIterations: 200, tolerance: 1e-7}) YIELD didConverge, ranIterations
// Output columns (result main = top 20 by PageRank, result humans = top 20 humans by
// PageRank): editor, kind, out_degree, editors_reverted, reverts_made,
//   reverts_received, pagerank.
// Output columns (result by_degree = top 20 by reverts_made): editor, kind, out_degree,
//   editors_reverted, reverts_made, reverts_received.
// The projection is dropped at the end. Editors are shown by alias.
// Neo4j Browser: first run  :params {top_n: 20, contested_min_edits: 10, contested_min_editors: 2, contested_min_actions: 2, contested_min_score: 0.2}

// Remove an old projection with the same name (no error if there is none)
CALL gds.graph.drop('cypher_q2_reverse', false) YIELD graphName
RETURN graphName;

// Project all Editor nodes and the REVERTED relationships, arrows turned around
CALL gds.graph.project('cypher_q2_reverse', 'Editor',
  {REVERTED: {orientation: 'REVERSE',
              properties: {count: {property: 'count', aggregation: 'SUM'}}}})
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount;

// result: main
CALL gds.pageRank.stream('cypher_q2_reverse',
  {relationshipWeightProperty: 'count', concurrency: 4, maxIterations: 200, tolerance: 1e-7})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS e, score
ORDER BY score DESC, e.key ASC
LIMIT $top_n
CALL (e) {
  OPTIONAL MATCH (e)-[r:REVERTED]->(v:Editor)
  RETURN count(r) AS out_degree, count(DISTINCT v) AS editors_reverted
}
RETURN e.alias AS editor, e.kind AS kind, out_degree, editors_reverted,
       e.reverts_made AS reverts_made, e.reverts_received AS reverts_received,
       round(score, 4) AS pagerank
ORDER BY score DESC, e.key ASC;

// result: humans
// The same ranking without bots: the most central human reverters.
CALL gds.pageRank.stream('cypher_q2_reverse',
  {relationshipWeightProperty: 'count', concurrency: 4, maxIterations: 200, tolerance: 1e-7})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS e, score
WHERE e.kind <> 'bot'
WITH e, score
ORDER BY score DESC, e.key ASC
LIMIT $top_n
CALL (e) {
  OPTIONAL MATCH (e)-[r:REVERTED]->(v:Editor)
  RETURN count(r) AS out_degree, count(DISTINCT v) AS editors_reverted
}
RETURN e.alias AS editor, e.kind AS kind, out_degree, editors_reverted,
       e.reverts_made AS reverts_made, e.reverts_received AS reverts_received,
       round(score, 4) AS pagerank
ORDER BY score DESC, e.key ASC;

// result: by_degree
// "Who reverts the most": degree only (no GDS needed); reverts_made is computed here
// from the relationships.
MATCH (e:Editor)-[r:REVERTED]->(v:Editor)
WITH e, count(r) AS out_degree, count(DISTINCT v) AS editors_reverted,
     sum(r.count) AS reverts_made
ORDER BY reverts_made DESC, out_degree DESC, e.key ASC
LIMIT $top_n
RETURN e.alias AS editor, e.kind AS kind, out_degree, editors_reverted, reverts_made,
       e.reverts_received AS reverts_received
ORDER BY reverts_made DESC, out_degree DESC, e.key ASC;

// Drop the projection (it holds a copy of the graph in memory)
CALL gds.graph.drop('cypher_q2_reverse') YIELD graphName
RETURN graphName;
