# Truth Lag: Measuring How Fast Live Wikipedia Metrics Converge to Reconciled History

**Report draft for the team (source for Tingyu, not the final text).** Group 9, DATA 226. Generated from `docs/final/results.json` at commit `84624f4` (2026-11-15T12:58:49Z). Every number below is filled from that file by `scripts/render_report.py`; edit `docs/final/report_draft.template.md`, never this file. `scripts/check_numbers.py` fails if a number here is not in `results.json`.

How to use it: each section holds the facts and tables the final IEEE-format report needs. Sentences are short fact statements, not report prose: the section owner rewrites them in their own words. Lines that start with **TODO** need a person. Do not quote edit comments anywhere (they can contain names).

## Abstract

Facts for the abstract (the owner writes the abstract):

- Question: after an edit is made on English Wikipedia, how long must a live dashboard wait before its count of reverted edits is close to the final count?
- Measure: E(L), the share of eventual reverts (within 4 days) that are still unknown after waiting L.
- Data: 12,328,679 captured stream events over 28 days and 2 monthly MediaWiki History snapshots (15,892,423 revision rows).
- System: a Bronze, Silver, Gold lakehouse on Delta Lake, written by 2 engines (delta-rs and Spark SQL).
- Main result: in the October cohort 57.95% of eventual reverts are known after 1 hour and 93.72% after 48 hours; E(1 h) = 0.4205.
- Check: the lake reproduces the published EC HW2 tables value for value, and a second History snapshot agrees with the stream labels for 99.86% of 279,466 revisions.

## I. Introduction

- Problem: live counts of "reverted edits" change after the fact, because reverts arrive late. A number shown now is a lower bound of the final number.
- Users: people who read live quality dashboards, and pipelines that train on recent edits.
- Contribution list (owner rewrites):
  - A lakehouse that keeps 4 clocks apart: event time, publish time, snapshot time and lake time.
  - A measured truth-lag curve E(L) for 4 series, with the same definition for stream labels and dump labels.
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
| EventStreams `mediawiki.page_change.v1` | every page change on enwiki, captured from 2026-10-19 to 2026-11-15 | 4,871,014 lines |
| EventStreams revert-risk predictions | one score per revision | 3,113,810 lines |
| EventStreams revision tag changes | includes the `mw-reverted` tag | 4,343,855 lines |
| MediaWiki History, snapshot 2026-09 | September 2026 revisions with revert labels | 5,266,843 revisions |
| MediaWiki History, snapshot 2026-10 | September and October 2026 revisions, cutoff 2026-11-01 01:30:05 UTC | 10,625,580 revisions |

Cohorts (a cohort is a group of revisions studied together):

| Cohort | Edits made (UTC) | Label source | Revisions | Eventual reverts within 4 days |
| --- | --- | --- | --- | --- |
| history | 2026-09-08 to 2026-09-10 | History dump | 295,016 | 17,646 |
| live | 2026-10-20 to 2026-10-22 | stream | 279,466 | 17,818 |
| live_ext | 2026-10-20 to 2026-11-08 | stream | 2,397,738 | 112,937 |

- The capture has 5 gaps longer than 120 seconds.
- Human editors appear only as keyed pseudonyms in every table that leaves the lake.
- **TODO (owner):** one sentence on licensing and on why the data fits the course (volume, velocity, veracity).

## IV. Architecture

Figure: `docs/final/figures/flow.png` (data flow from the sources through Bronze, Silver and Gold to the analyses).

| Layer | Written by | Holds | Tables or rows |
| --- | --- | --- | --- |
| Bronze | delta-rs, append-only | each captured line and each dump row, unchanged | 12,328,679 stream lines, 15,892,423 dump rows |
| Silver | delta-rs with the EC HW2 rules | one clean row per event; cohort tables rebuilt for a knowledge time | 4,871,010 page changes, 3,113,807 scored revisions, 4,343,852 tag events |
| Gold | Spark SQL | star schema and marts | 12 tables; 2,972,220 facts; 2,324,643 page versions of 2,253,040 pages |

- Star schema: `dim_cohort`, `dim_snapshot`, `dim_time`, `dim_user`, `dim_page` (slowly changing dimension, Type 2), `fact_edit`, `fact_revert_label`, and the marts.
- Every build takes a knowledge time ("as of"). The lake was built at 3 knowledge times, so each table's history shows what was known when.
- One engine writes each table. Both engines read every table.
- A full rebuild from the raw files into an empty folder takes about 15 minutes on one laptop and reproduces every number in this draft. 49 automated tests pass.

## V. Methods

### A. Truth-lag error E(L)

- An eventual revert is a revert within 4 days of the edit. It is known at wait L when the time to the revert plus the stream delay is at most L.
- E(L) is one minus known over eventual, at 9 waits from 0 to 4 days.
- Intervals: bootstrap over pages with 2,000 resamples (seed 226), because one page's reverts move together.

### B. Hypotheses

- H1: fewer than 60% of eventual reverts are known within 1 hour, and fewer than 95% within 48 hours.
- H3: at a fixed wait, E(L) is higher for burst edits (the page had 10 or more edits in the hour before) than for other edits.
- H4: joining facts to the page title valid at edit time, instead of the current title, changes page-level revert metrics for a measurable share of pages. Floor used: 1% of pages.
- H2 (early-signal model) was not built.

### C. Parity, reconciliation and time travel

- Parity: every lake table that EC HW2 also published is compared value for value with the published file.
- Reconciliation: stream labels of the live cohort against the labels of History snapshot 2026-10, joined on the revision id.
- Time travel: tables are read at the version written for a knowledge time. Versions are found by commit metadata, not by timestamp.

### D. Course techniques

- Streaming algorithms, each against the exact answer on 4,617,893 events: HyperLogLog, Flajolet-Martin, Bloom filter, DGIM, reservoir sampling, AMS second moment.
- Spark Structured Streaming: the Bronze-to-Silver step as a streaming query, replayed at fixed input rates.
- Locality-sensitive hashing: MinHash LSH on character 5-shingles of edit comments, at Jaccard similarity 0.6 or more, checked against an exact join and against hand-labeled pairs.
- Privacy: k-anonymity (k = 5) and l-diversity (l = 2, sensitive attribute: reverted within 4 days) of the tables that would be released, small-group suppression, and Laplace noise on the E(L) counts at 3 values of epsilon.
- The LSH and privacy numbers below come from the fallback notebooks (`notebooks/fallback/`), built with Claude Code for Scott. **If Wanru's or Zhenni's notebook arrives, its numbers replace these.**

## VI. Results

### A. The lake reproduces the published tables

| Check | Result |
| --- | --- |
| Bronze lines inside the published parse cut, 3 streams | equal for 3 of 3 (1,231,430 page-change lines) |
| Silver stream tables at the published cut | equal for 3 of 3 (1,231,427 page changes) |
| Cohort tables | equal for 6 of 6 (295,016 history and 279,466 live revisions) |
| Gold checks at the extended build | 33 of 33 passed |

### B. Truth-lag curve

Figure: `docs/final/figures/el_curve.png`.

| Wait | history, dump labels | live, stream labels | live, dump labels | live_ext, stream labels |
| --- | --- | --- | --- | --- |
| 1 min | 0.8013 | 0.7763 | 0.7684 | 0.7757 |
| 5 min | 0.6484 | 0.6095 | 0.6131 | 0.6123 |
| 15 min | 0.5615 | 0.5287 | 0.5338 | 0.5277 |
| 1 h | 0.4434 | 0.4205 | 0.4266 | 0.4126 |
| 6 h | 0.2690 | 0.2477 | 0.2549 | 0.2470 |
| 1 d | 0.1104 | 0.1056 | 0.1133 | 0.0950 |
| 2 d | 0.0522 | 0.0628 | 0.0683 | 0.0493 |
| eventual reverts | 17,646 | 17,818 | 18,077 | 112,937 |

- After 1 hour, 10,326 of 17,818 live reverts are known (57.95%).
- By editor kind at 1 hour, live cohort: temporary accounts E = 0.3494, registered accounts E = 0.5031.

### C. Hypotheses

H1, share of eventual reverts known (with 95% intervals). The live cohort is the primary series; the others are robustness checks.

| Series | Eventual reverts | Known at 1 hour | Known at 48 hours | Reading |
| --- | --- | --- | --- | --- |
| live (primary) | 17,818 | 57.95% (56.71 to 59.28) | 93.72% (92.66 to 94.59) | not falsified: both below their thresholds, intervals included |
| live_ext, October edits only | 67,998 | 58.11% (57.29 to 59.0) | 94.64% (94.1 to 95.08) | below both; the long-wait interval crosses its threshold |
| live_ext | 112,937 | 58.74% (58.04 to 59.49) | 95.07% (94.72 to 95.37) | borderline at the long wait: the point estimate is just above its threshold |
| history | 17,646 | 55.66% (54.49 to 56.88) | 94.78% (94.12 to 95.4) | below both; the long-wait interval crosses its threshold |

H3, E(L) for burst edits against the rest:

| Series | Wait | Burst reverts (pages) | E burst | E rest | Burst minus rest | Reading |
| --- | --- | --- | --- | --- | --- | --- |
| live | 1 h | 439 (70) | 0.2255 (0.0479 to 0.4503) | 0.4254 (0.4138 to 0.4369) | -0.1999 (-0.3716 to 0.0097) | intervals overlap |
| live_ext | 1 h | 3,401 (506) | 0.2887 (0.1884 to 0.3965) | 0.4164 (0.4111 to 0.4218) | -0.1277 (-0.2259 to -0.0210) | burst lower, intervals apart |
| history | 1 h | 343 (83) | 0.2566 (0.1367 to 0.4051) | 0.4471 (0.4353 to 0.4587) | -0.1905 (-0.3125 to -0.0532) | burst lower, intervals apart |
| live_ext | 1 d | 3,401 (506) | 0.0641 (0.0120 to 0.1366) | 0.0960 (0.0929 to 0.0991) | -0.0319 (-0.0834 to 0.0475) | intervals overlap |

- H3 is falsified in every series: burst edits are never slower with intervals apart. At 1 hour their reverts become known faster.

H4, title at edit time against current title:

| Measure | history | live_ext |
| --- | --- | --- |
| Facts whose title or namespace differs from now | 3,381 of 295,016 (1.146%) | 16,762 of 2,397,738 (0.699%) |
| Pages affected | 966 of 165,415 (0.584%) | 3,454 of 1,238,130 (0.279%) |
| Title keys whose edit or revert count changes | 1,853 (1.116%) | 6,779 (0.547%) |
| Title keys whose revert count changes | 168 (0.101%) | 601 (0.049%) |

- H4 is falsified at the 1% floor for pages affected in both cohorts. The effect exists but is small.

### D. Second snapshot: label changes and reconciliation

- Loading snapshot 2026-10 was one MERGE commit: 5,358,769 revisions inserted and 40,721 labels changed, of which 40,683 became reverted.
- Of the 2,970 September reverts that EC HW2 found in the stream after the first snapshot, the second snapshot confirms 2,967 (99.9%).

| Live cohort, stream label against dump label | Revisions | Share |
| --- | --- | --- |
| both reverted | 17,752 | 6.352% |
| neither | 261,323 | 93.508% |
| stream only | 66 | 0.024% |
| dump only | 325 | 0.116% |
| not in the dump | 0 | 0.0% |

- Agreement: 99.86%. The stream found 98.2% of the dump's reverts.

### E. Time travel

| Knowledge axis | Then | Now | Changes recorded in the change feed |
| --- | --- | --- | --- |
| History snapshots: reverted history-cohort revisions | 19,858 (snapshot 2026-09) | 20,925 (snapshot 2026-10) | 40,721 labels over all revisions |
| Stream knowledge time: reverted live revisions | 17,040 (as of 2026-10-24) | 17,818 (as of 2026-10-27) | 778 rows, median 2.84 days after the edit |

### F. Streaming algorithms

Exact answers on the same stream: 2,153,428 distinct pages and 229,828 distinct editors. Errors are the mean and standard deviation over 5 hash functions.

| Sketch | Memory (bytes) | Pages: mean error | Pages: SD | Editors: mean error | Editors: SD |
| --- | --- | --- | --- | --- | --- |
| HyperLogLog, 768 bytes | 768 | 1.60% | 2.94% | 0.11% | 2.60% |
| HyperLogLog, 3,072 bytes | 3,072 | 0.60% | 1.20% | -0.56% | 1.60% |
| HyperLogLog, 12,288 bytes | 12,288 | -0.30% | 1.18% | -0.74% | 1.16% |
| Flajolet-Martin, 256 bytes | 256 | 2.05% | 10.21% | 3.30% | 12.26% |
| Flajolet-Martin, 4,096 bytes | 4,096 | 2.37% | 2.88% | 1.44% | 3.63% |

- An exact set of the pages needs an estimated 17.2 megabytes; the largest sketch uses about 12 kilobytes.
- Bloom filter on the event id (8.3 megabytes against an estimated 36.9 for an exact set): all 4 repeated events found, 0 missed, 587 false positives in 4,617,897 events.
- DGIM, reverts in the last hour over the whole wiki: mean error 11.25% with at most 17 buckets (bound 50%), and 5.24% with at most 31 buckets (bound 25%). Per page the counts are tiny and DGIM's error reaches its bound (mean 41.18%).
- Reservoir sample of 10,000 edits: revert share 3.76% (3.387 to 4.133) against the exact 4.046%.
- AMS second moment of edits per page, one run: error -79.94% with 100 variables and -13.5% with 1,000.

Moments and reservoir sampling over many seeds (`notebooks/fallback/moments_reservoir.ipynb`). Exact moments of edits per page: F0 = 1,889,644, F1 = 4,209,083, F2 = 249,630,183.

| AMS variables | Mean absolute error of F2 over 30 seeds | Worst error |
| --- | --- | --- |
| 100 | 63.33% | 84.49% |
| 1,000 | 20.36% | 47.12% |
| 10,000 | 4.59% | 13.16% |

| Reservoir size | Spread of the revert share over 200 reservoirs (points) | Binomial standard error (points) |
| --- | --- | --- |
| 1,000 | 0.693 | 0.623 |
| 10,000 | 0.206 | 0.197 |
| 100,000 | 0.064 | 0.062 |

- A one-pass reservoir of 112,937 not-reverted edits matches the editor-kind mix of all 2,284,801 within 0.08 points.

### G. Structured Streaming

| Input rate (events per second) | Throughput | Median latency (s) | 95th percentile latency (s) |
| --- | --- | --- | --- |
| 1,000 | 981.8 | 1.897 | 2.901 |
| 2,500 | 2428.0 | 2.046 | 3.303 |
| 5,000 | 4717.6 | 2.177 | 3.406 |
| 10,000 | 9391.2 | 2.544 | 4.066 |
| 20,000 | 18275.9 | 3.483 | 5.216 |

- The 95th percentile latency first passes 5 seconds at 20,000 events per second. The proposal's target was 2,500 events per second.
- Without a rate limit the query drains 500,000 events at 16614.6 events per second, and its output equals the batch Silver rows (0 differing).
- For scale: the captured stream averages about 2.1 events per second.

### H. Locality-sensitive hashing

Source: `notebooks/fallback/lsh_minhash.ipynb` (fallback; a teammate's notebook replaces it).

- Input: 91,092 edit comments (26,646 of reverted edits, 64,446 of edits not reverted) with 49,140 distinct texts.
- Against an exact join of 7,998,000 pairs (4,000 texts, 2,162 true near-duplicate pairs, 190.8 seconds), LSH finds 89.32% of them with 1 hash table, 96.11% with 5 and 96.16% with 20, in 0.8 seconds at 5 tables.
- All texts: 420,629 near-duplicate pairs; 9,988 texts have a near-duplicate, in 1,419 groups (largest: 1,186 texts).
- Precision on hand-labeled pairs ("same edit pattern"): 40 of 40 pairs drawn by similarity band (100.0%, interval 91.2 to 100.0), and 37 of 40 pairs drawn one per group (92.5%, interval 80.1 to 97.4). Labels by Claude Code; 0 re-checked by a person so far.
- Reuse of summaries: 24.63% of reverted edits share their summary (exactly or nearly) with another edit, against 72.56% of edits not reverted. Near-duplicate summaries are mostly tool and bot templates, not vandal text.

### I. Privacy

Source: `notebooks/fallback/privacy.ipynb` (fallback; a teammate's notebook replaces it). Figure: `docs/final/figures/privacy_laplace.png`.

- Tables checked: an hourly grid by editor kind (1,875 cells) and a page-level summary (1,559,483 rows).
- k-anonymity, k = 5: 3.95% of grid cells have fewer than 5 editors; suppressing them keeps 99.168% of the edits. In the page summary 98.42% of rows are below k, and 81.63% have a single editor.
- l-diversity, l = 2: 92.69% of grid cells and 4.8% of page rows hold both reverted and not-reverted edits. 2,526 page rows hold only reverted edits, 2,170 of them from one editor.

| Suppression rule, page summary of live_ext | Rows kept | Edits kept | Reverts kept | Revert rate in the release (true 4.71%) |
| --- | --- | --- | --- | --- |
| At least 5 editors | 1.8% | 16.44% | 42.08% | 12.05% |
| At least 5 editors and both values present | 1.04% | 10.47% | 42.05% | 18.92% |

- Suppression alone biases the page-level release upward: only busy pages survive, and they are reverted more often.

| Laplace noise on the E(L) counts: series | Eventual reverts | Mean absolute error of E(L), epsilon 0.1 | epsilon 0.5 | epsilon 1.0 |
| --- | --- | --- | --- | --- |
| live_ext, all editors | 112,937 | 0.00014 | 0.00003 | 0.00001 |
| live, all editors | 17,818 | 0.00093 | 0.00018 | 0.00009 |
| live, temporary accounts | 9,772 | 0.00168 | 0.00035 | 0.00017 |
| live, bots | 141 | 0.15468 | 0.02346 | 0.01204 |

- The noise is edit-level (1,000 trials per epsilon). For the main series the error is far below the differences between series; for the bot series it is not.

## VII. Deviations from the Proposal

- Kafka (or Redpanda), Airflow and dbt were not built. The Bronze tables are the replayable log, and one script runs the steps in order.
- The page dimension is a plain slowly changing dimension (Type 2), not a bitemporal model.
- E(L) uses a 4-day horizon, not 30 days.
- History snapshot 2026-10 was filtered on the laptop, not on the capture server.
- Not built: H2 (early-signal model), experiments E0, E3, E6 and E7.
- **TODO (owner):** one sentence of reason for each, in the team's words.

## VIII. Limitations

- One wiki (English Wikipedia), 28 days of capture, 2 snapshots.
- The stream label needs an exact revert that the stream marks; 325 live revisions are reverted only according to the dump.
- The capture stores no receive time, so the publish time is the "known at" clock.
- Latency and throughput were measured on one laptop, with the producer on the same machine.
- The burst rule also catches edit wars. The burst groups are small (439 reverts in the live cohort).
- The H4 floor (1%) was set after seeing the data.

## IX. Lessons Learned

Rubric line "Lessons learned" (report and presentation), and the Canvas instruction to document key learnings, technical difficulties and best practices. These are facts from the build; the team adds its own.

- **Technical difficulty:** Spark would not start on the laptop until the driver was bound to the loopback address and the network transport was switched; timestamps were shifted until the session was forced to UTC. **Practice:** one session factory that every job uses.
- **Technical difficulty:** a planning note said the second History snapshot was already on the capture server; it was not. **Practice:** check that each input exists before planning work on it.
- **Learning:** a sample drawn by "sample, then limit" was not uniform; it under-sampled the latest edits. It was found only because the reservoir sample was compared with the exact mix of editor kinds. **Practice:** compare every sample with its population before using it.
- **Learning:** a cardinality sketch looked biased on one run; a test on made-up data showed the sketch was right and the spread came from the hash. **Practice:** report several hash salts, not one run.
- **Learning:** edit comments hold user names typed as plain text. **Practice:** mask comments before any export, and do not quote them.
- **Learning:** a failing test went unnoticed because only the last lines of the test output were read. **Practice:** check the exit code.
- **Best practice:** loads that can run twice without changing the table (a re-run writes no new version), and table versions addressed by commit metadata, not by timestamp.
- **Best practice:** every number in this draft is filled from one results file and checked by a script, so no number is typed by hand.
- **TODO (owner):** the team's own lessons (teamwork, tools, what you would do differently), and the text.

## X. Conclusion

- Facts to close on: 57.95% of eventual reverts are known after 1 hour and 89.44% after 1 day; stream and dump labels agree for 99.86% of revisions; the lake reproduces every published number.
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

The criteria in the order of the Canvas rubric (`docs/final/CANVAS_SPEC.md`), each with a runnable command, its output file and its notebook, are in `docs/final/RUBRIC_EVIDENCE.md` (checked by `scripts/check_evidence.py`). Rows marked open there have no evidence yet. **TODO (owner):** paste that table here, fill the open rows with real evidence or leave them stated as not done, and add the external links and the list of tools from the same file.

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
