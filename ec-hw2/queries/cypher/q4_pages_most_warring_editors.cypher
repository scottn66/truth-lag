// Cypher Q4 (spec 4.4): the pages with the most distinct warring editors
// Question: on which pages do the most editors fight each other?
// Two counts per page (both use reverts by another editor within 20 days):
//   - warring_editors: distinct editors who are in at least one mutual-revert pair
//     on the page (A reverted B AND B reverted A on this page, as in Cypher Q1).
//   - editors_in_any_revert: distinct editors at either end of any REVERTED
//     relationship on the page (they reverted someone there, or someone reverted
//     them there). Mutual pairs are rare, so this second count is wider.
// mutual_pairs = unordered mutual pairs on the page; edits and revert_actions come
// from the Page node (the shared definition of DATA_MODEL.md section 7).
// Output columns (result main = top 20 by warring_editors, then page_id): page_id,
//   page_title, warring_editors, mutual_pairs, editors_in_any_revert, revert_actions, edits.
// Output columns (result by_any_revert = top 20 by editors_in_any_revert, then
//   page_id): the same columns.
// Neo4j Browser: first run  :params {top_n: 20, contested_min_edits: 10, contested_min_editors: 2, contested_min_actions: 2, contested_min_score: 0.2}

// result: main
MATCH (a:Editor)-[r1:REVERTED]->(b:Editor)-[r2:REVERTED]->(a)
WHERE r1.page_id = r2.page_id
WITH r1.page_id AS page_id, count(DISTINCT a) AS warring_editors,
     count(*) / 2 AS mutual_pairs
CALL (page_id) {
  MATCH (x:Editor)-[r:REVERTED]->(y:Editor)
  WHERE r.page_id = page_id
  WITH collect(x) + collect(y) AS people
  UNWIND people AS e
  RETURN count(DISTINCT e) AS editors_in_any_revert
}
WITH page_id, warring_editors, mutual_pairs, editors_in_any_revert
ORDER BY warring_editors DESC, page_id ASC
LIMIT $top_n
MATCH (p:Page {id: page_id})
RETURN page_id, p.title AS page_title, warring_editors, mutual_pairs,
       editors_in_any_revert, p.revert_actions AS revert_actions, p.edits AS edits
ORDER BY warring_editors DESC, page_id ASC;

// result: by_any_revert
MATCH (x:Editor)-[r:REVERTED]->(y:Editor)
WITH r.page_id AS page_id, collect(x) + collect(y) AS people
UNWIND people AS e
WITH page_id, count(DISTINCT e) AS editors_in_any_revert
ORDER BY editors_in_any_revert DESC, page_id ASC
LIMIT $top_n
CALL (page_id) {
  OPTIONAL MATCH (a:Editor)-[r1:REVERTED]->(b:Editor)-[r2:REVERTED]->(a)
  WHERE r1.page_id = page_id AND r2.page_id = page_id
  RETURN count(DISTINCT a) AS warring_editors, count(r1) / 2 AS mutual_pairs
}
MATCH (p:Page {id: page_id})
RETURN page_id, p.title AS page_title, warring_editors, mutual_pairs,
       editors_in_any_revert, p.revert_actions AS revert_actions, p.edits AS edits
ORDER BY editors_in_any_revert DESC, page_id ASC;
