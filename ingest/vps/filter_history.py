#!/usr/bin/env python3
"""Stream-filter the enwiki 2026-09 MediaWiki History dump (bz2, 78 cols) without decompressing to disk."""
import bz2, gzip, json, os, sys, time
BASE = "/opt/truthlag/data/history"
SRC = os.path.join(BASE, "2026-09.enwiki.2026-09.tsv.bz2")
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
assert len(COLS) == 78, len(COLS)
I = {c: i for i, c in enumerate(COLS)}
SLIM = ["revision_id", "page_id", "event_timestamp", "revision_is_identity_revert", "revision_is_identity_reverted",
        "revision_first_identity_reverting_revision_id", "revision_seconds_to_identity_revert", "event_user_id",
        "event_user_text", "event_user_text_historical", "event_user_is_bot_by", "page_namespace"]
SI = [I[c] for c in SLIM]
O1 = os.path.join(BASE, "enwiki_rev_ns0_2026-09-08_10.tsv.gz")
O2 = os.path.join(BASE, "enwiki_rev_all_2026-09_slim.tsv.gz")
n = n1 = n2 = bad = 0; t0 = time.time()
with bz2.open(SRC, "rt", encoding="utf-8", newline="\n") as f, \
     gzip.open(O1 + ".tmp", "wt", encoding="utf-8", compresslevel=6) as w1, \
     gzip.open(O2 + ".tmp", "wt", encoding="utf-8", compresslevel=6) as w2:
    w1.write("\t".join(COLS) + "\n"); w2.write("\t".join(SLIM) + "\n")
    for line in f:
        n += 1
        p = line.rstrip("\n").split("\t")
        if len(p) != 78:
            bad += 1; continue
        if p[2] != "revision":
            continue
        w2.write("\t".join(p[i] for i in SI) + "\n"); n2 += 1
        ts = p[4]
        if p[33] == "0" and "2026-09-08" <= ts[:10] < "2026-09-11":
            w1.write("\t".join(p) + "\n"); n1 += 1
        if n % 2_000_000 == 0:
            print(f"{n} rows, ns0 Sep8-10={n1}, slim={n2}, {time.time()-t0:.0f}s", flush=True)
os.replace(O1 + ".tmp", O1); os.replace(O2 + ".tmp", O2)
stats = dict(total_rows=n, bad_rows=bad, ns0_sep8_10=n1, all_sep_revisions=n2, seconds=round(time.time()-t0))
print(json.dumps(stats), flush=True)
# Parquet (streamed via pyarrow CSV reader, batch-wise)
try:
    import pyarrow as pa, pyarrow.csv as pc, pyarrow.parquet as pq
    for src in (O1, O2):
        dst = src.replace(".tsv.gz", ".parquet")
        with gzip.open(src, "rb") as g:
            hdr = g.readline().decode().rstrip("\n").split("\t")
        r = pc.open_csv(src, read_options=pc.ReadOptions(block_size=16 << 20),
                        parse_options=pc.ParseOptions(delimiter="\t", quote_char=False, newlines_in_values=False),
                        convert_options=pc.ConvertOptions(column_types={c: pa.string() for c in hdr}, strings_can_be_null=True))
        wr = None
        for b in r:
            if wr is None: wr = pq.ParquetWriter(dst + ".tmp", b.schema, compression="zstd")
            wr.write_batch(b)
        wr.close(); os.replace(dst + ".tmp", dst)
        print("parquet", dst, flush=True)
except Exception as e:
    print("parquet failed:", repr(e), flush=True)
with open(os.path.join(BASE, "filter_stats.json"), "w") as f: json.dump(stats, f)
print("DONE", flush=True)
