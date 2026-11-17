# Research findings for the Delta Lake plan (Nov 13, 2026)

> Exported on 2026-11-13 from the Notion page of the same name. The Notion page is the working copy; if the two differ, Notion is newer.

> **Purpose.** The evidence behind the build plan on the parent page, published for other agents to review. Seven research agents ran in a cloud Claude Code session on Nov 13, 2026. Five read the sources and tested single building blocks (R1 to R5). Two built and tested prototypes of the riskiest steps (R6 and R7). Each sub-page is one agent's report, published as returned, with only formatting changes. No other agent or person has reviewed them yet. The plan on the parent page was reviewed once inside the same session; its Review log has the entry.

## How to read the evidence labels

- **RAN**: the agent executed it in the cloud session and saw the output. All runs used made-up events or synthetic tables, never the real TruthLag data.
- **READ**: read in the repository or a docs clone, cited as file:line. Repository state: `scottn66/truth-lag`, default branch at `8e28012`.
- **DERIVED**: arithmetic on values that were read.
- **UNVERIFIED**: not checked. Treat as a question, not a fact.

## What the cloud session could not see

- The raw capture files, the History dump files and the derived tables. They are on Scott's Mac and the VPS.
- `dumps.wikimedia.org`, the Wikimedia APIs and EventStreams. The session's network blocks them, and agents were told never to open an EventStreams connection.

## Sub-pages

| Page | Question it answers |
| --- | --- |
| R1 — Existing pandas pipeline: porting inventory | Which functions, rules, clocks and published numbers must the new pipeline reuse or reproduce? |
| R2 — delta-rs lab (deltalake 1.6.6) | Which Delta features work in the Python-only engine, with tested code? |
| R3 — PySpark and delta-spark lab | Which Delta features work in Spark, with tested code, and can the two engines share tables? |
| R4 — Delta Lake docs fact sheet | What do the Delta docs, protocol and source say about the behaviour the plan relies on? |
| R5 — History snapshots and the current-events slice | What does a second History snapshot add, and how can current-events pages be defined and compared? |
| R6 — Prototype: Bronze and Silver with delta-rs on the repo fixtures | Does the Python pipeline give the same tables as the old one on the repository's fixtures, and is a re-run safe? |
| R7 — Prototype: Gold SQL with Spark on made-up tables | Does the Gold SQL give known answers: the star schema, the SCD Type 2 dimension, the label MERGE with Change Data Feed, the E(L) mart? |
| R8 — Kit files that R6 and R7 do not hold: the check scripts | Not a report: the check scripts of the two prototypes, so that R6, R7 and R8 together hold every file of the hand-off kit's prototype folders. |

## How to review

Add a comment on the page you reviewed, or append a dated entry under **Review log** on the parent page. State what you checked, what you could not check, and each finding with its evidence. Do not edit the report text itself; corrections go in the review entry.
