# Truth Lag: slide outline

**Outline for the team (source for Tingyu, not the final deck).** Filled from `docs/final/results.json` at commit `{{meta.commit_short}}` by `scripts/render_report.py`; edit `docs/final/slides_outline.template.md`, never this file. One block per slide: a title, the facts to show, the figure to use. The rubric asks for a flow diagram and a CRediT slide: both are here. Do not quote edit comments on a slide.

## Slide 1: Title

- Truth Lag: how fast do live Wikipedia metrics converge to reconciled history? Group 9, DATA 226.

## Slide 2: The question

- A live count of reverted edits is a lower bound: reverts arrive late.
- E(L): the share of eventual reverts (within {{horizon_days}} days) still unknown after waiting L.
- **TODO (owner):** the one-sentence end-user scenario.

## Slide 3: Data

- {{bronze.stream_rows_total}} stream events captured over {{bronze.page_change.event_dates}} days ({{streams}} streams); {{snapshots}} History snapshots, {{bronze.history_slim.rows}} revision rows.
- Cohorts: history ({{gold.fact_edit.rows.history}} revisions), live ({{gold.fact_edit.rows.live}}), live_ext ({{gold.fact_edit.rows.live_ext}}).

## Slide 4: Architecture (flow diagram, required)

- Figure: `docs/final/figures/flow.png`.
- Bronze, Silver, Gold on Delta Lake; {{engines}} engines; {{gold.tables}} Gold tables; a rebuild from raw files takes about {{runtime.rebuild_e2e_min}} minutes.

## Slide 5: Is the lake right?

- Equal to the published EC HW2 tables value for value: {{parity.cohort.tables_equal}} of {{parity.cohort.tables}} cohort tables, {{parity.silver.tables_equal}} of {{streams}} stream tables.
- {{gold_checks.ext.passed}} of {{gold_checks.ext.total}} Gold checks and {{tests.passed}} tests pass.

## Slide 6: The truth-lag curve

- Figure: `docs/final/figures/el_curve.png`.
- After {{one}} hour {{el.live.stream.all.w1h.share_known|pct2}}% of eventual reverts are known; after {{one}} day {{el.live.stream.all.w1d.share_known|pct2}}%; after {{two}} days {{el.live.stream.all.w2d.share_known|pct2}}%.
- The longer cohort (live_ext, {{el.live_ext.stream.all.w4d.n_eventual}} reverts) gives {{el.live_ext.stream.all.w1h.share_known|pct2}}% after {{one}} hour.

## Slide 7: Hypotheses

- H1 (long tail): not falsified on the October cohort: {{h1.live.known_1h_pct}}% known at {{one}} hour (threshold {{h1_threshold_1h_pct}}%), {{h1.live.known_48h_pct}}% at {{h1_wait_long_h}} hours (threshold {{h1_threshold_48h_pct}}%).
- H3 (bursts converge slowest): falsified. At {{one}} hour E is {{h3.live_ext.w1h.e_burst|.4f}} for burst edits against {{h3.live_ext.w1h.e_rest|.4f}} for the rest (live_ext).
- H4 (page identity): small effect: {{h4.live_ext.pages_affected_pct}}% of pages (live_ext), {{h4.history.pages_affected_pct}}% (history); below the {{h4_floor_pct}}% floor.

## Slide 8: Two sources, two knowledge axes

- Stream labels against the second History snapshot: {{recon.live.agreement_pct}}% agreement; {{recon.live.stream_only}} stream only, {{recon.live.dump_only}} dump only.
- Time travel on snapshots: {{tt.snapshot.2026_09.reverted_then}} reverted revisions known then, {{tt.snapshot.2026_10.reverted_then}} now.
- Time travel on the stream: {{tt.asof.early.reverted_known}} live reverts known as of 2026-10-24, {{tt.asof.parity.reverted_known}} as of 2026-10-27.

## Slide 9: Streaming algorithms against exact answers

- HyperLogLog in about {{algos.hll_p14.bytes_kb}} kilobytes: mean error {{algos.hll_p14.pages.mean_err_pct|.2f}}% on {{algos.exact.pages}} distinct pages.
- Bloom filter: all {{algos.bloom.fp001.exact_repeats}} repeated events found, none missed.
- DGIM (reverts in the last hour): mean error {{algos.dgim.wiki.r4.mean_rel_error_pct}}% with at most {{algos.dgim.wiki.r4.max_buckets}} buckets.
- AMS second moment: mean absolute error {{moments.ams.v10000.mean_abs_error_pct}}% with {{moments.ams.v10000.variables}} variables.

## Slide 10: Structured Streaming

- Bronze to Silver as a streaming query: 95th percentile latency {{sss.rate2500.latency_p95_s}} seconds at {{sss.rate2500.rate}} events per second, {{sss.rate10000.latency_p95_s}} at {{sss.rate10000.rate}}.
- Drain without a rate limit: {{sss.drain.throughput_eps}} events per second; output equal to the batch tables.

## Slide 11: Locality-sensitive hashing (fallback numbers; a teammate's notebook replaces them)

- MinHash LSH on {{lsh.distinct_texts}} distinct edit summaries: {{lsh.recall_pct.tables5}}% recall against an exact join, in about {{lsh.seconds.tables5}} seconds instead of {{lsh.exact_join_seconds}}.
- Precision on labeled pairs: {{lsh.labels.by_group.same_pattern}} of {{lsh.labels.by_group.pairs}} (one pair per group).
- {{lsh.not_reverted.reuses_pct}}% of edits that were not reverted reuse a summary, against {{lsh.reverted.reuses_pct}}% of reverted edits.

## Slide 12: Privacy (fallback numbers; a teammate's notebook replaces them)

- Figure: `docs/final/figures/privacy_laplace.png`.
- The hourly table is nearly {{privacy.k}}-anonymous ({{privacy.grid.k5.rows_below_pct}}% of cells below). The page-level table is not: {{privacy.page.single_editor_pct}}% of rows have one editor.
- Suppression biases the page-level revert rate from {{privacy.suppress.live_ext.ruleA.true_revert_rate_pct}}% to {{privacy.suppress.live_ext.ruleA.released_revert_rate_pct}}%.
- Laplace noise at epsilon {{privacy.eps_low}} moves E(L) of the main series by {{privacy.laplace.live.stream.all.mae.eps_low|.5f}} on average.

## Slide 13: Deviations and limitations

- Not built: Kafka, Airflow, dbt, the early-signal model (H2). Horizon {{horizon_days}} days, not {{proposal_horizon_days}}.
- One wiki, {{bronze.page_change.event_dates}} days, one laptop.

## Slide 14: CRediT (required)

- The table of the report draft, section CRediT. Each person confirms their row.

## Slide 15: GenAI disclosure

- Code, checks and analysis scripts were written with Claude Code; every number comes from a logged command; the team wrote the text. Details: `docs/final/GENAI_LOG.md`.

## Slide 16: Lessons learned (rubric line)

- From the build: check every sample against its population; check that inputs exist before planning; one Spark session factory; mask comments before export; numbers filled from one file, never typed.
- **TODO (owner):** the team's own lessons.
