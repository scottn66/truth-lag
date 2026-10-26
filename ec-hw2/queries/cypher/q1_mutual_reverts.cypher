// Cypher Q1 (spec 4.1): mutual-revert pairs on the same page (edit wars)
// Question: which pairs of editors reverted EACH OTHER on the same page?
// A pair {a, b} on page p is mutual when a reverted b on p AND b reverted a on p
// (reverts by another editor within 20 days, history cohort; DATA_MODEL.md section 7).
// Each unordered pair is listed once (a.key < b.key). This is also the "mutual
// reverts" comparison query (spec 5): Mongo and SQL give the same ordered list.
// Output columns (result main): page_id, page_title, editor_a, editor_b,
//   a_reverted_b, b_reverted_a (distinct revert actions in each direction).
// Output columns (result total): mutual_pairs, pages, editors, pairs_with_bot.
// Editors are shown by alias (a pseudonym for humans; bots keep their name).
// Neo4j Browser: first run  :params {top_n: 20, contested_min_edits: 10, contested_min_editors: 2, contested_min_actions: 2, contested_min_score: 0.2}

// result: main
MATCH (a:Editor)-[r1:REVERTED]->(b:Editor)-[r2:REVERTED]->(a)
WHERE r1.page_id = r2.page_id AND a.key < b.key
MATCH (p:Page {id: r1.page_id})
RETURN p.id AS page_id, p.title AS page_title, a.alias AS editor_a, b.alias AS editor_b,
       r1.count AS a_reverted_b, r2.count AS b_reverted_a
ORDER BY page_id, a.key, b.key;

// result: total
// The size of the edit-war table: pairs, pages, distinct editors, and pairs with a bot.
MATCH (a:Editor)-[r1:REVERTED]->(b:Editor)-[r2:REVERTED]->(a)
WHERE r1.page_id = r2.page_id AND a.key < b.key
WITH count(*) AS mutual_pairs, count(DISTINCT r1.page_id) AS pages,
     count(CASE WHEN a.kind = 'bot' OR b.kind = 'bot' THEN 1 END) AS pairs_with_bot,
     collect(a) + collect(b) AS people
UNWIND people AS e
RETURN mutual_pairs, pages, count(DISTINCT e) AS editors, pairs_with_bot;
