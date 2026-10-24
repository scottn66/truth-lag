# Prompt given to the build agent "comparison"

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

YOUR PART: SQL and the three-engine comparison (checked later by the Comparison+viz role).
Create: ec-hw2/load_sql.py, ec-hw2/queries/sql/compare_top_contested.sql, ec-hw2/queries/sql/compare_mutual_reverts.sql, ec-hw2/queries/run_sql.py, ec-hw2/comparison/compare.py, ec-hw2/tests/test_sql.py, results/comparison.md and results/comparison.csv.
- load_sql.py loads the history cohort from data/tables/history_revisions.parquet and history_revert_links.parquet into config.SQLITE_PATH (data/tables/truthlag.sqlite).
  - Tables: revisions (flat columns; lists as comma text; times as ISO text) and revert_links.
  - Indexes on page_id, reverted_rev_id, author_key and reverter_key.
  - Write to a .tmp file, then replace.
- The SQL queries follow the shared definitions in DATA_MODEL.md section 7 exactly: float division (1.0 * a / b), the same order and limit, and mutual pairs (a < b) per page with both counts.
- compare.py covers the two questions (top contested pages; mutual reverts) on three engines. It loads the query text ONLY from these files:
  - MongoDB: queries/mongo/q2_top_contested_pages.json and compare_mutual_reverts.json
  - Cypher: queries/cypher/compare_top_contested.cypher and q1_mutual_reverts.cypher
  - SQL: queries/sql/*.sql
- For each run, compare.py does this:
  1. Checks that the outputs are identical (the full ordered list, scores rounded to 6) and records any difference.
  2. Measures the median of 7 warm runs after 1 warm-up, and records the machine (macOS version, CPU, RAM, database versions). Note that MongoDB and Neo4j run in a Colima VM with 4 CPU / 6 GB, while SQLite runs on the host.
  3. Counts lines of query code (non-blank, non-comment lines of the query text).
  4. Writes results/comparison.csv and results/comparison.md with a table: question | engine | lines of code | median ms | same result? | modeling note (one plain sentence each, from what you saw). Examples of notes: Mongo needs a self-$lookup for mutual pairs; the Cypher pattern is one line; SQL needs a self-join; Cypher needs page_id on REVERTED edges.
  5. Adds a "modeling pain" score 1-5 per engine per question, with a one-line reason.
  6. Adds a section "Candidate findings for 'Comparison top 5'": 6-8 bullet facts (numbers only, no conclusions). The Comparison+viz owner will turn them into their own words.
- Timings are noisy while other jobs run. Run compare.py once now to check equality, write the files and label the timing "draft". Support a --final flag that sets the label to "final"; that run happens later on an idle machine.
- Tests (test_sql.py) run on tiny fixtures in an in-memory SQLite: score ties, float division and mutual pairing.
- At the end, run load_sql.py, run_sql.py and compare.py for real.
```
