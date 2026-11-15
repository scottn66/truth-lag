# TruthLag final build: status

Branch `final-lake` (local only; Scott pushes). Numbers live in `RESULTS.md`, each with the command and table version behind it.

Scope amendment (from Scott, 2026-11-15): LSH (Wanru) and Privacy (Zhenni) are teammates' items. This build writes the extracts they need to `data/exports/` and documents them in `HANDOFF_TEAM.md`. Success = P0 + streaming algorithms + Structured Streaming + those exports.

## Work queue

**P0: core lake**
- [x] Phase 0 gate: Java and Spark start, parity reference exists, Spark reads a delta-rs table
- [x] Bronze from data/raw (3 streams, Oct 19 to Nov 13); Oct 19-27 counts match the parity reference
- [x] Silver + cohorts; test_parity on real data passes or every mismatch is explained
- [x] Gold: star schema, dim_page SCD2 (page_key MERGE), fact_edit, fact_revert_label, mart_el_curve; 57.95% at 1 h reproduced, then extended to Nov 13
- [x] Hypotheses H1, H3, H4 with numbers and verdicts
- [x] Time travel "then vs now" (80_time_travel_then_and_now.sql)

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
