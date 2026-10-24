// load.cypher: build the Truth Lag revert graph (history cohort) from 4 CSV files.
//
// What it does: deletes everything in the database, creates 2 uniqueness
// constraints and 2 indexes, then loads Editor and Page nodes and the EDITED and
// REVERTED relationships from editors.csv, pages.csv, edited.csv and reverted.csv
// (made by ec-hw2/export_graph.py; columns in DATA_MODEL.md section 5).
// Spec item: section 4, "Load: CSV export from Mongo via LOAD CSV".
//
// LOAD CSV reads every value as text, so every number, boolean and time is cast
// (toInteger, toFloat, toBoolean, datetime). An empty field means "no value".
//
// Neo4j Desktop / Neo4j Browser:
//   1. Copy the 4 CSV files into the "import" folder of your database
//      (Desktop: the "..." menu of the database > Open folder > Import).
//   2. Run the statements below one at a time, in order.
//   3. Put ":auto " in front of every statement with "IN TRANSACTIONS"
//      (Step 1 and the 4 LOAD CSV statements), for example:
//        :auto LOAD CSV WITH HEADERS FROM 'file:///editors.csv' AS row CALL (row) { ... } IN TRANSACTIONS OF 10000 ROWS
//      Browser normally runs a query inside one transaction. ":auto" makes it an
//      implicit transaction, which "IN TRANSACTIONS" needs.
//   You should see: 37,546 Editor nodes, 165,415 Page nodes, 295,013 EDITED and
//   13,269 REVERTED relationships (data-v1).
// Python: ec-hw2/load_neo4j.py --target local runs this same file (no ":auto" needed,
// because session.run is already an implicit transaction).

// Step 1: delete everything in the database (the graph is always rebuilt from the CSV files)
MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;

// Step 2: uniqueness constraints (they also make the MATCH by key fast) and 2 indexes
CREATE CONSTRAINT editor_key IF NOT EXISTS FOR (e:Editor) REQUIRE e.key IS UNIQUE;
CREATE CONSTRAINT page_id IF NOT EXISTS FOR (p:Page) REQUIRE p.id IS UNIQUE;
// Cypher Q4 looks up REVERTED relationships by page_id
CREATE INDEX reverted_page_id IF NOT EXISTS FOR ()-[r:REVERTED]-() ON (r.page_id);
// Cypher Q5 starts from the contested pages
CREATE INDEX page_contested IF NOT EXISTS FOR (p:Page) ON (p.contested);

// Step 3: Editor nodes. alias is a pseudonym for humans; bots keep their name.
LOAD CSV WITH HEADERS FROM 'file:///editors.csv' AS row
CALL (row) {
  CREATE (:Editor {key: row.key, alias: row.alias, kind: row.kind,
                   edits: toInteger(row.edits),
                   reverts_made: toInteger(row.reverts_made),
                   reverts_received: toInteger(row.reverts_received)})
} IN TRANSACTIONS OF 10000 ROWS;

// Step 4: Page nodes. score is empty (no value) when the page has no human edit.
LOAD CSV WITH HEADERS FROM 'file:///pages.csv' AS row
CALL (row) {
  CREATE (:Page {id: toInteger(row.id), title: row.title,
                 edits: toInteger(row.edits),
                 revert_actions: toInteger(row.revert_actions),
                 reverted_editors: toInteger(row.reverted_editors),
                 score: toFloat(row.score),
                 contested: toBoolean(row.contested)})
} IN TRANSACTIONS OF 10000 ROWS;

// Step 5: EDITED, one per history revision. reverting_rev_id is empty when nobody reverted it.
LOAD CSV WITH HEADERS FROM 'file:///edited.csv' AS row
CALL (row) {
  MATCH (e:Editor {key: row.editor_key})
  MATCH (p:Page {id: toInteger(row.page_id)})
  CREATE (e)-[:EDITED {rev_id: toInteger(row.rev_id), ts: datetime(row.ts),
                       reverted: toBoolean(row.reverted),
                       reverted_by_other: toBoolean(row.reverted_by_other),
                       within_followup: toBoolean(row.within_followup),
                       reverting_rev_id: toInteger(row.reverting_rev_id)}]->(p)
} IN TRANSACTIONS OF 10000 ROWS;

// Step 6: REVERTED, one per (reverter, reverted editor, page): reverts by others within 20 days
LOAD CSV WITH HEADERS FROM 'file:///reverted.csv' AS row
CALL (row) {
  MATCH (a:Editor {key: row.reverter_key})
  MATCH (b:Editor {key: row.author_key})
  CREATE (a)-[:REVERTED {page_id: toInteger(row.page_id), count: toInteger(row.count),
                         n_revisions: toInteger(row.n_revisions),
                         ts: datetime(row.ts), last_ts: datetime(row.last_ts)}]->(b)
} IN TRANSACTIONS OF 10000 ROWS;
