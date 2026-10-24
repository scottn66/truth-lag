# Prompt given to the build agent "scaleout"

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

YOUR PART: Scale-out demo and the setup guides (the Comparison+viz role checks the scale-out; all roles use the guides).
Create: ec-hw2/scaleout/docker-compose.sharded.yml, ec-hw2/scaleout/init_sharded.sh, ec-hw2/scaleout/demo_sharding.py, ec-hw2/scaleout/SHARDING.md, ec-hw2/guides/ATLAS_SETUP.md, ec-hw2/guides/ATLAS_CHARTS.md, ec-hw2/guides/NEO4J_SCREENSHOTS.md, and results/sharding.md (the output of the demo).
- **Sharded cluster.** A separate compose project ("name: truthlag-sharded") with its own named volumes, all on mongo:8.0:
  - cfg: configsvr, replSet cfgrs, port 27019, --wiredTigerCacheSizeGB 0.25, mem_limit 600m
  - shard1 and shard2: shardsvr, replSets shard1rs / shard2rs, port 27018 inside, cache 0.25, mem_limit 600m
  - mongos: port 27017 inside, published as 127.0.0.1:27020, mem_limit 256m
- **init_sharded.sh** runs rs.initiate for each replica set (configsvr: true for cfg), waits for a primary, then runs sh.addShard twice. It must be safe to run twice.
- **demo_sharding.py:**
  1. Connect to config.SHARDED_URI. Drop and recreate the database truthlag_sharded.
  2. Run sh.shardCollection('truthlag_sharded.revisions', {'page.id': 'hashed'}) on the EMPTY collection.
  3. Copy the history-cohort documents from the local MongoDB (config.MONGO_URI, database config.MONGO_DB, collection revisions, cohort 'history') in batches.
  4. Record:
     - the data distribution ($shardedDataDistribution, or per-shard counts)
     - the document count per shard
     - explain() of find({'page.id': X}), which should show SINGLE_SHARD
     - explain() of an aggregation grouped by hour_utc or of find({'user.id': Y}), which should show SHARD_MERGE / both shards
  5. Write results/sharding.md in plain English, with the numbers and the explain stage names. Make the script safe to re-run.
- **Memory rule.** Before starting the sharded cluster, run 'docker stop truthlag-neo4j-1' (stop only; never remove). When the demo is done, run 'docker start truthlag-neo4j-1', then stop the sharded cluster ('docker compose -f ec-hw2/scaleout/docker-compose.sharded.yml stop'). Never touch the main project's volumes.
- **SHARDING.md** explains:
  - why {"page.id": "hashed"}:
    - many distinct pages
    - an even spread from hashing
    - page queries (page history, contested pages) hit one shard
    - no hot spot from ever-growing ts or rev_id
    - upserts include page.id
  - what does not work on the Atlas free tier: no sharding, getShardDistribution unsupported, sharding starts at the M30 tier
  - the trade-off: queries by hour or by user go to all shards
- **Guides.** Plain English, numbered steps, exact clicks, what you should see, the screenshots to take and the time needed:
  - **ATLAS_SETUP.md:**
    - Create one shared Atlas project + a free cluster (M0, MongoDB 8.0, AWS us-west-2 if offered).
    - Invite all 4 members as Project Owner.
    - Create database users: one read-only per person and one write user for loading.
    - Network Access: each person's IP, or a temporary 0.0.0.0/0 entry that expires after 2026-10-30. Say this is a class-project shortcut.
    - Put the connection string into ec-hw2/.env as ATLAS_URI, and never commit it.
    - Load with '.venv/bin/python ec-hw2/load_mongo.py --target atlas --confirm-overwrite', then check in Data Explorer.
    - Screenshots to take: the cluster page showing the free tier, one sample document, the Indexes tab, and Mongo Q1-Q4 run in Data Explorer > Aggregations by pasting the pipeline from ec-hw2/queries/mongo/q1...json.
  - **ATLAS_CHARTS.md:** build at least 2 charts in Atlas Charts:
    1. Q1: revert rate by hour of day x user kind (chart_q1_hour_kind), as a heat map or grouped bar
    2. Q3: time-to-revert buckets (chart_q3_time_to_revert), as columns
    3. optional: the Q5 known-by curve (chart_q5_known_by) and the risk deciles (chart_q5_risk_deciles)
    - For each chart give: the data source, the chart type, which field goes to which axis or channel, the sort and the title.
    - Then: right-click > Save as PNG into ec-hw2/results/figures/, and upload it with the GitHub web page.
    - Notes: the free tier refreshes dashboards every 4 hours, so open the chart builder for fresh data; only a Project Owner can add a data source.
    - Take the field names from the real chart collections in the local MongoDB (list them).
  - **NEO4J_SCREENSHOTS.md:**
    - Open http://localhost:7474 (screen-share on Scott's Mac, or Neo4j Desktop / Aura on your own laptop) and log in.
    - Style: Editor caption = alias, Page caption = title.
    - Graph screenshots: paste queries that RETURN paths with LIMIT 50-100 (mutual-revert pairs; one contested page with its editors; the largest Louvain community, using communityId), plus CALL db.schema.visualization().
    - For each of the 5 Cypher queries in ec-hw2/queries/cypher/: a screenshot of the table result.
    - Use only pseudonyms (alias).
    - Bloom is not available on Community Docker, so write "Neo4j Browser (Bloom needs Neo4j Desktop or Aura)".
- At the end, run the sharding demo for real and put its numbers in results/sharding.md.
```
