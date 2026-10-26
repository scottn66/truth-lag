# EC HW2 report skeleton: Truth Lag in MongoDB and Neo4j (Group 9)

> **This is a frame, not the report.** It has no narrative paragraphs on purpose: our proposal lost points because it read as AI-written. Every sentence of the report is written by a team member, in their own words.
>
> **How to use it**
> 1. Sun 2026-10-25: the Report+GenAI owner imports `report/REPORT_SKELETON.docx` into Google Docs. From then on, the Google Doc is the master copy.
> 2. Each section has: the owner role, a word target, a facts box (keys from `report/FACTS.md`, with FINAL or PROVISIONAL), figure files, 3 guiding questions and an `[OWNER: ...]` line. Replace the `[OWNER: ...]` line with your text. Delete the questions when you are done.
> 3. Parts tagged `[drafted by Claude Code; checked by <name>, <date>]` are mechanical drafts (links, tables, query code, result rows). Check each one against the files, then put your name and the date in the tag.
> 4. Numbers marked PROVISIONAL change after the live refresh (after Mon 2026-10-26 5:05 PM PT, which is 2026-10-27 00:05 UTC). Copy them again from `report/FACTS.md` on Tue 2026-10-27.
> 5. Before you submit, search the Google Doc for `[OWNER`, `<name>`, `TODO` and `PROVISIONAL`.
>
> Section headings below are the spec section 7 headings, word for word and in order. Owners are roles; write names in the "Who did what" table at the end.

{{built}}

## Abstract

**Owner:** Report+GenAI. **Words:** about 150.

**Facts box**

{{facts: history_revisions, live_revisions, history_revert_rate_non_bot_pct, history_median_T_h, history_T_within_1h_pct, history_T_within_1d_pct, cypher_q1_mutual_pairs, mongo_q5_history_known_1h_pct, cmp_all_identical}}

**Figures:** none.

**Guiding questions**
1. What question do we answer, and on which data (two cohorts, which dates)?
2. Which 2 or 3 numbers should a reader remember?
3. What did we learn from asking the same questions in MongoDB, Neo4j and SQL?

[OWNER: write 3-6 short sentences (about 150 words) in your own words. Use 2-3 numbers from the facts box. Write it last, after the other sections.]

## Motivation

**Owner:** Report+GenAI. **Words:** about 400 (example 150, related work 250), plus Novelty about 150.

**Hint:** start from our own example page and its revert timeline (below). Then write half a page of related work from `report/references.md`.

**Facts box**

{{facts: example_slow_page_title, example_slow_edits, example_slow_reverted, example_slow_editor_kinds, example_slow_first_edit_utc, example_slow_last_revert_utc, example_slow_span_h, example_slow_T_min_s, example_slow_T_median_s, example_slow_T_max_s, example_slow_first_steps, example_fast_page_title, example_fast_edits, example_fast_reverted, example_fast_editor_kinds, example_fast_T_median_s, example_fast_T_max_s, history_T_within_1h_pct, history_T_over_7d_pct}}

**The example page, step by step** (history cohort; human editors as pseudonyms; full table in notebook 01) `[drafted by Claude Code; checked by <name>, <date>]`

{{timeline: slow}}

**Numbers from earlier studies to put next to ours** (from `report/references.md`, "Numbers to compare with ours") `[drafted by Claude Code; checked by <name>, <date>]`

| Paper | Their number | Data | Our number (FACTS key) |
|---|---|---|---|
| Viégas et al. 2004 [1] | median survival time (until the next change): 90.4 min for all content; 2.8 min only for the 3,574 mass deletions (vandalism) | May 2003 history | `history_median_T_h` (compare with the 90.4 min) |
| Buriol et al. 2006 [2] | about 70% of reverts within 1 hour | history to 2006-04 | `history_T_within_1h_pct` |
| Kittur et al. 2007 [6] | median survival of MD5 reverts: 9.7 min | 2006-07-02 dump | `history_median_T_h` |
| Halfaker & Riedl 2012 [13] (magazine column) | bots and tools remove most vandalism before readers see it | qualitative | `mongo_q4_made_by_bot_pct`, `mongo_q3_history_lt_1min_pct` |

Limits of this comparison (from `report/references.md`): [1] and [6] measure survival time, not time to revert. Our T counts only reverts within 20 days (`config.HISTORY_FOLLOWUP_DAYS`); [2] and [6] have no such limit. Their data is from 2003-2006.

**Guiding questions**
1. What did you see on the example page, and why would a reader or a tool that copies Wikipedia care?
2. What did earlier studies measure ([1], [2], [6], [13], [P3]), and what did they not measure?
3. Why is it a problem that the record of an edit (reverted or not) is only final days or weeks later?

[OWNER: write 3-6 short sentences about the example page, in your own words. Then write the related work (about 250 words) with citations [1]-[23] (the number [16] is not used) and [P1]-[P3] from report/references.md.]

### Novelty

**Owner:** Report+GenAI. **Hint:** a search-method sentence, the gap table, and 2 of our own numbers.

[OWNER: write ONE sentence on how we found the papers, as it really happened (it was not a keyword search): a candidate list suggested by an AI tool (Claude Code), plus the reference lists of the papers we read ("snowballing"); each paper was checked on Crossref and its abstract or full text was read (Semantic Scholar, OpenAlex or the publisher), on 2026-10-24 UTC. We screened 35 new papers and kept 22 (21 peer-reviewed papers and 1 magazine column). See report/references.md, "How we found and checked the papers".]

**Gap table** (copied from `report/references.md`) `[drafted by Claude Code; checked by <name>, <date>]`

{{gap_table}}

[OWNER: write 2-3 sentences: the 3 closest works and what each lacks. Add 2 of our numbers (for example `mongo_q5_history_known_1h_pct` and `late_reverts_rows`). Say that Wikimedia's daily history table is internal and does not measure a consumer's error against the wait time (references.md, facts W13-W16).]

### What we changed after the proposal feedback

`[drafted by Claude Code; checked by <name>, <date>]`

| Proposal item (score) | What we changed | Where to see it |
|---|---|---|
| Motivation (6/10) | Written by a person, starting from our own example page and its revert timeline | Motivation; FACTS keys `example_*`; notebook 01 |
| Literature (7/10) | 22 new sources: 21 peer-reviewed papers and 1 magazine column (the target was 12 or more), each checked by DOI on Crossref | `report/references.md` |
| Novelty (8/10) | The gap table, the search method (an AI-suggested candidate list plus snowballing, each paper checked) and our own numbers | Motivation > Novelty |
| Impact (9/10) | One persona (a RAG-crawler engineer) and the decision table | Results/insights > Impact; notebook 05 |

## Data + links

**Owner:** Data+MongoDB. **Words:** about 150, plus the tables.

**Facts box**

{{facts: history_file_rows, history_dropped_namespace_not_0, history_dropped_null_same_sha1, history_dropped_null_comment, history_revisions, wikistats_content_edits, history_file_vs_wikistats_pct, live_page_change_events, live_dropped_namespace_not_0, live_dropped_outside_window, live_dropped_not_edit, live_revisions, capture_page_change_first_utc, capture_tags_first_utc, live_newest_meta_dt, live_final_after}}

**Figures:**

{{figure: ../results/figures/fig_capture_coverage.png}}

**Sources** `[drafted by Claude Code; checked by <name>, <date>]`

| Source | Link | Size, dates | License | How we got it |
|---|---|---|---|---|
| MediaWiki History dump, English Wikipedia, snapshot 2026-09 | {{dump_url}} | {{dump_bytes}} bytes (557 MB, bz2); downloaded 2026-10-24 (UTC) | CC0 (see https://dumps.wikimedia.org/other/mediawiki_history/readme.html) | Downloaded on the VPS and filtered once by `ingest/vps/filter_history.py` (repo root) into 2 Parquet files: the 2026-09-08 to 2026-09-10 namespace-0 cohort and a slim file of all September revisions. Copied to the Mac with rsync. |
| Wikimedia EventStreams: `mediawiki.page_change.v1` | https://stream.wikimedia.org/v2/stream/mediawiki.page_change.v1 | replayed from 2026-10-19 23:00 UTC (the capture unit runs since 2026-10-24 04:52 UTC) | No license is stated; we link the service: https://wikitech.wikimedia.org/wiki/Event_Platform/EventStreams_HTTP_Service | Captured on the VPS by `ingest/vps/capture.py` (unit `truthlag-capture-a`). Copied to the Mac with rsync. No laptop connects to EventStreams. |
| Wikimedia EventStreams: `mediawiki.page_revert_risk_prediction_change.v1` | https://stream.wikimedia.org/v2/stream/mediawiki.page_revert_risk_prediction_change.v1 | replayed from 2026-10-19 23:00 UTC (same unit) | as above | Same connection as page_change (`truthlag-capture-a`). |
| Wikimedia EventStreams: `mediawiki.revision-tags-change` | https://stream.wikimedia.org/v2/stream/mediawiki.revision-tags-change | replayed from 2026-10-17 00:00 UTC (first event 2026-10-17 01:30 UTC; the unit runs since 2026-10-24 04:52 UTC) | as above | Captured on the VPS (`truthlag-capture-b`). |
| Our code | https://github.com/scottn66/truth-lag (branch `ec-hw2`, folder `ec-hw2/`) | | | |

**The two cohorts** `[drafted by Claude Code; checked by <name>, <date>]`

| | history cohort | live cohort |
|---|---|---|
| Edits made (UTC) | 2026-09-08 to 2026-09-10 | 2026-10-20 to 2026-10-22 |
| Source | MediaWiki History dump, snapshot 2026-09 | EventStreams, captured on the VPS |
| "Reverted" means | an identity revert within 20 days (dump label) | the first exact revert that covers the edit, within 4 days (stream label) |
| Revisions | `history_revisions` | `live_revisions` (PROVISIONAL) |
| Labels final | now | after 2026-10-27 00:05 UTC |

### Where we differ from the spec, and why

`[drafted by Claude Code; checked by <name>, <date>]`

| Spec says | We did | Why |
|---|---|---|
| Stream `recentchange` / `revision-create` | `mediawiki.page_change.v1`, plus the revert-risk and tags streams | The replay of revision-create is sparse and has no revert fields. page_change.v1 has `revision.revert` (method, exact or not, the reverted range). |
| One live sample, labelled by the dump of the same window | Two cohorts: history (dump labels) and live (stream labels), plus a small late-revert case study that links them | The 2026-10 dump appears in November, after our deadline (the dumps are monthly). |
| Revert label from the dump | For the live cohort: the stream label (the first exact revert within 4 days) | No October dump exists yet. A 4-day follow-up ends before the live cut-off (2026-10-27 00:05 UTC). |
| (no host given) | The capture runs on a VPS (2 systemd units); the data comes to the Mac by rsync | EventStreams allows 2 connections per IP and replays only about 7 days, so an always-on machine is safer. |
| `(:Editor)-[:REVERTED {ts, count}]->(:Editor)` | REVERTED also has `page_id` (and `n_revisions`, `last_ts`); one relationship per reverter, reverted editor and page | Mutual reverts (Cypher Q1) must be on the same page. |
| Atlas free tier + sharding | Atlas free tier = M0 (512 MB, no sharding). The shard key `{"page.id": "hashed"}` is shown on a local 2-shard Docker cluster. | M0 does not allow sharding; sharding starts at the paid M30 tier. |
| `(:Page)-[:IN_CATEGORY]->(:Category)` (optional) | Skipped | It is optional, the dump has no categories, and Cypher Q1-Q5 do not need them. |
| Neo4j Browser/Bloom screenshots | Neo4j Browser screenshots | Bloom is not part of Neo4j Community Edition. |
| `user.is_anon` | `user.is_anon` = a temporary account | Since 2025-11-04 English Wikipedia has no IP edits; logged-out editors get temporary accounts. |

**Guiding questions**
1. Which two sources do we use, and why do we need two cohorts?
2. Which rows did we drop, and why (namespace, null revisions, window)?
3. How do we know the data is complete (the Wikistats check, the capture gaps)?

[OWNER: write 3-6 short sentences in your own words, around the tables.]

## Architecture/workflow diagram

**Owner:** Report+GenAI. **Words:** about 100.

`[drafted by Claude Code; checked by <name>, <date>]` The picture is made from `report/figures/architecture.mmd` (Mermaid) by `report/make_figures.py`.

{{figure: figures/architecture.png}}

**Guiding questions**
1. Which steps run on the VPS, which run on the Mac, and why?
2. Where does each database get its data (MongoDB from Parquet, Neo4j from MongoDB's CSV export, SQLite from Parquet)?
3. Which step will change first in the final project (Kafka, Spark)?

[OWNER: write 3-6 short sentences in your own words that walk the reader through the picture.]

## Mongo section

**Owner:** Data+MongoDB. **Words:** about 400, plus the query blocks.

**Facts box**

{{facts: mongo_revisions_docs, mongo_revert_links_docs, mongo_page_hour_docs, mongo_indexes, mongo_index_list, mongo_ms_q1_revert_rate_by_hour, mongo_ms_q2_top_contested_pages, mongo_ms_q3_time_to_revert, mongo_ms_q4_bot_vs_human, mongo_ms_q5_truth_lag_preview, atlas_estimate_mb, shard_key, shard_shard1rs_pct, shard_shard2rs_pct, shard_route_one_page, shard_route_one_editor, shard_biggest_page_title, shard_biggest_page_revisions}}

**Figures:**

{{figure: ../results/figures/fig_revert_rate_by_hour.png}}

{{figure: ../results/figures/fig_time_to_revert.png}}

{{figure: ../results/figures/fig_bot_vs_human.png}}

{{figure: ../results/figures/chart_q1_hour_kind.png | Atlas Chart 1, made in the Atlas UI by Comparison+viz (guides/ATLAS_CHARTS.md, part B)}}

{{figure: ../results/figures/chart_q3_time_to_revert.png | Atlas Chart 2, made in the Atlas UI by Comparison+viz (guides/ATLAS_CHARTS.md, part C). The caption must say that the live time to revert is capped at 4 days and censored until 2026-10-27 00:05 UTC, and compare the live cohort only with the history_4d rows.}}

**Atlas screenshots** (made in the Atlas UI by Data+MongoDB, `guides/ATLAS_SETUP.md`, part F)

{{figure: ../results/figures/atlas_cluster_m0.png | The Atlas free-tier cluster card (M0), the evidence for "Atlas free tier"; guides/ATLAS_SETUP.md, step 19}}

{{figure: ../results/figures/atlas_indexes.png | The Indexes tab of revisions on Atlas; guides/ATLAS_SETUP.md, step 21}}

{{figure: ../results/figures/atlas_sample_document.png | One bot document in Data Explorer; guides/ATLAS_SETUP.md, step 20}}

{{figure: ../results/figures/atlas_mongo_q1.png | Mongo Q1 run in Data Explorer > Aggregations; guides/ATLAS_SETUP.md, step 22}}

{{figure: ../results/figures/atlas_mongo_q2.png | Mongo Q2 run in Data Explorer > Aggregations; guides/ATLAS_SETUP.md, step 22}}

{{figure: ../results/figures/atlas_mongo_q3.png | Mongo Q3 run in Data Explorer > Aggregations; guides/ATLAS_SETUP.md, step 22}}

{{figure: ../results/figures/atlas_mongo_q4.png | Mongo Q4 run in Data Explorer > Aggregations; guides/ATLAS_SETUP.md, step 22}}

{{figure: ../results/figures/mongo_q5_local.png | Mongo Q5 run on the local MongoDB (Compass in text view, or the Mongo Q5 output cell of notebook 02 or 05), because Atlas has no live cohort; guides/ATLAS_SETUP.md, step 23}}

**One `revisions` document** (history cohort, from `results/sample_documents.json`; the human editor is a pseudonym and the user id is hidden) `[drafted by Claude Code; checked by <name>, <date>]`

{{sample_doc}}

**Query blocks** `[drafted by Claude Code; checked by <name>, <date>]`

{{mongo: q1_revert_rate_by_hour | 8}}

{{mongo: q2_top_contested_pages | 10}}

**Mongo Q3: time to revert (`$bucket`).** The pipeline is long, so it is in the [Appendix: the long Mongo pipelines (Mongo Q3 and Q5)](#appendix-the-long-mongo-pipelines-mongo-q3-and-q5), with its result rows. File `queries/mongo/q3_time_to_revert.json`; results `results/mongo_q3_time_to_revert.md`. Compare the live cohort only with the `history_4d` rows (both 4 days).

{{mongo: q4_bot_vs_human | 8}}

**Mongo Q5: the truth-lag preview (`$lookup`).** The pipeline is long, so it is in the [Appendix: the long Mongo pipelines (Mongo Q3 and Q5)](#appendix-the-long-mongo-pipelines-mongo-q3-and-q5), with its result rows. File `queries/mongo/q5_truth_lag_preview.json`; results `results/mongo_q5_truth_lag_preview.md`. The risk-decile pipeline of the Impact decision table is `queries/mongo/q5_risk_deciles.json`.

**Scale-out:** see `scaleout/SHARDING.md` and `results/sharding.md` (the 2-shard demo), and the Atlas screenshots above (Data+MongoDB).

**Guiding questions**
1. Why one document per revision, and which data is embedded (the `history` part) and which is looked up with `$lookup` (`revert_links`)?
2. Which index helps which query, and what does each pipeline stage do?
3. What does the shard key `{"page.id": "hashed"}` do well (one page = one shard) and what not (one editor = every shard)?

[OWNER: write the Mongo section in your own words (about 400 words): the document model, the indexes, the 5 pipelines (1-2 sentences each), the timings, Atlas and the shard key.]

## Neo4j section

**Owner:** Neo4j. **Words:** about 400, plus the query blocks.

**Facts box**

{{facts: neo4j_editor_count, neo4j_page_count, neo4j_edited_count, neo4j_reverted_count, contested_pages_total, cypher_q1_mutual_pairs, cypher_q1_pages, cypher_q1_pairs_with_bot, cypher_q2_top_pagerank_editor, cypher_q2_top_pagerank, cypher_q2_top_human_pagerank, cypher_q3_louvain_communities, cypher_q3_louvain_modularity, cypher_q3_largest_community_editors, cypher_q3_largest_wcc_editors, cypher_q3_editors_without_revert_pct, cypher_q4_top_page_title, cypher_q4_top_page_warring_editors, cypher_q5_top_pair_shared_pages, cypher_ms_q1_mutual_reverts, cypher_ms_q2_central_reverters, cypher_ms_q3_conflict_communities, cypher_ms_q4_pages_most_warring_editors, cypher_ms_q5_two_hop_contested}}

**Figures:**

{{figure: ../results/figures/neo4j_edit_war_example.png}}

**Neo4j Browser screenshots** (made in Neo4j Browser by the Neo4j owner, `guides/NEO4J_SCREENSHOTS.md`)

{{figure: ../results/figures/neo4j_schema.png | The graph model, CALL db.schema.visualization(); guides/NEO4J_SCREENSHOTS.md, step 7}}

{{figure: ../results/figures/neo4j_mutual_reverts.png | Mutual-revert pairs (Cypher Q1 as a picture); guides/NEO4J_SCREENSHOTS.md, step 8}}

{{figure: ../results/figures/neo4j_contested_page.png | One contested page with its editors and reverts; guides/NEO4J_SCREENSHOTS.md, step 9}}

{{figure: ../results/figures/neo4j_largest_community.png | The largest Louvain community (a patroller and the editors they reverted); guides/NEO4J_SCREENSHOTS.md, step 10}}

{{figure: ../results/figures/neo4j_cypher_q1_table.png | The Cypher Q1 result table; guides/NEO4J_SCREENSHOTS.md, step 12}}

{{figure: ../results/figures/neo4j_cypher_q2_table.png | The Cypher Q2 result table; guides/NEO4J_SCREENSHOTS.md, step 12}}

{{figure: ../results/figures/neo4j_cypher_q3_table.png | The Cypher Q3 result table; guides/NEO4J_SCREENSHOTS.md, step 12}}

{{figure: ../results/figures/neo4j_cypher_q4_table.png | The Cypher Q4 result table; guides/NEO4J_SCREENSHOTS.md, step 12}}

{{figure: ../results/figures/neo4j_cypher_q5_table.png | The Cypher Q5 result table; guides/NEO4J_SCREENSHOTS.md, step 12}}

**Query blocks** `[drafted by Claude Code; checked by <name>, <date>]`

{{cypher: q1_mutual_reverts | 8}}

{{cypher: q2_central_reverters | 8}}

{{cypher: q3_conflict_communities | 6}}

{{cypher: q4_pages_most_warring_editors | 8}}

{{cypher: q5_two_hop_contested | 8}}

**Guiding questions**
1. What is a node and what is a relationship in our graph, and why does REVERTED carry `page_id`?
2. Which pattern or GDS algorithm answers each of Cypher Q1-Q5, and why does PageRank use the REVERSE direction? (Hint: the by-degree list answers "who reverts the most"; a high REVERSE PageRank means "reverts editors who are themselves active reverters".)
3. What did the graph show that a table query would not show easily?

[OWNER: write the Neo4j section in your own words (about 400 words): the graph model, the load (CSV + LOAD CSV), the 5 queries (1-2 sentences each) and the screenshots.]

## Results/insights

**Owners:** Data+MongoDB ("Answer to RQ1"), Neo4j ("Answer to RQ2"), Comparison+viz ("Impact"). **Words:** about 350 in all. RQ1 and RQ2 are the spec's two research questions (not Mongo Q1 or Cypher Q2).

### Answer to RQ1: which edits get reverted, how fast, and where?

**Facts box**

{{facts: history_revert_rate_non_bot_pct, history_revert_rate_temporary_pct, history_revert_rate_registered_pct, history_revert_rate_bot_pct, mongo_q1_history_temporary_vs_registered_ratio, history_median_T_h, history_median_T_temporary_h, history_median_T_registered_h, history_T_within_1h_pct, history_T_within_1d_pct, history_T_over_7d_pct, mongo_q4_made_by_bot_pct, mongo_q4_received_by_temporary_pct, mongo_q2_top5_titles, live_revert_rate_human_pct, live_median_T_h}}

**Guiding questions**
1. Who gets reverted most (user kind), and is it the same in both cohorts?
2. How fast are reverts, and what share takes more than 1 day?
3. Where (which pages) and by whom (bots or people)?

[OWNER (Data+MongoDB): write 3-6 short sentences that answer RQ1, with 3-4 numbers. Mark live numbers PROVISIONAL until Tue 2026-10-27. Compare the live time to revert only with the history cohort on the same 4-day horizon (`mongo_q5_history_known_1h_pct` next to `mongo_q5_live_known_1h_pct`).]

### Answer to RQ2: who reverts whom, and what structures go with edit wars?

**Facts box**

{{facts: cypher_q1_mutual_pairs, cypher_q1_pages, top20_pages_with_mutual_pair, top20_mutual_pairs, top20_mutual_pairs_pct, cypher_q2_top_pagerank_editor, cypher_q2_top_reverts_made, cypher_q3_largest_community_editors, cypher_q3_largest_wcc_pct, cypher_q4_top_page_title, cypher_q4_top_page_mutual_pairs}}

**Guiding questions**
1. How common are mutual reverts (edit wars), and where are they?
2. One association: what share of the mutual pairs is on the top 20 contested pages (20 of 165,415 pages)?
3. Who is central in the revert graph (bots or people), and what do the communities look like?

[OWNER (Neo4j): write 3-6 short sentences that answer RQ2, with one association (for example `top20_mutual_pairs_pct`).]

### Impact: the truth-lag preview

**Owner:** Comparison+viz. **Hint:** one persona (a RAG-crawler engineer) and the decision table from notebook 05.

**Facts box**

{{facts: mongo_q5_history_known_1min_pct, mongo_q5_history_known_1h_pct, mongo_q5_history_known_1d_pct, mongo_q5_live_known_1h_pct, risk_top_decile_score_min, risk_top_decile_revert_rate_pct, risk_top_decile_visible_1h_pct, risk_top_decile_visible_1h_ci, risk_top_decile_later_1h_pct, risk_top_decile_later_1d_pct, risk_bottom_decile_revert_rate_pct, risk_top2_deciles_share_of_reverts_pct, late_reverts_rows, late_reverts_exact, late_reverts_inexact_undo, late_reverts_method_unknown, live_followup_max_d}}

**Figures:**

{{figure: ../results/figures/fig_known_by_curves.png}}

{{figure: ../results/figures/fig_risk_deciles.png}}

{{figure: ../results/figures/fig_late_reverts.png}}

[OWNER: describe ONE persona in 2-3 sentences: a RAG-crawler engineer who copies Wikipedia pages into a search index for an AI assistant. What does she lose if she copies an edit too early? What does each hour of waiting cost her?]

**The decision table** (live cohort, from notebook 05; PROVISIONAL until the live refresh) `[drafted by Claude Code; checked by <name>, <date>]`

"Visible after w" = the share of the group's reverts within 4 days that already happened by the wait w. "Reverted later if clean at w" = of the edits not reverted by w, the share that is still reverted within 4 days. Brackets: Wilson 95% interval.

{{decision}}

The revert-risk score is Wikimedia's `revertrisk-language-agnostic` model: cite `report/references.md` W17. The "no score" group holds page creations plus edits whose score event was not captured.

**Guiding questions**
1. For the riskiest edits, how much does waiting 1 hour or 1 day help?
2. For the low-risk edits, is waiting worth it?
3. What do the late reverts (`late_reverts_*`) say about trusting the dump label?

[OWNER (Comparison+viz): write 3-6 short sentences in your own words, from the persona's point of view, with 2-3 numbers from the table.]

## Comparison top 5

**Owner:** Comparison+viz. **Words:** about 300.

**Facts box**

{{facts: cmp_loc_top_mongodb, cmp_loc_top_neo4j, cmp_loc_top_sqlite, cmp_loc_mutual_mongodb, cmp_loc_mutual_neo4j, cmp_loc_mutual_sqlite, cmp_ms_top_mongodb, cmp_ms_top_neo4j, cmp_ms_top_sqlite, cmp_ms_mutual_mongodb, cmp_ms_mutual_neo4j, cmp_ms_mutual_sqlite, cmp_pain_top_mongodb, cmp_pain_top_neo4j, cmp_pain_top_sqlite, cmp_pain_mutual_mongodb, cmp_pain_mutual_neo4j, cmp_pain_mutual_sqlite, cmp_all_identical, cmp_timing_label}}

**Figures:**

{{figure: ../results/figures/fig_comparison.png}}

The candidate findings (numbers only) are in `results/comparison.md`, section "Candidate findings for 'Comparison top 5'".

The `cmp_pain_*` scores are **drafts by Claude Code** (`comparison/pain.csv`). The Comparison+viz owner re-scores them from their own experience and writes their name in the `scored_by` column. Only then are they the team's judgment.

| # | Finding (in your own words) | Number | Evidence file |
|---|---|---|---|
| 1 | [OWNER] | | |
| 2 | [OWNER] | | |
| 3 | [OWNER] | | |
| 4 | [OWNER] | | |
| 5 | [OWNER] | | |

**Guiding questions**
1. In which engine was each question easiest to write, and why (lines of code, modeling pain)?
2. Are the speed differences big enough to matter, and what do the times include (network hop, Docker)? (Call an engine faster only when the min-max ranges do not overlap. The Neo4j mutual-reverts time does not include the aggregation that `export_graph.py` does before the load.)
3. Which modeling choice made a query easy or hard (for example `page_id` on REVERTED)?

[OWNER: write the 5 findings in your own words, one or two sentences each. Use the final timings (after `compare.py --final`), not the draft ones.]

## Technical difficulties

**Owner:** Report+GenAI, with everyone's notes from `PROGRESS.md` ("Personal observations"). **Words:** about 250.

**Facts box**

{{facts: capture_page_change_files_cut_short, capture_tags_files_cut_short, capture_revert_risk_gaps, capture_revert_risk_gap_s_total, history_dropped_null_comment, live_revert_events, live_revert_events_newest_not_parent, history_tag_share_T_7d_20d_pct, live_tag_confirmed_range_gt_15_pct, live_followup_max_d}}

**Figures:**

{{figure: ../results/figures/fig_tag_agreement.png}}

**Guiding questions**
1. What broke or surprised us (for example: gzip files cut short, dump columns that are all text, page moves that look like edits, the stream and the dump defining a revert differently)?
2. How did we check that the three databases give the same answer?
3. What would we do earlier next time?

[OWNER: write 3-6 short sentences per difficulty (2-4 difficulties), in your own words, from the team's notes.]

## Best practices + key learnings

**Owner:** Report+GenAI, with everyone's notes. **Words:** about 250.

**Facts box**

{{facts: cmp_all_identical, mongo_indexes, shard_checks_ok, atlas_estimate_mb}}

**Guiding questions**
1. Which rules kept the work safe and repeatable (never `rsync --delete`, write a `.tmp` file and then rename it, one `config.py` for every rule)?
2. What did each of us learn about document modeling compared with graph modeling?
3. What advice would you give a team that starts this homework tomorrow?

[OWNER: write 4-6 short bullet points in your own words. Each member adds at least one.]

## Criteria map table

**Owner:** Report+GenAI (check every file link). `[drafted by Claude Code; checked by <name>, <date>]`

| Criterion (spec section 8) | Evidence (file or figure) | As in spec / changed |
|---|---|---|
| Meaningful goal | Motivation; `report/FACTS.md` (`example_*`, `history_*`); notebook `05_truth_lag.ipynb` | as in spec (revert + Truth Lag framing) |
| Workflow | `report/figures/architecture.png`; `ec-hw2/README.md` section 1; `ingest/`, `load_mongo.py`, `export_graph.py`, `load_neo4j.py`, `queries/` | changed: VPS capture + rsync, `page_change.v1` (see "Where we differ from the spec") |
| Innovation | Mongo Q5 (`queries/mongo/q5_truth_lag_preview.json`, `results/mongo_q5_*.csv`); `fig_known_by_curves.png`, `fig_risk_deciles.png`; late-revert case study (`fig_late_reverts.png`); revert graph (Cypher Q1-Q5) | changed: two cohorts + Wikimedia's live revert-risk score |
| Technical difficulty | stream labels (`ingest/label_live.py`, range cover), dump labels (`ingest/parse_history.py`, reverter self-join), two databases + SQLite, GDS PageRank / Louvain / WCC (`queries/cypher/q2_*.cypher`, `q3_*.cypher`), `fig_tag_agreement.png` | changed: the stream + dump join is the late-revert case study (the October dump comes in November) |
| Queries/aggregations | `queries/mongo/q1-q5*.json` + `results/mongo_q*.md`; `queries/cypher/q1-q5*.cypher` + `results/cypher_q*.md`; notebooks 02 and 03 | as in spec (5 + 5) |
| Scale-out | `scaleout/SHARDING.md`, `results/sharding.md`; `load_mongo.py --target atlas`; Atlas screenshots in `results/figures/`: `atlas_cluster_m0.png` (the M0 free tier), `atlas_indexes.png`, `atlas_sample_document.png`, `atlas_mongo_q1.png` to `atlas_mongo_q4.png`; Mongo Q5 on the local MongoDB: `mongo_q5_local.png` | changed: Atlas M0 cannot shard, so a local 2-shard cluster shows the shard key |
| Programming | Python scripts in `ec-hw2/` (PyMongo, neo4j driver), Cypher files, tests in `ec-hw2/tests/` | as in spec |
| Visualization | Atlas Charts PNGs (`results/figures/chart_q1_hour_kind.png`, `chart_q3_time_to_revert.png`); Neo4j Browser screenshots in `results/figures/`: `neo4j_schema.png`, `neo4j_mutual_reverts.png`, `neo4j_contested_page.png`, `neo4j_largest_community.png`, `neo4j_cypher_q1_table.png` to `neo4j_cypher_q5_table.png`; `results/figures/fig_*.png`; `neo4j_edit_war_example.png` | changed: Neo4j Browser instead of Bloom |
| Comparison | `results/comparison.md`, `comparison/compare.py`, notebook `04_comparison.ipynb`, `fig_comparison.png` | as in spec (SQLite as the SQL engine) |
| Bonus | `ec-hw2/docker-compose.yml`, `scaleout/docker-compose.sharded.yml`; LLM use documented in `genai/PROMPTS.md` and `genai/prompts/`; blog or video: [OWNER: yes or no] | as in spec |

## Reuse note

**Owner:** Report+GenAI. **Words:** about 120. `[drafted by Claude Code; checked by <name>, <date>]`

HW2 is the storage and query MVP of our course project (Truth Lag). These parts carry over:

| HW2 part | File | Use in the final project |
|---|---|---|
| Live capture | `ingest/vps/capture.py` (repo root), `truthlag-capture-a` / `-b` | [OWNER] |
| Parsers | `ingest/parse_stream.py`, `ingest/parse_history.py`, `ingest/history_columns.py` | [OWNER] |
| Labels | `ingest/label_live.py` (range cover, 4-day label), `ingest/late_reverts.py` | [OWNER] |
| `revert_links` | `DATA_MODEL.md` section 3; MongoDB collection `revert_links` | [OWNER] |
| `page_hour` | `speed_layer.py`; MongoDB collection `page_hour` | [OWNER] |

Kafka and Spark come in the final project. HW2 does not use them.

[OWNER: write 2-4 short sentences in your own words: what we reuse, and what we add in the final project.]

## Mandatory GenAI Q&A

**Owner:** Report+GenAI; every member fills in their own row. `[drafted by Claude Code; checked by <name>, <date>]`

**Course question:** "Did you find or come across solutions to similar problems by using Generative AI or other sources?"

**Answer:** Yes.

[OWNER: write 2-4 short sentences in your own words: which tools we used, for what, and how people checked the output. Then answer the question itself: which solutions to similar problems we found, through AI or other sources (for example [6], [14], [P3] ORES, and Wikimedia's daily history table T424350, facts W13-W16 in report/references.md), and say that we reuse no code from them.]

| Spec item # | Tool + exact model ID | Verbatim prompt or link | Help given | What a person checked |
|---|---|---|---|---|
| Planning (all items) | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/PROMPTS.md`, `ec-hw2/genai/APPROVED_PLAN.md` | Drafted the plan; Scott Nelson approved it after 3 rounds of changes | [OWNER] |
| 2 Data (VPS capture and filter) | Claude Code, `claude-opus-5-5` | Made in an earlier Claude Code session directed by Scott; prompts not kept (`ec-hw2/genai/PROMPTS.md`) | Drafted `ingest/vps/capture.py`, the systemd units and `filter_history.py` | [OWNER] |
| 2 Data, 6 Engineering | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/prompts/build_history.md`, `build_stream.md` | Drafted the parse scripts and the stream labels | [OWNER] |
| 3 MongoDB (Mongo Q1-Q5) | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/prompts/build_mongo.md` | Drafted the 5 aggregation pipelines, `load_mongo.py`, `speed_layer.py` | [OWNER] |
| 3 Scale-out | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/prompts/build_scaleout.md` | Drafted the 2-shard demo and `SHARDING.md` | [OWNER] |
| 4 Neo4j (Cypher Q1-Q5) | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/prompts/build_neo4j.md` | Drafted the 5 Cypher queries, `export_graph.py`, `load_neo4j.py` | [OWNER] |
| 5 Comparison | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/prompts/build_comparison.md` | Drafted the SQL queries, `load_sql.py`, `compare.py` | [OWNER] |
| 7 Report: literature | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/prompts/build_literature.md` | Suggested the candidate list of papers, followed reference lists, checked each DOI on Crossref and read the abstracts | [OWNER: which papers a person opened and read, and what they found] |
| 7 Report: docs | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/prompts/build_docs.md`, `build_notebooks.md` | Drafted the docs, notebooks, `FACTS.md` and this skeleton (no narrative) | [OWNER] |
| Review (all items) | Claude Code Workflow, `claude-opus-5-5` | `ec-hw2/genai/workflows/verify.js`, `ec-hw2/genai/prompts/verify_*.md` | 7 independent AI reviewers tried to refute the build and listed findings | [OWNER] |
| Fixes after the review (all items) | Claude Code, `claude-opus-5-5` | `ec-hw2/genai/prompts/fix_common.md` and `fix_*.md` | Fixed the confirmed findings (see `ec-hw2/genai/PROMPTS.md`, "Errors the review caught") | [OWNER] |
| 5 Comparison: modeling pain | Claude Code, `claude-opus-5-5` (draft only) | `comparison/pain.csv` | Draft pain scores and reasons | [OWNER (Comparison+viz): your own scores, and what you changed] |
| [OWNER: item #] | [Scott Nelson: tool + model, or "none"] | | | |
| [OWNER: item #] | [Tingyu Lee: tool + model, or "none"] | | | |
| [OWNER: item #] | [Wanru Hsiao: tool + model, or "none"] | | | |
| [OWNER: item #] | [Zhenni Dai: tool + model, or "none"] | | | |

Translators and grammar tools count as AI tools: list them too.

**Errors that review caught**

The errors that the AI review found, and the fixes, are listed in `ec-hw2/genai/PROMPTS.md`, section "Errors the review caught (2026-10-24)". Add the errors that people found below.

| Error | Found by (person or check) | How it was fixed | Evidence (file, commit or PR comment) |
|---|---|---|---|
| [OWNER] | | | |
| [OWNER] | | | |
| [OWNER] | | | |

**Who did what** (verbs: built, verified, created in UI, wrote)

| Member | Built | Verified | Created in UI | Wrote | AI tools used (or none) |
|---|---|---|---|---|---|
| Scott Nelson | | | | | |
| Tingyu Lee | | | | | |
| Wanru Hsiao | | | | | |
| Zhenni Dai | | | | | |

### Appendix: the long Mongo pipelines (Mongo Q3 and Q5)

`[drafted by Claude Code; checked by <name>, <date>]` In the Google Doc, put this appendix after the last section. The Mongo section links here.

{{mongo: q3_time_to_revert | 30}}

{{mongo: q5_truth_lag_preview | 6 | user_kind=all; wait=1 min,1 h,1 d}}
