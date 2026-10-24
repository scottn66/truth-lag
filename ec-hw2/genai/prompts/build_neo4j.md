# Prompt given to the build agent "neo4j"

Tool: Claude Code Workflow (model claude-opus-5-5), run 2026-10-24. Source: ec-hw2/genai/workflows/build.js (this text is generated from it, word for word).

```text
You are building one part of the Truth Lag EC HW2 project (SJSU DATA 226, Group 9: a NoSQL mini project that answers "which English Wikipedia edits get reverted, how fast, and who reverts whom" in MongoDB and Neo4j, compared with SQL). Today is 2026-10-24 (UTC). The repo is /Users/scottnelson/Desktop/226/truth-lag on git branch ec-hw2. Work ONLY inside this repo.

Read first (all short): ec-hw2/SPEC.md (the assignment), ec-hw2/config.py (every path, window and rule: import it, never re-type a rule), ec-hw2/DATA_MODEL.md (every table and collection with its columns: follow it exactly), ec-hw2/STYLE.md (writing and code rules), ec-hw2/ingest/history_columns.py (types for the dump columns). The approved plan is /Users/scottnelson/.claude/plans/https-github-com-scottn66-truth-lag-this-mutable-whistle.md (read the parts about your work).

Environment: Python 3.12 venv at .venv. Run '.venv/bin/python ...' from the repo root. Installed: pandas 2.3, pyarrow, pymongo, neo4j (driver 6), matplotlib, tabulate, pytest, jupyter, nbconvert, ipykernel, python-dotenv. MongoDB 8.0 (mongodb://localhost:27017) and Neo4j 2026.10.1 with GDS + APOC (bolt://localhost:7687, Browser http://localhost:7474) run in Docker via Colima (containers truthlag-mongo-1 and truthlag-neo4j-1). Credentials are in ec-hw2/.env and config.py loads them: never print them. Data is in data/ (git-ignored): data/history (VPS-filtered dump as Parquet, ALL columns are strings), data/raw (copy of the live capture). The live capture runs on a VPS; the copy in data/raw was synced at the start of this build.

Hard rules:
- Touch only the files listed for your part. If you need a change in a shared file (config.py, DATA_MODEL.md, STYLE.md, ec-hw2/requirements.txt, ec-hw2/docker-compose.yml, ingest/history_columns.py), do NOT edit it: describe the change in shared_change_requests and work around it locally if you can.
- No git commands that change anything (no add, commit, checkout, stash, reset). No package installs (no pip or uv install). Never run "docker compose down -v" and never remove containers or volumes.
- Never ssh to the VPS, never run rsync, never open Wikimedia EventStreams connections, and never call Wikimedia web APIs. (Only the literature part may use the web, for papers.)
- Never use the "timeout" command (it is not on macOS). Run long jobs in the background with output to a log under data/logs/ and check the log.
- Never delete or rewrite anything under data/raw or data/history.
- Write output files safely: write <name>.tmp, then os.replace to the final name, then write a _SUCCESS_<step>.json next to it with row counts.
- Every script starts with a docstring: purpose, inputs, outputs, and the exact run command. Use plain short English in comments and docs. All times are timezone-aware UTC. A script in a sub-folder of ec-hw2 imports config with sys.path.insert(0, str(Path(__file__).resolve().parents[N])) (N = depth to ec-hw2) and then "import config".
- Put your tests in ec-hw2/tests/test_<part>.py with tiny synthetic fixtures that use the same column names and types as the real files. Run them with '.venv/bin/python -m pytest ec-hw2/tests/test_<part>.py -q'. Create ec-hw2/tests/__init__.py only if it does not exist.
- Human editors must appear only as pseudonyms in any committed result, figure or sample (bots keep their real names). Page titles are fine.
- At the end, run your code on the real data, check that the numbers make sense, and report honestly: what works, what does not, and every number you saw. Do not claim something works unless you ran it.

Return the structured result: part, files you created, commands that ran OK, key numbers (name/value), issues (anything wrong, surprising or unfinished), shared_change_requests, and notes_for_docs (facts the teammates should know, in plain English).

YOUR PART: Neo4j (checked later by the Neo4j role).
Input: the local MongoDB database (collections revisions and revert_links, history cohort only), built by the MongoDB part. Check that they exist.
Create:
- ec-hw2/export_graph.py and ec-hw2/load_neo4j.py
- ec-hw2/queries/cypher/load.cypher: a plain Cypher load for Neo4j Desktop users, with constraints and LOAD CSV using CALL (row) {...} IN TRANSACTIONS OF 10000 ROWS, plus a note to prefix ':auto' in Browser
- ec-hw2/queries/cypher/q1_mutual_reverts.cypher, q2_central_reverters.cypher, q3_conflict_communities.cypher, q4_pages_most_warring_editors.cypher, q5_two_hop_contested.cypher and compare_top_contested.cypher
- ec-hw2/queries/run_cypher.py and ec-hw2/tests/test_neo4j.py
- the outputs results/cypher_*.csv and results/cypher_*.md, and results/figures/neo4j_edit_war_example.png
Details:
- export_graph.py reads FROM MONGODB (this is the spec's "CSV export from Mongo") with aggregation pipelines. It writes data/neo4j/import/editors.csv, pages.csv, edited.csv and reverted.csv exactly as in DATA_MODEL.md section 5.
  - alias = 'editor_' + the first hex digits of sha1(key), long enough to be unique. Bots keep their real name as the alias.
  - The Page contested flag and counts use the shared definition in DATA_MODEL section 7, so the numbers match Mongo Q2.
  - Put reverting_rev_id, reverted_by_other and within_followup on EDITED rows, so Cypher can count DISTINCT reverting revisions for the comparison query.
  - REVERTED edges come from history links with within_followup and by_other: one edge per (reverter_key, author_key, page_id), with count = distinct reverting_rev_id, n_revisions, ts = first reverting ts, and last_ts. Skip null keys.
- load_neo4j.py: --target local|aura.
  - aura: use UNWIND $rows batches of 5,000 through the driver, because Aura cannot read local files. --subset contested keeps only the contested pages, their editors and the REVERTED edges among them. Make it ready, but do not run aura now.
  - local: wipe the content first (MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS). Create uniqueness constraints: CREATE CONSTRAINT editor_key IF NOT EXISTS FOR (e:Editor) REQUIRE e.key IS UNIQUE, and one for Page.id. Then load with LOAD CSV WITH HEADERS FROM 'file:///editors.csv' AS row CALL (row) { ... } IN TRANSACTIONS OF 10000 ROWS, run through session.run (implicit transactions).
  - Cast every value (toInteger, toFloat, datetime, toBoolean), because LOAD CSV reads strings and GDS needs numbers.
  - Use only current syntax: CALL (row) { }, never CALL { WITH row }; CREATE CONSTRAINT ... FOR ... REQUIRE, never ON ... ASSERT; no gds.graph.project.cypher; no apoc.load.csv.
  - The Neo4j import folder is data/neo4j/import, mounted read-only into the container at /import.
  - Print node and relationship counts.
- Each Cypher file starts with a comment block: what it answers in plain English, which spec item, and the output columns. Outputs show the alias, never the key or the name of a human.
  - Q1 (spec 4.1) mutual-revert pairs on the same page: MATCH (a:Editor)-[r1:REVERTED]->(b:Editor)-[r2:REVERTED]->(a) WHERE r1.page_id = r2.page_id AND a.key < b.key. Return the page title, both aliases and both counts, ordered by page_id, a.key, b.key. Also give the total number of pairs.
  - Q2 (spec 4.2) most central reverters: out-degree (reverts made = the sum of count) and GDS PageRank on a projection with REVERSE orientation, weight = count, so the score flows to editors who revert many editors. Top 20. Explain in the comment why REVERSE. Drop the projection afterwards.
  - Q3 (spec 4.3) communities of conflict: project Editor + REVERTED as UNDIRECTED with properties count, aggregation SUM. Run gds.louvain.write (writeProperty communityId, relationshipWeightProperty count). Add a summary: the top 10 communities by size, with distinct pages and total reverts. Run gds.wcc.stream for the component size distribution and the largest components. Concurrency <= 4.
  - Q4 (spec 4.4) pages with the most distinct warring editors: the distinct editors in mutual-revert pairs per page. If mutual pairs are rare, also give a second column with the editors in any REVERTED edge on the page, and define both clearly. Top 20 by distinct editors, ordered by editors desc, page_id asc.
  - Q5 (spec 4.5) 2-hop: editors linked through shared contested pages: MATCH (a:Editor)-[:EDITED]->(p:Page {contested: true})<-[:EDITED]-(b:Editor) WHERE a.key < b.key, excluding bots. Count distinct shared contested pages; top 20.
  - compare_top_contested.cypher (spec 5): compute the shared definition from the edges, not from the precomputed Page counts.
    - edits_p = EDITED edges from non-bot editors.
    - revert_actions_p = count(DISTINCT e.reverting_rev_id) where within_followup and reverted_by_other.
    - reverted_editors_p = count(DISTINCT editor) with such edges.
    - Use the same filter, order and limit as DATA_MODEL section 7, with toFloat for the score.
    - It must give the same 20 page_ids and scores (rounded to 6) as results/mongo_q2_top_contested_pages.csv. Check this and print the comparison.
- run_cypher.py runs each query file. It splits statements on ';' at line end and skips comment-only statements. Read queries get the median of 7 warm runs. It writes results/cypher_<name>.csv and .md (tabulate) and prints a summary.
- The picture results/figures/neo4j_edit_war_example.png is a small, clear drawing of one mutual-revert cluster, using only matplotlib (simple circle layout), pseudonyms only, with a title that states what it shows. It is a backup in case Browser screenshots fail.
- Tests (test_neo4j.py) test the CSV export logic in pure Python. Do NOT wipe the main graph in tests.
- At the end, export, load local, and run run_cypher.py for real.
```
