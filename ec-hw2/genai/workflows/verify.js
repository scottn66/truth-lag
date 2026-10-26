export const meta = {
  name: 'truthlag-hw2-verify',
  description: 'Adversarial review of the Truth Lag EC HW2 build: 7 independent reviewers try to refute what was built',
  phases: [{ title: 'Verify', detail: '7 independent reviewers, each with one lens' }],
}

// Word-for-word record of the review prompts (GenAI disclosure). Claude Code, claude-opus-5-5, 2026-10-24.

const FINDINGS = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    checked: { type: 'array', items: { type: 'string' } },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          title: { type: 'string' },
          file: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
          reproduced: { type: 'boolean' },
        },
        required: ['severity', 'title', 'file', 'evidence', 'fix', 'reproduced'],
      },
    },
  },
  required: ['lens', 'checked', 'findings'],
}

const COMMON = `You are an independent reviewer of a student project: Truth Lag EC HW2 (SJSU DATA 226, Group 9), a NoSQL mini project that answers "which English Wikipedia edits get reverted, how fast, and who reverts whom" in MongoDB and Neo4j, compared with SQL. Repo: /Users/scottnelson/Desktop/226/truth-lag (branch ec-hw2). The code was written by AI agents a few hours ago. Your job is to REFUTE it: find real bugs, wrong numbers, wrong definitions, missing deliverables and confusing docs. Default to doubt; a claim is only true if you checked it yourself.

Read first: ec-hw2/SPEC.md (the assignment), ec-hw2/config.py (all rules), ec-hw2/DATA_MODEL.md (all tables, collections and definitions), ec-hw2/STYLE.md. The approved plan is ec-hw2/genai/APPROVED_PLAN.md. Data is in data/ (git-ignored). MongoDB (mongodb://localhost:27017, database truthlag) and Neo4j (bolt://localhost:7687, credentials via config.py, never print them) are running. Python: .venv/bin/python from the repo root.

Rules:
- READ-ONLY review. Do not edit any file in the repo. You may write scratch files ONLY under data/verify/<your lens>/ (create it). Do not run the project's loaders or writers (load_mongo.py, load_neo4j.py, export_graph.py, load_sql.py, run_*.py, compare.py, parse_*.py, label_live.py, late_reverts.py, speed_layer.py, build_*.py, make_figures.py, refresh_live.sh, release_data.sh): they overwrite outputs. You MAY import their functions in your own scratch script, and read their outputs.
- Never write to the databases (read queries only). In Neo4j do not call gds.*.write or any CREATE/MERGE/SET/DELETE. GDS stream calls on a temporary projection are OK if you drop the projection afterwards.
- Never ssh, never rsync, never open Wikimedia EventStreams. Do not use the "timeout" command (not on macOS).
- Prefer independent re-computation (your own pandas/SQL code from the input files) over reading the project's own code.
- Report each finding with: severity (high = wrong result or missing deliverable; medium = misleading or fragile; low = polish), the file, concrete evidence (numbers, line numbers, query output), a precise fix, and reproduced = true only if you saw it happen by running something.
- Do not report style nits as high. Do not pad. If something is correct, list it under "checked".`

const LENSES = {
  etl: `LENS: ETL meaning (history and live cohorts, labels, late reverts).
1. History: from data/history/enwiki_rev_ns0_2026-09-08_10.parquet (all strings) recompute, with your own code: rows after the filters (window, historical namespace 0, null revisions), revert rates by user kind (reverted = identity reverted AND seconds <= 20 days), median time to revert, the number of revert links. Compare with data/tables/history_revisions.parquet, history_revert_links.parquet and history_summary.json. Check the reverter self-join on 30 random reverted rows by looking them up in the slim file yourself.
2. Live: from data/parsed/page_change.parquet and the raw files under data/raw/mediawiki.page_change.v1, pick 100 random live-cohort revisions and 50 random revert events. Recompute by hand which revisions each revert covers (the rule in DATA_MODEL.md section 3, including the 2026-10-24 fix 'R.rev_id <= newest_id'), and compare with data/tables/live_revert_links_all.parquet and live_revert_links.parquet. Check that the first EXACT covering revert is chosen, T_s and K_s, within_followup, the window [2026-10-20, 2026-10-23) UTC, dedupe on meta.id, unique rev_id, timezone handling.
3. Check the agreement between the range-cover labels and mw-reverted tags (data/parsed/tag_events.parquet): of the live revisions with an mw-reverted addition, how many have a covering revert? Explain the misses (sample 10).
4. Late reverts: take 20 random rows of data/tables/late_reverts.parquet and check each by hand: the September revision exists in the slim file, the dump says not reverted, the covering event or tag is real and covers it, the class is right.
5. Check data/tables/_SUCCESS_live.json: provisional flag and newest meta_dt are honest.`,
  mongo: `LENS: MongoDB correctness.
1. Check that the documents in collection revisions match DATA_MODEL.md section 4 (sample 5 history + 5 live; all fields, types, nulls), and that the indexes exist (list them).
2. For each query file in ec-hw2/queries/mongo/*.json, run the pipeline yourself (read-only aggregate, no $merge/$out) and recompute the same answer independently with pandas from data/tables/*.parquet. Compare: Q1 revert rate by hour x user kind; Q2 top 20 contested pages (DATA_MODEL section 7: definition, tie order, float score); Q3 time-to-revert buckets (boundaries, default bucket empty); Q4 bot vs human made/received shares; Q5 known-by shares and the risk deciles (n, revert rate, median T, residual with Wilson CI); compare_mutual_reverts pairs. Report every mismatch with numbers.
3. Check results/mongo_*.csv/.md equal what the pipelines return now.
4. Check the chart collections (chart_q1_hour_kind, chart_q3_time_to_revert, chart_q5_known_by, chart_q5_risk_deciles) exist with the fields listed in DATA_MODEL.md section 4, including bucket_sorted and wait_sorted.
5. Atlas privacy: import load_mongo.atlas_documents() in a scratch script and scan 20,000 generated documents of each collection: no human user name, no human 'u:<id>' key, user.id empty; bots keep names. (Do not connect to Atlas.)
6. Check that each query file's pipeline can be pasted into Atlas Data Explorer (Extended JSON; $date etc.) and that the description says how.`,
  cypher: `LENS: Neo4j / Cypher / GDS correctness.
1. Compare node and relationship counts in Neo4j with data/neo4j/import/*.csv and with MongoDB (history revisions and revert_links with within_followup and by_other).
2. Run each query in ec-hw2/queries/cypher/q*.cypher and compare_top_contested.cypher yourself (read-only; for Q2/Q3 use only gds.*.stream on a temporary projection with a unique name and drop it). Compare: Q1 mutual pairs vs an independent pandas computation from data/tables/history_revert_links.parquet (DATA_MODEL section 7); compare_top_contested vs Mongo Q2 / pandas; Q4 and Q5 definitions vs what the files say.
3. Check the PageRank direction: is a REVERSE projection really ranking 'editors who revert many editors' on reverter->reverted edges? Check Louvain/WCC settings (orientation, weights, concurrency <= 4).
4. Check the Cypher syntax is current (no CALL { WITH row }, no CREATE CONSTRAINT ON ... ASSERT, no gds.graph.project.cypher, no apoc.load.csv).
5. Check aliases: the same editor key gets the same alias in Neo4j and in results/mongo_*.csv; no human names or keys in results/cypher_*.csv or results/figures/neo4j_edit_war_example.png's source data.
6. Check load.cypher would work in Neo4j Desktop as written (paths, :auto, casts).`,
  comparison: `LENS: The three-engine comparison (spec section 5) and SQL.
1. Read ec-hw2/comparison/compare.py, ec-hw2/queries/sql/*.sql, results/comparison.md and comparison.csv.
2. Re-run the 6 comparison queries yourself (Mongo JSON pipelines, Cypher files, SQL files against data/tables/truthlag.sqlite; read-only) and check that the three engines really return identical ordered results (scores rounded to 6).
3. Check fairness: do the three versions of each question do comparable work (same filters, same indexes available)? Is the timing method sound (warm-up, median of 7, same machine, what runs in a VM)? Is the lines-of-code count consistent across engines? Are the 'modeling pain' notes and scores supported by the query texts?
4. Check that results/comparison.md labels the timing draft or final honestly, and that the 'Candidate findings' are facts, not conclusions.
5. Check the SQLite tables match DATA_MODEL.md section 6.`,
  readability: `LENS: Readability for the team (4 semi-technical teammates; English may be a second language).
Read ec-hw2/README.md, GLOSSARY.md, PROGRESS.md, STYLE.md, DATA_MODEL.md, guides/*.md, scaleout/SHARDING.md, report/REPORT_SKELETON.md, report/FACTS.md, report/references.md, ingest/README.md, and the 5 notebooks in ec-hw2/notebooks/ (read the .ipynb JSON: markdown and outputs).
Check against STYLE.md: short plain sentences, no idioms, every term defined in GLOSSARY.md, the same word for the same thing (history cohort / live cohort, revert, Mongo Q1-Q5, Cypher Q1-Q5), numbered steps with exact commands and expected output, time zones written, the words lane/agent/contract/fan-out absent from team docs, every notebook has the 4-line top box and a What/Why/You should see cell above every code cell, the last notebook cell checks FACTS.md, no secrets printed, no human editor names anywhere (bots are fine).
Also check: every relative link in README.md and the guides points to a file that exists; numbers quoted in README/GLOSSARY/PROGRESS/guides agree with report/FACTS.md (list each mismatch); leftover 'TODO' lines; the 中文 columns in GLOSSARY.md (flag translations that are clearly wrong or misleading); whether a new teammate can find their role's files in under 5 minutes. Give the 10 most useful fixes, most important first.`,
  coverage: `LENS: Grading coverage.
Go item by item through ec-hw2/SPEC.md sections 1-10 and the plan's 'Never cut' list (ec-hw2/genai/APPROVED_PLAN.md and ec-hw2/PROGRESS.md), and check that the repo really delivers each one with evidence (file paths). Especially: section 3 (MongoDB indexes; exactly the five aggregation topics; Atlas free tier + documented shard key; 2+ Atlas Charts prepared), section 4 (the graph model, LOAD CSV from a MongoDB CSV export, exactly the five Cypher topics, Browser screenshots guide), section 5 (same 2 questions in Mongo, Cypher and SQL with lines of code, query time, modeling pain, top 5 findings), section 6 (file names: ingest/, load_mongo.py, export_graph.py, load_neo4j.py, queries/; docker-compose.yml bonus; LLM prompts documented), section 7 (every report heading present word for word in report/REPORT_SKELETON.md, the criteria map table, the reuse note, the mandatory GenAI Q&A frame with the yes/no question, model, prompt, question number and help given), section 8 and section 10 ('Done =').
Also check the four proposal-feedback fixes are visible to a grader (motivation built from our own example, 12+ new verified papers, a gap table with search method, one concrete end-user persona with numbers), and that REPORT_SKELETON.md contains NO narrative paragraphs written by Claude in the owners' sections (the team must write those in their own words) - quote any that you find. Check the GenAI record in ec-hw2/genai/ is complete and word for word. List what is missing or weak, with the smallest fix for each.`,
  citations: `LENS: Citations. Read ec-hw2/report/references.md. For EVERY paper and every 'Citable Wikimedia fact', check with web search / fetch (publisher page, doi.org, Crossref API https://api.crossref.org/works/<doi>, Semantic Scholar, OpenAlex, PLoS, arXiv) that the title, authors, venue, year, volume/pages and DOI are correct, and that the one-sentence summary of what the paper showed is fair (read at least the abstract). For each Wikimedia fact, open the URL and check the quote is really there. You may use the web for this lens only. Report each wrong or unverifiable item as a finding (high if the paper or DOI does not exist or the summary is false; medium for wrong metadata; low for formatting). Also check that none of the papers is on the exclusion list in ec-hw2/genai/prompts/build_literature.md, and that the gap table cells match what the papers did.`,
}

phase('Verify')
const results = await parallel(Object.entries(LENSES).map(([key, prompt]) => () =>
  agent(COMMON + '\n\n' + prompt, { label: 'verify:' + key, phase: 'Verify', schema: FINDINGS })))
return results.filter(Boolean)
