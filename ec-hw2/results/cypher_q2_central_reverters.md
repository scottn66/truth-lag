# Cypher Q2 (spec 4.2): the most central reverters (degree and PageRank, with GDS)

Question: which editors revert the most, and who is most central in the revert graph?
Two measures, which answer two different questions:
- degree (result by_degree) answers "who reverts the most": out_degree = REVERTED
relationships that go out (one per reverted editor and page); editors_reverted =
distinct editors reverted; reverts_made = the sum of count on those relationships
(revert actions; one revert that undid two editors counts once for each).
- PageRank (results main and humans) on a GDS projection of Editor + REVERTED with
REVERSE orientation, weight = count. A high score means "reverts editors who are
themselves active reverters", not "reverts a lot".
Why REVERSE: (a)-[:REVERTED]->(b) means "a reverted b". PageRank moves score along
the arrows, so with the natural direction the score piles up on editors who GET
reverted. The projection turns every arrow around (b -> a), so each editor passes its
score to the editors who reverted it. An editor therefore scores high when the editors
it reverted have high scores themselves, which means they are active reverters too.
So an editor with few reverts can rank high if it reverted a busy reverter who was
seldom reverted by anyone else. The weight count gives more score to repeated reverts.
Convergence: both PageRank calls use maxIterations 200 and tolerance 1e-7 (the GDS
default stops after 20 iterations, before the scores settle). run_cypher.py first runs
gds.pageRank.stats with the same settings and stops with an error if didConverge is false.
In Neo4j Browser you can check it yourself after the projection step:
CALL gds.pageRank.stats('cypher_q2_reverse', {relationshipWeightProperty: 'count', concurrency: 4, maxIterations: 200, tolerance: 1e-7}) YIELD didConverge, ranIterations
Output columns (result main = top 20 by PageRank, result humans = top 20 humans by
PageRank): editor, kind, out_degree, editors_reverted, reverts_made,
reverts_received, pagerank.
Output columns (result by_degree = top 20 by reverts_made): editor, kind, out_degree,
editors_reverted, reverts_made, reverts_received.
The projection is dropped at the end. Editors are shown by alias.

Rows: 20. Median time: 193.3 ms (7 warm runs after 1 warm-up).
Made by `ec-hw2/queries/run_cypher.py` on 2026-10-24 09:56 UTC (data-v1). Query: `queries/cypher/q2_central_reverters.cypher`. Full table: `cypher_q2_central_reverters.csv`.

| editor            | kind       |   out_degree |   editors_reverted |   reverts_made |   reverts_received |   pagerank |
|-------------------|------------|--------------|--------------------|----------------|--------------------|------------|
| ClueBot NG        | bot        |          591 |                563 |            592 |                 36 |    87.5822 |
| editor_5d9d202d8d | registered |          233 |                225 |            246 |                 13 |    38.6567 |
| editor_8596618215 | registered |          196 |                182 |            215 |                 24 |    37.1652 |
| editor_3b75e7ac14 | registered |          133 |                121 |            154 |                 11 |    35.0454 |
| editor_858fa0fb69 | registered |          264 |                156 |            267 |                 12 |    32.3999 |
| MusikBot II       | bot        |           23 |                 21 |             23 |                 12 |    31.7853 |
| editor_71e32ee367 | registered |          170 |                 99 |            173 |                 10 |    31.4587 |
| editor_7ca4a5a591 | registered |          112 |                103 |            125 |                 20 |    31.0038 |
| editor_bfe10b76eb | registered |          135 |                131 |            141 |                 14 |    28.6187 |
| editor_ced644389c | registered |           82 |                 79 |             98 |                  6 |    26.9183 |
| editor_c1f0a5c150 | registered |           44 |                 36 |             44 |                  3 |    22.1561 |
| editor_4daa5740d4 | registered |           83 |                 77 |            101 |                 18 |    21.6641 |
| editor_b341e72d5f | registered |           62 |                 45 |             62 |                  3 |    20.1926 |
| editor_dd4c69c7ef | registered |           74 |                 61 |             88 |                 10 |    19.9543 |
| editor_59ebd927ba | registered |          121 |                 80 |            126 |                  8 |    19.4612 |
| editor_90f033f743 | registered |           69 |                 64 |             80 |                 11 |    19.262  |
| editor_c48102745d | registered |           51 |                 33 |             52 |                  1 |    18.7024 |
| editor_090f62746b | temporary  |            2 |                  2 |              5 |                  6 |    17.9313 |
| editor_5c67223c09 | registered |           71 |                 65 |             83 |                  7 |    16.6623 |
| editor_350d99a245 | temporary  |            1 |                  1 |              1 |                  4 |    16.0471 |

