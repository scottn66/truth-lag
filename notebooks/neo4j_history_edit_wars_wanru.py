"""Exported from neo4j_history_edit_wars_wanru.ipynb.
Neo4j history-cohort analysis for the DATA 226 TruthLag term project.
"""

# # Neo4j Analysis of Wikipedia Edit Wars in the History Cohort
#
# **DATA 226 Term Project — TruthLag**  
# **Analysis owner:** Wan-Ru Hsiao  
# **Course technique:** Graph data modeling, Cypher traversal, community detection, and edit-war analysis
#
# This notebook studies who reverted whom in the Wikipedia history cohort. Editors and pages are represented as first-class graph entities, while edit and revert actions become relationships. The analysis focuses on mutual reverts, conflict communities, and pages with many mutually reverting editors.
#
# **AI-use disclosure.** This focused notebook was adapted from the team's executed EC HW2 Neo4j notebook and its checked result files. Wan-Ru Hsiao selected the final-project scope and interpreted the edit-war findings. ChatGPT/Codex assisted with restructuring the notebook, documentation, and limitations. The underlying graph construction, Cypher queries, and numeric outputs remain those of the reproducible project pipeline.

# ## 1. Setup and reproducibility
#
# The graph is built from the history cohort. The notebook uses the same versioned query files as the existing pipeline instead of embedding a second, potentially inconsistent copy of each Cypher query. Human editor identities remain pseudonymized; bots retain their public names.

# %%
# Locate ec-hw2 whether Jupyter starts at the repository root or a notebooks directory.
import sys, time, json
from pathlib import Path
CWD = Path.cwd().resolve()
if (CWD / 'ec-hw2').exists():
    REPO, HW2 = CWD, CWD / 'ec-hw2'
elif CWD.name == 'notebooks' and (CWD.parent / 'ec-hw2').exists():
    REPO, HW2 = CWD.parent, CWD.parent / 'ec-hw2'
elif CWD.name == 'notebooks' and (CWD.parent / 'config.py').exists():
    HW2, REPO = CWD.parent, CWD.parent.parent
else:
    raise RuntimeError('Run this notebook from the repository root or a project notebooks directory')
sys.path.insert(0, str(HW2))
import config
import pandas as pd
from tabulate import tabulate
from IPython.display import Image, display
pd.set_option('display.width', 200)
pd.set_option('display.max_columns', 40)
pd.set_option('display.max_colwidth', 80)
T0 = time.time()

def _cell(v):
    if v is None or v is pd.NA or (isinstance(v, float) and v != v):
        return ''
    if isinstance(v, float):
        return f'{v:,.1f}' if abs(v) >= 1000 else f'{v:.4g}'
    return v

def show(df, n=None):
    d = df if n is None else df.head(n)
    rows = [[_cell(v) for v in r] for r in d.astype(object).itertuples(index=False)]
    print(tabulate(rows, headers=list(d.columns), tablefmt='github'))

print('DATA_VERSION:', config.DATA_VERSION)
print('Python:', sys.executable)

# ## 2. Connect to Neo4j and run versioned Cypher files
#
# The connection uses project configuration values without printing credentials. Each returned editor identifier is checked against the graph's approved aliases and bot names before it is displayed.

# %%
from neo4j import GraphDatabase
import load_neo4j
from queries import run_cypher
driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
driver.verify_connectivity()
session = driver.session()
version = session.run("CALL dbms.components() YIELD name, versions WHERE name = 'Neo4j Kernel' "
                      "RETURN versions[0] AS v").single()["v"]
print("connected to the local Neo4j, version", version)
allowed = set(session.run("MATCH (e:Editor) RETURN collect(e.alias) AS a").single()["a"])   # aliases + bot names
CDIR = HW2 / "queries" / "cypher"
times = {}

def run_cypher_file(name, print_code=True):
    """Print the statements of queries/cypher/<name>.cypher, run them in order, return the result tables."""
    q = run_cypher.parse_file(CDIR / f"{name}.cypher")
    frames = {}
    for i, st in enumerate(q["statements"], start=1):
        if print_code:
            print(f"// statement {i}" + (f"  (result: {st['label']})" if st["label"] else ""))
            print(st["code"].strip() + ";\n")
        keys, rows, ms = run_cypher.run_once(session, st["code"])
        if st["label"]:
            df = pd.DataFrame(rows, columns=keys)
            run_cypher.check_privacy(df, allowed, f"{name} {st['label']}")   # stops if a name is not an alias
            frames[st["label"]] = df
            times[(name, st["label"])] = round(ms, 1)
    print(f"-> results: {', '.join(f'{k} ({len(v)} rows)' for k, v in frames.items())}\n")
    return frames

# ## 3. History-cohort graph model
#
# The property graph contains `Editor` and `Page` nodes. `EDITED` links an editor to a page and stores revision-level attributes. `REVERTED` links the reverting editor directly to the reverted editor and stores the affected page and aggregate counts. This representation makes multi-hop traversal and mutual-revert detection more direct than repeated relational self-joins.
#
# The history graph uses a **20-day follow-up window**, inherited from EC HW2. The final lake's E(L) analysis uses a **4-day window**. These results therefore describe complementary analyses and must not be numerically combined.

# %%
counts = load_neo4j.graph_counts(session)
show(pd.DataFrame([{"what": k, "count": v} for k, v in counts.items()]))
print()
for label in ("Editor", "Page"):
    keys = session.run(f"MATCH (n:{label}) WITH n LIMIT 1 RETURN keys(n) AS k").single()["k"]
    print(f"(:{label}) properties: {', '.join(sorted(keys))}")
for rel in ("EDITED", "REVERTED"):
    keys = session.run(f"MATCH ()-[r:{rel}]->() WITH r LIMIT 1 RETURN keys(r) AS k").single()["k"]
    print(f"[:{rel}] properties: {', '.join(sorted(keys))}")
ex = session.run("MATCH (a:Editor)-[r:REVERTED]->(b:Editor) WHERE a.kind = 'bot' "
                 "RETURN a.alias AS reverter, b.alias AS reverted, r.page_id AS page_id, r.count AS count "
                 "ORDER BY r.count DESC, page_id LIMIT 3").data()
print("\nExample REVERTED relationships (aliases):")
show(pd.DataFrame(ex))

# ## 4. Mutual reverts: the core edit-war pattern
#
# An edit-war pair exists when editor A reverted editor B and editor B also reverted editor A on the same page. The Cypher pattern follows two `REVERTED` relationships and uses `a.key < b.key` so that each unordered pair appears once.
#
# The executed graph contains **462 mutual-revert pairs across 397 pages and 631 editors**. Only 51 pairs, or 11.0%, occur on the top 20 contested pages. A small page ranking therefore cannot represent the full conflict network.

# %%
r1 = run_cypher_file("q1_mutual_reverts")
show(r1["main"], 10)
print()
show(r1["total"])
tot = r1["total"].iloc[0]
q2_top = pd.read_csv(config.RESULTS_DIR / "mongo_q2_top_contested_pages.csv")["page_id"]
on_top = r1["main"][r1["main"]["page_id"].isin(q2_top)]
print(f"\nFacts: {tot['mutual_pairs']} editor pairs reverted each other on the same page, on {tot['pages']} pages. "
      f"{len(on_top)} of these pairs ({100 * len(on_top) / tot['mutual_pairs']:.1f}%) are on the top 20 contested pages "
      f"of Mongo Q2, which are 20 of {counts['Page']:,} pages.")

# ## 5. Communities of conflict
#
# Louvain community detection uses an undirected projection of `REVERTED`, weighted by the relationship's revert count. Weakly connected components provide a second view of the graph's reach.
#
# There are 28,615 Louvain communities, but 27,424 are isolated single editors. Only 1,191 communities contain at least two editors. The largest community has 564 editors and 661 revert actions, yet 69.1% of its revert relationships touch one top reverter, ClueBot NG. This is closer to a hub-and-spoke patrolling structure than a community in which everyone fights everyone else.

# %%
r3 = run_cypher_file("q3_conflict_communities")
show(r3["louvain_stats"])
print()
show(r3["community_sizes"])
print()
show(r3["main"])
print()
show(r3["wcc_sizes"])
c1 = r3["main"].iloc[0]
cz = r3["community_sizes"].iloc[0]
w = r3["wcc_sizes"]
print(f"\nFacts: {cz['communities_2plus']:,} of the {cz['communities']:,} Louvain communities have 2 or more editors. "
      f"The largest has {c1['editors']} editors and {c1['reverts']} revert actions on {c1['pages']} pages. "
      f"{100 * c1['star_share']:.1f}% of its REVERTED relationships touch its top reverter, and its top page "
      f"({c1['top_page']}) has only {100 * c1['top_page_reverts'] / c1['reverts']:.2f}% of its revert actions. "
      f"{100 * w.iloc[0]['share_of_editors']:.1f}% of the editors are alone (no revert), and one component holds "
      f"{100 * w.iloc[-1]['share_of_editors']:.1f}%.")

# ## 6. Pages with the most warring editors
#
# The page ranking counts editors who belong to at least one mutual-revert pair on the page. `PB&J_Otter` ranks first with 10 warring editors, 9 mutual pairs, and 34 revert actions among 39 human edits. High edit volume alone is not equivalent to conflict; the graph explicitly captures reciprocal behavior.

# %%
r4 = run_cypher_file("q4_pages_most_warring_editors")
show(r4["main"], 10)
t4 = r4["main"].iloc[0]
print(f"\nFacts: on {t4['page_title']}, {t4['warring_editors']} editors are in {t4['mutual_pairs']} mutual pairs; "
      f"the page has {t4['revert_actions']} revert actions on {t4['edits']} human edits.")

# ## 7. Edit-war visualization
#
# The graph below shows the selected `GPT-6` page. Nodes are pseudonymized editors and directed arrows mean "reverted." Two-way arrows expose mutual conflict, while one-way edges show asymmetric patrolling or correction behavior.

# %%
display(Image(filename=str(config.FIGURES_DIR / "neo4j_edit_war_example.png"), width=650))
page_id = run_cypher.pick_war_page(r4["main"])
title, edges = run_cypher.war_edges(session, page_id)
print(f"page {page_id}: {title}")
show(edges[["src", "src_kind", "dst", "dst_kind", "n"]].rename(columns={"src": "reverter", "dst": "reverted", "n": "count"}))

# ## 8. Quantitative performance
#
# The project recorded seven warm runs for ordinary queries and one run for the write-mode Louvain step.
#
# | Operation | Median runtime |
# |---|---:|
# | Mutual-revert pairs (Q1 main) | 261.2 ms |
# | Louvain write | 536.9 ms |
# | Community summary (Q3 main) | 115.8 ms |
# | Warring-page ranking (Q4 main) | 32.0 ms |
#
# The results show that graph traversal and aggregation remained interactive at 37,546 editor nodes and 13,269 `REVERTED` relationships.

# ## 9. Interpretation, limitations, and key learning
#
# Neo4j makes reciprocal and multi-hop conflict patterns explicit. Mutual reverts can be expressed as a short graph pattern, and community algorithms reveal whether a component is a dense conflict group or a hub centered on a patroller. The largest community's 69.1% star share demonstrates why community size alone can be misleading.
#
# The graph has several limitations. First, it covers the fixed history cohort and a 20-day follow-up window, not the final lake's 4-day E(L) horizon. Second, one identity revert that covers revisions from several authors produces one `REVERTED` edge per reverted author; this differs from studies that count only the closest prior author. Third, three history revisions have no editor key, so 295,013 `EDITED` relationships represent 295,016 cohort revisions. Finally, a mutual revert signals reciprocal action but does not prove misconduct or malicious intent.
#
# **Key learning:** graph structure adds information that page-level counts lose. A page can be heavily edited without mutual conflict, while a smaller page can contain a dense reciprocal edit war.

# %%
session.close()
driver.close()
print('Neo4j connection closed.')
