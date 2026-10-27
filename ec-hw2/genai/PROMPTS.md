# GenAI record for EC HW2 (word for word)

This folder is our evidence for the report's **Mandatory GenAI Q&A**. It also covers the spec's bonus item: "LLM used to draft Cypher/aggregations, documented with prompts".

- **Tool:** Claude Code (Anthropic), running in VS Code.
- **Model:** Claude Opus 5.5 (`claude-opus-5-5`).
- **Who prompted:** Scott Nelson, on 2026-10-23 and 2026-10-24 (PT).
- **Other members:** each member adds their own AI use (including translators and grammar tools) to the GenAI table in the report.

## 1. What is in this folder
| File | What it is |
|---|---|
| `PROMPTS.md` (this file) | Scott's own prompts and decisions, word for word |
| `APPROVED_PLAN.md` | The plan Claude wrote and Scott approved (after 3 rounds of changes) |
| `workflows/plan_verify_facts.js` | Planning step: 5 read-only agents that checked facts (dump schema, EventStreams, Atlas, Neo4j, this Mac) |
| `workflows/plan_critique.js` | Planning step: 4 read-only agents that tried to find problems in the draft plan |
| `workflows/build.js` | The build: the exact prompts given to the 9 build agents |
| `prompts/build_<part>.md` | The same 9 build prompts, one file each, generated word for word from `workflows/build.js` |
| `workflows/verify.js` | The review step (2026-10-24): the exact prompts given to 7 independent reviewers who tried to refute the build |
| `prompts/verify_<lens>.md` | The same 7 review prompts, one file each, generated word for word from `workflows/verify.js` |
| `prompts/fix_common.md` and `prompts/fix_<part>.md` | The fix step (2026-10-24): the prompts given to the fix agents after the review (Claude Code, Agent tool). Every fix agent got `fix_common.md` plus its own part |
| (no file) | VPS capture and filter scripts (`ingest/vps/`): made in an earlier Claude Code session directed by Scott; prompts not kept |

The prompts that **drafted the MongoDB aggregations** are in `prompts/build_mongo.md`. The prompts that **drafted the Cypher queries** are in `prompts/build_neo4j.md`.

## 2. Scott's prompts (word for word)

### Prompt 1 (2026-10-23)
The proposal document was attached to this prompt. It is in the course folder, not in this repo.
```text
https://github.com/scottn66/truth-lag
This is the current github associated with the Graduate level Big Data & Warehouse Technologies project.
Initial checkpoint for the project is specified in the EC_HW2_TruthLag_Spec.md
All notebooks, changes, documentation, and progress must be understandable for all group-members (assume semi-technical background and potential language barrier) to allow for smooth progress and unity.
project proposal included from submission with notable grading comments: (6/10 for motivation: Text appears to be copy pasted from chatgpt, Literature Survey 7/10 Please refer to more papers, Methodology 9/10 no comment, technical difficulty 9/10 no comment, Novelty 8/10 Novelty is well argued, but it could have been still more better to substantiate the gap, Impact 9/10 impact remains somewhat general and lacks a concrete end-user scneario. Abstract, Deliverables, Team members and their roles, Relevance to the course, and Heilmeier catechism all got full marks.
/workflow-authoring
```

### Decisions Scott made when Claude asked (2026-10-23)
| Question from Claude | Scott's answer |
|---|---|
| How much should Claude build vs. leave for teammates? | Full MVP; owners verify, do the UI steps and write their sections in their own words |
| How to run the databases on this Mac? | Colima + Docker CLI |
| Which data design? | Two cohorts + the late-revert join (see the answer below) |
| Who owns which part? | Leave as TBD (the team assigns roles) |

Scott's full answer on the data design (word for word):
```text
Pick the first option, two cohorts plus the late-revert join. My earlier plan was the same design minus that join, and the join makes it stronger.
Why it wins:
The September cohort does the grading work. It has full labels and the reverting user, which the Neo4j revert graph needs, and it backs all of the MongoDB aggregations.
The October cohort is real live data. It has the live counters and the stream's revert tags, so the speed layer isn't simulated.
The join is the Truth Lag idea in miniature. It matches October mw-reverted events against September rev_ids. The 2026-09 snapshot was taken at the end of September, so it still marks those edits as not reverted. The join catches exactly the cases where the dump's answer was wrong because it came too early. That's a clean finding, and the same code scales up in November.
The other two options each drop one of the sources the spec names.
Two caveats for Claude:
The join will be small. Most reverts happen within hours, so reverts of edits five or six weeks old are rare. Expect a handful to a few hundred matches, not thousands. Report it as a case study with counts, not a statistical result, and keep the HW2 grade riding on the two cohorts.
Back up the live data now. EventStreams only keeps a limited replay window. My notes say about 7 days, and possibly up to 31. Oct 16 may already be gone or close to it, and Oct 20–22 won't be available much longer. Start a replay for Oct 20–22 tonight on both revision-create and revision-tags-change, save it to Parquet or ndjson, and from then on the data no longer depends on the stream's retention.
```

### Plan changes Scott asked for (2026-10-24, word for word)
1.
```text
Update the plan only; do NOT rebuild the capture on the Mac. Changes since tonight:
Pre-flight: macOS update installed and restarted (done). Keep only "turn off automatic updates until Oct 30." Remove stale swap/staged-update facts.
Step 0: capture now runs on my Hostinger VPS (ssh vps-coin, /opt/truthlag) as systemd units truthlag-capture-a (page_change.v1 + revert_risk, since 2026-10-19T23:00Z) and truthlag-capture-b (revision-tags-change, since 2026-10-17T00:00Z): gzip ndjson by meta.dt, wb per session, atomic Last-Event-ID state. Drop capture.sh/caffeinate and the Mac catch-up disk math. Build agents never stop or restart the VPS units.
Step 1: the VPS downloads and filters the Sep dump into a Sep 8–10 ns0 file plus a slim all-September file for the reverter join. Both are rsynced to the Mac over the public IP. Adapt parse_history.py and parse_stream.py to those exact paths and schemas (put them in config.py).
Step 5: refresh_live.sh starts with an rsync from the VPS.
MongoDB and Neo4j stay on the Mac in Colima. Nothing heavy runs on the VPS (7.8 GB RAM, no swap). Add a VPS memory risk.
Note that Kafka belongs to the final project, not HW2.
Update Verification → Capture to check the VPS units.
```
2.
```text
Three small plan fixes, no other changes, and don't touch the VPS:
Pin the paths in Step 0 and config.py: RAW_STREAM_DIR=/opt/truthlag/data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-<session>-<n>.ndjson.gz, history at /opt/truthlag/data/history/. Parsers key on dt=.
In Verification → Capture, apply "within 5 min of now" only after catch-up, and compare file counts on closed files only (skip files changed in the last 2 min).
rsync via vps-coin (public IP, not the Tailscale alias) with -az --partial, never --delete.
```
3.
```text
Small plan fixes only, and don't touch the VPS:
Pin the exact stream dirs in config.py: mediawiki.page_change.v1, mediawiki.page_revert_risk_prediction_change.v1, mediawiki.revision-tags-change.
Pin the history files: enwiki_rev_ns0_2026-09-08_10.parquet (cohort) and enwiki_rev_all_2026-09_slim.parquet (slim). Read the Parquet copies. All columns are strings, so cast types explicitly in parse_history.py.
NRestarts baseline: capture-a=2, capture-b=1. Flag any increase.
Restore the fact that Oct 19 23:00Z leaves replay at about Tue Oct 27 03:00 PT, as a risk (already captured, but keep the raw files safe).
Never use timeout; it isn't on macOS.
```
(The VPS IP address is removed from this record on purpose.)

### Prompts in other sessions (2026-10-24, word for word)
Session `eefd88ce`, 08:55 UTC:
```text
Yes: review the build agents' issues and shared-change requests, then run the 7-agent verify workflow from the approved plan.
```
That session did not act on it, because this session was already running the review.

Session `eefd88ce`, 09:00 UTC:
```text
Well, do I need to setup mongoDB or Neo4j? I just setup an Atlas cluster and am looking at the username and password user credentials.
```
Scott also pasted a status message from the build session (VS Code output, about 20 lines): the changes since the build, and two notes from the build. It is left out here.

### Prompts in this session (2026-10-24, about 09:30 UTC, word for word)
1.
```text
Atlas settings are in ec-hw2/.env.atlas. Load the history cohort into Atlas and check the counts match notebook 02.
```
2.
```text
Fix all confirmed reviewer findings: make the top-contested comparison use the same method in all three engines, regenerate the notebook summary boxes from FACTS, put the cohorts on the same time-to-revert horizon or label the difference, run PageRank to convergence, fix the citation wording, and flag range_size as a lower bound. Then commit in logical pieces, push the ec-hw2 branch, and open the draft PR. Don't change the VPS units.
```

## 3. What the AI did, and what people must check
- **Claude Code wrote:**
  - the plan
  - `config.py`, `DATA_MODEL.md`, `STYLE.md` and `ingest/history_columns.py`
  - the workflow scripts
  - through its build agents: all scripts, queries, tests, notebooks, guides, the literature list and the report *skeleton*
- **The VPS capture and filter scripts** (`ingest/vps/`) were made in an earlier Claude Code session directed by Scott. The prompts of that session were not kept. Scott ran the scripts on the VPS.
- **The review** (`workflows/verify.js`, `prompts/verify_*.md`) and **the fixes** (`prompts/fix_*.md`) were done by Claude Code agents on 2026-10-24. See section 5.
- **Claude Code did not write the narrative report text.** Each owner writes their section in their own words.
- **People must check:**
  - every number in their notebook against `report/FACTS.md`
  - every paper they cite (open the DOI link)
  - every query result they put in the report

## 4. Errors that review caught during planning
The planning review agents caught these before any code ran:
- The first revert-range join used an exact-id match. Revert ranges need a page-level range join.
- The "top contested pages" ratio tied at 1.0 and had no tie order.
- Two of the six comparison queries were missing.
- The live time-to-revert used a different clock (`meta.dt`) from the dump (revision time).
- The GitHub invites had expired.
- Writing raw files by appending could make them unreadable after a crash.

## 5. Errors the review caught (2026-10-24)
After the build, 7 independent AI reviewers (Claude Code Workflow, `claude-opus-5-5`, `workflows/verify.js`) tried to refute it. Each reviewer had one lens: `verify:etl`, `verify:mongo`, `verify:cypher`, `verify:comparison`, `verify:readability`, `verify:coverage` and `verify:citations`. They reported 69 findings: 4 high, 32 medium and 33 low. Some findings appear in more than one lens. The full list, with evidence, is in `data/verify/REVIEW_FINDINGS.txt` (on Scott's Mac, not committed).

Below are the high and medium findings, one line each. "Changed" is what the fix step (`prompts/fix_*.md`) asked for. The commits show the final state.

| # | Level | Error | Caught by | Changed |
|---|---|---|---|---|
| 1 | high | The top-contested timing compared different work: MongoDB counted edits only for the candidate pages, SQL and Cypher for every page. | verify:comparison | SQL and Cypher now do the same steps as MongoDB. The rank column is added in Python for all three. |
| 2 | high | The notebook top boxes (notebooks 04 and 05) showed wrong headline numbers, and the FACTS check could not catch it. | verify:readability | The summary boxes are regenerated from `report/FACTS.md`. |
| 3 | high | Nothing of EC HW2 was on GitHub: no commit, no pushed branch, no data release. | verify:coverage | Commit, push of `ec-hw2`, draft pull request and data-v1 release follow the fixes. The README has a status line until then. |
| 4 | high | The UI deliverables (Atlas Charts, Atlas and Neo4j screenshots) did not exist yet. | verify:coverage | Still owner work (Sun 2026-10-25 to Tue 2026-10-27). `check_setup.py` lists every missing PNG by name, and the skeleton has a slot for each. |
| 5 | medium | `range_size` undercounts reverts whose range starts before the capture, which biases the ≤15 / >15 tag check. | verify:etl | New flag `range_complete`. The tag shares use complete ranges only. `range_size` is documented as a lower bound. |
| 6 | medium | Time-to-revert shares were compared across cohorts with different horizons (20 days vs 4 days; the live cohort is also censored). | verify:etl, verify:mongo | Mongo Q3 and `chart_q3_time_to_revert` have a `history_4d` series. The guides and the skeleton compare the live cohort only with it. |
| 7 | medium | Expected numbers in the guides and notebooks were stale ("You should see" lines, chart checks). | verify:mongo, verify:readability | The docs name FACTS keys instead of numbers. The notebook text is regenerated from FACTS. |
| 8 | medium | The Charts guide did not use the stored sort fields and told users to make calculated fields with the same names. | verify:mongo | The guide uses `bucket_sorted` and `wait_sorted`. A calculated field (with a new name) is only a fallback. |
| 9 | medium | Cypher Q2 PageRank did not converge (it stopped after 20 iterations). | verify:cypher | `maxIterations: 200`, `tolerance: 1e-7`, and `run_cypher.py` stops if PageRank does not converge. |
| 10 | medium | The pseudonyms were an unsalted SHA-1 of a small key space, so they could be reversed in seconds. | verify:cypher, verify:mongo | HMAC-SHA256 with `ALIAS_SECRET` from `ec-hw2/.env`, a fixed 10 hex digits, and a collision check. |
| 11 | medium | REVERSE PageRank called an editor with 5 reverts on one page a "most central reverter". | verify:cypher | The by-degree list answers "who reverts the most". PageRank is described as "reverts editors who are themselves active reverters". |
| 12 | medium | Mutual-reverts timing: Neo4j read edges built by the loader, while MongoDB and SQL aggregated at query time. | verify:comparison | Stated in `comparison.md`. An extra pre-aggregated SQLite row is timed. |
| 13 | medium | Timings were labelled "final" and "otherwise idle" although the idle check had failed. | verify:comparison | `--final` refuses on a busy Mac, and the measured load is written into `comparison.md`. |
| 14 | medium | The run-to-run noise was larger than the Neo4j-SQLite gap, and FACTS had two FINAL times for the same queries. | verify:comparison | 3 rounds x 7 runs, median with min-max. An engine is "faster" only when the ranges do not overlap. |
| 15 | medium | The lines-of-code headline depended on the JSON layout. | verify:comparison | Code characters next to lines of code; no lines-of-code headline. |
| 16 | medium | The modeling-pain scores were written by Claude Code, but labelled the team's judgment and FINAL. | verify:comparison, verify:coverage | Moved to `comparison/pain.csv`, labelled "draft by Claude Code". The Comparison+viz owner re-scores them. |
| 17 | medium | The MongoDB comparison inputs include the live cohort, and the live refresh did not re-run `compare.py`. | verify:comparison | `compare.py` is in `refresh_live.sh`; new index `revert_links {cohort, page_id}`; a note in `comparison.md`. |
| 18 | medium | Required report sections had no owner (Data + links, Architecture, Reuse note). | verify:readability | Owners added in README, PROGRESS and the "Who did what" table. |
| 19 | medium | The README run-book row counts were stale. | verify:readability | One line per step that names the `_SUCCESS` file and the FACTS keys. |
| 20 | medium | ATLAS_SETUP said that Atlas holds real editor names, and it pointed to the wrong step. | verify:readability | It now says pseudonyms; "step 15" is now "step 20". |
| 21 | medium | The repo-root README Quickstart told readers to open EventStreams from a laptop. | verify:readability (also verify:coverage) | A warning line under the HW2 banner. |
| 22 | medium | Key terms were missing from the GLOSSARY, and "Q1/Q2" meant two different things. | verify:readability | New glossary terms; the research questions are now RQ1 and RQ2. |
| 23 | medium | GLOSSARY example numbers came from the raw file and did not match FACTS. | verify:readability | FACTS keys, or the label "raw file, before clean-up". |
| 24 | medium | The report skeleton had no place for most screenshots, and Mongo Q5 had no screenshot at all. | verify:coverage | A "Figure not made yet" slot for every guide PNG, and a new Mongo Q5 step (`mongo_q5_local.png`). |
| 25 | medium | "23 new papers, none cited in the proposal" was false: ORES is cited in the proposal draft. | verify:coverage | ORES moved to [P3]; the counts are fixed (21 peer-reviewed papers and 1 magazine column). |
| 26 | medium | The Novelty prompt asked for search query strings, but there was no keyword search. | verify:coverage, verify:citations | The prompt describes the true method: an AI-suggested list plus snowballing, each paper checked. |
| 27 | medium | The GenAI record was not complete, and some labels were wrong. | verify:coverage | Prompts added word for word; `verify_*.md` headers fixed; "3 rounds"; rows for the VPS scripts, the review and the fixes. |
| 28 | medium | [13] is a magazine column, not a peer-reviewed paper. | verify:citations | Labelled; the counts are fixed. |
| 29 | medium | "Numbers to compare with ours" put our numbers next to a different group: [1]'s 2.8 minutes is for mass deletions only. | verify:citations | The all-content median (90.4 minutes) and the 20-day limit of our T are added. |
| 30 | medium | [3] and [5] measured hour of day in local time, but were cited for Mongo Q1 (UTC hours) with no warning. | verify:citations | A caveat in both rows. |

The 33 low findings are in the same file. The fix prompts asked to fix them where the fix is small; the commits show which ones were fixed.

## Run log (added 2026-10-27, PT)
These are records of pipeline runs, not prompts. Scott asked for them to be logged here on 2026-10-27. The runs were checked against the `_SUCCESS_*.json` files, `data/logs/` and `FACTS.md`.

1. **`ec-hw2/ingest/parse_history.py`** ran on 2026-10-24 at 2:46 AM PT and took 7.5 s. It wrote 295,016 revisions and 19,858 revert links to `data/tables/`: `history_revisions.parquet`, `history_revert_links.parquet`, `history_summary.json` and `_SUCCESS_history.json`. The history cohort is final. The `data-v1` tags inside these files are only labels.
2. **`ingest/vps/filter_history.py`** ran on the VPS. It produced the two cut-down Parquet files: the Sep 8–10 namespace-0 file (300,564 rows, 78 columns) and the slim September file (5.27M rows, 12 columns). They reached the Mac on 2026-10-23 at 9:57 PM PT, together with `filter_stats.json`. These are final too.
3. **`ec-hw2/refresh_live.sh`** ran on 2026-10-27, started by Grok Bot (226 · Big Data Warehouse) at Scott's request. All 11 steps finished without errors. `DATA_VERSION` changed to `data-v2`. There are 1.23M live edits and 4,350 late-revert documents, and every live edit now has at least 4 days of follow-up. The Neo4j mutual-reverts query went from 53 ms to 261 ms, possibly because of a cold cache. `compare.py --final` and `release_data.sh` have not been run yet, and the changes are not committed.
