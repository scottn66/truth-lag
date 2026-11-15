# Rubric evidence (for the report appendix)

For the report owner: each rubric line, with a command anyone can run, the output file that command produced, and the notebook that shows it. `scripts/check_evidence.py` confirms that every command target and every output file exists (run it on the Mac, where the lake is).

**The official rubric text is not in the repository or on the Mac.** The lines below are the ones named in `docs/delta_lake_handoff/DECISIONS.md` ("What the rubric asks for") and in the two loop prompts. Before pasting this into the report appendix, put the rows in the order of the rubric on Canvas and rename them to its wording (decision 1 in `docs/final/GATE_MON.md`).

How to run a command: from the repository root on the Mac, with `TRUTHLAG_HW2_DIR=$PWD/ec-hw2` set and `.venv-lake/bin/python` as `python`. Numbers for every row are in `docs/final/RESULTS.md` and `docs/final/results.json`. Commit: see `docs/final/results.json` (`meta.commit`).

## Evidence table

| # | Rubric line | Runnable command | Output file it produced | Notebook (executed, with `.py` copy) |
| --- | --- | --- | --- | --- |
| 1 | Data warehouse and data model: star schema, slowly changing dimension | `python -m etl.gold_run --as-of 2026-11-13T23:59:59.999999Z`; `python -m etl.gold_checks --out data/lake/_runs/gold_checks_ext.json` | `data/lake/_runs/gold_checks_ext.json` | `notebooks/final/02_gold_star_schema.ipynb` |
| 2 | Pipeline with layers (Bronze, Silver, Gold) and a flow diagram | `bash etl/build_all.sh`; `python -m etl.figures` | `data/lake/_runs/bronze_parity.json`; `docs/final/figures/flow.png` | `notebooks/final/01_bronze_silver_parity.ipynb` |
| 3 | Correctness and reproducibility: parity with the published tables, tests | `python -m etl.parity cohorts`; `python -m pytest tests_lake ec-hw2/tests/test_history.py ec-hw2/tests/test_stream.py -q -p no:cacheprovider` | `data/lake/_runs/cohort_parity.json`; `data/lake/_runs/silver_parity.json` | `notebooks/final/01_bronze_silver_parity.ipynb` |
| 4 | New tool (3 points): Delta Lake with two engines (delta-rs and Delta Spark) | `python docs/delta_lake_handoff/proto_fixture_pipeline/checks/cross_engine.py data/spark_home`; `python -m etl.gold_checks --out data/lake/_runs/gold_checks_ext.json` | `data/lake/_runs/gold_checks_ext.json` | `notebooks/final/02_gold_star_schema.ipynb` |
| 5 | Time travel, versioning and change data capture | `python -m etl.time_travel` | `data/lake/_runs/time_travel.json` | `notebooks/final/04_time_travel.ipynb` |
| 6 | Reconciliation of two sources (stream labels against a second History snapshot) | `python -m etl.history_slim data/history_raw/2026-10/2026-10.enwiki.2026-10.tsv.bz2`; `python -m etl.snapshot_checks` | `data/lake/_runs/snapshot_checks.json`; `data/history_slim/2026-10/enwiki_rev_all_2026-10_slim.stats.json` | `notebooks/final/08_second_snapshot.ipynb` |
| 7 | Hypotheses answered with numbers and intervals (H1, H3, H4) | `python -m etl.hypotheses` | `data/lake/_runs/hypotheses.json` | `notebooks/final/03_hypotheses.ipynb` |
| 8 | Streaming algorithms (5 points): reservoir sampling, Bloom filter, Flajolet-Martin, DGIM, moments | `python -m etl.streaming_algos`; `python notebooks/fallback/make_fallback.py moments_reservoir` | `data/lake/_runs/streaming_algos.json`; `data/lake/_runs/fallback_moments.json` | `notebooks/final/05_streaming_algorithms.ipynb`; `notebooks/fallback/moments_reservoir.ipynb` |
| 9 | Stream processing framework (5 points): Spark Structured Streaming | `python -m etl.stream_sss` | `data/lake/_runs/stream_sss.json` | `notebooks/final/06_structured_streaming.ipynb` |
| 10 | Locality-sensitive hashing (5 points): MinHash LSH with precision on hand-labeled pairs | `python notebooks/fallback/make_fallback.py lsh_minhash` | `data/lake/_runs/fallback_lsh.json`; `notebooks/fallback/lsh_pair_labels.csv` | `notebooks/fallback/lsh_minhash.ipynb` |
| 11 | Privacy techniques (5 points): k-anonymity, l-diversity, differential privacy (Laplace) | `python notebooks/fallback/make_fallback.py privacy` | `data/lake/_runs/fallback_privacy.json` | `notebooks/fallback/privacy.ipynb` |
| 12 | Other course techniques (5 points): Change Data Feed, MERGE-based idempotent loads, bootstrap intervals | `python -m etl.time_travel`; `python -m etl.hypotheses` | `data/lake/_runs/time_travel.json`; `data/lake/_runs/hypotheses.json` | `notebooks/final/04_time_travel.ipynb`; `notebooks/final/03_hypotheses.ipynb` |
| 13 | Version control (3 points): repository with commits through the semester | `git log --oneline`; `bash scripts/make_bundle.sh` | `dist/MANIFEST.txt` | `notebooks/final/07_team_exports.ipynb` |
| 14 | Report rules: no code in the text, numbers traceable, `.py` copy of every notebook, files near 1 MB, GenAI disclosure, flow diagram, CRediT | `python scripts/check_numbers.py`; `python scripts/check_evidence.py`; `python notebooks/final/make_notebooks.py` | `docs/final/results.json`; `docs/final/report_draft.md`; `docs/final/GENAI_LOG.md`; `docs/final/figures/flow.png` | `notebooks/final/07_team_exports.ipynb` |

Rows 8 (second notebook), 10 and 11 point at the fallback notebooks (built by Claude Code for Scott). If Wanru's LSH notebook or Zhenni's privacy notebook arrives, replace the command, output and notebook of that row with theirs: teammate work wins.

## What each row shows, in one line

1. Twelve Gold tables; every fact joins exactly one page version; the checks pass at the extended build.
2. One script builds the three layers from the raw files; the diagram shows the flow.
3. The lake equals the published EC HW2 tables value for value; the automated tests pass.
4. delta-rs writes Bronze and Silver, Spark SQL writes Gold, and each engine reads the other's tables.
5. "Then against now" on two knowledge axes (History snapshots and stream knowledge time), with the change feed holding exactly the changes in between.
6. The second snapshot agrees with the stream labels for almost every live revision and confirms the late reverts found in EC HW2.
7. H1 is not falsified on the October cohort; H3 and H4 are falsified; intervals come from a bootstrap over pages.
8. Six algorithms measured against exact answers on the same stream, with error and memory.
9. The Bronze-to-Silver step as a streaming query, with throughput and latency at five input rates.
10. Near-duplicate comments of reverted edits found with MinHash LSH; precision on labeled pairs; recall against an exact join.
11. Group sizes, diversity and suppression on the released tables; error of E(L) under Laplace noise at three epsilons.
12. Techniques from the course used inside the pipeline itself.
13. The commit history and the bundle manifest with the commit hash.
14. The number check, this evidence check, the notebook copies, the GenAI log and the diagram.

## Stated deviations from the proposal (for the report)

- Kafka (or Redpanda), Airflow and dbt were not built. The Bronze tables are the replayable log; `etl/build_all.sh` runs the steps in order.
- Plain slowly changing dimension (Type 2) in `dim_page`, not a bitemporal model. The four clocks are kept as columns and commit metadata (`docs/delta_lake_handoff/LAKE_DESIGN.md`).
- E(L) uses a 4-day horizon, not 30 days.
- The 2026-10 History snapshot was not on the VPS as `DECISIONS.md` assumed; it was downloaded from the public dump site and filtered locally (`etl/history_slim.py`).
- H2 and experiments E0, E3, E6, E7 were not built.
