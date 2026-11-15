# Truth Lag: Measuring How Fast Live Wikipedia Metrics Converge to Reconciled History

**Report draft for the team (source for Tingyu, not the final text).** Group 9, DATA 226. Generated from `docs/final/results.json` at commit `{{meta.commit_short}}` ({{meta.generated_at_utc}}). Every number below is filled from that file by `scripts/render_report.py`; edit `docs/final/report_draft.template.md`, never this file. `scripts/check_numbers.py` fails if a number here is not in `results.json`.

How to use it: each section holds the facts and tables the final IEEE-format report needs. Sentences are short fact statements, not report prose: the section owner rewrites them in their own words. Lines that start with **TODO** need a person. Do not quote edit comments anywhere (they can contain names).

## Abstract

Facts for the abstract (the owner writes the abstract):

- Question: after an edit is made on English Wikipedia, how long must a live dashboard wait before its count of reverted edits is close to the final count?
- Measure: E(L), the share of eventual reverts (within {{horizon_days}} days) that are still unknown after waiting L.
- Data: {{bronze.stream_rows_total}} captured stream events over {{bronze.page_change.event_dates}} days and {{snapshots}} monthly MediaWiki History snapshots ({{bronze.history_slim.rows}} revision rows).
- System: a Bronze, Silver, Gold lakehouse on Delta Lake, written by {{engines}} engines (delta-rs and Spark SQL).
- Main result: in the October cohort {{el.live.stream.all.w1h.share_known|pct2}}% of eventual reverts are known after {{one}} hour and {{el.live.stream.all.w2d.share_known|pct2}}% after {{h1_wait_long_h}} hours; E({{one}} h) = {{el.live.stream.all.w1h.e_l|.4f}}.
- Check: the lake reproduces the published EC HW2 tables value for value, and a second History snapshot agrees with the stream labels for {{recon.live.agreement_pct}}% of {{recon.live.total}} revisions.

## I. Introduction

- Problem: live counts of "reverted edits" change after the fact, because reverts arrive late. A number shown now is a lower bound of the final number.
- Users: people who read live quality dashboards, and pipelines that train on recent edits.
- Contribution list (owner rewrites):
  - A lakehouse that keeps {{clocks}} clocks apart: event time, publish time, snapshot time and lake time.
  - A measured truth-lag curve E(L) for {{el_series}} series, with the same definition for stream labels and dump labels.
  - A reconciliation of stream labels with a later History snapshot, and time travel on both knowledge axes.
  - Course techniques measured against exact answers on the same data: streaming algorithms, Structured Streaming, locality-sensitive hashing, privacy.
- **TODO (owner):** motivation paragraph and one concrete end-user scenario, in the team's own words (the proposal grader asked for this).

## II. Related Work

Pointers only; the owner writes the survey. The team's proposal lists its sources; the numbers in square brackets are the proposal's reference numbers.

- Revisions of published data and "real-time" data sets: [10], [11]. Nowcasting with reporting delay: [12].
- Reverts and quality control on Wikipedia: [15], [16], [17], [18]. The revert-risk model whose scores the stream carries: [19].
- Stream and warehouse foundations: the Dataflow model [20], stream warehouse consistency [21], online aggregation [22], dimensional modeling and slowly changing dimensions [23], time-oriented tables [24].
- Techniques used here: Delta Lake (Armbrust et al.), Structured Streaming (Armbrust et al.), HyperLogLog [25], Flajolet-Martin counting, Bloom filters, DGIM, AMS moments, reservoir sampling, MinHash and LSH, k-anonymity, l-diversity, differential privacy. Full entries are under References.
- **TODO (owner):** state the gap in one paragraph: prior work measures revert delay; it does not measure the error of a live count as a function of the wait.

## III. Data

| Source | What | Size in the lake |
| --- | --- | --- |
| EventStreams `mediawiki.page_change.v1` | every page change on enwiki, captured from 2026-10-19 to 2026-11-15 | {{bronze.page_change.rows}} lines |
| EventStreams revert-risk predictions | one score per revision | {{bronze.revert_risk.rows}} lines |
| EventStreams revision tag changes | includes the `mw-reverted` tag | {{bronze.tags.rows}} lines |
| MediaWiki History, snapshot 2026-09 | September 2026 revisions with revert labels | {{silver.history_slim.rows.2026_09}} revisions |
| MediaWiki History, snapshot 2026-10 | September and October 2026 revisions, cutoff {{text.snapshot_2026_10.cutoff}} | {{silver.history_slim.rows.2026_10}} revisions |

Cohorts (a cohort is a group of revisions studied together):

| Cohort | Edits made (UTC) | Label source | Revisions | Eventual reverts within {{horizon_days}} days |
| --- | --- | --- | --- | --- |
| history | {{text.history_window}} | History dump | {{gold.fact_edit.rows.history}} | {{el.history.dump.all.w4d.n_eventual}} |
| live | {{text.live_window}} | stream | {{gold.fact_edit.rows.live}} | {{el.live.stream.all.w4d.n_eventual}} |
| live_ext | {{text.live_ext_window}} | stream | {{gold.fact_edit.rows.live_ext}} | {{el.live_ext.stream.all.w4d.n_eventual}} |

- The capture has {{silver.capture_gaps.rows}} gaps longer than {{gap_min_s}} seconds.
- Human editors appear only as keyed pseudonyms in every table that leaves the lake.
- **TODO (owner):** one sentence on licensing and on why the data fits the course (volume, velocity, veracity).

## IV. Architecture

Figure: `docs/final/figures/flow.png` (data flow from the sources through Bronze, Silver and Gold to the analyses).

| Layer | Written by | Holds | Tables or rows |
| --- | --- | --- | --- |
| Bronze | delta-rs, append-only | each captured line and each dump row, unchanged | {{bronze.stream_rows_total}} stream lines, {{bronze.history_slim.rows}} dump rows |
| Silver | delta-rs with the EC HW2 rules | one clean row per event; cohort tables rebuilt for a knowledge time | {{silver.page_change.rows}} page changes, {{silver.revert_risk.rows}} scored revisions, {{silver.tag_events.rows}} tag events |
| Gold | Spark SQL | star schema and marts | {{gold.tables}} tables; {{gold.fact_edit.rows}} facts; {{gold.dim_page.rows}} page versions of {{gold.dim_page.pages}} pages |

- Star schema: `dim_cohort`, `dim_snapshot`, `dim_time`, `dim_user`, `dim_page` (slowly changing dimension, Type 2), `fact_edit`, `fact_revert_label`, and the marts.
- Every build takes a knowledge time ("as of"). The lake was built at {{asof_builds}} knowledge times, so each table's history shows what was known when.
- One engine writes each table. Both engines read every table.
- A full rebuild from the raw files into an empty folder takes about {{runtime.rebuild_e2e_min}} minutes on one laptop and reproduces every number in this draft. {{tests.passed}} automated tests pass.

## V. Methods

### A. Truth-lag error E(L)

- An eventual revert is a revert within {{horizon_days}} days of the edit. It is known at wait L when the time to the revert plus the stream delay is at most L.
- E(L) is one minus known over eventual, at {{wait_points}} waits from {{zero}} to {{horizon_days}} days.
- Intervals: bootstrap over pages with {{bootstrap_B}} resamples (seed {{seed}}), because one page's reverts move together.

### B. Hypotheses

- H1: fewer than {{h1_threshold_1h_pct}}% of eventual reverts are known within {{one}} hour, and fewer than {{h1_threshold_48h_pct}}% within {{h1_wait_long_h}} hours.
- H3: at a fixed wait, E(L) is higher for burst edits (the page had {{burst_min_edits}} or more edits in the hour before) than for other edits.
- H4: joining facts to the page title valid at edit time, instead of the current title, changes page-level revert metrics for a measurable share of pages. Floor used: {{h4_floor_pct}}% of pages.
- H2 (early-signal model) was not built.

### C. Parity, reconciliation and time travel

- Parity: every lake table that EC HW2 also published is compared value for value with the published file.
- Reconciliation: stream labels of the live cohort against the labels of History snapshot 2026-10, joined on the revision id.
- Time travel: tables are read at the version written for a knowledge time. Versions are found by commit metadata, not by timestamp.

### D. Course techniques

- Streaming algorithms, each against the exact answer on {{algos.stream_events}} events: HyperLogLog, Flajolet-Martin, Bloom filter, DGIM, reservoir sampling, AMS second moment.
- Spark Structured Streaming: the Bronze-to-Silver step as a streaming query, replayed at fixed input rates.
- Locality-sensitive hashing (MinHash) on the comments of reverted edits. **TODO: numbers from `notebooks/fallback/lsh_minhash.ipynb` or Wanru's notebook.**
- Privacy: k-anonymity, l-diversity and Laplace noise on the published marts. **TODO: numbers from `notebooks/fallback/privacy.ipynb` or Zhenni's notebook.**

## VI. Results

### A. The lake reproduces the published tables

| Check | Result |
| --- | --- |
| Bronze lines inside the published parse cut, {{streams}} streams | equal for {{parity.bronze.streams_equal}} of {{streams}} ({{bronze.page_change.lines_in_published_cut}} page-change lines) |
| Silver stream tables at the published cut | equal for {{parity.silver.tables_equal}} of {{streams}} ({{parity.silver.page_change.rows}} page changes) |
| Cohort tables | equal for {{parity.cohort.tables_equal}} of {{parity.cohort.tables}} ({{parity.cohort.history_revisions.rows}} history and {{parity.cohort.live_revisions.rows}} live revisions) |
| Gold checks at the extended build | {{gold_checks.ext.passed}} of {{gold_checks.ext.total}} passed |

### B. Truth-lag curve

Figure: `docs/final/figures/el_curve.png`.

| Wait | history, dump labels | live, stream labels | live, dump labels | live_ext, stream labels |
| --- | --- | --- | --- | --- |
| {{one}} min | {{el.history.dump.all.w1min.e_l|.4f}} | {{el.live.stream.all.w1min.e_l|.4f}} | {{el.live.dump.all.w1min.e_l|.4f}} | {{el.live_ext.stream.all.w1min.e_l|.4f}} |
| {{wait_5}} min | {{el.history.dump.all.w5min.e_l|.4f}} | {{el.live.stream.all.w5min.e_l|.4f}} | {{el.live.dump.all.w5min.e_l|.4f}} | {{el.live_ext.stream.all.w5min.e_l|.4f}} |
| {{wait_15}} min | {{el.history.dump.all.w15min.e_l|.4f}} | {{el.live.stream.all.w15min.e_l|.4f}} | {{el.live.dump.all.w15min.e_l|.4f}} | {{el.live_ext.stream.all.w15min.e_l|.4f}} |
| {{one}} h | {{el.history.dump.all.w1h.e_l|.4f}} | {{el.live.stream.all.w1h.e_l|.4f}} | {{el.live.dump.all.w1h.e_l|.4f}} | {{el.live_ext.stream.all.w1h.e_l|.4f}} |
| {{wait_6}} h | {{el.history.dump.all.w6h.e_l|.4f}} | {{el.live.stream.all.w6h.e_l|.4f}} | {{el.live.dump.all.w6h.e_l|.4f}} | {{el.live_ext.stream.all.w6h.e_l|.4f}} |
| {{one}} d | {{el.history.dump.all.w1d.e_l|.4f}} | {{el.live.stream.all.w1d.e_l|.4f}} | {{el.live.dump.all.w1d.e_l|.4f}} | {{el.live_ext.stream.all.w1d.e_l|.4f}} |
| {{two}} d | {{el.history.dump.all.w2d.e_l|.4f}} | {{el.live.stream.all.w2d.e_l|.4f}} | {{el.live.dump.all.w2d.e_l|.4f}} | {{el.live_ext.stream.all.w2d.e_l|.4f}} |
| eventual reverts | {{el.history.dump.all.w4d.n_eventual}} | {{el.live.stream.all.w4d.n_eventual}} | {{el.live.dump.all.w4d.n_eventual}} | {{el.live_ext.stream.all.w4d.n_eventual}} |

- After {{one}} hour, {{el.live.stream.all.w1h.n_known}} of {{el.live.stream.all.w1h.n_eventual}} live reverts are known ({{el.live.stream.all.w1h.share_known|pct2}}%).
- By editor kind at {{one}} hour, live cohort: temporary accounts E = {{el.live.stream.temporary.w1h.e_l|.4f}}, registered accounts E = {{el.live.stream.registered.w1h.e_l|.4f}}.

### C. Hypotheses

H1, share of eventual reverts known (with {{ci_level_pct}}% intervals). The live cohort is the primary series; the others are robustness checks.

| Series | Eventual reverts | Known at {{one}} hour | Known at {{h1_wait_long_h}} hours | Reading |
| --- | --- | --- | --- | --- |
| live (primary) | {{h1.live.eventual_reverts}} | {{h1.live.known_1h_pct}}% ({{h1.live.known_1h_lo}} to {{h1.live.known_1h_hi}}) | {{h1.live.known_48h_pct}}% ({{h1.live.known_48h_lo}} to {{h1.live.known_48h_hi}}) | not falsified: both below their thresholds, intervals included |
| live_ext, October edits only | {{h1.live_ext_october.eventual_reverts}} | {{h1.live_ext_october.known_1h_pct}}% ({{h1.live_ext_october.known_1h_lo}} to {{h1.live_ext_october.known_1h_hi}}) | {{h1.live_ext_october.known_48h_pct}}% ({{h1.live_ext_october.known_48h_lo}} to {{h1.live_ext_october.known_48h_hi}}) | below both; the long-wait interval crosses its threshold |
| live_ext | {{h1.live_ext.eventual_reverts}} | {{h1.live_ext.known_1h_pct}}% ({{h1.live_ext.known_1h_lo}} to {{h1.live_ext.known_1h_hi}}) | {{h1.live_ext.known_48h_pct}}% ({{h1.live_ext.known_48h_lo}} to {{h1.live_ext.known_48h_hi}}) | borderline at the long wait: the point estimate is just above its threshold |
| history | {{h1.history.eventual_reverts}} | {{h1.history.known_1h_pct}}% ({{h1.history.known_1h_lo}} to {{h1.history.known_1h_hi}}) | {{h1.history.known_48h_pct}}% ({{h1.history.known_48h_lo}} to {{h1.history.known_48h_hi}}) | below both; the long-wait interval crosses its threshold |

H3, E(L) for burst edits against the rest:

| Series | Wait | Burst reverts (pages) | E burst | E rest | Burst minus rest | Reading |
| --- | --- | --- | --- | --- | --- | --- |
| live | {{one}} h | {{h3.live.w1h.burst_reverts}} ({{h3.live.w1h.burst_pages}}) | {{h3.live.w1h.e_burst|.4f}} ({{h3.live.w1h.e_burst_lo|.4f}} to {{h3.live.w1h.e_burst_hi|.4f}}) | {{h3.live.w1h.e_rest|.4f}} ({{h3.live.w1h.e_rest_lo|.4f}} to {{h3.live.w1h.e_rest_hi|.4f}}) | {{h3.live.w1h.diff|.4f}} ({{h3.live.w1h.diff_lo|.4f}} to {{h3.live.w1h.diff_hi|.4f}}) | intervals overlap |
| live_ext | {{one}} h | {{h3.live_ext.w1h.burst_reverts}} ({{h3.live_ext.w1h.burst_pages}}) | {{h3.live_ext.w1h.e_burst|.4f}} ({{h3.live_ext.w1h.e_burst_lo|.4f}} to {{h3.live_ext.w1h.e_burst_hi|.4f}}) | {{h3.live_ext.w1h.e_rest|.4f}} ({{h3.live_ext.w1h.e_rest_lo|.4f}} to {{h3.live_ext.w1h.e_rest_hi|.4f}}) | {{h3.live_ext.w1h.diff|.4f}} ({{h3.live_ext.w1h.diff_lo|.4f}} to {{h3.live_ext.w1h.diff_hi|.4f}}) | burst lower, intervals apart |
| history | {{one}} h | {{h3.history.w1h.burst_reverts}} ({{h3.history.w1h.burst_pages}}) | {{h3.history.w1h.e_burst|.4f}} ({{h3.history.w1h.e_burst_lo|.4f}} to {{h3.history.w1h.e_burst_hi|.4f}}) | {{h3.history.w1h.e_rest|.4f}} ({{h3.history.w1h.e_rest_lo|.4f}} to {{h3.history.w1h.e_rest_hi|.4f}}) | {{h3.history.w1h.diff|.4f}} ({{h3.history.w1h.diff_lo|.4f}} to {{h3.history.w1h.diff_hi|.4f}}) | burst lower, intervals apart |
| live_ext | {{one}} d | {{h3.live_ext.w1d.burst_reverts}} ({{h3.live_ext.w1d.burst_pages}}) | {{h3.live_ext.w1d.e_burst|.4f}} ({{h3.live_ext.w1d.e_burst_lo|.4f}} to {{h3.live_ext.w1d.e_burst_hi|.4f}}) | {{h3.live_ext.w1d.e_rest|.4f}} ({{h3.live_ext.w1d.e_rest_lo|.4f}} to {{h3.live_ext.w1d.e_rest_hi|.4f}}) | {{h3.live_ext.w1d.diff|.4f}} ({{h3.live_ext.w1d.diff_lo|.4f}} to {{h3.live_ext.w1d.diff_hi|.4f}}) | intervals overlap |

- H3 is falsified in every series: burst edits are never slower with intervals apart. At {{one}} hour their reverts become known faster.

H4, title at edit time against current title:

| Measure | history | live_ext |
| --- | --- | --- |
| Facts whose title or namespace differs from now | {{h4.history.facts_title_differs}} of {{h4.history.facts}} ({{h4.history.facts_title_differs_pct}}%) | {{h4.live_ext.facts_title_differs}} of {{h4.live_ext.facts}} ({{h4.live_ext.facts_title_differs_pct}}%) |
| Pages affected | {{h4.history.pages_affected}} of {{h4.history.pages}} ({{h4.history.pages_affected_pct}}%) | {{h4.live_ext.pages_affected}} of {{h4.live_ext.pages}} ({{h4.live_ext.pages_affected_pct}}%) |
| Title keys whose edit or revert count changes | {{h4.history.titles_changed}} ({{h4.history.titles_changed_pct}}%) | {{h4.live_ext.titles_changed}} ({{h4.live_ext.titles_changed_pct}}%) |
| Title keys whose revert count changes | {{h4.history.titles_reverts_changed}} ({{h4.history.titles_reverts_changed_pct}}%) | {{h4.live_ext.titles_reverts_changed}} ({{h4.live_ext.titles_reverts_changed_pct}}%) |

- H4 is falsified at the {{h4_floor_pct}}% floor for pages affected in both cohorts. The effect exists but is small.

### D. Second snapshot: label changes and reconciliation

- Loading snapshot 2026-10 was one MERGE commit: {{snapshot.label_merge.inserted}} revisions inserted and {{snapshot.label_merge.updated}} labels changed, of which {{snapshot.label_change.became_reverted}} became reverted.
- Of the {{snapshot.late_reverts.exact.n}} September reverts that EC HW2 found in the stream after the first snapshot, the second snapshot confirms {{snapshot.late_reverts.exact.confirmed}} ({{snapshot.late_reverts.exact.confirmed_pct}}%).

| Live cohort, stream label against dump label | Revisions | Share |
| --- | --- | --- |
| both reverted | {{recon.live.both_reverted}} | {{recon.live.both_reverted.pct}}% |
| neither | {{recon.live.neither}} | {{recon.live.neither.pct}}% |
| stream only | {{recon.live.stream_only}} | {{recon.live.stream_only.pct}}% |
| dump only | {{recon.live.dump_only}} | {{recon.live.dump_only.pct}}% |
| not in the dump | {{recon.live.not_in_dump}} | {{recon.live.not_in_dump.pct}}% |

- Agreement: {{recon.live.agreement_pct}}%. The stream found {{recon.live.stream_found_of_dump_pct}}% of the dump's reverts.

### E. Time travel

| Knowledge axis | Then | Now | Changes recorded in the change feed |
| --- | --- | --- | --- |
| History snapshots: reverted history-cohort revisions | {{tt.snapshot.2026_09.reverted_then}} (snapshot 2026-09) | {{tt.snapshot.2026_10.reverted_then}} (snapshot 2026-10) | {{snapshot.label_merge.updated}} labels over all revisions |
| Stream knowledge time: reverted live revisions | {{tt.asof.early.reverted_known}} (as of 2026-10-24) | {{tt.asof.parity.reverted_known}} (as of 2026-10-27) | {{tt.asof.updates}} rows, median {{tt.asof.median_known_after_days}} days after the edit |

### F. Streaming algorithms

Exact answers on the same stream: {{algos.exact.pages}} distinct pages and {{algos.exact.editors}} distinct editors. Errors are the mean and standard deviation over {{hash_salts}} hash functions.

| Sketch | Memory (bytes) | Pages: mean error | Pages: SD | Editors: mean error | Editors: SD |
| --- | --- | --- | --- | --- | --- |
| HyperLogLog, {{algos.hll_p10.pages.bytes}} bytes | {{algos.hll_p10.pages.bytes}} | {{algos.hll_p10.pages.mean_err_pct|.2f}}% | {{algos.hll_p10.pages.sd_err_pct|.2f}}% | {{algos.hll_p10.editors.mean_err_pct|.2f}}% | {{algos.hll_p10.editors.sd_err_pct|.2f}}% |
| HyperLogLog, {{algos.hll_p12.pages.bytes}} bytes | {{algos.hll_p12.pages.bytes}} | {{algos.hll_p12.pages.mean_err_pct|.2f}}% | {{algos.hll_p12.pages.sd_err_pct|.2f}}% | {{algos.hll_p12.editors.mean_err_pct|.2f}}% | {{algos.hll_p12.editors.sd_err_pct|.2f}}% |
| HyperLogLog, {{algos.hll_p14.pages.bytes}} bytes | {{algos.hll_p14.pages.bytes}} | {{algos.hll_p14.pages.mean_err_pct|.2f}}% | {{algos.hll_p14.pages.sd_err_pct|.2f}}% | {{algos.hll_p14.editors.mean_err_pct|.2f}}% | {{algos.hll_p14.editors.sd_err_pct|.2f}}% |
| Flajolet-Martin, {{algos.fm_m64.pages.bytes}} bytes | {{algos.fm_m64.pages.bytes}} | {{algos.fm_m64.pages.mean_err_pct|.2f}}% | {{algos.fm_m64.pages.sd_err_pct|.2f}}% | {{algos.fm_m64.editors.mean_err_pct|.2f}}% | {{algos.fm_m64.editors.sd_err_pct|.2f}}% |
| Flajolet-Martin, {{algos.fm_m1024.pages.bytes}} bytes | {{algos.fm_m1024.pages.bytes}} | {{algos.fm_m1024.pages.mean_err_pct|.2f}}% | {{algos.fm_m1024.pages.sd_err_pct|.2f}}% | {{algos.fm_m1024.editors.mean_err_pct|.2f}}% | {{algos.fm_m1024.editors.sd_err_pct|.2f}}% |

- An exact set of the pages needs an estimated {{algos.exact.pages_bytes_mb_est}} megabytes; the largest sketch uses about {{algos.hll_p14.bytes_kb}} kilobytes.
- Bloom filter on the event id ({{algos.bloom.fp001.bloom_mb}} megabytes against an estimated {{algos.bloom.fp001.exact_set_mb_est}} for an exact set): all {{algos.bloom.fp001.exact_repeats}} repeated events found, {{algos.bloom.fp001.false_negatives}} missed, {{algos.bloom.fp001.false_positives}} false positives in {{algos.bloom.fp001.events}} events.
- DGIM, reverts in the last hour over the whole wiki: mean error {{algos.dgim.wiki.r2.mean_rel_error_pct}}% with at most {{algos.dgim.wiki.r2.max_buckets}} buckets (bound {{algos.dgim.wiki.r2.bound_pct|.0f}}%), and {{algos.dgim.wiki.r4.mean_rel_error_pct}}% with at most {{algos.dgim.wiki.r4.max_buckets}} buckets (bound {{algos.dgim.wiki.r4.bound_pct|.0f}}%). Per page the counts are tiny and DGIM's error reaches its bound (mean {{algos.dgim.page.r2.mean_rel_error_pct}}%).
- Reservoir sample of {{reservoir_k}} edits: revert share {{algos.reservoir.sample_pct}}% ({{algos.reservoir.ci_lo}} to {{algos.reservoir.ci_hi}}) against the exact {{algos.reservoir.exact_pct}}%.
- AMS second moment of edits per page: error {{algos.ams.vars100.err_pct}}% with {{ams_vars_small}} variables and {{algos.ams.vars1000.err_pct}}% with {{ams_vars_large}}.

### G. Structured Streaming

| Input rate (events per second) | Throughput | Median latency (s) | 95th percentile latency (s) |
| --- | --- | --- | --- |
| {{sss.rate1000.rate}} | {{sss.rate1000.throughput_eps}} | {{sss.rate1000.latency_p50_s}} | {{sss.rate1000.latency_p95_s}} |
| {{sss.rate2500.rate}} | {{sss.rate2500.throughput_eps}} | {{sss.rate2500.latency_p50_s}} | {{sss.rate2500.latency_p95_s}} |
| {{sss.rate5000.rate}} | {{sss.rate5000.throughput_eps}} | {{sss.rate5000.latency_p50_s}} | {{sss.rate5000.latency_p95_s}} |
| {{sss.rate10000.rate}} | {{sss.rate10000.throughput_eps}} | {{sss.rate10000.latency_p50_s}} | {{sss.rate10000.latency_p95_s}} |
| {{sss.rate20000.rate}} | {{sss.rate20000.throughput_eps}} | {{sss.rate20000.latency_p50_s}} | {{sss.rate20000.latency_p95_s}} |

- The 95th percentile latency first passes {{e5_latency_limit_s}} seconds at {{sss.rate20000.rate}} events per second. The proposal's target was {{e5_target_eps}} events per second.
- Without a rate limit the query drains {{sss.drain.events}} events at {{sss.drain.throughput_eps}} events per second, and its output equals the batch Silver rows ({{sss.drain.differing}} differing).
- For scale: the captured stream averages about {{sss.capture_mean_eps}} events per second.

### H. Locality-sensitive hashing

**TODO: fill from `notebooks/fallback/lsh_minhash.ipynb` (or Wanru's notebook, which wins if it arrives).**

### I. Privacy

**TODO: fill from `notebooks/fallback/privacy.ipynb` (or Zhenni's notebook, which wins if it arrives).**

## VII. Deviations from the Proposal

- Kafka (or Redpanda), Airflow and dbt were not built. The Bronze tables are the replayable log, and one script runs the steps in order.
- The page dimension is a plain slowly changing dimension (Type 2), not a bitemporal model.
- E(L) uses a {{horizon_days}}-day horizon, not {{proposal_horizon_days}} days.
- History snapshot 2026-10 was filtered on the laptop, not on the capture server.
- Not built: H2 (early-signal model), experiments E0, E3, E6 and E7.
- **TODO (owner):** one sentence of reason for each, in the team's words.

## VIII. Limitations

- One wiki (English Wikipedia), {{bronze.page_change.event_dates}} days of capture, {{snapshots}} snapshots.
- The stream label needs an exact revert that the stream marks; {{recon.live.dump_only}} live revisions are reverted only according to the dump.
- The capture stores no receive time, so the publish time is the "known at" clock.
- Latency and throughput were measured on one laptop, with the producer on the same machine.
- The burst rule also catches edit wars. The burst groups are small ({{h3.live.w1h.burst_reverts}} reverts in the live cohort).
- The H4 floor ({{h4_floor_pct}}%) was set after seeing the data.

## IX. Conclusion

- Facts to close on: {{el.live.stream.all.w1h.share_known|pct2}}% of eventual reverts are known after {{one}} hour and {{el.live.stream.all.w1d.share_known|pct2}}% after {{one}} day; stream and dump labels agree for {{recon.live.agreement_pct}}% of revisions; the lake reproduces every published number.
- **TODO (owner):** what a dashboard owner should do with the curve, and next steps.

## CRediT (Contributor Roles)

Proposed from the team message of 2026-11-15; each person confirms or corrects their row. If a fallback notebook built by Claude Code for Scott is used, the software credit for that technique moves to Scott's row and the GenAI disclosure names it.

| Person | Roles |
| --- | --- |
| Scott | Conceptualization, Software (lakehouse, hypotheses, streaming algorithms, Structured Streaming), Data curation, Validation |
| Wanru | Software and Investigation (MinHash LSH; Neo4j and History section) |
| Zhenni | Software and Investigation (privacy checks; MongoDB Charts), Visualization |
| Tingyu | Writing (report and slides), Visualization (flow diagram), Project administration (rubric appendix) |

## GenAI Disclosure

- The lakehouse code, its checks, the analysis scripts, this draft's tables and the fallback notebooks were written with Claude Code (Anthropic), from a plan and prototypes also drafted with Claude Code. Details per component: `docs/final/GENAI_LOG.md`.
- All code ran on the real data, and every number comes from a logged command (`docs/final/RESULTS.md`, `docs/final/results.json`).
- No LLM or deep learning method is part of the analysis.
- **TODO (owner):** state what each person checked, and that the team wrote the report and slide text.

## Appendix: Rubric Criteria in Order

The table of criteria with a runnable command and its output file for each is `docs/final/RUBRIC_EVIDENCE.md` (checked by `scripts/check_evidence.py`). **TODO (owner):** paste that table here in the order of the official rubric on Canvas.

## References

Entries marked (proposal) are the team's proposal references with their proposal numbers; the others are the standard sources of the techniques. The owner converts them to IEEE style and checks each one.

- [10] D. Croushore, T. Stark. A Real-Time Data Set for Macroeconomists. J. Econometrics 105(1), 2001. (proposal)
- [11] S. B. Aruoba. Data Revisions Are Not Well Behaved. J. Money, Credit and Banking 40(2-3), 2008. (proposal)
- [12] M. Höhle, M. an der Heiden. Bayesian Nowcasting during the STEC O104:H4 Outbreak in Germany, 2011. Biometrics 70(4), 2014. (proposal)
- [15] R. Priedhorsky et al. Creating, Destroying, and Restoring Value in Wikipedia. GROUP 2007. (proposal)
- [16] S. Kumar, R. West, J. Leskovec. Disinformation on the Web. WWW 2016. (proposal)
- [17] R. S. Geiger, A. Halfaker. When the Levee Breaks. OpenSym 2013. (proposal)
- [18] F. Flöck, D. Vrandečić, E. Simperl. Revisiting Reverts. HT 2012. (proposal)
- [19] M. Trokhymovych et al. Fair Multilingual Vandalism Detection System for Wikipedia. KDD 2023. (proposal)
- [20] T. Akidau et al. The Dataflow Model. PVLDB 8(12), 2015. (proposal)
- [21] L. Golab, T. Johnson. Consistency in a Stream Warehouse. CIDR 2011. (proposal)
- [22] J. M. Hellerstein, P. J. Haas, H. J. Wang. Online Aggregation. SIGMOD 1997. (proposal)
- [23] R. Kimball, M. Ross. The Data Warehouse Toolkit, 3rd ed. Wiley, 2013. (proposal)
- [24] R. T. Snodgrass. Developing Time-Oriented Database Applications in SQL. Morgan Kaufmann, 2000. (proposal)
- [25] P. Flajolet, É. Fusy, O. Gandouet, F. Meunier. HyperLogLog: the Analysis of a Near-Optimal Cardinality Estimation Algorithm. AofA 2007. (proposal)
- M. Armbrust et al. Delta Lake: High-Performance ACID Table Storage over Cloud Object Stores. PVLDB 13(12), 2020.
- M. Armbrust et al. Structured Streaming: A Declarative API for Real-Time Applications in Apache Spark. SIGMOD 2018.
- P. Flajolet, G. N. Martin. Probabilistic Counting Algorithms for Data Base Applications. J. Computer and System Sciences 31(2), 1985.
- B. H. Bloom. Space/Time Trade-offs in Hash Coding with Allowable Errors. Communications of the ACM 13(7), 1970.
- M. Datar, A. Gionis, P. Indyk, R. Motwani. Maintaining Stream Statistics over Sliding Windows. SIAM J. Computing 31(6), 2002.
- N. Alon, Y. Matias, M. Szegedy. The Space Complexity of Approximating the Frequency Moments. STOC 1996.
- J. S. Vitter. Random Sampling with a Reservoir. ACM Trans. Mathematical Software 11(1), 1985.
- A. Z. Broder. On the Resemblance and Containment of Documents. SEQUENCES 1997.
- P. Indyk, R. Motwani. Approximate Nearest Neighbors: Towards Removing the Curse of Dimensionality. STOC 1998.
- L. Sweeney. k-Anonymity: A Model for Protecting Privacy. Int. J. Uncertainty, Fuzziness and Knowledge-Based Systems 10(5), 2002.
- A. Machanavajjhala, D. Kifer, J. Gehrke, M. Venkitasubramaniam. l-Diversity: Privacy Beyond k-Anonymity. ACM TKDD 1(1), 2007.
- C. Dwork, F. McSherry, K. Nissim, A. Smith. Calibrating Noise to Sensitivity in Private Data Analysis. TCC 2006.
