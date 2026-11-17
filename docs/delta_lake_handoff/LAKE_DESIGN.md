# Lake design reference: tables, keys and clocks (draft v1, Nov 13, 2026)

> Exported on 2026-11-13 from the Notion page of the same name. The Notion page is the working copy; if the two differ, Notion is newer.

> **Purpose.** The table catalog for the TruthLag lakehouse: every Bronze, Silver and Gold table with its grain, key, source and write pattern. It is the recommended design from the build plan on the parent page, and it is a draft for review. The choices behind it are in the plan's **Design decisions** section. Columns that already exist are defined in `ec-hw2/DATA_MODEL.md`; this page lists only what is new.

## Conventions

- Every table is a path-based Delta table at `data/lake/<layer>/<table>/`. `data/` is already git-ignored.
- Code never spells a path. One registry module, `etl/tables.py`, maps each table name to its path, key, partition columns and schema.
- All times are UTC and stored with microsecond precision. The existing cohort Parquet files use nanoseconds, so cast when loading them.
- All windows are half-open, `[start, end)`, as in `ec-hw2/config.py`.
- Every build takes an `as_of` time. It limits stream events only: a build uses events with `meta_dt <= as_of`. Dump labels are limited by the `snapshot` argument of the label loads and the marts. The default `as_of` is the newest event over the three Silver stream tables. Each commit stores its `as_of`, and its `snapshot` where it has one, in the commit's user metadata.
- An `as_of` is always spelled one way: `YYYY-MM-DDTHH:MM:SS.ffffffZ`. Only this text is compared, stored and put into SQL.
- To reproduce the published EC HW2 numbers, build with `as_of = 2026-10-27T20:59:59.999999Z`. That keeps every event up to the end of capture hour 20 on Oct 27, the last hour in `data-v2`.
- Rules and constants stay in `ec-hw2/config.py`. Lake-only settings go in a new `etl/lake_config.py`.

## The four clocks

TruthLag is about when something became known, so every table says which clock each time column uses.

| Clock | Columns | What it records |
| --- | --- | --- |
| Event time | `rev_dt` in the stream, `event_timestamp` in the dump, `event_dt` in Gold | When the revision was saved. Whole seconds. |
| Publish time | `meta_dt`; in cohort tables `seen_ts`, `known_at`, `mw_reverted_at` | When EventStreams published the event: the earliest moment a subscriber could know it. Milliseconds. This is the stream's "known at" clock. |
| Snapshot time | `snapshot`, `snapshot_cutoff`, `snapshot_published_at` | Which dump a label came from, the time of its last revision, and when it was published. |
| Lake time | `loaded_at`, plus the version and timestamp of each Delta commit | When this lake recorded the row. It depends on when a job ran, unless the job replays history with `as_of`. |

The capture stores no receive time (`ingest/vps/capture.py` writes the payload unchanged), and the live cohort was replayed 1.2 to 4.2 days after publication. So publish time is the only per-event knowledge clock, and all published numbers use it.

## Bronze: what was received

| Table | One row per | Built from | Write pattern | Partition |
| --- | --- | --- | --- | --- |
| `bronze/page_change_events` | Captured line of `mediawiki.page_change.v1` | Raw `.ndjson.gz` files | Append only; each raw file loaded once | `event_date` |
| `bronze/revert_risk_events` | Captured line of `mediawiki.page_revert_risk_prediction_change.v1` | Same | Same | `event_date` |
| `bronze/tags_events` | Captured line of `mediawiki.revision-tags-change` | Same | Same | `event_date` |
| `bronze/history_slim` | Dump row of one revision, 12 text columns | Snapshot 2026-09: `data/history/enwiki_rev_all_2026-09_slim.parquet`. Later snapshots: `data/history_slim/<snapshot>/enwiki_rev_all_<month>_slim.parquet`. | Append once per snapshot and month | `snapshot` |
| `bronze/history_full` | Dump row of one cohort-window revision, 78 text columns. A landed copy: no later step reads it. | `data/history/enwiki_rev_ns0_2026-09-08_10.parquet` | Append once per snapshot and window | `snapshot` |
| `bronze/load_log` | Raw file load. Optional: add it only if re-runs are slow. | The loaders | Append | none |

Columns of the three event tables:

| Column | Type | Source |
| --- | --- | --- |
| `meta_id` | string | `meta.id` |
| `meta_dt` | timestamp | `meta.dt`, read from the payload, never from the folder name |
| `event_date` | date | Date of `meta_dt` |
| `stream` | string | `meta.stream` |
| `wiki_id` | string | `wiki_id`, or `database` in the tags stream |
| `kafka_topic`, `kafka_partition`, `kafka_offset` | string, int, long | `meta.topic`, `meta.partition`, `meta.offset`. Not a dedupe key: offsets are shared with other wikis. |
| `raw_json` | string | The captured line, unchanged |
| `source_file`, `source_line` | string, long | Path under `data/raw/` and line number |
| `capture_session` | string | From the part file name |
| `batch_id`, `loaded_at` | string, timestamp | Set by the loader |

Bronze rules:

- Duplicates stay. The capture can repeat events after a reconnect; Silver removes them.
- A loader skips files changed in the last 120 seconds (`config.OPEN_FILE_GRACE_S`). It keeps the complete lines of a gzip file with no end marker, as `parse_stream.read_lines` does. In the parsed span, 105 of 748 part files had no end marker.
- `bronze/load_log` is optional. The loader's source of truth is the event table itself: it reads the highest line already loaded for each source file and loads only later lines, so a file that grew gets only its new lines. A load log (path, size, lines loaded) only saves re-reading unchanged files. Track files, not folders: an old hour folder can receive a new file.
- The history tables add `snapshot`, `dump_month`, `source_file`, `source_row` and `loaded_at` to the dump's own text columns. `source_row` is the row's position in the source file. The loader reads the highest one already loaded per file and appends only later rows, so a load that stopped half way is finished by the next run. Nothing is cast in Bronze, and literal strings such as "NA" or "NULL" must stay strings. The existing 2026-09 Parquet copies turned them into nulls.
- Statistics are collected on the envelope columns only, not on `raw_json`.

## Silver: one clean row per thing

| Table | One row per | Key | Built from | Write pattern |
| --- | --- | --- | --- | --- |
| `silver/page_change` | Page-change event, all namespaces and kinds | `meta_id` | `bronze/page_change_events` | Insert-only MERGE, limited to the event dates in the batch |
| `silver/revert_risk` | Revision, earliest score kept | `rev_id` | `bronze/revert_risk_events` | MERGE; update only when the source `meta_dt` is earlier |
| `silver/tag_events` | Tag-change event | `meta_id` | `bronze/tags_events` | Insert-only MERGE |
| `silver/capture_gaps` | Hole longer than 120 s in one stream | `stream`, `gap_start` | The Bronze envelope columns. Silver lacks topic and partition for two of the streams. | Overwrite |
| `silver/history_slim` | Revision in one snapshot, typed | `snapshot`, `revision_id` | `bronze/history_slim` | Replace one snapshot and month |
| `silver/history_revisions` | History-cohort revision | `rev_id` | The two 2026-09 files in `data/history/` (the same files that Bronze loads), through the old history code | Rebuilt per snapshot; replaced only when rows changed |
| `silver/history_revert_links` | Reverted history-cohort revision | `reverted_rev_id` | Same | Same |
| `silver/live_revisions` | Live-cohort revision | `rev_id` | The three stream tables, through the old label code | Rebuilt as of a time; replaced only when rows changed |
| `silver/live_revert_links` | Reverted live-cohort revision, first covering exact revert | `reverted_rev_id` | Same | Same |
| `silver/live_revert_links_all` | Every (reverted, reverting) pair | `reverted_rev_id`, `reverting_rev_id` | Same | Same |
| `silver/late_reverts` | Earlier-month revision the dump calls unreverted and the stream shows reverted | `rev_id` | The 2026-09 slim file in `data/history/` and the stream tables, through the old code | Same |
| `silver/page_activity_hour` (stretch) | Page and hour, per source | `page_id`, `hour_start`, `source` | Silver events | Overwrite |

Silver rules:

- Columns are exactly those of the matching Parquet table in `ec-hw2/DATA_MODEL.md` (sections 2 and 3). The only added column is `event_date`, on `silver/page_change` and `silver/tag_events`. The cohort is the existing column `cohort`. The snapshot behind the history tables and `late_reverts` is stored in the commit metadata, not as a column. `silver/history_slim` is the one Silver table with `snapshot` and `dump_month` columns.
- The old code reads all-text Parquet files by path. It reads one snapshot and one month at a time. So the history cohort tables and `late_reverts` are built from the files in `data/history/`, not from the Bronze or Silver history tables. `bronze/history_slim`, `bronze/history_full` and `silver/history_slim` feed Gold only.
- The stream tables keep every captured date and namespace. The filter order of `parse_stream.parse_stream_dir` is kept: bad JSON, canary, not enwiki, no `meta.id` or `meta.dt`, repeated `meta.id`.
- Cohort tables keep the EC HW2 rules exactly, by calling the existing functions in `ec-hw2/ingest/` (see the plan). A cohort is a row of `gold/dim_cohort`: a source, a window and a follow-up.
- Labels for live revisions stay in the link tables, as in EC HW2. "Reverted" means a link with `within_followup` exists.

## Gold: the star schema and the measures

| Table | One row per | Key | Write pattern |
| --- | --- | --- | --- |
| `gold/dim_cohort` | Cohort: id, source, window, follow-up days | `cohort_id` | MERGE from config; changed rows only |
| `gold/dim_snapshot` | Dump snapshot: cutoff, published time, loaded time, row counts | `snapshot` | MERGE |
| `gold/dim_time` | Minute that occurs in the facts | `time_key` | MERGE; inserts new minutes |
| `gold/dim_user` | Editor, Type 1 | `user_key` | MERGE |
| `gold/dim_page` | Version of a page, SCD Type 2 | `page_key` | SCD2: the full version list is recomputed, then one MERGE on the key |
| `gold/fact_edit` | Revision | `wiki_db`, `rev_id` | MERGE, update only changed rows; Change Data Feed on |
| `gold/fact_revert_label` | Revision with a dump label | `wiki_db`, `rev_id` | MERGE per snapshot, update only when a label column changed; Change Data Feed on |
| `gold/mart_el_curve` | Cohort, label source, user kind and wait L | all four | Overwrite |
| `gold/mart_reconciliation` | Cohort, snapshot and match class | all three | Replaced per cohort and snapshot |
| `gold/recon_mismatch` | Revision where stream and dump disagree, or that the dump does not hold | `cohort_id`, `snapshot`, `rev_id` | Replaced per cohort and snapshot |
| `gold/mart_label_change` | Revision whose dump label changed between snapshots | `wiki_db`, `rev_id`, `commit_version` | Insert-only MERGE, built from the change feed |
| `gold/mart_el_by_burst` | Cohort, label source, burst group and wait L | all four | Overwrite |

Five columns of the draft are left out: `fact_edit.ingested_at`, `dim_user.is_anonymous`, `dim_user.groups`, `fact_revert_label.snapshot` and `fact_revert_label.is_censored`. The capture stores no receive time, the two editor columns were not needed, and the last two are replaced by `first_reverted_snapshot`, `last_changed_snapshot` and the censoring rule below. Otherwise the columns of the dimension and fact tables follow `docs/schema_and_warehouse.md`:

- **`fact_edit`:** `wiki_db, rev_id, parent_rev_id, page_key, user_key, time_key, event_dt, seen_dt, bytes_diff, is_bot, live_revert_flag, live_revert_dt, live_known_dt, revert_risk_score, page_edits_prev_1h, cohort_id, user_kind`. `seen_dt` is the edit event's `meta_dt`. `live_known_dt` is the revert event's `meta_dt`.
- **`dim_page`:** `page_key, wiki_db, page_id, title, namespace, is_redirect, is_deleted, valid_from, valid_to, is_current`. A new version starts on a move, delete, restore or redirect change. Facts join as of `event_dt`. The first version of a page starts at the sentinel 1900-01-01, so earlier facts still join. The key is built from the page id and the start of the version, so a rebuild gives the same keys. The redirect flag is a stretch item: the parsed tables do not hold it. The observations behind the versions come from the stream events and from the history-cohort rows: the title at edit time, and the dump's current title at the snapshot's cutoff.
- **`dim_user`:** `user_key, user_id, user_text, user_kind, is_bot, is_temporary`. `user_key` is `config.editor_key`; editors without a key use the member `unknown`. The table is Type 1 and holds the editor's latest kind, so marts take the kind at edit time from the revision. Pseudonyms are not stored in Gold. The evidence notebook makes them in Python, with the function in `ec-hw2/ingest/build_documents.py`, for the rows it shows; bots keep their names.
- **`fact_revert_label`:** `wiki_db, rev_id, is_identity_reverted, reverting_rev_id, seconds_to_identity_revert, label_dt, first_reverted_snapshot, last_changed_snapshot`. `label_dt` is `event_dt` plus the seconds to revert.
- **Censoring.** The tested mart SQL has no censoring rule, so an E(L) mart is valid only when follow-up is complete. For the stream series that means `as_of >= config.LIVE_FINAL_AFTER` (2026-10-27 00:05 UTC). For the dump series it means that the snapshot's cutoff is at least 4 days after the end of the cohort window; Phase 5 of the plan checks this. For an earlier `as_of`, no E(L) mart is written. Nothing about censoring is stored per row.

Measure definitions for `mart_el_curve` (the published EC HW2 definition, so the numbers can be compared):

- Horizon 4 days. An eventual revert has `0 <= T_s <= 345,600`, self-reverts included.
- Waits are the 9 points of `config.WAIT_POINTS_S`: 0, 1 min, 5 min, 15 min, 1 h, 6 h, 1 d, 2 d, 4 d.
- A revert is known by wait L when `T_s + coalesce(K_s, 0) <= L`, inclusive. `K_s` is the stream delay of the reverting event and is null for dump labels.
- `E(L) = 1 - known / eventual`. Groups with fewer than 100 eventual reverts are kept and flagged (`small_group`). This is the one difference from the published code, which drops them. Compare with the published result file on the rows that are not flagged.

## Which Delta feature does which job

| Need | Delta feature | Where |
| --- | --- | --- |
| Raw events are never altered | Append-only table property | Bronze |
| A re-run adds nothing | The loader reads from the table which lines are already loaded | Bronze |
| One row per event | Insert-only MERGE on the event id | Silver stream tables |
| A page's title and namespace at edit time | SCD Type 2 MERGE | `gold/dim_page` |
| Labels that change after the fact | MERGE that updates only changed rows, with Change Data Feed | `gold/fact_edit`, `gold/fact_revert_label` |
| "What did we know at time T?" | Time travel by version over commits built with `as_of` | Silver cohort tables and Gold |
| Who changed what, and when | Table history and commit user metadata | Every table |
| Fast per-page and per-day reads | Date partitions in Bronze; Z-order by page in Gold | Bronze, Gold |

## Changes on Nov 13, after the prototype runs

Draft v1 was edited once, after the two prototypes ran (research pages R6 and R7). What changed:

- The parity `as_of` ends at 20:59:59.999999, so that events in the last second of capture hour 20 are kept.
- The default `as_of` stays the newest event over the three Silver stream tables, as in the prototype. An earlier edit of this page had changed it to the newest page-change event; a review run on the fixtures showed that this changes 1 row of `late_reverts`.
- After the review of Nov 13: `as_of` limits stream events only, and dump labels are limited by `snapshot`. The Silver cohort keys are those of the prototype. New slim files go to `data/history_slim/`. The Bronze history tables got `source_row`. The censoring rule says when an E(L) mart is valid. `gold/mart_el_by_burst` moved from stretch into Phase 4.
- The Bronze table for tag changes is named `bronze/tags_events`, as in the prototype.
- The load log became optional. The loader reads from the event table which lines are already loaded.
- Capture gaps are computed from the Bronze envelope columns.
- The Silver cohort tables are rebuilt as of a time and replaced when their rows changed. They are no longer merged row by row.
- `dim_page` is built by recomputing the full list of versions, with a key that a rebuild reproduces.
- `fact_edit` gained `user_kind`, the editor's kind at edit time. `dim_user` is Type 1 and holds the latest kind.
