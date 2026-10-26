# Prompt given to the build agent "docs"

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

YOUR PART: The team docs skeleton (checked later by the Report+GenAI role). Start now. Other parts are being built at the same time, so write what you can and mark the missing parts clearly as 'TODO(after build): ...' where numbers or file lists are not ready.
Create: ec-hw2/README.md, ec-hw2/GLOSSARY.md, ec-hw2/PROGRESS.md, ec-hw2/check_setup.py, ec-hw2/ingest/README.md, and ec-hw2/tests/test_check_setup.py (light).
- **Readers:** 4 teammates, semi-technical. English may be a second language; two use Chinese, Traditional and Simplified, on their phones. Follow ec-hw2/STYLE.md strictly.
- **Roles:** Data+MongoDB, Neo4j, Comparison+viz, Report+GenAI. Owners are TBD: never write a person's name as an owner.
- **README.md** (the start page):
  1. **Top box:** "EC HW2 - NoSQL mini project. Due Thu 2026-10-29 4:29 PM PT. Internal deadline Thu 12:00 PT." Then 2-3 plain sentences on what we do: which English Wikipedia edits get reverted, how fast, and who reverts whom; MongoDB holds documents, Neo4j holds a graph, and we compare both with SQL.
  2. **"Where the data comes from":** a Mermaid flowchart. The VPS capture (systemd, 3 streams) -> rsync -> Mac data/raw -> parse -> Parquet tables -> MongoDB -> CSV -> Neo4j and SQLite. The History dump 2026-09 -> filtered on the VPS -> rsync -> Mac data/history. Say that Kafka and Spark are for the final project.
  3. **"Two cohorts" table:**
     - history cohort: 2026-09-08 to 2026-09-10 UTC, from the dump, labels after 20 days
     - live cohort: 2026-10-20 to 2026-10-22 UTC, from EventStreams, labels after 4 days; final after Mon 2026-10-26 5 PM PT
     - why two cohorts: the October dump only comes out in November
  4. **"Your role" table** with one row per role:
     - What to verify: Data+MongoDB = notebooks 01 and 02 + Atlas; Neo4j = notebook 03; Comparison+viz = notebooks 04 and 05 + sharding + Charts; Report+GenAI = README, glossary, report skeleton, criteria map.
     - The UI artifact to make and upload yourself: Data+MongoDB = Atlas screenshots + Q1-Q4 in Data Explorer; Neo4j = Neo4j Browser screenshots; Comparison+viz = 2 or more Atlas Charts as PNG; Report+GenAI = the final PDF.
     - The section to write in your own words: Data+MongoDB = the Mongo section + "Answer to Q1"; Neo4j = the Neo4j section + "Answer to Q2"; Comparison+viz = Comparison top 5 + Impact; Report+GenAI = Abstract, Motivation + related work, Technical difficulties, Key learnings.
     - The literature batch, plus your own GenAI row and 2-3 dated observations in PROGRESS.md.
     - "You only need these files": 3-6 files per role. Use these planned paths: notebooks/01_data.ipynb, 02_mongodb.ipynb, 03_neo4j.ipynb, 04_comparison.ipynb, 05_truth_lag.ipynb; queries/mongo/*.json; queries/cypher/*.cypher; queries/sql/*.sql; guides/*.md; report/REPORT_SKELETON.md; report/FACTS.md; report/references.md.
  5. **"Three ways to check your part":**
     1. Read only, on GitHub: open the notebook on branch ec-hw2; the outputs are saved.
     2. With a free app and no Python: paste a query JSON into Atlas Data Explorer > Aggregations; run load.cypher and the queries in Neo4j Desktop (install the APOC + Graph Data Science plugins from the Plugins tab; on a Mac add server.jvm.additional=-Djol.skipHotspotSAAttach=true); open data/tables/truthlag.sqlite from the data release in DB Browser for SQLite and run queries/sql/*.sql.
     3. With Python: Mac and Windows commands side by side. Create a venv, install ec-hw2/requirements.txt, copy .env.example to .env, download the data release files into data/ exactly, run 'python ec-hw2/check_setup.py', then 'jupyter lab' and open the notebooks.
  6. **"GitHub without Git (6 steps)":**
     1. Accept the invite at https://github.com/scottn66/truth-lag/invitations.
     2. Switch the branch menu to ec-hw2.
     3. Open a notebook to read the results.
     4. Comment in the pull request "Conversation" tab, or send the comment in the group chat.
     5. Review: "Files changed" > "Review changes" > "Approve", and list the numbers you checked.
     6. Upload your screenshots and PNGs with "Add file > Upload files" into ec-hw2/results/figures/ on branch ec-hw2.
     - Rules: never commit .env or data files; commit only the notebook you own.
  7. **"How to run everything (Scott's Mac)",** numbered:
     1. colima start
     2. docker compose up
     3. rsync: 'rsync -az --partial vps-coin:/opt/truthlag/data/raw/ data/raw/' and the history one; never --delete
     4. the pipeline commands in order. Write 'TODO(after build)' for the exact script names beyond: ingest/parse_history.py, ingest/parse_stream.py, ingest/label_live.py, ingest/late_reverts.py, load_mongo.py, speed_layer.py, export_graph.py, load_neo4j.py, load_sql.py, queries/run_all.py, comparison/compare.py, refresh_live.sh.
  8. **"Safety rules":** a short copy of the STYLE.md safety rules.
  9. **"Status":** link to PROGRESS.md.
- **GLOSSARY.md:**
  - A table: Term | Plain meaning (1-2 short sentences) | Example from our data | 中文 (繁體) | 中文 (简体).
  - A note at the top: "The Chinese columns were drafted by Claude (AI). Please correct them. That fix is a real contribution: log it in PROGRESS.md."
  - About 50 terms: revision, edit, page, namespace 0 (article), revert, identity revert, exact revert, rollback, undo, manual revert, reverted (label), time to revert, self-revert, reverter, edit war, mutual revert, contested page, temporary account (logged-out editor), registered user, bot, cohort, history cohort, live cohort, snapshot (dump), MediaWiki History dump, EventStreams, replay, follow-up window, truth lag, stream delay (K), known-by time, revert-risk score, late revert, lower bound, censoring, UTC and PT, half-open window [start, end), Parquet, ndjson.gz, rsync, VPS, systemd unit, document (MongoDB), collection, aggregation pipeline, $lookup, $bucket, $facet, index, view, Atlas free tier (M0), sharding, shard key, hashed shard key, replica set, mongos, node, relationship, Cypher, PageRank, Louvain, WCC (connected components), degree, GDS, LOAD CSV, SQLite.
  - Then a "Proposal word -> HW2 word" table:
    - Cohort A -> history or live cohort
    - H = 30 days -> follow-up window (20 d history, 4 d live)
    - bronze/silver/gold -> the parsed/ and tables/ folders
    - speed layer -> the page_hour live counters
    - Kafka/Redpanda -> final project only (not HW2)
    - E0-E7 experiments -> final project
    - V1/V2 tiers -> live label / dump label
- **PROGRESS.md:**
  1. **"Never cut"** list: Mongo Q1-Q5, Cypher Q1-Q5, the 3-engine comparison, 2 or more Charts, screenshots, the criteria map, GenAI Q&A, grader access. **"Cut first"** order: --follow, late-revert detail, risk deciles, sharding demo (keep the explanation), GDS (Cypher fallback), shrink the live cohort.
  2. **A schedule table in PT:**
     - Sat 12:00: roles claimed
     - Sat: Atlas project + history load
     - Sun: verify the FINAL numbers + screenshots + literature notes
     - Mon 20:00: Neo4j screenshots
     - Mon after 5 PM PT: live refresh
     - Tue 20:00: charts + sections
     - Wed 18:00: integrated Google Doc
     - Wed: merge + tag + repo access
     - Thu 12:00: internal submit
     - Thu 4:29 PM PT: Canvas deadline
  3. **A checklist per role:** Role | Task | Status [ ] | Done by (name) | Date | Link.
  4. **A "Who did what" table:** File or section | Built by | Verified by (name, date) | Created in UI by | Written by | AI tools used (including translators) or none.
  5. **"Personal observations":** a sub-heading per role, for 2-3 dated notes.
  6. **"Daily log":** the first entry, dated 2026-10-24:
     - What changed: the capture runs on the VPS since 2026-10-24 about 04:50 UTC, with replay from Oct 19 (page_change + revert risk) and Oct 17 (tags); the history cohort is filtered (300,564 rows); the databases are set up.
     - What is next.
     - What we need from you: accept the GitHub invite; claim a role by Sat 12:00 PT; answer "Windows or Mac? Python installed? Free hours Sat-Tue?"
  7. **"After any restart (Scott's Mac)":** colima start; docker compose ... up -d; check the VPS read-only with 'ssh vps-coin systemctl is-active truthlag-capture-a truthlag-capture-b'.
- **check_setup.py** prints one line per check, "OK", "FAIL" or "SKIP", with a plain-English hint.
  - Checks:
    - the Python version (3.12 recommended, >= 3.11 OK)
    - the required packages can be imported: pandas, pyarrow, pymongo, neo4j, dotenv, matplotlib, tabulate
    - ec-hw2/.env exists (never print the values)
    - the data files are present: data/tables/history_revisions.parquet, live_revisions.parquet, history_revert_links.parquet, live_revert_links.parquet, late_reverts.parquet, truthlag.sqlite, and data/neo4j/import/*.csv; plus data/tables/DATA_VERSION if present
    - the local MongoDB is reachable (serverSelectionTimeoutMS 2000)
    - Atlas is reachable if ATLAS_URI is set
    - Neo4j is reachable if NEO4J_PASSWORD is set (3-second connection timeout)
  - It never crashes: it catches everything and prints FAIL with the reason (no secrets). The exit code is always 0.
  - It works on Windows and Mac (pathlib, no shell).
  - It tells people to paste the output into the group chat when they need help.
- **ingest/README.md** explains the ingest folder:
  - The VPS capture is the copy in the repo-root ingest/vps/ (capture.py, filter_history.py, the unit files, the README). The live copy runs on the VPS: never edit it from here.
  - The repo-root ingest/collect_eventstreams.py is the older Mac collector and is not used for HW2.
  - The parse scripts (names above), and what each one reads and writes (from DATA_MODEL.md).
```
