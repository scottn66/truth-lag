# DATA 226 Group 9 — TruthLag on Delta Lake: build plan and handoff (Nov 13, 2026)

> Exported on 2026-11-13 from the Notion page of the same name. The Notion page is the working copy; if the two differ, Notion is newer.

> **Purpose.** A build plan and handoff for agents and teammates who will rebuild the TruthLag pipeline as a Bronze, Silver and Gold lakehouse on Delta Lake before the term project is due on 2026-11-17. It was written in a cloud Claude Code session with Scott on Nov 13, 2026. Everything marked *ran* was executed in that session on made-up events. Nothing here was run on the real data, which lives only on Scott's Mac and the VPS. Reviewers: read **How to review** first.

## TL;DR

- **Goal.** Rebuild the TruthLag pipeline as Bronze, Silver and Gold Delta tables under `data/lake/`, and reproduce every published EC HW2 number from them.
- **Engines.** Python with delta-rs writes Bronze and Silver and reuses the tested functions in `ec-hw2/ingest/`. Spark SQL writes Gold: the star schema, the SCD Type 2 page dimension, the label fact with Change Data Feed, and the E(L) mart. One engine writes each table. If Spark does not start on the Mac, Gold has to be rewritten for delta-rs; that path was tested only as single operations.
- **Proof of correctness.** The published numbers must match (page R1 lists them in 44 rows), for example 295,016 and 279,466 revisions, and E(1 h) = 0.4434 and 0.4205.
- **New result, if the 2026-10 History snapshot is online.** Dump labels for the live cohort joined on `(wiki_db, rev_id)`; the September labels that changed between two snapshots; a time-travel query on the label table before and after the load.
- **What was tested.** Both engines ran every building block on made-up data in the cloud session (research pages R2 and R3). Two prototypes of the pipeline then passed their checks, also on made-up data (R6 and R7). Nothing ran on the real data.
- **Status.** Draft for review, written Nov 13, 2026, and revised the same day after an internal review (see **Review log**). No file in the repository was changed. Scott's open decisions are in **Open decisions for Scott**. Reviewers start at **How to review**.

Sub-page: Research findings for the Delta Lake plan (Nov 13, 2026)

## Deadline and scope

- **Due:** term project report, slides and code on 2026-11-17. Source: this project's tracker row and the Class work row, both taken from the Canvas snapshot. The time of day is not confirmed.
- **Days left when this was written:** 4.
- **Who builds:** Claude Code on Scott's Mac, where the data is. A cloud session can write and test code on made-up events only.

| Tier | Item | Why |
| --- | --- | --- |
| Must | Bronze, Silver and Gold tables on Delta for the existing capture, reproducing the published EC HW2 numbers | Proves the lakehouse is correct. Needs no new data. |
| Must | Star schema with `dim_page` as SCD Type 2, `fact_edit`, and the E(L) mart | Promised in the proposal and in `docs/schema_and_warehouse.md`. |
| Must | Tests on made-up events, a table catalog document, a GenAI disclosure entry | Repo conventions and course policy. |
| Should | Load the 2026-10 History snapshot; reconcile the live cohort with dump labels on `(wiki_db, rev_id)`; find September labels that changed, with MERGE and Change Data Feed | The project's central comparison. Possible only if the snapshot is online. |
| Should | Time-travel demonstration: the label fact before and after the 2026-10 load | Ties the Delta Lake paper to TruthLag. Nearly free once the load exists. |
| Should | Burst slice: E(L) by the page's activity in the hour before the edit, from columns that already exist | The team's current-events question. One more SQL file in Phase 4. Committed results suggest the effect may be null. |
| Could | Intervals for the burst contrast; a replay by day with `as_of`; an OPTIMIZE and Z-order demonstration | Stretch. |
| Not now (proposed) | Kafka or Redpanda, Airflow, dbt, pageview data, polling Wikipedia for editorial signals, any change to the VPS capture | No time before the deadline. Dropping Kafka is a decision for Scott (see Design decisions). |

## Rules (must hold for any change)

From the repository's own documents (`ec-hw2/STYLE.md`, `ec-hw2/ingest/README.md`, `ec-hw2/config.py`) and this tracker's guardrails:

- Never stop, restart or edit the capture units `truthlag-capture-a` and `truthlag-capture-b` on the VPS. Never open an EventStreams connection from a laptop or a cloud session.
- Never delete or change anything in `data/raw/` or `data/history/`. Never add `--delete` to rsync. Never commit anything under `data/`.
- New code only. Nothing from ClaimKB, corpus-engine, DATA 245 or DATA 255. Reusing TruthLag's own EC HW2 code is inside the project.
- Keep a GenAI disclosure entry for every AI-assisted piece of work. The repository's pattern is `ec-hw2/genai/PROMPTS.md`.
- Scott sends all team messages and submits the work. Agents draft only.
- Human editor names stay out of committed results. Use the keyed pseudonyms (`config.ALIAS_SECRET`); bots keep their names.
- Every rule and constant comes from `ec-hw2/config.py`. `ec-hw2/DATA_MODEL.md` is the contract for existing tables. Documents follow `ec-hw2/STYLE.md`: short sentences, numbers with units, data times in UTC.

Added by this plan:

- Treat `ec-hw2/` as frozen. Import from it; do not edit it. The submitted state has no tag yet.
- A new package must not be named `ingest`, `config` or `tests`. Those names collide with existing folders (ran for the name `ingest`: the import fails).
- Never write into `data/parsed/` or `data/tables/`. They hold the only copy of the published `data-v2` tables, and the parity checks need them. Never run the old scripts (`parse_stream.py`, `parse_history.py`, `label_live.py`, `late_reverts.py`, `refresh_live.sh`) as scripts, and never call their `run()` functions without a temporary output folder: their default outputs are these two folders.
- New input files go into new folders next to `data/history/`: downloads into `data/history_raw/<snapshot>/`, and slim files made by this project into `data/history_slim/<snapshot>/`. Nothing new is written into `data/raw/` or `data/history/`, except by Scott's rsync. Both new folders are named once, in `etl/lake_config.py`.
- One writing process per Delta table at a time. Delta gives no guarantee for concurrent writers on a local file system.
- Never run VACUUM on the lake before the project is submitted.
- Do not push or open a pull request without Scott's explicit go-ahead.

## Current state

Verified on Nov 13 from a clone of the repository, unless marked.

- **Repository:** `scottn66/truth-lag` (private), default branch at `8e28012` (Oct 29). The cloud session that wrote this page can read it. An agent that gets a 404 lacks access to the private repository.
- **Capture:** the repository documents two systemd units on the VPS `vps-coin`, started about 2026-10-24 04:52 UTC, replaying from 2026-10-19 23:00 UTC (page changes and revert risk) and 2026-10-17 (tag changes). *Not checked:* whether they still run today.
- **Pipeline:** the EC HW2 pandas pipeline is complete (`ec-hw2/ingest/`: `parse_stream.py`, `parse_history.py`, `label_live.py`, `late_reverts.py`). Its 30 ingest tests pass in a clean environment (ran: Python 3.12.3, pandas 2.3.3, pyarrow 26.0.1).
- **Final-project code:** `etl/` and `reconcile/` hold only `.gitkeep`. PySpark has never run in this repository: the saved output of `notebooks/00_access_points.ipynb` shows a Java error.
- **Published numbers:** `ec-hw2/report/FACTS.md`, built on 2026-10-29 from `data-v2`. The newest parsed event is 2026-10-27T20:59:59Z.

| Data | Location | Reachable from a cloud session |
| --- | --- | --- |
| Raw stream files (`.ndjson.gz`) | VPS `/opt/truthlag/data/raw/`; copied to Scott's Mac `data/raw/` by rsync | No |
| Filtered History files, snapshot 2026-09 | Mac `data/history/` | No |
| Raw History dump `2026-09.enwiki.2026-09.tsv.bz2` (557 MB) | VPS only | No |
| Parsed and cohort tables | Mac `data/parsed/`, `data/tables/` | No. GitHub release `data-data-v1` has a 107 MB zip of the tables (seen on GitHub on Nov 13); `data-v2` was not published. |
| Published numbers and query results | `ec-hw2/report/FACTS.md`, `ec-hw2/results/` | Yes |

| | History cohort | Live cohort |
| --- | --- | --- |
| Edits made (UTC) | 2026-09-08 to 2026-09-10 | 2026-10-20 to 2026-10-22 |
| Source | History dump, snapshot 2026-09 | EventStreams capture |
| Revisions after filters | 295,016 | 279,466 |
| Reverted | 19,700 within 20 days; 17,646 within 4 days | 17,818 within 4 days |
| Share of eventual reverts known after 1 hour (4-day horizon) | 55.66% | 57.95% |
| Labels | From the dump | From the stream only |

Volumes over the parsed span (190 hours): 1,231,427 page-change events (about 155,500 per day), 789,634 revert-risk events, and 1,603,253 tag events over 259.5 hours. Raw gzip was about 1.0 GB, growing about 117 MB per day. Details and sources are in the research page R1.

Sub-page: Lake design reference: tables, keys and clocks (draft v1, Nov 13, 2026)

## Target design in one page

The table catalog, with every key and column, is on the sub-page **Lake design reference**, just above this section. This is the short form.

| Layer | Holds | Tables | Written by | Write rule |
| --- | --- | --- | --- | --- |
| Bronze | What was received, unchanged | `bronze/page_change_events`, `bronze/revert_risk_events`, `bronze/tags_events`, `bronze/history_slim`, `bronze/history_full` | Python with delta-rs | Append only. Each captured line and each dump file is loaded once. |
| Silver | One clean row per thing | Stream: `silver/page_change`, `silver/revert_risk`, `silver/tag_events`, `silver/capture_gaps`. Dump: `silver/history_slim`. Cohorts: `silver/history_revisions`, `silver/history_revert_links`, `silver/live_revisions`, `silver/live_revert_links`, `silver/live_revert_links_all`, `silver/late_reverts` | Python with delta-rs, calling the functions in `ec-hw2/ingest/` | Stream tables: insert-only MERGE on the event id; for revert risk, the earliest score per revision. Cohort tables: rebuilt as of a time, and replaced only when rows changed. |
| Gold | Star schema and measures | `gold/dim_cohort`, `gold/dim_snapshot`, `gold/dim_time`, `gold/dim_user`, `gold/dim_page` (SCD Type 2), `gold/fact_edit`, `gold/fact_revert_label`, `gold/mart_el_curve`, `gold/mart_reconciliation`, `gold/recon_mismatch`, `gold/mart_label_change` | Spark SQL | MERGE that touches only changed rows. Change Data Feed on the two facts. |

Three ideas carry the design:

1. **Four clocks.** Event time (`rev_dt`), publish time (`meta_dt`), snapshot time (which dump a label came from) and lake time (when a Delta commit recorded it). The capture stores no receive time, so publish time is the stream's "known at" clock.
2. **Every build has an** `as_of`**.** `as_of` limits stream events only: a build uses events with `meta_dt <= as_of`. Dump labels are limited by the `snapshot` argument of the label loads and of the reconciliation marts. The E(L) mart reads the current label fact, and its commit metadata names the newest snapshot loaded. A commit stores both values in its metadata. Building at an early and then a late `as_of` gives two table versions, and time travel answers "what did we know at time T?".
3. **The old code stays the source of the rules.** Silver calls the existing functions in `ec-hw2/ingest/` instead of rewriting them. Equal numbers follow from equal code, and the parity checks prove it.

To reproduce the published numbers, build with `as_of = 2026-10-27T20:59:59.999999Z`. This cut is inferred, not recorded. `FACTS.md` prints the newest events in whole seconds, 20:59:59 for page changes and tags and 20:59:58 for revert risk, so the published tables appear to end with capture hour 20 of Oct 27. Phase 2 has the exact cut.

## Design decisions

Each row is a choice the build depends on. **Default** is what this plan recommends, and what the build does unless Scott says otherwise. Evidence pages: R1 (old pipeline), R2 and R3 (engine labs), R4 (Delta docs), R5 (snapshots and current events), R6 and R7 (prototypes).

| ID | Decision | Default | Main alternative | Evidence | Needed by |
| --- | --- | --- | --- | --- | --- |
| D1 | Which engine writes which layer | delta-rs writes Bronze and Silver. Spark SQL writes Gold. One engine per table. | delta-rs for everything, if Spark does not start on the Mac. For Gold that is a rewrite: only single operations were tested (R2). | R6: both engines in one environment, and 16 parity tests pass. R7: 78 of 78 Gold checks pass. | Phase 4 |
| D2 | Where the lake lives | `data/lake/` in the repository folder, on the Mac's local disk. Spark's side folders go in `data/spark_home/`. | An external disk, if the Mac has less than 10 GB free | `data/` is already git-ignored | Phase 1 |
| D3 | Scope for Nov 17 | The tiers in **Deadline and scope**, cut in the order given under **Build phases** | Stop after Phase 4 | The deadline | Phase 0 |
| D4 | Kafka or Redpanda, Airflow, dbt | Not built. The report says so and gives the reason. The Bronze tables are the replayable log. | Add Redpanda between capture and Bronze | `docs/schema_and_warehouse.md` lists them as later options. The glossary in `ec-hw2/GLOSSARY.md` (section 6) says the proposal named Kafka or Redpanda for the final project, so leaving it out is a deviation to state. | Phase 0 |
| D5 | How the 2026-10 History snapshot lands | The Mac downloads the two month files and keeps them. A new script cuts each to the 12 slim columns. Bronze loads the slim files. | Run the existing filter on the VPS. This needs Scott: agents may not change anything there. | The plan's own choice: the reconciliation needs only the 12 slim columns, and the raw files stay on disk. R5 recommends loading the whole monthly file. | Phase 5 |
| D6 | Definition of E(L) | The published one: 4-day horizon, 9 wait points, a revert is known when `T_s + coalesce(K_s, 0) <= L`. The marts read T and K from the Silver link tables. | The proposal's 30-day horizon: the history cohort has that much follow-up once the 2026-10 snapshot is loaded, the live cohort has about 9 days. Also possible: a 9-day horizon with dump labels; Kaplan-Meier. | R1 golden numbers. R7: the mart equals an independent pandas computation. | Phase 4 |
| D7 | How changing labels are stored | `gold/fact_revert_label` holds the current dump label per revision. Each snapshot is one MERGE commit. Change Data Feed and `gold/mart_label_change` hold the changes. Silver keeps every snapshot's rows. | An append-only observation table only | R7: 700 planted label changes were found exactly | Phase 5 |
| D8 | How `dim_page` is built | Recompute the full list of page versions, keep the rows that are new or changed, then one MERGE on a deterministic `page_key` | The classic staged MERGE with a NULL merge key | R7: the classic form loses versions when a page changes twice in one run. 207 pages differed, and 4,210 fact rows found no version. | Phase 4 |
| D9 | How table versions are addressed | By version number, found through the commit metadata (`step`, `as_of`, `snapshot`). Never by timestamp. | In-commit timestamps, which delta-rs cannot write | R2 and R3: timestamp travel follows file modification times and breaks after a copy | Phase 1 |
| D10 | Table features | Used: append-only on Bronze, Change Data Feed on the two facts. Not used: deletion vectors, liquid clustering, identity or generated columns, VARIANT, column mapping, in-commit timestamps. | Deletion vectors on Gold: a faster MERGE, but delta-rs can then no longer read the table through pandas | R3 cross-engine table | Phase 1 |
| D11 | Retention | Every table is created with 3650 days of log and deleted-file retention, and with log cleanup off. No VACUUM before submission. | The defaults, under which commits older than 30 days are deleted at a checkpoint | R2 saw the default delete old commits | Phase 1 |
| D12 | Raw payload in Bronze | `raw_json` as a string, ZSTD compression, statistics on the envelope columns only | VARIANT. An append from delta-rs broke such a table for Spark. | R2: ZSTD 187 MB against snappy 442 MB for 500,000 made-up events. R3: VARIANT was about 10% smaller than a string. | Phase 1 |
| D13 | How a re-run adds nothing | The loader reads from Bronze the highest line already loaded per source file, and loads only later lines | Trust the application-transaction marker alone | R2: with the marker alone, a repeated batch was appended again each time. R6: the table-based check passed, also for a file that grew. | Phase 1 |
| D14 | How the cohort tables are built | The old code, unchanged, on an export of Silver as of `as_of`. A table is replaced only when its rows changed. | Rewrite the label rules as incremental MERGE logic | R6: equal to the old pipeline on the fixtures, also when the events arrive in two parts | Phase 3 |
| D15 | Default `as_of` | The newest `meta_dt` over the three Silver stream tables, as in the prototype. The commit metadata also stores the newest page-change event, from which the old label code takes its follow-up. | The newest page-change event only. It cuts later tag and revert-risk events, and in a review run on the fixtures it changed 1 row of `late_reverts`. | R6 passed with the prototype default | Phase 3 |
| D16 | Repository logistics | A branch for the work, a tag on the submitted EC HW2 state, and no push or pull request without Scott's go-ahead | Work on the default branch | Tracker guardrails | Phase 0 |
| D17 | Editor names | Real names stay in local tables. Anything committed uses the keyed pseudonyms. | None | `ec-hw2/STYLE.md` and `config.ALIAS_SECRET` | Phase 6 |
| D18 | SQL parameters in Gold | `{placeholders}` that the runner fills from a whitelist | Named parameters with `spark.sql.legacy.parameterSubstitution.constantsOnly=true` | R7: named parameters fail under the Delta extension with `UNBOUND_SQL_PARAMETER` | Phase 4 |
| D19 | Editor kind in marts | The kind at edit time, stored on `fact_edit` and read from the Silver revisions. Never from `dim_user`. | None | R7: `dim_user` is Type 1 and differed for 424 revisions | Phase 4 |
| D20 | Current-events slice | A burst mart in Phase 4, from columns that already exist. One contrast, fixed in advance: edits with 10 or more page edits in the prior hour against the rest, at 1 h and 1 d. Intervals are a stretch item. | Editorial signals or pageviews, which need new data | R5: bursts are 2.0% to 2.5% of edits, and their revert rate is not higher | Phase 4 |

### The choices that need Scott

- **D1.** Is a hybrid acceptable for the course? The plan keeps Spark where a warehouse rubric is most likely to look: the star schema, the SCD Type 2 MERGE, Change Data Feed and time travel are all Spark SQL. Bronze and Silver stay in Python for two reasons. Spark's gzip reader fails on a file with no end marker, and 105 of the 748 raw files had none. And the tested label code is pandas.
- **D3 and D4.** Confirm the tiers. Confirm that "Kafka was not built, and here is why" is acceptable in the report.
- **D5.** Who downloads the 2026-10 files, and on which machine? The plan assumes the Mac. The host is `dumps.wikimedia.org`, a file server. It is not EventStreams and not the MediaWiki API.
- **D16.** The branch name, the tag name, and where the GenAI log for the final project lives.

## Build phases

The build runs on Scott's Mac, where the data is. Each phase lists its files, its steps, and the checks that must pass before the next phase starts. Times are estimates for an agent session with Scott at hand.

**Starting point.** Two prototypes exist and passed on made-up data. R6 is the `etl` package for Bronze and Silver, with its parity test. R7 is the Gold SQL with its runner. Copy them in and adapt them; do not write these parts from nothing. The code is in the hand-off kit (a zip file that Scott has). Pages R6 and R7 hold the same code, and page R8 holds the kit's check scripts.

### Phase 0. Decide and prepare (about 2 hours, needs Scott)

1. Scott answers **Open decisions for Scott**.
2. Check the Mac, read-only. Record each result in the progress file.
    - `git status` is clean, and the default branch is at `8e28012` or later.
    - Python 3.12 is available. Java 17 or 21 is available (`java -version`). PySpark has never run in this repository: the saved notebook output says `JAVA_HOME is not set`.
    - Free disk is 10 GB or more. Note the RAM.
    - `data/raw/`, `data/history/`, `data/parsed/` and `data/tables/` exist.
    - `data/parsed/_SUCCESS_parsed.json` shows the published state: 1,231,427 page-change rows, and a newest event at 2026-10-27T20:59:59Z. If it shows a later state, stop and tell Scott, because the parity files are then not the published ones. From the same file, record for each stream the values `lines`, `files_skipped_open` and `cut_short_files` with their `lines_kept`. Phase 2 needs them.
    - Copy `data/parsed/` and `data/tables/` to `data/parity_ref/`, and record the SHA-256 of every file in the progress file. Do this before step 7, and keep the copy until the project is submitted.
3. Scott tags the submitted EC HW2 state. The work then moves to a new branch.
4. Make a new environment, apart from the EC HW2 one: Python 3.12, `delta-spark==4.4.1` (it brings `pyspark==4.2.0`), `deltalake==1.6.6`, `pandas==2.3.3`, `pyarrow==26.0.1`, `polars==2.1.0`, `pytest`. Page R6 lists the 22 versions that were tested together. Then add what later phases need and the labs did not test: `jupyter`, `nbconvert`, `ipykernel` and `matplotlib` for Phase 6; `python-dotenv`, because `config.py` loads `ALIAS_SECRET` from `ec-hw2/.env` only with it; and `pymongo`, because the pseudonym function is in `ec-hw2/ingest/build_documents.py`, which imports `bson`. The 22 tested versions must not change; if one does, stop and tell Scott. Never print the value of `ALIAS_SECRET`, never ask for it in the session, and never write a new one: committed EC HW2 files already hold pseudonyms made with it. If the check at the end of this step fails, stop and tell Scott, who puts the value into `ec-hw2/.env` himself. After the install, run `uv pip check` and record the list of versions. Check that `ec-hw2/.env` on the Mac holds `ALIAS_SECRET`: this command must pass: `python -c "import sys; sys.path.insert(0, 'ec-hw2'); import config; assert config.ALIAS_SECRET"`.
5. Run the 30 old ingest tests in the new environment: `python -m pytest ec-hw2/tests/test_history.py ec-hw2/tests/test_stream.py -q -p no:cacheprovider`. Expect `30 passed`. They must pass before anything else. Do not run the whole `ec-hw2/tests/` folder: its other files need the EC HW2 databases.
6. **Spark gate.** Run the cross-engine check from the kit: `python <kit>/proto_fixture_pipeline/checks/cross_engine.py data/spark_home`. Spark starts with Delta and writes a table, delta-rs reads it, and the reverse. Expect the last line `STEP1C OK`. If this does not pass within about 1 hour of work, stop and tell Scott. The fallback is a rewrite, not a switch: each Gold table is computed in pandas, starting from the independent computations in `verify_gold.py` of the kit, and written with the `delta_io` helpers (pre-filter, then MERGE on the key, with Change Data Feed set when the table is created). Scott decides how much time it gets; expect about one extra day.
7. Scott refreshes the raw data: `rsync -az --partial vps-coin:/opt/truthlag/data/raw/ data/raw/`. Never add `--delete`. Agents do not run ssh or rsync unless Scott says so in the session.
8. Check whether the 2026-10 snapshot is online, with the three `curl` commands on page R5. If it is, download `2026-10.enwiki.2026-10.tsv.bz2` and `2026-10.enwiki.2026-09.tsv.bz2` into `data/history_raw/2026-10/`. Expect about 0.6 GB each; that size is an estimate. Also download `2026-10.enwiki.2026-11.tsv.bz2` if it exists: it is small, holds the first hours of November, and gives the snapshot's cutoff. Record the `Last-Modified` header of each file (`curl -sI`): it says when the snapshot was published.
9. Scott copies the raw 2026-09 `.bz2` file from the VPS to `data/history_raw/2026-09/`. Upstream keeps only two snapshots, so 2026-09 disappears there when 2026-11 is published.
10. Start the GenAI disclosure entry for this work.

Done when: the old tests pass, the Spark gate has a result, and the progress file says which data is present.

### Phase 1. Scaffold and Bronze (about 3 hours)

Files: `etl/__init__.py`, `etl/hw2.py`, `etl/lake_config.py`, `etl/tables.py`, `etl/delta_io.py`, `etl/bronze_stream.py`, `etl/run.py` (all from R6); new `etl/bronze_history.py`; tests in `tests_lake/`.

1. Copy the R6 package into `etl/` and its test into `tests_lake/`. The folder names `ingest`, `config` and `tests` are taken by the old code.
2. Point the import shim at `ec-hw2/` in the repository. The prototype reads the path from the variable `TRUTHLAG_HW2_DIR`; its fallback to a folder next to `etl/` was not run. Set the lake root to `data/lake/`.
3. Run `tests_lake/`. The 16 prototype tests must pass on the Mac before any real data is touched.
4. Run the Bronze loader on `data/raw/`. It appends one row per complete captured line, with the line itself in `raw_json`.
5. Write `etl/bronze_history.py`. It loads `enwiki_rev_all_2026-09_slim.parquet` into `bronze/history_slim` and `enwiki_rev_ns0_2026-09-08_10.parquet` into `bronze/history_full`, both with `snapshot = '2026-09'` and `dump_month = '2026-09'`. Each row also gets `source_file` and `source_row`, its 1-based position in the source file. `source_file` is the file's path below `data/`, never the bare name: the September file has the same name in both snapshots. Before loading, the loader reads from the table the highest `source_row` per `source_file` and appends only later rows, as `bronze_stream.loaded_lines` does for lines. A run that stopped half way is then finished by the next run. Read and write in batches of 500,000 rows: the slim file has 5,266,843 rows of text.
6. Test the history loader on the made-up frames of `ec-hw2/tests/test_history.py`, including a load that stops half way.

Checks:

- A second run adds 0 rows and writes no commit.
- Rows per stream are at least the published event counts: 1,231,427 page changes, 789,634 revert-risk events and 1,603,253 tag events. Bronze keeps repeats and later events, so it holds more.
- The loader reports the cut-short files. The published parse saw 105 of 748.
- `bronze/history_slim` has 5,266,843 rows, and `bronze/history_full` has 300,564. In both, the row count of each source file equals its highest `source_row`.
- The progress file records the Bronze size on disk and the run time.
- If a re-run takes more than about a minute, add a small file ledger (path, size, lines loaded) so that unchanged files are skipped. Compare sizes, not modification times.

### Phase 2. Silver stream tables (about 2 hours)

Files: `etl/silver_stream.py` (from R6); new `etl/parity.py`.

1. Build `silver/page_change`, `silver/revert_risk`, `silver/tag_events` and `silver/capture_gaps` for every event date.
2. Write `etl/parity.py`. It compares a lake table with an old Parquet file after sorting by key: same keys, same values, times equal to the microsecond. The comparison function `assert_same_table` is in the R6 test file; move it into `etl/parity.py` and let the test import it from there.
3. Compare the Silver stream tables, cut at `meta_dt <= 2026-10-27T20:59:59.999999Z`, with the files in `data/parsed/`.

Checks, all at the cut:

- `silver/page_change`: 1,231,427 rows, equal to `page_change.parquet`.
- `silver/tag_events`: 1,603,253 rows, equal to `tag_events.parquet`.
- `silver/revert_risk`: equal to `revert_risk.parquet`. It has one row per revision; the count is in `_SUCCESS_parsed.json` on the Mac.
- Capture gaps that end before the cut: 3, with 850 s in total, all in the revert-risk stream.
- If the counts are close but not equal, check in this order.
    1. The cut. The time cut is inferred from the newest event times. The exact cut is in `_SUCCESS_parsed.json`. Take the files in hour folders up to `dt=2026-10-27/hour=20`, matched by their path below `data/raw/`. Their number must equal `files_read` in the same file (232 page-change, 230 revert-risk and 286 tag files). Leave out the Bronze rows of the files in `files_skipped_open`, and of files whose capture session started after the parse. For each file in `cut_short_files`, keep only the rows with `source_line <= lines_kept`. The Bronze row count of each stream must then equal `lines`.
    2. A revert-risk row with a null `rev_id`. The old file keeps one such row, and the lake drops it.
    3. A `meta_id` that occurs on two event dates. The lake would insert it twice.

### Phase 3. Silver cohort tables (about 4 hours)

Files: `etl/silver_cohorts.py` (from R6); new `etl/silver_history.py`.

1. Write `etl/silver_history.py`. Its first function builds `silver/history_slim`: the Bronze rows typed with `history_columns.cast_history_frame`, in batches.
2. Its second function, `build_history(snapshot)`, runs once per snapshot, not once per `as_of`. It calls `parse_history.run(cohort_path, slim_path, tmp_dir)` on the two 2026-09 files in `data/history/`: the old code reads all-text Parquet files by path, one snapshot and one month at a time. `tmp_dir` is a temporary folder, never `data/tables/`. It then loads `history_revisions` and `history_revert_links` into Silver, replacing a table only when its rows changed, with `step = history` and the snapshot in the commit metadata. It keeps the file `history_revisions.parquet` that the old code wrote. Take the two Arrow schemas from the files that `parse_history` writes, with times cast to microseconds, and add both tables to `etl/tables.py` with the keys `rev_id` and `reverted_rev_id`. The prototype did not port this part.
3. Every `build(as_of)` passes that file through its existing `history_revisions=` argument, so that `late_reverts` marks the history cohort from it.
4. Make `build(as_of)` write `data/lake/_runs/latest.json` at its end: the `as_of`, the build time, and the current version of each table it builds. Spell every `as_of` one way, `YYYY-MM-DDTHH:MM:SS.ffffffZ`, as `silver_cohorts.iso()` does. Only this text is compared, stored in commit metadata and put into SQL.
5. Test the history part on the made-up frames of `ec-hw2/tests/test_history.py`.
6. Build the cohort tables with `as_of = 2026-10-27T20:59:59.999999Z`.
7. Compare them with the files in `data/tables/`.

Checks (numbers from `ec-hw2/report/FACTS.md`):

- `silver/history_revisions` 295,016 rows; `silver/history_revert_links` 19,858.
- `silver/live_revisions` 279,466 rows; `silver/live_revert_links` 18,358.
- `silver/late_reverts` 4,350 rows, 3,591 of them in namespace 0.
- Every table equals its Parquet file in `data/tables/`, value for value.
- A second build with the same `as_of` writes no new version.
- If a cohort table differs in a few rows, look for two page-change events with the same `rev_id` and `meta_dt`. The export is sorted by `meta_dt` and `meta_id`, the old files are in file order, and the old code breaks such a tie by input order.

### Phase 4. Gold: star schema and the E(L) marts (about 6 hours)

Files: `etl/spark_session.py`, `etl/gold_run.py`, `etl/sql/` (from R7); tests in `tests_lake/gold/` (`gen_silver.py`, `planted.json` and `verify_gold.py` from R7) and `tests_lake/test_gold.py`.

1. Copy the R7 SQL files, without files 24, 25 and 26 (the classic SCD2 comparison). The lab runner `run_gold.py` is a fixed scenario on made-up data, and it records an error and goes on. Do not use it as the build tool. Keep its helpers `render`, `table_version`, `find_version`, `newest_as_of`, `run_sql` and `write_step`,. Add `view_step`, `one`, `dim_page_run` and `label_change_run` (the last sits inside `main()`), and change `write_step` so that it raises an error instead of recording it. Leave out the parts for `dim_page_classic`, and `jvm_peak_rss_mb`, which reads `/proc` and does not work on a Mac. Then write a new entry point: `python -m etl.gold_run --as-of <time> [--snapshot <YYYY-MM>] --steps dims,facts,labels,marts`. Any error, a refused `as_of` included, must stop the run with a non-zero exit code.
2. Fill the SQL placeholders from `ec-hw2/config.py`, not from literals: the windows from `HISTORY_WINDOW` and `LIVE_WINDOW`, the follow-up days from `HISTORY_FOLLOWUP_DAYS` and `LIVE_FOLLOWUP_DAYS`, the horizon from `LIVE_FOLLOWUP_S`, the small-group limit from `RISK_MIN_GROUP_N`, and the list of waits from `WAIT_POINTS_S`. No such number stays in a `.sql` file or in the runner.
3. Keep the runner's two guards: it sets the commit metadata before every write, and it refuses an `as_of` older than the newest one already committed. Add a third: `gold_run` reads `data/lake/_runs/latest.json` and stops unless its `as_of` equals the one there, and every table version listed there is still the table's current version. Add a fourth: the `marts` step stops when the `as_of` is before `config.LIVE_FINAL_AFTER` (2026-10-27 00:05 UTC), because the follow-up of the live cohort is then incomplete.
4. Move the checks of the lab runner (75 of the 78; the other 3 need the classic table, which is not copied) into `tests_lake/test_gold.py`. The test builds the made-up Silver lake in a temporary folder, runs `etl.gold_run` on it at the two lab `as_of` values, and asserts the planted counts. The generator writes no `latest.json`, so the test writes one before each run, and it spells the lab's `as_of` values the plan's way. Then the test runs the 18 checks of `verify_gold.py` on the same lake; change that script so that it takes the lake path as an argument. Both must pass before Gold runs on real data.
5. Add `user_kind` to `fact_edit` (D19), and to the rows that the test expects.
6. Make the page-version view repeatable. Add `meta_dt` to its observations (null for history rows), and keep an observation only when its time and its `meta_dt` are both at or before `as_of`. Silver holds events newer than the parity `as_of`; without this filter some of them would enter `dim_page`.
7. Add the dump's current title to the view. The R7 view reads only the title at edit time. A page that was renamed after its last cohort edit, and that has no event in the capture, would then keep its old title as the current row. Add one more branch: for every row of `silver/history_revisions` with a `page_title`, an observation with that title at the time `config.HISTORY_DUMP_LAST_REVISION`. Such a version starts when the new title was first seen, not when the page moved; say so in the notebook.
8. Look at one real raw line of each of the kinds `delete`, `undelete`, `move` and `visibility_change` before trusting the view. The R7 view takes the time of `delete` and `undelete` from `meta_dt`, because its made-up events carried the `rev_dt` of an older revision. The made-up data had no `visibility_change` events, and the published span holds 28. If such an event carries the `rev_dt` of an older revision, use `meta_dt` for this kind too, or leave the kind out of the view.
9. Add `gold/mart_el_by_burst`: the E(L) mart again, grouped by the page's edits in the hour before the edit (0, 1, 2 to 4, 5 to 9, 10 or more) in place of the editor kind.
10. Build Gold with the parity `as_of` and run the checks.

Checks:

- `fact_edit` has 574,482 rows: 295,016 history and 279,466 live.
- `mart_el_curve`, all editors, both cohorts: the 18 known-by counts in **Numbers the build must reproduce**. So E(1 h) is 0.4434 for history and 0.4205 for live.
- `mart_el_by_burst`, revisions per group (0, 1, 2 to 4, 5 to 9, 10 or more). History: 202,410; 42,155; 32,697; 11,888; 5,866. Live: 190,392; 39,277; 30,782; 11,929; 7,086. Eventual reverts in the group of 10 or more: 343 for history and 439 for live.
- By editor kind at 1 h. History: temporary 6,157 of 9,863; registered 3,622 of 7,623. Live: temporary 6,358 of 9,772; registered 3,928 of 7,905.
- `dim_page`: one current row per page; no gap and no overlap between versions; every fact row joins to exactly one version with `event_dt >= valid_from AND (valid_to IS NULL OR event_dt < valid_to)`.
- A second run with the same `as_of` writes no commit in any dimension or fact.
- delta-rs reads every Gold table with the same row counts.
- A new number for the report: how many facts have a title at edit time that differs from the page's current title. This is what hypothesis H4 in `docs/schema_and_warehouse.md` asks about. Beside it, report the count of `silver/history_revisions` rows where `page_title` differs from `page_title_historical`. The two numbers should be close; list the pages where they differ.

### Phase 5. Second snapshot: reconcile, and track label changes (about 4 hours; only if 2026-10 is online)

Files: new `etl/history_slim.py`. The SQL for this phase is already among the R7 files in `etl/sql/` (label load, change feed, reconciliation, time travel); `reconcile/` gets a short note that points to them.

1. Write `etl/history_slim.py`. It streams a `.tsv.bz2` month file and writes, as text, the 12 columns of `config.HISTORY_SLIM_COLUMNS` for rows with `event_entity = 'revision'`. Model it on `ingest/vps/filter_history.py`, with three differences.
    - Only an empty field is null: literal strings such as "NA" stay strings.
    - The output goes to `data/history_slim/<snapshot>/enwiki_rev_all_<month>_slim.parquet`, for example `data/history_slim/2026-10/enwiki_rev_all_2026-09_slim.parquet`.
    - The script writes `name.tmp` and then renames it. It stops if any row does not have 78 fields; the 2026-09 file had none.
    - The script refuses an output path under `data/history/`, and it refuses to replace an existing file. This matters: the September file of snapshot 2026-10 has the same name as the 2026-09 file in `data/history/` that the old code reads, and the model script replaces its output file.
2. Test it on a made-up `.tsv.bz2` with 78 columns: a page row, a row with 77 fields, an empty field, and the literal NA.
3. Load both 2026-10 slim files into Bronze and Silver with `snapshot = '2026-10'`.
4. Fill `gold/dim_snapshot`. The cutoff of snapshot 2026-09 is `config.HISTORY_DUMP_LAST_REVISION` (2026-10-01 01:38:27 UTC). For 2026-10, take the last revision time in `2026-10.enwiki.2026-11.tsv.bz2` if it was downloaded. If not, store the last revision time of the October file, and say in the notebook that the real cutoff is later. Store the published time from Phase 0 where it is known, in a new nullable column `snapshot_published_at` (the tested DDL does not have it). Change `11_dim_snapshot_merge.sql` to match: the R7 file takes the newest revision time in `silver/history_slim` as the cutoff, which is about 1.6 hours too early for 2026-09. Let `gold_run` pass the cutoff in, and keep the row count from the table. Every run must pass the same cutoff, so that a re-run writes no commit.
5. Load `gold/fact_revert_label`: snapshot 2026-09 first, then 2026-10 as one MERGE commit. That commit updates only the rows whose label changed, and inserts the revisions it has not seen. Each month file has about 5.3 million revisions and the lab ran 300,000, so raise `spark.sql.shuffle.partitions` for these loads (for example to 16), and stop if a load takes more than 10 minutes.
6. Build `gold/mart_label_change` from the change feed. Build `gold/mart_reconciliation` and `gold/recon_mismatch` for the live cohort.
7. Run the E(L) mart again after the label loads. Its SQL already holds the series "live cohort, dump labels".
8. Run the time-travel query: reverted history-cohort revisions as known at the 2026-09 load, and now.

Checks. Published numbers exist for the 2026-09 load only. At the `fact_revert_label` version of that load, the history-cohort revisions must show 19,858 rows with `is_identity_reverted`, 19,700 of them with `seconds_to_identity_revert <= 1,728,000`, and 17,646 with `<= 345,600`. The "then" value of the time-travel query must be 19,858. The other checks test consistency:

- A re-run of either snapshot load writes no commit.
- In the change feed, update pre-images = update post-images = rows in `mart_label_change`.
- Follow-up: every live revision has at least 4 days between its time and the 2026-10 cutoff. Report how many do not.
- Cross-check with EC HW2. The stream found 2,970 September revisions that were reverted exactly after the 2026-09 snapshot (`late_reverts`, class `exact`). Report how many of them `mart_label_change` shows as newly reverted. A low share means a bug or a gap between the two definitions, and both are worth knowing.
- Report the five reconciliation classes with counts and shares: both reverted, stream only, dump only, neither, not in the dump.

### Phase 6. Ordered rebuild, evidence and hand-in material (about 4 hours)

1. **Ordered rebuild.** So far the tables were built during development, in no meaningful order. Delete `data/lake/gold/`, `data/lake/_runs/` and the four Silver tables that are built per `as_of` (`live_revisions`, `live_revert_links`, `live_revert_links_all`, `late_reverts`). They are derived data; Bronze, the Silver stream tables and the Silver history tables stay. Then rebuild in knowledge order: cohorts, dimensions and facts at `as_of = 2026-10-24T00:00:00.000000Z`; cohorts and all of Gold at the parity `as_of`; the label loads for 2026-09 and then 2026-10; the marts. At the early `as_of` the follow-up of the live cohort is not complete, so no E(L) mart is written for it. Run every check again. Each table's history then tells the story in order, and the early version of `fact_edit` shows fewer known reverts than the late one.
2. `notebooks/10_lakehouse_evidence.ipynb`, following the notebook rules in `ec-hw2/STYLE.md`. Every table it shows goes through `public_name` and `editor_alias` of `ec-hw2/ingest/build_documents.py` first. It never shows `user_text`, `user_name`, `reverter_name`, `user_id`, `user_key`, `author_key` or `reverter_key`. It shows: the table list with versions; one table history with its commit metadata; the parity table; the E(L) curves from Gold; one moved page in `dim_page`, with a fact joined as of its edit time; the label change feed; the then-and-now result; the reconciliation table.
3. `docs/lake_design.md`: the table catalog from the design sub-page, with the decisions taken.
4. Update `docs/schema_and_warehouse.md` and `README.md` where this plan answers an open point (engine, layers, Kafka). Scott approves the wording.
5. Figures for the report and slides: the three-layer flow, the E(L) curves, the then-and-now table.
6. Finish the GenAI disclosure entry.
7. Last checks: all tests pass; `git ls-files data` prints only `data/.gitkeep`; a search of the files that this build added or changed (`git diff --name-only 8e28012 HEAD`, notebook outputs included) finds no temporary account name (text that starts with `~2` and a digit) and no editor key of the form `t:` and a name or `u:` and a number. The only allowed hits are made-up values in test code. Do not search older files: they already hold made-up names of this kind.

### Stretch items, in this order

1. **Replay.** In the ordered rebuild, use `as_of` = 00:00 UTC on Oct 24, 25, 26 and 27, and the parity `as_of` last. Plot, per day, the reverts within 4 days that were known by then, as a share of the final 17,818. Do not plot E(L) for these builds: their follow-up is incomplete, so their E(L) is biased low.
2. **Intervals for the burst contrast** of D20: a bootstrap that resamples pages, because one page can carry a group.
3. **OPTIMIZE with Z-order** by `page_key` on `gold/fact_edit`, with the files scanned before and after for a query on one page. The key starts with the page id; the table has no `page_id` column. This mirrors Figure 5 of the Delta Lake paper.
4. `is_redirect` in `dim_page`, read from `raw_json`.

### Schedule

| Day (PT) | Work |
| --- | --- |
| Fri Nov 13, evening | Phase 0 |
| Sat Nov 14 | Phases 1 to 3 |
| Sun Nov 15 | Phases 4 and 5 |
| Mon Nov 16 | Phase 6, report and slides, spare time |
| Tue Nov 17 | Submit. No new features. |

The estimates add up to about 25 hours of session work, next to the report and the slides. If Phase 3 is not finished on Saturday, drop Phase 5 at once.

### If time runs short, cut in this order

1. The stretch items.
2. In Phase 5: the mismatch list and the extra E(L) series.
3. All of Phase 5. The report then names the reconciliation as the next step.
4. The burst mart.
5. The early `as_of` in the ordered rebuild.
6. Detail in `dim_time` and `dim_user`.

Never cut: the parity checks, the SCD Type 2 dimension, the E(L) mart, the GenAI disclosure.

## Numbers the build must reproduce

All are read from `ec-hw2/report/FACTS.md` and the committed result files, built from `data-v2`. Page R1 lists 44 such numbers with the expression for each. A rebuild must stop at the parity `as_of` to match the live numbers.

**Known reverts by wait, all editors, 4-day horizon.** A revert counts when `0 <= T_s <= 345,600`. It is known by wait L when `T_s + coalesce(K_s, 0) <= L`.

| Wait L | History: known of 17,646 | History E(L) | Live: known of 17,818 | Live E(L) |
| --- | --- | --- | --- | --- |
| 0 | 0 | 1.0000 | 0 | 1.0000 |
| 1 min | 3,506 | 0.8013 | 3,986 | 0.7763 |
| 5 min | 6,204 | 0.6484 | 6,958 | 0.6095 |
| 15 min | 7,737 | 0.5615 | 8,398 | 0.5287 |
| 1 h | 9,822 | 0.4434 | 10,326 | 0.4205 |
| 6 h | 12,900 | 0.2690 | 13,405 | 0.2477 |
| 1 d | 15,697 | 0.1104 | 15,936 | 0.1056 |
| 2 d | 16,725 | 0.0522 | 16,699 | 0.0628 |
| 4 d | 17,646 | 0.0000 | 17,818 | 0.0000 |

**Row counts.**

| Table | Rows | Note |
| --- | --- | --- |
| `silver/page_change` at the cut | 1,231,427 | One row per `meta_id`, all namespaces and kinds |
| `silver/tag_events` at the cut | 1,603,253 | 99,606 of them add `mw-reverted` |
| Revert-risk events at the cut | 789,634 | Before the one-row-per-revision rule |
| `silver/history_revisions` | 295,016 | From 300,564 cohort-file rows: 4,265 not in namespace 0, 568 and 715 null revisions |
| `silver/history_revert_links` | 19,858 | 19,700 within 20 days; 17,646 within 4 days |
| `silver/live_revisions` | 279,466 | |
| `silver/live_revert_links` | 18,358 | 17,818 within 4 days |
| `silver/late_reverts` | 4,350 | Namespace 0: 3,591. Class `exact`: 2,970; `inexact_undo`: 198; `method_unknown`: 1,182 |

**Revisions by editor kind** (rows of `fact_edit` by `user_kind`). History: bot 33,483; temporary 38,164; registered 223,366; unknown 3. Live: bot 31,973; temporary 36,314; registered 211,179; unknown 0.

**Targets that need no real data.** The repository's fixture scenario has 38 page-change, 7 tag and 3 revert-risk events. It must give: `page_change` 38 rows, `revert_risk` 2, `tag_events` 7, 4 capture gaps, `live_revisions` 32, `live_revert_links` 9, `live_revert_links_all` 17, `late_reverts` 5. The R6 prototype meets all of them.

## Verified building blocks

Everything in this section ran in the cloud session on made-up data. Pages R2, R3, R6 and R7 hold the code and the outputs.

### Versions that work together

| Package | Version |
| --- | --- |
| Python | 3.12.3 |
| delta-spark | 4.4.1 |
| pyspark | 4.2.0. delta-spark 4.4.1 does not accept 4.3.0. |
| deltalake (delta-rs) | 1.6.6 |
| pandas | 2.3.3 |
| pyarrow | 26.0.1 |
| polars | 2.1.0 |
| Java | OpenJDK 21. Spark needs 17 or newer. |

One environment holds all of them with no conflict, and the 30 old ingest tests pass in it (R6). The runs were on Linux. Nothing has run on macOS.

### Spark session that worked in every run

```python
import os, sys
os.environ["PYSPARK_PYTHON"] = sys.executable          # else the workers may start another Python
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

HOME = "/abs/path/to/data/spark_home"                  # keeps side files out of the working folder
b = (SparkSession.builder.master("local[2]").appName("truthlag")
     .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
     .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
     .config("spark.driver.memory", "4g")
     .config("spark.sql.shuffle.partitions", "4")
     .config("spark.sql.session.timeZone", "UTC")
     .config("spark.sql.warehouse.dir", HOME + "/warehouse")
     .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={HOME}/derby -Duser.timezone=UTC")
     .config("spark.local.dir", HOME + "/sparktmp")
     .config("spark.jars.ivy", HOME + "/ivy")
     .config("spark.ui.enabled", "false")
     .config("spark.ui.showConsoleProgress", "false"))
spark = configure_spark_with_delta_pip(b).getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
```

The first start downloads the Delta jars from Maven Central (33 jars, 87 MB, about 29 s in the lab). Later starts took about 5 s.

### Table properties

- Every table: `delta.logRetentionDuration = 'interval 3650 days'`, `delta.deletedFileRetentionDuration = 'interval 3650 days'`, `delta.enableExpiredLogCleanup = 'false'`.
- Bronze adds `delta.appendOnly = 'true'`, and limits `delta.dataSkippingStatsColumns` to the envelope columns.
- `gold/fact_edit` and `gold/fact_revert_label` add `delta.enableChangeDataFeed = 'true'`, set when the table is created.
- Resulting protocol: reader 1 and writer 2 everywhere, and writer 7 with `changeDataFeed` on the two facts. Each engine read every table the other wrote.

### Pitfalls and their fixes

| Pitfall | Fix | Seen in |
| --- | --- | --- |
| Spark's gzip reader fails on a file with no end marker. With `ignoreCorruptFiles` it silently loses the rest of the file. | Read raw files with the old Python reader, `parse_stream.read_lines` | R3 |
| delta-rs application transactions do not stop a repeated append | Check the table content before loading (D13) | R2, R6 |
| MERGE does not remove duplicates inside its source | Deduplicate the batch first | R2, R3 |
| A MERGE update that changes nothing still writes a commit and change rows | Pre-filter the source to rows that are new or changed | R3, R7 |
| In delta-rs, `a IS DISTINCT FROM b OR c IS DISTINCT FROM d` is parsed wrongly and skips real changes | Put each term in parentheses | R2 |
| Timestamp time travel follows file modification times | Address versions by number (D9) | R2, R3 |
| Spark cannot see the custom commit keys that delta-rs writes | Also store the metadata as JSON text under the key `userMetadata` | R6 |
| `SELECT ... FROM (DESCRIBE HISTORY ...)` does not parse | Look the version up in Python | R7 |
| Named SQL parameters are unbound under the Delta extension | `{placeholders}` from a whitelist (D18) | R7 |
| The classic SCD Type 2 MERGE loses versions when a page changes twice in one run | Recompute the version list and MERGE on `page_key` (D8) | R7 |
| An older `as_of` would reopen closed page versions | The runner refuses it | R7 |
| With pyarrow 26, files rewritten by a delta-rs MERGE read back as `string_view`, and string filters fail | Read through `DeltaTable.scan`, `QueryBuilder` or polars | R2, R6 |
| Spark computes dates in the session time zone | Set the session time zone to UTC, and compute `event_date` in Python | R3 |
| Spark workers start another Python version | Set `PYSPARK_PYTHON` to the driver's interpreter | R3 |
| Every Spark write costs 3 to 11 s, even on a tiny table | Few, large statements. The whole Gold run took 255 s on made-up data. | R7 |
| The old cohort files store nanoseconds, and Delta stores microseconds | Cast on load. The values are whole seconds or milliseconds, so nothing is lost. | R6 |
| A script that ends right after `to_pyarrow_table` may abort with exit code 134, although the data is complete | Read through the prototype's `delta_io.read_table`. If it happens, repeat the read. Do not reload. | R2 |
| The capture's `dt=` folder is not the event date in the test fixtures. The real capture names the folder from the publish time. | Compute `event_date` from `meta_dt` for each line | R6 |

## Current-events slice

The team's idea: pages about current events get bursts of edits, and the live view is least settled there. Page R5 compares five ways to define such pages. The plan takes the one that needs no new data, and builds it in Phase 4 as `gold/mart_el_by_burst`.

- **Definition.** A revision is in a burst when its page had 10 or more edits in the hour before it: `page_edits_prev_1h >= 10`. The column exists in both cohorts.
- **How common.** 5,866 of 295,016 history revisions (1.99%) and 7,086 of 279,466 live revisions (2.54%).
- **What is already known.** The revert rate in bursts is not higher: 5.85% against 5.98% overall in the history cohort. Whether reverts in bursts become known sooner or later is open, and that is what E(L) measures.
- **The one contrast, fixed in advance.** E(1 h) and E(1 d), burst against the rest, for each cohort. The burst groups hold 343 (history) and 439 (live) eventual reverts, so the intervals will be wide. The intervals are a stretch item: a bootstrap that resamples pages, because one page can carry a group.
- **Limits.** A burst rule also catches edit wars and vandal fights. The two cohorts count the prior hour on different clocks. The result may be "no difference", and the report should then say so.
- **Not now.** Editorial signals (the Current template, the Current events portal) and pageviews need new data pulls.

## Risks and limits

| Risk | Effect | What the plan does |
| --- | --- | --- |
| Nothing ran on the real data | A rule may meet a case the fixtures lack | Parity checks after every phase, against tables that already exist on the Mac |
| Spark may not start on the Mac. It never has in this repository. | Gold in Spark is blocked | The Spark gate in Phase 0. The fallback is a rewrite of Gold for delta-rs; only its single operations were tested (R2). |
| The 2026-10 snapshot may not be online, or its cutoff may be early | No reconciliation, or too little follow-up | Phase 5 stands alone and can be dropped. The follow-up check is one of its steps. |
| Upstream keeps only two snapshots | The raw 2026-09 file is gone when 2026-11 appears, about early December | Mirror it from the VPS in Phase 0 |
| The Mac's disk. About 21 GB free was recorded in October. | The lake does not fit | Check in Phase 0. Stop under 4 GB free. ZSTD in Bronze. |
| Steps that recompute everything (cohort tables, page versions), and the label MERGE (about 5.3 million rows per month file; the lab ran 300,000) | Slow on real data | They were timed on made-up data only. If a step takes more than 10 minutes, tell Scott before changing the design. |
| The published parse skipped files changed in its last 2 minutes | Stream parity may be off by a few events at the cut | Use the exact cut from `_SUCCESS_parsed.json` (Phase 2). If a difference remains, list it and decide with Scott. |
| An event that the capture delivers late could move the start of a page version | A `page_key` stored in `fact_edit` would change | Not tested. Phase 4 step 6 removes the case of events that are merely newer than `as_of`. Report any key that disappears between two runs. |
| Two writers on one table | Delta gives no guarantee on a local file system | One writing process per table at a time |
| Time | Four days, with the report and slides in the same window | The cut order under **Build phases** |

What this plan does not cover: the report and slide text, the team's split of work, and any change to the capture.

## Open decisions for Scott

1. **Deadline.** The tracker says the report, slides and code are due Nov 17. At what time?
2. **D1.** Is the hybrid acceptable for the course: delta-rs for Bronze and Silver, Spark SQL for Gold?
3. **D3 and D4.** Are the tiers right? Is "Kafka was not built, and here is why" acceptable in the report?
4. **D5.** Is the 2026-10 snapshot online, and may the Mac download it? Will you mirror the raw 2026-09 file from the VPS?
5. **D16.** The branch name, the tag name for the submitted EC HW2 state, and where the GenAI log for the final project lives. `ec-hw2/genai/PROMPTS.md` is the existing pattern.
6. **The Mac.** Java version, free disk and RAM. Are `data/parsed/` and `data/tables/` still the published `data-v2` state?
7. **The capture.** Do the two units still run? The plan loads whatever `data/raw/` holds after your rsync.
8. **Hypotheses.** `docs/schema_and_warehouse.md` refers to H1 to H4 without defining them. The glossary in `ec-hw2/GLOSSARY.md` (section 6) lists the proposal's "E0-E7 experiments" as final-project work, and records that the proposal used a 30-day horizon. The proposal itself is not in the repository, so none of these definitions were read. Which of them must the lake answer? Phase 4 covers H4, as far as the schema document describes it.
9. **Team split.** Which phases, if any, go to Tingyu, Wanru or Zhenni? Phase 6 and the stretch items work from the Gold tables alone, once those are shared.

## How to review

For agents and teammates. The aim is to find what is wrong or missing before the build starts.

- **Check claims against their sources.** Published numbers come from `ec-hw2/report/FACTS.md` in the repository. Test results come from pages R1 to R7.
- **The most useful checks.**
    1. Do the build phases miss a rule from `ec-hw2/config.py` or `ec-hw2/DATA_MODEL.md`?
    2. Does any step break a rule in **Rules**?
    3. Is any check in a phase impossible to run with the data named in **Current state**?
    4. Does the Gold SQL on page R7 match the measure definition on the design sub-page?
    5. Is a decision missing from **Design decisions**?
- **What cannot be checked from Notion.** The real data, and anything on Scott's Mac or the VPS. Say so instead of guessing. The tracker's rule is to cite Mac files by path and date, and not to claim they were checked.
- **Where to write.** Append a dated entry to **Review log** at the end of this page: who you are, what you checked, what you could not check, and each finding with its evidence. Do not edit the plan text.
- **Do not act on the plan.** Reviewing is reading. The build starts only when Scott starts it.

## Hand-off prompt for the build session

For a new Claude Code session on Scott's Mac, opened in the repository folder. The session needs the hand-off kit, unpacked outside the repository, for example in `~/truthlag_handoff_kit/`. Without the kit, the same files are on the research pages: R6 and R7 hold the `etl` package, its test, the Gold SQL and the runner, and R8 holds the check scripts.

```text
You are building the TruthLag lakehouse on Delta Lake in this repository (scottn66/truth-lag), on the machine that holds the data. Work from the plan. Do not redesign it.

Read first, in this order:
1. The plan: PLAN.md in the hand-off kit, or the Notion page "DATA 226 Group 9 — TruthLag on Delta Lake: build plan and handoff (Nov 13, 2026)". Then the table catalog: LAKE_DESIGN.md, or the sub-page "Lake design reference".
2. In the repository: ec-hw2/STYLE.md, ec-hw2/config.py, ec-hw2/DATA_MODEL.md, ec-hw2/ingest/README.md, docs/schema_and_warehouse.md.
3. The two prototypes: the folders proto_fixture_pipeline/ and proto_gold_sql/ in the kit, or the research pages R6, R7 and R8. They passed on made-up data in another session. Nothing has run on the real data yet.

Rules that always hold:
- Never stop, restart or edit the capture units on the VPS. Never open an EventStreams connection. Never run ssh or rsync unless Scott tells you to in this session, and never with --delete.
- Never delete or change anything under data/raw/ or data/history/. Never commit anything under data/.
- Never write into data/parsed/ or data/tables/: they hold the only copy of the published tables. Never run the old scripts as scripts, and never call their run() functions without a temporary output folder.
- New input files go to data/history_raw/ and data/history_slim/, never into data/history/.
- Treat ec-hw2/ as frozen: import from it, do not edit it.
- New folders must not be named ingest, config or tests.
- One writing process per Delta table at a time. Never run VACUUM.
- Do not push, open a pull request or send any message. Scott does that.
- Human editor names never go into a committed file. Use the pseudonyms.
- Keep the GenAI disclosure entry up to date as you work.
- If a check fails, stop and report the numbers. Never change a rule, a window or a threshold to make a number match.

How to work:
- Start with Phase 0 of the plan. It needs Scott's answers to "Open decisions for Scott". Ask him for the missing ones in one message.
- Then one phase at a time. Each phase ends with its checks. Report the results as a table (check, expected, got) before you start the next phase.
- Start from the prototype code. Adapt it; do not rewrite it.
- Record each phase's results, run times and table sizes in the progress file that Scott names.
- If a step takes more than 10 minutes on the real data, or free disk falls under 4 GB, stop and tell Scott before you change the design.
- Stay inside the tiers of "Deadline and scope". Stretch items come only after Phase 6.

Your first message to Scott: the Phase 0 check results (git state, Python, Java, free disk, RAM, which data folders exist, whether data/parsed is the published data-v2 state) and the decisions you still need from him.
```

## Provenance

- **Written by:** Claude (Claude Code, cloud session) with Scott, Nov 13, 2026. It is a draft. No teammate or instructor has reviewed it.
- **Repository state read:** `scottn66/truth-lag`, default branch at `8e28012` (Oct 29, 2026). The session changed no file in the repository.
- **How the evidence was made:** seven agents in that session. R1, R4 and R5 read the repository and documentation. R2 and R3 ran each engine's building blocks. R6 and R7 built and tested the two prototypes. Every run used made-up data. Three more agents then reviewed this plan against the repository, the reports and the prototype code, and the plan was revised (see **Review log**).
- **Checked by no one yet:** anything on the Mac or the VPS; whether the capture still runs; whether the 2026-10 snapshot is online; the time of day of the deadline.
- **GenAI disclosure.** This plan, the research pages and both prototypes were produced with generative AI. The project's rule asks for a log entry for each piece of AI-assisted work. Suggested text: "The plan and the prototype code for the Delta Lake lakehouse were drafted with Claude Code on Nov 13, 2026. The prototypes were tested on synthetic data only. The code was then run and checked on the real data by (name) on (date)."

## Review log

Add entries below, newest last: date, reviewer, what was checked, what could not be checked, findings with evidence.

- **2026-11-13, internal review by the session that wrote the plan.** Three review agents, each with one task: can a fresh session carry out every step; do the numbers and claims match their sources; does the plan match the prototype code. A second agent checks each finding; the author applied the fixes that the evidence supports without waiting for every verdict.
    - Checked: this page and the design sub-page against `ec-hw2/config.py`, `ec-hw2/DATA_MODEL.md`, `ec-hw2/report/FACTS.md`, the result files, the old pipeline code, the reports R1 to R7 and the prototype code. About 290 numbers and claims were traced or recomputed. Several findings were tested by running the prototypes on the fixtures.
    - Could not check: the real data, the Mac, the VPS, the shape of real events, anything at real size.
    - Result: every published number matched. 42 findings, about 30 distinct, all led to a change. The main ones:
        1. New History files would have gone into `data/history/`, where the September file of snapshot 2026-10 has the name of the 2026-09 file that the old code reads. They now go to `data/history_raw/` and `data/history_slim/`.
        2. No rule protected `data/parsed/` and `data/tables/`, the only copy of the parity reference. There is now a rule and a copy step.
        3. A default `as_of` on the newest page-change event changed 1 row of `late_reverts` on the fixtures. The prototype's default stays.
        4. The Gold lab runner records an error and goes on. Phase 4 now asks for a new entry point that stops.
        5. The delta-rs fallback for Gold was called tested. It is a rewrite, and the plan now says so.
        6. The guard between the cohort build and Gold was undefined. It is now `data/lake/_runs/latest.json`.
        7. The history cohort is built once per snapshot from the files in `data/history/`, which the old code can read. The catalog had named lake tables that it cannot read.
        8. Tests for Gold and for the new history code are now steps of the plan.
        9. The page dimension would have missed pages renamed after their last cohort edit. The view now also reads the dump's current title.
        10. The replay no longer plots E(L) for days with incomplete follow-up.
        11. The environment lacked the packages for the notebook and for the pseudonyms.
    - Limit: the reviewers ran in the same session that wrote the plan. This entry does not replace a review by another agent or a person.
