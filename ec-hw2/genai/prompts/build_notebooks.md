# Prompt given to the build agent "notebooks"

Tool: Claude Code Workflow (model claude-opus-5-5), run 2026-10-24. Source: ec-hw2/genai/workflows/build.js (this text is generated from it, word for word).

```text
You are building one part of the Truth Lag EC HW2 project (SJSU DATA 226, Group 9: a NoSQL mini project that answers "which English Wikipedia edits get reverted, how fast, and who reverts whom" in MongoDB and Neo4j, compared with SQL). Today is 2026-10-24 (UTC). The repo is /Users/scottnelson/Desktop/226/truth-lag on git branch ec-hw2. Work ONLY inside this repo.

Read first (all short): ec-hw2/SPEC.md (the assignment), ec-hw2/config.py (every path, window and rule: import it, never re-type a rule), ec-hw2/DATA_MODEL.md (every table and collection with its columns: follow it exactly), ec-hw2/STYLE.md (writing and code rules), ec-hw2/ingest/history_columns.py (types for the dump columns). The approved plan is /Users/scottnelson/.claude/plans/https-github-com-scottn66-truth-lag-this-mutable-whistle.md (read the parts about your work).

Environment: Python 3.12 venv at .venv. Run '.venv/bin/python ...' from the repo root. Installed: pandas 2.3, pyarrow, pymongo, neo4j (driver 6), matplotlib, tabulate, pytest, jupyter, nbconvert, ipykernel, python-dotenv. MongoDB 8.0 (mongodb://localhost:27017) and Neo4j 2026.10.1 with GDS + APOC (bolt://localhost:7687, Browser http://localhost:7474) run in Docker via Colima (containers truthlag-mongo-1 and truthlag-neo4j-1). Credentials are in ec-hw2/.env and config.py loads them: never print them. Data is in data/ (git-ignored): data/history (VPS-filtered dump as Parquet, ALL columns are strings), data/raw (copy of the live capture). The live capture runs on a VPS; the copy in data/raw was synced at the start of this build.

Hard rules:
- Touch only the files listed for your part. If you need a change in a shared file (config.py, DATA_MODEL.md, STYLE.md, ec-hw2/requirements.txt, ec-hw2/docker-compose.yml, ingest/history_columns.py), do NOT edit it: describe the change in shared_change_requests and work around it locally if you can.
- No git commands that change anything (no add, commit, checkout, stash, reset). No package installs (no pip or uv install). Never run "docker compose down -v" and never remove containers or volumes.
- Never ssh to the VPS, never run rsync, never open Wikimedia EventStreams connections, and never call Wikimedia web APIs. (Only the literature part may use the web, for papers.)
- Never use the "timeout" command (it is not on macOS). Run long jobs in the background with output to a log under data/logs/ and check the log.
- Never delete or rewrite anything under data/raw or data/history.
- Write output files safely: write <name>.tmp, then os.replace to the final name, then write a _SUCCESS_<step>.json next to it with row counts.
- Every script starts with a docstring: purpose, inputs, outputs, and the exact run command. Use plain short English in comments and docs. All times are timezone-aware UTC. A script in a sub-folder of ec-hw2 imports config with sys.path.insert(0, str(Path(__file__).resolve().parents[N])) (N = depth to ec-hw2) and then "import config".
- Put your tests in ec-hw2/tests/test_<part>.py with tiny synthetic fixtures that use the same column names and types as the real files. Run them with '.venv/bin/python -m pytest ec-hw2/tests/test_<part>.py -q'. Create ec-hw2/tests/__init__.py only if it does not exist.
- Human editors must appear only as pseudonyms in any committed result, figure or sample (bots keep their real names). Page titles are fine.
- At the end, run your code on the real data, check that the numbers make sense, and report honestly: what works, what does not, and every number you saw. Do not claim something works unless you ran it.

Return the structured result: part, files you created, commands that ran OK, key numbers (name/value), issues (anything wrong, surprising or unfinished), shared_change_requests, and notes_for_docs (facts the teammates should know, in plain English).

YOUR PART: The notebooks, the report skeleton and FACTS (checked later by the Report+GenAI role; each notebook is checked by its role).
Everything else is built now. Read: results/*.md and *.csv, data/tables/_SUCCESS_*.json and *_summary.json, results/comparison.md, results/sharding.md, report/references.md, README.md, GLOSSARY.md and PROGRESS.md (all made by other parts).
Create:
- ec-hw2/notebooks/01_data.ipynb, 02_mongodb.ipynb, 03_neo4j.ipynb, 04_comparison.ipynb and 05_truth_lag.ipynb
- ec-hw2/report/FACTS.md and ec-hw2/report/REPORT_SKELETON.md (+ .docx)
- ec-hw2/report/figures/architecture.mmd + architecture.png
- results/figures/*.png (charts)
Update README.md only where it has 'TODO(after build)' lines (fill them; do not rewrite the rest).
- **Notebook rules** (STYLE.md):
  - a top box: Question / Answer (the number) / Time to run / Needs
  - the first code cell sets up the paths (sys.path to ec-hw2) and prints config.DATA_VERSION
  - a markdown cell with What / Why / You should see above every code cell
  - never print secrets; pseudonyms for human editors
  - the last cell compares the key numbers with FACTS.md and prints OK or DIFFERENT
  - Notebooks CALL the project scripts and functions or read their outputs; do not re-implement logic.
  - Keep each one under about 2 minutes when the databases are up.
- **Execute every notebook** with '.venv/bin/jupyter nbconvert --to notebook --execute --inplace ec-hw2/notebooks/NN_x.ipynb'. If the kernel is not the venv, register it with '.venv/bin/python -m ipykernel install --user --name truthlag-hw2' and add --ExecutePreprocessor.kernel_name=truthlag-hw2. Fix errors until all 5 run.
- **Notebook contents:**
  - **01_data:**
    - where the data comes from: the VPS capture + the filtered dump, rsync, no live connections from laptops
    - counts per cohort and the filters that dropped rows
    - capture coverage + gaps
    - sanity checks: the history count vs Wikistats (298,802 content edits Sep 8-10), the non-bot revert rate, the median T
    - the definition-gap table: dump label vs mw-reverted tag agreement by T bucket; live tag confirmation by range size (<= 15 / > 15)
    - one real revisions document, with pseudonyms
  - **02_mongodb:**
    - the schema and indexes (list them from the local DB)
    - the 5 pipelines (print each JSON) and their results as text tables, each with 1-2 plain sentences of facts on what it means
    - the timings
    - the Atlas status: if ATLAS_URI is set; otherwise say "Atlas not loaded yet"
  - **03_neo4j:** the graph model (node and relationship counts), the 5 Cypher queries (print the text) with their results, and the edit-war picture.
  - **04_comparison:** results/comparison.md, the equality checks, the timings (with the draft/final label) and the modeling notes.
  - **05_truth_lag:** the truth-lag preview.
    - the known-by curves for both cohorts (a figure)
    - the RAG-crawler decision table: wait time -> share of eventual reverts already visible, by risk decile, with n and the 95% CI
    - the late-revert case study: counts and 3 examples (pseudonyms; page titles are fine)
    - clearly labelled PROVISIONAL if the live labels are not final (read _SUCCESS_live.json)
- **Charts** follow good chart practice. Load the 'dataviz' skill if your tools allow. Otherwise: a clear title that states the finding, labelled axes with units, no 3D, a colour-blind-safe palette, direct labels, a light grid. Save PNGs to results/figures/ at 150 dpi.
- **FACTS.md** is one table: key | value | unit | source file | FINAL or PROVISIONAL. PROVISIONAL means it depends on the live cohort until 2026-10-27 00:05 UTC. Include every number a teammate needs to write their section:
  - cohort sizes, revert rates, median T, % within 1 h / 1 d
  - the bot share of reverts made and received
  - top contested page examples, the number of mutual pairs, the largest community size
  - comparison timings + lines of code
  - the sharding distribution
  - late-revert counts by class
  - the decision-table headline numbers
  - one concrete, non-sensitive example page from the history cohort with a short revert timeline, for the Motivation
- **REPORT_SKELETON.md:**
  - The spec section 7 headings, word for word and in order: Abstract, Motivation, Data + links, Architecture/workflow diagram, Mongo section, Neo4j section, Results/insights, Comparison top 5, Technical difficulties, Best practices + key learnings, Criteria map table, Reuse note, Mandatory GenAI Q&A.
  - For EACH heading: the owner role, a word target, a facts box (FACTS keys + figure files), 3 guiding questions, and an '[OWNER: write 3-6 short sentences ...]' line.
  - CLAUDE WRITES NO NARRATIVE PARAGRAPHS: our proposal lost points because it read as AI-written.
  - You MAY draft only these mechanical parts, each tagged '[drafted by Claude Code; checked by <name>, <date>]':
    - **Data + links:** the dump file URL, its size (557,344,652 bytes), the download date (2026-10-24), the EventStreams stream URLs and the VPS filter script name. Licenses: the History dump is CC0; EventStreams has no stated license, so link it.
    - **The architecture figure:** embed report/figures/architecture.png. The Mermaid source in architecture.mmd shows: VPS capture -> rsync -> Mac -> parse -> Parquet -> MongoDB -> CSV -> Neo4j / SQLite, and dump -> VPS filter -> rsync. Render it with '.venv/bin/python' + mermaid-cli via 'npx -y @mermaid-js/mermaid-cli' using the installed Google Chrome (set PUPPETEER_SKIP_DOWNLOAD=1 and a puppeteer config with executablePath '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'). If that fails, draw it with matplotlib.
    - **The "Where we differ from the spec, and why" table:**
      - page_change.v1 instead of recentchange/revision-create
      - two cohorts, because the 2026-10 dump appears in November
      - live label = the 4-day stream label
      - the capture runs on a VPS and the data comes by rsync
      - REVERTED has page_id
      - Atlas free tier = M0
      - IN_CATEGORY skipped
      - Bloom is not on Community, so Neo4j Browser is used
    - **Query blocks** for the Mongo and Neo4j sections: the code + the first 5-10 result rows as text tables.
    - **The criteria map table:** each spec section 8 row -> file or figure evidence + 'as in spec / changed'.
    - **The Reuse note frame:** what carries over to the final project (capture, parsers, labels, revert_links, page_hour); Kafka and Spark come in the final project.
    - **The "What we changed after the proposal feedback" table:**
      - Motivation 6/10 -> human-written, from our own example
      - Literature 7/10 -> 12+ new verified papers in references.md
      - Novelty 8/10 -> gap table + search method + our numbers
      - Impact 9/10 -> one persona (a RAG-crawler engineer) + the decision table
    - **The GenAI Q&A frame:**
      - the course question "Did you find or come across solutions to similar problems by using Generative AI or other sources?", answered Yes
      - a table with the columns: spec item # | tool + exact model ID (Claude Code, claude-opus-5-5) | verbatim prompt or link (ec-hw2/genai/prompts/...) | help given | what a person checked
      - a row for each of the 4 members to fill: Scott Nelson, Tingyu Lee, Wanru Hsiao, Zhenni Dai
      - a "Who did what" table frame
  - **Hints for the owners:**
    - Motivation: start from the example page in FACTS and its revert timeline, then half a page of related work from report/references.md.
    - Novelty: a placeholder for the search-method sentence, plus the gap table from references.md.
    - Impact: a placeholder for the RAG-crawler engineer persona, plus the decision table from notebook 05.
- Convert REPORT_SKELETON.md to report/REPORT_SKELETON.docx with pandoc (embed the PNG figures), so the Report+GenAI owner can import it into Google Docs.
```
