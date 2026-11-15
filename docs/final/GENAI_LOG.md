# GenAI log: final build of the TruthLag lake

This log feeds the GenAI disclosure of the term project. It lists what Claude (Claude Code, model Claude Opus 5.5) wrote, generated or decided, per component. A person must check each item before it goes into the report. Claude wrote no report or slide prose.

## Sessions

| Date (UTC) | Where | Who started it | What |
| --- | --- | --- | --- |
| 2026-11-13 | Cloud Claude Code session | Scott | Plan, research reports R1-R7, two prototypes on made-up data (`docs/delta_lake_handoff/`, commit 5079d0b). Its own provenance note is in `docs/delta_lake_handoff/README.md`. |
| 2026-11-15 | Claude Code on Scott's Mac, branch `final-lake` | Scott, with the loop prompt `CLAUDE_LOOP_PROMPT.md` and an amendment (LSH and Privacy go to Wanru and Zhenni) | The real-data build: everything below. Local commits only; Scott pushes. |

## By component (session of 2026-11-15)

| Component | Files | What Claude did | What it reused | How it was checked |
| --- | --- | --- | --- | --- |
| Environment and Spark on macOS | `etl/spark_session.py`, `.gitignore` | Installed Homebrew openjdk@21 and a uv venv from the kit's pinned versions. Found and fixed the macOS start failure (loopback driver, NIO transport) and the time-zone shift (TZ=UTC). | Kit's `spark_session.py` | Kit check `cross_engine.py` prints `STEP1C OK` |
| Bronze stream loader | `etl/bronze_stream.py`, `etl/delta_io.py`, `etl/tables.py`, `etl/lake_config.py`, `etl/run.py` | Copied from the kit; set the lake root to `data/lake/`; added the extended-cohort table specs. | Prototype R6 (kit) | `etl/parity.py bronze`: line counts equal the published parse cut for all 3 streams; re-run adds 0 rows |
| Parity checks | `etl/parity.py` | Wrote: rebuild of the published parse cut from `_SUCCESS_parsed.json`; table comparison; cohort comparison. | `assert_same_table` idea from the kit test | Ran on the real data; results in RESULTS.md |
| History (dump) side | `etl/history.py` | Wrote: Bronze landing with `source_row` resume, typed Silver slim, history cohort through the old `parse_history.run`. | Old EC HW2 code, unchanged | Row counts equal FACTS.md; cohort tables equal `data/tables` |
| Silver stream and cohort tables | `etl/silver_stream.py`, `etl/silver_cohorts.py` | Copied from the kit. Added `write_latest` (the `_runs/latest.json` guard) and `build_ext` (the live rules on a longer window by swapping `config.LIVE_WINDOW` during the call). | Prototype R6; old `label_live.py`, `late_reverts.py` | Equal to the published Parquet files value for value |
| Gold SQL and runner | `etl/gold_run.py`, `etl/sql/*.sql` | Adapted the kit's SQL: `user_kind` and the cohort key on `fact_edit`, the `live_ext` cohort, the `as_of` filter on stream observations, the dump's current title, the burst mart, waits from config. Wrote a new runner that stops on error and has the four guards of the plan. Decided: key `fact_edit` by `(cohort_id, wiki_db, rev_id)`; leave `visibility_change` out of `dim_page`. | Prototype R7 SQL and helpers | `etl/gold_checks.py`: 30 of 30 checks (published counts, SCD2 integrity, delta-rs read-back) |
| Hypotheses | `etl/hypotheses.py` | Wrote the H1, H3, H4 computations and the page-level Poisson bootstrap. Chose: B = 2,000, seed 226, L = 1 h and 1 d for H3, the H4 measures, and a 1% floor for H4 (DECISIONS.md left it open; the team should confirm or change it). | Definitions in DECISIONS.md and D20 | Numbers re-derived from the marts (H1 live equals FACTS.md) |
| Time travel | `etl/time_travel.py`, `etl/sql/80_time_travel_then_and_now.sql` | Rewrote the kit's SQL: no 2026-10 snapshot exists, so the knowledge axis is the stream `as_of` (versions found by commit metadata). | Kit SQL 80, 50 | Counts agree with Silver by version and with the change feed |
| Streaming algorithms | `etl/streaming_algos.py` | Wrote HyperLogLog, Flajolet-Martin PCSA, Bloom filter, time-based DGIM, reservoir sampling and AMS from the textbook definitions; chose parameters and the 5-salt repetition after a first run looked biased (a synthetic test showed the sketch was fine). | None (numpy only); Spark's `approx_count_distinct` as a reference | Each against the exact answer on the same stream |
| Structured Streaming replay | `etl/stream_sss.py` | Wrote the producer (delta-rs appends at a fixed rate), the streaming query with `foreachBatch` MERGE, and the latency and throughput measurement. | R3 lab pattern (`foreachBatch`) | Streamed rows compared with batch Silver (parity counts in RESULTS.md) |
| Exports and hand-off | `etl/exports.py`, `docs/final/HANDOFF_TEAM.md` | Wrote the extracts for the LSH and privacy work and for charts; pseudonyms through `build_documents.public_name`. | Old pseudonym code | Sizes and hashes in `data/exports/manifest.json` |
| Figures | `etl/figures.py`, `docs/final/flow.mmd`, `docs/final/figures/*.png` | Drew the flow diagram and the E(L) figure. | | Looked at the PNGs |
| Status and evidence documents | `docs/final/STATUS.md`, `RESULTS.md`, `RUBRIC_EVIDENCE.md`, this file | Wrote them as records of commands and numbers. They are not report text. | | Every number comes from a command shown next to it |

## Decisions Claude made that the team may want to revisit

1. The extended live cohort `live_ext` covers edits of 2026-10-20 to 2026-11-08, so that each has 4 days of follow-up by the end of Nov 13.
2. H4 floor of 1% of pages (DECISIONS.md: "a floor that is still to be set").
3. The time-travel demo uses build `as_of` versions instead of two History snapshots (none exists for 2026-10).
4. `fact_edit` key includes `cohort_id`; `dim_page` ignores `visibility_change` events.
5. In Bronze and Silver, the lake keeps every captured event through 2026-11-15; analyses stop at the end of 2026-11-13.

## Suggested disclosure text (for the report owner to edit)

"The Delta Lake pipeline code, its checks and the analysis scripts were written with Claude Code (Anthropic), from a plan and prototypes also drafted with Claude Code on Nov 13, 2026. All code ran on the real data on Nov 15, 2026, and every reported number comes from a logged command. The team checked [what] and wrote all report and slide text."
