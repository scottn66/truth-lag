# Decisions from Scott (2026-11-13)

These answer "Open decisions for Scott" in `PLAN.md`. Where they differ from the plan, this file wins.

## Answers

1. **Engines.** The hybrid is accepted, reluctantly: delta-rs writes Bronze and Silver, Spark SQL writes Gold.
2. **Kafka or Redpanda.** Leaving it out is accepted. The report states it as a deviation from the proposal.
3. **2026-10 History snapshot.** It is on the VPS. So Phase 0 step 8 changes: Scott copies the 2026-10 files from the VPS into `data/history_raw/2026-10/` (rsync, never `--delete`). No download from the dump host is needed. Not yet known: which files are there (raw `.tsv.bz2` month files or filtered files), and whether the small `2026-10.enwiki.2026-11.tsv.bz2` file is among them.
4. **Deadline.** Tuesday 2026-11-17, 11:59 PM. Report, slides and code are uploaded to Canvas.
5. **Hypotheses and experiments.** Defined below.

Still open: the branch name, the tag for the submitted EC HW2 state, and where the GenAI log for the final project lives.

## Hypotheses H1 to H4

Source: `TruthLag_Problem_Statement.md` v0.2 (Oct 15). Thresholds were never fixed. The proposal's E2 uses another H1 to H3 numbering; ignore it.

- **H1, long-tailed lag.** In the October 2026 cohort, under 60% of eventual reverts are visible in the stream within 1 h, and under 95% within 48 h. Falsified if either share is above its threshold.
- **H2, early signals beat waiting.** Page signals available W minutes after an edit (edit velocity, distinct editors, share of temporary accounts and bots, live revert-risk score) predict the later revert label better than the "survived so far" baseline at the same lag, by PR-AUC. Falsified if the bootstrap interval of the gain over B0 and B2 includes 0.
- **H3, bursty pages converge slowest.** At a fixed L, the truth-lag error is higher on bursty page-hours than on other page-hours. Falsified if the intervals overlap.
- **H4, page identity matters.** Joining revert labels to the `dim_page` version current at event time changes page-level revert metrics for a measurable share of pages, against a current-title join. Falsified if the share is below a floor that is still to be set.

## Experiments E0 to E7

Source: the proposal document "Project Proposal – Group 9", Tab 3, section 4.4.

- **E0.** e(Δ) for net surviving edits N matches the Kaplan-Meier prediction.
- **E1.** e(Δ) and time-to-trust T(ε) per metric and stratum, for the tiers V0 (naive), V1 (stream revert ranges) and V1t (`mw-reverted` tags). The 2026-10 snapshot validates Cohort A (H = 30 d) and Oct 1 to 24 (H = 7 d). V3 compares September across snapshots.
- **E2.** Superseded by H1 to H4 above.
- **E3.** The MongoDB state equals the warehouse rebuild as of the same knowledge time.
- **E4.** HyperLogLog for wiki-wide distinct editors and pages, beside the truth-lag error.
- **E5.** Replay until p95 latency is over 5 s (target: 2,500 events per second or more).
- **E6.** Volume: the full enwiki History, file by file, with yearly revert and deletion curves since 2010.
- **E7.** Stretch: a reporting-triangle nowcast. The proposal drops E7 first. The minimum was E0 and E1 for N and the top 10.

## How the plan covers them

| Item | Covered by the plan as written | Gap |
| --- | --- | --- |
| H1 | Yes. The published live numbers already answer it: 57.95% known at 1 h, and `mart_el_curve` gives the 2 d point. | The 48 h share is 16,699 of 17,818 = 93.7%. State the result against both thresholds. |
| H2 | No. | Needs a model on early page signals. Not in any phase. |
| H3 | Partly. `mart_el_by_burst` compares burst revisions with the rest. | H3 is stated per page-hour and asks for intervals; the plan has intervals as a stretch item. |
| H4 | Yes. Phase 4 reports facts whose title at edit time differs from the current title. | H4 asks for the change in page-level revert metrics, not only a count of facts. One more query. |
| E1 | Partly. Phase 5 gives the dump labels for the live cohort and the September comparison across snapshots (V3). | The 30-day horizon for the history cohort and the Oct 1 to 24 cohort are not built. The capture starts on Oct 19, so Oct 1 to 18 has no stream side. |
| E3 | Related: the ordered rebuild shows the lake "as of" a time. | The comparison with MongoDB is not built. |
| E0, E4, E5, E6, E7 | No. | Not in any phase. |

## What the rubric asks for that the plan does not build

The rubric (100 points) names these, 5 points each unless noted. The plan was written before the rubric was seen.

| Rubric item | In the plan | Cheapest honest way to add it |
| --- | --- | --- |
| Streaming algorithms (Reservoir Sampling, Bloom filter, Flajolet-Martin, DGIM, moments) | No | E4 fits here: HyperLogLog or Flajolet-Martin for distinct editors and pages over the Bronze stream, checked against the exact count. A Bloom filter on `meta_id` for the repeat check, measured against the MERGE. DGIM for reverts in the last hour per page. |
| Stream processing frameworks (Spark, Flink, Kafka) | Partly: Spark SQL in batch | Spark Structured Streaming from Bronze to Silver. The Spark lab (R3) tested a file-source stream and a Delta-to-Delta stream with `foreachBatch`. |
| Locality Sensitive Hashing | No | MinHash LSH on edit comments or page titles to group near-duplicate reverts or vandal edits (`pyspark.ml.feature.MinHashLSH`). |
| Privacy techniques (k-anonymity, l-diversity, differential privacy) | Partly: keyed pseudonyms only | Check k-anonymity of the published marts (group sizes; the small-group flag is a start). Add Laplace noise to the E(L) counts and report the error. |
| Other course techniques (5) and a new tool (3) | New tool: Delta Lake and delta-rs | Delta Lake counts as the new tool. |
| Version control: public repository, commits through the semester (3) | The repository is private | Scott decides when to make it public. |
| Report rules | Not covered | No code in the report; an appendix that lists the rubric criteria in order with evidence; `.py` copies of every notebook; files near 1 MB; a CRediT slide; a flow diagram in slides and report. |

Scott decides which of these enter the scope. Each one costs time against the phases in `PLAN.md`.
