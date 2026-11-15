# TruthLag final build: status

Branch `final-lake` (local only; Scott pushes). Numbers live in `RESULTS.md`, each with the command and table version behind it.

Scope amendment (from Scott, 2026-11-15): LSH (Wanru) and Privacy (Zhenni) are teammates' items. This build writes the extracts they need to `data/exports/` and documents them in `HANDOFF_TEAM.md`. Success = P0 + streaming algorithms + Structured Streaming + those exports.

## Summary (2026-11-15, about 10:15 UTC / 2:15 AM PT): stop condition 1, success

**Done.** All P0 items, both P1 items this build owns (streaming algorithms, Structured Streaming), the extracts for the LSH and privacy owners, and all P2 items. Everything ran on the real data on Scott's Mac. Every number below is in `RESULTS.md` with its command and table version.

**Headline numbers**
- Bronze: 4,871,014 page-change, 3,113,810 revert-risk and 4,343,855 tag lines (Oct 17 to Nov 15). Inside the published parse cut the line counts equal the published ones exactly (1,231,430 / 789,634 / 1,603,253).
- Silver equals the published EC HW2 tables value for value: 3 stream tables at the cut and 6 cohort tables (295,016 history and 279,466 live revisions, 19,858 and 18,358 revert links, 4,350 late reverts).
- Gold: 30 of 30 checks at the parity as_of and again at Nov 13. All 18 published known-by counts are reproduced: live E(1 h) = 0.4205, so **57.95% of reverts are known at 1 h**; history E(1 h) = 0.4434. Extended live cohort (edits Oct 20 - Nov 8, 112,937 eventual reverts): 58.74% at 1 h, 95.07% at 48 h.
- H1: not falsified on the October cohort (57.95% < 60%, 93.72% < 95%, intervals below both). Borderline at 48 h on the longer window (95.07%, CI 94.72-95.37).
- H3: falsified. At 1 h, burst edits' reverts become known *faster* (E(1 h) 0.23-0.35 for bursts vs 0.42-0.45 for the rest; intervals apart in history and live_ext); at 1 d the intervals overlap.
- H4: small effect. 0.3-0.6% of pages and 0.5-1.1% of title keys change; falsified at a 1% floor (the floor is our choice; see question 2).
- Time travel on two axes. Snapshots: fact_revert_label v1 (2026-09 load) knew 19,858 reverted history-cohort revisions; v2 (2026-10 load) knows 20,925. Stream as_of: fact_edit v1 (Oct 24) knew 17,040 live reverts; v2 (Oct 27) knew 17,818. Each change feed holds exactly the updates in between (40,721 and 778).
- Second History snapshot (2026-10, added later on 2026-11-15): filtered locally (10,625,580 revisions, no malformed row), loaded as one MERGE commit (40,721 labels changed, 40,683 of them became reverted). The 2026-10 dump confirms 2,967 of the 2,970 late reverts that EC HW2 found in the stream. Live cohort vs dump: 99.86% agreement (17,752 both, 66 stream only, 325 dump only); E(1 h) 0.4205 with stream labels, 0.4266 with dump labels.
- Streaming algorithms: HLL p = 14 in 12 KB gives -0.30% mean error (5 salts) on 2,153,428 distinct pages. The Bloom filter finds all 4 real repeats with no false negative. DGIM stays within its bound wiki-wide.
- Structured Streaming: p95 latency 3.30 s at 2,500 events/s and 4.07 s at 10,000/s; it first passes 5 s at 20,000/s (5.22 s). The drain runs at 16,615 events/s, and the streamed rows equal batch Silver.

- End to end: a rebuild from scratch into an empty folder (`SKIP_EXTRAS=1 bash etl/build_all.sh data/lake_e2e`, 12 min) gives the same parity results, 30 of 30 checks, and identical E(L), hypothesis and time-travel numbers.

**Not done / left for others**
- Report and slides (Tingyu and all); LSH notebook (Wanru, input `data/exports/lsh_edits.parquet`); k-anonymity and Laplace noise (Zhenni, inputs in `data/exports/`). See `HANDOFF_TEAM.md`.
- Shortcuts, stated: the lab's 75 Gold checks on made-up data were not ported into `tests_lake/test_gold.py`; the 30 real-data checks in `etl/gold_checks.py` replace them. Not built: OPTIMIZE/Z-order, `is_redirect`.

**Questions for Scott (stop condition 3: a decision looks wrong)**
1. ~~The 2026-10 History snapshot was not on the VPS.~~ Resolved: Scott downloaded the public files to `data/history_raw/2026-10/`; Phase 5 is built (RESULTS.md, "Second History snapshot 2026-10"). Note for the report: DECISIONS.md answer 3 (snapshot on the VPS) was not accurate.
2. H4 needs a floor. This build uses 1% of pages. Confirm it or give another value.
3. Commits use the author email scottn66@users.noreply.github.com (as the memory notes say for this repo). Your recent commits on main use your personal email. Change before pushing if you prefer.

**How to rerun** (from the repository root on the Mac)
1. Environment, once: `uv venv --python 3.12 .venv-lake && uv pip install --python .venv-lake/bin/python -r docs/delta_lake_handoff/requirements-lake.txt`; Java: `brew install openjdk@21` (`etl/spark_session.py` finds it).
2. Data: `rsync -az --partial vps-coin:/opt/truthlag/data/raw/ data/raw/` (never `--delete`); `data/parity_ref/` must hold the copy of `data/parsed` and `data/tables` (SHA-256 list in `data/parity_ref/SHA256SUMS.txt`).
3. Everything: `bash etl/build_all.sh` (lake in `data/lake/`; it includes the 2026-10 snapshot steps when `data/history_raw/2026-10/*.tsv.bz2` exist, and runs the filter only for missing slim files). Or a fresh folder: `SKIP_EXTRAS=1 bash etl/build_all.sh data/lake_e2e` (core build and checks only).
4. Tests: `TRUTHLAG_HW2_DIR=$PWD/ec-hw2 .venv-lake/bin/python -m pytest tests_lake/test_parity.py ec-hw2/tests/test_history.py ec-hw2/tests/test_stream.py -q -p no:cacheprovider` plus `tests_lake/test_history_slim.py` (49 passed).

## Work queue

**P0: core lake**
- [x] Phase 0 gate: Java and Spark start, parity reference exists, Spark reads a delta-rs table
- [x] Bronze from data/raw (3 streams, Oct 19 to Nov 13); Oct 19-27 counts match the parity reference
- [x] Silver + cohorts; test_parity on real data passes or every mismatch is explained
- [x] Gold: star schema, dim_page SCD2 (page_key MERGE), fact_edit, fact_revert_label, mart_el_curve; 57.95% at 1 h reproduced, then extended to Nov 13
- [x] Hypotheses H1, H3, H4 with numbers and verdicts
- [x] Time travel "then vs now" (80_time_travel_then_and_now.sql)
- [x] Phase 5, second History snapshot 2026-10: local filter, Bronze/Silver load, label MERGE + change feed mart, reconciliation, snapshot-axis time travel (80) restored, as_of demo kept (81)

**P1: course techniques**
- [x] Streaming algorithms: FM/HLL distinct editors and pages, Bloom filter on meta_id, DGIM reverts per page per hour; error and memory vs exact
- [x] Spark Structured Streaming Bronze -> Silver (foreachBatch); events/s and p95 latency
- [x] Team extracts for LSH (Wanru) and Privacy (Zhenni) + docs/final/HANDOFF_TEAM.md  *(replaces building LSH and Privacy)*

**P2: report-ready outputs**
- [x] One notebook per component under notebooks/final/ with .py exports (each about 1 MB or less)
- [x] Flow diagram (mermaid + PNG)
- [x] docs/final/RUBRIC_EVIDENCE.md
- [x] docs/final/GENAI_LOG.md
- [x] Gold mart extracts in data/exports/ (< 50 MB each, not committed)
