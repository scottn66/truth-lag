# Truth Lag: schema and warehouse (draft)

Based on the Group 9 proposal and `TruthLag_Problem_Statement.md`. **TBD** = open team decision.

## Question
For enwiki content revisions: how long between seeing a revision live on EventStreams and its reconciled state in MediaWiki History, how wrong is the live view at each wait *L*, and how much can early page signals close that gap?

## Layers
| Layer | Contents | Format |
|---|---|---|
| raw | append-only EventStreams events (`page_change.v1`, `recentchange`, `revert_risk`), MediaWiki History TSV snapshots, as received | hourly ndjson -> parquet |
| staging | typed, deduped (by event id / `(wiki_db, rev_id)`), enwiki ns0 filter, UTC timestamps | parquet |
| warehouse | star schema below, plus marts for E(L) | parquet (engine TBD) |

## Star schema
- **fact_edit**: grain = one revision. `wiki_db, rev_id, parent_rev_id, page_key, user_key, time_key, event_dt (t0), ingested_at, bytes_diff, is_bot, live_revert_flag, live_revert_dt, revert_risk_score`.
- **dim_page (SCD Type 2)**: `page_key, wiki_db, page_id, title, namespace, is_redirect, is_deleted, valid_from, valid_to, is_current`. New version on move, delete, restore, redirect change. Facts join as-of `event_dt` (H4 compares this to a current-title join).
- **dim_user**: `user_key, user_id/user_text, is_temporary, is_anonymous, is_bot, groups` (Type 1 to start).
- **dim_time**: minute/hour/day/month keys (UTC).
- **fact_revert_label**: from history reconciliation. `wiki_db, rev_id, is_identity_reverted, reverting_rev_id, seconds_to_identity_revert, label_dt, snapshot, is_censored`.

## Truth-lag measure
`truth_lag = label_time - event_time`, where `event_time` = live `dt` (t0) and `label_time` = time the revert first becomes known (live `revision.revert` on the reverting edit, else History `t0 + seconds_to_identity_revert`).
Headline: **E(L)** = share of eventually-reverted revisions not yet flagged at wait *L* (1 - recall), on a log grid 1 min .. *H*.

## Reconciliation join
Live and History meet on **`(wiki_db, rev_id)`** (`revision.rev_id` in the stream = `revision_id` in History). Unmatched rows on either side go to a gap/mismatch table and are reported.

## Right-censoring
A snapshot only shows reverts up to its cutoff. Revisions newer than cutoff - *H* are censored: label them `is_censored`, exclude them from y, and use Kaplan-Meier for time-to-revert. The Aug 2026 probe (49.7% / 86.9% within 1 h / 48 h) is censored and is motivation, not a finding.

## Ingestion platform (KISS)
1. `ingest/collect_eventstreams.py`: Python SSE client, hourly ndjson, Last-Event-ID resume.
2. Monthly History download into raw (only two snapshots are kept upstream, so mirror on release).
3. PySpark (local mode) batch ETL: raw -> staging -> warehouse, SCD2 merge for `dim_page`.
4. Later options: Kafka/Redpanda between collector and ETL; Airflow scheduling; dbt marts and snapshots.

```mermaid
flowchart LR
  ES[EventStreams SSE] --> C[Python collector] --> R[(raw ndjson)]
  MH[MediaWiki History dump] --> R2[(raw TSV)]
  R --> S[PySpark staging]
  R2 --> S
  S --> W[(warehouse: fact_edit, dim_page SCD2, dim_user, dim_time)]
  S --> RC[reconcile on wiki_db, rev_id] --> FL[(fact_revert_label)]
  W --> M[E(L) / metrics]
  FL --> M
  C -. later .-> K[Kafka]
```

## Open decisions (TBD)
1. Which proposal tab was submitted Oct 1 (Tab 1 or Tab 3)?
2. Is capture running: since when, how many hosts, Cohort A replay? Second host?
3. Stability condition and *H* (Tab 3: 30 days), observation window, lag grid.
4. H1-H4 thresholds; is the prediction extension (W, grain, model) in?
5. Kafka vs Redpanda; Tab 3's MongoDB speed layer?
6. Warehouse engine; bitemporal vs plain SCD2; where Airflow and dbt run.
7. Do roles change from Tab 1?
8. Canvas dates for report, code, slides.
