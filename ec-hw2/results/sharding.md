# Sharding demo: results

Made by `ec-hw2/scaleout/demo_sharding.py` on 2026-10-24 08:11 UTC (data-v1). MongoDB 8.0.34.

All 4 servers run in Docker on one Mac. So the times here say nothing about real speed. The demo shows **how** MongoDB splits the data and the queries. SHARDING.md explains why we chose this shard key.

## 1. The cluster

| part | what it is |
|---|---|
| config server | replica set `cfgrs`, 1 member (`cfg:27019`) |
| shard `shard1rs` | `shard1rs/shard1:27018`, 1 member |
| shard `shard2rs` | `shard2rs/shard2:27018`, 1 member |
| router | `mongos`, published on the Mac as `127.0.0.1:27020` |

- Collection: `truthlag_sharded.revisions`.
- Shard key: `{"page.id": "hashed"}`.
- We sharded the collection while it was still **empty**. MongoDB then made the chunks on both shards first, and every document went straight to its shard.

## 2. The data spread

We copied **295,016** history-cohort documents from the local MongoDB (database `truthlag`, collection `revisions`) in batches of 5,000. The copy took 3.4 seconds (about 87,649 documents per second). Then we built the same 4 indexes as the local collection. The collection now has these indexes: `_id_`, `page.id_hashed`, `page.id_1_ts_1`, `user.id_1`, `history.reverted_1`, `cohort_1_ts_1` (shardCollection made `page.id_hashed`).

| shard | documents | share | data (MB) | indexes (MB) | chunks | orphaned documents |
|---|---:|---:|---:|---:|---:|---:|
| `shard1rs` | 147,462 | 49.98% | 91.3 | 13.6 | 1 | 0 |
| `shard2rs` | 147,554 | 50.02% | 91.4 | 13.6 | 1 | 0 |

Sources: documents and orphaned documents from `$shardedDataDistribution`; MB from `$collStats` (data = uncompressed BSON); chunks from `config.chunks`.

## 3. Which shards a query uses

- The page example is **List_of_2018_albums** (page id 54168882), the page with the most revisions: 261.
- The editor example is the bot ZackBot, with 8,635 revisions.

| query | explain shows | shards used | documents read, per shard | rows each shard sent to mongos | rows in the answer |
|---|---|---|---|---|---:|
| history of one page | `SINGLE_SHARD` | shard2rs | shard2rs: 261 | shard2rs: 261 | 261 |
| all edits of one editor | `SHARD_MERGE` | shard1rs, shard2rs | shard1rs: 4,307, shard2rs: 4,328 | shard1rs: 4,307, shard2rs: 4,328 | 8,635 |
| a range of page ids | `SHARD_MERGE` | shard1rs, shard2rs | shard1rs: 6,548, shard2rs: 6,600 | shard1rs: 6,548, shard2rs: 6,600 | 13,148 |
| revert rate by hour of day | both shards, merged by mongos | shard1rs, shard2rs | shard1rs: 147,462, shard2rs: 147,554 | shard1rs: 24, shard2rs: 24 | 24 |
| the 20 pages with the most revisions | both shards, merged by mongos | shard1rs, shard2rs | shard1rs: 147,462, shard2rs: 147,554 | shard1rs: 82,772, shard2rs: 82,643 | 20 |

"Documents read" is totalDocsExamined from explain('executionStats'). For a group-by, each shard sends one partial row per group to mongos.

The queries, as you would type them in mongosh, and what explain() shows:

1. **History of one page**: `db.revisions.find({"page.id": 54168882}).sort({ts: 1})`
   - Top stage `SINGLE_SHARD`. The plan on each shard: `shard2rs`: FETCH > IXSCAN (index `page.id_1_ts_1`).
2. **All edits of one editor**: `db.revisions.find({"user.id": 29639097})`
   - Top stage `SHARD_MERGE`. The plan on each shard: `shard1rs`: SHARDING_FILTER > FETCH > IXSCAN (index `user.id_1`); `shard2rs`: SHARDING_FILTER > FETCH > IXSCAN (index `user.id_1`).
3. **A range of page ids**: `db.revisions.find({"page.id": {$gte: 1000000, $lt: 2000000}})`
   - Top stage `SHARD_MERGE`. The plan on each shard: `shard1rs`: FETCH > SHARDING_FILTER > IXSCAN (index `page.id_1_ts_1`); `shard2rs`: FETCH > SHARDING_FILTER > IXSCAN (index `page.id_1_ts_1`).
4. **Revert rate by hour of day**: `db.revisions.aggregate([{$match: {cohort: "history"}}, {$group: {_id: "$hour_utc", edits: {$sum: 1}, reverted: {$sum: {$cond: ["$history.reverted", 1, 0]}}}}, {$sort: {_id: 1}}])`
   - mergeType `mongos`. Shard part of the pipeline: `$match, $group`. Merge part: `$mergeCursors, $group, $sort`.
   - The plan on each shard: `shard1rs`: GROUP > SHARDING_FILTER > FETCH > IXSCAN (index `cohort_1_ts_1`); `shard2rs`: GROUP > SHARDING_FILTER > FETCH > IXSCAN (index `cohort_1_ts_1`).
5. **The 20 pages with the most revisions**: `db.revisions.aggregate([{$group: {_id: "$page.id", n: {$sum: 1}}}, {$sort: {n: -1, _id: 1}}, {$limit: 20}])`
   - mergeType `mongos`. Shard part of the pipeline: `$group`. Merge part: `$mergeCursors, $group, $sort`.
   - The plan on each shard: `shard1rs`: GROUP > SHARDING_FILTER > COLLSCAN; `shard2rs`: GROUP > SHARDING_FILTER > COLLSCAN.

## 4. Checks

- OK: every copied document is in the sharded collection (295,016 in the sharded collection, 295,016 read from the local database).
- OK: the shards own all documents ($shardedDataDistribution) (295,016 owned).
- OK: no orphaned documents (no chunk moved during the load) (0 orphaned).
- OK: even spread: each shard owns 45%-55% of the documents (shard1rs 49.98%, shard2rs 50.02%).
- OK: routing of 'history of one page' is SINGLE_SHARD (SINGLE_SHARD).
- OK: routing of 'all edits of one editor' is SHARD_MERGE (SHARD_MERGE).
- OK: routing of 'a range of page ids' is SHARD_MERGE (SHARD_MERGE).
- OK: routing of 'revert rate by hour of day' is both shards (both shards, merged by mongos).
- OK: routing of 'the 20 pages with the most revisions' is both shards (both shards, merged by mongos).
- OK: every page is on one shard only (partial rows of the top-pages query = distinct pages) (165,415 partial rows, 165,415 distinct pages).
- OK: page history: same number of revisions as the local database (261 sharded, 261 local).
- OK: revert rate by hour: the same 24 rows as the local database (24 rows).

## 5. What this shows

1. Hashing `page.id` spreads the documents: 49.98% and 50.02%. There are 165,415 distinct pages. The biggest page has 261 revisions (0.09% of all documents), so no single page can make one shard much bigger than the other.
2. A query for one page goes to **one shard** (`SINGLE_SHARD`, `shard2rs`), and that shard reads only the 261 documents of the page. The history of a page and the score of one contested page work this way.
3. A query for one editor goes to **both shards** (`SHARD_MERGE`). An editor edits many pages, and the pages are on both shards. A range of page ids also goes to both shards (`SHARD_MERGE`), because hashing mixes up the order of the ids.
4. A group-by over all documents (by hour, or the top pages) runs on both shards. Each shard groups its own documents, then mongos merges the partial rows. For the top-20 pages, the shards sent 82,772 + 82,643 = 165,415 partial rows to mongos, and mongos kept 20. 165,415 is also the number of distinct pages, so no page is split over the 2 shards. Even so, mongos runs a `$group` again in the merge part: MongoDB does not use the fact that each page is on one shard.

## How to run it again

See `ec-hw2/scaleout/SHARDING.md`, section "Run the demo". The script drops and rebuilds `truthlag_sharded` every time, so a re-run gives the same numbers (only the times change).
