# Cypher Q3 (spec 4.3): communities of conflict (Louvain and WCC, with GDS)

Question: do reverts form groups of editors who keep clashing with each other?
The GDS projection has all Editor nodes and the REVERTED relationships as
UNDIRECTED (who reverted whom does not matter for a group). Parallel
relationships between two editors (other pages, the other direction) are merged
into one, and their count values are added (aggregation SUM).
- Louvain finds communities: many reverts inside, few between. It WRITES the
property communityId on every Editor (concurrency 1, so a re-run gives the same
groups). An editor without any REVERTED relationship is a community of 1.
- WCC (weakly connected components) finds the groups joined by any chain of reverts.
Repeatability: on the same loaded graph, Louvain gives the same communities every
time. After a new load, Neo4j gives the nodes new internal ids, and Louvain visits
the nodes in id order, so a few communities can merge or split (data-v1, three loads:
modularity 0.9138, 0.9142 and 0.9143). The community numbers are internal ids, not names.
The WCC results do not change.
Output columns (result louvain_stats): communities, modularity, levels, editors_written.
Output columns (result community_sizes): communities (the total, as in louvain_stats),
communities_2plus (communities with 2 or more editors), communities_1 (one editor
alone), editors_without_revert (editors with no REVERTED relationship at all; each is
a community of 1). Most of the total are such single editors, so report
communities_2plus next to the total.
Output columns (result main = the 10 largest Louvain communities with 2+ editors):
rank, community, editors, bots, pages, reverts, reverted_edges, star_share, top_page,
top_page_reverts, top_page_share, top_reverters.
pages = distinct pages of the REVERTED relationships inside the community;
reverts = the sum of their count; reverted_edges = the number of those relationships;
top_reverters = the 3 members with the most reverts_made (aliases); the first one is
the community's top editor. star_share = the share of the community's REVERTED
relationships that touch the top editor (as reverter or as reverted editor). A share
near 1 means the community is one patroller (often a bot) and the editors it reverted,
not a group of editors who fight each other.
top_page = the page with the most of the community's reverts; top_page_reverts = its
reverts; top_page_share = top_page_reverts / reverts. A small share means the
community is spread over many pages.
Output columns (result wcc_sizes): component_size, components, editors, share_of_editors.
Output columns (result wcc_largest = the 5 largest components): rank, editors, bots,
pages, reverts, top_reverters.
The projection is dropped at the end. Editors are shown by alias.

Rows: 10. Median time: 106.9 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-24 09:56 UTC (data-v1). Query: `queries/cypher/q3_conflict_communities.cypher`. Full table: `cypher_q3_conflict_communities.csv`.

|   rank |   community |   editors |   bots |   pages |   reverts |   reverted_edges |   star_share | top_page                             |   top_page_reverts |   top_page_share | top_reverters                                             |
|--------|-------------|-----------|--------|---------|-----------|------------------|--------------|--------------------------------------|--------------------|------------------|-----------------------------------------------------------|
|      1 |       14645 |       564 |      1 |     555 |       661 |              645 |        0.691 | Désiré_Doué                          |                  9 |            0.014 | ClueBot NG | editor_6b17555cf5 | editor_1a2a631783        |
|      2 |       12289 |       354 |      0 |     342 |       428 |              392 |        0.487 | Pororo_the_Little_Penguin            |                 11 |            0.026 | editor_5d9d202d8d | editor_ced644389c | editor_a7199a021c |
|      3 |        1190 |       220 |      0 |     207 |       279 |              255 |        0.69  | Special_Operations_Executive         |                  5 |            0.018 | editor_8596618215 | editor_737f100f98 | editor_fad7c96275 |
|      4 |       15783 |       198 |      0 |     188 |       250 |              224 |        0.563 | Jim_Queen                            |                  6 |            0.024 | editor_3b75e7ac14 | editor_eee0c6e1d9 | editor_e02e1213ad |
|      5 |        3208 |       196 |      0 |     188 |       264 |              235 |        0.332 | List_of_companies_named_after_people |                 25 |            0.095 | editor_4daa5740d4 | editor_5ca7ccde36 | editor_fcc23e4eff |
|      6 |       16919 |       188 |      0 |     272 |       299 |              296 |        0.818 | List_of_Regular_Show_characters      |                  4 |            0.013 | editor_858fa0fb69 | editor_bd06c7bddd | editor_b0edd87066 |
|      7 |       36724 |       171 |      1 |     176 |       259 |              239 |        0.096 | Paris_Saint-Germain_FC               |                  9 |            0.035 | editor_b0b9bc4bf6 | editor_00b207b1cd | editor_9880a6129d |
|      8 |       18032 |       168 |      1 |     169 |       264 |              241 |        0.32  | Mike_McFarland                       |                 25 |            0.095 | editor_dd4c69c7ef | editor_e0ef1516a7 | MusikBot II       |
|      9 |       34164 |       160 |      0 |     217 |       249 |              244 |        0.684 | Noise_pop                            |                  5 |            0.02  | editor_71e32ee367 | editor_e21de22bd0 | editor_07627a7542 |
|     10 |       19136 |       158 |      0 |     144 |       183 |              170 |        0.535 | Jordan_Ayew                          |                  9 |            0.049 | editor_189d3af8ce | editor_65acaa3cc9 | editor_2a2c1d5e4e |

