# Cypher Q3 (spec 4.3): communities of conflict (Louvain and WCC, with GDS) (result community_sizes)

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

Rows: 1. Median time: 19.2 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-24 09:56 UTC (data-v1). Query: `queries/cypher/q3_conflict_communities.cypher`. Full table: `cypher_q3_conflict_communities_community_sizes.csv`.

|   communities |   communities_2plus |   communities_1 |   editors_without_revert |
|---------------|---------------------|-----------------|--------------------------|
|         28615 |                1191 |           27424 |                    27424 |

