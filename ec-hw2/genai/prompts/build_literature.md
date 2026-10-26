# Prompt given to the build agent "literature"

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

YOUR PART: Literature (all four roles will read it). Create ec-hw2/report/references.md. It answers the proposal grade "Literature 7/10: Please refer to more papers" and "Novelty: could substantiate the gap better". You may use web search and fetch for this part only. Write no other files.
- **Target.** Find at least 12 (aim for 14-18) NEW peer-reviewed papers. None of them may already be cited in either proposal version (exclusion list below). Each must back one of our design choices.
- **Themes** (at least 3 papers each):
  1. revert timing and vandalism repair on Wikipedia
  2. edit wars, conflict and revert networks (graphs of who reverts whom)
  3. bots and live monitoring or streams of Wikipedia
  4. document vs graph vs relational databases (NoSQL comparisons, graph query performance)
  5. Add the original PageRank and Louvain papers.
- **VERIFY EVERY PAPER.** Use web search, the publisher page, doi.org, ACM DL, IEEE Xplore, PLoS, Semantic Scholar or Google Scholar to confirm the title, all authors, venue, year, pages and DOI. Leave out any paper you cannot verify. Never invent a DOI. Mark each paper "Verified" with the URL you checked.
- **Exclusion list** (already cited in a proposal):
  - Steiner, van Hooland & Summers 2013 (MJ no more); Träris & Balsacq 2021
  - Pendyala 2018 (Veracity of Big Data); Pendyala & Hall 2024
  - Carlini et al. 2024 (poisoning web-scale training datasets)
  - Croushore & Stark 2001; Aruoba 2008; Höhle & an der Heiden 2014
  - Priedhorsky et al. 2007; Kumar, West & Leskovec 2016 (hoaxes)
  - Geiger & Halfaker 2013 (When the levee breaks); Flöck, Vrandečić & Simperl 2012 (Revisiting reverts)
  - Trokhymovych et al. 2023; Akidau et al. 2015 (Dataflow); Golab & Johnson 2011; Hellerstein, Haas & Wang 1997
  - Kimball & Ross 2013; Snodgrass 2000; Flajolet et al. 2007 (HyperLogLog); Confluent cp-demo
- **Candidates** (verify; do not assume they are correct):
  - Viégas, Wattenberg & Dave 2004 (history flow, CHI)
  - Kittur, Suh, Pendleton & Chi 2007 (He says, she says, CHI)
  - Suh, Chi, Kittur & Pendleton 2008 (Lifting the veil, CHI); Suh et al. 2007 (us vs. them, VAST)
  - Sumi, Yasseri, Rung, Kornai & Kertész 2011 (Edit wars in Wikipedia, SocialCom/PASSAT)
  - Yasseri, Sumi, Rung, Kornai & Kertész 2012 (Dynamics of conflicts in Wikipedia, PLoS ONE)
  - Brandes, Kenis, Lerner & van Raaij 2009 (Network analysis of collaboration structure in Wikipedia, WWW)
  - Halfaker, Kittur & Riedl 2011 (Don't bite the newbies, WikiSym)
  - Halfaker, Geiger, Morgan & Riedl 2013 (The rise and decline of an open collaboration system, American Behavioral Scientist)
  - Halfaker & Riedl 2012 (Bots and cyborgs, IEEE Computer)
  - Geiger & Ribes 2010 (The work of sustaining order in Wikipedia, CSCW)
  - Tsvetkova, García-Gavilanes, Floridi & Yasseri 2017 (Even good bots fight, PLoS ONE)
  - West, Kannan & Lee 2010 (spatio-temporal analysis of revision metadata, EUROSEC)
  - Potthast, Stein & Gerling 2008 (Automatic vandalism detection in Wikipedia, ECIR)
  - Adler, de Alfaro, Mola-Velasco, Rosso & West 2011 (CICLing)
  - Kiesel et al. 2017 (Spatio-temporal analysis of reverted Wikipedia edits, ICWSM)
  - Keegan, Gergle & Contractor 2013 (Hot off the wiki, American Behavioral Scientist)
  - Vicknair et al. 2010 (A comparison of a graph database and a relational database, ACM SE)
  - Cattell 2011 (Scalable SQL and NoSQL data stores, SIGMOD Record)
  - Angles & Gutierrez 2008 (Survey of graph database models, ACM Computing Surveys)
  - Holzschuher & Peinl 2013 (Performance of graph query languages)
  - Brin & Page 1998 (WWW) or Page et al. 1999
  - Blondel, Guillaume, Lambiotte & Lefebvre 2008 (Fast unfolding of communities, J. Stat. Mech.)
  - Books are allowed but do not count toward the 12.
- **Format of references.md** (plain short English, following ec-hw2/STYLE.md):
  1. A 2-3 sentence intro saying what the list is for.
  2. One table per theme: # | Full citation (IEEE style) | DOI or URL | Verified (URL checked) | What it measured or showed (one plain sentence, max 25 words) | Where we use it (the design choice or query, e.g. Cypher Q1 mutual reverts, Mongo Q3 time to revert, the comparison section).
  3. A "Gap table".
     - Rows: the 6-8 closest works.
     - Columns: uses a live stream? | uses dump labels? | measures time to revert? | compares the live view with the later record? | builds a revert graph? | compares document vs graph databases?
     - Last row: "Our HW2".
     - Base each cell on what the paper actually did, and write "unclear" when unsure.
  4. "Reading batches": split the new papers into 4 batches of about 4, one per role (Data+MongoDB, Neo4j, Comparison+viz, Report+GenAI), matching themes to roles. Add an empty column "Teammate notes (own words)".
  5. "Citable Wikimedia facts", each with its exact URL and a short quote:
     - the MediaWiki History dumps page (monthly snapshots; only the last two kept)
     - Manual:Reverts (mw-reverted only for reverts of 15 or fewer revisions; manual revert detection looks back 15 revisions)
     - the EventStreams HTTP service page (a replay window of 7-31 days; a 15-minute connection timeout)
     - the page/change schema
     - any Wikitech or Phabricator statement that analyses wait weeks for the monthly rebuild, or about an incremental daily table (T424350)
- **key_numbers:** the number of verified new papers per theme.
```
