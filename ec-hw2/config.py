"""One place for every setting and every definition used in EC HW2.

Every script and notebook imports this file. If you want to change a rule
(a time window, the "contested page" rule, a file path), change it HERE only.

How to import it from a script in a sub-folder of ec-hw2/:
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import config
From a notebook in ec-hw2/notebooks/:
    import sys, pathlib; sys.path.insert(0, str(pathlib.Path.cwd().parent)); import config

All data times are UTC. All windows are half-open: [start, end) means
"start is included, end is not".
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# 1. Folders (they work from any folder: we find the repo root first)
# --------------------------------------------------------------------------
HW2_DIR = Path(__file__).resolve().parent          # .../truth-lag/ec-hw2
REPO_ROOT = HW2_DIR.parent                          # .../truth-lag
DATA_DIR = REPO_ROOT / "data"                       # git-ignored, never committed

RAW_DIR = DATA_DIR / "raw"                          # copy of the VPS capture (rsync)
HISTORY_DIR = DATA_DIR / "history"                  # copy of the VPS-filtered dump (rsync)
PARSED_DIR = DATA_DIR / "parsed"                    # stream events turned into Parquet tables
TABLES_DIR = DATA_DIR / "tables"                    # final cohort tables (Parquet + SQLite)
NEO4J_IMPORT_DIR = DATA_DIR / "neo4j" / "import"    # CSV files that Neo4j reads with LOAD CSV
RESULTS_DIR = HW2_DIR / "results"                   # small query outputs, committed to git
FIGURES_DIR = HW2_DIR / "results" / "figures"

DATA_VERSION = "data-v1"   # data-v2 after the live cutoff (Mon 2026-10-26 5:05 PM PT = 2026-10-27 00:05 UTC)
DATA_VERSION_FILE = TABLES_DIR / "DATA_VERSION"   # written by release_data.sh

# --------------------------------------------------------------------------
# 2. Where the data comes from (VPS "vps-coin"; we only READ it)
# --------------------------------------------------------------------------
# The capture runs on the VPS as systemd units truthlag-capture-a / -b.
# Nobody stops, restarts or edits them from this repo.
VPS_HOST = "vps-coin"                     # = its public IP (see ~/.ssh/config), not the Tailscale alias
VPS_BASE = "/opt/truthlag"
VPS_RAW_DIR = f"{VPS_BASE}/data/raw/"
VPS_HISTORY_DIR = f"{VPS_BASE}/data/history/"
RSYNC_FLAGS = ["-az", "--partial"]        # NEVER add --delete: the raw files cannot be fetched again

# Raw file layout (same on the VPS and on the Mac):
#   data/raw/<stream>/dt=YYYY-MM-DD/hour=HH/part-<session>-<n>.ndjson.gz
# Partitions use meta.dt (the time the event was published). Every part file is
# one gzip file written by one capture session. A file that is still open has
# no gzip end marker yet, so readers skip files changed in the last 2 minutes.
RAW_STREAM_DIR = RAW_DIR
RAW_GLOB = "dt=*/hour=*/part-*.ndjson.gz"
OPEN_FILE_GRACE_S = 120
CAPTURE_GAP_S = 120          # a "gap" = two kept events of one stream more than 120 s apart

STREAM_PAGE_CHANGE = "mediawiki.page_change.v1"
STREAM_REVERT_RISK = "mediawiki.page_revert_risk_prediction_change.v1"
STREAM_TAGS = "mediawiki.revision-tags-change"
STREAM_DIRS = [STREAM_PAGE_CHANGE, STREAM_REVERT_RISK, STREAM_TAGS]

# Capture start times (the "since" value of each VPS unit)
CAPTURE_A_SINCE = datetime(2026, 10, 19, 23, 0, tzinfo=timezone.utc)   # page_change + revert risk
CAPTURE_B_SINCE = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)    # tags-change

# History dump, filtered on the VPS by ingest/vps/filter_history.py.
HISTORY_SOURCE_URL = ("https://dumps.wikimedia.org/other/mediawiki_history/2026-09/enwiki/"
                      "2026-09.enwiki.2026-09.tsv.bz2")
HISTORY_SOURCE_BYTES = 557_344_652
HISTORY_SNAPSHOT = "2026-09"
# Outside check (Wikimedia Analytics API, "edits", enwiki, content pages, all editor types,
# daily, 2026-09-08..10): 101,989 + 98,615 + 98,198.
WIKISTATS_CONTENT_EDITS_SEP8_10 = 298_802
HISTORY_COHORT_FILE = "enwiki_rev_ns0_2026-09-08_10.parquet"   # all 78 columns, ns0, Sep 8-10
HISTORY_SLIM_FILE = "enwiki_rev_all_2026-09_slim.parquet"      # all September revisions, 12 columns
# The VPS filter keeps a revision in the cohort file when page_namespace (the CURRENT
# namespace, column 33) is "0". We also require page_namespace_historical == "0"
# (namespace at edit time) so the history cohort matches the live stream.
# IMPORTANT: every column in both Parquet files is a STRING. Cast with
# ingest/history_columns.py (cast_history_frame), never by guessing.
# Note: pyarrow turned some literal strings such as "NA", "NULL", "nan" into null
# when it wrote the Parquet copies. This can blank a few titles or comments; page_id
# and rev_id are never affected.
HISTORY_SLIM_COLUMNS = [
    "revision_id", "page_id", "event_timestamp", "revision_is_identity_revert",
    "revision_is_identity_reverted", "revision_first_identity_reverting_revision_id",
    "revision_seconds_to_identity_revert", "event_user_id", "event_user_text",
    "event_user_text_historical", "event_user_is_bot_by", "page_namespace",
]

# --------------------------------------------------------------------------
# 3. The two cohorts (a cohort = one group of revisions we study together)
# --------------------------------------------------------------------------
HISTORY_WINDOW = (datetime(2026, 9, 8, tzinfo=timezone.utc),
                  datetime(2026, 9, 11, tzinfo=timezone.utc))      # Tue-Thu, [start, end)
LIVE_WINDOW = (datetime(2026, 10, 20, tzinfo=timezone.utc),
               datetime(2026, 10, 23, tzinfo=timezone.utc))        # Tue-Thu, [start, end)
COHORT_HISTORY = "history"
COHORT_LIVE = "live"

HISTORY_FOLLOWUP_DAYS = 20   # "reverted" in history = reverted within 20 days
LIVE_FOLLOWUP_DAYS = 4       # "reverted" in live    = reverted within 4 days
HISTORY_FOLLOWUP_S = HISTORY_FOLLOWUP_DAYS * 86400
LIVE_FOLLOWUP_S = LIVE_FOLLOWUP_DAYS * 86400
# Every history revision is followed at least 20 days: the last one (Sep 10 23:59)
# + 20 days = Sep 30 23:59, before the dump's last revision (Oct 1 01:38 UTC).
HISTORY_DUMP_LAST_REVISION = datetime(2026, 10, 1, 1, 38, 27, tzinfo=timezone.utc)
# The live labels are final only when the capture has passed this time:
LIVE_FINAL_AFTER = LIVE_WINDOW[1] + timedelta(days=LIVE_FOLLOWUP_DAYS, minutes=5)  # 2026-10-27 00:05 UTC

# --------------------------------------------------------------------------
# 4. Shared definitions
# --------------------------------------------------------------------------
# Time to revert T = (time of the reverting revision) - (time of the reverted revision),
# in seconds, for BOTH cohorts. The stream delay K = meta.dt - rev_dt of the reverting
# event is kept separately; the live "known-by" time is T + K.

# Lag grid in seconds (used by Mongo Q3 $bucket and by Q5). Last edge = 20 days + 1 s.
LAG_GRID_S = [0, 60, 300, 900, 3600, 21600, 86400, 172800, 345600, 604800, 1209600, 1728001]
LAG_LABELS = ["<1 min", "1-5 min", "5-15 min", "15-60 min", "1-6 h", "6-24 h", "1-2 d",
              "2-4 d", "4-7 d", "7-14 d", "14-20 d"]
LAG_DEFAULT_BUCKET = "over_20d"   # must stay empty; scripts assert this
WAIT_POINTS_S = {"0": 0, "1 min": 60, "5 min": 300, "15 min": 900, "1 h": 3600,
                 "6 h": 21600, "1 d": 86400, "2 d": 172800, "4 d": 345600}

# User kinds, checked in this order:
#   1. unknown    - the user name is empty (the dump hides it; measured: 3 of 295,016
#                   history cohort rows, 483 of 5,266,843 slim rows)
#   2. bot        - "group" in event_user_is_bot_by (dump) / performer.is_bot (stream)
#   3. temporary  - a logged-out editor. Since 2025-11-04 enwiki gives logged-out
#                   editors temporary accounts named "~2026-12345-67". There are no IP edits.
#   4. registered - everyone else
# The spec's field user.is_anon means "logged out", so is_anon = (kind == "temporary").
# We use the CURRENT bot flag (event_user_is_bot_by) in the dump because the slim
# September file (used for reverters) only has that one; authors and reverters then
# follow the same rule.
USER_KINDS = ["bot", "temporary", "registered", "unknown"]
TEMP_NAME_PREFIX = "~2"


def user_kind(name: str | None, bot_flag: str | bool | None, is_temp: bool | None = None) -> str:
    """Return bot / temporary / registered / unknown (same rule for dump and stream)."""
    if name is None or str(name).strip() == "":
        return "unknown"
    if isinstance(bot_flag, bool):
        if bot_flag:
            return "bot"
    elif bot_flag and "group" in str(bot_flag).split(","):
        return "bot"
    if is_temp is True or str(name).startswith(TEMP_NAME_PREFIX):
        return "temporary"
    return "registered"


def editor_key(kind: str, user_id, name) -> str | None:
    """Stable id for an editor: 'u:<user_id>' (registered, bot) or 't:<name>' (temporary)."""
    if kind == "unknown":
        return None
    if kind == "temporary":
        return f"t:{name}"
    if user_id in (None, "", 0):
        return f"t:{name}"   # should not happen; keeps the key unique anyway
    return f"u:{int(user_id)}"


# "reverted_by_other": the reverter is a different editor from the author.
# Self-reverts count for Mongo Q1, Q3, Q5 ("reverted (any)") but NOT for Q2,
# contested pages, Q4 or graph edges.

# Contested page (computed on the history cohort, bots excluded from edits_p):
#   edits_p            = human (non-bot) revisions on the page
#   revert_actions_p   = distinct reverting revisions, by another editor, that reverted
#                        at least one cohort revision on the page
#   reverted_editors_p = distinct authors on the page who were reverted by someone else
#   score              = revert_actions_p / edits_p   (a float, also in SQL: 1.0 * a / b)
CONTESTED_MIN_EDITS = 10
CONTESTED_MIN_ACTIONS = 2
CONTESTED_MIN_EDITORS = 2
CONTESTED_MIN_SCORE = 0.2
TOP_N = 20
# Order for "top contested pages" in every engine (Mongo, Cypher, SQL):
#   score DESC, revert_actions DESC, edits DESC, page_id ASC
# Engines are compared on (page_id, round(score, 6)).
SCORE_ROUND = 6

# Mutual reverts (an edit war): editor A reverted B AND B reverted A on the SAME page.
# Exact reverts by others only (self-reverts removed).

# Null revisions in the dump (same content as the parent: page moves, protection changes).
# Rule (a): sha1 == parent sha1 when the parent is in the cohort file.
# Rule (b): bytes_diff == 0 AND the comment, after removing a leading "<editor name> "
# (MediaWiki writes "<user> moved page ..."), starts with one of these (case-insensitive).
NULL_REV_COMMENT_PREFIXES = (
    "moved page", "protected", "changed protection", "unprotected",
    "changed content model", "imported",
    "removed protection", "configured pending changes", "reset pending changes",
)
PAGE_PREV_WINDOW_S = 3600    # page_edits_prev_1h looks back 1 hour (both cohorts)

# MediaWiki adds the mw-reverted tag only when a revert covers at most 15 revisions
# ($wgRevertedTagMaxDepth default). Rollback and undo of any size still appear in the stream.
MW_REVERTED_MAX_DEPTH = 15

# Late reverts (case study): September revisions that the dump says are NOT reverted
# but that the October stream shows being reverted. Counts are LOWER BOUNDS because
# we did not watch from Oct 1 01:38 UTC until the capture started.
LATE_TAG_LINK_WINDOW_S = 600   # link an mw-reverted tag event to a covering revert <= 10 min before
LATE_CLASSES = ["exact", "inexact_undo", "method_unknown"]

# Save-time tags for live revisions: tag events up to 60 s after the edit.
SAVE_TIME_TAG_WINDOW_S = 60
MW_REVERTED_TAG = "mw-reverted"

# Revert-risk score (Wikimedia model "revertrisk-language-agnostic")
RISK_DECILES = 10
RISK_MIN_GROUP_N = 100
DECISION_WAITS_S = {"now": 0, "1 h": 3600, "1 d": 86400}

# --------------------------------------------------------------------------
# 5. Databases (values come from ec-hw2/.env; see ec-hw2/.env.example)
# --------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    # .env.atlas first (Atlas onboarding file, never committed), so an empty ATLAS_URI= line
    # in .env cannot hide it. load_dotenv never overwrites a value that is already set.
    load_dotenv(HW2_DIR / ".env.atlas")
    load_dotenv(HW2_DIR / ".env")
except ImportError:   # python-dotenv not installed: use the shell environment
    pass

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "truthlag")
ATLAS_URI = os.environ.get("ATLAS_URI", "")
ATLAS_DB = os.environ.get("ATLAS_DB", "truthlag")
SHARDED_URI = os.environ.get("SHARDED_URI", "mongodb://localhost:27020")
SHARDED_DB = "truthlag_sharded"
SHARD_KEY = {"page.id": "hashed"}
NEO4J_AURA_URI = os.environ.get("NEO4J_AURA_URI", "")   # optional cloud copy (Aura Free has no GDS)
NEO4J_AURA_USER = os.environ.get("NEO4J_AURA_USER", "neo4j")
NEO4J_AURA_PASSWORD = os.environ.get("NEO4J_AURA_PASSWORD", "")
CONTAINERS = {"mongo": "truthlag-mongo-1", "neo4j": "truthlag-neo4j-1"}

# Pseudonyms for human editors: "editor_" + the first ALIAS_HEX hex digits of
# HMAC-SHA256(ALIAS_SECRET, editor_key). The secret lives in ec-hw2/.env (never committed),
# so nobody can rebuild the key from the alias by trying every user id. This is a display
# mask on public Wikipedia data, not anonymization: a rev_id still leads to the edit on
# Wikipedia. Bots keep their real names.
ALIAS_SECRET = os.environ.get("ALIAS_SECRET", "")
ALIAS_HEX = 10
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
SQLITE_PATH = TABLES_DIR / "truthlag.sqlite"
ATLAS_BUDGET_MB = 400          # Atlas free tier limit is 512 MB (uncompressed data + indexes)

# MongoDB collection names
COL_REVISIONS = "revisions"
COL_REVERT_LINKS = "revert_links"
COL_PAGE_HOUR = "page_hour"
COL_PAGE_HOUR_LIVE = "page_hour_live"
COL_TAG_EVENTS = "tag_events"
COL_LATE_REVERTS = "late_reverts"
# Small pre-aggregated collections for Atlas Charts (names are frozen once Charts exist)
CHART_COLLECTIONS = ["chart_q1_hour_kind", "chart_q3_time_to_revert",
                     "chart_q5_known_by", "chart_q5_risk_deciles"]

# --------------------------------------------------------------------------
# 6. Helpers
# --------------------------------------------------------------------------
def ensure_dirs() -> None:
    for d in (PARSED_DIR, TABLES_DIR, NEO4J_IMPORT_DIR, RESULTS_DIR, FIGURES_DIR):
        d.mkdir(parents=True, exist_ok=True)


def utc(s: str) -> datetime:
    """Parse '2026-09-08 00:00:00.0' (dump) or '2026-10-20T01:02:03Z' (stream) to aware UTC."""
    s = s.strip().replace("Z", "+00:00")
    if " " in s and "T" not in s:
        s = s.replace(" ", "T")
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
