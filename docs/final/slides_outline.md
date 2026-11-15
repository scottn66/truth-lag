# Truth Lag: slide outline

**Outline for the team (source for Tingyu, not the final deck).** Filled from `docs/final/results.json` at commit `84624f4` by `scripts/render_report.py`; edit `docs/final/slides_outline.template.md`, never this file. One block per slide: a title, the facts to show, the figure to use. The rubric asks for a flow diagram and a CRediT slide: both are here. Do not quote edit comments on a slide.

## Slide 1: Title

- Truth Lag: how fast do live Wikipedia metrics converge to reconciled history? Group 9, DATA 226.

## Slide 2: The question

- A live count of reverted edits is a lower bound: reverts arrive late.
- E(L): the share of eventual reverts (within 4 days) still unknown after waiting L.
- **TODO (owner):** the one-sentence end-user scenario.

## Slide 3: Data

- 12,328,679 stream events captured over 28 days (3 streams); 2 History snapshots, 15,892,423 revision rows.
- Cohorts: history (295,016 revisions), live (279,466), live_ext (2,397,738).

## Slide 4: Architecture (flow diagram, required)

- Figure: `docs/final/figures/flow.png`.
- Bronze, Silver, Gold on Delta Lake; 2 engines; 12 Gold tables; a rebuild from raw files takes about 15 minutes.

## Slide 5: Is the lake right?

- Equal to the published EC HW2 tables value for value: 6 of 6 cohort tables, 3 of 3 stream tables.
- 33 of 33 Gold checks and 49 tests pass.

## Slide 6: The truth-lag curve

- Figure: `docs/final/figures/el_curve.png`.
- After 1 hour 57.95% of eventual reverts are known; after 1 day 89.44%; after 2 days 93.72%.
- The longer cohort (live_ext, 112,937 reverts) gives 58.74% after 1 hour.

## Slide 7: Hypotheses

- H1 (long tail): not falsified on the October cohort: 57.95% known at 1 hour (threshold 60%), 93.72% at 48 hours (threshold 95%).
- H3 (bursts converge slowest): falsified. At 1 hour E is 0.2887 for burst edits against 0.4164 for the rest (live_ext).
- H4 (page identity): small effect: 0.279% of pages (live_ext), 0.584% (history); below the 1% floor.

## Slide 8: Two sources, two knowledge axes

- Stream labels against the second History snapshot: 99.86% agreement; 66 stream only, 325 dump only.
- Time travel on snapshots: 19,858 reverted revisions known then, 20,925 now.
- Time travel on the stream: 17,040 live reverts known as of 2026-10-24, 17,818 as of 2026-10-27.

## Slide 9: Streaming algorithms against exact answers

- HyperLogLog in about 12 kilobytes: mean error -0.30% on 2,153,428 distinct pages.
- Bloom filter: all 4 repeated events found, none missed.
- DGIM (reverts in the last hour): mean error 5.24% with at most 31 buckets.
- AMS second moment: mean absolute error 4.59% with 10,000 variables.

## Slide 10: Structured Streaming

- Bronze to Silver as a streaming query: 95th percentile latency 3.303 seconds at 2,500 events per second, 4.066 at 10,000.
- Drain without a rate limit: 16614.6 events per second; output equal to the batch tables.

## Slide 11: Locality-sensitive hashing (fallback numbers; a teammate's notebook replaces them)

- MinHash LSH on 49,140 distinct edit summaries: 96.11% recall against an exact join, in about 0.8 seconds instead of 190.8.
- Precision on labeled pairs: 37 of 40 (one pair per group).
- 72.56% of edits that were not reverted reuse a summary, against 24.63% of reverted edits.

## Slide 12: Privacy (fallback numbers; a teammate's notebook replaces them)

- Figure: `docs/final/figures/privacy_laplace.png`.
- The hourly table is nearly 5-anonymous (3.95% of cells below). The page-level table is not: 81.63% of rows have one editor.
- Suppression biases the page-level revert rate from 4.71% to 12.05%.
- Laplace noise at epsilon 0.1 moves E(L) of the main series by 0.00093 on average.

## Slide 13: Deviations and limitations

- Not built: Kafka, Airflow, dbt, the early-signal model (H2). Horizon 4 days, not 30.
- One wiki, 28 days, one laptop.

## Slide 14: CRediT (required)

- The table of the report draft, section CRediT. Each person confirms their row.

## Slide 15: GenAI disclosure

- Code, checks and analysis scripts were written with Claude Code; every number comes from a logged command; the team wrote the text. Details: `docs/final/GENAI_LOG.md`.
