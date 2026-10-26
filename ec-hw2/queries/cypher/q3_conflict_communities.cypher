// Cypher Q3 (spec 4.3): communities of conflict (Louvain and WCC, with GDS)
// Question: do reverts form groups of editors who keep clashing with each other?
// The GDS projection has all Editor nodes and the REVERTED relationships as
// UNDIRECTED (who reverted whom does not matter for a group). Parallel
// relationships between two editors (other pages, the other direction) are merged
// into one, and their count values are added (aggregation SUM).
//   - Louvain finds communities: many reverts inside, few between. It WRITES the
//     property communityId on every Editor (concurrency 1, so a re-run gives the same
//     groups). An editor without any REVERTED relationship is a community of 1.
//   - WCC (weakly connected components) finds the groups joined by any chain of reverts.
// Repeatability: on the same loaded graph, Louvain gives the same communities every
// time. After a new load, Neo4j gives the nodes new internal ids, and Louvain visits
// the nodes in id order, so a few communities can merge or split (data-v1, three loads:
// modularity 0.9138, 0.9142 and 0.9143). The community numbers are internal ids, not names.
// The WCC results do not change.
// Output columns (result louvain_stats): communities, modularity, levels, editors_written.
// Output columns (result community_sizes): communities (the total, as in louvain_stats),
//   communities_2plus (communities with 2 or more editors), communities_1 (one editor
//   alone), editors_without_revert (editors with no REVERTED relationship at all; each is
//   a community of 1). Most of the total are such single editors, so report
//   communities_2plus next to the total.
// Output columns (result main = the 10 largest Louvain communities with 2+ editors):
//   rank, community, editors, bots, pages, reverts, reverted_edges, star_share, top_page,
//   top_page_reverts, top_page_share, top_reverters.
//   pages = distinct pages of the REVERTED relationships inside the community;
//   reverts = the sum of their count; reverted_edges = the number of those relationships;
//   top_reverters = the 3 members with the most reverts_made (aliases); the first one is
//   the community's top editor. star_share = the share of the community's REVERTED
//   relationships that touch the top editor (as reverter or as reverted editor). A share
//   near 1 means the community is one patroller (often a bot) and the editors it reverted,
//   not a group of editors who fight each other.
//   top_page = the page with the most of the community's reverts; top_page_reverts = its
//   reverts; top_page_share = top_page_reverts / reverts. A small share means the
//   community is spread over many pages.
// Output columns (result wcc_sizes): component_size, components, editors, share_of_editors.
// Output columns (result wcc_largest = the 5 largest components): rank, editors, bots,
//   pages, reverts, top_reverters.
// The projection is dropped at the end. Editors are shown by alias.
// Neo4j Browser: first run  :params {top_n: 20, contested_min_edits: 10, contested_min_editors: 2, contested_min_actions: 2, contested_min_score: 0.2}

// Remove an old projection with the same name (no error if there is none)
CALL gds.graph.drop('cypher_q3_undirected', false) YIELD graphName
RETURN graphName;

CALL gds.graph.project('cypher_q3_undirected', 'Editor',
  {REVERTED: {orientation: 'UNDIRECTED',
              properties: {count: {property: 'count', aggregation: 'SUM'}}}})
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount;

// result: louvain_stats
CALL gds.louvain.write('cypher_q3_undirected',
  {writeProperty: 'communityId', relationshipWeightProperty: 'count', concurrency: 1})
YIELD communityCount, modularity, ranLevels, nodePropertiesWritten
RETURN communityCount AS communities, round(modularity, 4) AS modularity,
       ranLevels AS levels, nodePropertiesWritten AS editors_written;

// result: community_sizes
// How many communities have 2 or more editors (read from the communityId just written).
MATCH (e:Editor)
WHERE e.communityId IS NOT NULL
WITH e.communityId AS community, count(*) AS editors,
     count(CASE WHEN NOT EXISTS { (e)-[:REVERTED]-() } THEN 1 END) AS no_revert
RETURN count(*) AS communities,
       count(CASE WHEN editors >= 2 THEN 1 END) AS communities_2plus,
       count(CASE WHEN editors = 1 THEN 1 END) AS communities_1,
       sum(no_revert) AS editors_without_revert;

// result: main
MATCH (e:Editor)
WHERE e.communityId IS NOT NULL
WITH e.communityId AS community, count(*) AS editors
WHERE editors >= 2
ORDER BY editors DESC, community ASC
LIMIT 10
CALL (community) {
  MATCH (m:Editor {communityId: community})
  WITH m ORDER BY m.reverts_made DESC, m.key ASC
  RETURN collect(m)[0] AS star, collect(m.alias)[0..3] AS top_reverters,
         count(CASE WHEN m.kind = 'bot' THEN 1 END) AS bots
}
CALL (community, star) {
  MATCH (x:Editor {communityId: community})-[r:REVERTED]->(y:Editor {communityId: community})
  RETURN count(DISTINCT r.page_id) AS pages, sum(r.count) AS reverts, count(r) AS edges,
         count(CASE WHEN x = star OR y = star THEN 1 END) AS star_edges
}
CALL (community) {
  MATCH (:Editor {communityId: community})-[r:REVERTED]->(:Editor {communityId: community})
  WITH r.page_id AS page_id, sum(r.count) AS n
  ORDER BY n DESC, page_id ASC
  LIMIT 1
  MATCH (p:Page {id: page_id})
  RETURN p.title AS top_page, n AS top_page_reverts
}
WITH community, editors, bots, pages, reverts, edges, star_edges, top_page, top_page_reverts,
     top_reverters
ORDER BY editors DESC, community ASC
WITH collect({community: community, editors: editors, bots: bots, pages: pages,
              reverts: reverts, edges: edges, star_edges: star_edges, top_page: top_page,
              top_page_reverts: top_page_reverts, top_reverters: top_reverters}) AS rows
UNWIND range(0, size(rows) - 1) AS i
WITH i + 1 AS rank, rows[i] AS c
RETURN rank, c.community AS community, c.editors AS editors, c.bots AS bots,
       c.pages AS pages, c.reverts AS reverts, c.edges AS reverted_edges,
       CASE WHEN c.edges > 0 THEN round(toFloat(c.star_edges) / c.edges, 3) END AS star_share,
       c.top_page AS top_page, c.top_page_reverts AS top_page_reverts,
       CASE WHEN c.reverts > 0 THEN round(toFloat(c.top_page_reverts) / c.reverts, 3) END
         AS top_page_share,
       c.top_reverters AS top_reverters
ORDER BY rank;

// result: wcc_sizes
CALL gds.wcc.stream('cypher_q3_undirected', {concurrency: 4})
YIELD nodeId, componentId
WITH componentId, count(*) AS size
WITH CASE WHEN size = 1 THEN 1 WHEN size = 2 THEN 2 WHEN size <= 5 THEN 3
          WHEN size <= 10 THEN 4 WHEN size <= 100 THEN 5 WHEN size <= 1000 THEN 6
          ELSE 7 END AS bucket, size
WITH bucket, count(*) AS components, sum(size) AS editors
WITH collect({bucket: bucket, components: components, editors: editors}) AS rows,
     sum(editors) AS all_editors
UNWIND rows AS r
RETURN ['1 (no revert at all)', '2', '3-5', '6-10', '11-100', '101-1000', 'over 1000'][r.bucket - 1]
         AS component_size,
       r.components AS components, r.editors AS editors,
       round(toFloat(r.editors) / all_editors, 4) AS share_of_editors
ORDER BY r.bucket;

// result: wcc_largest
CALL gds.wcc.stream('cypher_q3_undirected', {concurrency: 4})
YIELD nodeId, componentId
WITH componentId, collect(nodeId) AS ids, count(*) AS editors
ORDER BY editors DESC, componentId ASC
LIMIT 5
CALL (ids) {
  UNWIND ids AS id
  WITH gds.util.asNode(id) AS m
  OPTIONAL MATCH (m)-[r:REVERTED]->()
  RETURN count(DISTINCT r.page_id) AS pages, coalesce(sum(r.count), 0) AS reverts,
         count(DISTINCT CASE WHEN m.kind = 'bot' THEN m END) AS bots
}
CALL (ids) {
  UNWIND ids AS id
  WITH gds.util.asNode(id) AS m
  ORDER BY m.reverts_made DESC, m.key ASC
  LIMIT 3
  RETURN collect(m.alias) AS top_reverters
}
WITH editors, bots, pages, reverts, top_reverters
ORDER BY editors DESC, reverts DESC
WITH collect({editors: editors, bots: bots, pages: pages, reverts: reverts,
              top_reverters: top_reverters}) AS rows
UNWIND range(0, size(rows) - 1) AS i
RETURN i + 1 AS rank, rows[i].editors AS editors, rows[i].bots AS bots,
       rows[i].pages AS pages, rows[i].reverts AS reverts,
       rows[i].top_reverters AS top_reverters
ORDER BY rank;

// Drop the projection (it holds a copy of the graph in memory)
CALL gds.graph.drop('cypher_q3_undirected') YIELD graphName
RETURN graphName;
