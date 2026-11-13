# R5 — History snapshots and the current-events slice

> **Research report, not yet reviewed.** Output of the research agent `sources_events` in a cloud Claude Code session on Nov 13, 2026, as returned. Evidence labels: RAN = executed in that session on made-up data; READ = read at the cited file and line; DERIVED = arithmetic on values that were read; UNVERIFIED = not checked. Paths that start with /tmp/claude-0/ or /home/user/ are on that session's machine and cannot be opened from elsewhere. Repository state read: scottn66/truth-lag at 8e28012.

## Summary

Research for the Medallion plan, key sources_events. (A) dumps.wikimedia.org is blocked from this container (RAN: "curl: (56) CONNECT tunnel failed, response 403"; WebFetch "getaddrinfo ENOTFOUND dumps.wikimedia.org"), so whether the 2026-10 snapshot is published today and the sizes of its enwiki files are UNVERIFIED. What is established from the repo and from the public upstream dumper source: snapshots are monthly, published "around the end of the month's first week", only the last two are kept, each snapshot is a full rebuild, and enwiki is split into one file per month named <snapshot>/enwiki/<snapshot>.enwiki.<YYYY-MM>.tsv.bz2. So the two files the plan needs are 2026-10.enwiki.2026-10.tsv.bz2 (labels for the Oct 20-22 live cohort, about 9 days of uncensored follow-up) and 2026-10.enwiki.2026-09.tsv.bz2 (September restated, which turns the 3,591 lower-bound late reverts into an exact label diff). (B) Four operational definitions of "current events" are compared (burst, new page, editorial signals, pageview spikes) plus a zero-cost title-year heuristic. Only burst and new-page are computable from data the project already holds; committed results show bursts are rare: 2.0% (history) and 2.5% (live) of edits have 10 or more page edits in the prior hour, 6.0% and 6.8% have 5 or more, and the revert rate is NOT higher in the 10+ bucket (5.85% vs 5.98% overall in history). (C) Proposed Gold objects: an interval dimension dim_page_current_event, an edit-to-slice bridge, mart_el_by_slice, mart_el_slice_contrast, a Kaplan-Meier mart and a named-episode mart, with page-clustered confidence intervals, a common fixed horizon, and a 100-eventual-revert suppression rule.

## History snapshots

**Network status from this container (RAN, 2026-11-13 11:15-11:17 UTC).** The dump host is blocked, so nothing about the live directory could be checked.
- `curl -sS -I https://dumps.wikimedia.org/other/mediawiki_history/` -> `curl: (56) CONNECT tunnel failed, response 403`. Same for GET and for `/2026-10/enwiki/`.
- Proxy status entry: `kind: connect_rejected, detail: gateway answered 403 to CONNECT (policy denial or other refusal), host: dumps.wikimedia.org:443`.
- WebFetch: `getaddrinfo ENOTFOUND dumps.wikimedia.org`.
- Same 403 refusal for wikitech.wikimedia.org, wikimedia.org (pageviews REST), www.mediawiki.org, meta.wikimedia.org, api.wikimedia.org, analytics.wikimedia.org, three dump mirrors and web.archive.org. I did not try to route around it.
- **Therefore UNVERIFIED: whether 2026-10 is published today, and the byte sizes of its enwiki 2026-09 and 2026-10 files.** By the documented schedule it should be out (see below), but that is an inference.

**What is established**

| Question | Answer | Evidence |
|---|---|---|
| Cadence | Monthly | READ `ec-hw2/report/references.md:136`, quoting the Wikitech page (permanent link oldid=2433177): "The updates for this data set are monthly, around the end of the month's first week." A web search summary of a mirror of `readme.html` returned the same sentence (page itself not opened). |
| When in the next month | End of the first week; team planning figure "around Nov 1-12" | READ `ec-hw2/genai/APPROVED_PLAN.md:8`. Observed: on 2026-10-15 the listing already had `2026-09/` (READ `notebooks/00_access_points.ipynb` cell 7 output: `200 ['../', '2026-08/', '2026-09/', 'readme.html']`). |
| Snapshots kept upstream | Two | READ `references.md:137` quote: "for storage reasons only the last two versions are available." Also `APPROVED_PLAN.md:27` ("Only the 2026-08 and 2026-09 snapshots are online"), `docs/schema_and_warehouse.md:34`, and the notebook listing above (exactly two folders). |
| File naming | `<snapshot>/<wiki>/<snapshot>.<wiki>.<time_bucket>.tsv.bz2`; enwiki bucket = one calendar month | READ `notebooks/00_access_points.ipynb` cell 6. READ upstream `MediawikiHistoryDumper.scala` (wikimedia/analytics-refinery-source, master, fetched from raw.githubusercontent.com): `WikisInMonthlyBuckets = Seq("wikidatawiki", "commonswiki", "enwiki")` (lines 90-94); `destinationDirectory = s"$outputBasePath/$snapshot/$wiki"`, `destinationFile = s"$snapshot.$wiki.$timeBucket.tsv.bz2"` (lines 268-269); month bucket built at line 230. |
| Is each snapshot a full rebuild | Yes; old rows change | READ `references.md:138` quote: "So an event triggered today may change the state of that table 10 years ago." |
| 2026-09 enwiki month file | 557,344,652 bytes; 6,369,430 rows, 0 bad rows, 5,266,843 revision rows (so about 1.10 M page and user event rows); streamed and filtered in 154 s on the VPS | READ `ec-hw2/config.py:71-74`, `ingest/vps/filter_stats.json` |
| Snapshot cutoff | Not exactly month end: last revision 2026-10-01 01:38:27 UTC; the 2026-09 folder has a `...2026-10` file that is "a 1.6-hour spill-over" | READ `config.py:111`, `APPROVED_PLAN.md:30` |
| Format | No header, 78 tab-separated columns, null = empty field, times `%Y-%m-%d %H:%M:%S.%f`, lists comma-joined with `\,` escape, sha1 base 36; `event_log_id` (index 1) added May 2026 | READ `ec-hw2/ingest/history_columns.py:9,19-46,80,114-135`, `ingest/vps/filter_history.py:6-22` |

**Files the plan needs from 2026-10 (names derived from the naming code above; existence and sizes UNVERIFIED)**
- `https://dumps.wikimedia.org/other/mediawiki_history/2026-10/enwiki/2026-10.enwiki.2026-10.tsv.bz2` (October events)
- `https://dumps.wikimedia.org/other/mediawiki_history/2026-10/enwiki/2026-10.enwiki.2026-09.tsv.bz2` (September events, restated)
- Probably a small `2026-10.enwiki.2026-11.tsv.bz2` spill-over, by analogy with 2026-09.
- Size expectation (estimate only): each about 0.5-0.6 GB, like the 557 MB September file.

**Step 0 for the executing session, on a machine that can reach the host**
```
curl -s -A "<generic UA>" https://dumps.wikimedia.org/other/mediawiki_history/ | grep -o 'href="[^"]*"'
curl -sI -A "<generic UA>" https://dumps.wikimedia.org/other/mediawiki_history/2026-10/enwiki/2026-10.enwiki.2026-10.tsv.bz2
curl -sI -A "<generic UA>" https://dumps.wikimedia.org/other/mediawiki_history/2026-10/enwiki/2026-10.enwiki.2026-09.tsv.bz2
```

**What the repo already records that the Bronze design must respect (READ)**
- The VPS filter keeps only `event_entity == "revision"` rows (`filter_history.py:40`) and, for the 78-column file, only current-namespace 0 on Sep 8-10 (`:44`). Page and user events were dropped. `dim_page` SCD2 (moves, deletes, restores) and the new-page definition need them, so Bronze should land the whole monthly file.
- The slim file has 12 columns and no `page_creation_timestamp` or `page_first_edit_timestamp` (`config.py:88-93`).
- The Parquet copies turned literal strings "NA", "NULL", "nan" into null (`config.py:85-87`, caused by `strings_can_be_null=True` at `filter_history.py:60`). Bronze must not do that.
- The raw 2026-09 `.bz2` lives only on the VPS; the Mac copy excludes it (`ingest/vps/README.md`, rsync `--exclude '*.bz2'`).
- Retention consequence (inference from the two-snapshot rule): when 2026-11 is published in early December, 2026-09 disappears upstream. Both snapshots are downloadable together only between the 2026-10 and 2026-11 releases.

**What a second snapshot adds**
1. **Truth labels for the October live cohort.** `2026-10.enwiki.2026-10` carries `revision_is_identity_reverted`, `revision_first_identity_reverting_revision_id` and `revision_seconds_to_identity_revert` for the 279,466 live revisions of Oct 20-22 (`FACTS.md:62`). This is the first real `(wiki_db, rev_id)` reconciliation; ec-hw2 could only compare two separate cohorts. If the cutoff is about Nov 1 01:xx UTC (UNVERIFIED), follow-up is 9 days for the last live edit and 12 days for the first, so a horizon up to 9 days is uncensored (stream labels gave 4 days). A 20-day horizon for October needs the 2026-11 snapshot.
2. **Changed labels for September.** `2026-10.enwiki.2026-09` restates September as of about Nov 1. Diffing it against the 2026-09 snapshot gives the exact set of revisions whose label flipped. ec-hw2 could only give lower bounds from the stream: 3,591 namespace-0 late reverts (4,350 all namespaces), of which 2,472 `exact` (should flip in the dump), 194 `inexact_undo` (the dump will never count them), 925 `method_unknown`; 217 fall in the Sep 8-10 cohort (`FACTS.md:298-309`). The stream saw nothing between 2026-10-01 01:38 UTC and the capture start, so the true count is higher.
3. **This diff is the natural payload for `fact_revert_label` MERGE plus Change Data Feed**, and for the Silver label-observation table at grain (rev_id, snapshot). Caution (inference): columns that hold current state (`page_title`, `page_namespace`, `event_user_text`, `event_user_is_bot_by`) are also restated each month, so compare a hash of the label columns only, or the change feed fills with non-label updates.
4. **Page events for October** from the dump (moves, deletes, restores), to check the stream-derived `dim_page` versions.
5. **A time-travel demo with real content:** `fact_revert_label` as of the commit that loaded 2026-09 versus after the 2026-10 merge.

## Current-events definitions

All rules below use an as-of time `asof_ts` = `seen_ts` (meta.dt) for live rows and `ts` for history rows, matching how `page_edits_prev_1h` is built today (READ `ec-hw2/DATA_MODEL.md:72`, `ingest/label_live.py:424-426`, `ingest/parse_history.py:30`). API and pageview details are UNVERIFIED in this session (docs hosts blocked; the en.wikipedia.org API answered HTTP 429 twice).

**Comparison**

| # | Definition | Extra data beyond the capture | Cost | Works for Sep and Oct cohorts | Main weakness |
|---|---|---|---|---|---|
| D1 | Burst of edits on the page | None | Very low: one window aggregation | Yes, both | Confounded with the outcome (edit wars and vandal fights are bursts) |
| D2 | New page (created within N days) | Creation time for pages older than the capture start: History columns | Low once the full monthly file is in Bronze | Yes, both | Most new pages are not news; most news lands on old pages |
| D3 | Editorial signals ({{Current}} family, Category:Current events, Portal:Current events) | MediaWiki Action API polls | Medium: a small poller plus an interval table | Portal pages: yes, backfillable. Template and category: only from first poll (or 30 days back, unverified) | Very small group; applied by hand |
| D4 | Pageview spike | Pageviews API or dumps | High: 1 request per day for top-1000, or tens of GB for full baselines | Yes if downloaded | Reader attention, not editing; daily grain; title-keyed |
| D5 | Title carries the current year (optional, zero cost) | None | Trivial | Yes | Only dated events |

**D1. Burst-based**
- Rule D1a (exists today): `is_burst_10 := page_edits_prev_1h >= 10`. Sensitivity: `>= 5`.
- Rule D1b (recommended refinement, same inputs): per page and sliding hour, `nonrevert_human_edits_1h >= 10 AND distinct_human_editors_1h >= 5`, built from Silver `page_change` columns `page_id, meta_dt, kind IN ('edit','create'), revert_method IS NULL, is_bot = false, user_id/user_name` (history side: `revision_is_identity_revert = false`, `event_user_is_bot_by` without `group`).
- Episode form for descriptive use: maximal run of hot hours with gaps of 6 h or less; `valid_from` = first hot hour, `valid_to` = last hot hour + 24 h. This form looks ahead inside the first hour, so use it for description only and the edit-level form for any "early signal" claim.
- Weaknesses: (1) reverts are edits, so PB&J_Otter (39 edits, 34 revert actions) and Watergate_scandal (32 edits, 28 revert actions) qualify without being news; (2) one editor saving many times, bots, and list upkeep (List_of_2018_albums, 261 revisions) qualify unless distinct editors are required; (3) the two cohorts measure it differently (meta.dt versus revision time; the history count includes every slim-file revision); (4) the clock-hour `page_hour` variant undercounts (1.14% of live edits in 10+ versus 2.54% with the sliding hour), so use sliding windows.

**D2. New page**
- Rule: `is_new_page_7d := asof_ts - page_created_dt < 7 days`, namespace 0, not a redirect. Sensitivity N = 2 and 30.
- `page_created_dt` = `rev_dt` of the page's `kind = 'create'` event in `page_change` (READ `parse_stream.py:139`, `label_live.py:402`); else History `page_first_edit_timestamp` or `page_creation_timestamp` (column indexes 38 and 37, READ `history_columns.py:31`). The two differ for merged or imported histories (upstream comment, `MediawikiEvent.scala:368`: "Using pageCreationTimestamp with page events (not pageFirstEditTimestamp)"); which one fits best is UNVERIFIED.
- Extra data: the stream only knows creations after 2026-10-19 23:00 UTC, so for Oct 20-22 with N = 7 the pages created Oct 13-19 need the 2026-10 snapshot. For September the 78-column cohort file already has both columns.
- Interim proxy if the snapshot is late: `page_id` is assigned in creation order, so `page_id >=` the smallest `page_id` among create events inside the look-back. Breaks for drafts moved into namespace 0 (old id, new to readers).
- Weaknesses: new stubs, redirects and moved drafts dominate; breaking news on existing pages is missed (Harald_V, page_id 66069); new pages are often deleted, which removes or flags their revisions in later snapshots, so label coverage is worse in this slice; page creations have no revert-risk score and 0 of 5,392 were reverted within 4 days (`FACTS.md:333-334`).

**D3. Editorial signals on Wikipedia (no EventStreams connection needed)**
- Template family: `action=query&list=embeddedin&eititle=Template:Current&einamespace=0&eilimit=max` (repeat for Current related, Current disaster, Current person, Current election; the family guide is Wikipedia:Current event templates).
- Category: `action=query&list=categorymembers&cmtitle=Category:Current events&cmnamespace=0&cmprop=ids|title|timestamp&cmsort=timestamp&cmlimit=max`. The `timestamp` is when the page entered the category, which gives a start time without polling. There is no removal time: poll hourly and diff, or read `list=recentchanges&rctype=categorize&rctitle=Category:Current events` (recent changes are kept about 30 days; if true, Oct 20-22 drops out around Nov 19-21, so fetch soon).
- Portal: `action=query&prop=links&titles=Portal:Current events/2026 October 20&plnamespace=0&pllimit=max`, one daily subpage per date. These pages are archival, so this is the only editorial signal that can be backfilled for both cohorts.
- Rule: a revision is in the slice when an interval row exists with `page_id` equal and `valid_from <= asof_ts < valid_to`. Template or category: first seen to last seen plus one poll interval. Portal: date d 00:00 UTC to d + 2 days, and only for pages linked on 3 or fewer days in the prior 90 (drops context links such as countries).
- Cost: about 100 lines of requests code with continuation and backoff, a scheduler, and a few thousand rows.
- Weaknesses: tiny group (the template is meant for articles many people edit on the same day and is removed quickly), tagging lags the event, humans apply it unevenly, portal links are noisy. Best used as a validation set for D1 and D2, not as the main slice.
- RAN here: the en.wikipedia.org API is reachable through the proxy but returned HTTP 429 twice: "You are making too many requests to the API." The poller must run elsewhere.

**D4. Pageview spikes**
- Rule: `is_pv_spike := views_user(d-1) >= 5 * median(views_user over d-29..d-2) AND views_user(d-1) >= 1000`, where d is the UTC date of the edit. Using d-1 keeps it as-of.
- Sources: Analytics REST `.../metrics/pageviews/top/en.wikipedia/all-access/YYYY/MM/DD` (1,000 pages per day) and `.../per-article/en.wikipedia/all-access/user/<title>/daily/<start>/<end>`; or the daily `pageview_complete` dump files. Both hosts are blocked from this container (RAN: 403).
- Cost: top-1000 is about 60 requests for both months but gives no baseline; baselines for the 165,415 cohort pages mean one request per page or about 35 daily dump files per cohort.
- Weaknesses: measures readers, not editors; daily grain lags breaking news by up to a day; anniversaries, television and automated traffic cause spikes; new pages have no baseline; keyed by title, so the join needs `dim_page` as-of (a use for the SCD2 dimension, and the same issue as hypothesis H4).

**D5. Title-year heuristic (optional):** `page_title RLIKE '(^|[^0-9])2026([^0-9]|$)'`. Catches 2026_Kazakh_legislative_election and 2026_Yemen_offensives; misses IPhone_Duo and GPT-6.

**Recommendation for the plan**
- Build D1 and D2 in Gold now from data already held; they cover both cohorts.
- Headline slice: `ce_strict := D1b AND (D2 OR D3 OR D5)`; wide slice: `ce_any := D1a`.
- Add D3 portal backfill plus forward polling as a validation set. Treat D4 as a stretch item (top-1000 only).
- Store every definition as rows in one interval dimension so that adding a definition never changes a schema.

## Evidence from committed results

**How common are bursts (RAN: computed from `ec-hw2/results/mongo_q5_truth_lag_preview_activity.csv`; cohort totals match `FACTS.md`)**

| Page edits in prior hour | History edits (Sep 8-10) | Share | Reverted within 4 d | Live edits (Oct 20-22), sliding hour | Share | Reverted within 4 d |
|---|---|---|---|---|---|---|
| 0 | 202,410 | 68.61% | 5.63% | 190,392 | 68.13% | 6.05% |
| 1 | 42,155 | 14.29% | 5.98% | 39,277 | 14.05% | 6.27% |
| 2-4 | 32,697 | 11.08% | 8.03% | 30,782 | 11.01% | 8.49% |
| 5-9 | 11,888 | 4.03% | 6.45% | 11,929 | 4.27% | 6.56% |
| 10+ | 5,866 | 1.99% | 5.85% | 7,086 | 2.54% | 6.20% |
| Total | 295,016 | | 5.98% | 279,466 | | 6.38% |

- 5 or more: 17,754 history edits (6.02%) and 19,015 live edits (6.80%).
- Eventual 4-day reverts inside the slices: 10+ has 343 (history) and 439 (live); 5+ has 1,110 and 1,221. These are the denominators E(L) would use.
- The revert rate is not higher on the busiest pages. It peaks at 2-4 prior edits and falls back to about the overall rate at 10+. So "burst" does not mean "more reverted"; whether reverts are known sooner or later there (the E(L) question) is not in the committed results.
- The live clock-hour measure from `page_hour` puts only 3,185 edits (1.14%) in 10+ because "the edits earlier in the same clock hour are not in it" (`mongo_q5_truth_lag_preview_activity.md`).
- `page_hour` holds 605,017 page-hours over the capture (`FACTS.md:115`); its distribution is not committed.

**Baselines the slice would be compared with (READ `ec-hw2/results/mongo_q5_truth_lag_preview.csv`, 4-day horizon)**
- History, all editors: 55.66% of eventual reverts known after 1 h and 88.96% after 1 d, so E(1 h) = 44.3% and E(1 d) = 11.0%.
- Live, all editors: 57.95% and 89.44%, so E(1 h) = 42.0% and E(1 d) = 10.6%.
- Editor kind matters a lot: history temporary accounts 62.4% known at 1 h, registered 47.5%, bots 25.5% (157 eventual reverts only).

**Pages that look like current events (history cohort, Sep 8-10 2026; human edits; reverts by another editor within 20 days). Classification is my reading of the titles; the committed results hold no creation dates or news flags.**

| Page (page_id) | Edits | Revert actions | Editors in any revert | Other | File |
|---|---|---|---|---|---|
| IPhone_Duo (84184840) | 255 | 19 | 22 | 4 warring editors, 3 mutual pairs; score 19/255 = 0.07, so not "contested" | `cypher_q4_pages_most_warring_editors_by_any_revert.csv` |
| 2026_Yemen_offensives (84167596) | 197 | 5 | 10 | | same |
| Death_and_state_funeral_of_Harald_V (84083326) | 119 | 8 | 11 | 2 warring | same |
| The_Legend_of_Zelda:_Ocarina_of_Time_(2026_video_game) (83401625) | 102 | 9 | 14 | | same |
| Hanuman_Ansh (83375714) | 96 | 12 | 18 | | same |
| Danny_Tommo (84165176) | 36 | 9 | 16 | | same |
| 2026_Kazakh_legislative_election (83118601) | 25 | 9 | 15 | 2 warring, 1 mutual pair | same |
| GPT-6 (84135854) | 23 | 17 | 8 | score 0.739, rank 9; 6 warring, 4 mutual pairs | `mongo_q2_top_contested_pages.csv`, `cypher_q4_pages_most_warring_editors.csv` |
| Harald_V (66069) | 15 | 8 | 8 | 4 warring; old page hit by the same event | `cypher_q4_pages_most_warring_editors.csv` |
| 2026_Pennsylvania_gubernatorial_election (72291474) | 14 | 9 | 6 | score 0.643, rank 13 | `mongo_q2_top_contested_pages.csv` |
| Avian_influenza (442916) | 9 | 6 | 4 | 3 warring | `cypher_q4_pages_most_warring_editors.csv` |
| Queen_Sonja_of_Norway (98262) | 6 | 5 | 4 | 3 warring; same event cluster | same |

**What these examples show**
- Several have the highest page ids in the results (84.08-84.18 million), which fits pages created just before the window. That supports D2, but it is not proof.
- One event spreads over several pages, old and new (Harald_V, Death_and_state_funeral_of_Harald_V, Queen_Sonja_of_Norway). D2 alone misses the old ones.
- The busiest news page (IPhone_Duo, 255 edits) has a low revert share, so the contested-page score from ec-hw2 does not find current events. A separate slice is justified.
- Counter-examples that a burst rule would wrongly include: Watergate_scandal (52382; 32 edits, 28 revert actions, score 0.875), PB&J_Otter (3146234; 39 edits, 34 revert actions), Pendulum (42709; median time to revert 27 s, `FACTS.md` example_fast), List_of_2018_albums (54168882; 261 revisions, `results/sharding.md:33`), September_10 (28020; 19 edits, a date page edited on its own date).
- Only 126 of 165,415 pages are "contested" (`FACTS.md:177`, `scaleout/SHARDING.md:20`).

## Proposed marts

**Silver additions**
- `silver.page_activity_hour`. Grain: wiki_db, page_id, hour_start, source (stream or history). Columns: edits, human_edits, nonrevert_human_edits, distinct_human_editors, revert_events, reverted_revs, creates. Computed by grouping Silver events on the hour of `meta_dt` (stream) or `event_timestamp` (history). Replaces the MongoDB `page_hour` collection (`ec-hw2/speed_layer.py`).
- `silver.current_event_signal`. Append-only observations from Bronze API or pageview pulls: wiki_db, page_id, page_title, signal_source, signal_ts, observed_at, payload.

**Gold**
1. `gold.dim_page_current_event`. Grain: one interval per (page_id, definition). Columns: ce_key, wiki_db, page_id, definition (`burst_1h_10`, `burst_episode`, `new_page_7d`, `tpl_current`, `cat_current_events`, `portal_daily`, `pv_spike`, `title_year`), valid_from, valid_to, is_open, evidence (peak edits per hour, distinct editors, page_created_dt, template or portal date), computed_at. Computed by gaps-and-islands over `page_activity_hour` (burst), `[created_dt, created_dt + N days)` (new page), first-seen to last-seen (editorial). Loaded with MERGE on (page_id, definition, valid_from), closing open intervals: the same pattern as `dim_page` SCD2.
2. `gold.bridge_edit_slice`. Grain: revision x definition (long form). Columns: wiki_db, rev_id, definition, in_slice, evidence_value. Computed by the as-of range join `e.page_id = d.page_id AND e.asof_ts >= d.valid_from AND e.asof_ts < d.valid_to`, plus the edit-level features `page_edits_prev_1h`, `page_distinct_editors_prev_1h`, `page_age_days_at_edit`. Derived rows `ce_any` and `ce_strict` live here too. `fact_edit` stays narrow.
3. `gold.mart_el_by_slice`. Grain: cohort, label_source (stream or history snapshot), horizon_s, definition, in_slice, user_kind (including all), wait_s. Columns: n_edits, n_pages, n_eventual_reverted, n_known_by_wait, share_known, e_l, wilson_lo, wilson_hi, boot_lo, boot_hi, top_page_share, min_followup_s, suppressed, label_table_version.
4. `gold.mart_el_slice_contrast`. Grain: cohort, label_source, horizon_s, definition, wait_s. Columns: e_in, e_out, diff, ratio, diff_lo, diff_hi, e_in_standardized (reweighted to the out-group mix of user_kind), still_wrong_in, still_wrong_out (= revert rate x E(L), per edit).
5. `gold.mart_time_to_flag_km`. Grain: cohort, definition, in_slice, t. Columns: n_at_risk, n_events, n_censored, survival. Time from edit to the moment the revert is known, censored at `followup_s`.
6. `gold.mart_current_event_episodes`. Grain: page_id, episode. Columns: title as of the episode, first and last hot hour, edits, distinct editors, revert actions, revert rate, share known at 1 h, which definitions fired. This is the named-example table (IPhone_Duo and the like).
7. `gold.mart_slice_overlap`. Grain: cohort, definition_a, definition_b. Columns: n_both, n_only_a, n_only_b, jaccard. Shows how far burst and editorial definitions agree.

**Core computation of mart 3**
```sql
SELECT e.cohort, l.label_source, :H AS horizon_s, s.definition, s.in_slice, e.user_kind, w.wait_s,
       COUNT(*) AS n_edits, COUNT(DISTINCT e.page_id) AS n_pages,
       SUM(CASE WHEN l.t_s BETWEEN 0 AND :H THEN 1 ELSE 0 END) AS n_eventual_reverted,
       SUM(CASE WHEN l.t_s BETWEEN 0 AND :H AND l.known_by_s <= w.wait_s THEN 1 ELSE 0 END) AS n_known_by_wait
FROM gold.fact_edit e
JOIN gold.bridge_edit_slice s USING (wiki_db, rev_id)
LEFT JOIN gold.fact_revert_label l USING (wiki_db, rev_id)
CROSS JOIN gold.dim_wait w
WHERE e.followup_s >= :H
GROUP BY 1,2,3,4,5,6,7;   -- e_l = 1 - n_known_by_wait / n_eventual_reverted
```
`known_by_s` = T + K for stream labels and T for history labels, as in ec-hw2 Mongo Q5.

**How to compare E(L) between current-events pages and other pages**
1. **One fixed horizon for both groups.** Keep only revisions followed at least H, and define "eventually reverted" as reverted within H. The horizon changes the answer: the September share known at 1 h is 49.86% with a 20-day horizon and 55.66% with 4 days (`FACTS.md` history_T_within_1h_pct and history_T_within_1h_4d_pct). Options: 4 days (stream), up to 9 days (October with the 2026-10 snapshot, if its cutoff is about Nov 1), 20 days (September).
2. **Never report E(L) for L beyond the shortest follow-up.** Where follow-up is unequal (pooled capture days for a rare slice), use the Kaplan-Meier mart and compare curves or restricted mean time, not raw shares.
3. **Small groups.** Reuse the existing rule of 100 eventual reverts (`config.RISK_MIN_GROUP_N`; Mongo Q5 drops smaller groups) but set `suppressed = true` instead of dropping rows. At p near 0.5 the 95% half-width is about 4.7 points for 439 eventual reverts, 5.3 for 343, 2.8 for 1,221 and 9.8 for 100. Editorial slices will likely be below 100 in a 3-day cohort, so pool the whole capture.
4. **Clustered data.** Revisions on one page are not independent, and one revert can cover many revisions. Wilson intervals on revisions are too narrow. Use a bootstrap that resamples pages (for example 1,000 draws), and publish `n_pages` and `top_page_share`. Add a leave-one-page-out check, because one page can carry a slice (IPhone_Duo alone is 255 edits).
5. **Composition.** Editor kind drives timing (temporary 62.4% known at 1 h versus registered 47.5%). News pages are often protected, which changes the mix. Report E(L) within user_kind and a standardized contrast.
6. **Two views of the gap.** E(L) is conditional on being reverted. Also report the per-edit share still wrong at L (revert rate x E(L)), because the groups' revert rates differ.
7. **Definition leakage.** Count only non-revert human edits in the burst rule; otherwise the slice is selected on revert activity. Use only as-of features for any "early signal" claim.
8. **Label noise that differs by slice.** On busy pages later edits sit between an edit and its removal, so removals are more often partial and the dump's identity-revert label misses them (194 `inexact_undo` late reverts show the gap exists). Report revert method mix and the live-to-dump match rate per slice. In the new-page slice, deleted pages remove labels.
9. **Multiple looks.** Nine wait points times several definitions and thresholds. Fix the primary contrast before looking: for example `burst_1h_10` versus the rest at L = 1 h and 1 d; everything else is sensitivity.

## Risks

1. **The key input is unconfirmed.** dumps.wikimedia.org is blocked here, so the plan cannot assume 2026-10 exists or know its size. It needs a step 0 check and a fallback path that runs on 2026-09 plus stream labels only.
2. **Upstream retention.** Only two snapshots are kept. The 2026-09 raw `.bz2` exists only on the VPS today, and upstream will drop it when 2026-11 is published (early December, by the stated schedule). If it is not mirrored, the September-versus-October label diff cannot be rebuilt from raw.
3. **Where ingestion can run.** This container cannot reach the dump host, the pageviews API, or (in practice) the MediaWiki API (HTTP 429 from the shared egress address). The executing session needs a machine with access, or pre-staged files.
4. **The existing History extracts are too narrow.** The VPS filter dropped page and user events and kept 12 columns for most of September. New-page detection and `dim_page` SCD2 need the full monthly file re-read.
5. **Editorial signals decay.** Template and category membership is only known from the first poll onward. The 30-day recent-changes route for Oct 20-22 (unverified) would close around Nov 19-21. Portal daily pages remain the only safe backfill.
6. **No ground truth for "current event".** A burst rule mixes news with edit wars, vandal fights and list upkeep. Without a hand-checked sample (for example the top 50 episodes) or the editorial list as reference, the slice's precision is unknown.
7. **Small and clustered groups.** The 10+ burst slice has 343-439 eventual reverts in a 3-day cohort from a limited number of pages; editorial slices will be far smaller. Naive intervals will overstate certainty.
8. **The burst measure differs by cohort.** Live uses publication time and counts stream events; history uses revision time and counts every slim-file revision. Cross-cohort comparison of the slice needs one shared rule recomputed in Silver.
9. **Finding may be null.** Committed results show no higher revert rate on the busiest pages. The slice may show a timing difference or none. The plan should present it as a measured comparison, not a presumed effect.
10. **Pageviews cost.** Full baselines mean tens of GB of downloads and a title-to-page_id as-of join. It can absorb time without changing the conclusion.
11. **Adding a stream for category changes.** `mediawiki.recentchange` carries category changes, and one connection can carry several streams (capture-a already does, `ingest/vps/README.md`), but that means restarting a capture unit, which the repo forbids from here (`config.py:43-44`), and it only works forward.
12. **API etiquette.** Wikimedia asks automated clients for a descriptive user agent; the team must choose its own. I used a generic one and included no personal or project details.

## Test matrix

| Feature | Status | Evidence |
| --- | --- | --- |
| HTTP HEAD/GET to dumps.wikimedia.org (History listing, 2026-10 check, file sizes) | fails | RAN: curl HEAD and GET on https://dumps.wikimedia.org/other/mediawiki_history/ and /2026-10/enwiki/ both failed. Proxy status: connect_rejected, 'gateway answered 403 to CONNECT (policy denial or other refusal)', host dumps.wikimedia.org:443. WebFetch: 'getaddrinfo ENOTFOUND dumps.wikimedia.org'. |
| MediaWiki Action API on en.wikipedia.org (embeddedin Template:Current) | partial | RAN: CONNECT 200 through the proxy, but HTTP 429 on both attempts (siteinfo, then list=embeddedin), header x-envoy-ratelimited: true, retry-after: 46. No API data obtained; parameter names in the report are UNVERIFIED. |
| Wikimedia pageviews REST (wikimedia.org/api/rest_v1) and docs hosts (wikitech, mediawiki.org, meta) | fails | RAN: same CONNECT 403 for wikimedia.org, wikitech.wikimedia.org, www.mediawiki.org, meta.wikimedia.org, api.wikimedia.org, analytics.wikimedia.org, three dump mirrors and web.archive.org. |
| Upstream dump file naming and enwiki monthly split | works | READ: MediawikiHistoryDumper.scala fetched from raw.githubusercontent.com/wikimedia/analytics-refinery-source/master (HTTP 200, 12,890 bytes, sha256 9a742fda...), lines 90-94 and 268-269. Agrees with notebooks/00_access_points.ipynb cell 6 and ec-hw2/config.py:71-72. |
| Monthly cadence, timing and two-snapshot retention | works | READ: ec-hw2/report/references.md:136-138 (verbatim Wikitech quotes with permanent link oldid=2433177); notebooks/00_access_points.ipynb cell 7 output on 2026-10-15; ec-hw2/genai/APPROVED_PLAN.md:8,27; docs/schema_and_warehouse.md:34. |
| Burst frequency from committed results | works | RAN: python over ec-hw2/results/mongo_q5_truth_lag_preview_activity.csv. Bucket totals sum to 295,016 (history) and 279,466 (live), matching FACTS.md. |
| Is the 2026-10 snapshot published, and sizes of 2026-10.enwiki.2026-09 / 2026-10.enwiki.2026-10 | untested | UNVERIFIED: host blocked. File names are derived from the upstream naming code; the only known size is 557,344,652 bytes for 2026-09.enwiki.2026-09.tsv.bz2 (ec-hw2/config.py:73). |

## Tested snippets

### HTTP HEAD/GET to dumps.wikimedia.org (History listing, 2026-10 check, file sizes)

```bash
curl: (56) CONNECT tunnel failed, response 403
```

### MediaWiki Action API on en.wikipedia.org (embeddedin Template:Current)

```text
You are making too many requests to the API.
Please follow the best practices at https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits.
```

### Wikimedia pageviews REST (wikimedia.org/api/rest_v1) and docs hosts (wikitech, mediawiki.org, meta)

```bash
curl: (56) CONNECT tunnel failed, response 403
```

### Upstream dump file naming and enwiki monthly split

```text
val WikisInMonthlyBuckets = Seq("wikidatawiki", "commonswiki", "enwiki")
val destinationDirectory = s"$outputBasePath/$snapshot/$wiki"
val destinationFile = s"$snapshot.$wiki.$timeBucket.tsv.bz2"
```

### Monthly cadence, timing and two-snapshot retention

```text
"The updates for this data set are monthly, around the end of the month's first week."
"for storage reasons only the last two versions are available."
200 ['../', '2026-08/', '2026-09/', 'readme.html']
```

### Burst frequency from committed results

```text
history prev_1h >=10: 5866 (1.99%), eventual reverts 343; >=5: 17754 (6.02%), 1110
live prev_1h >=10: 7086 (2.54%), eventual reverts 439; >=5: 19015 (6.80%), 1221
```

## Open questions

- Is the 2026-10 snapshot online today, and what are the byte sizes of 2026-10.enwiki.2026-09.tsv.bz2 and 2026-10.enwiki.2026-10.tsv.bz2? Not checkable here: dumps.wikimedia.org has to be allowed in the session's network settings, or checked from another machine.
- What is the exact cutoff (last revision timestamp) of the 2026-10 snapshot, and is there a 2026-10.enwiki.2026-11 spill-over file? This sets the uncensored horizon for the Oct 20-22 cohort (9 days if the cutoff is about Nov 1).
- Is the raw 2026-09 .bz2 still on the VPS, and will the team mirror both raw snapshots before upstream drops 2026-09 (expected when 2026-11 is published in early December)?
- Does an upstream archive of older snapshots exist? A web search result hinted at one via a third-party scraper project; the repo's quoted documentation says only two versions are available.
- Which machine will run History download and API polling? This container cannot reach the dump host or the pageviews API, and the MediaWiki API answered 429.
- How many pages carry {{Current}} or sit in Category:Current events at one time, and are recent changes of type categorize kept 30 days and filterable by category title? All unverified; they decide whether the editorial definition can be backfilled for Oct 20-22.
- Do captured page_change events carry any page creation time or redirect flag beyond the create event itself? The raw data is not in this container.
- Which History column is the right creation time for the new-page rule: page_creation_timestamp or page_first_edit_timestamp? And how should drafts moved into namespace 0 be treated?
- Team decisions: primary definition and thresholds (10 or 5 edits per hour, distinct-editor minimum, N days for new pages), and whether the slice is descriptive only or also an 'early signal' feature.
- What is the distribution of edits per page-hour over the capture? The page_hour collection (605,017 page-hours) is not committed, so episode counts cannot be estimated from the repo.
- May the team add mediawiki.recentchange to an existing VPS connection to capture category changes going forward? It needs a capture restart, which the repo currently forbids.
- Should the September month file be re-read in full (all 6,369,430 rows, all 78 columns) so that page and user events and creation timestamps are available for dim_page SCD2 and the new-page slice?
