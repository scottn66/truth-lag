# Truth Lag

SJSU DATA 226, Group 9: Scott, Tingyu, Wanru, Zhenni.

How long until live data tells the truth? We compare early Wikimedia EventStreams page signals with later MediaWiki History revert labels, joined on `(wiki_db, rev_id)`, and store pages in an SCD Type 2 warehouse.

## Layout
```
notebooks/00_access_points.ipynb   EventStreams, History dump, MediaWiki API, PySpark
docs/schema_and_warehouse.md       layers, star schema, truth-lag measure, open decisions
ingest/collect_eventstreams.py     SSE -> hourly ndjson collector
etl/  reconcile/                   (to come) PySpark ETL, live-to-history reconciliation
data/                              local only, git-ignored
```

## Quickstart
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python ingest/collect_eventstreams.py mediawiki.page_change.v1 data/raw   # Ctrl-C to stop; WIKI="" for all wikis
jupyter notebook notebooks/00_access_points.ipynb
```
PySpark needs Java 17+. Please don't commit data.
