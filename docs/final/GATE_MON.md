# GATE_MON: every decision for Scott, each with a default

Last updated: 2026-11-16 02:00 UTC (Sun Nov 15, 6:00 PM PT), after the Canvas rubric (`docs/final/CANVAS_SPEC.md`) was mapped. Due: Tue Nov 17, 11:59 PM PT on Canvas (report PDF, slides, code). This is the only file that asks you anything. If you do nothing, the **Default** column is what stands.

## Where things are

| Observable of loop 2 | State | Check it yourself |
| --- | --- | --- |
| 1. Number check | passes: zero mismatches; `results.json` has 1,130 facts, stamped at a clean commit | `.venv-lake/bin/python scripts/check_numbers.py` |
| 2. Evidence check | passes for what can be checked: of the 24 Canvas rubric lines, 14 have a command and an output file that exist; 10 are open and need a person (decision 17) | `.venv-lake/bin/python scripts/check_evidence.py` |
| 3. Rubric techniques | all built: LSH, privacy, and moments/reservoir are in `notebooks/fallback/` (executed, `.py` copies) | `ls notebooks/fallback` |
| 4. Report draft | `docs/final/report_draft.md` (skeleton of facts, no prose, no code) and `docs/final/slides_outline.md` | open them |
| 5. Bundle | `dist/` built from a fresh clone; output recorded in RESULTS.md ("Bundle") | `bash scripts/make_bundle.sh` |
| 6. This file | current | |

Loop 2 was pushed on your word ("Push final-lake", Nov 15); commits made after that are local until you say so. Not done by design: nothing touched the VPS, no data or secret was committed. No stop condition was hit (Spark fine, 29 GB free, every regenerated number equals RESULTS.md).

## Decisions

| # | Decision | Default (stands if you do nothing) | To change it | Your minutes |
| --- | --- | --- | --- | --- |
| 1 | **Push.** Loop 2 is on `origin/final-lake`. The rubric re-map commit made after it is local. | Not pushed. | `git push origin final-lake` | 1 |
| 2 | **Send the extracts.** `data/truthlag_exports_2026-11-15.zip` (61.5 MB, not in git) holds the 14 export files and `HANDOFF_TEAM.md`; `lsh_pairs_to_label.csv` is left out. | Not sent. | Put the zip on Drive and send the link to Wanru and Zhenni. | 5 |
| 3 | **Rubric order.** Done: `RUBRIC_EVIDENCE.md` follows the 24 Canvas lines in order. Lines 22 and 23 claim that star schema, time travel and MERGE were "covered in the course" and that Delta Lake was "not used for any HW". | The claims stand as written. | Tell Tingyu to reword lines 22 and 23 if either is not true. | 2 |
| 4 | **Fallback or teammate notebooks for LSH and privacy.** | The report uses the fallback numbers unless Wanru's or Zhenni's notebook is in the repository by Mon Nov 16, 9 PM PT. A teammate's notebook always wins. | Tell Tingyu a different cut-off. | 0 |
| 5 | **Who labeled the 80 LSH pairs.** Claude did, by reading both comments; disclosed in `GENAI_LOG.md`. Canvas instruction 4 says not to use LLMs in the project; these labels are evaluation ground truth, not the method, but a grader may not see the difference. | Keep Claude's labels, disclosed. Precision: 40 of 40 by similarity band, 37 of 40 one-per-group. | Safer: fill `human_label` in `notebooks/fallback/lsh_pair_labels.csv` using `data/exports/lsh_pairs_to_label.csv`, then `python notebooks/fallback/make_fallback.py lsh_minhash` (5 min run) and `python scripts/make_results.py`. | 10 |
| 6 | **H4 floor.** | 1% of pages (logged). H4 is falsified at that floor. | Say another value; the numbers do not change, only the verdict sentence. | 0 |
| 7 | **Primary series for H1.** | The `live` cohort (Oct 20-22); `live_ext` and `history` are robustness checks (logged). | Say which. | 0 |
| 8 | **Commit email.** | Stays `scottn66@users.noreply.github.com` (logged). | `git rebase` with another author before pushing. | 0 |
| 9 | **Public repository.** Rubric line 6 (3 points) says "must be publicly accessible", and instruction 3 says every link in the appendix must be reachable by the teaching team. | Stays private: line 6 is then not met and the GitHub link in the appendix does not work for graders. Only you can change it. | GitHub settings, before submitting. Checked Nov 15: no secret, connection string or IP address is tracked; `ec-hw2/.env.example` is the only env file. | 2 |
| 10 | **CRediT rows.** Proposed in `report_draft.md` from your team message. If a fallback notebook is used, that software credit moves to your row. | As proposed, each person confirms. | Edit the table in `report_draft.template.md`. | 0 |
| 11 | **What to upload as "code".** Canvas does not accept zip files (accepted: pdf, py, ipynb, pptx, tex, txt, html and a few others; no md, no png). The two zips in `dist/` cannot be uploaded. | Upload the 11 notebooks with their `.py` copies from `dist/notebooks/` (largest 133 KB) and give the GitHub link in the appendix for the rest of the code. This needs decision 9 to be "public". | Also upload the 22 `.py` files of `etl/` one by one, or put a zip on Drive and link it (instruction 7 allows Drive links for large files). | 5 |
| 12 | **The LSH extract was re-drawn** at 12:46 UTC today: its first version under-sampled the latest not-reverted edits (found by the reservoir check; RESULTS.md, "Export fix"). | Send the new file. If a teammate already has the older one (unlikely: it was made at 10:10 UTC), they swap it. | Nothing. | 0 |
| 13 | **Reference list.** The technique references in `report_draft.md` were written from memory by Claude. | Only the proposal's own references are used as they are; each added reference goes in after Tingyu verifies it. | Nothing. | 0 |
| 14 | **Slides.** Claude wrote a 15-slide outline of facts, not a deck. | Tingyu builds the deck from `slides_outline.md` and `docs/final/figures/`. | Ask Claude for a deck (not started). | 0 |
| 15 | **Checking the final PDF and slides.** `check_numbers.py` can check exported text, but a wrong number that happens to equal another fact passes. | Tingyu runs `pdftotext -layout report.pdf report.txt`, then `python scripts/check_numbers.py --text report.txt` and skims `--explain report.txt`. If nobody does, the final files are unchecked. | Do it yourself. | 10 |
| 16 | **Rebuild `dist/` after your last commit.** `dist/` is built from the commit named in its `MANIFEST.txt`. | The `dist/` on disk (see RESULTS.md, "Bundle"). | `bash scripts/make_bundle.sh` after any new commit. | 2 |
| 17 | **Ten rubric lines have no evidence from the build** (36 of 100 points): 2 presentation skills (5), 3 Q&A (5), 8 prospects (3), 10 teamwork (5), 12 pair programming (2), 13 agile (2), 14 slides (3), 15 LaTeX `.tex` file (2), 16 creative presentation (2), 17 literature survey (7). Lines 12, 13 and 15 need artifacts that are not in the repository: screenshots or notes of pairing, sprint minutes and backlog, a `.tex` file from the IEEE template. | The team supplies what it has; a line with nothing is stated as not done in the appendix (Canvas: "do not mislead"). | Ask the team today what exists for 12, 13 and 15. | 5 |
| 18 | **Mandatory GenAI question and certificate.** Canvas asks for full details of GenAI use including the prompt, and advises submitting the certificate from `sjsusaid.vercel.app`. | Not generated: only a person can do it. `GENAI_LOG.md` has the details; the two loop prompts are in your Downloads folder, not in the repository. | Generate the certificate and upload it with the report. | 10 |
| 19 | **Lessons learned** (rubric line 7, 5 points). Claude added a section of facts from the build to the report draft and a slide to the outline. | They stay as source facts; Tingyu writes the text and adds the team's own. | Edit the two `.template.md` files. | 0 |

## Your 90 minutes, suggested

1. Read this page (10). 2. Push (1) and share `data/exports/` (5). 3. Send the team message below (5). 4. Skim `report_draft.md` and `slides_outline.md` for anything you disagree with (20). 5. Ask the team for pair-programming, sprint and LaTeX evidence; make the repository public; GenAI certificate (15). 6. Optional: re-label LSH pairs (10). 7. Tuesday: rebuild `dist/`, run the number check on the exported report and slides, upload to Canvas (25). That is about 90 with no spare; the optional re-labeling is the item to drop.

## Draft message to the team (you send it; edit freely)

> Update on the final project. The lake, results and checks are on branch `final-lake`. For Tingyu: `docs/final/report_draft.md` is a section-by-section skeleton with every number filled in (please write the text in your own words; lines marked TODO need you), `docs/final/slides_outline.md` is the same for 15 slides, figures are in `docs/final/figures/`, and `docs/final/RUBRIC_EVIDENCE.md` is the rubric appendix, already in the Canvas order; ten of its rows are open and need us (talk, slides, LaTeX file, literature survey, and evidence of pair programming and sprints: please send what you have). Do not type numbers by hand: copy them from the draft. For Wanru and Zhenni: your input files are in the shared folder (schemas in `docs/final/HANDOFF_TEAM.md`). So that we are covered, there are fallback notebooks for LSH and privacy in `notebooks/fallback/`; yours replace them if they are in the repo by Monday 9 PM. Please also confirm your CRediT row in the draft.
