# After Nov 17: ideas noted, not built

Out of scope until the term project is submitted (loop 2 prompt). Nothing here is started. Each line says what, why, and the first step.

## Engineering hardening (for employers reading the repository)

- **One environment file and a lock.** `requirements-lake.txt` pins 8 packages; the rest float. First step: `uv pip compile` to a lock file and a `make setup` target.
- **CI on the fixture tests.** The 49 tests need no real data. First step: a GitHub Actions workflow with Java 21 that runs `tests_lake/` and the two EC HW2 test files.
- **Gold tests on made-up data.** The kit's 75 Gold checks were not ported (`tests_lake/test_gold.py` does not exist). First step: copy `gen_silver.py` and `verify_gold.py` from `docs/delta_lake_handoff/proto_gold_sql/`.
- **A file ledger for Bronze.** A Bronze re-run re-reads every gzip file (24 s now; grows with the capture). First step: the optional `bronze/load_log` table of LAKE_DESIGN.md.
- **Incremental cohort builds.** `label_live` runs on a full export per `as_of` (about 6 GB of RAM for 20 days). First step: partition the export by event date and bound the look-back window.
- **Typed configuration.** Windows and thresholds live in `ec-hw2/config.py` and `etl/lake_config.py`. First step: one typed settings module, with `ec-hw2` frozen as a dependency.
- **Remove the macOS-only fixes from the session factory** behind a platform check, and test Spark start on Linux.
- **OPTIMIZE and Z-order** on `gold/fact_edit` by `page_key`, with files scanned before and after (the plan's stretch item 3).
- **Packaging.** `etl/` as an installable package with console scripts instead of `python -m etl.*`.

## The lake as a reusable resource

- **A public, pseudonymized release** of the Gold marts and the reconciliation table (after the privacy findings: the page-level table needs generalization or noise before any release; see `notebooks/fallback/privacy.ipynb`).
- **corpus-engine, the wiki, the knowledge-graph curriculum, ClaimKB.** The useful export is "revision, page version at edit time, revert label with the time it became known". First step: write down which of these each repository would read, before building any interface.
- **Thesis directions.**
  - H2, the early-signal model: predict the later revert label from page signals available W minutes after the edit, against the "survived so far" baseline.
  - A reporting-triangle nowcast of the final revert count from the live count (experiment E7), using the E(L) curve by editor kind as the delay distribution.
  - A third History snapshot (2026-11, due in early December): label changes across three snapshots, and the 30-day horizon of the proposal.
  - Why 325 live revisions are reverted only in the dump (`gold/recon_mismatch`): inexact reverts, reverts the stream does not mark, or deletions.
  - Other wikis: the capture and the lake take a wiki id; nothing is enwiki-specific except the filters.

## Loose ends from the build

- The Kaplan-Meier view of E(L) with censoring (the plan's E0) would allow cohorts with incomplete follow-up.
- `is_redirect` in `dim_page` (the events carry it; the parsed tables do not).
- The raw 2026-09 dump file is mirrored in `data/history_raw/`; upstream drops it when 2026-11 is published.
