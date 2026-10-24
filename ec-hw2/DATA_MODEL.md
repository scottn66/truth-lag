# Data model: every file, table and collection in EC HW2

This page lists every data file the scripts make, with its columns. If a script and this page disagree, the bug is in the script. All rules (windows, thresholds) are in `config.py`. All times are UTC.

```
VPS capture (raw .ndjson.gz) --rsync--> data/raw/ ---------> parse_stream.py --> data/parsed/*.parquet --+
VPS-filtered dump (.parquet)  --rsync--> data/history/ ----> parse_history.py ------------------------+    |
                                                                                                    v    v
                                                   data/tables/{history,live}_revisions.parquet  (+ revert_links)
                                                                         |
                                     build_documents.py + load_mongo.py  v              load_sql.py
                                            MongoDB  (revisions, revert_links, page_hour, ...)    --> data/tables/truthlag.sqlite
                                                 |                                                    (history cohort, from the
                                  export_graph.py v                                                    Parquet tables)
                                  data/neo4j/import/*.csv
                                                 |
                                  load_neo4j.py   v
                                            Neo4j (Editor, Page, EDITED, REVERTED)
```

## 1. Input files (copied from the VPS; never edited)
| File | What it is |
|---|---|
| `data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-<session>-<n>.ndjson.gz` | One raw event per line, enwiki only, canary events removed. The partitions use `meta.dt`. A file that is still open has no gzip end marker yet. |
| `data/history/enwiki_rev_ns0_2026-09-08_10.parquet` | 300,564 dump rows, all 78 columns, **all strings**. Revision creates on pages whose *current* namespace is 0, dated 2026-09-08 to 2026-09-10. |
| `data/history/enwiki_rev_all_2026-09_slim.parquet` | 5,266,843 rows: every September 2026 revision (all namespaces). 12 string columns, see `config.HISTORY_SLIM_COLUMNS`. |

The streams are `mediawiki.page_change.v1` (edits, with `revision.revert`), `mediawiki.page_revert_risk_prediction_change.v1` (live revert-risk score) and `mediawiki.revision-tags-change` (tags, including `mw-reverted`).

## 2. Parsed stream tables (`data/parsed/`, made by `ingest/parse_stream.py`)
- **Dedupe rule:** each table keeps one row per `meta.id`. The capture can repeat events after a reconnect.
- **Files:** it reads every part file older than 2 minutes, and a broken gzip end only loses that file's last line.

| Table | One row per | Main columns |
|---|---|---|
| `page_change.parquet` | page_change event, **all namespaces**, all kinds | meta_id, wiki_id, meta_dt, topic, partition, offset, kind, page_id, page_title, ns, rev_id, parent_id, rev_dt, rev_size, sha1, comment, prior_rev_id, prior_rev_dt, prior_rev_size, prior_sha1, user_id, user_name, is_bot, is_temp, edit_count, revert_method, revert_is_exact, revert_original_id, revert_original_dt, revert_oldest_id, revert_newest_id |
| `revert_risk.parquet` | rev_id (earliest score kept) | rev_id, page_id, meta_dt, rev_dt, prob_true, model_name, model_version |
| `tag_events.parquet` | tags-change event | meta_id, meta_dt, rev_id, page_id, ns, rev_timestamp, tags, prior_tags, added, removed, mw_reverted_added |
| `capture_gaps.csv` | hole in the data | stream, topic, partition, gap_start, gap_end, gap_s. A hole is two consecutive kept events of one stream more than `config.CAPTURE_GAP_S` (120 s) apart. Kafka offsets are shared with other wikis, so offset jumps are normal and are not gaps; topic/partition are those of the first event after the hole. |

## 3. Cohort tables (`data/tables/`)
### `history_revisions.parquet` and `live_revisions.parquet` (the same columns)
| Column | Type | history cohort (dump) | live cohort (stream) |
|---|---|---|---|
| cohort | str | `history` | `live` |
| wiki_db | str | wiki_db | wiki_id |
| rev_id | int | revision_id | revision.rev_id |
| parent_id | int/null | revision_parent_id | revision.rev_parent_id |
| page_id | int | page_id | page.page_id |
| page_title | str | the dump's CURRENT page_title (falls back to page_title_historical); this keeps vandal page-move titles out of the results | page.page_title |
| page_title_historical | str | page_title_historical (the title at edit time) | page.page_title |
| page_ns | int | page_namespace_historical (must be 0) | page.namespace_id (must be 0) |
| ts | time | event_timestamp | revision.rev_dt |
| seen_ts | time/null | null | meta.dt of the edit event |
| hour_utc | int | hour of ts | hour of ts |
| size | int | revision_text_bytes | revision.rev_size |
| size_delta | int | revision_text_bytes_diff | rev_size − prior rev_size (a page creation: rev_size) |
| comment | str | event_comment | revision.comment |
| tags | list[str] | revision_tags without `mw-reverted` | tags from tag events ≤60 s after ts, without `mw-reverted` |
| mw_reverted_tag | bool | `mw-reverted` in revision_tags | an `mw-reverted` addition was seen |
| mw_reverted_at | time/null | null | meta.dt of the first `mw-reverted` addition |
| is_revert | bool | revision_is_identity_revert | `revision.revert` is present |
| revert_method | str/null | null | revision.revert.method |
| user_id | int/null | event_user_id | performer.user_id |
| user_name | str/null | event_user_text_historical | performer.user_text |
| user_kind | str | `config.user_kind(...)` | `config.user_kind(...)` |
| user_key | str/null | `config.editor_key(...)` | `config.editor_key(...)` |
| is_bot, is_temp, is_anon | bool | from user_kind (is_anon = temporary) | same |
| edit_count | int/null | event_user_revision_count (counts the edit itself: minimum 1) | performer.edit_count (does NOT count the edit itself: can be 0). Add 1 before comparing cohorts. |
| sha1 | str | hex of revision_text_sha1 (base 36 in the dump) | hex of revision.rev_sha1 (also base 36 in the stream; only the API uses hex) |
| revert_risk | float/null | null | prob_true from revert_risk |
| page_edits_prev_1h | int | revisions on the page in [ts−1 h, ts), from the slim file | page_change edits on the page with meta.dt in [seen_ts−1 h, seen_ts): what was known when the edit was seen |
| followup_s | int | `HISTORY_DUMP_LAST_REVISION − ts` | newest captured meta.dt − ts |

**Labels.** The live labels are *not* stored in `live_revisions` (they live in `revert_links`). This is so that Mongo Q5 must join with `$lookup`. The history labels **are** stored, because the spec's document shape has a `history` part.

| Column | Type | history cohort |
|---|---|---|
| reverted | bool | revision_is_identity_reverted AND seconds ≤ 20 days |
| reverted_any | bool | revision_is_identity_reverted (any time before the snapshot) |
| secs_to_revert | int/null | revision_seconds_to_identity_revert |
| reverting_rev_id | int/null | revision_first_identity_reverting_revision_id |
| reverter_key, reverter_name, reverter_kind | | from the reverting row in the slim file |
| reverted_by_other | bool | reverter_key ≠ user_key (both not null) |

**Rows dropped from both cohorts:**
- null revisions: same sha1 as the parent revision; this includes page moves and protection changes.
  - History: rule (a) sha1 = parent sha1 when the parent is in the cohort file and both sha1 values are known; otherwise rule (b) bytes_diff = 0 and the comment (after removing a leading "<editor name> ") starts with one of `config.NULL_REV_COMMENT_PREFIXES`.
  - Live: page moves arrive as kind `move` and are dropped by the kind rule, so the sha1 rule drops 0 live rows.
  - History `parent_id` is 0 (not null) for page creations, as in the dump.
  - Known asymmetry: the history cohort cannot contain edits on pages that were moved out of namespace 0 before the snapshot (the VPS filter keeps the CURRENT namespace 0), while the live cohort keeps them (namespace at event time). In the live data this is a few hundred revisions, mostly pages moved to Draft.
  - Empty comments are stored as null in both cohorts.
- revisions outside the window
- namespace not 0

Each script prints how many rows each rule drops.

### `history_revert_links.parquet` and `live_revert_links.parquet`
There is one row per **reverted cohort revision**. For the live cohort, the row is its **first covering exact revert**, ordered by (rev_dt, rev_id).

| Column | Meaning |
|---|---|
| cohort, source | `history` + `dump`, or `live` + `stream` |
| reverted_rev_id, page_id, reverted_ts, author_key, author_kind | the revision that was reverted |
| reverting_rev_id, reverting_ts, reverter_key, reverter_name, reverter_kind | the revert |
| T_s | time to revert = reverting_ts − reverted_ts (seconds) |
| known_at, K_s | live only: meta.dt of the reverting event, and K = known_at − reverting_ts, in seconds (float, millisecond precision) |
| method, is_exact | live: rollback / undo / manual and exactness. History: null / true |
| by_other | reverter_key ≠ author_key |
| within_followup | T_s ≤ 20 days (history) or ≤ 4 days (live) |
| range_size | live: number of CAPTURED revisions the revert covered. A lower bound when range_complete is false. |
| range_complete | live: true when revert_oldest_id is a captured revision on that page, or oldest_id ≥ the page's first captured rev_id (the whole range is inside the capture). History: null. |
| confirmed_by_tag | history: `mw-reverted` is in revision_tags of the reverted revision (= mw_reverted_tag); live: an `mw-reverted` addition was seen for this revision |

**Range cover (live).** A revert event E on page P covers revision R (on page P) when all of these hold:
- `R.rev_dt < E.rev_dt`
- E is exact: `(E.revert_original_dt, E.revert_original_id) < (R.rev_dt, R.rev_id) <= (E.prior_rev_dt, E.parent_id)`. An exact revert restores the original version, so it identity-reverts everything after the original up to its parent, as the dump does (this includes the edits after newest_id when an exact undo targets an older edit).
- E is not exact: `E.revert_oldest_id <= R.rev_id <= E.revert_newest_id` and `(R.rev_dt, R.rev_id) <= (E.prior_rev_dt, E.revert_newest_id)`. An inexact undo changes only the edits it names.

We check that `E.revert_newest_id == E.parent_id` and log every exception (undos of older edits are the normal exception). Revert events are never filtered by namespace.

`live_revert_links_all.parquet` keeps **every** (reverted, reverting) pair, for all methods. It is used for sensitivity checks. Extra columns: page_ns, in_cohort, beyond_newest (the pair lies after revert_newest_id; only exact undos of an older edit have it, and MediaWiki does not tag these); cohort is null when the reverted revision is not in the live cohort.

The history reverter fields are null when the reverting revision is not in the slim September file (4 links, all with T > 20 days, reverted on 2026-10-01). `K_s` is float seconds (millisecond precision) in the live table and empty in the history table.

### `late_reverts.parquet` (case study)
There is one row per **September** rev_id (from the slim file) where the dump says *not* reverted, but the October stream shows a revert.

| Column | Meaning |
|---|---|
| rev_id, page_id, rev_ts | the September revision |
| first_signal_at | the earliest stream signal: the covering revert's meta.dt, or the tag's meta.dt |
| via | the set of sources: `page_change`, `tag` |
| class | `exact` (the label changed after the snapshot), `inexact_undo` (a definition gap: History will never count it), or `method_unknown` (a tag only) |
| reverting_rev_id, method | null when only a tag was seen |
| age_days, age_upper_bound | from the reverting rev_dt. For tag-only rows it uses the tag time and age_upper_bound is true. |
| page_ns | the page's current namespace. All namespaces are kept; late_reverts_summary.json also gives the namespace-0 counts (`*_ns0`). |
| restored_later | a later revert covered the reverting revision |
| in_history_cohort | the rev_id is in the history cohort (Sep 8–10) |

All counts are **lower bounds**: no one watched the stream from 2026-10-01 01:38 UTC until the capture started.

## 4. MongoDB (database `truthlag`)
- `revisions`: one document per revision, both cohorts.
  ```
  {_id: "enwiki:<rev_id>", wiki_db, rev_id, parent_id, cohort: "history"|"live",
   page: {id, title, ns},
   user: {id, name, kind, key, is_bot, is_anon, is_temp, edit_count},
   ts, hour_utc, size, size_delta, comment (first 120 characters), tags: [...], mw_reverted_tag,
   is_revert, revert_method,
   live:    {seen_ts, revert_risk, page_edits_prev_1h},                  // live documents only
   history: {snapshot: "2026-09", reverted, reverted_any, secs_to_revert, reverting_rev_id,
             reverter: {key, name, kind} or null, reverted_by_other, followup_s,
             page_edits_prev_1h}}                                          // history documents only
  ```
  - Indexes: `{"page.id": 1, ts: 1}`, `{"user.id": 1}`, `{"history.reverted": 1}`, `{cohort: 1, ts: 1}`.
- `revert_links`: the rows of both revert-link tables (all link columns, nulls kept). `_id: "<cohort>:<reverted_rev_id>"`. Indexes `{reverted_rev_id: 1}`, `{page_id: 1}` (makes the self-`$lookup` of compare_mutual_reverts take 0.12 s instead of 34 s) and `{cohort: 1, page_id: 1}`.
- `page_hour` holds the live counters. Its key is `{_id: "<page_id>:<YYYY-MM-DDTHH>"}`, with page_id, hour, edits_seen, revert_events_seen and reverted_revs_seen. Each count goes in the hour (meta.dt) when it **became known**. It is rebuilt the same way every time (staging collections `page_change_min` and `page_change_min_cover`, then `$group` + `$merge`, then the staging collections are dropped; field `built_at`); a batch build never uses `$inc`.
- `page_hour_live` is the `--follow` demo only. It may use `$inc`, and counts only edits_seen and revert_events_seen.
- `tag_events` holds `mw-reverted` additions only (`_id` = meta_id; meta_dt, rev_id, page_id, ns, rev_timestamp, tags, prior_tags, added, removed), and `late_reverts` holds the case study (`_id` = rev_id, plus the Parquet columns).
- The chart collections are `chart_q1_hour_kind`, `chart_q3_time_to_revert`, `chart_q5_known_by` and `chart_q5_risk_deciles`. They are small, and their names **and fields** are frozen once Atlas Charts use them:
  - `chart_q1_hour_kind`: cohort, hour_utc, user_kind, edits, reverted, revert_rate
  - `chart_q3_time_to_revert` (cohorts `history` = 20-day horizon, `history_4d` = history reverts within 4 days, `live` = 4-day horizon; compare `history_4d` with `live`): cohort, bucket, bucket_order (1-11), bucket_sorted ("01 <1 min", sorts as text), bucket_lower_s, bucket_upper_s, n, share, cum_share
  - `chart_q5_known_by`: cohort, user_kind, wait, wait_s, wait_sorted ("01 0", sorts as text), n_edits, n_reverted_4d, revert_rate_4d, known, share_known
  - `chart_q5_risk_deciles`: the risk-decile table of Mongo Q5
- **Atlas** (free tier, 512 MB) gets the history documents **without `comment`**, `revert_links` for the history cohort, and the chart collections. On Atlas every human editor is a pseudonym in names and keys (`editor_` + 10 hex digits of HMAC-SHA256(ALIAS_SECRET, key); the secret is in ec-hw2/.env, so the alias cannot be reversed by trying user ids; it is a display mask on public data, not anonymization), and `user.id` is empty, because the whole team sees Data Explorer; bots keep their names.
- **Sharded demo** (`config.SHARDED_URI`, database `truthlag_sharded`): collection `revisions` = the history documents, sharded on `{"page.id": "hashed"}`; rebuilt by `scaleout/demo_sharding.py`.

## 5. Neo4j (built from the history cohort, via CSV files that MongoDB exports)
- **Nodes:**
  - `(:Editor {key, alias, kind, edits, reverts_made, reverts_received})`. `alias` is a pseudonym such as `editor_7f3a2b1c9d` (10 hex digits of HMAC-SHA256, see config.py) for humans; bots keep their real name.
  - `(:Page {id, title, edits, revert_actions, reverted_editors, score, contested})`
- Editor details: edits = history revisions of the editor (bots included); reverts_made / reverts_received = sum of `count` on outgoing / incoming REVERTED. Editors = history authors plus reverters with no history revision. Revisions without an editor key (3) get no node and no EDITED relationship. Cypher Q3 writes `communityId`.
- Page details: score is null when edits = 0 (bot-only pages). `title` is read from MongoDB `page.title` (the history table's display title rule: the dump's current title).
- **Relationships:**
  - `(:Editor)-[:EDITED {rev_id, ts, reverted, reverted_by_other, within_followup, reverting_rev_id}]->(:Page)`. `reverted` = `within_followup` (reverted within 20 days). `reverted_by_other` and `reverting_rev_id` mean "reverted at any time before the snapshot", so always add `within_followup` when you count 20-day reverts.
  - `(:Editor)-[:REVERTED {page_id, count, n_revisions, ts, last_ts}]->(:Editor)`, with one edge per (reverter, reverted editor, page). It only uses reverts by another editor within 20 days. `count` is the number of distinct revert actions, `n_revisions` the number of reverted revisions, and `ts` is the first one (the spec's `ts`).
  - One identity revert that covers several revisions makes one REVERTED edge per reverted author. Kittur et al. (2007) and Geiger & Halfaker (2017) count only the last (closest) author, so our graph has more edges per revert; say this in the Neo4j section.
- Indexes from `load.cypher`: the two uniqueness constraints, `reverted_page_id` (REVERTED.page_id, for Cypher Q4) and `page_contested` (Page.contested, for Cypher Q5).
- **CSV files** (`data/neo4j/import/`): `editors.csv`, `pages.csv`, `edited.csv` (editor_key, page_id, rev_id, ts, reverted, reverted_by_other, within_followup, reverting_rev_id), `reverted.csv` (reverter_key, author_key, page_id, count, n_revisions, ts, last_ts).

## 6. SQLite (`data/tables/truthlag.sqlite`, history cohort)
- Tables: `revisions` (the flat history columns; `rev_id` is the primary key) and `revert_links` (history), with indexes on page_id, reverted_rev_id, author_key and reverter_key.
- `revisions` also has page_title_historical; `revert_links` has range_complete (NULL).
- Storage: times are ISO text in UTC (`2026-09-08T00:00:00+00:00`); lists are comma text (`AWB,mobile edit`; a comma inside an item is `\,`; an empty list is ''); true/false are 1/0; empty values are NULL.
- Used by `queries/sql/compare_top_contested.sql`, `compare_mutual_reverts.sql` and `compare_mutual_reverts_preaggregated.sql` (builds a TEMP table of grouped triples in memory, not timed, then times the self-join; the database file is not changed).

## 7. Shared query definitions (the same in MongoDB, Cypher and SQL)
- **Contested pages:**
  - edits_p = non-bot history revisions on the page
  - revert_actions_p = distinct `reverting_rev_id` among links with `within_followup` and `by_other` on the page
  - reverted_editors_p = distinct `author_key` among those links
  - Keep pages with edits_p ≥ 10 and reverted_editors_p ≥ 2.
  - score = revert_actions_p / edits_p (a float).
  - Order by score desc, revert_actions desc, edits desc, page_id asc; top 20.
  - "Contested" also needs revert_actions ≥ 2 and score ≥ 0.2.
  - The 3 history revisions without an editor key count as human edits in MongoDB, SQL and pandas, but have no EDITED edge in Neo4j. This does not change the top 20.
- **Mutual reverts:**
  - From history links with `within_followup` and `by_other` (both keys not null), make the triples (reverter_key, author_key, page_id).
  - A mutual pair is {a, b} on page p when both (a, b, p) and (b, a, p) exist.
  - Report one row per page and unordered pair (a < b, plain binary string order of the editor key), with the counts in both directions: a_reverted_b and b_reverted_a = the number of DISTINCT reverting_rev_id in each direction on that page (the same as REVERTED.count).
  - Output columns: page_id, a, b, a_reverted_b, b_reverted_a. Order by page_id, a, b.

## 8. Status files
Each step writes `_SUCCESS_<step>.json` next to its output, with row counts and `data_version`: `_SUCCESS_history.json`, `_SUCCESS_parsed.json`, `_SUCCESS_live.json`, `_SUCCESS_late_reverts.json` (data/tables or data/parsed), and `_SUCCESS_<queries>.json` in `ec-hw2/results/`. `data/tables/DATA_VERSION` holds the data version of the release (written by `release_data.sh`).

## 9. Comparison outputs
- `results/comparison.csv` / `.md`: 2 questions × 3 engines. Columns include lines_of_code, code_chars, bracket_only_lines, median_ms, min_ms, max_ms, runs (3 rounds × 7 warm runs), faster_than (only when the min-max ranges do not overlap), same_result, input_note, modeling_pain and pain_scored_by.
- `results/comparison_extra.csv`: the extra pre-aggregated SQLite timing for mutual reverts.
- `comparison/pain.csv`: the modeling-pain scores. They start as drafts by Claude Code; the Comparison+viz owner re-scores them and writes their name in `scored_by`.
- Cypher Q3 also writes `results/cypher_q3_conflict_communities_community_sizes.csv` (all communities, communities with 2+ editors, single-editor communities); the main Q3 result has star_share (share of the community's REVERTED edges that touch its top editor) and top_page_share.
