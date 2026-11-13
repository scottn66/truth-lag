# R1 — Existing pandas pipeline: porting inventory

> **Research report, not yet reviewed.** Output of the research agent `port_inventory` in a cloud Claude Code session on Nov 13, 2026, as returned. Evidence labels: RAN = executed in that session on made-up data; READ = read at the cited file and line; DERIVED = arithmetic on values that were read; UNVERIFIED = not checked. Paths that start with /tmp/claude-0/ or /home/user/ are on that session's machine and cannot be opened from elsewhere. Repository state read: scottn66/truth-lag at 8e28012.

## Summary

Porting inventory for the pandas pipeline (parse_stream, parse_history, label_live, late_reverts, history_columns, config). Main findings. (1) capture.py does NOT record when it received an event: it writes the SSE payload unchanged (capture.py:114) and partitions by the event's own meta.dt (capture.py:45). The units also started about 2026-10-24 04:52 UTC with a replay from 2026-10-19 / 2026-10-17, so the only usable 'when did we know' clock in the data is meta.dt (publish time), which is what seen_ts, known_at, mw_reverted_at and first_signal_at already use. (2) Almost all rules live in pure functions on pandas frames; file I/O sits in run() and a few small readers and writers. RAN here on a byte-identical scratch copy: the 30 ingest tests pass (Python 3.12.3, pandas 2.3.3, pyarrow 26.0.1); the functions import from outside ec-hw2 when ec-hw2 is on sys.path (repo root alone fails: 'ImportError cannot import name parse_stream from ingest (unknown location)'); label_live gives identical tables with plain, numpy_nullable or Arrow-mapped dtypes. (3) Incremental needs: unbounded per-page lookback for the range cover, 1 h for page_edits_prev_1h, 60 s lookahead for save-time tags, 600 s for the late-tag link, 4-day and 20-day follow-up, plus conditional MERGE rules for 'earliest per rev_id' and 'first exact revert'. (4) 44 golden numbers with expressions (row counts, known-by counts and E(L) at 9 waits for both cohorts), volumes, 34 gotchas with file:line, fixture reuse recipe and repo conventions are in the sections. Not in the repo: per-day row counts, runtimes of 3 scripts, rows of revert_risk.parquet and live_revert_links_all.parquet, uncompressed raw size (see open_questions).

## Functions

Evidence labels used in every section: READ = read in the repo (file:line). RAN = executed here, in my scratch folder, on a byte-identical copy of the repo files (venv: Python 3.12.3, pandas 2.3.3, pyarrow 26.0.1, numpy 2.5.4, pytest 9.2.0). DERIVED = arithmetic on READ values. UNVERIFIED = not checked.

Short file names used in all sections:
- PS = /home/user/truth-lag/ec-hw2/ingest/parse_stream.py
- PH = /home/user/truth-lag/ec-hw2/ingest/parse_history.py
- LL = /home/user/truth-lag/ec-hw2/ingest/label_live.py
- LR = /home/user/truth-lag/ec-hw2/ingest/late_reverts.py
- HC = /home/user/truth-lag/ec-hw2/ingest/history_columns.py
- CFG = /home/user/truth-lag/ec-hw2/config.py
- CAP = /home/user/truth-lag/ingest/vps/capture.py
- FH = /home/user/truth-lag/ingest/vps/filter_history.py
- DM = /home/user/truth-lag/ec-hw2/DATA_MODEL.md
- FACTS = /home/user/truth-lag/ec-hw2/report/FACTS.md
- TS = /home/user/truth-lag/ec-hw2/tests/test_stream.py
- TH = /home/user/truth-lag/ec-hw2/tests/test_history.py

General shape (READ): each script = pure functions on pandas / numpy / pyarrow objects, one `run(...)` that does all file reads and writes, and `main()`. No script is incremental: every run reads all inputs and rewrites all outputs. Every `run` takes its folders as arguments, so the tests call it on temp folders (TS:252-258, TH:307).

### 1. parse_stream.py (PS, 416 lines)
Module objects: `PAGE_CHANGE_SCHEMA` (31 fields, PS:58-70), `REVERT_RISK_SCHEMA` (10, PS:72-76), `REVERT_RISK_COLUMNS` (the 7 written, PS:77-78), `TAG_SCHEMA` (13, PS:79-84), `TAG_COLUMNS` (the 11 written, PS:85-86), `STREAMS` = stream name -> (table name, schema, flatten function) (PS:194-198), `BATCH_ROWS = 200_000` (PS:52), `GAP_MIN_S` (PS:51), `GZIP_ERRORS` (PS:53).

| Function (line) | Pure or I/O | Input -> output |
|---|---|---|
| `list_part_files(stream_dir: Path, now: float, include_open: bool)` (92) | I/O: glob + stat | folder -> (files to read, files skipped as open) |
| `read_lines(path: Path, problems: list)` (104) | I/O: gzip read, generator | one part file -> its lines (bytes). On EOFError / zlib.error / BadGzipFile it keeps the lines already read and appends {file, error, lines_kept} to `problems` |
| `flat_page_change(ev: dict) -> dict` (130) | pure | one event -> one row dict, 31 keys |
| `flat_revert_risk(ev: dict) -> dict` (158) | pure | one event -> row dict, 10 keys |
| `flat_tags(ev: dict) -> dict` (174) | pure | one event -> row dict, 13 keys; computes added, removed, mw_reverted_added |
| `class TableBuilder(schema, batch_rows=BATCH_ROWS)`: `add(row)`, `flush()`, `table()` (201) | pure, in memory | row dicts -> `pa.Table`; ISO text is cast to timestamp[us, UTC] (PS:223-225) |
| `parse_stream_dir(stream: str, stream_dir: Path, now: float, include_open: bool) -> tuple[pa.Table, dict]` (238) | I/O read | all part files of one stream -> (table after filters and meta.id dedupe, stats) |
| `find_gaps(stream: str, df, min_gap_s: float = GAP_MIN_S) -> DataFrame` (279) | pure | frame with meta_dt, topic, partition -> gap rows |
| `dedupe_revert_risk(df) -> tuple[DataFrame, int]` (303) | pure | keeps the earliest meta_dt per rev_id |
| `iso(ts)` (310), `rows_per_day(s)` (316) | pure | summary helpers |
| `write_parquet(table, path)` (322), `write_json(obj, path)` (328) | I/O write | name.tmp then os.replace; Parquet zstd |
| `run(raw_dir: Path, out_dir: Path, include_open: bool = False, now: float = None) -> dict` (334) | I/O | orchestrates, returns the summary |
| `main(argv=None)` (401) | CLI | |

Flow of run (PS:334-398): for each stream in `config.STREAM_DIRS` -> `parse_stream_dir` (list files, read lines, json.loads, drop canary, drop non-enwiki, drop events without meta.id or meta.dt, drop repeated meta.id, flatten, build the Arrow table) -> revert risk only: `dedupe_revert_risk`; tags only: select `TAG_COLUMNS` -> `write_parquet` -> `find_gaps` -> stats (rows, first and last meta_dt, rows_per_day, kinds, revert_events, seconds). Then capture_gaps.csv, then _SUCCESS_parsed.json.
CLI flags (PS:402-407): `--include-open`; hidden `--raw-dir` (default config.RAW_STREAM_DIR) and `--out-dir` (default config.PARSED_DIR).
Memory: the whole stream is in memory. One Arrow table per stream, a Python set of every meta.id of that stream (PS:246), then pandas copies (PS:347-349). Streams run one after another and are freed (PS:357, 384).

### 2. parse_history.py (PH, 669 lines)
Module objects: `REVISION_COLUMNS` (39, PH:88-97), `LINK_COLUMNS` (22, PH:98-103), `T_BUCKETS` (PH:79-85), `SLIM_TIME_COLS`, `SLIM_REVERTER_COLS` (PH:73-75), output names (PH:61-65).

| Function (line) | Pure or I/O | Input -> output |
|---|---|---|
| `filter_cohort(df) -> (df, drops)` (161) | pure | cast cohort frame -> rows with entity revision, type create, ts in HISTORY_WINDOW, page_namespace_historical == 0 |
| `comment_null_prefix(comment, user_name) -> Series` (182) | pure | the null-action prefix a comment starts with, after removing a leading '<user name> ' |
| `null_revision_masks(df, full) -> (rule_a, rule_b, rule_b_prefix)` (203) | pure | needs the FULL cast cohort file to look up the parent sha1 |
| `add_user_fields(df) -> df` (227) | pure | adds user_kind, user_key, is_bot, is_temp, is_anon |
| `add_labels(df) -> df` (246) | pure | adds reverted_any, secs_to_revert, reverting_rev_id, reverted |
| `read_slim_reverters(slim_path: Path, rev_ids) -> df` (259) | I/O: pq.read_table with a filter on string ids | cast slim rows of the reverting revisions |
| `join_reverters(df, slim_rev) -> (df, checks)` (270) | pure | adds reverter_name / kind / key, reverted_by_other |
| `count_prev_window(page, ts_s, slim_page, slim_ts_s, window_s=PREV_WINDOW_S) -> ndarray` (322) | pure numpy | count of slim rows on the page in [ts - window, ts) |
| `read_slim_page_times(slim_path) -> df` (350) | I/O | page_id + event_timestamp of every slim row |
| `build_revisions(df, prev_1h) -> df` (358) | pure | the 39 output columns |
| `build_revert_links(rev) -> df` (405) | pure | one row per revision with reverted_any |
| `t_bucket(t)` (458), `summarize(rev, links, rows, join_checks) -> dict` (466), `print_summary(s)` (549) | pure / print | summary |
| `run(cohort_path: Path, slim_path: Path, out_dir: Path, quiet: bool = False) -> dict` (591) | I/O | orchestrates |
| `main()` (659) | CLI | |

Flow of run (PH:591-656): read the cohort Parquet -> `cast_history_frame` -> stop if revision_id repeats -> `filter_cohort` -> `null_revision_masks` -> drop rule (a) or (b) -> `add_user_fields` -> `add_labels` -> `read_slim_reverters` -> `join_reverters` -> `read_slim_page_times` -> stop if any time has parts of a second -> `count_prev_window` -> `build_revisions` -> `build_revert_links` -> stop if rev_id repeats -> `summarize` -> write history_revisions.parquet, history_revert_links.parquet, history_summary.json, _SUCCESS_history.json.
CLI flags (PH:660-664): `--cohort`, `--slim`, `--out-dir`.
Memory: whole cohort file (300,564 rows x 78 strings) plus a cast copy, and 2 slim columns for all 5,266,843 rows. Docstring: about 10 seconds and about 2.5 GB (PH:36).

### 3. label_live.py (LL, 705 lines)
Module objects: `EDIT_KINDS = ('create', 'edit')` (LL:49), `ID_BITS = 32` (LL:51), `LIVE_REVISIONS_SCHEMA` (31 fields, LL:58-70), `LINKS_SCHEMA` (22, LL:71-80), `LINKS_ALL_SCHEMA` (25, LL:84-85), `BIG_ID` (LL:156). Times in these schemas are timestamp[ns, UTC] (LL:57).

| Function (line) | Pure or I/O | Input -> output |
|---|---|---|
| `add_user_columns(df) -> df` (103) | pure | adds user_kind, user_key from user_name, is_bot, is_temp, user_id |
| `secs`, `micros`, `seconds_between`, `pair_key`, `ids`, `to_int` (127-167) | pure | time and id helpers |
| `load_page_change(path) -> df` (173) | I/O | pd.read_parquet(dtype_backend='numpy_nullable') |
| `edit_events(pc) -> (ed, n_dup, examples)` (178) | pure | all captured edits and creates, all namespaces, one row per rev_id (earliest meta_dt) |
| `revert_events(pc) -> (E, n_dup)` (191) | pure | every event with a revert, all namespaces, one row per rev_id |
| `check_newest_parent(E) -> dict` (199) | pure | count of revert_newest_id != parent_id |
| `range_cover(R, E) -> DataFrame[r_row, e_row, range_size]` (210) | pure | every (revision, revert) covering pair. R needs page_id, rev_id, rev_dt |
| `range_complete_flags(E, captured) -> Series` (303) | pure | does the range of E start inside the capture |
| `save_time_tags(revs, tags, window_s=config.SAVE_TIME_TAG_WINDOW_S) -> Series` (326) | pure | rev_id -> sorted tag list |
| `first_mw_reverted(tags) -> Series` (340) | pure | rev_id -> meta_dt of the first mw-reverted addition |
| `count_in_window(ev_page, ev_t, q_page, q_lo, q_hi) -> ndarray` (346) | pure numpy | events on the page with q_lo <= t < q_hi |
| `build_cohort(ed, n_dup_rev) -> (c, drops)` (369) | pure | ns 0, rev_dt in LIVE_WINDOW, not a null revision |
| `live_revisions(c, ed, tags, risk, newest_meta_dt) -> df` (384) | pure | the 31 output columns |
| `build_links_all(R, E, pairs, cohort_ids, mw_ids) -> df` (434) | pure | one row per covering pair |
| `first_exact_links(links_all) -> df` (474) | pure | per cohort revision, the first exact cover by (reverting_ts, reverting_rev_id) |
| `summarize(...)` (501), `print_summary(s)` (670) | pure / print | summary |
| `write_parquet(df, schema, path)` (596), `write_json` (602) | I/O write | .tmp then os.replace |
| `run(parsed_dir=config.PARSED_DIR, tables_dir=config.TABLES_DIR) -> dict` (608) | I/O | orchestrates |
| `main()` (699) | no CLI flags | |

Flow of run (LL:608-667): require _SUCCESS_parsed.json -> load page_change (all columns), tag_events (4 columns), revert_risk (2 columns) -> newest = max meta_dt -> `edit_events` + `add_user_columns` -> `revert_events` + `add_user_columns` -> `build_cohort` -> `live_revisions` -> `check_newest_parent` -> `range_cover(ed, E)` -> `range_complete_flags` -> `build_links_all` -> `first_exact_links` -> write 3 Parquet files -> `summarize` -> live_summary.json -> _SUCCESS_live.json.
Memory: all of page_change.parquet (1,231,427 rows x 31 columns), 4 columns of tag_events (1,603,253 rows, one list column) and 2 columns of revert_risk are in pandas at once.

### 4. late_reverts.py (LR, 326 lines)
Module objects: `SLIM_COLUMNS` (LR:54-55), `LATE_SCHEMA` (13 fields, LR:57-62). It imports `BIG_ID, ids, load_page_change, range_cover, revert_events` from label_live (LR:50).

| Function (line) | Pure or I/O | Input -> output |
|---|---|---|
| `iso(ts)` (65) | pure | |
| `load_september(slim_path, page_ids, rev_ids) -> (df, stats)` (74) | I/O | slim rows on the candidate pages or with the candidate rev_ids, not reverted in the dump, cast |
| `history_cohort_ids(tables_dir, sept) -> (bool array, method)` (100) | I/O (optional read of history_revisions.parquet, else a window fallback) | |
| `cover_pairs(sept, E) -> df` (116) | pure | every (September revision, October revert) pair, via `range_cover` |
| `link_tags(tags, P, window_s=config.LATE_TAG_LINK_WINDOW_S) -> df` (131) | pure | adds `linked` to each mw-reverted addition |
| `late_rows(sept, P, T, restored_ids, in_cohort) -> df` (145) | pure | one row per September rev_id with a stream signal |
| `summarize(rows, P, T, E, titles, sept_stats, cohort_method, capture_starts) -> dict` (188) | pure | |
| `run(parsed_dir=config.PARSED_DIR, tables_dir=config.TABLES_DIR, history_dir=config.HISTORY_DIR) -> dict` (257) | I/O | orchestrates |
| `main()` (320) | no CLI flags | |

Flow of run (LR:257-297): require _SUCCESS_parsed.json and _SUCCESS_live.json -> load page_change -> `revert_events` -> page titles -> mw-reverted additions from tag_events -> `load_september` -> `cover_pairs` -> `link_tags` -> restored_ids from live_revert_links_all -> `history_cohort_ids` -> `late_rows` -> write late_reverts.parquet, late_reverts_summary.json, _SUCCESS_late_reverts.json.
Memory: 5 slim columns for all 5,266,843 rows as Arrow strings (LR:79), all of page_change (LR:263), 5 columns of tag_events (LR:269-270).

### 5. Helpers that the four scripts import
- HC: `cast_history_frame(df) -> df` (HC:99), `split_list(value) -> list[str]` (HC:114), `sha1_base36_to_hex(s)` (HC:131). All pure.
- CFG: `user_kind(name, bot_flag, is_temp=None) -> str` (CFG:145), `editor_key(kind, user_id, name)` (CFG:159), `utc(s) -> datetime` (CFG:279) are pure; `ensure_dirs()` (CFG:274) makes folders and is only called on request.

## Raw contract

READ unless marked. The raw data is not in this container. The field list is what the parser reads and what the test fixtures contain; I did not see a real raw event.

**Layout.** `data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-<session>-<n>.ndjson.gz` (CFG:51-57; `RAW_GLOB = 'dt=*/hour=*/part-*.ndjson.gz'`). One JSON event per line, exactly the SSE `data:` payload (CAP:104, 114). Streams (CFG:61-64): `mediawiki.page_change.v1`, `mediawiki.page_revert_risk_prediction_change.v1`, `mediawiki.revision-tags-change`.

**What the partition folders mean.** `<stream>` = `meta.stream` of the event (CAP:113; 'unknown' if missing). `dt` = `meta.dt[:10]` and `hour` = `meta.dt[11:13]` (CAP:45, 50): the UTC date and hour when the stream published the event, taken as text slices. It is not the arrival time. `<session>` = start time of the capture process, `YYYYMMDDTHHMMSS-<6 hex>` (CAP:23). `<n>` counts how many times this session opened a writer for that (stream, dt, hour) (CAP:49); it grows when the 48-writer LRU closes and reopens a partition (CAP:15, 55-56). So one hour can hold several files from several sessions, and an old hour can get a new file later (restart with resume, or replay).

**What the capture already filtered (CAP:106-112).** Bad JSON is skipped. An event is kept only if `meta.domain != 'canary'` and `(wiki_id or database) == 'enwiki'` and `meta.dt` is set.

**Parser filters, in this order (PS:250-270).** Bad JSON -> counter `bad_json`. Canary rule: `meta.domain == 'canary'` -> `canary`. `(ev.wiki_id or ev.database) != 'enwiki'` -> `other_wiki` (PS:190-191; the tags stream has `database`, not `wiki_id`). Missing `meta.id` or `meta.dt` -> `no_meta`. `meta.id` already seen in this stream -> `duplicate_meta_id`.

**Dedupe key.** `meta.id`, per stream; the first occurrence in sorted path order wins (PS:95, 246, 262-269). Kafka topic, partition and offset are not used for the dedupe or the gaps (PS:279-285). Second-level keys: revert risk keeps the earliest `meta_dt` per `rev_id` (PS:303-307); label_live keeps the earliest `meta_dt` per `rev_id` for edits (LL:178-188) and for revert events (LL:191-196). Real data: 3 repeated meta.id in page_change, 0 in the other two streams; 0 repeated rev_id among edits (notebook /home/user/truth-lag/ec-hw2/notebooks/01_data.ipynb, outputs of code cells 7 and 11).

**Open-file rule.** Skip a part file when `now - mtime < config.OPEN_FILE_GRACE_S` (120 s), unless `--include-open` (PS:92-101, CFG:58). **Cut-short rule.** A gzip file without its end marker raises EOFError / zlib.error / BadGzipFile at the end; every complete line read before is kept and the file is listed in `cut_short_files` (PS:104-120). RAN: `test_gzip_without_end_marker_keeps_flushed_lines` and `test_truncated_part_file_keeps_complete_lines` pass; the kept lines are a clean prefix of the file. The capture sync-flushes all open writers every 500 received events (CAP:14, 61-63, 119-120).

**page_change: JSON path -> column (Arrow type)** (PS:130-155; schema PS:58-70). All 31 columns are written; all namespaces and all kinds are kept.

| JSON path | Column | Type |
|---|---|---|
| meta.id | meta_id | string |
| meta.dt | meta_dt | timestamp[us, UTC] |
| meta.topic | topic | string |
| meta.partition | partition | int32 |
| meta.offset | offset | int64 |
| wiki_id | wiki_id | string |
| page_change_kind | kind | string |
| page.page_id | page_id | int64 |
| page.page_title | page_title | string |
| page.namespace_id | ns | int32 |
| revision.rev_id | rev_id | int64 |
| revision.rev_parent_id | parent_id | int64 |
| revision.rev_dt | rev_dt | timestamp[us, UTC] |
| revision.rev_size | rev_size | int64 |
| revision.rev_sha1 | sha1 | string (base 36) |
| revision.comment | comment | string |
| prior_state.revision.rev_id | prior_rev_id | int64 |
| prior_state.revision.rev_dt | prior_rev_dt | timestamp[us, UTC] |
| prior_state.revision.rev_size | prior_rev_size | int64 |
| prior_state.revision.rev_sha1 | prior_sha1 | string (base 36) |
| performer.user_id | user_id | int64 |
| performer.user_text | user_name | string |
| performer.is_bot | is_bot | bool |
| performer.is_temp | is_temp | bool |
| performer.edit_count | edit_count | int64 |
| revision.revert.method | revert_method | string |
| revision.revert.is_exact | revert_is_exact | bool |
| revision.revert.rev_original_id | revert_original_id | int64 |
| revision.revert.rev_original_dt | revert_original_dt | timestamp[us, UTC] |
| revision.revert.rev_reverted_oldest_id | revert_oldest_id | int64 |
| revision.revert.rev_reverted_newest_id | revert_newest_id | int64 |

**revert risk** (PS:158-171; schema PS:72-78). Written: the 7 `REVERT_RISK_COLUMNS`, one row per rev_id.

| JSON path | Column | Type |
|---|---|---|
| meta.id, meta.topic, meta.partition | meta_id, topic, partition (used, not written) | string, string, int32 |
| revision.rev_id | rev_id | int64 |
| page.page_id | page_id | int64 |
| meta.dt | meta_dt | timestamp[us, UTC] |
| revision.rev_dt | rev_dt | timestamp[us, UTC] |
| predicted_classification.probabilities.true | prob_true | float64 |
| predicted_classification.model_name | model_name | string |
| predicted_classification.model_version | model_version | string (via str) |

**tags-change** (PS:174-187; schema PS:79-86). Written: the 11 `TAG_COLUMNS`.

| JSON path | Column | Type |
|---|---|---|
| meta.id | meta_id | string |
| meta.dt | meta_dt | timestamp[us, UTC] |
| meta.topic, meta.partition | topic, partition (used, not written) | string, int32 |
| rev_id | rev_id | int64 |
| page_id | page_id | int64 |
| page_namespace | ns | int32 |
| rev_timestamp | rev_timestamp | timestamp[us, UTC] |
| tags | tags | list of string, sorted, distinct |
| prior_state.tags | prior_tags | list of string, sorted, distinct |
| computed: tags minus prior_tags | added | list of string |
| computed: prior_tags minus tags | removed | list of string |
| computed: 'mw-reverted' in added | mw_reverted_added | bool |

Fields in the fixtures that the parser does not read (they are lost unless Bronze keeps the raw JSON): top-level `dt`, `changelog_kind`, `$schema`, `meta.stream`, `page.is_redirect`, `page.namespace_is_content`, `revision.is_minor_edit`, `performer.groups`, the tags event's `page_title` and `rev_sha1`, the risk event's `predictions` (TS:46-104). Real events may hold more fields: UNVERIFIED.

**History.**
- The 78 names: `COLUMNS` at HC:19-46 (the same list as `COLS` at FH:6-22). Types: `INT_COLUMNS` HC:48-55 (18 names), `BOOL_COLUMNS` HC:56-66 (23), `TIME_COLUMNS` HC:67-72 (10), `LIST_COLUMNS` HC:74-79 (14; kept as comma text, split with `split_list`), the other 13 are strings. Time text format `'%Y-%m-%d %H:%M:%S.%f'` (HC:80). `cast_history_frame` (HC:99-111) casts whatever columns the frame has. An empty string becomes null; a bad int, bool or time raises.
- Columns the pipeline uses. Cohort file, 24 of 78: wiki_db, event_entity, event_type, event_timestamp, event_comment, event_user_id, event_user_text_historical, event_user_is_bot_by, event_user_is_temporary, event_user_revision_count, page_id, page_title_historical, page_title, page_namespace_historical, revision_id, revision_parent_id, revision_text_bytes, revision_text_bytes_diff, revision_text_sha1, revision_is_identity_reverted, revision_first_identity_reverting_revision_id, revision_seconds_to_identity_revert, revision_is_identity_revert, revision_tags (PH:166-178, 209-221, 228-231, 248-252, 360-392). Slim file, 8 of 12: revision_id, page_id, event_timestamp, event_user_id, event_user_text_historical, event_user_is_bot_by (PH:73-75), revision_is_identity_reverted, page_namespace (LR:54-55). No script reads the slim columns revision_is_identity_revert, revision_first_identity_reverting_revision_id, revision_seconds_to_identity_revert, event_user_text.
- What the VPS filter keeps (FH). It streams the bz2 dump. A line that does not split into exactly 78 tab fields is counted as bad and dropped (FH:37-39; 0 bad rows). It keeps only `event_entity == 'revision'` (FH:40-41; it does not test event_type). Slim file: 12 columns of every such row (FH:24-27, 42). Cohort file: all 78 columns when `page_namespace` (column 33, the CURRENT namespace) is '0' and '2026-09-08' <= event_timestamp[:10] < '2026-09-11' (FH:43-45). Both TSV files are then written to Parquet with every column typed string and `strings_can_be_null=True` (FH:58-60); the config note says this turned literal strings such as 'NA', 'NULL', 'nan' into null (CFG:83-87). Counts: 6,369,430 rows read, 300,564 cohort rows, 5,266,843 slim rows, 154 s (/home/user/truth-lag/ingest/vps/filter_stats.json).

## Clocks

**Does capture.py record when it RECEIVED an event? No.** READ: the whole receive loop is CAP:95-116. The payload is parsed only to filter it (CAP:107-112) and is then written unchanged: `writers.get(stream, meta['dt']).write((payload + '\n').encode())` (CAP:114). No field is added. The partition folder comes from the event's own `meta.dt` (CAP:45: `key = (stream, dt[:10], dt[11:13])`), not from the wall clock. The SSE `id:` line is read (CAP:97-98) but only kept as `last_event_id` in the state file (CAP:117-118); it is not in the raw files.

The wall clock is read in three places, none of them per event in the data:
1. CAP:23: `SESSION` = start time of the capture process (UTC). It is part of every file name (CAP:52). It is a lower bound of the receive time of every line in that file.
2. CAP:122: `updated` in `state/<conn>.json`, overwritten every 500 events. VPS only.
3. CAP:19-20, 124-125: the log time of the line `seen=... kept=... last_dt=...`, once per 10,000 events. VPS only. This is the only place that pairs a wall-clock time with a meta.dt.
A further proxy is the file mtime (last write of the capture; an upper bound). rsync -a should keep it on the Mac copy: UNVERIFIED.

**A receive clock would not fit the published cohort anyway.** READ: the units ask for `since=2026-10-19T23:00:00Z` (a) and `since=2026-10-17T00:00:00Z` (b) (/home/user/truth-lag/ingest/vps/truthlag-capture-a.service, truthlag-capture-b.service; CFG:67-68) but started about 2026-10-24 04:52 UTC (/home/user/truth-lag/ec-hw2/ingest/README.md:24-25; /home/user/truth-lag/ec-hw2/PROGRESS.md:246-247). So every event of the live window (2026-10-20 to 2026-10-22) was received 1.2 to 4.2 days after it was published (DERIVED). The existing pipeline therefore uses `meta.dt` as the 'when it became known' clock everywhere (seen_ts, known_at, mw_reverted_at, first_signal_at, page_hour).

The older collector /home/user/truth-lag/ingest/collect_eventstreams.py does stamp `_ingested_at` (line 53) and partitions by arrival hour (lines 16-19, 52-55). It was not used for the data (/home/user/truth-lag/ec-hw2/ingest/README.md:41-44).

**Clocks in the raw events** (READ)

| Field | Streams | Moment it records | Precision |
|---|---|---|---|
| meta.dt | all 3 | the stream published the event (the repo's wording: CFG:53; ingest README:35). Risk stream: the score event was published. Tags stream: the tag change was published. The exact Wikimedia meaning (publish vs ingest by EventGate) is UNVERIFIED | milliseconds, for example 2026-10-20T00:00:00.973Z (PS:224) |
| revision.rev_dt | page_change, revert risk | the revision was saved | whole seconds (LL:230-231 relies on it) |
| prior_state.revision.rev_dt | page_change | the parent revision was saved | whole seconds |
| revision.revert.rev_original_dt | page_change, reverts only | save time of the revision whose content the revert restored | whole seconds |
| rev_timestamp | tags | the tagged revision was saved | whole seconds |
| dt (top level) | page_change | event time; equal to rev_dt in the fixtures (TS:63); the parser does not read it | - |

**Clocks in each table** (READ)

| Table | Column | Moment |
|---|---|---|
| page_change.parquet | meta_dt, rev_dt, prior_rev_dt, revert_original_dt | as above, timestamp[us, UTC] |
| revert_risk.parquet | meta_dt, rev_dt | publish time of the EARLIEST score event; revision saved |
| tag_events.parquet | meta_dt, rev_timestamp | tag change published; revision saved |
| capture_gaps.csv | gap_start, gap_end | meta.dt of the last event before and the first event after a hole (ISO text) |
| history_revisions | ts | dump event_timestamp = revision saved, whole seconds (PH:371) |
| history_revisions | seen_ts, mw_reverted_at | always null (PH:372, 381) |
| history_revisions | followup_s | HISTORY_DUMP_LAST_REVISION (2026-10-01T01:38:27Z, CFG:111) minus ts (PH:396-397) |
| live_revisions | ts | revision.rev_dt (LL:397) |
| live_revisions | seen_ts | meta.dt of the edit event: the edit became visible on the stream (LL:398) |
| live_revisions | mw_reverted_at | meta.dt of the first tags event that added mw-reverted: the tag label became known (LL:340-343, 408-409) |
| live_revisions | followup_s | newest page_change meta_dt of that run minus ts (LL:427, 618). It changes on every run |
| history_revert_links | reverted_ts, reverting_ts | ts; ts + secs_to_revert (computed, PH:417). known_at and K_s are null (PH:422-423) |
| live_revert_links, live_revert_links_all | reverted_ts, reverting_ts | R.rev_dt and E.rev_dt: the two revisions were saved (LL:442-446) |
| live_revert_links, live_revert_links_all | known_at | E.meta_dt: the reverting event was published = the stream label became known (LL:450) |
| live_revert_links, live_revert_links_all | T_s, K_s | T_s = floor(reverting_ts - reverted_ts), int (LL:457). K_s = known_at - reverting_ts, float seconds (LL:458) |
| late_reverts | rev_ts | dump event_timestamp of the September revision |
| late_reverts | first_signal_at | min(meta_dt of the first covering revert, meta_dt of the first mw-reverted addition) (LR:155-164) |
| late_reverts | age_days | reverting rev_dt minus rev_ts; for tag-only rows the tag meta_dt (an upper bound) (LR:172-176) |
| _SUCCESS_*.json and summaries | created_at, finished_at_utc, made_at_utc | wall clock of the script run (PS:339, PH:469, 646, LL:658, LR:292). _SUCCESS_live.json also has newest_meta_dt and live_final_after |
| Mongo page_hour | hour, built_at | hour of meta.dt (events) or of known_at (covered revisions), so each count sits in the hour it became known (/home/user/truth-lag/ec-hw2/speed_layer.py:4-10, 109-115); built_at = wall clock of the build |

**File-level clocks.** Partition folder = meta.dt date and hour. File name = session start. File mtime = last write.

**History snapshot clocks.** Snapshot id '2026-09' (CFG:74). Last revision in the dump 2026-10-01T01:38:27Z (CFG:111). Downloaded 2026-10-24 UTC (/home/user/truth-lag/ec-hw2/report/skeleton_template.md:104). No publication date of the snapshot is recorded in the repo.

**What this means for a 'when did we know' clock.** Three clocks can be built. (a) meta.dt: when a stream reader could have known; exists for every event; used for all published numbers. (b) A new Bronze column such as ingested_at, or the Delta commit time: when the warehouse knew; only meaningful for data loaded after the lakehouse exists, and for the old data it is the backfill time. (c) File proxies (session start, mtime): coarse, per file. Time travel answers 'what did the warehouse know at commit N'; E(L) on the published cohort needs clock (a).

## Reuse plan

### How imports work
- READ: `config.py` asks callers to put its folder on sys.path, then `import config` (CFG:6-11). The ingest scripts do `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`, `import config`, then `from ingest.history_columns import ...` (PH:53-59, LL:43-45, LR:47-50). `ec-hw2` has a hyphen, so it cannot be a package name; `/home/user/truth-lag/ec-hw2/ingest/__init__.py` and `/home/user/truth-lag/ec-hw2/tests/__init__.py` exist (empty).
- A new module, for example in /home/user/truth-lag/etl/, needs: `sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ec-hw2'))`, then `import config` and `from ingest import parse_stream, label_live, late_reverts, parse_history`.
- RAN (probe /tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/port_inventory/probe/import_probe.py): with ec-hw2 on sys.path, before or after the repo root, `ingest` resolves to ec-hw2/ingest and all five modules import. With only the repo root on sys.path, `ingest` is the repo-root folder (a namespace package) and the import fails: `ImportError cannot import name 'parse_stream' from 'ingest' (unknown location)`. So a new package must not be named `ingest`, `config` or `tests`.
- READ: importing config loads `ec-hw2/.env.atlas` and `ec-hw2/.env` if python-dotenv is installed (CFG:226-233) and makes no folders. The four scripts need only pandas, numpy, pyarrow. `ingest/build_documents.py` needs `bson` (pymongo); do not import it in the Delta path. RAN: the imports and tests worked in a venv without pymongo.
- Spark workers also need ec-hw2 on their Python path if a UDF imports these modules: UNVERIFIED.

### A. Import unchanged (pure, no file access)
- CFG: every constant, `user_kind`, `editor_key`, `utc`.
- HC: `COLUMNS` and the type sets, `cast_history_frame`, `split_list`, `sha1_base36_to_hex`.
- PS: `flat_page_change`, `flat_revert_risk`, `flat_tags`, the three schemas and the two column lists, `TableBuilder`, `find_gaps`, `dedupe_revert_risk`. RAN: `json.loads` -> `flat_*` -> `TableBuilder` builds the Arrow table from event dicts with no file involved (38 fixture events -> 38 rows, times timestamp[us, UTC]).
- PH: `filter_cohort`, `comment_null_prefix`, `null_revision_masks`, `add_user_fields`, `add_labels`, `join_reverters`, `count_prev_window`, `build_revisions`, `build_revert_links`, `t_bucket`, `summarize`.
- LL: `add_user_columns`, `edit_events`, `revert_events`, `check_newest_parent`, `range_cover`, `range_complete_flags`, `save_time_tags`, `first_mw_reverted`, `count_in_window`, `build_cohort`, `live_revisions`, `build_links_all`, `first_exact_links`, `summarize`.
- LR: `cover_pairs`, `link_tags`, `late_rows`, `summarize`.

### B. Thin wrapper: same logic, read from tables instead of files
| Existing | What the wrapper replaces |
|---|---|
| `parse_stream.list_part_files` + `read_lines` | Reuse as the Bronze file reader (pure Python gzip; tolerant of cut-short files). The wrapper appends (raw line as string + envelope) to the Bronze table instead of flattening |
| `parse_stream.parse_stream_dir` (PS:238-273) | Its filter order (bad JSON, canary, non-enwiki, no meta, repeated meta.id) must be re-done on Bronze rows. The in-memory `seen` set becomes an insert-only MERGE on meta_id |
| `parse_stream.run` (PS:334-398) | Table writes instead of `write_parquet`; keep the stats dict as the _SUCCESS content |
| `parse_history.run` (PH:591-656) | Read the two History snapshot tables as string frames, then the same function chain. `read_slim_reverters` (PH:259, a Parquet filter on a file path) becomes a semi-join on revision_id; `read_slim_page_times` (PH:350) becomes a 2-column table read |
| `label_live.load_page_change` + the three reads in `label_live.run` (LL:614-617) | Read Silver tables into pandas. RAN (probe /tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/port_inventory/probe/dtype_probe.py): on the fixture data the three live output tables are identical whether page_change is loaded with numpy_nullable dtypes (the script's way), with plain pandas dtypes (float64 and object for nullable columns, as a Spark toPandas would give), or from a pyarrow table with `to_pandas(types_mapper=...)`. Plain dtypes print a pandas FutureWarning at LL:252 and LL:452. Not tested on real data |
| `late_reverts.load_september` (LR:74-97) | Table read with the same two membership filters (page_id in the revert pages, or revision_id in the mw-reverted rev_ids), then `cast_history_frame` |
| `late_reverts.history_cohort_ids` (LR:100-110) | Read rev_id from the history revisions table |
| the `write_parquet` / `write_json` helpers | Delta writes; keep a _SUCCESS_<step>.json for the row counts |

The lowest-effort bridge also works: export the needed tables to temp Parquet files and call the existing `run(...)` functions with folder arguments (RAN on fixtures: `parse_stream.run(raw, parsed)`, `label_live.run(parsed, tables)`, `late_reverts.run(parsed, tables, hist)`).

### C. Logic that must be restructured to run per day or per hour
| Step | Rule today | Lookback or state an incremental run needs |
|---|---|---|
| Bronze append | all files re-read each run | A file ledger (path, size, lines already loaded). Skip files younger than 120 s (CFG:58). A file read while open or cut short can grow later; its old lines stay a prefix, so load only the lines after the stored count. Old hour folders can get new files (new session, replay), so track files, not partitions |
| Event dedupe | set of meta.id per stream (PS:246) | Insert-only MERGE on (stream, meta_id). A repeated event carries the same meta.dt, so the MERGE can be limited to the event-date partitions present in the batch (DERIVED from CAP:45 and PS:262-269) |
| One row per rev_id, earliest meta_dt (edits LL:178-188, reverts LL:191-196, risk PS:303-307) | sort + keep first | Insert-only MERGE on rev_id keeps the first LOADED row, not the earliest. Either keep event grain in Silver and pick the earliest at read time, or MERGE with 'update when source.meta_dt < target.meta_dt'. Real data: 0 repeated rev_id among edits; the risk stream does repeat rev_ids |
| page_edits_prev_1h, live (LL:424-426) | edit and create events on the same page_id, all namespaces, one per rev_id, with meta_dt in [seen_ts - 3600 s, seen_ts), microseconds, the edit itself excluded | The batch plus the previous 1 hour of Silver events by meta_dt. A late event changes the count of edits seen up to 1 hour after it |
| page_edits_prev_1h, history (PH:322-347, 620-628) | slim rows on the page with event_timestamp in [ts - 3600 s, ts), whole seconds, all revisions | Slim rows from 1 hour before the window start. Same-second revisions are not counted |
| Save-time tags (LL:326-337) | union of `tags` of tag events with tag.meta_dt <= rev ts + 60 s (inclusive, relative to rev_dt, not seen_ts), minus mw-reverted | 60 s of lookahead on the tags stream, which is a separate capture unit with its own lag. Finalize a batch only when the tags stream is past max(rev_dt) + 60 s, or update later |
| mw_reverted_tag, mw_reverted_at, confirmed_by_tag (LL:340-343, 466, 644) | first mw-reverted addition at ANY later time | Unbounded lookahead: this is a label observation that arrives later (append to the observations table, MERGE into the label fact) |
| Range cover (LL:210-300) | exact E covers R on the same page when (original_dt, original_id) < (R.rev_dt, R.rev_id) <= (prior_rev_dt, parent_id) and R.rev_dt < E.rev_dt; inexact E covers revert_oldest_id <= R.rev_id <= revert_newest_id | Unbounded lookback, set per revert by its own fields: all Silver revisions of the page with rev_dt > E.revert_original_dt (exact) or rev_id >= E.revert_oldest_id (inexact). Evidence that it is long: October reverts cover September revisions with a median age of 33.1 days (FACTS:314); 773 reverted live revisions sit in ranges that start before the capture (FACTS:85). MediaWiki's mw-reverted tag stops at 15 revisions, the stream revert does not (CFG:204-206) |
| Order between batches | none (one batch) | R is saved before E but can be published after E when both are seconds apart (K median 3.44 s, p99 17.78 s, FACTS:76-78). Re-check reverts of the previous batch against new revisions, or hold a watermark of a few minutes |
| First exact revert per cohort revision (LL:474-479) | min (reverting_ts, reverting_rev_id) among exact covers | MERGE upsert on reverted_rev_id: replace when the new (reverting_ts, reverting_rev_id) is smaller. With ordered loads the first one stays |
| range_size, range_complete (LL:299, 303-320) | pairs per E over all captured revisions; per page the first captured rev_id | range_size can grow when a late revision arrives. State: min captured rev_id per page |
| within_followup, provisional flag (LL:465, 526; CFG:105-113) | T_s <= 345,600 s (live), <= 1,728,000 s (history). Labels final when the newest meta_dt >= LIVE_WINDOW end + 4 days + 5 minutes | Each cohort day becomes final 4 days (+5 min) after its end. followup_s depends on the newest event of the run, so compute it at read time or per commit |
| Late-tag link (LR:131-142) | a covering revert on the same page with meta_dt in [tag.meta_dt - 600 s, tag.meta_dt] | 600 s of page_change revert events before the tag event |
| restored_later (LR:177-179) | the reverting revision is itself covered by a later revert | Unbounded lookahead: update when it happens |
| Late-revert candidates (LR:74-97, 276-277) | slim rows not reverted in the dump, on pages with any captured revert or with an mw-reverted addition | The History snapshot table (static per snapshot) joined to new reverts and tag events |
| History null-revision rule (a) (PH:203-221) | parent sha1 looked up in the whole cohort file | The parent row; parents before the window are not in the file and fall to rule (b) |
| History reverter join (PH:259-316) | reverting revision looked up in the slim month file | Slim rows up to the end of the snapshot month; 4 reverts dated 2026-10-01 are not found (DM:124) |
| History labels | one batch per monthly snapshot | Unit = snapshot. Each cohort revision has 20 days of follow-up before the dump's last revision (CFG:109-111) |

`/home/user/truth-lag/ec-hw2/speed_layer.py` is an existing example of both patterns: a batch rebuild that replaces by key and removes stale rows (lines 127-163), and a follow mode that tails raw files, keeps a set of meta.id and skips half-written lines (lines 219-267).

## Golden numbers

All values are READ from FACTS (line numbers given) or from the committed result files /home/user/truth-lag/ec-hw2/results/mongo_q5_truth_lag_preview.csv, mongo_q3_time_to_revert.csv and mongo_q5_truth_lag_preview_activity.csv. E(L) values are DERIVED as 1 - known / n. Table names are those of DM. FACTS was built on 2026-10-29 from data-v2; the newest parsed event is 2026-10-27T20:59:59Z (FACTS:3, 88). A rebuild must stop at that event to match the live numbers.

| # | Key | Value | Cohort | Filter or expression |
|---|---|---|---|---|
| 1 | history_file_rows (FACTS:14) | 300,564 | history input | count(*) of data/history/enwiki_rev_ns0_2026-09-08_10.parquet |
| 2 | history_slim_file_rows (15) | 5,266,843 | history input | count(*) of data/history/enwiki_rev_all_2026-09_slim.parquet |
| 3 | history_dropped_namespace_not_0 / null_same_sha1 / null_comment (16-18) | 4,265 / 568 / 715 | history | cohort file rows with page_namespace_historical != 0; then rule (a); then rule (b) |
| 4 | history_revisions (19) | 295,016 | history | count(*) history_revisions (= 300,564 - 4,265 - 568 - 715) |
| 5 | history_revert_links = history_reverted_any_time (52, 35) | 19,858 | history | count(*) history_revert_links = count(history_revisions where reverted_any) |
| 6 | capture_page_change_events = live_page_change_events (95, 61) | 1,231,427 | stream | count(*) page_change (distinct meta_id, all namespaces, all kinds) |
| 7 | capture_tags_events (107) | 1,603,253 | stream | count(*) tag_events |
| 8 | capture_revert_risk_events (101) | 789,634 | stream | distinct meta_id of the risk stream BEFORE the per-rev_id dedupe (stats 'rows', PS:272; build_facts.py:512). It is not the row count of revert_risk.parquet |
| 9 | live_dropped_not_edit / namespace_not_0 / outside_window (65, 63, 64) | 33,915 / 379,956 / 538,090 | live | page_change kind not in (edit, create) [delete 25,950; move 7,658; undelete 279; visibility_change 28]; then ns != 0; then rev_dt outside [2026-10-20, 2026-10-23). Repeated rev_id 0, null revisions 0 |
| 10 | live_revisions (62) | 279,466 | live | count(*) live_revisions |
| 11 | live_revert_events (86) | 52,112 | stream, all namespaces | page_change where revert_method is not null, one row per rev_id |
| 12 | live_revert_events_newest_not_parent (87) | 2,209 | stream | of those: revert_newest_id or parent_id null, or not equal (LL:199-207) |
| 13 | mongo_revert_links_docs (112) | 38,216 | both | count(history_revert_links) + count(live_revert_links); so live_revert_links has 18,358 rows (DERIVED) |
| 14 | mongo_tag_events_docs (113) | 99,606 | stream | count(tag_events where mw_reverted_added) |
| 15 | history_edits_bot / temporary / registered / unknown (22-25) | 33,483 / 38,164 / 223,366 / 3 | history | history_revisions group by user_kind |
| 16 | live edits by kind (results CSV, n_edits) | bot 31,973 / temporary 36,314 / registered 211,179 / unknown 0 | live | live_revisions group by user_kind |
| 17 | history_pages / history_editors (20-21) | 165,415 / 37,177 | history | nunique(page_id); nunique(user_key) |
| 18 | history_reverted_20d, history_revert_rate_pct (29-30) | 19,700; 6.68% | history | history_revisions where reverted (= reverted_any and secs_to_revert <= 1,728,000) |
| 19 | history revert rate non-bot / temporary / registered / bot (31-34) | 7.43 / 27.32 / 4.03 / 0.81 % | history | mean(reverted) for user_kind != bot, and by user_kind |
| 20 | history_reverted_4d, mongo_q5_history_revert_rate_4d_pct (47, 152) | 17,646; 5.98% | history | history_revert_links where within_followup and T_s <= 345,600; divided by 295,016 |
| 21 | history_links_by_other_20d (53) | 17,868 | history | history_revert_links where within_followup and by_other |
| 22 | live_reverted_4d, live_revert_rate_pct (66-67) | 17,818; 6.38% | live | live_revert_links where within_followup (first exact cover, T_s <= 345,600); divided by 279,466 |
| 23 | live revert rate human / temporary / registered / bot (68-71) | 7.14 / 26.91 / 3.74 / 0.44 % | live | same label by user_kind (temporary 9,772 of 36,314; registered 7,905 of 211,179; bot 141 of 31,973); human = user_kind != bot |
| 24 | history_median_T_s (36) | 3,660 s | history | median(T_s) of links where within_followup |
| 25 | history median T by author kind (38-41) | non-bot 0.96 h; temporary 0.33 h; registered 3.03 h; bot 47.23 h | history | same, by author_kind |
| 26 | history_T_within_1h / within_1d / over_7d / p90 (42-45) | 49.86% / 79.68% / 6.32% / 4.21 days | history, 20-day reverts | share T_s < 3,600; < 86,400; > 604,800; 90th percentile |
| 27 | history_median_T_4d_s (48) | 1,942 s | history, 4-day horizon | median(T_s) of links where within_followup and T_s <= 345,600 |
| 28 | live_median_T_s (72) | 1,344 s | live | median(T_s) of live_revert_links where within_followup |
| 29 | Mongo Q3 bucket counts, history 20 d (results CSV) | 3,470; 2,722; 1,542; 2,088; 3,078; 2,797; 1,028; 921; 808; 852; 394 | history | T_s cut on config.LAG_GRID_S, lower edge included, upper not |
| 30 | Mongo Q3 bucket counts, live 4 d (results CSV) | 4,148; 2,830; 1,428; 1,923; 3,076; 2,532; 763; 1,118 | live | same cut on live links within_followup |
| 31 | history_T_within_1h_4d / 1d_4d (50-51); live_T_within_1h / 1d (74-75) | 55.66 / 88.96 %; 57.97 / 89.44 % | both, 4-day horizon | cumulative share of T_s below 3,600 and below 86,400 (strictly below) |
| 32 | Known-by counts, history, user kind all (results CSV) | waits 0, 1 min, 5 min, 15 min, 1 h, 6 h, 1 d, 2 d, 4 d: 0; 3,506; 6,204; 7,737; 9,822; 12,900; 15,697; 16,725; 17,646 of 17,646 | history | revisions left-joined to links; eventual = 0 <= T_s <= 345,600; known when T_s + coalesce(K_s, 0) <= wait (inclusive) (/home/user/truth-lag/ec-hw2/queries/run_mongo.py:850-866) |
| 33 | E(L), history (DERIVED) | 1.0000; 0.8013; 0.6484; 0.5615; 0.4434; 0.2690; 0.1104; 0.0522; 0.0000 | history | 1 - known / 17,646 |
| 34 | Known-by counts, live, user kind all (results CSV) | 0; 3,986; 6,958; 8,398; 10,326; 13,405; 15,936; 16,699; 17,818 of 17,818 | live | same expression; K_s is the stream delay of the first exact revert |
| 35 | E(L), live (DERIVED) | 1.0000; 0.7763; 0.6095; 0.5287; 0.4205; 0.2477; 0.1056; 0.0628; 0.0000 | live | 1 - known / 17,818 |
| 36 | mongo_q5 known at 1 min / 1 h / 1 d (153-155, 160-162) | history 19.87 / 55.66 / 88.96 %; live 22.37 / 57.95 / 89.44 % | both | rows 32 and 34 as shares |
| 37 | known at 1 h by author kind (156-157, 163-164) | history temporary 62.43% (6,157 of 9,863), registered 47.51% (3,622 of 7,623); live temporary 65.06% (6,358 of 9,772), registered 49.69% (3,928 of 7,905) | both | same, by user_kind |
| 38 | live_K_median_s / p90 / p99 (76-78) | 3.44 / 8.57 / 17.78 s | live | percentiles of K_s over live_revert_links with one row per reverting_rev_id (LL:523, 561) |
| 39 | live tag confirmation (80-85) | range <= 15: 16,761 revisions, 99.42% confirmed; range > 15: 284, 0.00%; incomplete range: 773, 67.27% | live | live_revert_links where within_followup; split by range_complete and range_size <= 15; share with confirmed_by_tag (LL:515-518) |
| 40 | history_tag_agreement_pct (54) | 99.52% | history | mean(reverted_any == mw_reverted_tag) |
| 41 | live_revert_risk_coverage_pct; risk_no_score_edits (79, 331-335) | 98.15%; 10,450 = 5,392 page creations + 5,058 not captured | live | live_revisions where revert_risk is null; coverage = scored / rows with parent_id not 0 and not null (269,016 of 274,074, DERIVED) |
| 42 | page_edits_prev_1h groups 0, 1, 2-4, 5-9, 10+ (activity CSV) | history 202,410; 42,155; 32,697; 11,888; 5,866. Live 190,392; 39,277; 30,782; 11,929; 7,086 | both | count of revisions by page_edits_prev_1h group |
| 43 | late_reverts rows and classes (298-309) | 4,350 rows (namespace 0: 3,591); exact 2,970 (2,472); inexact_undo 198 (194); method_unknown 1,182 (925); in history cohort 217 (121 / 16 / 80) | late | count(*) late_reverts; page_ns == 0; group by class; in_history_cohort |
| 44 | late_reverts pages / reverting actions / restored later / median age exact (310, 312, 315, 314) | 2,437 / 1,684 / 206 / 33.1 days | late | nunique(page_id); nunique(reverting_rev_id); restored_later is true; median(age_days) where class = exact |

Capture checks that belong next to these: first and last meta.dt per stream (FACTS:93-94, 99-100, 105-106), gaps over 120 s = 0 / 3 / 0 with 850 s in total (96, 102, 104, 108), files cut short 27 of 232, 28 of 230, 50 of 286 (97, 103, 109).

A small parity target that runs without real data (RAN on the fixtures of TS): 38 page_change, 7 tags and 3 risk events -> page_change.parquet 38 rows (39 lines read, 1 repeated meta.id), revert_risk 2, tag_events 7, capture_gaps 4; live_revisions 32; live_revert_links 9; live_revert_links_all 17; late_reverts 5 (exact 3, inexact_undo 1, method_unknown 1); known-by at 1 min = 8 of 9.

## Volumes

The raw data and tables are not in this container, so every number here is READ from committed files or DERIVED from them.

| What | Value | Source |
|---|---|---|
| page_change events (distinct meta.id) | 1,231,427 from 2026-10-19T23:00:00Z to 2026-10-27T20:59:59Z (190.0 h): about 6,481 per hour, about 155,500 per day | FACTS:93-95; rate DERIVED |
| of which edit + create | 1,197,512 in all namespaces; 817,556 in namespace 0 (about 103,300 per day) | DERIVED from FACTS:61, 63, 65 |
| live cohort | 279,466 revisions in 72 h: about 3,881 per hour, 93,155 per day | FACTS:62; /home/user/truth-lag/ec-hw2/scaleout/SHARDING.md:25 says 'about 3,900 new revisions per hour' |
| revert events | 52,112 in all namespaces (about 6,580 per day) | FACTS:86 |
| other kinds | delete 25,950; move 7,658; undelete 279; visibility_change 28 | /home/user/truth-lag/ec-hw2/notebooks/01_data.ipynb, output of code cell 7 |
| revert-risk events | 789,634 in the same 190.0 h: about 4,156 per hour, about 99,700 per day | FACTS:99-101 |
| tags events | 1,603,253 from 2026-10-17T01:30:18Z to 2026-10-27T20:59:59Z (259.5 h): about 6,178 per hour, about 148,300 per day. 99,606 of them add mw-reverted | FACTS:105-107, 113 |
| raw bytes, gzip (Mac copy when notebook 01 last ran) | page_change 233 part files, 452.0 MB; revert risk 231 files, 263.1 MB; tags 287 files, 292.8 MB. Total 751 files, 1,007.9 MB | notebook 01_data.ipynb, output of code cell 5 |
| gzip bytes per event | about 367 (page_change), 333 (revert risk), 183 (tags) | DERIVED |
| growth per day, gzip | about 57 + 33 MB (capture a) and 27 MB (capture b), about 117 MB together. The plan had guessed 250 MB per day | DERIVED; /home/user/truth-lag/ec-hw2/genai/APPROVED_PLAN.md:376 |
| earlier state | 486 MB in 449 part files on 2026-10-24 about 06:00 UTC | /home/user/truth-lag/ec-hw2/PROGRESS.md:247 |
| uncompressed raw size | not recorded | open question |
| files read by the last parse; cut short | 232 / 230 / 286 files; 27 / 28 / 50 cut short (105 of 748) | FACTS:97, 103, 109 |
| repeated meta.id dropped | 3 / 0 / 0 | notebook 01, output of code cell 11 |
| capture gaps over 120 s | page_change 0; tags 0; revert risk 3: 198.1 s and 347.7 s on 2026-10-21 (11:38:05 to 11:47:11 UTC), 304.0 s on 2026-10-26 (14:08:37 to 14:13:41 UTC); total 850 s | notebook 01, cell 11; FACTS:96, 102, 104, 108 |
| capture start | unit a: since 2026-10-19T23:00:00Z; unit b: since 2026-10-17T00:00:00Z, first tags event 2026-10-17T01:30:18Z. Both units started about 2026-10-24 04:52 UTC and replayed | service files in /home/user/truth-lag/ingest/vps/; CFG:67-68; /home/user/truth-lag/ec-hw2/ingest/README.md:24-25 |
| replay catch-up | on 2026-10-24 about 06:00 UTC the newest page_change hour was 2026-10-23 13:00 UTC | PROGRESS.md:247 |
| restarts | 7 capture-a sessions and 4 capture-b sessions between 04:52 and 05:37 UTC on 2026-10-24; baseline NRestarts a = 2, b = 1 | PROGRESS.md:257 |
| capture limits | MemoryMax 500M; stops below 5 GB free disk; at most 48 open writers; state saved every 500 events | service files; CAP:13-15 |
| History dump | 557,344,652 bytes (bz2); 6,369,430 rows; 78 columns; 0 bad rows | CFG:73; /home/user/truth-lag/ingest/vps/filter_stats.json |
| History filter output | cohort file 300,564 rows x 78 string columns; slim file 5,266,843 rows x 12 string columns. File sizes are not recorded | filter_stats.json; DM:25-26 |
| parsed tables, rows | page_change.parquet 1,231,427; tag_events.parquet 1,603,253; revert_risk.parquet at most 789,634 (exact count not in the repo); capture_gaps.csv 3 | FACTS:95, 107, 101, 102 |
| cohort tables, rows | history_revisions 295,016; history_revert_links 19,858; live_revisions 279,466; live_revert_links 18,358 (DERIVED: 38,216 - 19,858); live_revert_links_all not in the repo; late_reverts 4,350 | FACTS:19, 52, 62, 112, 298 |
| Mongo page_hour | 605,017 (page, hour) documents, namespace 0, whole capture | FACTS:115 |
| rows per day per stream | written to `rows_per_day` in data/parsed/_SUCCESS_parsed.json (PS:364), which is not in the repo | open question |
| runtime: filter_history.py | 154 s on the VPS | filter_stats.json |
| runtime: parse_history.py | 7.5 s on 2026-10-24; the docstring says about 10 s and about 2.5 GB of memory | /home/user/truth-lag/ec-hw2/genai/PROMPTS.md:179; PH:36 |
| runtime: parse_stream.py, label_live.py, late_reverts.py | each writes `seconds` into its _SUCCESS file (PS:365, LL:664, LR:294); those files are not in the repo | open question |
| runtime: tests | the two ingest test files, 30 tests, 0.93 s | RAN here |

## Gotchas

Each rule is READ at the lines given, unless marked.

**Clocks and time**
1. No receive time exists. The capture writes the payload unchanged (CAP:114) and partitions by meta.dt (CAP:45). The data of the live window was replayed days later (ingest README:24-25). Use meta.dt as the knowledge clock.
2. meta.dt has milliseconds; rev_dt has whole seconds. T_s is a floored int (LL:457); K_s is a float (LL:458). Parsed tables store timestamp[us] (PS:55); cohort tables store timestamp[ns] (LL:57; history via pandas, PH:140-143). RAN: confirmed on the fixture outputs. Delta has microsecond timestamps only, and Spark may refuse nanosecond Parquet: UNVERIFIED here.
3. Cohort windows are half-open [start, end) (CFG:13-15, 98-101; PH:171-172; LL:374-375). `within_followup` is inclusive: T_s <= 345,600 or <= 1,728,000 (LL:465; PH:251).
4. Known-by uses `known_by <= wait` (inclusive) on T_s + coalesce(K_s, 0) (/home/user/truth-lag/ec-hw2/queries/run_mongo.py:856-863). The time-to-revert buckets use [lower, upper) (CFG:122-123; run_mongo.py:927). So 'known within 1 min' (3,506) is not 'T under 1 min' (3,470). The last grid edge is 20 days + 1 s so that T = 20 days lands in the last bucket (CFG:122-123).
5. The wait starts at the reverted revision's save time (rev_dt), not at its publish time. Eventual revert = 0 <= T_s <= 4 days for BOTH cohorts in the known-by numbers, self-reverts included (run_mongo.py:856). Groups with fewer than 100 eventual reverts are dropped (CFG:220; run_mongo.py:860-861).
6. `followup_s` and the provisional flag depend on the newest page_change meta_dt of the run (LL:427, 526, 618).

**Raw files and parsing**
7. 105 of 748 part files have no gzip end marker (FACTS:97, 103, 109). A reader must keep the complete lines (PS:104-120). A file without an end marker is not always still open; the 120 s mtime rule decides (PS:96-97). Whether Spark's own gzip reader tolerates this is UNVERIFIED.
8. Dedupe on meta.id only, per stream (PS:262-269). Do not use topic / partition / offset: offsets are shared with other wikis (PS:282-284), and every fixture event has partition 0 and offset 1 (TS:46-49).
9. The filter order matters for the counters: bad JSON, canary, non-enwiki, no meta, repeated id (PS:250-270). The tags stream uses `database`, `page_namespace`, `rev_timestamp` and top-level `rev_id` / `page_id` (PS:174-191).
10. The partition folder is not a safe source of the event date. Read meta.dt from the payload. The test helper `write_part` puts all events into the folder of the first event (TS:114-120).
11. Tag lists are turned into sorted sets (PS:176-177). `mw_reverted_added` is true only when the tag is in `tags` and not in `prior_state.tags` (PS:178, 186).
12. Revert risk: one row per rev_id, the EARLIEST score (PS:303-307). `capture_revert_risk_events` counts events, not rows (build_facts.py:512). Page creations never have a score (FACTS:333).
13. Gaps: per stream, over kept events sorted by meta.dt, strictly more than 120 s (PS:289-291; CFG:59).

**History**
14. Every dump column is a string. Cast with `cast_history_frame` only (CFG:83-84; HC:99-111). Booleans are 'true' / 'false'; times look like '2026-09-08 00:00:00.0' (HC:80). Some literal strings became null in the Parquet copy (CFG:85-87; FH:60).
15. Two namespace columns. The VPS filter used the CURRENT namespace (FH:44). The cohort also needs `page_namespace_historical == 0` (PH:176); 4,265 rows drop. The live cohort uses the namespace at event time, so the cohorts differ by design (DM:91).
16. Null revisions. Rule (a): same sha1 as the parent, looked up in the FULL cohort file, not in the filtered rows (PH:209-215). Rule (b) only when (a) cannot apply: bytes_diff == 0 and the comment, after removing a leading '<user name> ' (case-insensitive, name from event_user_text_historical), starts with one of 9 prefixes (PH:182-200, 217-220; CFG:197-201). Live: only kind == 'edit' with sha1 == prior_sha1 (LL:378); page moves are their own kind.
17. User kind order: unknown, bot, temporary, registered (CFG:130-156). Bot = 'group' is an item of `event_user_is_bot_by`, the CURRENT flag, not the historical one; 'name' alone is not a bot (TH:168-169). The slim file has no temporary flag, so reverters use the '~2' name prefix (PH:295-296; CFG:142). A numpy bool fails the `isinstance(flag, bool)` test, so flags are turned into Python bools first (LL:103-119; TS:506-511).
18. `editor_key` is 'u:<user_id>' or 't:<name>' (CFG:159-167). `by_other` needs both keys non-null and different (PH:302-303; LL:463-464).
19. sha1 is base 36 in the dump and in the stream; the tables store 40-digit hex (HC:131-135; PH:392; LL:422). The null-revision tests compare the base-36 text.
20. `edit_count` differs: the dump counts the edit itself (minimum 1), the stream does not (can be 0) (DM:69).
21. History `parent_id` is 0 for a page creation (DM:90). Code that counts edits uses `parent_id.fillna(0) != 0` (LL:522).
22. `page_title` in the history table is the dump's CURRENT title, with the title at edit time kept in `page_title_historical` (PH:368-369). The live table has only the title at edit time (LL:393-395). This matters for dim_page.
23. History `reverting_ts` is computed as ts + secs_to_revert (PH:417). 4 reverting revisions are not in the slim file (DM:124). The 20-day label uses `revision_seconds_to_identity_revert <= 1,728,000` (PH:251).
24. `count_prev_window` needs whole seconds and stops otherwise (PH:623-624). It counts all slim revisions on the page, bots and null revisions included, and not the edit itself or another revision of the same second (PH:322-347; TH:250-258).

**Live labels**
25. Labels are not columns of live_revisions; they live in live_revert_links (DM:75). 'Reverted' = a link with within_followup exists.
26. Range cover (LL:210-300; DM:115-120). Exact revert: (original_dt, original_id) < (R.rev_dt, R.rev_id) <= (prior_rev_dt, parent_id); a missing parent_id falls back to revert_newest_id (LL:269-275). Inexact revert: revert_oldest_id <= R.rev_id <= revert_newest_id. Always R.rev_dt < E.rev_dt (LL:285-286). The newest_id bound applies to inexact reverts only (LL:225-226). The comparison packs (seconds, rev_id) into one int64 and asserts rev_id < 2^32 (LL:147-153). A null `revert_is_exact` counts as not exact (LL:252).
27. Revert events are never filtered by namespace, and the candidate revisions are all captured edits and creates in all namespaces (LL:642; DM:120). The cohort link is the first EXACT cover by (reverting_ts, reverting_rev_id) (LL:474-479). A revision covered only by an inexact undo gets no label (TS:455).
28. `range_size` counts captured revisions and is a lower bound when `range_complete` is false (LL:303-320). The tag-confirmation shares use complete ranges only (LL:515-518).
29. Save-time tags: tag.meta_dt <= rev ts + 60 s, measured from rev_dt, inclusive, union of the full tag sets, mw-reverted removed (LL:326-337). `mw_reverted_at` is the first addition at any time (LL:340-343).
30. Live `page_edits_prev_1h` uses meta_dt in microseconds and the literal 3600 (LL:424-426), not `config.PAGE_PREV_WINDOW_S`. It counts events of all namespaces on the page.
31. `human_share` means user_kind != 'bot', so it includes 'unknown' (LL:536-537).

**Late reverts**
32. A slim row with a null `revision_is_identity_reverted` counts as not reverted (LR:89-90; TS:230). `page_ns` is the page's CURRENT namespace (LR:14-17). The chosen revert is the first exact one, else the first one (LR:152-154). Tag-only rows have class method_unknown and an upper-bound age (LR:169, 176). All counts are lower bounds (LR:12-13). Without history_revisions the cohort flag uses a window fallback (LR:106-110).

**Project**
33. Two folders are named `ingest` (/home/user/truth-lag/ec-hw2/ingest/README.md:3). RAN: with only the repo root on sys.path the import fails. Also, `refresh_live.sh` runs rsync against the VPS and uses the macOS form `sed -i ''` (/home/user/truth-lag/ec-hw2/refresh_live.sh:22, 42): do not run it here.
34. Two definitions exist for the headline. /home/user/truth-lag/docs/schema_and_warehouse.md:23-24 defines truth_lag = label_time - event_time and E(L) on a grid up to H, with H still open (line 54). The published numbers use the 9 wait points of CFG:127-128 and a 4-day horizon.

## Test fixtures

READ: TS and TH. RAN: both files pass here (30 tests, 0.93 s), and the builders can be imported from outside the tests folder (probe /tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/port_inventory/probe/fixture_probe.py: `from tests import test_stream as ts, test_history as th` with ec-hw2 on sys.path).

### Stream fixtures (TS)
The header says the events use the same fields and types as the real files: page_change 1.12.0, tags-change 1.0.0, revert-risk 1.3.0 (TS:6-8).

| Helper (line) | What it builds |
|---|---|
| `iso(ts)`, `iso_ms(ts)` (38, 42) | ISO text with whole seconds (rev_dt) or milliseconds (meta.dt) |
| `meta(stream, mid, dt, domain='en.wikipedia.org')` (46) | the meta block: stream, id, domain, dt, topic 'eqiad.<stream>', partition 0, offset 1 |
| `person(name='Alice', uid=11, bot=False, temp=False)` (52) | a performer block |
| `pc_ev(rev_id, page_id, rev_dt, parent_id=0, prior=None, kind='edit', ns=0, sha1=None, size=100, revert=None, who=None, meta_dt=None, mid=None, domain=...)` (57) | one page_change event. meta_dt defaults to rev_dt + 2 s; `prior` = (rev_id, rev_dt, size, sha1) |
| `revert(method, exact, oldest, newest, original=None)` (80) | the revision.revert block |
| `tag_ev(mid, rev_id, page_id, rev_ts, meta_dt, tags, prior_tags, ns=0)` (88) | one tags-change event |
| `risk_ev(mid, rev_id, page_id, rev_dt, meta_dt, p)` (96) | one revert-risk event |
| `part_path(raw, stream, dt, session, n)` (107), `write_part(raw, stream, events, session, mtime=OLD)` (114) | writes events as one .ndjson.gz part file in the dt / hour folder of the FIRST event, with an old mtime |
| `BOB` (temporary), `CAROL`, `DAVE`, `BOT` (126-129) | performers |
| `scenario_events()` (132) | returns (page_change events, tag events, risk events) |
| `slim_frame()` (222) | 8 September slim rows, all strings, 12 columns |
| `pipeline` fixture (242) | writes the raw files (plus one repeated event in a second session file), then runs parse_stream.run -> label_live.run -> late_reverts.run in a temp folder |
| `_lines(n)` (266), `_R(rows)` (358), `_E(**kw)` (363) | lines for gzip tests; small R and E frames for range_cover unit tests |

`scenario_events` covers (TS:132-219):
- page 1: an exact manual revert of 102-103 back to 101;
- page 2: an inexact undo of 202-203;
- page 3: an inexact undo first, then two exact reverts in the same second (the first exact by (rev_dt, rev_id) is 304);
- page 4: an inexact undo of an older edit (newest_id != parent_id);
- page 5: a null revision;
- page 6: namespace 1, not in the cohort, its revert is still used;
- 701 outside the live window; 801 a bot edit; 901 a page move;
- pages 10, 11, 13, 17: October reverts of September revisions (exact, restored later, inexact undo, exact plus tags, namespace 4);
- page 15: an exact undo of an older edit that covers up to the parent (beyond_newest);
- page 16: a rollback whose range starts before the capture (range_complete false);
- tags: one at +30 s (kept), one at +90 s (too late), mw-reverted additions, a tag-only late revert from before the page_change capture, and two tags 300 s and 1,200 s after a revert (the 600 s link window);
- risk: two scores for one rev_id (the earliest wins) and one more.
RAN counts: 38 page_change events (31 edit, 6 create, 1 move; namespaces 0: 35, 1: 2, 4: 1; 15 revert events), 7 tag events, 3 risk events. Outputs: page_change 38 rows, revert_risk 2, tag_events 7, live_revisions 32, live_revert_links 9, live_revert_links_all 17, late_reverts 5.

Other stream tests: gzip without an end marker, a truncated file, open files skipped, meta.id dedupe plus canary, gaps by time only, numpy bool flags, the provisional flag.

### History fixtures (TH)
| Helper (line) | What it builds |
|---|---|
| `cohort_row(**kw)` (33) | one dump row with all 78 columns as strings or null; defaults inside HISTORY_WINDOW |
| `slim_row(**kw)` (52) | one slim row, 12 string columns |
| `string_frame(rows, columns)` (64), `write_strings(rows, columns, path)` (68) | a frame, or a Parquet file, where every column is a string |
| `cast_cohort(rows)` (75) | `cast_history_frame` on such a frame |
| `_reverted(rev_id, reverting_id, secs='600', **kw)` (206) | a reverted cohort row |
Tests: casting, the half-open window and the historical namespace, rules (a) and (b), user kind order and keys, the 20-day label, the reverter join, the prev-1h count against a slow count, and one full run (TH:277-352).

### How a Delta pipeline's tests can reuse them
1. Import the builders: put ec-hw2 on sys.path, then `from tests import test_stream as ts, test_history as th`. Moving the builders to a shared helper module would be cleaner; that is a repo change for the plan to decide.
2. Parity test: build the raw files with `ts.write_part(...)` from `ts.scenario_events()`, run the old `parse_stream.run`, `label_live.run`, `late_reverts.run` into a temp folder, run the Delta pipeline on the same raw folder, then compare table by table after sorting by key (meta_id, rev_id, or (reverted_rev_id, reverting_rev_id)). The same test works on real data when it is present.
3. Incremental test: split `scenario_events()` into two or more batches by meta.dt and write them as separate session files; the final tables must equal the one-batch result. Useful splits: between a revision and its revert (pages 1, 3, 15), between an edit and its tag at +30 s, and with the repeated event in the second batch.
4. History: `th.write_strings(...)` gives the two all-string Parquet inputs; load them into the Bronze snapshot tables and compare with `parse_history.run(cohort_path, slim_path, out_dir, quiet=True)`.
5. Watch out: `write_part` puts all events into the folder of the first event; every fixture event has partition 0 and offset 1; `write_part` sets an old mtime so the open-file rule does not skip the file (pass `now=` or `include_open=True` to `parse_stream.run` if needed).

## Repo conventions

READ unless marked.

**Writing rules for docs, notebooks and comments** (/home/user/truth-lag/ec-hw2/STYLE.md)
- Short sentences (about 20 words), one idea each; plain words; no idioms (lines 6-8).
- One word per thing, defined in GLOSSARY.md: 'revert'; 'history cohort' and 'live cohort'; 'stream label' and 'dump label'; 'RQ1' and 'RQ2' (lines 9-14).
- Numbers carry units. Do not type a number that FACTS.md can change; name the FACTS key instead (lines 15-17).
- Data times are UTC, schedule times are PT, dates are YYYY-MM-DD, and the time zone is always written (line 18).
- Steps are numbered, with the exact command and what you should see (line 19).
- The words lane, agent, contract and fan-out are for the build log only (line 20). A list of words to avoid is at lines 22-26.
- Notebooks: a 4-line box (Question / Answer / Time to run / Needs); a What / Why / You should see cell above every code cell; the first code cell prints DATA_VERSION; the last cell checks the numbers against FACTS.md; commit with outputs (lines 28-35).

**Code rules** (STYLE.md:37-44)
- Every script starts with a docstring: purpose, inputs, outputs, exact run command. Comments explain why.
- Every rule and every path comes from `config.py`; never type a window, threshold or path twice. DM is the contract: 'If a script and this page disagree, the bug is in the script' (DM:3). A new pipeline should add its lake paths, table names and partition columns to config.py. Scripts that needed a not-yet-added constant used `getattr(config, NAME, default)` (PS:51; LL:54).
- Safe writes: write `name.tmp`, rename with os.replace, then write `_SUCCESS_<step>.json` with the row counts (PS:322-331, 390-397; PH:140-151, 641-651; LL:596-605, 657-665; LR:286-295). `*.tmp` is git-ignored.
- `_SUCCESS_<step>.json` holds step, data_version, a creation time, row counts and step flags (provisional, newest_meta_dt, lower_bound, seconds). The key names differ: `row_counts` in parsed, live and late_reverts; `rows` plus `inputs` in history. The next step checks the file before it runs (LL:609-611; LR:259-261; /home/user/truth-lag/ec-hw2/ingest/build_documents.py:88-109). build_facts.py reads these files and the summary JSON files, so a rebuilt pipeline should keep writing them (/home/user/truth-lag/ec-hw2/report/build_facts.py:343-348, 441-443).
- All times in code are timezone-aware UTC. Windows are half-open (CFG:13-15).
- Human editors appear only as pseudonyms in committed results; bots keep their names. The summaries hold no editor names (TH:350-352).

**Safety rules** (STYLE.md:46-52): never stop or change the VPS capture; never open EventStreams from a laptop; never `rsync --delete`; never `docker compose down -v`; never commit `ec-hw2/.env` or anything in `data/`; do not use the `timeout` command. Never delete or change data/raw or data/history (/home/user/truth-lag/ec-hw2/ingest/README.md:78).

**Running**
- Scripts run from the repo root: `.venv/bin/python ec-hw2/ingest/<script>.py`. Order: parse_history, parse_stream, label_live, late_reverts (/home/user/truth-lag/ec-hw2/ingest/README.md:50-61).
- Tests: `.venv/bin/python -m pytest ec-hw2/tests -q`, or one file (ingest README:80-85). Test files are `ec-hw2/tests/test_<part>.py` with tiny synthetic fixtures that use the real column names and types. There is no pyproject.toml, pytest.ini, conftest.py, uv.lock or .python-version in the repo (RAN: ls).
- Logging: parse_stream, label_live and late_reverts log to stdout with the logging module; parse_history uses print.

**Version pins**
- Python 3.12 is recommended, 3.11 works, older fails (/home/user/truth-lag/ec-hw2/check_setup.py:207-221; /home/user/truth-lag/ec-hw2/README.md:144). Notebook 00 was last run on 3.13.5.
- /home/user/truth-lag/ec-hw2/requirements.txt: `pandas>=2.3,<3` with the comment 'kept below 3 so PySpark works later in the final project'; `pyarrow>=17`; `pymongo>=4.19,<5`; `neo4j>=6.4,<7`; `python-dotenv>=1.0`; `pytest>=8`; no PySpark ('that is for the final project').
- /home/user/truth-lag/requirements.txt: `requests>=2.31`, `pandas>=2.0`, `pyarrow>=14`, `jupyter`, optional `pyspark>=3.5`. The root README says PySpark needs Java 17+.
- RAN: the ingest code and its 30 tests pass on Python 3.12.3, pandas 2.3.3, pyarrow 26.0.1, numpy 2.5.4.
- .gitignore already lists `data/*`, `*.parquet`, `spark-warehouse/`, `metastore_db/`, `derby.log`, `*.tmp`.

**PySpark so far.** Only /home/user/truth-lag/notebooks/00_access_points.ipynb, section (d), uses it: `SparkSession.builder.master('local[2]').appName('truthlag').getOrCreate()`, `spark.createDataFrame(mwh.astype(str))`, one groupBy count. Its saved output is 'PySpark skipped: [JAVA_GATEWAY_EXITED] Java gateway process exited before sending its port number.' and 'JAVA_HOME is not set'. So PySpark has never run in this repo. The top-level `etl/` and `reconcile/` folders hold only `.gitkeep`.

**Data release.** `ec-hw2/release_data.sh` zips data/tables (Parquet, JSON, SQLite), the Neo4j CSV files and DATA_VERSION into `data/release/truthlag-<version>.zip` and can publish it as a GitHub release. It does not contain data/raw, data/history or data/parsed (/home/user/truth-lag/ec-hw2/release_data.sh:4-5, 23).

## Open questions

- Where will the coding session get the inputs? data/raw, data/history and data/parsed are not in this container, ssh and rsync are forbidden for agents, and the GitHub data release holds only data/tables. Without them only the fixture parity test can run; the golden numbers cannot be reproduced here.
- Row counts not recorded in the repo: revert_risk.parquet (distinct rev_id; FACTS only has the 789,634 events before the per-rev_id dedupe) and live_revert_links_all.parquet (live_summary.json 'links.all_pairs'). Both are in JSON files on the owner's Mac.
- Rows per day per stream ('rows_per_day' in data/parsed/_SUCCESS_parsed.json) and the runtimes of parse_stream.py, label_live.py and late_reverts.py ('seconds' in their _SUCCESS files) are not in the repo. I could only derive average rates.
- Uncompressed size of the raw JSON per stream is not recorded (only gzip MB per stream from notebook 01). It is needed to size a Bronze table that keeps the raw JSON as a string.
- Which clock should 'when did we know' use? The raw data has no receive time and the live window was replayed 1.2 to 4.2 days late. Options: meta.dt (what all published numbers use), a new Bronze ingested_at or the Delta commit time (the backfill time for old data), or file proxies (session start in the file name, mtime). Only the VPS log pairs wall-clock time with meta.dt (one line per 10,000 events) and it is not in the repo.
- The exact meaning of meta.dt at Wikimedia (publish time vs ingest time at EventGate) was not checked; the repo calls it 'the time the stream published the event' (config.py:53).
- I did not see a real raw event. The JSON paths are those the parser reads plus the fields in the test fixtures. Whether real page_change events hold a null or a 0 rev_parent_id for page creations, and which extra fields exist, is unverified.
- Has the capture kept running after 2026-10-27T20:59:59Z (the newest parsed event), and is the 2026-10 MediaWiki History snapshot available? Both decide whether Bronze holds more than one snapshot and whether the live window can get dump labels. The published live numbers need a cut at the data-v2 event.
- Do Spark and delta-rs read the existing cohort Parquet files, whose timestamps are nanoseconds (label_live.py:57), and do they tolerate the 105 gzip files without an end marker? Not tested by me (another lab covers the engines).
- label_live gave identical outputs for three pandas dtype backends on the fixtures only. Real data (null parent ids, null flags, 1.2 million rows) was not tested.
- The headline definition is still open in docs/schema_and_warehouse.md (horizon H, lag grid, censoring with Kaplan-Meier, lines 22-30 and 54). The published numbers use a 4-day horizon, 9 wait points and T + K. The plan must say which definition the Gold E(L) mart follows, or keep both.
- Whether the 3 repeated meta.id events in page_change are byte-identical copies is unknown; the parser keeps the first in sorted path order.
