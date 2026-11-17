# Hand-off prompt for the build session

Paste the text below into a new Claude Code session on the Mac, opened in the repository folder.

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
