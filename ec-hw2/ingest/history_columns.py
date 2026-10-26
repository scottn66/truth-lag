"""The 78 columns of the MediaWiki History dump, and how to give them real types.

Why this file exists: the VPS wrote the filtered dump to Parquet with EVERY column
as text (string). Before we can do math or compare times, we must turn each column
into its real type: whole numbers, true/false, or UTC times. This file says which
column has which type, and does the conversion in one place.

Source of the column order: Wikitech "Data Platform/Data Lake/Edits/MediaWiki history dumps"
and the refinery code (MediawikiEvent.toTSVLine). Index 1 (event_log_id) was added in May 2026.

Use:
    from ingest.history_columns import cast_history_frame
    df = cast_history_frame(pd.read_parquet(path))
"""
from __future__ import annotations

import pandas as pd

COLUMNS = [
    "wiki_db", "event_log_id", "event_entity", "event_type", "event_timestamp", "event_comment",
    "event_user_id", "event_user_central_id", "event_user_text_historical", "event_user_text",
    "event_user_blocks_historical", "event_user_blocks", "event_user_groups_historical",
    "event_user_groups", "event_user_is_bot_by_historical", "event_user_is_bot_by",
    "event_user_is_created_by_self", "event_user_is_created_by_system", "event_user_is_created_by_peer",
    "event_user_is_anonymous", "event_user_is_temporary", "event_user_is_permanent",
    "event_user_is_cross_wiki", "event_user_registration_timestamp", "event_user_creation_timestamp",
    "event_user_first_edit_timestamp", "event_user_revision_count",
    "event_user_seconds_since_previous_revision",
    "page_id", "page_title_historical", "page_title", "page_namespace_historical",
    "page_namespace_is_content_historical", "page_namespace", "page_namespace_is_content",
    "page_is_redirect", "page_is_deleted", "page_creation_timestamp", "page_first_edit_timestamp",
    "page_revision_count", "page_seconds_since_previous_revision",
    "user_id", "user_central_id", "user_text_historical", "user_text", "user_blocks_historical",
    "user_blocks", "user_groups_historical", "user_groups", "user_is_bot_by_historical",
    "user_is_bot_by", "user_is_created_by_self", "user_is_created_by_system",
    "user_is_created_by_peer", "user_is_anonymous", "user_is_temporary", "user_is_permanent",
    "user_registration_timestamp", "user_creation_timestamp", "user_first_edit_timestamp",
    "revision_id", "revision_parent_id", "revision_minor_edit", "revision_deleted_parts",
    "revision_deleted_parts_are_suppressed", "revision_text_bytes", "revision_text_bytes_diff",
    "revision_text_sha1", "revision_content_model", "revision_content_format",
    "revision_is_deleted_by_page_deletion", "revision_deleted_by_page_deletion_timestamp",
    "revision_is_identity_reverted", "revision_first_identity_reverting_revision_id",
    "revision_seconds_to_identity_revert", "revision_is_identity_revert",
    "revision_is_from_before_page_creation", "revision_tags",
]
assert len(COLUMNS) == 78

INT_COLUMNS = {
    "event_log_id", "event_user_id", "event_user_central_id", "event_user_revision_count",
    "event_user_seconds_since_previous_revision", "page_id", "page_namespace_historical",
    "page_namespace", "page_revision_count", "page_seconds_since_previous_revision", "user_id",
    "user_central_id", "revision_id", "revision_parent_id", "revision_text_bytes",
    "revision_text_bytes_diff", "revision_first_identity_reverting_revision_id",
    "revision_seconds_to_identity_revert",
}
BOOL_COLUMNS = {
    "event_user_is_created_by_self", "event_user_is_created_by_system",
    "event_user_is_created_by_peer", "event_user_is_anonymous", "event_user_is_temporary",
    "event_user_is_permanent", "event_user_is_cross_wiki", "page_namespace_is_content_historical",
    "page_namespace_is_content", "page_is_redirect", "page_is_deleted", "user_is_created_by_self",
    "user_is_created_by_system", "user_is_created_by_peer", "user_is_anonymous",
    "user_is_temporary", "user_is_permanent", "revision_minor_edit",
    "revision_deleted_parts_are_suppressed", "revision_is_deleted_by_page_deletion",
    "revision_is_identity_reverted", "revision_is_identity_revert",
    "revision_is_from_before_page_creation",
}
TIME_COLUMNS = {
    "event_timestamp", "event_user_registration_timestamp", "event_user_creation_timestamp",
    "event_user_first_edit_timestamp", "page_creation_timestamp", "page_first_edit_timestamp",
    "user_registration_timestamp", "user_creation_timestamp", "user_first_edit_timestamp",
    "revision_deleted_by_page_deletion_timestamp",
}
# Comma lists stay as text; use split_list() when you need the items.
LIST_COLUMNS = {
    "event_user_blocks_historical", "event_user_blocks", "event_user_groups_historical",
    "event_user_groups", "event_user_is_bot_by_historical", "event_user_is_bot_by",
    "user_blocks_historical", "user_blocks", "user_groups_historical", "user_groups",
    "user_is_bot_by_historical", "user_is_bot_by", "revision_deleted_parts", "revision_tags",
}
TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"   # e.g. "2026-09-08 00:00:00.0" (UTC)


def _to_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace("", None), errors="raise").astype("Int64")


def _to_bool(s: pd.Series) -> pd.Series:
    mapped = s.map({"true": True, "false": False})
    bad = s.notna() & (s != "") & mapped.isna()
    if bad.any():
        raise ValueError(f"{s.name}: not true/false: {s[bad].unique()[:5]}")
    return mapped.astype("boolean")


def _to_time(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s.replace("", None), format=TIME_FORMAT, utc=True, errors="raise")


def cast_history_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with real types. Works for the full and the slim file."""
    out = df.copy()
    for col in out.columns:
        if col in INT_COLUMNS:
            out[col] = _to_int(out[col])
        elif col in BOOL_COLUMNS:
            out[col] = _to_bool(out[col])
        elif col in TIME_COLUMNS:
            out[col] = _to_time(out[col])
        else:
            out[col] = out[col].astype("string")
    return out


def split_list(value) -> list[str]:
    """Split a dump list like 'mobile edit,visualeditor' (a comma inside an item is '\\,')."""
    if value is None or value is pd.NA or value == "":
        return []
    items, cur, i, s = [], [], 0, str(value)
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] == ",":
            cur.append(","); i += 2; continue
        if s[i] == ",":
            items.append("".join(cur)); cur = []
        else:
            cur.append(s[i])
        i += 1
    items.append("".join(cur))
    return [x for x in items if x != ""]


def sha1_base36_to_hex(s: str | None) -> str | None:
    """The dump AND the stream store sha1 in base 36; only the Action API uses 40-digit hex."""
    if not s:
        return None
    return format(int(s, 36), "040x")
