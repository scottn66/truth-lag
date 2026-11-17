"""Cut a MediaWiki History month file (.tsv.bz2, 78 columns, no header) to the 12 slim columns, locally.

Modeled on ingest/vps/filter_history.py (the 2026-09 filter that ran on the VPS), with the plan's changes (PLAN.md,
Phase 5 step 1):
  * keeps rows with event_entity = 'revision' and writes config.HISTORY_SLIM_COLUMNS, all as text;
  * only an EMPTY field becomes null: literal strings such as "NA" or "NULL" stay strings (the 2026-09 Parquet
    copies turned them into nulls);
  * stops at the first row that does not have 78 fields (the 2026-09 file had none);
  * writes <name>.tmp and renames it; refuses an output under data/history/ and refuses to replace a file.

Output: data/history_slim/<snapshot>/enwiki_rev_all_<month>_slim.parquet, plus <same>.stats.json.

Run
    python -m etl.history_slim data/history_raw/2026-10/2026-10.enwiki.2026-09.tsv.bz2 [more files]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pcsv
import pyarrow.parquet as pq

from . import lake_config
from .hw2 import config

# The 78 columns of the MediaWiki History TSV, in file order (as in ingest/vps/filter_history.py).
COLS = """wiki_db event_log_id event_entity event_type event_timestamp event_comment
event_user_id event_user_central_id event_user_text_historical event_user_text event_user_blocks_historical event_user_blocks
event_user_groups_historical event_user_groups event_user_is_bot_by_historical event_user_is_bot_by event_user_is_created_by_self
event_user_is_created_by_system event_user_is_created_by_peer event_user_is_anonymous event_user_is_temporary event_user_is_permanent
event_user_is_cross_wiki event_user_registration_timestamp event_user_creation_timestamp event_user_first_edit_timestamp
event_user_revision_count event_user_seconds_since_previous_revision
page_id page_title_historical page_title page_namespace_historical page_namespace_is_content_historical page_namespace
page_namespace_is_content page_is_redirect page_is_deleted page_creation_timestamp page_first_edit_timestamp page_revision_count
page_seconds_since_previous_revision
user_id user_central_id user_text_historical user_text user_blocks_historical user_blocks user_groups_historical user_groups
user_is_bot_by_historical user_is_bot_by user_is_created_by_self user_is_created_by_system user_is_created_by_peer user_is_anonymous
user_is_temporary user_is_permanent user_registration_timestamp user_creation_timestamp user_first_edit_timestamp
revision_id revision_parent_id revision_minor_edit revision_deleted_parts revision_deleted_parts_are_suppressed revision_text_bytes
revision_text_bytes_diff revision_text_sha1 revision_content_model revision_content_format revision_is_deleted_by_page_deletion
revision_deleted_by_page_deletion_timestamp revision_is_identity_reverted revision_first_identity_reverting_revision_id
revision_seconds_to_identity_revert revision_is_identity_revert revision_is_from_before_page_creation revision_tags""".split()
assert len(COLS) == 78
SLIM = list(config.HISTORY_SLIM_COLUMNS)
NAME_RE = re.compile(r"^(?P<snapshot>\d{4}-\d{2})\.(?P<wiki>[a-z_]+)\.(?P<month>\d{4}-\d{2})\.tsv\.bz2$")
FORBIDDEN = (lake_config.REPO_DIR / "data" / "history").resolve()


def output_path(src: Path, out_root: Path | None = None) -> tuple[Path, str, str]:
    m = NAME_RE.match(src.name)
    if not m:
        raise ValueError(f"{src.name}: not a <snapshot>.<wiki>.<month>.tsv.bz2 file")
    root = Path(out_root) if out_root else lake_config.HISTORY_SLIM_DIR
    out = root / m.group("snapshot") / f"{m.group('wiki')}_rev_all_{m.group('month')}_slim.parquet"
    return out, m.group("snapshot"), m.group("month")


def cut(src: str | Path, out_root: str | Path | None = None, block_mb: int = 64) -> dict:
    src = Path(src)
    out, snapshot, month = output_path(src, out_root)
    res = out.resolve()
    if res == FORBIDDEN or FORBIDDEN in res.parents:
        raise SystemExit(f"refused: {out} is under data/history/ (the old code reads that folder)")
    if out.exists():
        raise SystemExit(f"refused: {out} exists; this script never replaces a file")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    t0 = time.time()
    reader = pcsv.open_csv(
        pa.input_stream(str(src), compression="bz2"),
        read_options=pcsv.ReadOptions(column_names=COLS, block_size=block_mb << 20),
        parse_options=pcsv.ParseOptions(delimiter="\t", quote_char=False, double_quote=False, escape_char=False,
                                        newlines_in_values=False),          # a row with != 78 fields raises: stop
        convert_options=pcsv.ConvertOptions(column_types={c: pa.string() for c in COLS}, include_columns=["event_entity"] + SLIM,
                                            null_values=[""], strings_can_be_null=True, quoted_strings_can_be_null=False))
    schema = pa.schema([pa.field(c, pa.string()) for c in SLIM])
    rows = kept = 0
    entities: dict[str, int] = {}
    writer = pq.ParquetWriter(tmp, schema, compression="zstd")
    try:
        for batch in reader:
            rows += batch.num_rows
            ent = batch.column("event_entity")
            for v in pc.value_counts(ent).to_pylist():
                entities[str(v["values"])] = entities.get(str(v["values"]), 0) + v["counts"]
            keep = pc.equal(ent, "revision")
            t = pa.Table.from_batches([batch]).filter(keep).select(SLIM)
            kept += t.num_rows
            if t.num_rows:
                writer.write_table(t.cast(schema))
    except Exception:
        writer.close()
        tmp.unlink(missing_ok=True)
        raise
    writer.close()
    tmp.rename(out)
    data_dir = (lake_config.REPO_DIR / "data").resolve()
    stats = {"source": str(src.resolve().relative_to(data_dir)) if data_dir in src.resolve().parents else str(src),
             "source_bytes": src.stat().st_size, "snapshot": snapshot, "dump_month": month, "rows_in": rows,
             "rows_by_entity": entities, "revision_rows_out": kept, "output": str(out), "output_bytes": out.stat().st_size,
             "seconds": round(time.time() - t0, 1)}
    out.with_name(out.name.replace(".parquet", ".stats.json")).write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats), flush=True)
    return stats


if __name__ == "__main__":
    for f in sys.argv[1:]:
        cut(f)
