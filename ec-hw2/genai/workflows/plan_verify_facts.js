export const meta = {
  name: 'truthlag-hw2-verify',
  description: 'Read-only verification of data, database and runtime facts for the Truth Lag EC HW2 plan',
  phases: [{ title: 'Verify', detail: 'parallel read-only fact checks against official docs and public endpoints' }],
}

const FACT_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    facts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          status: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
          evidence: { type: 'string' },
          source: { type: 'string' },
        },
        required: ['claim', 'status', 'evidence', 'source'],
      },
    },
    implications: { type: 'array', items: { type: 'string' } },
  },
  required: ['topic', 'facts', 'implications'],
}

const COMMON = `You are verifying facts for a student data-engineering project plan (SJSU DATA 226, Group 9, "Truth Lag" EC HW2: a MongoDB + Neo4j mini project on English Wikipedia revert data; today is 2026-10-23).
STRICTLY READ-ONLY: do not create, modify, or delete any file anywhere (not even in /tmp); pipe downloads to stdout only; do not install anything; do not start servers or containers.
Network GETs to public documentation and public Wikimedia endpoints are fine. For any request to wikimedia.org / wikipedia.org use the User-Agent "TruthLag/0.1 (SJSU DATA 226 Group 9; class project)" and never put an email address in it. Be polite: serial requests, no hammering.
Prefer official documentation. For each claim: status confirmed / refuted / uncertain, a short concrete piece of evidence (quote or number), and the source URL. Then list implications for the plan. Keep it tight.`

const TASKS = [
  {
    key: 'history-schema',
    prompt: `Topic: MediaWiki History dump TSV schema and release cadence (2026).
(a) Find the official field documentation (Wikitech "Data Platform/Data Lake/Edits/MediaWiki history dumps" or its current URL, the "Mediawiki history" table schema page, and https://dumps.wikimedia.org/other/mediawiki_history/readme.html). Return the ordered field list with 0-based indices.
(b) Cross-check against real data by streaming (no saving): curl -s -A "<UA>" https://dumps.wikimedia.org/other/mediawiki_history/2026-09/enwiki/2026-09.enwiki.2026-10.tsv.bz2 | bunzip2 | python3 -c '...'. Rows have 78 tab-separated columns; an older field list had 77, so identify the extra field. From value patterns we believe: 0 wiki_db, 2 event_entity, 3 event_type, 4 event_timestamp, 5 event_comment, 6 event_user_id, 9 event_user_text, 13 event_user_groups, 15 event_user_is_bot_by, 19 event_user_is_anonymous, 20 event_user_is_temporary(?), 26 event_user_revision_count, 28 page_id, 30 page_title, 33 page_namespace, 34 page_namespace_is_content, 60 revision_id, 61 revision_parent_id, 62 revision_minor_edit, 65 revision_text_bytes, 66 revision_text_bytes_diff, 67 revision_text_sha1, 70 revision_is_deleted_by_page_deletion, 72 revision_is_identity_reverted, 73 revision_first_identity_reverting_revision_id, 74 revision_seconds_to_identity_revert, 75 revision_is_identity_revert, 77 revision_tags. Confirm or correct every index, and say what indices 1, 7, 21 and 22 are. Count rows where 72=='true' and check 73/74 are populated for them; count rows where 75=='true'.
(c) Semantics: exact meaning of revision_is_identity_reverted, revision_first_identity_reverting_revision_id, revision_seconds_to_identity_revert, revision_is_identity_revert (any lookback/window limit?); how bots are flagged (event_user_is_bot_by values); how anonymous and temporary accounts are represented in 2026; whether revision_tags is comma-separated; how null is encoded.
(d) Release cadence: when monthly snapshots are published (2026-09 appeared 05-Oct-2026, 2026-08 on 02-Sep-2026), how many are retained, when 2026-10 is expected, and whether ANY public source of October 2026 enwiki revisions with identity-revert labels exists before Oct 29 2026.`,
  },
  {
    key: 'stream-api',
    prompt: `Topic: Wikimedia EventStreams and MediaWiki Action API semantics.
(a) Fetch the mediawiki page/change JSON schema version 1.12.0 (try https://schema.wikimedia.org/repositories/primary/jsonschema/mediawiki/page/change/1.12.0 and the "latest" variant). Report the exact definition of revision.revert (allowed method values, is_exact, rev_original_id, rev_original_dt, rev_reverted_oldest_id, rev_reverted_newest_id) and whether the reverted set is "all revisions of that page with rev_id between oldest and newest inclusive". Also prior_state.revision.rev_size (to compute size delta), performer.is_temp / is_bot / groups / edit_count semantics, page.namespace_is_content, and whether page_change carries change tags at all.
(b) MediaWiki revert detection: Manual:Reverts and the mw-reverted tag: max depth ($wgRevertedTagMaxDepth default), whether mw-reverted tagging is delayed (e.g. until patrol/approval), and how it relates to MediaWiki History's sha1-based identity revert.
(c) EventStreams docs (Wikitech "Event Platform/EventStreams HTTP Service"): replay retention per stream for since= and Last-Event-ID (we measured ~7 days for page_change.v1 and ~9 days for revision-tags-change), the ~15 minute connection timeout, the User-Agent policy (is a project name + repo URL acceptable without an email?), and any rate etiquette.
(d) Action API: action=query&prop=revisions&revids=... — max revids per request for non-bot clients, useful rvprop values (ids|timestamp|user|userid|size|sha1|tags|comment|flags), how missing or deleted revisions are reported (badrevids, texthidden, etc.), maxlag etiquette and a safe request rate. Give one tiny real example by querying 2 revids: 1380574019 and 1380644875 (read-only GET).`,
  },
  {
    key: 'mongodb',
    prompt: `Topic: MongoDB facts needed for the plan.
(a) MongoDB Atlas free tier (M0) limits as currently documented: storage limit (and whether it counts data+index, compressed or not), max connections, whether sharding is supported (and from which tier), aggregation limitations ($out/$merge, allowDiskUse, server-side JavaScript, $lookup/$graphLookup/$bucket/$facet/$setWindowFields support), whether views (db.createView) work, free clusters per project, and any 2025-2026 tier changes (Flex replacing M2/M5/Serverless).
(b) Atlas Charts: available and free with M0? Can a chart use a MongoDB view as data source? How to export a chart as an image/PNG for a report? Free-tier usage limits?
(c) Sharding: is a hashed shard key on an embedded field such as {"page.id": "hashed"} allowed? Give a minimal docker-compose design for a LOCAL sharded cluster with the official mongo image (state the current major tag, e.g. mongo:8.0): config server replica set + 2 single-node shard replica sets + mongos, with exact init steps (rs.initiate, sh.addShard, sh.enableSharding if still needed, sh.shardCollection), how to show balance (db.collection.getShardDistribution()) and targeted vs scatter-gather queries in explain(). Mention MongoDB 8 options like config shards if relevant.
(d) Confirm that MongoDB 5.0+ allows $lookup with localField/foreignField together with let/pipeline, and that the equality part can use an index on the foreign collection.
(e) Current PyMongo major version and Python 3.12 support; whether mongosh / mongoimport / mongodb-community are installable via Homebrew (mongodb/brew tap) on Apple Silicon.`,
  },
  {
    key: 'neo4j',
    prompt: `Topic: Neo4j facts needed for the plan.
(a) Official Docker image: current tags (5.26 LTS vs calendar versions like 2025.x / 2026.x), community vs enterprise; how NEO4J_PLUGINS='["apoc","graph-data-science"]' works and the needed config (procedures unrestricted/allowlist); GDS community limits (e.g. max concurrency 4); version compatibility between Neo4j and GDS.
(b) LOAD CSV with CALL { ... } IN TRANSACTIONS OF N ROWS (Neo4j 5 syntax, and any newer replacement syntax); the import directory in the Docker image and how to mount it; uniqueness constraint syntax.
(c) Current GDS procedure names and syntax: gds.graph.project (and Cypher projection), gds.pageRank.stream / write, gds.louvain.stream / write, gds.wcc.stream, gds.degree.stream; whether Louvain needs an UNDIRECTED projection; how to project relationship weights (e.g. a count property).
(d) Neo4j AuraDB Free limits (nodes / relationships) and whether GDS or Aura Graph Analytics is available on the free tier in 2026; whether Neo4j Sandbox still exists and includes GDS + APOC (and its expiry); Neo4j Desktop 2 (bundled Java? plugin install); where Bloom / Explore is available (Desktop, Aura, community Docker?).
(e) Current neo4j Python driver version and Python 3.12 support; recommended batched write pattern (UNWIND $rows) for 100k+ rows.`,
  },
  {
    key: 'runtime',
    prompt: `Topic: local runtime on the user's Mac (macOS on Darwin 27, Apple Silicon, 16 GB RAM, 10 CPUs, only ~22 GB free disk; Homebrew, uv and python3.12 present; no Docker; no Java runtime).
(a) Colima + docker CLI + docker-compose via Homebrew: exact install and start commands (e.g. brew install colima docker docker-compose; colima start --cpu 4 --memory 6 --disk 30 --vm-type vz), how the compose plugin is wired (cliPluginsExtraDirs in ~/.docker/config.json), disk footprint, known issues on the newest macOS. Compare briefly with Docker Desktop (license terms for students, install size) and OrbStack.
(b) Read-only checks of this machine: brew list --versions 2>/dev/null | grep -i -E "colima|docker|lima|mongo|neo4j|openjdk|qemu|pandoc"; ls /Applications | grep -i -E "docker|orbstack|neo4j|mongodb|chrome"; ls -d ~/.colima ~/.docker ~/.orbstack 2>/dev/null; /usr/libexec/java_home -V 2>&1 | head -5. Do not install anything.
(c) Python 3.12 support (cp312 macOS arm64 wheels) for pymongo, neo4j, pandas, pyarrow, matplotlib, requests, python-dotenv, jupyter, nbconvert via the PyPI JSON API (https://pypi.org/pypi/<pkg>/json). Also: does the latest PySpark support Python 3.14 (the default python3 here is 3.14.5)?`,
  },
]

phase('Verify')
const results = await parallel(TASKS.map(t => () =>
  agent(`${COMMON}\n\n${t.prompt}`, { label: `verify:${t.key}`, phase: 'Verify', schema: FACT_SCHEMA, agentType: 'Explore' })
))
const ok = results.filter(Boolean)
log(`${ok.length}/${TASKS.length} verification reports returned`)
return ok
