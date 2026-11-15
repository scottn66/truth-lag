# GATE_MON: every decision for Scott, each with a default

Last updated: 2026-11-15 13:10 UTC (Sun 5:10 AM PT), loop 2 stop. Due: Tue Nov 17, 11:59 PM PT on Canvas (report PDF, slides, code). This is the only file that asks you anything. If you do nothing, the **Default** column is what stands.

## Where things are

| Observable of loop 2 | State | Check it yourself |
| --- | --- | --- |
| 1. Number check | passes: zero mismatches; `results.json` has 1,130 facts, stamped at a clean commit | `.venv-lake/bin/python scripts/check_numbers.py` |
| 2. Evidence check | passes: 14 of 14 rubric lines have a command, an output file and an executed notebook | `.venv-lake/bin/python scripts/check_evidence.py` |
| 3. Rubric techniques | all built: LSH, privacy, and moments/reservoir are in `notebooks/fallback/` (executed, `.py` copies) | `ls notebooks/fallback` |
| 4. Report draft | `docs/final/report_draft.md` (skeleton of facts, no prose, no code) and `docs/final/slides_outline.md` | open them |
| 5. Bundle | `dist/` built from a fresh clone; output recorded in RESULTS.md ("Bundle") | `bash scripts/make_bundle.sh` |
| 6. This file | current | |

Not done by design: nothing was pushed, nothing touched the VPS, no data or secret was committed. No stop condition was hit (Spark fine, 29 GB free, every regenerated number equals RESULTS.md).

## Decisions

| # | Decision | Default (stands if you do nothing) | To change it | Your minutes |
| --- | --- | --- | --- | --- |
| 1 | **Push loop 2.** The loop-2 commits are local only (rule of the prompt). Teammates see nothing of them until you push. | Not pushed. | `git push origin final-lake` | 1 |
| 2 | **Send the extracts.** `data/exports/` (103 MB, not in git) is what Wanru and Zhenni need. | Not sent. | Share the folder (Drive or zip). `lsh_pairs_to_label.csv` in it holds comment text: leave it out or keep it private. | 5 |
| 3 | **Official rubric wording and order.** The rubric text is not on this Mac; `RUBRIC_EVIDENCE.md` uses the lines named in `DECISIONS.md`. | Tingyu re-orders the 14 rows to match Canvas when pasting the appendix. | Paste the rubric into `docs/final/RUBRIC_CANVAS.md` and ask Claude to re-map the table. | 5 |
| 4 | **Fallback or teammate notebooks for LSH and privacy.** | The report uses the fallback numbers unless Wanru's or Zhenni's notebook is in the repository by Mon Nov 16, 9 PM PT. A teammate's notebook always wins. | Tell Tingyu a different cut-off. | 0 |
| 5 | **Who labeled the 80 LSH pairs.** Claude did, by reading both comments; disclosed in `GENAI_LOG.md`. The prompt bans LLM methods in the analysis; these labels are evaluation ground truth, not the method. | Keep Claude's labels, disclosed. Precision: 40 of 40 by similarity band, 37 of 40 one-per-group. | Fill `human_label` in `notebooks/fallback/lsh_pair_labels.csv` using `data/exports/lsh_pairs_to_label.csv`, then `python notebooks/fallback/make_fallback.py lsh_minhash` (5 min run) and `python scripts/make_results.py`. | 10 |
| 6 | **H4 floor.** | 1% of pages (logged). H4 is falsified at that floor. | Say another value; the numbers do not change, only the verdict sentence. | 0 |
| 7 | **Primary series for H1.** | The `live` cohort (Oct 20-22); `live_ext` and `history` are robustness checks (logged). | Say which. | 0 |
| 8 | **Commit email.** | Stays `scottn66@users.noreply.github.com` (logged). | `git rebase` with another author before pushing. | 0 |
| 9 | **Public repository** (the rubric gives points for version control with a public repository). | Stays private. | GitHub settings. Checked today: no secret, connection string or IP address is tracked; `ec-hw2/.env.example` is the only env file. | 2 |
| 10 | **CRediT rows.** Proposed in `report_draft.md` from your team message. If a fallback notebook is used, that software credit moves to your row. | As proposed, each person confirms. | Edit the table in `report_draft.template.md`. | 0 |
| 11 | **File left out of the code zip.** `ec-hw2/report/REPORT_SKELETON.docx` (3.2 MB) is over the 1.2 MB limit for "files near 1 MB". | Left out of the zip (it stays in the repository). | Raise `LIMIT_KB` in `scripts/make_bundle.sh`. | 0 |
| 12 | **The LSH extract was re-drawn** at 12:46 UTC today: its first version under-sampled the latest not-reverted edits (found by the reservoir check; RESULTS.md, "Export fix"). | Send the new file. If a teammate already has the older one (unlikely: it was made at 10:10 UTC), they swap it. | Nothing. | 0 |
| 13 | **Reference list.** The technique references in `report_draft.md` were written from memory by Claude. | Only the proposal's own references are used as they are; each added reference goes in after Tingyu verifies it. | Nothing. | 0 |
| 14 | **Slides.** Claude wrote a 15-slide outline of facts, not a deck. | Tingyu builds the deck from `slides_outline.md` and `docs/final/figures/`. | Ask Claude for a deck (not started). | 0 |
| 15 | **Checking the final PDF and slides.** `check_numbers.py` can check exported text, but a wrong number that happens to equal another fact passes. | Tingyu runs `pdftotext -layout report.pdf report.txt`, then `python scripts/check_numbers.py --text report.txt` and skims `--explain report.txt`. If nobody does, the final files are unchecked. | Do it yourself. | 10 |
| 16 | **Rebuild `dist/` after your last commit.** `dist/` is built from the commit named in its `MANIFEST.txt`. | The `dist/` on disk (see RESULTS.md, "Bundle"). | `bash scripts/make_bundle.sh` after any new commit. | 2 |

## Your 90 minutes, suggested

1. Read this page (10). 2. Push (1) and share `data/exports/` (5). 3. Send the team message below (5). 4. Skim `report_draft.md` and `slides_outline.md` for anything you disagree with (20). 5. Rubric order with Tingyu (5). 6. Optional: re-label LSH pairs (10). 7. Tuesday: rebuild `dist/`, run the number check on the exported report and slides, upload to Canvas (25). Spare: 9.

## Draft message to the team (you send it; edit freely)

> Update on the final project. The lake, results and checks are on branch `final-lake`. For Tingyu: `docs/final/report_draft.md` is a section-by-section skeleton with every number filled in (please write the text in your own words; lines marked TODO need you), `docs/final/slides_outline.md` is the same for 15 slides, figures are in `docs/final/figures/`, and `docs/final/RUBRIC_EVIDENCE.md` is the rubric appendix (please put its rows in the Canvas order). Do not type numbers by hand: copy them from the draft. For Wanru and Zhenni: your input files are in the shared folder (schemas in `docs/final/HANDOFF_TEAM.md`). So that we are covered, there are fallback notebooks for LSH and privacy in `notebooks/fallback/`; yours replace them if they are in the repo by Monday 9 PM. Please also confirm your CRediT row in the draft.
