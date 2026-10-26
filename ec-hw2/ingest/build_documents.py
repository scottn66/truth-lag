"""Turn the cohort tables (Parquet) into MongoDB documents.

Purpose
    Make the documents of DATA_MODEL.md section 4, one Python dict per document:
    - revisions:    one document per revision, both cohorts. History documents
                    have a history{} part, live documents have a live{} part.
    - revert_links: one document per reverted cohort revision.
    - tag_events:   the mw-reverted additions only.
    - late_reverts: the late-revert case study.
    Times are timezone-aware UTC datetimes. The comment is cut to 120 characters.
    load_mongo.py imports this file and inserts the documents. This file writes
    nothing to disk except results/sample_documents.json.

    It also holds the ONE pseudonym rule for human editors. MongoDB, Atlas, SQL and
    Neo4j all import it from here: alias = "editor_" + the first config.ALIAS_HEX
    (10) hex digits of HMAC-SHA256(config.ALIAS_SECRET, editor_key). The length is
    fixed (it does not depend on the data). alias_length() checks that no two keys
    share an alias and stops with a clear error if they do, or if ALIAS_SECRET is
    empty. The secret lives in ec-hw2/.env, so nobody can rebuild a key from its
    alias by trying every user id. It is a display mask on public data, not
    anonymization: a rev_id still leads to the edit on Wikipedia.
    Empty comments are stored as null in both cohorts.

Inputs
    data/tables/history_revisions.parquet, live_revisions.parquet,
    history_revert_links.parquet, live_revert_links.parquet, late_reverts.parquet,
    data/parsed/tag_events.parquet, and the _SUCCESS_*.json files of the steps
    that made them.

Outputs
    ec-hw2/results/sample_documents.json: ONE history and ONE live document, for
    the report picture. Human editors are pseudonyms; their user id is hidden.

Run (from the repo root)
    .venv/bin/python ec-hw2/ingest/build_documents.py
    It checks the inputs, builds every document once (no database needed),
    prints the counts and writes the sample file.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from bson import json_util

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

COMMENT_MAX = 120          # DATA_MODEL.md section 4: comment = first 120 characters
BATCH_ROWS = 5_000         # rows read from Parquet at a time (keeps memory low)
# Kept for older callers. The alias length is now always config.ALIAS_HEX (10).
ALIAS_MIN_HEX = 4

# Input files and the _SUCCESS file that proves each one is complete.
TABLE_FILES = {
    "history_revisions": config.TABLES_DIR / "history_revisions.parquet",
    "live_revisions": config.TABLES_DIR / "live_revisions.parquet",
    "history_revert_links": config.TABLES_DIR / "history_revert_links.parquet",
    "live_revert_links": config.TABLES_DIR / "live_revert_links.parquet",
    "live_revert_links_all": config.TABLES_DIR / "live_revert_links_all.parquet",
    "late_reverts": config.TABLES_DIR / "late_reverts.parquet",
    "page_change": config.PARSED_DIR / "page_change.parquet",
    "tag_events": config.PARSED_DIR / "tag_events.parquet",
}
SUCCESS_FILES = {
    config.TABLES_DIR / "_SUCCESS_history.json": ["history_revisions", "history_revert_links"],
    config.TABLES_DIR / "_SUCCESS_live.json": ["live_revisions", "live_revert_links",
                                               "live_revert_links_all"],
    config.TABLES_DIR / "_SUCCESS_late_reverts.json": ["late_reverts"],
    config.PARSED_DIR / "_SUCCESS_parsed.json": ["page_change", "tag_events"],
}
SAMPLE_PATH = config.RESULTS_DIR / "sample_documents.json"


# --------------------------------------------------------------------------
# Input checks
# --------------------------------------------------------------------------
def check_inputs(names: Iterable[str] | None = None) -> dict:
    """Stop with a clear message if an input file or its _SUCCESS file is missing.

    Returns {success_file_name: parsed json} so callers can read flags such as
    the live 'provisional' flag.
    """
    wanted = set(names) if names is not None else set(TABLE_FILES)
    found = {}
    problems = []
    for success, tables in SUCCESS_FILES.items():
        if not wanted.intersection(tables):
            continue
        if not success.exists():
            problems.append(f"missing {success} (run the step that makes {', '.join(tables)})")
            continue
        found[success.name] = json.loads(success.read_text(encoding="utf-8"))
        for t in tables:
            if t in wanted and not TABLE_FILES[t].exists():
                problems.append(f"missing {TABLE_FILES[t]}")
    if problems:
        raise SystemExit("STOP: inputs are not ready:\n  " + "\n  ".join(problems))
    return found


def live_is_provisional(success: dict) -> bool:
    return bool(success.get("_SUCCESS_live.json", {}).get("provisional", False))


# --------------------------------------------------------------------------
# Reading Parquet rows as plain Python values
# --------------------------------------------------------------------------
def _plain_batch(batch: pa.RecordBatch) -> list[dict]:
    """Turn one Arrow batch into dicts of plain Python values.

    BSON dates have millisecond precision, so nanosecond times are cast to
    microseconds first (pyarrow then returns datetime objects, not pandas).
    Nulls become None. Lists become Python lists.
    """
    cols = []
    for field, col in zip(batch.schema, batch.columns):
        if pa.types.is_timestamp(field.type):
            col = pc.cast(col, pa.timestamp("us", tz="UTC"), safe=False)
        cols.append(col)
    rows = pa.RecordBatch.from_arrays(cols, names=batch.schema.names).to_pylist()
    for row in rows:
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.astimezone(timezone.utc)
            elif isinstance(v, float) and v != v:     # NaN that is not null
                row[k] = None
    return rows


def iter_rows(path: Path, columns: list[str] | None = None,
              filter_fn=None) -> Iterator[dict]:
    """Yield the rows of a Parquet file as dicts, BATCH_ROWS at a time."""
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=BATCH_ROWS, columns=columns):
        if filter_fn is not None:
            batch = filter_fn(batch)
            if batch.num_rows == 0:
                continue
        yield from _plain_batch(batch)


def rows_from_table(table: pa.Table) -> list[dict]:
    """The same conversion for an in-memory table (used by the tests)."""
    out = []
    for batch in table.to_batches():
        out.extend(_plain_batch(batch))
    return out


def parquet_rows(path: Path) -> int:
    return pq.ParquetFile(path).metadata.num_rows


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------
def _cut(text, n: int = COMMENT_MAX):
    """The first n characters. An empty comment is null, the same in both cohorts
    (the dump has null for an empty comment, the stream has '')."""
    if text is None or text == "":
        return None
    return str(text)[:n]


def revision_document(row: dict, lean: bool = False) -> dict:
    """One revisions document (DATA_MODEL.md section 4) from one cohort-table row.

    lean=True drops the comment (the Atlas copy, to stay inside the free tier).
    """
    cohort = row["cohort"]
    doc = {
        "_id": f"{row['wiki_db']}:{row['rev_id']}",
        "wiki_db": row["wiki_db"],
        "rev_id": row["rev_id"],
        "parent_id": row["parent_id"],
        "cohort": cohort,
        "page": {"id": row["page_id"], "title": row["page_title"], "ns": row["page_ns"]},
        "user": {"id": row["user_id"], "name": row["user_name"], "kind": row["user_kind"],
                 "key": row["user_key"], "is_bot": row["is_bot"], "is_anon": row["is_anon"],
                 "is_temp": row["is_temp"], "edit_count": row["edit_count"]},
        "ts": row["ts"],
        "hour_utc": row["hour_utc"],
        "size": row["size"],
        "size_delta": row["size_delta"],
        "comment": _cut(row["comment"]),
        "tags": list(row["tags"] or []),
        "mw_reverted_tag": row["mw_reverted_tag"],
        "is_revert": row["is_revert"],
        "revert_method": row["revert_method"],
    }
    if lean:
        del doc["comment"]
    if cohort == config.COHORT_LIVE:
        doc["live"] = {"seen_ts": row["seen_ts"], "revert_risk": row["revert_risk"],
                       "page_edits_prev_1h": row["page_edits_prev_1h"]}
    elif cohort == config.COHORT_HISTORY:
        has_reverter = any(row.get(k) is not None
                           for k in ("reverter_key", "reverter_name", "reverter_kind"))
        doc["history"] = {
            "snapshot": config.HISTORY_SNAPSHOT,
            "reverted": row["reverted"],
            "reverted_any": row["reverted_any"],
            "secs_to_revert": row["secs_to_revert"],
            "reverting_rev_id": row["reverting_rev_id"],
            "reverter": ({"key": row["reverter_key"], "name": row["reverter_name"],
                          "kind": row["reverter_kind"]} if has_reverter else None),
            "reverted_by_other": row["reverted_by_other"],
            "followup_s": row["followup_s"],
            # Not in DATA_MODEL.md yet (shared change request): Mongo Q5 needs the
            # page activity of the history cohort, which has no page_hour counters.
            "page_edits_prev_1h": row["page_edits_prev_1h"],
        }
    else:
        raise ValueError(f"unknown cohort {cohort!r} for rev_id {row.get('rev_id')}")
    return doc


LINK_COLUMNS = ["cohort", "source", "reverted_rev_id", "page_id", "reverted_ts", "author_key",
                "author_kind", "reverting_rev_id", "reverting_ts", "reverter_key",
                "reverter_name", "reverter_kind", "T_s", "known_at", "K_s", "method",
                "is_exact", "by_other", "within_followup", "range_size", "range_complete",
                "confirmed_by_tag"]


def revert_link_document(row: dict) -> dict:
    """One revert_links document: _id = '<cohort>:<reverted_rev_id>' plus the link columns."""
    if row.get("cohort") not in (config.COHORT_HISTORY, config.COHORT_LIVE):
        raise ValueError(f"revert link without a cohort: {row.get('reverted_rev_id')}")
    doc = {"_id": f"{row['cohort']}:{row['reverted_rev_id']}"}
    for c in LINK_COLUMNS:
        doc[c] = row.get(c)
    return doc


TAG_COLUMNS = ["meta_id", "meta_dt", "rev_id", "page_id", "ns", "rev_timestamp", "tags",
               "prior_tags", "added", "removed"]


def tag_event_document(row: dict) -> dict:
    """One tag_events document (an mw-reverted addition). _id = meta.id of the event."""
    doc = {"_id": row["meta_id"]}
    for c in TAG_COLUMNS[1:]:
        v = row.get(c)
        doc[c] = list(v) if isinstance(v, (list, tuple)) else v
    return doc


def late_revert_document(row: dict) -> dict:
    """One late_reverts document. _id = the September rev_id (one row per rev_id)."""
    doc = {"_id": row["rev_id"]}
    for k, v in row.items():
        doc[k] = list(v) if isinstance(v, (list, tuple)) else v
    return doc


# --------------------------------------------------------------------------
# Document streams for load_mongo.py
# --------------------------------------------------------------------------
def _mw_reverted_only(batch: pa.RecordBatch) -> pa.RecordBatch:
    mask = pc.fill_null(batch.column(batch.schema.get_field_index("mw_reverted_added")), False)
    return batch.filter(mask)


def iter_revision_documents(cohort: str, lean: bool = False) -> Iterator[dict]:
    path = TABLE_FILES[f"{cohort}_revisions"]
    for row in iter_rows(path):
        yield revision_document(row, lean=lean)


def iter_revert_link_documents(cohort: str) -> Iterator[dict]:
    for row in iter_rows(TABLE_FILES[f"{cohort}_revert_links"], columns=LINK_COLUMNS):
        yield revert_link_document(row)


def iter_tag_event_documents() -> Iterator[dict]:
    cols = TAG_COLUMNS + ["mw_reverted_added"]
    for row in iter_rows(TABLE_FILES["tag_events"], columns=cols, filter_fn=_mw_reverted_only):
        yield tag_event_document(row)


def iter_late_revert_documents() -> Iterator[dict]:
    for row in iter_rows(TABLE_FILES["late_reverts"]):
        yield late_revert_document(row)


def count_mw_reverted_additions() -> int:
    t = pq.read_table(TABLE_FILES["tag_events"], columns=["mw_reverted_added"])
    return int(pc.sum(pc.fill_null(t["mw_reverted_added"], False)).as_py() or 0)


# --------------------------------------------------------------------------
# Pseudonyms: 'editor_' + HMAC-SHA256(config.ALIAS_SECRET, editor_key), fixed length
# --------------------------------------------------------------------------
class AliasError(RuntimeError):
    """The pseudonym rule cannot be used: no secret, or two keys share one alias."""


def _alias_secret() -> bytes:
    secret = config.ALIAS_SECRET
    if not secret:
        raise AliasError("ALIAS_SECRET is empty. Put a long random value in ec-hw2/.env "
                         "(see .env.example). Every pseudonym needs it, and every part must "
                         "use the same value.")
    return secret.encode("utf-8")


def _alias_hex(key: str) -> str:
    digest = hmac.new(_alias_secret(), key.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:config.ALIAS_HEX]


def check_aliases_unique(keys: Iterable[str]) -> int:
    """Stop with AliasError if two different keys get the same alias. Returns the key count."""
    seen: dict[str, str] = {}
    clashes = 0
    for k in {k for k in keys if k}:
        if seen.setdefault(_alias_hex(k), k) != k:
            clashes += 1
    if clashes:
        # The keys themselves are not printed: they could identify the editors.
        raise AliasError(f"{clashes} pair(s) of editor keys share one alias with "
                         f"config.ALIAS_HEX = {config.ALIAS_HEX} hex digits. Raise ALIAS_HEX "
                         "in config.py and rebuild every output that shows aliases.")
    return len(seen)


def alias_length(keys: Iterable[str], start: int = ALIAS_MIN_HEX) -> int:
    """Check that every key gets its own alias, then return config.ALIAS_HEX.

    The length no longer depends on the data, so Mongo, SQL and Neo4j always agree.
    `start` is kept so older calls still work; it is not used.
    """
    check_aliases_unique(keys)
    return config.ALIAS_HEX


def editor_alias(key: str | None, n_hex: int | None = None) -> str | None:
    """'editor_' + the first config.ALIAS_HEX hex digits of HMAC-SHA256(secret, key).

    n_hex is ignored (it is kept so older calls still work): every caller gets the
    same alias, even one that read an old alias length from a _SUCCESS file.
    """
    if key is None or key == "":
        return None
    return "editor_" + _alias_hex(key)


def public_name(kind: str | None, key: str | None, name: str | None,
                n_hex: int | None = None) -> str | None:
    """What a result may show for an editor: bots keep their name, humans get an alias."""
    if kind == "bot" and name:
        return name
    if key is None:
        return None if name is None else "editor_unknown"
    return editor_alias(key, n_hex)


def all_editor_keys() -> set[str]:
    """Every editor key in both cohorts (authors and reverters): the alias universe."""
    keys: set[str] = set()
    for cohort in (config.COHORT_HISTORY, config.COHORT_LIVE):
        t = pq.read_table(TABLE_FILES[f"{cohort}_revisions"], columns=["user_key"])
        keys.update(k for k in t["user_key"].to_pylist() if k)
        t = pq.read_table(TABLE_FILES[f"{cohort}_revert_links"],
                          columns=["author_key", "reverter_key"])
        keys.update(k for k in t["author_key"].to_pylist() if k)
        keys.update(k for k in t["reverter_key"].to_pylist() if k)
    return keys


def pseudonymize_revision(doc: dict, n_hex: int) -> dict:
    """A copy of a revisions document that is safe to commit (no human names or ids)."""
    out = json_util.loads(json_util.dumps(doc))       # deep copy, keeps datetimes
    u = out["user"]
    if u["kind"] != "bot":
        u["name"] = public_name(u["kind"], u["key"], u["name"], n_hex)
        u["key"] = editor_alias(u["key"], n_hex)
        u["id"] = None
    rv = (out.get("history") or {}).get("reverter")
    if rv and rv.get("kind") != "bot":
        rv["name"] = public_name(rv["kind"], rv["key"], rv["name"], n_hex)
        rv["key"] = editor_alias(rv["key"], n_hex)
    return out


# --------------------------------------------------------------------------
# The sample file for the report picture
# --------------------------------------------------------------------------
# A comment that names a user or links to one could undo the pseudonym.
_RISKY_COMMENT = re.compile(r"user|special:|talk|\[\[|~2\d{3}-|contribs", re.IGNORECASE)


def _good_comment(c) -> bool:
    return bool(c) and len(c) >= 10 and not _RISKY_COMMENT.search(c)


def _no_blp(tags) -> bool:
    # Keep the report picture away from edits about living people.
    return not any("BLP" in t for t in (tags or []))


def pick_sample_rows() -> tuple[dict, dict]:
    """Pick one history row (a human edit reverted by a bot) and one live row.

    The choice is deterministic: the lowest rev_id that fits.
    """
    hist = None
    for row in iter_rows(TABLE_FILES["history_revisions"]):
        if (row["user_kind"] in ("registered", "temporary") and row["reverted"]
                and row["reverter_kind"] == "bot" and row["tags"] and _no_blp(row["tags"])
                and _good_comment(row["comment"])):
            if hist is None or row["rev_id"] < hist["rev_id"]:
                hist = row
    live = None
    for row in iter_rows(TABLE_FILES["live_revisions"]):
        if (row["user_kind"] in ("registered", "temporary") and row["revert_risk"] is not None
                and row["tags"] and _no_blp(row["tags"]) and row["page_edits_prev_1h"]
                and _good_comment(row["comment"])):
            if live is None or row["rev_id"] < live["rev_id"]:
                live = row
    if hist is None or live is None:
        raise SystemExit("STOP: could not find sample rows")
    return hist, live


def write_json_safely(obj, path: Path) -> None:
    """Write <name>.tmp, then rename it, so a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json_util.dumps(obj, indent=2, json_options=json_util.RELAXED_JSON_OPTIONS)
                   + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_success(step: str, rows: dict, folder: Path, extra: dict | None = None) -> Path:
    """Write _SUCCESS_<step>.json with the row counts (after the outputs are in place)."""
    info = {"step": step, "data_version": config.DATA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rows": rows}
    if extra:
        info.update(extra)
    path = folder / f"_SUCCESS_{step}.json"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def write_sample_documents(n_hex: int | None = None) -> Path:
    if n_hex is None:
        n_hex = alias_length(all_editor_keys())
    hist_row, live_row = pick_sample_rows()
    sample = {
        "note": ("One real document of each cohort from the MongoDB collection 'revisions'. "
                 "Human editors are shown as pseudonyms (editor_ + the first "
                 f"{n_hex} hex digits of HMAC-SHA256(secret key, editor key)) and their user "
                 "id is hidden (null). Bots keep their real names. Times are UTC."),
        "history": pseudonymize_revision(revision_document(hist_row), n_hex),
        "live": pseudonymize_revision(revision_document(live_row), n_hex),
    }
    write_json_safely(sample, SAMPLE_PATH)
    write_success("sample_documents", {"sample_documents.json": 2}, SAMPLE_PATH.parent,
                  {"alias_hex_digits": n_hex})
    return SAMPLE_PATH


def main() -> None:
    success = check_inputs()
    if live_is_provisional(success):
        print("NOTE: the stream labels of the live cohort are PROVISIONAL (capture not yet past "
              f"{config.LIVE_FINAL_AFTER.isoformat()}).")
    counts = {}
    ids = set()
    for cohort in (config.COHORT_HISTORY, config.COHORT_LIVE):
        n = 0
        for doc in iter_revision_documents(cohort):
            ids.add(doc["_id"])
            n += 1
        counts[f"revisions ({cohort})"] = n
        counts[f"revert_links ({cohort})"] = sum(1 for _ in iter_revert_link_documents(cohort))
    counts["revisions _id unique"] = len(ids)
    counts["tag_events (mw-reverted additions)"] = sum(1 for _ in iter_tag_event_documents())
    counts["late_reverts"] = sum(1 for _ in iter_late_revert_documents())
    keys = all_editor_keys()
    n_hex = alias_length(keys)
    counts["editor keys (both cohorts)"] = len(keys)
    counts["alias hex digits"] = n_hex
    for k, v in counts.items():
        print(f"{k:40s} {v:>10,}")
    path = write_sample_documents(n_hex)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
