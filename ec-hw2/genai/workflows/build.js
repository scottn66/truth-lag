export const meta = {
  name: 'truthlag-hw2-build',
  description: 'Build the Truth Lag EC HW2 MVP: ETL, MongoDB, Neo4j, SQL comparison, scale-out, literature, docs and notebooks',
  phases: [
    { title: 'Build data', detail: 'history ETL and stream ETL in parallel' },
    { title: 'Databases', detail: 'MongoDB, then Neo4j, then SQL comparison, then the sharding demo' },
    { title: 'Docs', detail: 'literature and docs skeleton early; notebooks + report skeleton last' },
  ],
}

// This file is the word-for-word record of the prompts Claude Code (claude-opus-5-5) gave to its
// build agents for EC HW2 (GenAI disclosure). Run by Claude Code's Workflow tool on 2026-10-24.

const RESULT = {
  type: 'object',
  properties: {
    part: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    commands_ok: { type: 'array', items: { type: 'string' } },
    key_numbers: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, value: { type: 'string' } }, required: ['name', 'value'] } },
    issues: { type: 'array', items: { type: 'string' } },
    shared_change_requests: { type: 'array', items: { type: 'string' } },
    notes_for_docs: { type: 'array', items: { type: 'string' } },
  },
  required: ['part', 'files', 'commands_ok', 'key_numbers', 'issues', 'shared_change_requests', 'notes_for_docs'],
}

const COMMON = `You are building one part of the Truth Lag EC HW2 project (SJSU DATA 226, Group 9: a NoSQL mini project that answers "which English Wikipedia edits get reverted, how fast, and who reverts whom" in MongoDB and Neo4j, compared with SQL). Today is 2026-10-24 (UTC). The repo is /Users/scottnelson/Desktop/226/truth-lag on git branch ec-hw2. Work ONLY inside this repo.

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

Return the structured result: part, files you created, commands that ran OK, key numbers (name/value), issues (anything wrong, surprising or unfinished), shared_change_requests, and notes_for_docs (facts the teammates should know, in plain English).`

const P = {}

P.history = `YOUR PART: History ETL (checked later by the Data+MongoDB role).
Create ec-hw2/ingest/parse_history.py and ec-hw2/tests/test_history.py.
Inputs: config.HISTORY_DIR / config.HISTORY_COHORT_FILE (the cohort, all 78 columns) and config.HISTORY_DIR / config.HISTORY_SLIM_FILE (all September 2026 revisions, 12 columns). All columns are strings: cast with ingest.history_columns.cast_history_frame.
Outputs (DATA_MODEL.md section 3): data/tables/history_revisions.parquet, data/tables/history_revert_links.parquet, data/tables/history_summary.json, data/tables/_SUCCESS_history.json.
Steps:
1. Read and cast the cohort. Keep event_entity == revision, event_type == create, ts in config.HISTORY_WINDOW, and page_namespace_historical == 0 (the VPS filter already kept current namespace 0). Drop null revisions (same content as the parent revision): (a) if the parent revision is in the cohort file, compare revision_text_sha1 directly; (b) otherwise call it null when revision_text_bytes_diff == 0 AND the comment starts (case-insensitive) with one of: 'moved page', 'protected', 'changed protection', 'unprotected', 'changed content model', 'imported'. Print how many rows each rule drops.
2. User fields: user_kind = config.user_kind(event_user_text_historical, event_user_is_bot_by, event_user_is_temporary); user_key = config.editor_key(user_kind, event_user_id, event_user_text_historical); is_bot, is_temp and is_anon come from user_kind (is_anon = temporary).
3. Labels: reverted_any = revision_is_identity_reverted; reverted = reverted_any AND revision_seconds_to_identity_revert <= config.HISTORY_FOLLOWUP_S; reverting_rev_id = revision_first_identity_reverting_revision_id; secs_to_revert = revision_seconds_to_identity_revert.
4. Reverter self-join: join reverting_rev_id to revision_id in the slim file (cast it; keep only the columns you need, to save memory). reverter_name = event_user_text_historical of that row; reverter_kind = config.user_kind(reverter_name, event_user_is_bot_by) (the slim file has no temp flag; user_kind uses the '~2' name prefix); reverter_key = config.editor_key(...). reverted_by_other = both keys not null and different. Report how many reverting ids were not found in the slim file (expect about 0).
5. page_edits_prev_1h: for each cohort revision, count the revisions in the slim file on the same page_id with event_timestamp in [ts - 1 hour, ts), not counting the revision itself. Do this with a vectorised method (sort by page_id and time, then numpy searchsorted per page group, or merge_asof). Do NOT loop over 300k rows in Python filtering 5M rows each time.
6. All other columns exactly as DATA_MODEL.md section 3: tags = split_list(revision_tags) without 'mw-reverted'; mw_reverted_tag; sha1 = sha1_base36_to_hex(revision_text_sha1); size, size_delta, hour_utc, followup_s = (config.HISTORY_DUMP_LAST_REVISION - ts) in whole seconds; cohort = 'history'; seen_ts = null; revert_risk = null; is_revert = revision_is_identity_revert; revert_method = null; mw_reverted_at = null; page_title = page_title_historical (fall back to page_title when null); page_ns = page_namespace_historical; wiki_db; parent_id; comment; edit_count = event_user_revision_count.
7. history_revert_links.parquet: one row per cohort revision with reverted_any true. Columns per DATA_MODEL.md: cohort 'history', source 'dump', reverted_rev_id, page_id, reverted_ts, author_key, author_kind, reverting_rev_id, reverting_ts = ts + secs_to_revert, reverter_key, reverter_name, reverter_kind, T_s = secs_to_revert, known_at = null, K_s = null, method = null, is_exact = true, by_other = reverted_by_other, within_followup = reverted, range_size = null, confirmed_by_tag = mw_reverted_tag.
8. Print and save in history_summary.json: rows in and out with each drop reason; revert rates (all, non-bot, by user_kind); median and p90 of T for reverted; share reverted within 1 h and within 1 d; the self-revert share by kind; agreement between reverted_any and mw_reverted_tag (2x2 counts, plus the same split by T bucket: <1 h, 1 h-1 d, 1-7 d, 7-20 d, >20 d); the top 5 pages by number of reverted revisions (titles).
Tests: tiny fixtures for casting, the null-revision rule, the user_kind order, the reverter join, the 20-day label and the prev_1h count.
Expected: about 296k rows after the filters; non-bot revert rate roughly 5-9 percent; median T a few hours. If you see something very different, investigate and explain it in issues.`

P.stream = `YOUR PART: Stream ETL (checked later by the Data+MongoDB role).
Create ec-hw2/ingest/parse_stream.py, ec-hw2/ingest/label_live.py, ec-hw2/ingest/late_reverts.py and ec-hw2/tests/test_stream.py.
Inputs: data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-*.ndjson.gz for the 3 streams in config.STREAM_DIRS (already enwiki only, canary events already removed; drop meta.domain == 'canary' again to be safe). Read ec-hw2/../ingest/vps/capture.py (repo root ingest/vps/capture.py) to understand the files: one gzip file per writer session and partition; a file that is still open has no gzip end marker. Skip files modified within config.OPEN_FILE_GRACE_S seconds of now unless --include-open is given. If a gzip file is cut short (EOFError, zlib.error, gzip.BadGzipFile), keep the complete lines read before the error and log it.
A) parse_stream.py writes data/parsed/page_change.parquet, revert_risk.parquet, tag_events.parquet and capture_gaps.csv (DATA_MODEL.md section 2), plus _SUCCESS_parsed.json.
- Dedupe on meta.id.
- page_change: keep ALL namespaces and kinds, and flatten the fields listed in DATA_MODEL.md (prior_state.revision fields become prior_*; prior_sha1 from prior_state.revision.rev_sha1).
- revert_risk: prob_true = predicted_classification.probabilities.true; keep model_name, model_version; dedupe by rev_id keeping the earliest meta.dt.
- tag_events: added = tags minus prior_state.tags, removed = prior minus tags, mw_reverted_added = 'mw-reverted' in added.
- capture_gaps.csv: per stream, sort events by meta.dt and list holes longer than 120 seconds between consecutive kept events (enwiki-level gaps). Kafka offsets are shared with other wikis in the same partition, so offset jumps are normal; do not report them as gaps, only add the topic/partition as context.
- Print the first and last meta.dt per stream and rows per day.
- Work memory-efficiently: go file by file and build Arrow tables in batches (about 1-3 million events in total).
B) label_live.py writes data/tables/live_revisions.parquet, live_revert_links.parquet, live_revert_links_all.parquet, live_summary.json and _SUCCESS_live.json.
- Live cohort = page_change events with kind in {create, edit}, ns == 0 and rev_dt in config.LIVE_WINDOW. After the meta.id dedupe, rev_id should be unique; if it is not, keep the earliest meta.dt and report the count. Drop null revisions (edits where sha1 == prior_sha1).
- Columns exactly as DATA_MODEL.md section 3: user_kind = config.user_kind(user_name, is_bot, is_temp); user_key = config.editor_key(...); size_delta = rev_size - prior_rev_size (creates: rev_size); seen_ts = meta_dt; tags = union of tags from tag_events for that rev_id with meta_dt <= rev_dt + config.SAVE_TIME_TAG_WINDOW_S, without 'mw-reverted'; mw_reverted_tag and mw_reverted_at from tag events with mw_reverted_added (any time in the capture); revert_risk from revert_risk.parquet; page_edits_prev_1h = number of page_change edit/create events on the same page_id with meta_dt in [seen_ts - 1 hour, seen_ts), not counting itself; followup_s = (newest meta_dt in page_change) - ts. History-only label columns are not in this table (labels go to live_revert_links), but keep the column set otherwise equal to the history table where DATA_MODEL.md says so.
- Range cover exactly as in DATA_MODEL.md section 3 "Range cover (live)". Candidate revisions R = ALL captured page_change edits/creates (all namespaces). Revert events E = all page_change events with a revert (never filter E by namespace). Implement it efficiently: group by page_id and sort; do not run an O(N x M) Python loop over everything. Check E.revert_newest_id == E.parent_id and log the exceptions (count plus 5 examples). range_size = number of captured revisions that E covers.
- live_revert_links_all.parquet = every (R, E) covering pair, any method. live_revert_links.parquet = for each LIVE COHORT revision, its first covering EXACT revert by (E.rev_dt, E.rev_id), with the columns in DATA_MODEL.md: T_s = E.rev_dt - R.rev_dt; known_at = E.meta_dt; K_s = known_at - E.rev_dt; within_followup = T_s <= config.LIVE_FOLLOWUP_S; the reverter from E's performer (user_kind, editor_key, name); by_other; confirmed_by_tag = R has an mw-reverted addition; method; is_exact; range_size; cohort 'live'; source 'stream'.
- The labels are PROVISIONAL until the capture is past config.LIVE_FINAL_AFTER (2026-10-27 00:05 UTC). Write provisional true/false and the newest meta_dt into _SUCCESS_live.json and print a clear warning.
- Print and save in live_summary.json: cohort rows and drops; the revert share (exact, within follow-up) overall and by user_kind; median T; the share confirmed by a tag, split by range_size <= 15 and > 15; how many tag-confirmed reverted revisions the range cover found; K_s p50/p90/p99; revert_risk coverage (share of cohort edits with a score); the newest_id == parent check.
C) late_reverts.py writes data/tables/late_reverts.parquet and late_reverts_summary.json (DATA_MODEL.md section 3, late_reverts).
- September revisions come from the slim file (cast it; keep revision_id, page_id, event_timestamp, revision_is_identity_reverted). Keep those where revision_is_identity_reverted is NOT true.
- Step 1: expand every page_change revert event E (all methods) to September revisions on the same page with the same cover rule (here R comes from the slim file and R.rev_dt = event_timestamp).
- Step 2: take mw-reverted tag additions (tag_events) whose rev_id is a September revision. Link each to a covering page_change revert on the same page with meta_dt in [tag.meta_dt - config.LATE_TAG_LINK_WINDOW_S, tag.meta_dt].
- Step 3: one row per September rev_id with first_signal_at, via, class (exact / inexact_undo / method_unknown), reverting_rev_id, method, age_days (from the reverting rev_dt; for tag-only rows from the tag meta_dt, flagged as an upper bound), restored_later (the reverting revision is itself covered by a later revert in live_revert_links_all), in_history_cohort (rev_id is in data/tables/history_revisions.parquet if that file exists; otherwise use the cohort window from config).
- Print counts by class, distinct reverting actions, distinct pages and the 5 pages with the most rows, and state that these are lower bounds (nobody watched from 2026-10-01 01:38 UTC until the capture started).
Tests: fixtures for gzip tolerance (a truncated part file), meta.id dedupe, the cover rule (exact with an original revision, inexact with oldest, the newest == parent check), the first-exact choice, the 60-second tag window and the late-revert classes.`

P.mongo = `YOUR PART: MongoDB (checked later by the Data+MongoDB role).
Inputs (made by other parts, they exist now; check the _SUCCESS_*.json files and stop with a clear message if one is missing): data/tables/history_revisions.parquet, history_revert_links.parquet, live_revisions.parquet, live_revert_links.parquet, live_revert_links_all.parquet, late_reverts.parquet, data/parsed/page_change.parquet and tag_events.parquet.
Create: ec-hw2/ingest/build_documents.py, ec-hw2/load_mongo.py, ec-hw2/speed_layer.py, the query files ec-hw2/queries/mongo/q1_revert_rate_by_hour.json, q2_top_contested_pages.json, q3_time_to_revert.json, q4_bot_vs_human.json, q5_truth_lag_preview.json and compare_mutual_reverts.json (the "top contested pages" comparison query is q2), ec-hw2/queries/run_mongo.py, ec-hw2/queries/run_all.py (calls run_mongo, then queries/run_cypher.py and queries/run_sql.py only if those files exist; other parts write them), ec-hw2/tests/test_mongo.py, and the outputs results/mongo_*.csv and results/mongo_*.md.
Follow DATA_MODEL.md section 4 exactly for documents and collections, and section 7 for the shared definitions.
- build_documents.py: Parquet -> documents (dicts; datetimes as timezone-aware datetime). comment is cut to 120 characters. Live documents have live{} and history documents have history{}. It writes nothing to disk except results/sample_documents.json: ONE history and ONE live document, with human editor names replaced by pseudonyms (for the report picture).
- load_mongo.py: --target local|atlas|sharded (URIs from config); --confirm-overwrite is required for atlas.
  - local: drop and reload revisions, revert_links, tag_events (mw-reverted additions only) and late_reverts. Create the indexes: the spec's {"page.id": 1, "ts": 1}, {"user.id": 1}, {"history.reverted": 1}, plus {cohort: 1, ts: 1} and revert_links {reverted_rev_id: 1}. Use insert_many in batches of 5,000 (ordered=False).
  - atlas: history documents WITHOUT comment, history revert_links and the chart collections only. Before loading, estimate the size (average BSON size of a sample times the count, plus an index estimate) and refuse if it is over config.ATLAS_BUDGET_MB. Print the database stats after loading. Do not run the atlas target now (there is no ATLAS_URI yet); just make it ready and test the size estimate.
  - sharded: only make the connection work; the scale-out part copies the data.
- speed_layer.py builds page_hour from data/parsed/page_change.parquet (ns 0, edit/create, the whole capture). The key is (page_id, UTC hour of meta_dt). edits_seen = edit events published in that hour; revert_events_seen = events with a revert in that hour; reverted_revs_seen = covered revisions (from live_revert_links_all) counted in the hour of the reverting event's meta_dt.
  - The batch mode must give the same counts on every re-run. Load a staging collection page_change_min (only the needed fields), run an aggregation with $group and $merge into page_hour (whenMatched 'replace'), then drop the staging collection. This shows MongoDB doing the speed-layer job.
  - The --follow mode tails the newest LOCAL raw files (never EventStreams) and applies $inc to page_hour_live. It stops on Ctrl-C and never counts a meta.id twice (keep a set).
  - Print the top 10 page-hours by edits_seen.
- Query files: write each pipeline as MongoDB Extended JSON (bson.json_util) in its own .json file: {"collection": ..., "description": "plain English, including how to paste the pipeline into Atlas Data Explorer > Aggregations or Compass", "pipeline": [...]}. Each pipeline starts with $match on cohort.
  - Q1 (spec 3.1) revert rate by hour of day x user kind. Use both cohorts. Reverted = history.reverted for history; for live, use a $lookup to revert_links with within_followup. Group by cohort, hour_utc and user.kind; output edits, reverted and revert_rate. run_mongo.py also writes chart_q1_hour_kind with $merge.
  - Q2 (spec 3.2) top 20 contested pages: the history cohort with the exact DATA_MODEL section 7 definition. edits_p counts non-bot edits. revert_actions_p = distinct reverting_rev_id from revert_links with within_followup and by_other. Also reverted_editors_p. Keep pages with edits >= 10 and editors >= 2. The score is a float. Order by score desc, revert_actions desc, edits desc, page_id asc, and limit to 20. Add the contested flag and the page title.
  - Q3 (spec 3.3) time-to-revert distribution: $bucket on revert_links.T_s (within_followup) by cohort, with boundaries config.LAG_GRID_S and default config.LAG_DEFAULT_BUCKET. run_mongo.py asserts the default bucket is empty. Output n and share per bucket. Also write chart_q3_time_to_revert.
  - Q4 (spec 3.4) bot vs human share of reverts: a $facet over history revert_links with within_followup and by_other. One facet gives reverts MADE by reverter_kind (share); one gives reverts RECEIVED by author_kind (share). Add the revert rate of bot edits vs human edits from revisions.
  - Q5 (spec 3.5) truth-lag preview. Start from revisions (both cohorts). Use an equality $lookup to revert_links on reverted_rev_id (plus a cohort match). Also $lookup page_hour for the page's edits in the hour before the edit; that is live only, and for history use history page_edits_prev_1h and say so in a note.
    - Compute T, and for live also known-by = T + K.
    - Output, for each cohort and user_kind: the share of eventual reverts (within 4 days, the common horizon) already known at each wait in config.WAIT_POINTS_S.
    - For live, also output revert-risk deciles (in run_mongo.py, with $bucketAuto or precomputed decile cut points). For each decile give n, the revert rate within 4 d, the median T, and the residual P(w < T <= 4 d | T > w) for each w in config.DECISION_WAITS_S, with a Wilson 95% CI (the CI may be computed in Python after the pipeline).
    - Also write chart_q5_known_by and chart_q5_risk_deciles. Drop groups with n < config.RISK_MIN_GROUP_N.
  - compare_mutual_reverts (spec 5): history revert_links with within_followup and by_other. $group to (reverter_key, author_key, page_id) counts, then a self-$lookup to find the reverse direction on the same page. Output unordered pairs (a < b) per page with both counts, ordered by page_id, a, b.
- run_mongo.py runs all 6 pipelines on local (or --target atlas) and times each one (median of 7 warm runs after 1 warm-up). It writes results/mongo_<name>.csv and .md (the first rows as text tables, using tabulate), writes the chart collections, asserts the Q3 default bucket is empty, and prints a summary. Replace human editor names with pseudonyms in any result that shows editors (the same alias rule as the graph: 'editor_' + the first hex digits of sha1(editor_key), long enough to be unique).
- Check your results against Python:
  - The Q5 share known within 4 d computed from the Parquet tables must equal the Mongo result (print both).
  - Q2 must match a pandas computation from the Parquet tables (same 20 page_ids, scores rounded to 6).
- Tests (test_mongo.py) may use the local MongoDB with database truthlag_test, dropped at the end. Cover the document builder shape, the Q2 tie order on a tiny fixture, the Q3 bucket edges and the mutual-revert pairing.
- At the end, load local for real and run run_mongo.py.`

P.neo4j = `YOUR PART: Neo4j (checked later by the Neo4j role).
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
- At the end, export, load local, and run run_cypher.py for real.`

P.comparison = `YOUR PART: SQL and the three-engine comparison (checked later by the Comparison+viz role).
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
- At the end, run load_sql.py, run_sql.py and compare.py for real.`

P.scaleout = `YOUR PART: Scale-out demo and the setup guides (the Comparison+viz role checks the scale-out; all roles use the guides).
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
- At the end, run the sharding demo for real and put its numbers in results/sharding.md.`

P.literature = `YOUR PART: Literature (all four roles will read it). Create ec-hw2/report/references.md. It answers the proposal grade "Literature 7/10: Please refer to more papers" and "Novelty: could substantiate the gap better". You may use web search and fetch for this part only. Write no other files.
- **Target.** Find at least 12 (aim for 14-18) NEW peer-reviewed papers. None of them may already be cited in either proposal version (exclusion list below). Each must back one of our design choices.
- **Themes** (at least 3 papers each):
  1. revert timing and vandalism repair on Wikipedia
  2. edit wars, conflict and revert networks (graphs of who reverts whom)
  3. bots and live monitoring or streams of Wikipedia
  4. document vs graph vs relational databases (NoSQL comparisons, graph query performance)
  5. Add the original PageRank and Louvain papers.
- **VERIFY EVERY PAPER.** Use web search, the publisher page, doi.org, ACM DL, IEEE Xplore, PLoS, Semantic Scholar or Google Scholar to confirm the title, all authors, venue, year, pages and DOI. Leave out any paper you cannot verify. Never invent a DOI. Mark each paper "Verified" with the URL you checked.
- **Exclusion list** (already cited in a proposal):
  - Steiner, van Hooland & Summers 2013 (MJ no more); Träris & Balsacq 2021
  - Pendyala 2018 (Veracity of Big Data); Pendyala & Hall 2024
  - Carlini et al. 2024 (poisoning web-scale training datasets)
  - Croushore & Stark 2001; Aruoba 2008; Höhle & an der Heiden 2014
  - Priedhorsky et al. 2007; Kumar, West & Leskovec 2016 (hoaxes)
  - Geiger & Halfaker 2013 (When the levee breaks); Flöck, Vrandečić & Simperl 2012 (Revisiting reverts)
  - Trokhymovych et al. 2023; Akidau et al. 2015 (Dataflow); Golab & Johnson 2011; Hellerstein, Haas & Wang 1997
  - Kimball & Ross 2013; Snodgrass 2000; Flajolet et al. 2007 (HyperLogLog); Confluent cp-demo
- **Candidates** (verify; do not assume they are correct):
  - Viégas, Wattenberg & Dave 2004 (history flow, CHI)
  - Kittur, Suh, Pendleton & Chi 2007 (He says, she says, CHI)
  - Suh, Chi, Kittur & Pendleton 2008 (Lifting the veil, CHI); Suh et al. 2007 (us vs. them, VAST)
  - Sumi, Yasseri, Rung, Kornai & Kertész 2011 (Edit wars in Wikipedia, SocialCom/PASSAT)
  - Yasseri, Sumi, Rung, Kornai & Kertész 2012 (Dynamics of conflicts in Wikipedia, PLoS ONE)
  - Brandes, Kenis, Lerner & van Raaij 2009 (Network analysis of collaboration structure in Wikipedia, WWW)
  - Halfaker, Kittur & Riedl 2011 (Don't bite the newbies, WikiSym)
  - Halfaker, Geiger, Morgan & Riedl 2013 (The rise and decline of an open collaboration system, American Behavioral Scientist)
  - Halfaker & Riedl 2012 (Bots and cyborgs, IEEE Computer)
  - Geiger & Ribes 2010 (The work of sustaining order in Wikipedia, CSCW)
  - Tsvetkova, García-Gavilanes, Floridi & Yasseri 2017 (Even good bots fight, PLoS ONE)
  - West, Kannan & Lee 2010 (spatio-temporal analysis of revision metadata, EUROSEC)
  - Potthast, Stein & Gerling 2008 (Automatic vandalism detection in Wikipedia, ECIR)
  - Adler, de Alfaro, Mola-Velasco, Rosso & West 2011 (CICLing)
  - Kiesel et al. 2017 (Spatio-temporal analysis of reverted Wikipedia edits, ICWSM)
  - Keegan, Gergle & Contractor 2013 (Hot off the wiki, American Behavioral Scientist)
  - Vicknair et al. 2010 (A comparison of a graph database and a relational database, ACM SE)
  - Cattell 2011 (Scalable SQL and NoSQL data stores, SIGMOD Record)
  - Angles & Gutierrez 2008 (Survey of graph database models, ACM Computing Surveys)
  - Holzschuher & Peinl 2013 (Performance of graph query languages)
  - Brin & Page 1998 (WWW) or Page et al. 1999
  - Blondel, Guillaume, Lambiotte & Lefebvre 2008 (Fast unfolding of communities, J. Stat. Mech.)
  - Books are allowed but do not count toward the 12.
- **Format of references.md** (plain short English, following ec-hw2/STYLE.md):
  1. A 2-3 sentence intro saying what the list is for.
  2. One table per theme: # | Full citation (IEEE style) | DOI or URL | Verified (URL checked) | What it measured or showed (one plain sentence, max 25 words) | Where we use it (the design choice or query, e.g. Cypher Q1 mutual reverts, Mongo Q3 time to revert, the comparison section).
  3. A "Gap table".
     - Rows: the 6-8 closest works.
     - Columns: uses a live stream? | uses dump labels? | measures time to revert? | compares the live view with the later record? | builds a revert graph? | compares document vs graph databases?
     - Last row: "Our HW2".
     - Base each cell on what the paper actually did, and write "unclear" when unsure.
  4. "Reading batches": split the new papers into 4 batches of about 4, one per role (Data+MongoDB, Neo4j, Comparison+viz, Report+GenAI), matching themes to roles. Add an empty column "Teammate notes (own words)".
  5. "Citable Wikimedia facts", each with its exact URL and a short quote:
     - the MediaWiki History dumps page (monthly snapshots; only the last two kept)
     - Manual:Reverts (mw-reverted only for reverts of 15 or fewer revisions; manual revert detection looks back 15 revisions)
     - the EventStreams HTTP service page (a replay window of 7-31 days; a 15-minute connection timeout)
     - the page/change schema
     - any Wikitech or Phabricator statement that analyses wait weeks for the monthly rebuild, or about an incremental daily table (T424350)
- **key_numbers:** the number of verified new papers per theme.`

P.docs = `YOUR PART: The team docs skeleton (checked later by the Report+GenAI role). Start now. Other parts are being built at the same time, so write what you can and mark the missing parts clearly as 'TODO(after build): ...' where numbers or file lists are not ready.
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
  - The parse scripts (names above), and what each one reads and writes (from DATA_MODEL.md).`

P.notebooks = `YOUR PART: The notebooks, the report skeleton and FACTS (checked later by the Report+GenAI role; each notebook is checked by its role).
Everything else is built now. Read: results/*.md and *.csv, data/tables/_SUCCESS_*.json and *_summary.json, results/comparison.md, results/sharding.md, report/references.md, README.md, GLOSSARY.md and PROGRESS.md (all made by other parts).
Create:
- ec-hw2/notebooks/01_data.ipynb, 02_mongodb.ipynb, 03_neo4j.ipynb, 04_comparison.ipynb and 05_truth_lag.ipynb
- ec-hw2/report/FACTS.md and ec-hw2/report/REPORT_SKELETON.md (+ .docx)
- ec-hw2/report/figures/architecture.mmd + architecture.png
- results/figures/*.png (charts)
Update README.md only where it has 'TODO(after build)' lines (fill them; do not rewrite the rest).
- **Notebook rules** (STYLE.md):
  - a top box: Question / Answer (the number) / Time to run / Needs
  - the first code cell sets up the paths (sys.path to ec-hw2) and prints config.DATA_VERSION
  - a markdown cell with What / Why / You should see above every code cell
  - never print secrets; pseudonyms for human editors
  - the last cell compares the key numbers with FACTS.md and prints OK or DIFFERENT
  - Notebooks CALL the project scripts and functions or read their outputs; do not re-implement logic.
  - Keep each one under about 2 minutes when the databases are up.
- **Execute every notebook** with '.venv/bin/jupyter nbconvert --to notebook --execute --inplace ec-hw2/notebooks/NN_x.ipynb'. If the kernel is not the venv, register it with '.venv/bin/python -m ipykernel install --user --name truthlag-hw2' and add --ExecutePreprocessor.kernel_name=truthlag-hw2. Fix errors until all 5 run.
- **Notebook contents:**
  - **01_data:**
    - where the data comes from: the VPS capture + the filtered dump, rsync, no live connections from laptops
    - counts per cohort and the filters that dropped rows
    - capture coverage + gaps
    - sanity checks: the history count vs Wikistats (298,802 content edits Sep 8-10), the non-bot revert rate, the median T
    - the definition-gap table: dump label vs mw-reverted tag agreement by T bucket; live tag confirmation by range size (<= 15 / > 15)
    - one real revisions document, with pseudonyms
  - **02_mongodb:**
    - the schema and indexes (list them from the local DB)
    - the 5 pipelines (print each JSON) and their results as text tables, each with 1-2 plain sentences of facts on what it means
    - the timings
    - the Atlas status: if ATLAS_URI is set; otherwise say "Atlas not loaded yet"
  - **03_neo4j:** the graph model (node and relationship counts), the 5 Cypher queries (print the text) with their results, and the edit-war picture.
  - **04_comparison:** results/comparison.md, the equality checks, the timings (with the draft/final label) and the modeling notes.
  - **05_truth_lag:** the truth-lag preview.
    - the known-by curves for both cohorts (a figure)
    - the RAG-crawler decision table: wait time -> share of eventual reverts already visible, by risk decile, with n and the 95% CI
    - the late-revert case study: counts and 3 examples (pseudonyms; page titles are fine)
    - clearly labelled PROVISIONAL if the live labels are not final (read _SUCCESS_live.json)
- **Charts** follow good chart practice. Load the 'dataviz' skill if your tools allow. Otherwise: a clear title that states the finding, labelled axes with units, no 3D, a colour-blind-safe palette, direct labels, a light grid. Save PNGs to results/figures/ at 150 dpi.
- **FACTS.md** is one table: key | value | unit | source file | FINAL or PROVISIONAL. PROVISIONAL means it depends on the live cohort until 2026-10-27 00:05 UTC. Include every number a teammate needs to write their section:
  - cohort sizes, revert rates, median T, % within 1 h / 1 d
  - the bot share of reverts made and received
  - top contested page examples, the number of mutual pairs, the largest community size
  - comparison timings + lines of code
  - the sharding distribution
  - late-revert counts by class
  - the decision-table headline numbers
  - one concrete, non-sensitive example page from the history cohort with a short revert timeline, for the Motivation
- **REPORT_SKELETON.md:**
  - The spec section 7 headings, word for word and in order: Abstract, Motivation, Data + links, Architecture/workflow diagram, Mongo section, Neo4j section, Results/insights, Comparison top 5, Technical difficulties, Best practices + key learnings, Criteria map table, Reuse note, Mandatory GenAI Q&A.
  - For EACH heading: the owner role, a word target, a facts box (FACTS keys + figure files), 3 guiding questions, and an '[OWNER: write 3-6 short sentences ...]' line.
  - CLAUDE WRITES NO NARRATIVE PARAGRAPHS: our proposal lost points because it read as AI-written.
  - You MAY draft only these mechanical parts, each tagged '[drafted by Claude Code; checked by <name>, <date>]':
    - **Data + links:** the dump file URL, its size (557,344,652 bytes), the download date (2026-10-24), the EventStreams stream URLs and the VPS filter script name. Licenses: the History dump is CC0; EventStreams has no stated license, so link it.
    - **The architecture figure:** embed report/figures/architecture.png. The Mermaid source in architecture.mmd shows: VPS capture -> rsync -> Mac -> parse -> Parquet -> MongoDB -> CSV -> Neo4j / SQLite, and dump -> VPS filter -> rsync. Render it with '.venv/bin/python' + mermaid-cli via 'npx -y @mermaid-js/mermaid-cli' using the installed Google Chrome (set PUPPETEER_SKIP_DOWNLOAD=1 and a puppeteer config with executablePath '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'). If that fails, draw it with matplotlib.
    - **The "Where we differ from the spec, and why" table:**
      - page_change.v1 instead of recentchange/revision-create
      - two cohorts, because the 2026-10 dump appears in November
      - live label = the 4-day stream label
      - the capture runs on a VPS and the data comes by rsync
      - REVERTED has page_id
      - Atlas free tier = M0
      - IN_CATEGORY skipped
      - Bloom is not on Community, so Neo4j Browser is used
    - **Query blocks** for the Mongo and Neo4j sections: the code + the first 5-10 result rows as text tables.
    - **The criteria map table:** each spec section 8 row -> file or figure evidence + 'as in spec / changed'.
    - **The Reuse note frame:** what carries over to the final project (capture, parsers, labels, revert_links, page_hour); Kafka and Spark come in the final project.
    - **The "What we changed after the proposal feedback" table:**
      - Motivation 6/10 -> human-written, from our own example
      - Literature 7/10 -> 12+ new verified papers in references.md
      - Novelty 8/10 -> gap table + search method + our numbers
      - Impact 9/10 -> one persona (a RAG-crawler engineer) + the decision table
    - **The GenAI Q&A frame:**
      - the course question "Did you find or come across solutions to similar problems by using Generative AI or other sources?", answered Yes
      - a table with the columns: spec item # | tool + exact model ID (Claude Code, claude-opus-5-5) | verbatim prompt or link (ec-hw2/genai/prompts/...) | help given | what a person checked
      - a row for each of the 4 members to fill: Scott Nelson, Tingyu Lee, Wanru Hsiao, Zhenni Dai
      - a "Who did what" table frame
  - **Hints for the owners:**
    - Motivation: start from the example page in FACTS and its revert timeline, then half a page of related work from report/references.md.
    - Novelty: a placeholder for the search-method sentence, plus the gap table from references.md.
    - Impact: a placeholder for the RAG-crawler engineer persona, plus the decision table from notebook 05.
- Convert REPORT_SKELETON.md to report/REPORT_SKELETON.docx with pandoc (embed the PNG figures), so the Report+GenAI owner can import it into Google Docs.`

const run = (key, phase) => agent(COMMON + '\n\n' + P[key], { label: key, phase, schema: RESULT })

// Light parts that need no data: start them now.
phase('Docs')
const litP = run('literature', 'Docs')
const docsP = run('docs', 'Docs')

phase('Build data')
const [history, stream] = await parallel([() => run('history', 'Build data'), () => run('stream', 'Build data')])
if (!history || !stream) log('WARNING: an ETL part returned nothing; later parts will report missing inputs')

phase('Databases')
const mongo = await run('mongo', 'Databases')
const neo4j = await run('neo4j', 'Databases')
const comparison = await run('comparison', 'Databases')
const scaleout = await run('scaleout', 'Databases')

const [literature, docs] = await Promise.all([litP, docsP])
phase('Docs')
const notebooks = await run('notebooks', 'Docs')

return { history, stream, mongo, neo4j, comparison, scaleout, literature, docs, notebooks }
