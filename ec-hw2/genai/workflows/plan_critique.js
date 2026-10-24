export const meta = {
  name: 'truthlag-hw2-plan-critique',
  description: 'Read-only adversarial critique of the draft EC HW2 plan from four lenses',
  phases: [{ title: 'Critique', detail: 'four independent read-only reviewers, each trying to find what breaks' }],
}

const CRIT_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          issue: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['issue', 'severity', 'evidence', 'fix'],
      },
    },
    keep: { type: 'array', items: { type: 'string' } },
  },
  required: ['lens', 'findings', 'keep'],
}

const CONTEXT = `You are reviewing a DRAFT implementation plan before it is executed. STRICTLY READ-ONLY: do not create, modify or delete any file; do not install anything; do not start servers. Network GETs to public docs and public Wikimedia endpoints are allowed (User-Agent "TruthLag/0.1 (SJSU DATA 226 Group 9; class project)", never an email).
Read these first:
- Draft plan: /Users/scottnelson/.claude/plans/https-github-com-scottn66-truth-lag-this-mutable-whistle.md
- Assignment spec: /Users/scottnelson/Desktop/226/truth-lag/EC_HW2_TruthLag_Spec.md
- Repo files: /Users/scottnelson/Desktop/226/truth-lag/README.md, ingest/collect_eventstreams.py, docs/schema_and_warehouse.md, notebooks/00_access_points.ipynb, requirements.txt, .gitignore
Background: today is Fri 2026-10-23 ~20:00 PT; due Thu 2026-10-29 4:29 PM PT. Team of 4 (Scott, Tingyu, Wanru, Zhenni), semi-technical, possible language barrier; owners TBD. User decisions: Claude builds a full working MVP and owners verify, do the UI steps (Atlas Charts, Neo4j screenshots) and write their report sections in their own words; Colima + Docker CLI on Scott's Mac (no Docker/Java now, ~22 GB free disk, 16 GB RAM); data design = History cohort Sep 8-10 from the 2026-09 dump + live cohort Oct 20-22 from EventStreams page_change.v1 + revision-tags-change, plus a small late-revert join (case study). The proposal grader said: motivation looked ChatGPT-written (6/10), literature needs more papers (7/10), novelty gap not substantiated (8/10), impact lacks a concrete end-user scenario (9/10).
Your job: find real problems — wrong assumptions, missing steps, logic errors, sequencing bugs, things that will fail or cost the grade — and give a concrete fix for each. Be specific (cite the plan line or spec item). Do not pad: if something is fine, put it in "keep". Rank findings most severe first; at most 12 findings.`

const LENSES = [
  {
    key: 'data-method',
    prompt: `LENS: data and methodology correctness. Check: (1) History identity-revert semantics vs the stream's revision.revert ranges (is_exact, methods, range = all revisions of the page between oldest and newest inclusive?) — are the two labels comparable for the truth-lag preview? (2) The cutoff/censoring rule for cohort H (labels "as of 2026-10-01"; note the 2026-09 snapshot also contains a partial October file with ~16k revision rows up to 2026-10-04 03:42) and the 4-day horizon for cohort L. (3) Late-revert join logic: tag events (mw-reverted added; $wgRevertedTagMaxDepth) and page_change ranges matched to September rev_ids where the dump says not reverted — any double counting, false positives (e.g. edits reverted then restored), or definitional mismatch? (4) Reverter self-join; self-reverts; bots; temporary accounts vs anonymous. (5) Live counters (page_hour with $inc and retractions) — knowledge-time semantics correct? (6) Cohort comparability (Sep vs Oct, Tue-Thu) and whether ~330-380k per cohort is realistic for enwiki ns0 (Wikistats ~172k edits/day all namespaces in Aug 2026). (7) Anything in M1-M5 / N1-N5 definitions that is ill-defined or will produce misleading numbers. Propose precise definitions where needed.`,
  },
  {
    key: 'execution-risk',
    prompt: `LENS: execution risk and critical path. Check: (1) Step 0 capture: Last-Event-ID + since semantics on EventStreams (which wins on reconnect?), the 15-minute server timeout, macOS sleep (caffeinate -s only works on AC power; lid close), restart behavior, bandwidth (~40 GB catch-up, ~7-9 GB/day), disk (22 GB free), gzip append pattern (multi-member gzip), partition-by-event-hour with out-of-order replay, dedupe. (2) Colima on macOS (Darwin 27) via Homebrew, compose plugin wiring, 8 GB VM with Mongo + Neo4j + optional 4-node sharded profile — memory pressure? (3) Neo4j image + APOC + GDS plugin auto-download, import dir mount, LOAD CSV performance for ~400k rows. (4) Atlas M0 limits (512 MB) vs ~700k docs; Charts on views. (5) Workflow orchestration hazards: parallel agents sharing one MongoDB/Neo4j instance and one working tree, shared files (requirements.txt, config.py, compose), long-running data jobs inside agents, partial live data while lane B runs. (6) Timeline realism vs human-only tasks (Atlas account, Charts, screenshots, Canvas) with owners TBD and teammates who have not yet accepted GitHub invites. (7) What is the minimum viable fallback for each failure so "Done" (spec §10) is still met by Thu? Give concrete fixes and ordering changes.`,
  },
  {
    key: 'rubric-coverage',
    prompt: `LENS: grading coverage. Go item by item through the spec (§1-§10, especially §3 MongoDB: indexes, ≥5 pipelines with the exact five topics, Atlas M0 + shard key, ≥2 Atlas Charts; §4 Neo4j: model, LOAD CSV/APOC from a Mongo CSV export, ≥5 Cypher with the exact five topics, Browser/Bloom screenshots; §5 comparison incl. SQL; §6 file names and ec-hw2/ location, docker-compose bonus, LLM prompts bonus; §7 every report section incl. criteria map and mandatory GenAI Q&A; §8 criteria; §10 Done list) and check the plan delivers each with evidence. Also check that the four proposal-feedback items (motivation not AI-sounding, more papers, substantiated gap, concrete end-user scenario) are addressed in a way a grader will notice. Flag anything missing, mis-named, or weakly evidenced, and anything the plan adds that risks the grade (e.g. scope creep). Suggest the smallest change that closes each gap.`,
  },
  {
    key: 'team-process',
    prompt: `LENS: team understandability and process for a semi-technical, possibly multilingual team with owners TBD. Check: (1) Can each teammate, on their own laptop (Windows or Mac, maybe without Docker), understand and verify their lane from the docs/notebooks the plan describes? Is there a no-install reading path and a minimal run path per lane? (2) Data access for teammates (raw stream data exists only on Scott's Mac; derived data via a private GitHub Release; Atlas as shared copy) — workable? Any license/size/privacy issue? (3) Are STYLE.md/GLOSSARY/PROGRESS/notebook conventions enough for a language barrier (e.g. diagrams, consistent terms, expected outputs, short sentences)? What concrete additions would help most without bloat? (4) Git/PR workflow for people new to GitHub (pending invites, branch, draft PR, how to comment/review). (5) Fairness/uniform-workload optics given Claude builds the MVP: what should each owner concretely do so their contribution is real and visible, and how does the GenAI disclosure stay honest (who wrote what)? (6) Anything in the plan that would confuse teammates (jargon in the plan's own names, too many files, unclear entry point). Give specific, minimal fixes.`,
  },
]

phase('Critique')
const results = await parallel(LENSES.map(l => () =>
  agent(`${CONTEXT}\n\n${l.prompt}`, { label: `critique:${l.key}`, phase: 'Critique', schema: CRIT_SCHEMA, agentType: 'Plan' })
))
const ok = results.filter(Boolean)
log(`${ok.length}/${LENSES.length} critiques returned; ${ok.reduce((n, r) => n + r.findings.length, 0)} findings`)
return ok
