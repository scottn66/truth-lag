# Wan-Ru's Two-Slide Content

These slides are designed to replace or expand the current "Two sources, two knowledge axes" and "Locality-sensitive hashing" slides. Keep the deck's existing visual theme and final slide numbering.

## Slide A — History Is Revised After Publication

**Subtitle:** Delta time travel preserves what was known at each snapshot

**Main visual:**

`2026-09 snapshot: 19,858 reverted` → `+1,067 net newly known` → `2026-10 snapshot: 20,925 reverted`

**Supporting evidence:**

- 2,967 of 2,970 late exact reverts were confirmed by the later snapshot (**99.9%**).
- Stream and dump labels agreed on **99.86%** of 279,466 live revisions.
- Delta versions preserve both answers instead of overwriting the earlier state.
- Stream knowledge also changed: **17,040 → 17,818** known live reverts in three days.

**Small footer:** Snapshot axis and stream as-of axis are separate knowledge clocks.

### Speaker notes

MediaWiki History is corrected over time, so a monthly dump should not be treated as permanently final. For the same September cohort, the number of revisions known to be reverted increased from 19,858 in the 2026-09 snapshot to 20,925 in the 2026-10 snapshot. Our stream had already detected 2,970 exact late reverts, and the later dump confirmed 2,967 of them. Delta Lake time travel lets us reproduce both the earlier and later answers through separate table versions rather than replacing history silently.

## Slide B — Relationship and Text Patterns Reveal Different Signals

**Left side: Neo4j edit-war graph**

- Model: `Editor —EDITED→ Page`; `Editor —REVERTED→ Editor`
- **462** mutual-revert pairs across **397** pages
- Largest community: **564 editors**, but **69.1%** of relationships touch one top reverter
- Interpretation: large community ≠ everyone fighting everyone

**Suggested visual:** `ec-hw2/results/figures/neo4j_edit_war_example.png`

**Right side: MinHashLSH on edit comments**

- Five-character shingles; Jaccard similarity ≥ 0.60
- Five hash tables: **96.11% recall** on the exact validation sample
- Human review: **77/80** same-pattern pairs
- Estimated precision: **96.2%** (95% CI: 89.5%–98.7%)

**Bottom takeaway:** Graph traversal identifies reciprocal conflict; LSH finds repeated language patterns without an all-pairs comparison.

**Small footer:** Neo4j uses the legacy 20-day history window; E(L) and LSH labels use four days.

### Speaker notes

The two techniques answer different questions. Neo4j makes reciprocal conflict explicit: 462 editor pairs reverted each other on the same page. Community detection also showed that the largest group was mostly a hub around one patroller, so community size alone can be misleading. MinHashLSH instead searches edit comments. With five hash tables it recovered 96.11% of exact near-duplicate pairs in the validation sample, and manual review confirmed that 77 of 80 candidates represented the same edit pattern. Together, these methods reveal relational and textual structure that simple counts miss.

## Optional Q&A Responses

**Why did the snapshot counts change?**  
Later reverts changed the labels of revisions that already existed in the earlier snapshot.

**Does a mutual revert prove an edit war or misconduct?**  
No. It is an operational indicator of reciprocal actions and requires contextual interpretation.

**Why not use 20 MinHash tables?**  
Recall improved only from 96.11% with five tables to 96.16% with twenty, so the additional cost produced almost no benefit.
