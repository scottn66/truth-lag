# TruthLag on Delta Lake: hand-off kit

Made on 2026-11-13 in a cloud Claude Code session, for the build session on Scott's Mac.

## What this is

- A plan to rebuild the TruthLag pipeline as Bronze, Silver and Gold Delta tables before the term project is due on 2026-11-17, and the material behind the plan.
- **Status: a draft for review.** Everything here was tested on made-up data only. Nothing has run on the real data. The plan was reviewed once inside the session that wrote it, and revised; its Review log has the entry. No other agent or person has reviewed it.
- The working copy of the plan is in Notion. `PLAN.md`, `LAKE_DESIGN.md` and `RESEARCH_INDEX.md` are exports of it. If they differ from Notion, Notion is newer.

**Read `DECISIONS.md` first.** It holds Scott's answers of 2026-11-13 (deadline, engines, where the 2026-10 snapshot is, the hypotheses H1 to H4 and experiments E0 to E7) and what the course rubric asks for that the plan does not build. Where it differs from `PLAN.md`, it wins.

## Contents

| Path | What it is |
| --- | --- |
| `PLAN.md` | The build plan: scope, rules, design decisions D1 to D20, build phases 0 to 6, the numbers to reproduce, risks, open decisions for Scott |
| `LAKE_DESIGN.md` | The table catalog: every Bronze, Silver and Gold table with its key and write rule |
| `HANDOFF_PROMPT.md` | The text to paste into the build session |
| `RESEARCH_INDEX.md` | What each research report answers. Its page R8 is not a file here: R8 holds the check scripts, which the kit has in the prototype folders. |
| `research/R1_port_inventory.md` | The old pandas pipeline: functions, rules, clocks, 44 published numbers |
| `research/R2_deltars_lab.md` | delta-rs 1.6.6: what works, with tested code |
| `research/R3_spark_lab.md` | PySpark 4.2.0 with delta-spark 4.4.1: what works, and how the two engines share tables |
| `research/R4_delta_docs.md` | Facts from the Delta Lake documentation and protocol |
| `research/R5_sources_events.md` | The History snapshots, and how to define current-events pages |
| `research/R6_fixture_pipeline.md` | Report on prototype 1 |
| `research/R7_gold_sql_lab.md` | Report on prototype 2 |
| `proto_fixture_pipeline/` | Prototype 1: the `etl` package (Bronze and Silver with delta-rs), its parity test in `tests_lake/`, and check scripts in `checks/` |
| `proto_gold_sql/` | Prototype 2: the Gold SQL files in `sql/`, the runner `run_gold.py`, the made-up data generator `gen_silver.py`, and the verifier `verify_gold.py` |
| `requirements-lake.txt` | The package versions that ran together |
| `MANIFEST.txt` | Every file of the original kit with its size and SHA-256. `README.md` was edited after it was made, and `DECISIONS.md` was added. |
| `DECISIONS.md` | Scott's decisions, H1 to H4, E0 to E7, and the gaps against the rubric |

## How to use it

1. This folder is the kit, committed at Scott's request. The plan's phases copy the prototype code from here into `etl/` and `tests_lake/`.
2. Read `PLAN.md`, then `LAKE_DESIGN.md`.
3. Answer the points under "Open decisions for Scott" in `PLAN.md`.
4. Open a new Claude Code session in the repository folder on the Mac, and paste the text in `HANDOFF_PROMPT.md`.
5. The session copies the prototype code into the repository in Phase 1 and Phase 4 of the plan, and adapts it there.

## Before you run the prototypes

- They were written and run on Linux, with Python 3.12.3 and OpenJDK 21. Nothing ran on macOS.
- Make one environment from `requirements-lake.txt`. Spark needs Java 17 or newer.
- **Prototype 1** reads two variables:
    - `TRUTHLAG_HW2_DIR`: the path of the `ec-hw2` folder of the repository. If it is not set, the code looks for a folder named `ec-hw2` next to the `etl` package.
    - `TRUTHLAG_LAKE_DIR`: the folder for the Delta tables.
    - To run its test, from the folder that holds `etl/` and `tests_lake/`: `TRUTHLAG_HW2_DIR=<repo>/ec-hw2 PYTHONDONTWRITEBYTECODE=1 python -m pytest tests_lake/test_parity.py -q -p no:cacheprovider`. Expected: `16 passed`.
    - The test imports the old fixtures from `ec-hw2/tests/`. With `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1` it writes nothing into the repository.
- **Prototype 2** reads two variables. Its files hold default paths of the machine it ran on, so set both:
    - `GOLD_LAB`: set it to the `proto_gold_sql/` folder itself. The scripts read `sql/` from it, and they write `lake/`, `out/` and `planted.json` into it.
    - `GOLD_IVY`: a folder for the Delta jars that Spark downloads from Maven Central on its first start.
    - Run order, from the `proto_gold_sql/` folder: `python gen_silver.py`, then `python run_gold.py` (about 4 minutes), then `python verify_gold.py`. Expected: 78 of 78 checks, then 18 of 18 checks. `run_gold.py` expects an empty `lake/gold/`.
- The research reports quote paths that start with `/tmp/claude-0/` or `/home/user/`. Those paths are on the machine of the cloud session and do not exist elsewhere.

## Rules, in short

`PLAN.md` has the full list. The ones that must never be broken:

- Never stop, restart or edit the capture units on the VPS. Never open an EventStreams connection.
- Never delete or change anything under `data/raw/` or `data/history/`. Never use `rsync --delete`. Never commit anything under `data/`.
- Treat `ec-hw2/` as frozen: import from it, do not edit it.
- New folders must not be named `ingest`, `config` or `tests`.
- One writing process per Delta table at a time. Never run VACUUM before the project is submitted.
- Human editor names never go into a committed file.
- Scott pushes, opens pull requests and sends messages. Agents do not.

## Provenance and GenAI note

- Written by Claude (Claude Code, cloud session) with Scott on 2026-11-13. No teammate or instructor has reviewed it.
- Repository state read: `scottn66/truth-lag`, default branch at `8e28012`. The session changed no file in the repository.
- The plan, the research reports and both prototypes were produced with generative AI. The project's rule asks for a GenAI log entry for each piece of AI-assisted work, so code taken from this kit needs one.
