# Progress: EC HW2

Start page: [README.md](README.md). Words: [GLOSSARY.md](GLOSSARY.md).
Owners are not chosen yet. When you claim a role, write your name in the "Done by" column of your tasks.

**On this page**
1. [Never cut, and cut first](#1-never-cut-and-cut-first)
2. [Schedule (PT)](#2-schedule-pt)
3. [Checklist per role](#3-checklist-per-role)
4. [Who did what](#4-who-did-what)
5. [Personal observations](#5-personal-observations)
6. [Daily log](#6-daily-log)
7. [After any restart (Scott's Mac)](#7-after-any-restart-scotts-mac)

---

## 1. Never cut, and cut first

**Never cut** (the grade depends on these):
- Mongo Q1-Q5
- Cypher Q1-Q5
- the 3-engine comparison (MongoDB, Neo4j, SQL)
- 2 or more Atlas Charts
- the screenshots
- the criteria map
- the GenAI Q&A
- grader access to the repo

**Cut first**, in this order, if we run out of time:
1. `--follow` (the live demo mode of `speed_layer.py`)
2. late-revert detail (keep only the counts)
3. risk deciles
4. the sharding demo (keep the explanation in `scaleout/SHARDING.md`)
5. GDS (use plain Cypher instead)
6. shrink the live cohort (to the captured hours only)

---

## 2. Schedule (PT)

| When (PT) | What | Who |
|---|---|---|
| Sat 2026-10-24 12:00 | Roles claimed; GitHub invites accepted | everyone |
| Sat 2026-10-24 | Atlas cluster created (done by Scott); all 4 invited as Project Owner; history cohort loaded; `check_setup.py` run on every laptop | Scott; Data+MongoDB; Scott's Mac |
| Sat 2026-10-24 | Code committed, branch `ec-hw2` pushed, draft pull request opened, data-v1 released | Scott's Mac |
| Sun 2026-10-25 | Verify the FINAL numbers; take screenshots; literature notes | every role |
| Mon 2026-10-26 20:00 | Neo4j screenshots done | Neo4j |
| Mon 2026-10-26 after 5:05 PM (2026-10-27 00:05 UTC) | Live refresh (`refresh_live.sh`), then data-v2 | Scott's Mac |
| Tue 2026-10-27 20:00 | Charts and all sections done | Comparison+viz (charts); every role (sections) |
| Wed 2026-10-28 18:00 | Integrated Google Doc | Report+GenAI |
| Wed 2026-10-28 | Merge the pull request, tag `ec-hw2-submitted`, give the grader access to the repo | repo owner |
| **Thu 2026-10-29 12:00** | **Internal submit** (a named submitter and a backup) | Report+GenAI + backup |
| **Thu 2026-10-29 4:29 PM** | **Canvas deadline** | - |

The live labels are final at 2026-10-27 00:05 UTC, which is Mon 2026-10-26 5:05 PM PT.
Numbers that depend on the live cohort are PROVISIONAL until then.

---

## 3. Checklist per role

How to use it: change `[ ]` to `[x]`, and write your name and the date (YYYY-MM-DD).
Add a link to a commit, a file or a PR comment.
"Verify" means: check the numbers against `report/FACTS.md`, then approve the pull request and list the numbers you checked.

### Data+MongoDB
| Role | Task | Status | Done by (name) | Date | Link |
|---|---|---|---|---|---|
| Data+MongoDB | Claim the role in the group chat (by Sat 2026-10-24 12:00 PT) | [ ] | | | |
| Data+MongoDB | Run `check_setup.py`, or read the notebooks on GitHub | [ ] | | | |
| Data+MongoDB | Verify notebook 01 (data counts, filters, basic checks) | [ ] | | | |
| Data+MongoDB | Verify notebook 02 (the 5 pipelines and their results) | [ ] | | | |
| Data+MongoDB | Accept the Atlas invite as Project Owner. Scott created the project and cluster on 2026-10-24 (`guides/ATLAS_SETUP.md`, part A) | [ ] | | | |
| Data+MongoDB | Verify the Atlas load (counts in Atlas = counts in notebook 02) | [ ] | | | |
| Data+MongoDB | Atlas screenshots: free-tier cluster page, one document, Indexes tab | [ ] | | | |
| Data+MongoDB | Run Mongo Q1-Q4 in Data Explorer > Aggregations, with screenshots | [ ] | | | |
| Data+MongoDB | Mongo Q5 screenshot from the local MongoDB (`mongo_q5_local.png`; Atlas has no live cohort) | [ ] | | | |
| Data+MongoDB | Upload the screenshots to `ec-hw2/results/figures/` | [ ] | | | |
| Data+MongoDB | Write "Data + links", the Mongo section and "Answer to RQ1" in your own words | [ ] | | | |
| Data+MongoDB | Literature batch: 1-2 sentences per paper | [ ] | | | |
| Data+MongoDB | Your GenAI row, and 2-3 dated observations (below) | [ ] | | | |
| Data+MongoDB | Approve the pull request and list the numbers you checked | [ ] | | | |

### Neo4j
| Role | Task | Status | Done by (name) | Date | Link |
|---|---|---|---|---|---|
| Neo4j | Claim the role in the group chat (by Sat 2026-10-24 12:00 PT) | [ ] | | | |
| Neo4j | Run `check_setup.py`, or read the notebooks on GitHub | [ ] | | | |
| Neo4j | Verify notebook 03 (the graph counts and the 5 Cypher queries) | [ ] | | | |
| Neo4j | Neo4j Browser screenshots: the 5 Cypher query results and `CALL db.schema.visualization()` (`guides/NEO4J_SCREENSHOTS.md`) | [ ] | | | |
| Neo4j | Graph screenshots: mutual-revert pairs, one contested page, the largest Louvain community (pseudonyms only) | [ ] | | | |
| Neo4j | Upload the screenshots to `ec-hw2/results/figures/` (by Mon 2026-10-26 20:00 PT) | [ ] | | | |
| Neo4j | Write the Neo4j section and "Answer to RQ2" in your own words | [ ] | | | |
| Neo4j | Literature batch: 1-2 sentences per paper | [ ] | | | |
| Neo4j | Your GenAI row, and 2-3 dated observations (below) | [ ] | | | |
| Neo4j | Approve the pull request and list the numbers you checked | [ ] | | | |

### Comparison+viz
| Role | Task | Status | Done by (name) | Date | Link |
|---|---|---|---|---|---|
| Comparison+viz | Claim the role in the group chat (by Sat 2026-10-24 12:00 PT) | [ ] | | | |
| Comparison+viz | Run `check_setup.py`, or read the notebooks on GitHub | [ ] | | | |
| Comparison+viz | Verify notebook 04 (the 3-engine comparison: same results, times, lines of code) | [ ] | | | |
| Comparison+viz | Verify notebook 05 (the truth-lag preview; PROVISIONAL until after Mon 2026-10-26 5:05 PM PT, which is 2026-10-27 00:05 UTC) | [ ] | | | |
| Comparison+viz | Check the sharding demo (`results/sharding.md`, `scaleout/SHARDING.md`) | [ ] | | | |
| Comparison+viz | Atlas Chart 1: Mongo Q1, revert rate by hour of day and user kind (`guides/ATLAS_CHARTS.md`) | [ ] | | | |
| Comparison+viz | Atlas Chart 2: Mongo Q3, time to revert (use the `history_4d` rows to compare with the live cohort) | [ ] | | | |
| Comparison+viz | Optional: the Mongo Q5 chart, after the live refresh | [ ] | | | |
| Comparison+viz | Save the charts as PNG and upload them to `ec-hw2/results/figures/` | [ ] | | | |
| Comparison+viz | Re-score the modeling pain: the scores in `comparison/pain.csv` are drafts by Claude Code. Write your scores and your name in `scored_by` | [ ] | | | |
| Comparison+viz | Write "Comparison top 5" and "Impact" in your own words | [ ] | | | |
| Comparison+viz | Literature batch: 1-2 sentences per paper | [ ] | | | |
| Comparison+viz | Your GenAI row, and 2-3 dated observations (below) | [ ] | | | |
| Comparison+viz | Approve the pull request and list the numbers you checked | [ ] | | | |

### Report+GenAI
| Role | Task | Status | Done by (name) | Date | Link |
|---|---|---|---|---|---|
| Report+GenAI | Claim the role in the group chat (by Sat 2026-10-24 12:00 PT) | [ ] | | | |
| Report+GenAI | Verify README, GLOSSARY (also the Chinese columns), the report skeleton and the criteria map | [ ] | | | |
| Report+GenAI | Sun 2026-10-25: make the Google Doc from `report/REPORT_SKELETON.docx` | [ ] | | | |
| Report+GenAI | Write Abstract, Motivation + related work, Technical difficulties, Key learnings (with everyone's notes) | [ ] | | | |
| Report+GenAI | Write the Architecture caption + walkthrough, and the Reuse note (rewrite or sign its drafted sentences) | [ ] | | | |
| Report+GenAI | Complete the GenAI Q&A table (one row for each of the 4 members) and the "Who did what" table | [ ] | | | |
| Report+GenAI | Wed 2026-10-28 18:00 PT: the integrated Google Doc | [ ] | | | |
| Report+GenAI | Before submitting, search the report and repo for `TBD`, `[OWNER` and `TODO` | [ ] | | | |
| Report+GenAI | Make the final PDF and upload it to `ec-hw2/report/` | [ ] | | | |
| Report+GenAI | Thu 2026-10-29 12:00 PT: submit on Canvas (name the submitter and a backup) | [ ] | | | |
| Report+GenAI | Literature batch: 1-2 sentences per paper | [ ] | | | |
| Report+GenAI | Your GenAI row, and 2-3 dated observations (below) | [ ] | | | |
| Report+GenAI | Approve the pull request and list what you checked | [ ] | | | |

---

## 4. Who did what

Use these exact verbs:
- **built**: wrote the code or the file
- **verified**: checked the numbers
- **created in UI**: made it in Atlas, Neo4j Browser or Google Docs
- **wrote**: wrote the text in your own words

List every AI tool you used, including translators. Write "none" if you used none.

| File or section | Built by | Verified by (name, date) | Created in UI by | Written by | AI tools used (including translators) or none |
|---|---|---|---|---|---|
| VPS capture copy (repo-root `ingest/vps/`) | Claude Code, in an earlier session directed by Scott (copied read-only from the VPS) | | | | Claude Code (claude-opus-5-5) |
| `config.py`, `DATA_MODEL.md`, `STYLE.md`, `ingest/history_columns.py` | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `ingest/parse_history.py` (history cohort) | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `ingest/parse_stream.py`, `label_live.py`, `late_reverts.py` (live cohort) | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `load_mongo.py`, `speed_layer.py`, `queries/mongo/` (Mongo Q1-Q5) | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `export_graph.py`, `load_neo4j.py`, `queries/cypher/` (Cypher Q1-Q5) | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `load_sql.py`, `queries/sql/`, `comparison/compare.py` | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `scaleout/` (sharding demo, `SHARDING.md`) | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `guides/` (Atlas, Atlas Charts, Neo4j screenshots) | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `report/references.md` (literature) | Claude Code | | | | Claude Code (claude-opus-5-5), web search |
| `README.md`, `GLOSSARY.md`, `PROGRESS.md`, `check_setup.py` | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `GLOSSARY.md` Chinese columns: corrections | | | | | |
| Notebooks 01-05 | Claude Code | | | | Claude Code (claude-opus-5-5) |
| `report/FACTS.md`, `report/REPORT_SKELETON.md` | Claude Code | | | | Claude Code (claude-opus-5-5) |
| Review of the build (7 AI reviewers: `genai/workflows/verify.js`, `genai/prompts/verify_*.md`) | Claude Code | | | | Claude Code (claude-opus-5-5) |
| Fixes after the review (`genai/prompts/fix_*.md`) | Claude Code | | | | Claude Code (claude-opus-5-5) |
| Modeling-pain scores (`comparison/pain.csv`): re-scored by the owner | Claude Code (draft scores) | | | | Claude Code (claude-opus-5-5) |
| Atlas project and cluster | | | Scott Nelson (2026-10-24) | | |
| Atlas users, network access and invites | | | | | |
| Atlas screenshots + Mongo Q1-Q4 in Data Explorer | | | | | |
| Mongo Q5 screenshot from the local MongoDB | | | | | |
| Neo4j Browser screenshots | | | | | |
| Atlas Charts (2 or more) | | | | | |
| Report: Abstract | | | | | |
| Report: Motivation + related work | | | | | |
| Report: Data + links | | | | | |
| Report: Architecture caption + walkthrough | | | | | |
| Report: Mongo section + "Answer to RQ1" | | | | | |
| Report: Neo4j section + "Answer to RQ2" | | | | | |
| Report: Comparison top 5 | | | | | |
| Report: Impact | | | | | |
| Report: Technical difficulties | | | | | |
| Report: Best practices + key learnings | | | | | |
| Report: Reuse note | | | | | |
| Report: GenAI Q&A | | | | | |
| Google Doc and final PDF | | | | | |
| Canvas submission | | | | | |

---

## 5. Personal observations

Write 2-3 short dated notes in your own words: what surprised you, what was hard, or what you learned.
These notes feed "Technical difficulties" and "Key learnings" in the report.

### Data+MongoDB
- YYYY-MM-DD (name):
- YYYY-MM-DD (name):
- YYYY-MM-DD (name):

### Neo4j
- YYYY-MM-DD (name):
- YYYY-MM-DD (name):
- YYYY-MM-DD (name):

### Comparison+viz
- YYYY-MM-DD (name):
- YYYY-MM-DD (name):
- YYYY-MM-DD (name):

### Report+GenAI
- YYYY-MM-DD (name):
- YYYY-MM-DD (name):
- YYYY-MM-DD (name):

---

## 6. Daily log

Newest entry first. Data times are UTC; schedule times are PT.

### 2026-10-24 (later that day, about 09:30 UTC)
**What changed**
- The build is done. `report/FACTS.md`, the 5 notebooks and the report skeleton were built at 09:03 UTC (data-v1).
- The newest page_change event in the Mac copy is `capture_page_change_last_utc` (report/FACTS.md). The capture has caught up with the replay.
- The review is done. 7 independent AI reviewers checked the build (`genai/workflows/verify.js`). They reported 69 findings: 4 high, 32 medium and 33 low. Some findings appear in more than one reviewer's list. The list with the fixes is in `genai/PROMPTS.md`, section "Errors the review caught (2026-10-24)".
- The fixes (`genai/prompts/fix_*.md`), in short:
  - Pseudonyms are now a keyed hash: `editor_` + 10 hex digits.
  - The 3 engines do the same work in the top-contested comparison.
  - Cypher Q2 PageRank runs until it converges.
  - Mongo Q3 also has a `history_4d` series, so both cohorts can be compared on the same 4-day horizon.
  - The live tag check marks reverts whose range starts before the capture (`range_size` is then a lower bound).
  - The docs name FACTS keys instead of typing numbers. The citations, the GenAI record and the owners of every report section are fixed.
- Scott created the Atlas project and cluster. The history cohort is being loaded into it.

**What is next**
- Scott's Mac re-runs the whole pipeline after the fixes, then rebuilds FACTS, the notebooks and the skeleton.
- Then: commit, push the branch `ec-hw2`, open the draft pull request, and publish the data-v1 release.
- Atlas is loaded again after the re-run (the pseudonyms changed).
- Sun 2026-10-25: owners start. Verify your notebook, make your UI items (screenshots, charts) and start your sections.

**What we need from you**
1. Accept the GitHub invite: https://github.com/scottn66/truth-lag/invitations
2. Claim a role in the group chat by Sat 2026-10-24 12:00 PT. If you do not claim one, Scott assigns one.
3. Accept the Atlas invite (Project Owner) when it arrives by email.
4. Run `check_setup.py` once (README, section 4, Way 3) and paste all lines into the group chat. The "Figures" lines list the screenshots and charts that are not made yet.

### 2026-10-24 (morning, about 06:00 UTC)
**What changed**
- The live capture runs on the VPS since 2026-10-24, about 04:50 UTC. It started with a replay: page_change + revert risk from 2026-10-19 23:00 UTC, and tags from 2026-10-17 00:00 UTC.
- The copy on Scott's Mac (synced at the start of the build) is 486 MB in 449 part files. The newest hour of page_change was 2026-10-23 13:00 UTC, so the replay was still catching up. Revert risk and tags had reached 2026-10-24 05:00 UTC.
- The history cohort is filtered on the VPS: 300,564 rows (2026-09-08 to 2026-09-10, namespace 0). There is also a slim file with all 5,266,843 September revisions. The filter read 6,369,430 rows in 154 seconds, with 0 bad rows.
- The databases are set up on Scott's Mac: MongoDB 8.0.34, and Neo4j 2026.10.1 with GDS 2026.10.1. At 05:57 UTC both were reachable and still empty.
- First build of the history cohort table: 295,016 revisions after clean-up (confirmed in `report/FACTS.md`, `history_revisions`).
- The team docs are drafted: README, GLOSSARY, PROGRESS and `check_setup.py`.

**What is next**
- Claude Code finishes the build: the live cohort, MongoDB, Neo4j, the SQL comparison, the sharding demo, the notebooks and the report skeleton.
- Sat 2026-10-24: the data-v1 release, and a draft pull request with a checklist per role.
- Sat 2026-10-24: the Atlas project, and the history cohort loaded into Atlas.
- To check (read-only): the raw files show 7 capture-a sessions and 4 capture-b sessions between 04:52 and 05:37 UTC. Each new session means the program started again. Compare `NRestarts` with the baseline (capture-a = 2, capture-b = 1).

**What we need from you**
1. Accept the GitHub invite: https://github.com/scottn66/truth-lag/invitations
2. Claim a role in the group chat by Sat 2026-10-24 12:00 PT: Data+MongoDB, Neo4j, Comparison+viz or Report+GenAI. If you do not claim one, Scott assigns one.
3. Answer in the group chat: Windows or Mac? Python installed? Free hours from Sat 2026-10-24 to Tue 2026-10-27?

---

## 7. After any restart (Scott's Mac)

Run these from the repo folder (`cd ~/Desktop/226/truth-lag`).
1. Start the Docker machine:
   ```
   colima start
   ```
   You should see `done` at the end.
2. Start MongoDB and Neo4j:
   ```
   docker compose -f ec-hw2/docker-compose.yml --env-file ec-hw2/.env up -d
   ```
   You should see `truthlag-mongo-1` and `truthlag-neo4j-1` as `Running` or `Started`.
3. Check the VPS capture. These commands only read; they change nothing:
   ```
   ssh vps-coin systemctl is-active truthlag-capture-a truthlag-capture-b
   ssh vps-coin systemctl show -p NRestarts truthlag-capture-a truthlag-capture-b
   ```
   You should see `active` twice. The restart counts should be the baseline (capture-a = 2, capture-b = 1) or a little higher.
   If you do not see `active` twice, do not change the units. Read the log first: `ssh vps-coin tail -n 50 /opt/truthlag/logs/capture-a.log`.
4. Check the Mac:
   ```
   .venv/bin/python ec-hw2/check_setup.py
   ```
   You should see `OK` on the lines "MongoDB local" and "Neo4j".
