# Neo4j screenshots: 4 graph pictures and 5 query tables

**Who:** the Neo4j owner.
**Time:** about 45 minutes (Mon 2026-10-26 20:00 PT at the latest).
**Spec item:** section 4, "Viz: Neo4j Browser/Bloom screenshots".
**Tool:** Neo4j Browser. Bloom is not available in the Community edition that runs in our Docker container. In the report, write: "Neo4j Browser (Bloom needs Neo4j Desktop or Aura)".

What you get at the end: 9 PNG files in `ec-hw2/results/figures/` (10 with the optional one).

| file | what it shows |
|---|---|
| `neo4j_schema.png` | the graph model: `CALL db.schema.visualization()` |
| `neo4j_mutual_reverts.png` | mutual-revert pairs (edit wars) |
| `neo4j_contested_page.png` | one contested page with its editors and their reverts |
| `neo4j_largest_community.png` | the largest Louvain community of reverts (optional: `neo4j_largest_community_humans.png`, the same without the bot) |
| `neo4j_cypher_q1_table.png` to `neo4j_cypher_q5_table.png` | the table result of each Cypher query Q1 to Q5 |

**Privacy rule:** human editors appear only by their pseudonym (`alias`: `editor_` + 10 hex digits, such as `editor_7f3a2b1c9d`). Bots keep their real names (`ClueBot NG`). Page titles are fine. Never show the `key` property (it holds a user id or a temporary account name), and never take a screenshot while the property panel of an editor is open.

**Check numbers.** Names such as `cypher_q1_mutual_pairs` below are keys of `report/FACTS.md`. Look up the value there. The full expected tables are in `ec-hw2/results/cypher_*.md`.

---

## Part A: open Neo4j Browser and log in (about 5 minutes)

1. **Choose where to run it.**
   - **On Scott's Mac (best, with screen sharing).** Neo4j runs in Docker there, with the full graph and the GDS plugin. Scott opens http://localhost:7474 in Chrome and shares the screen (Zoom, Meet or Teams); you say what to click, or Scott gives you remote control.
   - **On your own laptop, with Neo4j Desktop.** Use the 4 CSV files and `queries/cypher/load.cypher` (see `README.md`, section 4, "Way 2").
   - **On Aura Free, with the contested subset.** Scott loads it with `.venv/bin/python ec-hw2/load_neo4j.py --target aura --subset contested --confirm-overwrite`. Aura Free has no GDS inside the database. So Cypher Q2 and Q3 and the community picture (step 10) only work on Scott's Mac or in Neo4j Desktop.
2. **Log in.** In the connect form, use:
   - Connect URL: `neo4j://localhost:7687` (or `bolt://localhost:7687`)
   - Database user: `neo4j`
   - Password: the value of `NEO4J_PASSWORD` in `ec-hw2/.env`. Scott types it himself; it must never be on a shared screen, in the chat or in a screenshot.
   You should see the query editor at the top and the database information (node labels `Editor` and `Page`, relationship types `EDITED` and `REVERTED`).
3. **Check the graph.** Paste this into the editor and press Ctrl+Enter (Mac: Cmd+Enter), or click the run button:
   ```
   MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes
   ```
   You should see `Editor` with `neo4j_editor_count` nodes and `Page` with `neo4j_page_count` nodes. If the counts are 0, the graph is not loaded: ask Scott to run `.venv/bin/python ec-hw2/load_neo4j.py --target local`.
4. **Set the query parameters once** (the Cypher files use them):
   ```
   :params {top_n: 20, contested_min_edits: 10, contested_min_editors: 2, contested_min_actions: 2, contested_min_score: 0.2}
   ```
   You should see the 5 parameters listed.

## Part B: the style (once, about 5 minutes)

Do this **before** the first graph screenshot, so no node shows its `key`.

5. Run the schema query of step 7 (or any query that returns nodes). The graph view opens.
6. In the "Results overview" panel on the right, click the label **Editor**. In the style panel, set the **Caption** to `alias`. Then click **Page** and set its Caption to `title`. Optional: give Editor and Page two clear colours, and set the caption of the relationship `REVERTED` to `count`.
   You should see editor nodes with names such as `editor_7f3a2b1c9d` or `ClueBot NG`, and page nodes with titles. No node may show `u:...` or `t:...`.
   Browser remembers the style in your browser, so you do this only once.

## Part C: the 4 graph screenshots (about 15 minutes)

For each picture:
1. Run the query.
2. Switch to the **Graph** view.
3. Drag the nodes a little, so the picture is clear.
4. Take the screenshot. On a Mac, press Cmd+Shift+4 and drag over the area; on Windows, press Win+Shift+S.

Each query returns paths with `LIMIT 50` or `LIMIT 100`, so the picture stays readable.

7. **The graph model** → `neo4j_schema.png`
   ```
   CALL db.schema.visualization()
   ```
   You should see 2 nodes, `Editor` and `Page`, an `EDITED` arrow from Editor to Page, and a `REVERTED` arrow from Editor back to Editor.
8. **Mutual-revert pairs (Cypher Q1 as a picture)** → `neo4j_mutual_reverts.png`
   ```
   MATCH path = (a:Editor)-[r1:REVERTED]->(b:Editor)-[r2:REVERTED]->(a)
   WHERE r1.page_id = r2.page_id AND a.key < b.key
   RETURN path
   LIMIT 50
   ```
   You should see editor nodes in small groups. Each pair is joined by 2 arrows that point in opposite directions. In total there are `cypher_q1_mutual_pairs` mutual pairs on `cypher_q1_pages` pages; the picture shows the first 50.
9. **One contested page with its editors** → `neo4j_contested_page.png`
   ```
   MATCH (p:Page {contested: true})
   WITH p ORDER BY p.revert_actions DESC, p.id ASC LIMIT 1
   MATCH ed = (:Editor)-[:EDITED]->(p)
   WITH p, collect(ed) AS edits
   OPTIONAL MATCH rv = (:Editor)-[r:REVERTED]->(:Editor)
   WHERE r.page_id = p.id
   RETURN p.title AS page, edits, collect(rv) AS reverts
   ```
   You should see the contested page with the most revert actions in the middle (in data-v1: `PB&J_Otter`). Its editors are around it, with `EDITED` arrows to the page and `REVERTED` arrows between the editors.
10. **The largest Louvain community** → `neo4j_largest_community.png`
    First check that the communities exist (Cypher Q3 writes `communityId`):
    ```
    MATCH (e:Editor) WHERE e.communityId IS NOT NULL RETURN count(e) AS editors_with_community
    ```
    If it shows 0, run Cypher Q3 first (Part D, step 12). Then:
    ```
    MATCH (e:Editor) WHERE e.communityId IS NOT NULL
    WITH e.communityId AS community, count(*) AS editors
    ORDER BY editors DESC, community ASC LIMIT 1
    MATCH path = (a:Editor {communityId: community})-[:REVERTED]->(b:Editor {communityId: community})
    RETURN path
    LIMIT 100
    ```
    You should see a star: one patroller in the middle (in data-v1, the bot `ClueBot NG`) with arrows to the editors it reverted. The community has `cypher_q3_largest_community_editors` editors. The share of its `REVERTED` relationships that touch the top editor (the "star share") is in `ec-hw2/results/cypher_q3_conflict_communities.md`. The picture shows the first 100 relationships. The community number is an internal id and can change after a new load.

    Optional, a second picture without the bot → `neo4j_largest_community_humans.png`: run the same query with one more line, `WHERE a.kind <> 'bot'`, right after the second `MATCH` line. You should see several small groups of human editors.

## Part D: the 5 query tables (about 15 minutes)

The query files are in `ec-hw2/queries/cypher/`. Each file has comments (`//`) and one or more statements that end with `;`. The statement for the screenshot follows the line `// result: main`.

11. For each file:
    1. Copy **one statement at a time** (from its first line to its `;`).
    2. Paste it into the editor and run it.
    3. Switch the result to the **Table** view.
    4. Take the screenshot of the table with the query above it.
12. Run the statements in this order:

    | Cypher query | file | run these statements, in order | screenshot | you should see (keys of report/FACTS.md) |
    |---|---|---|---|---|
    | Q1 mutual-revert pairs | `q1_mutual_reverts.cypher` | `result: main` (optional: `result: total`) | `neo4j_cypher_q1_table.png` | `cypher_q1_mutual_pairs` rows; the first row is the first row of `results/cypher_q1_mutual_reverts.md`. `total`: `cypher_q1_mutual_pairs` pairs, `cypher_q1_pages` pages, `cypher_q1_editors` editors, `cypher_q1_pairs_with_bot` pairs with a bot. |
    | Q2 central reverters | `q2_central_reverters.cypher` | 1. the `gds.graph.drop` statement, 2. the `gds.graph.project` statement, 3. `result: main`, 4. the last `gds.graph.drop` | `neo4j_cypher_q2_table.png` | 20 rows. The first is `cypher_q2_top_pagerank_editor`, with PageRank `cypher_q2_top_pagerank`. PageRank here means: this editor reverts editors who are themselves active reverters. The list "who reverts the most" is the `by_degree` result (`results/cypher_q2_central_reverters_by_degree.md`). |
    | Q3 conflict communities | `q3_conflict_communities.cypher` | 1. drop, 2. project, 3. `result: louvain_stats` (it writes `communityId`), 4. `result: main`, 5. the last drop | `neo4j_cypher_q3_table.png` | `louvain_stats`: `cypher_q3_louvain_communities` communities, modularity `cypher_q3_louvain_modularity`. Most communities are one editor with no revert; the number with 2 or more editors is in `results/cypher_q3_conflict_communities.md`. `main`: 10 rows; rank 1 has `cypher_q3_largest_community_editors` editors. |
    | Q4 pages with the most warring editors | `q4_pages_most_warring_editors.cypher` | `result: main` | `neo4j_cypher_q4_table.png` | 20 rows. The first: `cypher_q4_top_page_title`, `cypher_q4_top_page_warring_editors` warring editors, `cypher_q4_top_page_mutual_pairs` mutual pairs. |
    | Q5 2-hop through contested pages | `q5_two_hop_contested.cypher` | `result: main` | `neo4j_cypher_q5_table.png` | 20 rows. The first pair shares `cypher_q5_top_pair_shared_pages` contested pages; its aliases are in the first row of `results/cypher_q5_two_hop_contested.md`. |

    The full expected tables are in `ec-hw2/results/cypher_q1_mutual_reverts.md` to `cypher_q5_two_hop_contested.md`. The Louvain numbers can differ a little after a new load (see the comment at the top of the Q3 file).
13. Check every table: the editor columns show only aliases (`editor_...`) and bot names. If you see `u:` or `t:`, do not use the screenshot.

## Part E: upload (about 5 minutes)

14. Upload the 9 PNG files yourself, so they carry your name:
    1. Open https://github.com/scottn66/truth-lag and switch the branch to `ec-hw2`.
    2. Open `ec-hw2/results/figures/`, click "Add file" > "Upload files", and drag the files in.
    3. Write the message `Add Neo4j Browser screenshots`.
    4. Choose "Commit directly to the ec-hw2 branch" and click "Commit changes".
    You should see the 9 files in the folder.

## If something goes wrong

| problem | what to do |
|---|---|
| the page http://localhost:7474 does not open | Neo4j is stopped. Scott runs `docker start truthlag-neo4j-1` (it is stopped while the sharding demo runs). |
| "Expected parameter(s): top_n" | Run the `:params` line of step 4 again. |
| "There is no procedure with the name gds..." | GDS is missing (for example on Aura Free). Use Scott's Mac. |
| "A graph with name 'cypher_q2_reverse' already exists" | Run the first `gds.graph.drop` statement of the file, then continue. |
| nodes show `u:12345` or `<id>` | Set the captions again (step 6). |
| the pseudonyms have 8 hex digits (`editor_` + 8) | The graph is from before the 2026-10-24 fixes. Ask Scott to run `export_graph.py` and `load_neo4j.py` again. |
| the graph is too crowded | Lower the `LIMIT`, or drag the nodes apart before the screenshot. |
