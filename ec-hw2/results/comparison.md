# Three-engine comparison: MongoDB, Neo4j and SQLite

**Timing label: final.** Load average (1 / 5 / 15 min): 1.91 / 2.33 / 2.81 at the start and 2.51 / 2.44 / 2.84 at the end. `--final` runs only when the 1-minute load average is at most 2.0.

Made by `ec-hw2/comparison/compare.py` on 2026-10-27 22:57 UTC (data-v2). Full tables: `comparison.csv` (the 6 compared rows) and `comparison_extra.csv` (the extra row). Both questions use the history cohort and the shared definitions in `DATA_MODEL.md` section 7.

## Results

| question | engine | lines of code | code characters | median ms | min-max ms | same result? | modeling note |
|---|---|---:|---:|---:|---:|---|---|
| top contested pages | MongoDB | 62 | 1,040 | 71.5 | 67.7-73.3 | yes | 12 stages: group the links per page and keep pages with 2+ reverted editors; then a $lookup into revisions counts the human edits of the 1,357 kept pages only. |
| top contested pages | Neo4j | 18 | 768 | 106.2 | 100.4-130.9 | yes | Two MATCH steps: the first filters all 295,013 EDITED relationships on the revert flags (there is no separate revert-link table), the second counts the edits of the 1,357 kept pages only. |
| top contested pages | SQLite | 38 | 1,224 | 33.4 | 28.8-53.7 | yes | GROUP BY with HAVING, then one correlated COUNT per kept page (the 1,357 kept pages); the score is 1.0 * a / b to avoid whole-number division. |
| mutual reverts | MongoDB | 52 | 884 | 127.2 | 121.7-133.6 | yes | The reverse direction needs a self-$lookup with let and $expr, run once per a < b triple (4,229 times). |
| mutual reverts | Neo4j | 6 | 275 | 41.0 | 33.9-64.1 | yes | The pattern (a)-[:REVERTED]->(b)-[:REVERTED]->(a) is one line, but it needs page_id on all 13,269 REVERTED relationships. |
| mutual reverts | SQLite | 13 | 412 | 23.1 | 17.9-26.8 | yes | A CTE of (reverter, author, page) triples is joined to itself with the roles swapped. |
| mutual reverts | SQLite, pre-aggregated input (extra row, not compared) | 5 | 188 | 1.7 | 1.5-3.5 | yes (same rows as the SQLite raw-link query) | The same self-join as the SQLite query, on the pre-aggregated TEMP table. |

**Speed.** We call an engine faster only when its min-max range does not overlap the other engine's range.

- top contested pages: MongoDB is faster than Neo4j (67.7-73.3 ms vs 100.4-130.9 ms; the ranges do not overlap).
- top contested pages: SQLite is faster than MongoDB (28.8-53.7 ms vs 67.7-73.3 ms; the ranges do not overlap).
- top contested pages: SQLite is faster than Neo4j (28.8-53.7 ms vs 100.4-130.9 ms; the ranges do not overlap).
- mutual reverts: Neo4j is faster than MongoDB (33.9-64.1 ms vs 121.7-133.6 ms; the ranges do not overlap).
- mutual reverts: SQLite is faster than MongoDB (17.9-26.8 ms vs 121.7-133.6 ms; the ranges do not overlap).
- mutual reverts: SQLite is faster than Neo4j (17.9-26.8 ms vs 33.9-64.1 ms; the ranges do not overlap).
- mutual reverts, extra row: SQLite, pre-aggregated input is faster than Neo4j (1.5-3.5 ms vs 33.9-64.1 ms; the ranges do not overlap).

## What each timed query reads

- **Neo4j, mutual reverts:** Reads the REVERTED relationships that export_graph.py pre-aggregated (one per reverter, reverted editor and page, with count); that grouping is NOT inside the timed query. In MongoDB, the export_graph.py step that builds these relationships took 0.09 s (from `_SUCCESS_export_graph.json`). MongoDB and SQLite do this grouping inside the timed query, so the Neo4j time is not like for like.
- **Extra row:** `queries/sql/compare_mutual_reverts_preaggregated.sql` gives SQLite the same head start. It builds the grouped triples once as a TEMP table in memory (19.0 ms, not timed; 15 lines of setup code), then times only the self-join. Its result is compared with the SQLite raw-link result: yes (same rows as the SQLite raw-link query).
- **MongoDB:** revert_links holds 38,216 documents (19,858 history, 18,358 live) and revisions holds 574,482 documents (295,016 history). Both pipelines start with $match cohort = 'history', so the live documents are filtered out inside the timed query.
  - top contested pages: query plan of the first $match: IXSCAN on index cohort_1_page_id_1, 19,858 documents examined; median 69.3 ms with this default plan and 65.9 ms with a forced collection scan (hint {$natural: 1}, 7 runs each, helper runs).
  - mutual reverts: query plan of the first $match: IXSCAN on index cohort_1_page_id_1, 19,858 documents examined; median 127.3 ms with this default plan and 126.6 ms with a forced collection scan (hint {$natural: 1}, 7 runs each, helper runs).
- **SQLite and Neo4j** hold the history cohort only.

## Modeling pain (1 = easy, 5 = hard)

Scored by: draft by Claude Code; Comparison+viz owner to re-score. The scores and reasons come from `comparison/pain.csv`. They are not the team's judgment until the Comparison+viz owner re-scores them in that file and writes their name in scored_by.

| question | engine | pain | reason | scored by |
|---|---|---:|---|---|
| top contested pages | MongoDB | 3 | Two collections: a $lookup sub-pipeline counts the human edits, and each distinct count needs $addToSet and then $size. | draft by Claude Code; Comparison+viz owner to re-score |
| top contested pages | Neo4j | 3 | The revert facts are on the EDITED relationships only because the export copied them there; the query needs two MATCH steps and a CASE inside count(). | draft by Claude Code; Comparison+viz owner to re-score |
| top contested pages | SQLite | 2 | Plain GROUP BY with HAVING and a correlated COUNT, but a plain join made SQLite scan all revisions, and the float division (1.0 * a / b) needs care. | draft by Claude Code; Comparison+viz owner to re-score |
| mutual reverts | MongoDB | 4 | The longest query: a self-$lookup with let variables, and its inner $match repeats the outer filter. | draft by Claude Code; Comparison+viz owner to re-score |
| mutual reverts | Neo4j | 2 | The query is short, but the loader first had to build one REVERTED relationship per editor pair and page. | draft by Claude Code; Comparison+viz owner to re-score |
| mutual reverts | SQLite | 2 | Short, but the swapped join condition (r.a = f.b AND r.b = f.a) is easy to get wrong. | draft by Claude Code; Comparison+viz owner to re-score |

## Candidate findings for 'Comparison top 5'

Facts with numbers only. The Comparison+viz owner turns them into findings in their own words.

- Top contested pages: the outputs are identical in MongoDB, Neo4j and SQLite (20 rows, in order, scores to 6 digits). Rank 1 is page 11383948 (Personality_and_image_of_Elizabeth_II): 13 revert actions / 14 human edits = 0.928571.
- Top contested pages, step 1 keeps 1,357 pages with 2+ reverted editors; all 3 engines count the human edits for these pages only.
- 5 of the top 20 pages share a score with another page (scores 0.714286, 0.600000). The tie order uses revert_actions, then edits, then page_id, in all 3 engines.
- Mutual reverts: the outputs are identical in the 3 engines: 462 pairs on 397 pages, with 631 distinct editors; 25 pairs include a bot.
- 18 of the top 20 contested pages have at least one mutual pair; together they hold 51 of the 462 pairs.
- Query size (code characters without spaces / lines of code): top contested pages: MongoDB 1,040 characters / 62 lines, Neo4j 768 characters / 18 lines, SQLite 1,224 characters / 38 lines; mutual reverts: MongoDB 884 characters / 52 lines, Neo4j 275 characters / 6 lines, SQLite 412 characters / 13 lines. Line counts depend on the layout: 40 of the 114 MongoDB lines hold only brackets or commas.
- Median time in ms with the min-max range (final, 1 warm-up, then 3 rounds of 7 timed runs (21 runs per query)): top contested pages: MongoDB 71.5 (67.7-73.3), Neo4j 106.2 (100.4-130.9), SQLite 33.4 (28.8-53.7); mutual reverts: MongoDB 127.2 (121.7-133.6), Neo4j 41.0 (33.9-64.1), SQLite 23.1 (17.9-26.8).
- Speed, top contested pages: MongoDB is faster than Neo4j (67.7-73.3 ms vs 100.4-130.9 ms; the ranges do not overlap). SQLite is faster than MongoDB (28.8-53.7 ms vs 67.7-73.3 ms; the ranges do not overlap). SQLite is faster than Neo4j (28.8-53.7 ms vs 100.4-130.9 ms; the ranges do not overlap).
- Speed, mutual reverts: Neo4j is faster than MongoDB (33.9-64.1 ms vs 121.7-133.6 ms; the ranges do not overlap). SQLite is faster than MongoDB (17.9-26.8 ms vs 121.7-133.6 ms; the ranges do not overlap). SQLite is faster than Neo4j (17.9-26.8 ms vs 33.9-64.1 ms; the ranges do not overlap).
- Mutual reverts on pre-aggregated input (extra row): SQLite takes 1.7 ms (1.5-3.5) when it reads triples grouped beforehand, against 23.1 ms (17.9-26.8) on the raw revert links; Neo4j, which reads the REVERTED relationships grouped by export_graph.py, takes 41.0 ms (33.9-64.1). Building the TEMP table took 19.0 ms (not timed).
- Input sizes: SQLite revert_links has 19,858 rows (17,868 pass within_followup and by_other), which make 13,269 (reverter, author, page) triples; 4,229 of them have a < b, so the MongoDB self-$lookup runs 4,229 times. MongoDB revert_links has 38,216 documents (19,858 history). Neo4j has 13,269 REVERTED relationships and 295,013 EDITED relationships.
- MongoDB first $match (cohort = 'history'): top contested pages: IXSCAN cohort_1_page_id_1, 19,858 documents examined, median 69.3 ms with the default plan (the index exists) vs 65.9 ms with a forced collection scan; mutual reverts: IXSCAN cohort_1_page_id_1, 19,858 documents examined, median 127.3 ms with the default plan (the index exists) vs 126.6 ms with a forced collection scan.
- 3 history revisions have no editor key (pages 87880, 20197943, 84167596). SQLite and MongoDB count them as human edits; Neo4j has no EDITED relationship for them. None of these pages is in the top 20.

## How we measured

1. **Same result?** We compare the full ordered list. Top contested pages: (page_id, score rounded to 6 digits), as `config.py` says. We also compare edits, revert_actions, reverted_editors and contested, and the 3 top-contested queries must return the same columns. No query computes a rank: `run_mongo.py`, `run_cypher.py` and `run_sql.py` add it in Python, so it is not timed in any engine. Mutual reverts: (page_id, a, b, a_reverted_b, b_reverted_a). Neo4j shows aliases, so we turn them back into editor keys with the graph's own key/alias map. "yes" means equal to both other engines.
2. **Time.** 1 warm-up, then 3 rounds of 7 timed runs (21 runs per query). The engines take turns, and the order changes after every run. The time runs in Python from sending the query until every row is in memory, so it includes the network hop and decoding for MongoDB and Neo4j. We report the median and the min-max range of all timed runs; `comparison.csv` also has the median of each round (round_medians_ms). We call an engine faster only when the ranges do not overlap. This file and `comparison.csv` are the one timing source for the comparison; the times in the `results/mongo_*`, `cypher_*` and `sql_*` files are single-engine runs, not for the comparison.
3. **Query size.** Lines of code are non-blank lines that are not comments; code characters are the characters without spaces. MongoDB: the "pipeline" array in the JSON file, as `run_mongo.py` writes it. Neo4j: the "main" statement only (Cypher Q1 also has a "total" statement, which is not counted). SQLite: the whole statement, with its params block. Line counts depend on the layout (the CSV column bracket_only_lines counts lines with only brackets or commas), so read both numbers together.
4. **Where the engines run.** MongoDB and Neo4j run in Docker in a Colima VM. SQLite runs inside the Python process on the host, with no network hop. So the times compare whole setups, not only the database engines.
5. **Modeling pain** is a draft until the owner re-scores it (see above). The numbers in the modeling notes come from this run.

## Machine

| item | value |
|---|---|
| macOS | 27.0.1 (arm64) |
| CPU (host) | Apple M5, 10 cores (4 performance + 6 efficiency) |
| RAM (host) | 16.0 GiB |
| Colima VM (MongoDB + Neo4j) | 4 CPUs, 5.8 GiB RAM, Ubuntu 24.04.4 LTS |
| MongoDB container memory limit | 1.5 GiB |
| Neo4j container memory limit | 3.0 GiB |
| MongoDB version | 8.0.34 |
| MongoDB WiredTiger cache | 1.0 GiB |
| Neo4j version | 2026.10.1 community |
| Neo4j memory | heap 1.46GiB, page cache 1.00GiB |
| SQLite version | 3.53.1 (in the Python process on the host) |
| Python and drivers | Python 3.12.13, pymongo 4.19.0, neo4j driver 6.4.1 |
| load average (1 / 5 / 15 min), start | 1.91 / 2.33 / 2.81 |
| load average (1 / 5 / 15 min), end | 2.51 / 2.44 / 2.84 |
| --final load threshold (1 min) | 2.0 |

## Query files

- top contested pages: MongoDB `queries/mongo/q2_top_contested_pages.json`, Neo4j `queries/cypher/compare_top_contested.cypher`, SQLite `queries/sql/compare_top_contested.sql`
- mutual reverts: MongoDB `queries/mongo/compare_mutual_reverts.json`, Neo4j `queries/cypher/q1_mutual_reverts.cypher`, SQLite `queries/sql/compare_mutual_reverts.sql`
- extra row: `queries/sql/compare_mutual_reverts_preaggregated.sql`
