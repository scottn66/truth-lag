# Rubric evidence (for the report appendix)

For the report owner: the rubric criteria **in the order of the Canvas rubric** (`docs/final/CANVAS_SPEC.md`, copied from the assignment page on 2026-11-15), each with the evidence that exists today. Canvas asks for this appendix "in the same order" and says "please do not mislead", so a line with no evidence yet says so.

Two kinds of rows:

- **Checked rows** have a command anyone can run, the output file that command produced, and (where one fits) an executed notebook with a `.py` copy. `scripts/check_evidence.py` confirms every one of those exists.
- **Open rows** say `TODO (owner)` in the command column. They are judged live, or their evidence is a person's to supply (minutes, a `.tex` file, the deck). The checker lists them as open; it cannot pass them.

How to run a command: from the repository root on the Mac, with `TRUTHLAG_HW2_DIR=$PWD/ec-hw2` set and `.venv-lake/bin/python` as `python`. Numbers for every row are in `docs/final/RESULTS.md` and `docs/final/results.json`. Commit: see `docs/final/results.json` (`meta.commit`).

## Evidence table

| # | Rubric line (Canvas wording, points) | Runnable command | Output file it produced | Notebook (executed, with `.py` copy) |
| --- | --- | --- | --- | --- |
| 1 | Code Walkthrough (5) | `bash etl/build_all.sh`; `python -m etl.gold_run --as-of 2026-11-13T23:59:59.999999Z`; `python -m etl.gold_checks --out data/lake/_runs/gold_checks_ext.json` | `data/logs/lake/build_all_e2e2.log`; `data/lake/_runs/gold_checks_ext.json` | `notebooks/final/01_bronze_silver_parity.ipynb`; `notebooks/final/02_gold_star_schema.ipynb` |
| 2 | Presentation Skills, includes time management (5) | TODO (owner): judged live. Source for the talk: `docs/final/slides_outline.md` | none yet | n/a |
| 3 | Discussion / Q&A (5) | TODO (owner): judged live. Numbers to answer from: `docs/final/RESULTS.md` | none yet | n/a |
| 4 | Demo (5) | `python -m etl.time_travel`; `python -m etl.stream_sss` | `data/lake/_runs/time_travel.json`; `data/lake/_runs/stream_sss.json` | `notebooks/final/04_time_travel.ipynb`; `notebooks/final/06_structured_streaming.ipynb` |
| 5 | Report: format, completeness, language, plagiarism, no unnecessary screenshots (7) | `python scripts/check_numbers.py`; `python scripts/render_report.py` | `docs/final/report_draft.md`; `docs/final/results.json` | n/a |
| 6 | Version Control: Git / GitHub, publicly accessible, commits through the semester (3) | `git log --date=short --format=%ad_%an_%s`; `bash scripts/make_bundle.sh` | `dist/MANIFEST.txt` | n/a |
| 7 | Lessons learned, in the report and the presentation (5) | `python scripts/render_report.py` | `docs/final/report_draft.md`; `docs/final/slides_outline.md` | n/a |
| 8 | Prospects of winning competition / publication (3) | TODO (owner): the team states the case | none yet | n/a |
| 9 | Innovation (5) | `python -m etl.hypotheses`; `python -m etl.snapshot_checks` | `data/lake/_runs/hypotheses.json`; `data/lake/_runs/snapshot_checks.json`; `docs/final/figures/el_curve.png` | `notebooks/final/03_hypotheses.ipynb`; `notebooks/final/08_second_snapshot.ipynb` |
| 10 | Teamwork (5) | TODO (owner): each person confirms their CRediT row in `docs/final/report_draft.md` | none yet | n/a |
| 11 | Technical difficulty (5) | `python -m etl.parity cohorts`; `python -m etl.history_slim data/history_raw/2026-10/2026-10.enwiki.2026-10.tsv.bz2`; `python -m pytest tests_lake ec-hw2/tests/test_history.py ec-hw2/tests/test_stream.py -q -p no:cacheprovider` | `data/lake/_runs/cohort_parity.json`; `data/lake/_runs/silver_parity.json`; `data/history_slim/2026-10/enwiki_rev_all_2026-10_slim.stats.json` | `notebooks/final/01_bronze_silver_parity.ipynb`; `notebooks/final/08_second_snapshot.ipynb` |
| 12 | Practiced pair programming? (2) | TODO (owner): nothing in the repository shows it | none yet | n/a |
| 13 | Practiced agile / scrum (1-week sprints)? (2) | TODO (owner): minutes and sprint backlog are not in the repository | none yet | n/a |
| 14 | Slides (3) | TODO (owner): the deck. Source: `docs/final/slides_outline.md` | none yet | n/a |
| 15 | Used LaTeX: upload the `.tex` file from the IEEE template (2) | TODO (owner): no `.tex` file is in the repository | none yet | n/a |
| 16 | Used creative presentation techniques (2) | TODO (owner): the deck | none yet | n/a |
| 17 | Literature Survey (7) | TODO (owner): Section II of `docs/final/report_draft.md` is a list of sources; the added references are unverified | none yet | n/a |
| 18 | Use of streaming algorithms: reservoir sampling, Bloom filter, Flajolet-Martin, DGIM, computing moments (5) | `python -m etl.streaming_algos`; `python notebooks/fallback/make_fallback.py moments_reservoir` | `data/lake/_runs/streaming_algos.json`; `data/lake/_runs/fallback_moments.json` | `notebooks/final/05_streaming_algorithms.ipynb`; `notebooks/fallback/moments_reservoir.ipynb` |
| 19 | Use of Stream Processing Frameworks such as Spark, Flink, and Kafka (5) | `python -m etl.stream_sss` | `data/lake/_runs/stream_sss.json` | `notebooks/final/06_structured_streaming.ipynb` |
| 20 | Use of Locality Sensitive Hashing (5) | Teammate-built (Wanru): `jupyter nbconvert --to notebook --execute notebooks/lsh_minhash_wanru.ipynb`. Backup: `python notebooks/fallback/make_fallback.py lsh_minhash` | `notebooks/lsh_pair_labels.csv`; `docs/final/wanru_history_report_section.md`; backup: `data/lake/_runs/fallback_lsh.json` | `notebooks/lsh_minhash_wanru.ipynb`; backup: `notebooks/fallback/lsh_minhash.ipynb` |
| 21 | Use of Privacy techniques: k-anonymity, l-diversity, differential privacy (5) | Teammate-built (Zhenni): `jupyter nbconvert --to notebook --execute notebooks/privacy_zhenni/privacy_k_anonymity_I-Diversity_Suppression.ipynb`; `jupyter nbconvert --to notebook --execute notebooks/privacy_zhenni/privacy_laplace.ipynb`. Backup: `python notebooks/fallback/make_fallback.py privacy` | `notebooks/privacy_zhenni/outputs/k_anonymity/k_summary.csv`; `notebooks/privacy_zhenni/outputs/k_anonymity/l_diversity_summary.csv`; `notebooks/privacy_zhenni/outputs/k_anonymity/suppression_summary.csv`; `notebooks/privacy_zhenni/outputs/laplace/laplace_summary.csv`; backup: `data/lake/_runs/fallback_privacy.json` | `notebooks/privacy_zhenni/privacy_k_anonymity_I-Diversity_Suppression.ipynb`; `notebooks/privacy_zhenni/privacy_laplace.ipynb`; backup: `notebooks/fallback/privacy.ipynb` |
| 22 | Any other tools and techniques covered in the course not included in the other criteria (5) | `python -m etl.gold_checks --out data/lake/_runs/gold_checks_ext.json`; `python -m etl.time_travel`; `python -m etl.hypotheses` | `data/lake/_runs/gold_checks_ext.json`; `data/lake/_runs/time_travel.json`; `data/lake/_runs/hypotheses.json` | `notebooks/final/02_gold_star_schema.ipynb`; `notebooks/final/04_time_travel.ipynb` |
| 23 | Use of new tool(s) that were not used for any of the HW (3) | `python docs/delta_lake_handoff/proto_fixture_pipeline/checks/cross_engine.py data/spark_home`; `python -m etl.gold_checks --out data/lake/_runs/gold_checks_ext.json` | `data/lake/_runs/gold_checks_ext.json` | `notebooks/final/02_gold_star_schema.ipynb` |
| 24 | The slides and report include a Flow schematic diagram (1) | `python -m etl.figures` | `docs/final/figures/flow.png`; `docs/final/flow.mmd` | n/a |

Rows 20 and 21 are teammate-built: row 20 is Wanru's MinHash LSH notebook and row 21 is Zhenni's two privacy notebooks. The fallback notebooks in `notebooks/fallback/` (built by Claude Code for Scott) stay as a backup and are named second in each cell. The teammates' numbers are in `docs/final/results.json` under `wanru.*` and `zhenni.*`, read from the files they committed. Row 18's second notebook is still a fallback notebook. Zhenni's notebooks read the team exports from a folder next to the notebook (`notebooks/privacy_zhenni/README.md` says how to run them).

## What each row shows, and what is still missing

1. One script builds the three layers from the raw files; the notebooks walk through Bronze, Silver and Gold in order. The walkthrough itself is live.
2. Open. Judged at the presentation.
3. Open. Judged at the presentation.
4. Two things that run in front of an audience: "then against now" on two knowledge axes, and the Bronze-to-Silver step as a streaming query. The demo itself is live.
5. What exists is a skeleton of facts with every number filled from one file and checked. **Missing:** the report text, the IEEE format and the PDF (owner: Tingyu).
6. The history runs from the first commit on 2026-10-15 to today; the manifest names the commit of the bundle. **Missing:** the rubric says "must be publicly accessible" and the repository is private today (decision 9 in `docs/final/GATE_MON.md`). The history starts in mid-October, not at the start of the semester.
7. The draft has a "Lessons Learned" section and the slide outline has a lessons slide, both as facts from the build. **Missing:** the team's own lessons and the text.
8. Open. Facts the team can use: the second snapshot confirms almost all late reverts, and the lake rebuilds from raw files with one script.
9. What is measured here and not taken from elsewhere: the truth-lag curve E(L) from knowledge-time builds, and the check of stream labels against a second History snapshot. Whether that is innovative is the team's claim to make.
10. Open. The CRediT table is proposed, not confirmed. The commit history shows who committed what.
11. The lake equals the published tables value for value; a full History dump is filtered and loaded locally; the automated tests pass.
12. Open. No evidence exists in the repository. `docs/final/GENAI_LOG.md` records the use of Claude Code, which the rubric calls optional and gives no points for.
13. Open. No minutes, backlog or board link is in the repository.
14. Open. There is an outline of facts, not a deck.
15. Open. The draft is Markdown; the points need a `.tex` file that shows the IEEE template.
16. Open.
17. Open. The rubric asks for subsections, no missed work and standard citations; the draft's added references were written from memory and are not verified.
18. Six algorithms measured against exact answers on the same stream, with error and memory.
19. Spark Structured Streaming, with throughput and latency at several input rates. Kafka and Flink were not used (see deviations).
20. Teammate-built (Wanru). Near-duplicate edit comments found with MinHash LSH; recall against an exact join; precision on 80 sampled pairs. Her notebook says she reviewed all 80 pairs by hand and that it was adapted from the fallback notebook; her label file holds a human label for every pair. In the fallback notebook the pairs were labeled by Claude Code (disclosed; decision 5).
21. Teammate-built (Zhenni). Group sizes (k-anonymity), diversity (l-diversity) and suppression on the released tables; error of E(L) under Laplace noise at three epsilons. The fallback notebook covers the same ground as a backup.
22. Star schema with a slowly changing dimension, time travel with the change data feed, MERGE-based idempotent loads, bootstrap intervals. Whether each was covered in the course is for the team to confirm.
23. Delta Lake with two engines: delta-rs writes Bronze and Silver, Spark SQL writes Gold, and each reads the other's tables. Whether it was used in a homework is for the team to confirm.
24. The diagram is in the figures folder, is referenced in the draft's architecture section and has its own slide in the outline.

## Canvas instructions that are not rubric lines

- **Mandatory question on Generative AI, and the certificate.** Canvas asks whether solutions were found with Generative AI or other sources, with full details including the prompt, and advises submitting the certificate from the site it names. The material for the answer is `docs/final/GENAI_LOG.md`. **Missing:** nobody has generated the certificate.
- **Accepted file types.** The upload takes pdf, py, ipynb, pptx, tex, txt, html and a few others. It does not take zip, md or png. Code goes up as `.py` and `.ipynb` files, and anything else by link.
- **External links.** The appendix must list them and they must be reachable by the teaching team: GitHub `https://github.com/scottn66/truth-lag` (branch `final-lake`; private today). **Missing:** a board or minutes link, and an elevator pitch video link if the team made one.
- **Tools used** (instruction 8 asks for the list with the criteria): Python, Delta Lake (delta-rs and Delta Spark), Apache Spark (SQL, Structured Streaming, MLlib MinHashLSH), pandas, pyarrow, matplotlib, Jupyter, pytest, Git and GitHub, Claude Code. From the earlier homework stage in `ec-hw2/`: MongoDB and Neo4j. The team adds what it used for the report and slides.
- **CRediT statement in a slide.** In the outline; rows are not confirmed.
- **No code in the report, `.py` copy of every notebook, files near the stated size.** Checked by `scripts/check_numbers.py`, `scripts/check_evidence.py` and `scripts/make_bundle.sh`.
- **No Agentic AI, LLM or deep learning methods in the project.** None is part of the pipeline or the analysis. One use touches this: in the fallback LSH notebook the evaluation pairs were labeled by Claude Code (decision 5); Wanru's notebook states that she reviewed the same 80 pairs by hand.

## Stated deviations from the proposal (for the report)

- Kafka (or Redpanda), Airflow and dbt were not built. The Bronze tables are the replayable log; `etl/build_all.sh` runs the steps in order.
- Plain slowly changing dimension (Type 2) in `dim_page`, not a bitemporal model. The four clocks are kept as columns and commit metadata (`docs/delta_lake_handoff/LAKE_DESIGN.md`).
- E(L) uses a 4-day horizon, not 30 days.
- The 2026-10 History snapshot was not on the VPS as `DECISIONS.md` assumed; it was downloaded from the public dump site and filtered locally (`etl/history_slim.py`).
- H2 and experiments E0, E3, E6, E7 were not built.
