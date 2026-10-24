# DATA 226 EC HW2 — NoSQL Mini Project Spec (Truth Lag MVP)
Due Thu Oct 29 2026 4:29pm PT · one group submission (Group 9) · Canvas 7835916

## 1. Problem
**Q1 (document): Which Wikipedia edits get reverted, how fast, and where?**
**Q2 (graph): Who reverts whom — what editor/page structures predict edit wars?**
Same problem, two databases. This is the storage + query MVP for the Truth Lag final project (disclosed in report).

## 2. Data (link, don't upload)
- Wikimedia EventStreams `recentchange` / `revision-create` — live sample, ~3–7 days, enwiki ns0.
- MediaWiki History dump (same window) — revert labels (`revision_is_identity_reverted`, `revision_seconds_to_identity_revert`, reverting user).
- Join key: `(wiki_db, rev_id)`. Target ~100k–500k revisions.

## 3. MongoDB (document)
Collection `revisions`, one doc per revision:
`{_id: "enwiki:rev_id", wiki_db, rev_id, page:{id,title,ns}, user:{id,name,is_bot,is_anon}, ts, size_delta, comment, tags[], live:{seen_ts,…}, history:{reverted, secs_to_revert, reverter}}`
Indexes: `page.id+ts`, `user.id`, `history.reverted`.
Required ≥5 aggregation pipelines:
1. Revert rate by hour-of-day × anon/registered
2. Top 20 contested pages (reverts / edits)
3. Distribution of time-to-revert ($bucket)
4. Bot vs human share of reverts
5. **Truth Lag preview:** live-stream signals ($lookup/$group) vs eventual revert label
Scale-out: Atlas free tier (M0) + documented sharding key choice (`page.id` hashed) — demo or explain if M0 limits.
Viz: ≥2 MongoDB Atlas Charts.

## 4. Neo4j (graph)
Model: `(:Editor)-[:EDITED {ts,rev_id}]->(:Page)`, `(:Editor)-[:REVERTED {ts,count}]->(:Editor)`, `(:Page)-[:IN_CATEGORY]->(:Category)` (optional).
Load: CSV export from Mongo via `LOAD CSV` / APOC.
Required ≥5 Cypher queries:
1. Mutual-revert pairs (edit wars): `(a)-[:REVERTED]->(b)-[:REVERTED]->(a)`
2. Most central reverters (degree / PageRank via GDS if available)
3. Communities of conflict (Louvain/WCC)
4. Pages with the most distinct warring editors
5. 2-hop: editors connected via shared contested pages
Viz: Neo4j Browser/Bloom screenshots.

## 5. Comparison (top 5 own experiences)
Same question ("top contested pages" + "mutual reverts") in Mongo, Cypher, and SQL (Postgres/SQLite). Record LOC, query time, and modeling pain. Pick the 5 most insightful findings.

## 6. Engineering
- Python (PyMongo, neo4j driver) scripts: `ingest/`, `load_mongo.py`, `export_graph.py`, `load_neo4j.py`, `queries/`.
- `docker-compose.yml` (mongo + neo4j) — low-stakes bonus.
- LLM used to draft Cypher/aggregations — documented with prompts (bonus + GenAI disclosure).
- Lives in `scottn66/truth-lag` under `ec-hw2/`.

## 7. Report (no fixed format) must contain
Abstract · Motivation · Data + links · Architecture/workflow diagram · Mongo section · Neo4j section · Results/insights · Comparison top 5 · Technical difficulties · Best practices + key learnings · **Criteria map table** (each rubric bullet → evidence) · Reuse note (MVP for course project) · **Mandatory GenAI Q&A** (yes/no; model, prompt, question #, help given).

## 8. Grading criteria → where met
| Criterion | Evidence |
|---|---|
| Meaningful goal | §1 revert / Truth Lag framing |
| Workflow | §6 pipeline + diagram |
| Innovation | live-vs-history revert prediction; revert graph |
| Technical difficulty | stream+dump join, two DBs, GDS |
| Queries/aggregations | §3 (5) + §4 (5) |
| Scale-out | Atlas + shard key |
| Programming | Python + Cypher |
| Visualization | Atlas Charts + Bloom |
| Comparison | §5 |
| Bonus | docker-compose, LLM, public blog/video (optional) |

## 9. Plan / owners (4 people)
Fri–Sat data pull · Sun Mongo · Mon Neo4j · Tue comparison + charts + Atlas · Wed report + GenAI log · Thu AM review & submit.
Owners: Data+Mongo / Neo4j / Comparison+viz / Report+GenAI (assign).

## 10. Done =
Both DBs loaded from linked public data; 10 queries with outputs + screenshots; 2+ charts; comparison table; report with criteria map + GenAI answers; code in repo; one Canvas submission before 4:29pm Oct 29.
