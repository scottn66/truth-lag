# Writing and code style for EC HW2

Our team works in English, and English is not everyone's first language. Every file must be easy to read for a semi-technical reader. These rules apply to docs, notebooks, code comments and the report.

## Writing
1. Use short sentences (about 20 words or fewer), with one idea in each sentence.
2. Use plain words. Write "use", not "leverage", and "show", not "showcase".
3. Do not use idioms or slang, such as "under the hood", "low-hanging fruit" or "out of the box".
4. Define each technical word once in `GLOSSARY.md`. Then always use the same word for the same thing.
   - Say **revert**, not "rollback / undo / revert" mixed together.
   - Say **history cohort** and **live cohort**, not H and L.
   - Say **Mongo Q1–Q5** and **Cypher Q1–Q5**. These are numbered as in the spec, sections 3 and 4.
   - Say **RQ1** and **RQ2** for the two research questions of the spec. "Q1" alone is not clear.
   - Say **stream label** (from EventStreams) and **dump label** (from the History dump), not "live label".
5. Give numbers with their units, for example "3.8 hours", "300,564 revisions" or "557 MB".
   - Do not type a number that `report/FACTS.md` can change. Name the FACTS key instead, for example "late_reverts_rows in report/FACTS.md".
   - A number from a raw file is fine if you label it "raw file, before clean-up".
6. **Times.** Data times are in **UTC**. Schedule times are in **PT** (Pacific Time). Always write the time zone. Dates use the format YYYY-MM-DD.
7. Steps are numbered. Each step shows the exact command and what you should see after you run it.
8. The words "lane", "agent", "contract" and "fan-out" are for the build log only. Do not use them in team documents.

## Words to avoid in the report
These words make text sound machine-written. Our proposal lost points for that.
- Avoid: delve, tapestry, landscape, realm, robust, seamless, leverage, pivotal, crucial, holistic, synergy, "in today's fast-paced world", "it is worth noting", "plays a vital role", "a testament to", "navigate the complexities".
- Write simple English with **our own numbers**. That is better than polished text.
- If you use a translator or an AI tool to improve your English, that is fine. List it in the GenAI table in the report.

## Notebooks
- At the top of each notebook, put a 4-line box: **Question / Answer / Time to run / Needs**.
- Above every code cell, put a short markdown cell with **What** (what the cell does), **Why** (why we need it) and **You should see** (the expected output).
- The last cell checks the key numbers against `report/FACTS.md` and prints `OK` or `DIFFERENT`.
- The first code cell prints `DATA_VERSION`.
- In `report/FACTS.md` every number is **FINAL** (will not change) or **PROVISIONAL** (depends on the live cohort until 2026-10-27 00:05 UTC). Comparison timings labelled "draft" are also PROVISIONAL.
- Never print a password or a connection string.
- Commit notebooks **with their outputs**, so teammates can read the results on GitHub without running anything.

## Code
- Every script starts with a docstring. It says what the script is for, what it reads, what it writes, and how to run it (with the exact command).
- Comments explain **why**, not what.
- Every rule and every path comes from `config.py`. Never type a window, a threshold or a path in two places.
- Write output files safely. First write `name.tmp`, then rename it to the final name. Then write `_SUCCESS_<step>.json` with the row counts.
- All times inside the code are timezone-aware UTC.
- Human editors appear only as pseudonyms (for example `editor_7f3a2b1c9d`: `editor_` + 10 hex digits) in screenshots, figures and the report. Bots are named.
  - The pseudonym is a keyed hash (HMAC-SHA256 with `ALIAS_SECRET` from `ec-hw2/.env`). It is a display mask on public Wikipedia data, not anonymization: a rev_id still leads to the edit on Wikipedia.

## Safety rules (everyone, including AI tools)
- Never stop, restart or change the capture on the VPS (`truthlag-capture-a`, `truthlag-capture-b`).
- Never open Wikimedia EventStreams connections from your laptop. The VPS needs both connection slots.
- Never use `rsync --delete`. The raw stream files cannot be downloaded again.
- Never run `docker compose down -v`, because it deletes the databases.
- Never commit `ec-hw2/.env` or anything in `data/`.
- Do not use the `timeout` command; it does not exist on macOS.
