# Plan: Truth Lag EC HW2, a MongoDB + Neo4j MVP (due Thu 2026-10-29, 4:29 PM PT)

## Context
EC HW2 (`EC_HW2_TruthLag_Spec.md`) asks Group 9 to answer one problem in MongoDB (documents) and Neo4j (graph), then compare both with SQL. The problem: *which English Wikipedia edits get reverted, how fast, and who reverts whom.* The team also writes a report with a criteria map and GenAI answers. HW2 is the storage + query MVP for the final project. The private repo `scottn66/truth-lag` holds only a scaffold today.

Four facts drive the plan:
1. **Time.** 6 days remain. EventStreams keeps only about 7 days of replay. The live capture is already running on the VPS.
2. **Data timing.** The October History snapshot only appears around Nov 1–12, so we use **two cohorts plus a small late-revert join**.
3. **Proposal feedback.** Motivation 6/10 (it read as AI-written), Literature 7/10 (more papers needed), Novelty 8/10 (show the gap), Impact 9/10 (no concrete user). We think the short Tab 1 version was submitted, but that is not confirmed.
4. **Team.** The team is semi-technical and may face a language barrier. The chat export shows Chinese (Traditional and Simplified) phone settings.

**User decisions (Oct 23):**
- Claude builds a full working MVP. Each owner verifies their part, does the UI steps and writes their report section in their own words.
- Colima + Docker CLI on the Mac for MongoDB and Neo4j.
- Two cohorts + the late-revert join, as a case study with counts; the grade rides on the two cohorts.
- Owners are **TBD** (docs show roles without names).
- The capture and the dump filtering run on Scott's Hostinger VPS (`ssh vps-coin`, `/opt/truthlag`); the data reaches the Mac by rsync.

**Out of scope for HW2:** Kafka/Redpanda and PySpark belong to the final project. The report says so in its reuse note.

**Topology:**
- **VPS (light work only):** the capture units and the one-time dump filtering.
- **Mac:** everything else (rsync copy of the data, ETL, MongoDB + Neo4j in Colima, SQLite, notebooks).

### Verified facts (probes plus 9 review agents, 2026-10-24 UTC)
- **History dump.**
  - Only the 2026-08 and 2026-09 snapshots are online. `2026-09.enwiki.2026-09.tsv.bz2` is 557,344,652 bytes.
  - It has 78 columns in the confirmed order (refinery source). Null is an empty field and sha1 is base-36.
  - Identity reverts have no depth limit; the only limit is the snapshot cutoff.
  - The `…2026-10` file is a 1.6-hour spill-over, so we ignore it.
  - Wikistats: content edits for Sep 8–10 total **298,802**.
- **Revert timing (Sep 1 sample).** 6.9% of human namespace-0 edits are reverted. The median time to revert is 3.8 h. 33% of reverts take more than 1 day and 15% more than 7 days.
- **Temporary accounts.** Since 2025-11-04 enwiki has no IP edits. Logged-out editors use temporary accounts.
- **`page_change.v1` 1.12.0.**
  - Replay keeps about 7 days. Data from Oct 19 23:00Z leaves the replay around Tue Oct 27 03:00 PT.
  - `revision.revert` has {method, is_exact, rev_original_id/dt (only if exact), rev_reverted_oldest_id/newest_id}.
  - The reverted set is the page's revisions in (timestamp, rev_id) order.
  - No tags.
- **`revision-tags-change`.** It carries save-time tags (giving `tags[]` for live edits) and `mw-reverted` additions. It has no performer, no method and no reverting rev_id.
- **`page_revert_risk_prediction_change.v1`.** Wikimedia's live revert-risk score per edit, arriving about 3 s after the edit. This is a real **live signal** for Q5.
- **`revision-create`.** Its replay is sparse and has no revert fields, so the capture uses page_change.v1 instead.
- **EventStreams rules.** No server-side filter; canary events must be dropped. Resume can repeat events, so dedupe on `meta.id`. At most 2 connections per IP.
- **Atlas free tier (M0).**
  - 0.5 GB of uncompressed BSON plus indexes. No sharding.
  - Views, `$lookup`, `$bucket` and `$facet` work. MongoDB 8.0. One free cluster per project.
  - Charts: only a Project Owner adds data sources; views work; PNG export.
- **Neo4j.**
  - `neo4j:2026.10.1` community bundles GDS + APOC and works offline.
  - Load with `LOAD CSV … CALL (row) {…} IN TRANSACTIONS OF 10000 ROWS` in an implicit transaction. Cast all values.
  - Browser at :7474. Aura Free allows 200k nodes / 400k relationships and has no in-database GDS.
- **This Mac.**
  - M5, 16 GB RAM, about 21 GB disk free (uv cache = 11 GB).
  - No Docker; uv, Python 3.12, node/npx and Chrome are installed.
  - Colima on macOS 27: no `brew services`; if the CPU spikes, use `--mount-inotify=false`.
- **VPS.** 7.8 GB RAM, **no swap**.
- **GitHub.** All 3 invites (wanru0215, Memme3636, daizhenni) **expired** (created Oct 15–16).

## Pre-flight tonight (about 10 min)
- **Scott:** System Settings → Software Update: turn off automatic updates until Oct 30.
- **Claude:**
  - `uv cache prune` (cache only).
  - Re-send the 3 GitHub invites: delete each expired invitation, then `gh api -X PUT repos/scottn66/truth-lag/collaborators/<login> -f permission=push`.
  - Draft **Message 1** for Scott to send tonight:
    - the invite link
    - the 4 spec roles (Data+MongoDB / Neo4j / Comparison+viz / Report+GenAI), with "claim one by Sat 12:00 PT, otherwise Scott assigns"
    - 3 questions: Windows or Mac? Is Python installed? Free hours Sat–Tue?

## Step 0: capture (already running on the VPS; we only read it)
- **Units** (systemd, `/opt/truthlag` on `vps-coin`):
  - `truthlag-capture-a` = `page_change.v1` + revert-risk, since 2026-10-19T23:00Z
  - `truthlag-capture-b` = `revision-tags-change`, since 2026-10-17T00:00Z
- **Output format:** gzip ndjson partitioned by `meta.dt` hour, one `wb` part file per writer session, atomic Last-Event-ID state.
- **Pinned paths (copied into `config.py`):**
  - `RAW_STREAM_DIR = /opt/truthlag/data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-<session>-<n>.ndjson.gz`
  - `STREAM_DIRS` (the `<stream>` values) = `mediawiki.page_change.v1`, `mediawiki.page_revert_risk_prediction_change.v1`, `mediawiki.revision-tags-change`
  - `HISTORY_DIR = /opt/truthlag/data/history/`
  - `HISTORY_COHORT_FILE = enwiki_rev_ns0_2026-09-08_10.parquet` (the cohort)
  - `HISTORY_SLIM_FILE = enwiki_rev_all_2026-09_slim.parquet` (slim all-September file, for the reverter join)
  - The Mac mirrors the same layout under `data/raw/` and `data/history/`.
  - Parsers find partitions by the `dt=` and `hour=` keys and read every `part-*` file.
- **Hard rules for Claude and all build agents:**
  - Never stop, restart, edit or redeploy the VPS units.
  - Never open EventStreams connections. Live data arrives only through rsync.
  - On the VPS, run only read-only commands (`systemctl status`, `ls`, `zcat | head`, `df`, `free -m`) and rsync *from* it.
- **Copy for the record:** pull a read-only copy of the VPS collector script and unit files into `ingest/vps/` so the repo documents the capture ("code in repo"). The README says the live copy runs on the VPS.
- **rsync rule (every sync, everywhere):**
  - Always go through `vps-coin`, which is the public IP <VPS public IP>, not the Tailscale alias.
  - Always use `-az --partial`; **never `--delete`**.
  - First sync: `rsync -az --partial vps-coin:/opt/truthlag/data/raw/ data/raw/`. Re-run it whenever needed; it is incremental.

## Step 1: environment and data paths (inline)
- **Python:**
  - `uv venv --python 3.12`
  - `ec-hw2/requirements.txt` (no pyspark): pandas 2.3.x, pymongo ≥4.19,<5, neo4j ≥6.4,<7, pyarrow, requests, python-dotenv, matplotlib, pytest, jupyter, nbconvert, ipykernel, tabulate
  - Notebooks run with `uv run jupyter lab`.
- **Containers (Mac only):**
  - `brew install colima docker docker-compose pandoc`
  - `colima start --cpus 4 --memory 6 --disk 20`
  - Merge `cliPluginsExtraDirs` into `~/.docker/config.json`.
- **`ec-hw2/docker-compose.yml`:**
  - `mongo:8.0` (matches Atlas): `--wiredTigerCacheSizeGB 1`, `mem_limit 1.5g`, named volume `mongo_data`
  - `neo4j:2026.10.1`: `NEO4J_PLUGINS='["apoc","graph-data-science"]'`, 1.5 GB heap + 1 GB page cache, `mem_limit 3g`, named volume `neo4j_data`, bind-mounts only `data/neo4j/import` (read-only) and plugins, password ≥8 characters
  - Test with `RETURN gds.version()`.
- **History data:**
  - The VPS downloads and filters the September dump into two files:
    - the **Sep 8–10 namespace-0 cohort file**
    - a **slim all-September file** for the reverter self-join
  - Both live under `/opt/truthlag/data/history/`. They are copied with `rsync -az --partial vps-coin:/opt/truthlag/data/history/ data/history/`, never with `--delete`.
  - We read the **Parquet copies**: `enwiki_rev_ns0_2026-09-08_10.parquet` (cohort) and `enwiki_rev_all_2026-09_slim.parquet` (slim).
  - **All their columns are strings**, so `parse_history.py` casts every type explicitly (ints, booleans, timestamps, the tag list), using one typed map in `config.py`.
  - First, inspect the files read-only on the Mac copy (size, row count, column list, sample rows). Record the column lists in `config.py` with `HISTORY_DIR`, `HISTORY_COHORT_FILE`, `HISTORY_SLIM_FILE`, `RAW_STREAM_DIR` and `STREAM_DIRS`.
  - Also record in the report: the dump's source URL, its size (557,344,652 bytes), the download date and the VPS filter command, because the dump link dies in early December.
  - Copy the VPS filter script into `ingest/vps/` if it exists.
- **Repo:**
  - Create branch `ec-hw2`. Move the spec to `ec-hw2/SPEC.md`. Update `.gitignore`.
  - Add a banner at the top of the root README: "EC HW2 → `ec-hw2/README.md`".
  - Mark `notebooks/00_access_points.ipynb` as "final project, read only" (78 columns, not 77; do not open live streams).

## Data design (written once in `ec-hw2/config.py`)
| | `history` cohort | `live` cohort |
|---|---|---|
| Source | VPS-filtered dump 2026-09 (cohort file + slim file) | rsynced raw: page_change + revert-risk (A), tags-change (B) |
| Window (half-open, UTC) | [2026-09-08, 2026-09-11), about 299k | [2026-10-20, 2026-10-23), about 300k |
| Reverted | col 72 and col 74 ≤ 20 d (`HISTORY_FOLLOWUP_DAYS=20`; every revision is followed ≥20 d) | First covering **exact** revert with T ≤ 4 d (`LIVE_FOLLOWUP_DAYS=4`) |
| Reverter | Self-join of col 73 against the **slim all-September** file (user id, name, bot, temp) | Performer of the reverting edit |

**Shared definitions:**
- **Time to revert** T = reverting rev_dt − reverted rev_dt, in both cohorts.
- **Stream delay** K = `meta.dt − rev_dt` of the reverting event, in its own table. The live "known-by" curve is T + K.
- **Range cover:** the upper bound is (ts, rev_id) ≤ (prior_state.revision.rev_dt, newest_id). The lower bound is (rev_original_dt, rev_original_id) < (ts, rev_id) when the revert is exact; otherwise use rev_id ≥ oldest_id. Assert that newest = rev_parent_id and log any exceptions. Revert events are never filtered by namespace.
- **Lag grid (s):** [0, 60, 300, 900, 3600, 21600, 86400, 172800, 345600, 604800, 1209600, 1728001]. Use `$bucket` with a default bucket and assert that it stays empty.
- **User kind**, checked in this order:
  1. empty name → `unknown`
  2. bot (`group` in col 14 / `performer.is_bot`)
  3. `temporary` (logged out)
  4. otherwise `registered`
  - We keep the spec's `user.is_anon` = temporary.
  - Editor key: `u:<user_id>` (registered or bot) or `t:<name>` (temporary). `unknown` gets no key.
- **`reverted_by_other`** (reverter ≠ author) is used for Q2, contested pages, Q4 and graph edges. "Reverted (any)" is used for Q1, Q3 and Q5, and the self-revert share is printed.
- **Contested page:**
  - Input: edits_p (no bots) ≥ 10.
  - Counts: revert_actions_p (distinct reverting revisions by others) and reverted_editors_p.
  - Score = revert_actions_p / edits_p (float).
  - A page is contested if revert_actions ≥ 2, reverted_editors ≥ 2 and score ≥ 0.2.
  - Order by score desc, revert_actions desc, edits desc, page_id asc. Engines are compared on (page_id, round(score, 6)).
- **Clean-up:**
  - Drop null revisions (sha1 = parent sha1) in both cohorts.
  - For a page creation, `size_delta` = rev_size.
  - `tags[]` = save-time tags without `mw-reverted` (live: tag events ≤60 s after the edit). `mw_reverted_tag` is stored separately.
  - `rev_id` must be unique in the live cohort, after dedupe on `meta.id`.
- **Revert-risk:**
  - Dedupe by rev_id (earliest score).
  - Deciles are computed over scored edits, plus a "no score" group (page creations).
  - Decision table: P(w < T ≤ 4 d | T > w) for w ∈ {0, 1 h, 1 d}, with n and a Wilson 95% CI.
  - Drop groups with n < 100.
- **Live counters `page_hour`:**
  - Key: (page_id, UTC hour of `meta.dt`). Fields: edits_seen, revert_events_seen, reverted_revs_seen, each counted in the hour it became known.
  - Built with `$group + $merge (replace)`, so a re-run is safe.
  - `page_edits_prev_1h` uses the window [t−1h, t) and excludes the edit itself.
- **Late reverts (case study):**
  1. Expand every page_change revert (all methods) to September rev_ids through a range on page_id, against the slim September file.
  2. Link `mw-reverted` tag events to a covering revert on the same page within 10 min.
  3. Keep one row per September rev_id where col 72 is not true, with first_signal_at, via, class ∈ {exact, inexact_undo, method_unknown} and restored_later.
  4. Report counts by class, distinct reverting actions, distinct pages and age. Say they are **lower bounds**, because of the unseen gap from Oct 1 01:38 to capture start.
  - The slim file must include page_id, ts, rev_id and col 72. Check this in Step 1.
- **Definition gap (a finding):**
  - Manual reverts are detected only within the last 15 revisions; rollback and undo have no limit.
  - `mw-reverted` is added only for reverts of ≤15 revisions. The dump has no limit.
  - Recompute dump-vs-tag agreement over the whole history cohort, split by time-to-revert bucket.
  - For live: report the confirmation share separately for ranges of ≤15 and >15 revisions ("unconfirmed ≠ wrong").

## Step 2: build workflow (Workflow, about 8 agents, started while Scott is awake)
Before the fan-out, I write the contracts (`config.py` with the VPS file paths and schemas, `ingest/history_columns.py`, the collection shapes) and run each new command type once, so any approval prompt comes up early. I also copy every workflow script and its prompts **word for word** to `ec-hw2/genai/{workflows,prompts}/`.

**Agent rules:**
- Touch only your own files. No git writes, no package installs, no `docker compose down -v`.
- **No VPS commands** except the read-only list in Step 0, and never touch the capture units. No EventStreams connections.
- Write `*.tmp` → `os.replace` → `_SUCCESS.json` with row counts; downstream lanes wait for that file.
- Run long jobs in the background with a log.
- **Never use `timeout`**; it does not exist on macOS. Use the tool's own time limits or background jobs.
- At most 2 data-heavy jobs at a time, all on the Mac.

| Build lane → role that checks it | Files (under `ec-hw2/`) | Waits for |
|---|---|---|
| History ETL → Data+MongoDB | `ingest/parse_history.py`: reads the rsynced Parquet cohort and slim files at the `config.py` paths, casting the all-string columns explicitly → `data/gold/history_*.parquet` + history `revert_links` (reverter self-join); tests on fixtures in the same schema | Step 1 rsync |
| Stream ETL → Data+MongoDB | `ingest/parse_stream.py`: reads the rsynced raw tree at `RAW_STREAM_DIR` (every part file; tolerates a truncated gzip; skips files changed in the last 2 min) → bronze Parquet; `ingest/label_live.py`; `ingest/late_reverts.py`; tests | Step 0 rsync |
| MongoDB → Data+MongoDB | `ingest/build_documents.py`; `load_mongo.py` (`--target local\|atlas\|sharded`; Atlas needs `--confirm-overwrite` and has a ≤400 MB budget with no `comment`); `speed_layer.py` (page_hour; `--follow` tails the local rsynced files and writes only `page_hour_live`); `queries/mongo/q1…q5.json` + `compare_mutual_reverts.json`; `queries/run_all.py` | the two ETL lanes |
| Neo4j → Neo4j | `export_graph.py` (MongoDB → CSV, with an alias for human editors); `load_neo4j.py` (constraints, LOAD CSV; `--target aura --subset contested` uses UNWIND); `queries/cypher/q1…q5.cypher` + `compare_top_contested.cypher` + `load.cypher` for Neo4j Desktop | MongoDB |
| Comparison → Comparison+viz | `load_sql.py` → `data/gold/truthlag.sqlite`; `queries/sql/compare_*.sql`; `comparison/compare.py` (reads queries only from `queries/`; counts lines of code; full ordered-list equality; median of 7 warm runs, timed alone after Step 3; modeling pain 1–5) | Neo4j |
| Scale-out → Comparison+viz | `scaleout/docker-compose.sharded.yml` (separate project, port 27020; each mongod has a 0.25 GB cache / 600m limit; mongos 256m); init script; `demo_sharding.py` (shards the **empty** collection, loads, then shows the distribution and SINGLE_SHARD vs SHARD_MERGE). Runs on the Mac only after the Comparison lane, with Neo4j stopped. `SHARDING.md` gives the key choice. | Comparison |
| Literature → all four roles | `report/references.md`: ≥12 **new** peer-reviewed papers (none from either proposal version), each checked by DOI and tied to a design choice, split into 4 reading batches | none |
| Docs & report → Report+GenAI | Starts **early** as a skeleton and fills in as lanes finish: `README.md` (incl. the VPS → rsync → Mac data-flow picture), `GLOSSARY.md`, `STYLE.md`, `PROGRESS.md`, `check_setup.py`, notebooks 01–05, `report/REPORT_SKELETON.md`, `report/FACTS.md`, figures (Mermaid → PNG via mermaid-cli using the installed Chrome) | all |

**Collections:**
- `revisions` (one per revision): `{_id:"enwiki:<rev_id>", wiki_db, rev_id, parent_id, cohort, page:{id,title,ns}, user:{id,name,kind,is_bot,is_anon,is_temp,edit_count}, ts, hour_utc, size, size_delta, comment, tags[], mw_reverted_tag, is_revert, revert_method, live:{seen_ts, revert_risk}, history:{reverted, reverted_any, secs_to_revert, reverting_rev_id, reverter:{key,name,kind}, followup_s}}`
- `revert_links` (one per reverted revision; source dump or stream; `reverting_rev_dt`; `known_at` for stream rows only)
- `page_hour`, `tag_events`, `late_reverts`
- Indexes (spec): `{page.id, ts}`, `{user.id}`, `{history.reverted}`. Plus `{cohort, ts}` and `revert_links.reverted_rev_id`.

**Queries (numbered as in spec §3 and §4):**
| Mongo | | Cypher | |
|---|---|---|---|
| Q1 | Revert rate by hour of day × user kind | Q1 | Mutual-revert pairs on the same page |
| Q2 | Top 20 contested pages | Q2 | Central reverters: out-degree + PageRank on the REVERSE projection |
| Q3 | Time to revert (`$bucket`, lag grid) | Q3 | Louvain (UNDIRECTED, weight = count) + WCC |
| Q4 | Bot vs human: reverts made and received (`$facet`) | Q4 | Pages with the most distinct warring editors |
| Q5 | Truth-lag preview: equality `$lookup` revert_links (+ page_hour) → lag buckets, `$group` by kind and risk decile; history vs live | Q5 | 2-hop: editors linked through contested pages |

- **Comparison queries:** `compare_mutual_reverts` (Mongo, using a self-`$lookup`) and `compare_top_contested` (Cypher) complete the 2 questions × 3 engines.
- **Graph model:**
  - `(:Editor {key,alias,kind})-[:EDITED {ts,rev_id,reverted}]->(:Page {id,title,contested})`
  - `(:Editor)-[:REVERTED {page_id,count,ts,last_ts}]->(:Editor)`: exact reverts by others only, one edge per pair and page.
- **Scale-out:** the history cohort (lean documents) and small pre-aggregated live/Q5 collections go to Atlas. `SHARDING.md` explains `{"page.id":"hashed"}`.

## Step 3: verify workflow (about 7 adversarial agents)
Each reviewer tries to refute what it checks:
1. ETL meaning, including that the parsers match the VPS file schemas
2. Mongo results vs the ETL labels
3. Cypher and GDS (PageRank direction)
4. Comparison fairness and equality across the 3 engines
5. Readability for the team
6. Coverage of spec §3–§10 and the 4 feedback items
7. Citations

I fix each confirmed finding and re-run what it affects. Then I time the comparison on an otherwise idle Mac.

## Step 4: share (Sat)
- Commit **one lane at a time** with plain messages and attribution lines. Push. Open a **draft PR** with per-role file links and checklists.
- Publish **data-v1** as a private Release: the final history cohort + the partial live cohort, as Parquet, graph CSVs and `.sqlite`.
  - Teammates download it in the browser into the exact folder; nothing downloads automatically.
  - `check_setup.py` checks the files and `DATA_VERSION`.
- Draft **Message 2** for Scott: "MVP ready, here is your checklist", with links to `tree/ec-hw2/ec-hw2`.

## Step 5: live cutoff (Mon Oct 26 after 5 PM PT)
`ec-hw2/refresh_live.sh` runs in order:
1. `rsync -az --partial vps-coin:/opt/truthlag/data/raw/ data/raw/` (public IP, never `--delete`).
2. Check that the newest `meta.dt` is ≥ 2026-10-27T00:05Z; stop if it is not.
3. Stream ETL + labels + late reverts.
4. Build and load the live cohort.
5. page_hour `$merge`.
6. Atlas chart collections (names and fields frozen).
7. run_all.
8. Execute notebooks 01 and 05.
9. Update FACTS.md.
10. Release **data-v2**.

It prints the change in headline numbers since Sunday. The VPS capture keeps running untouched.

## Team plan (roles TBD; each role has the same 5 items, about 6–8 h)
| Item | Data+MongoDB | Neo4j | Comparison+viz | Report+GenAI |
|---|---|---|---|---|
| 1. Verify (re-run, then PR "Approve" listing the numbers checked) | notebooks 01–02, Atlas load | notebook 03 | notebooks 04–05, sharding output | README, glossary, skeleton, criteria map |
| 2. UI artifact (upload yourself on GitHub, so it carries your name) | Atlas tier/doc/indexes screenshots + Mongo Q1–Q4 run in Data Explorer | Neo4j Browser shots (screen-share on Scott's Mac, or Aura subset) incl. `db.schema.visualization()` | ≥2 Atlas Charts as PNGs (history views from Sun; live chart after Mon) | final PDF from Google Docs |
| 3. Write in own words (from FACTS.md) | Mongo section + "Answer to Q1" | Neo4j section + "Answer to Q2" | Comparison top 5 + Impact | Abstract, Motivation + related work, Technical difficulties, Key learnings (with everyone's notes) |
| 4. Literature | Read about 4 abstracts; write 1–2 sentences each; open each DOI | same | same | same |
| 5. Own GenAI row + 2–3 dated observations in PROGRESS.md | ✓ | ✓ | ✓ | ✓ |

**Schedule (PT):**
| When | What |
|---|---|
| Sat 12:00 | Roles claimed; invites accepted |
| Sat | Atlas project created and all 4 invited as Project Owner; Scott's Mac loads the history cohort that night; check_setup on every laptop; a 15-minute read-test of the README by one teammate |
| Sun | Check the FINAL numbers, take screenshots, finish literature notes |
| Mon 20:00 | Neo4j screenshots done |
| Tue 20:00 | Charts and all sections done |
| Wed 18:00 | Integrated Google Doc |
| Wed | Merge PR to main, tag `ec-hw2-submitted`, then Scott chooses: make the repo public or invite the instructor; test the logged-out view |
| **Thu 12:00** | Internal submit: named submitter + backup; grep for `TBD` / `[OWNER` / `TODO` |

If someone misses a deadline, Scott does the task. Claude drafts a short daily chat update for Scott to send.

**Never cut:** Mongo Q1–Q5, Cypher Q1–Q5, the 3-engine comparison, ≥2 Charts, screenshots, the criteria map, GenAI Q&A, grader access.

**Cut first, in this order:**
1. `--follow`
2. Late-revert detail (keep only the counts)
3. Risk deciles
4. Sharding demo (keep the explanation)
5. GDS (fall back to Cypher)
6. Shrink the live cohort to the captured hours

**Core check:** Sat 23:59.

## Report plan (Google Doc is the master copy from Sun)
On Sunday the Report+GenAI owner creates the Google Doc from the skeleton's DOCX export. Q5 and Impact numbers stay marked PROVISIONAL until the Monday refresh. On Thursday the final PDF and text are committed to `ec-hw2/report/`.
- **`REPORT_SKELETON.md`:** spec §7 headings word for word. Each heading has a facts box (FACTS keys tagged FINAL or PROVISIONAL), figures, a word target, 3 guiding questions and an `[OWNER: …]` line. **Claude writes no narrative paragraphs.** Claude drafts only the mechanical parts, each tagged "[drafted by Claude Code; checked by <name>, <date>]":
  - data links
  - the deviations table
  - the criteria map
  - query blocks (code + first 5–10 result rows as text)
  - captions
  - reuse note (incl. "Kafka/Spark come in the final project")
  - the GenAI table frame
- **Feedback fixes the grader will see:**
  - Motivation opens with one real page and its revert timeline, followed by half a page of related work with the new papers.
  - Novelty gives:
    - the search method (databases, query strings, date, number screened)
    - the 3 closest works and what each lacks
    - 2 of our own numbers
    - a note that Wikimedia's daily table is internal and does not measure consumer error against wait time
  - Impact has **one persona, a RAG-crawler engineer**, plus the decision table from notebook 05 (wait time → share of eventual reverts already visible, by risk decile).
  - A table "What we changed after the proposal feedback".
  - Results open with "Answer to Q1" and "Answer to Q2". The Q2 answer includes one association, such as the share of mutual pairs on the top pages.
- **Mandatory GenAI Q&A:**
  - It starts with the course question, answered **Yes**.
  - A table: spec item # | tool + exact model ID (`claude-opus-5-5`) | verbatim prompt or link | help given | what a person checked.
  - The errors that review caught, and who caught each one.
  - A named row for each of the 4 members.
  - A "who did what" table with exact verbs (built / verified / created in UI / wrote).
- **Deviations table:** page_change instead of revision-create; two cohorts; capture on a VPS with rsync; the 4-day stream label; `REVERTED.page_id`; Atlas free tier (M0); `IN_CATEGORY` skipped.
- **Privacy:** human editors appear only as pseudonyms in screenshots and the report; bots are named. Licenses are stated exactly: History is CC0; EventStreams publishes no license, so we link it.

## Team-friendly docs (`STYLE.md`, `GLOSSARY.md`, `README.md`)
- **Writing:**
  - Short plain sentences; one term for each idea; numbered steps with the exact command and the expected output.
  - Data times in UTC, schedule times in PT, and every time shows its time zone.
  - Use words, not letters (`history`/`live`, role names, Mongo Q1–Q5, Cypher Q1–Q5). "Lane/agent/contract" never appear in team docs.
  - A list of AI-sounding phrases to avoid. "Simple English with our own numbers beats polished text"; any translator or AI help must be logged.
- **Pictures:** the data flow (VPS capture → rsync → Mac → MongoDB → CSV → Neo4j/SQLite), one real `revisions` document and the graph model, as PNG + Mermaid.
- **Every notebook:**
  - a 4-line top box: Question / Answer / Time to run / Needs
  - "What / Why / You should see" above every cell
  - a final cell that checks the numbers against FACTS.md (OK / DIFFERENT)
  - `DATA_VERSION` printed
  - outputs committed
- **`GLOSSARY.md`:**
  - every term with an example from our data
  - a **中文 column** (繁體/简体), drafted by Claude and marked "please correct"
  - a "proposal word → HW2 word" table (Cohort A, H = 30 d, bronze/silver/gold, Kafka → final project …)
- **`README.md`:**
  - the start point
  - "three ways to check" per role:
    1. read on GitHub
    2. use a GUI: paste the JSON into Atlas Data Explorer; `load.cypher` + queries in Neo4j Desktop; DB Browser for SQLite on the Release `.sqlite`
    3. Python with Mac and Windows commands side by side, plus `check_setup.py`
  - "you only need these files" per role
  - a 6-step "GitHub without Git" box

## Verification
- `pytest ec-hw2/tests`, with fixtures in the exact VPS file schemas for:
  - column map and types
  - range cover and the newest = parent assertion
  - reverter self-join and the 20-day label
  - user-kind order
  - contested score ties
  - late-revert classes
  - base-36 sha1
  - truncated-gzip tolerance in `parse_stream.py`
- Notebook 01 sanity checks:
  - history count ≈ 298,802 (minus null revisions)
  - human revert rate ≈ 5–8%
  - median T of a few hours
  - no duplicate `meta.id` after dedupe
  - the gap list (holes > 2 min per topic, computed from the data)
  - tag agreement figures
- **Equality:** the top-20 contested pages and the mutual pairs come out identical in MongoDB, SQLite and Neo4j. Mongo Q5 equals `label_live.py`.
- **No-Docker path:** a fresh venv with only the Atlas URI and Neo4j Desktop runs `ec-hw2/notebooks/01–05`. Run the clean-clone test after Step 4, with data-v1.
- **Capture (VPS, read-only):**
  - `ssh vps-coin systemctl is-active truthlag-capture-a truthlag-capture-b` returns `active` twice.
  - `systemctl show -p NRestarts`: the baseline is **capture-a = 2, capture-b = 1**. Flag any increase to Scott.
  - **After catch-up only:** the newest `meta.dt` per stream is within 5 min of now. During the replay catch-up, check that it keeps moving forward instead.
  - The earliest A event is ≤ 2026-10-19T23:05Z; the earliest B event is recorded in FACTS.md.
  - `df -h` and `free -m` show healthy headroom.
  - The Mac's rsync copy matches the VPS file count. Count **closed files only**, skipping files changed in the last 2 minutes on either side.

## Risks and fallbacks
- **VPS memory (7.8 GB RAM, no swap).** An OOM kill could stop the capture. Nothing heavy runs there (no MongoDB, Neo4j, pandas loads or parsing). The filtering is a one-time, streaming job. Watch `free -m` and `journalctl -u truthlag-capture-*` for OOM or restart loops, and tell Scott at once; he decides any fix. A gap shorter than about 7 days heals on resume.
- **VPS disk or network trouble:** same rule. Report it to Scott; rsync whatever already exists.
- **Replay window for the live start.**
  - Data from 2026-10-19T23:00Z leaves the EventStreams replay around **Tue Oct 27 03:00 PT**.
  - It is already captured, but after that time it cannot be fetched again.
  - So the raw files are irreplaceable. Keep the VPS copy and the Mac rsync copy; rsync never uses `--delete`; nothing deletes or rewrites `data/raw/`.
- **Colima** still failing after 45 min: switch to OrbStack (free for students). If that fails too: `brew install mongodb-community@8.0` plus Neo4j Desktop.
- **Capture broken for good:** build Q5 from tags-change plus a dump-only lag curve, and label it as such.
- **Atlas over budget:** load a stratified 100k sample.
- **Mac disk (~21 GB free):** the rsynced raw is about 250 MB/day. The guards stop the jobs below 4 GB free. Reload by dropping collections, not volumes.
- **Open (not blocking):** whether Tab 1 or Tab 3 was submitted. Scott makes the Wed repo-visibility choice.
