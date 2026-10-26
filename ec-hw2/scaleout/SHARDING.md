# Sharding: our shard key and the demo

**Spec item:** section 3, "Scale-out: Atlas free tier (M0) + documented sharding key choice (`page.id` hashed), demo or explain if M0 limits".

**Short answer:** We shard the `revisions` collection on `{"page.id": "hashed"}`. The Atlas free tier cannot be sharded, so we show it on Scott's Mac, with 2 shards in Docker. The results are in [`results/sharding.md`](../results/sharding.md).

Words used on this page (see also `GLOSSARY.md`):
- **shard**: one server (here, a replica set with 1 member) that holds part of a collection.
- **mongos**: the router. Programs connect to it, and it sends each query to the right shards.
- **config server**: it stores which chunk is on which shard.
- **chunk**: a range of shard-key values. Each chunk lives on one shard.
- **SINGLE_SHARD / SHARD_MERGE**: the top stage in `explain()` on mongos. SINGLE_SHARD means mongos asked one shard. SHARD_MERGE means mongos asked several shards and merged their answers.

---

## 1. Why `{"page.id": "hashed"}`

A good shard key has many different values, spreads the writes, and lets the common queries go to one shard. Here is how `page.id` does on our data (history cohort, data-v1; numbers from `results/sharding.md`).

1. **Many distinct pages.** The history cohort has 295,016 revisions on 165,415 distinct pages. The biggest page (List_of_2018_albums) has only 261 revisions, which is 0.09% of all documents. So no single page can make one shard much bigger than the others.
2. **An even spread from hashing.** MongoDB hashes the page id into a random-looking number and splits those numbers into chunks. In the demo, shard 1 got 147,462 documents (49.98%) and shard 2 got 147,554 (50.02%).
3. **Page queries go to one shard.** All revisions of one page have the same shard key, so they are on the same shard.
   - The history of one page, `find({"page.id": X}).sort({ts: 1})`, is `SINGLE_SHARD` in the demo. That shard reads only the 261 documents of the page (with the `page.id_1_ts_1` index).
   - Contested pages (Mongo Q2) count edits and reverts per page. Each page's documents are on one shard, so each shard can count its own pages completely. In the demo, the 2 shards sent 82,772 + 82,643 = 165,415 partial rows for a group by page: exactly the number of pages, so no page is split.
4. **No hot spot from a growing key.** `ts` and `rev_id` grow all the time. With a range key on `ts` or `rev_id`, every new edit goes to the last chunk, so one shard takes all the writes. The live stream brings about 3,900 new revisions per hour (`live_revisions` in report/FACTS.md, over 72 hours). A hashed page id sends each new edit to a random-looking place, so both shards share the writes.
5. **Upserts include `page.id`.** In a sharded collection, an upsert must have the full shard key in its filter. Every revision document and every stream event already has the page id. So a loader can always write `{_id: "enwiki:<rev_id>", "page.id": <page_id>}` as the filter, and mongos sends the write to one shard.

Keys we did not choose:

| key | why not |
|---|---|
| `{ts: 1}` or `{rev_id: 1}` (range) | Every new edit goes to the newest chunk: one shard gets all the writes (point 4). |
| `{_id: "hashed"}` | The spread is even, but the history of one page is then on every shard, so page queries go to all shards. |
| `{"user.id": ...}` | Some editors are huge: the bot ZackBot made 8,635 of the 295,016 history revisions (2.9%). The top 3 bots made 20,314. Also, page queries would go to all shards. |
| `{"page.id": 1}` (range, not hashed) | New articles get new, high page ids and many edits, so most writes go to the last chunk. We never need ranges of page ids, so hashing costs us nothing there. |

## 2. The trade-off: some queries go to every shard

- **By hour or by user.** A query that does not filter on `page.id` must ask every shard.
  - `find({"user.id": Y})` for one editor is `SHARD_MERGE`: in the demo, shard 1 read 4,307 documents and shard 2 read 4,328.
  - The revert rate by hour of day (like Mongo Q1) reads all 295,016 documents on the 2 shards. Each shard sends 24 partial rows, and mongos adds them up.
- **Ranges of page ids.** Hashing mixes up the order of the ids, so `{"page.id": {$gte: A, $lt: B}}` is `SHARD_MERGE` too.
- **Rankings over all pages.** A top-20 list (like Mongo Q2) also asks every shard. Each shard sends one partial row per page (165,415 in total), and mongos sorts them and keeps 20. MongoDB 8.0 even runs a `$group` again on mongos, although no page is split.
- This is fine for us. Our questions are about pages (contested pages, the history of a page, Truth Lag per page). With more shards, each shard has less data to read for the all-shard queries, but every shard must answer them.
- `revert_links` (19,858 history documents) is small. We would leave it unsharded, on one shard. `$lookup` from a sharded collection into it works in MongoDB 8.0.

## 3. What does not work on the Atlas free tier (M0)

- **No sharding.** M0 is one small replica set. `sh.enableSharding` and `sh.shardCollection` are not allowed.
- **`db.collection.getShardDistribution()` is not supported**, and neither is `sh.status()`: there is no mongos and there are no shards. `$shardedDataDistribution` does not work either.
- **Sharding starts at the M30 tier** (a paid, dedicated cluster). That is far outside a class budget.
- The free tier also has a 512 MB limit. Our Atlas copy is estimated at `atlas_estimate_mb` in report/FACTS.md, well under the limit (`load_mongo.py --target atlas --estimate-only`).

So Atlas holds the hosted copy for Data Explorer and Charts, and the Docker cluster on the Mac shows the sharding.

## 4. Run the demo (Scott's Mac, about 5 minutes)

The cluster is a separate compose project, `truthlag-sharded`, with its own volumes: `truthlag-sharded_cfg_data`, `truthlag-sharded_shard1_data` and `truthlag-sharded_shard2_data`. It never touches the main project's volumes (`truthlag_mongo_data`, `truthlag_neo4j_data`).

| server | replica set | port | memory limit | WiredTiger cache |
|---|---|---|---|---|
| `cfg` (config server) | `cfgrs` | 27019 (inside Docker) | 600 MB | 0.25 GB |
| `shard1` | `shard1rs` | 27018 (inside Docker) | 600 MB | 0.25 GB |
| `shard2` | `shard2rs` | 27018 (inside Docker) | 600 MB | 0.25 GB |
| `mongos` (router) | none | 27017 inside, **127.0.0.1:27020** on the Mac | 256 MB | none |

**Memory rule.** Colima has 6 GB. Neo4j uses about 2.3 GB, so stop it while the cluster runs. Only stop it: never remove it.

Run every command from the repo folder (`cd ~/Desktop/226/truth-lag`). The main MongoDB must be running, because the demo copies from it.

1. Stop Neo4j (about 10 seconds).
   ```
   docker stop truthlag-neo4j-1
   ```
   You should see: `truthlag-neo4j-1`.
2. Start the sharded cluster (a few seconds; the first time it may download `mongo:8.0`).
   ```
   docker compose -f ec-hw2/scaleout/docker-compose.sharded.yml up -d
   ```
   You should see 4 lines that end in `Started`: `truthlag-sharded-cfg-1`, `-shard1-1`, `-shard2-1` and `-mongos-1`.
3. Set up the replica sets and the shards (about 30 seconds the first time). It is safe to run it again.
   ```
   bash ec-hw2/scaleout/init_sharded.sh
   ```
   You should see `cfgrs: PRIMARY`, `shard1rs: PRIMARY`, `shard2rs: PRIMARY`, then `shard1rs: added`, `shard2rs: added` and `shards: shard1rs=shard1rs/shard1:27018, shard2rs=shard2rs/shard2:27018`. The second time, the lines say `already initiated` and `already a shard`.
4. Run the demo (about 10 seconds).
   ```
   .venv/bin/python ec-hw2/scaleout/demo_sharding.py
   ```
   You should see `copied 295,016 history documents`, the 5 query lines (`SINGLE_SHARD on shard2rs`, then `SHARD_MERGE` and `both shards` for the others), 12 lines that start with `check: OK`, and `wrote .../ec-hw2/results/sharding.md`.
   For a quick test, add `--limit 20000`. Then the page goes to `data/logs/sharding_test.md`, and `results/sharding.md` is not changed.
5. Start Neo4j again.
   ```
   docker start truthlag-neo4j-1
   ```
6. Stop the sharded cluster (about 10 seconds). Use `stop`, never `down -v`.
   ```
   docker compose -f ec-hw2/scaleout/docker-compose.sharded.yml stop
   ```
   You should see 4 lines that end in `Stopped`. Later, `docker ps -a` may list mongos as `Exited (137)`: Docker forced it to stop after 10 seconds. That is harmless, because mongos keeps no data.
7. Open [`results/sharding.md`](../results/sharding.md) and check the numbers: 2 shards with about 50% each, 0 orphaned documents, and every check `OK`.

**Optional: look at it in mongosh.** While the cluster runs, you can open mongosh **inside the cfg container**:
```
docker compose -f ec-hw2/scaleout/docker-compose.sharded.yml exec cfg mongosh "mongodb://mongos:27017/truthlag_sharded"
```
Then type `db.revisions.getShardDistribution()`. You should see `docs: 147462` on one shard, `docs: 147554` on the other, and `50.02 % data` / `49.97 % data` in the totals. `db.revisions.find({"page.id": 54168882}).explain().queryPlanner.winningPlan.stage` prints `SINGLE_SHARD`.

Do **not** start mongosh inside the shard or mongos containers. mongosh needs about 150 MB. A loaded shard already uses about 460 to 520 MB of its 600 MB, so Docker kills the shard server when the limit is reached. This happened once during the build (shard1 stopped, and `docker compose ... up -d` started it again with its data). `init_sharded.sh` always runs mongosh in the cfg container for this reason.

## 5. If something goes wrong

| message | what to do |
|---|---|
| `STOP: cannot reach the sharded cluster at config.SHARDED_URI` | Do steps 2 and 3. Check that `SHARDED_URI` in `ec-hw2/.env` is `mongodb://localhost:27020`. |
| `STOP: the container 'shard1' is not running` | Do step 1, then step 2 (it starts only the missing containers), then step 3. |
| `STOP: config.SHARDED_URI is not a mongos router` | `SHARDED_URI` points to a normal MongoDB. The script stops before it changes anything. Fix `ec-hw2/.env`. |
| `STOP: the cluster has 0 shard(s), it needs 2` | Run step 3. |
| `WARNING: truthlag-neo4j-1 is running` | Stop it (step 1) before the demo, to keep enough memory. |
| a `check:` line says `DIFFERENT` | Do not use the numbers. Run step 4 again; if it is still `DIFFERENT`, tell Scott. |

`.venv/bin/python ec-hw2/load_mongo.py --target sharded` only checks the connection. It prints the MongoDB version and the shard names.

## 6. Files

| file | what it does |
|---|---|
| `scaleout/docker-compose.sharded.yml` | the 4 servers (compose project `truthlag-sharded`) |
| `scaleout/init_sharded.sh` | `rs.initiate` for the 3 replica sets, waits for a primary, then `sh.addShard` twice |
| `scaleout/demo_sharding.py` | drops and recreates `truthlag_sharded`, shards the empty collection, copies the history cohort, records the spread and `explain()`, writes the results |
| `results/sharding.md` | the results, with all numbers and explain stage names |
| `results/_SUCCESS_sharding.json` | the row counts and the check results of the last run |
| `tests/test_scaleout.py` | tests without a database: `.venv/bin/python -m pytest ec-hw2/tests/test_scaleout.py -q` |
