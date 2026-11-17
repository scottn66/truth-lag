"""Lake settings: where the Delta tables live and which table properties they get.

The rules of the project (windows, thresholds, stream names) stay in ec-hw2/config.py.
This file only holds what is new with the lake.

Layout
    <lake>/bronze/<table>/     raw events, append-only
    <lake>/silver/<table>/     typed tables with the columns of the old Parquet files
    <lake>/_runs/<as_of>/      JSON summaries of each cohort build (plain files)
"""
from __future__ import annotations

import os
from pathlib import Path

from deltalake import WriterProperties

ENV_VAR = "TRUTHLAG_LAKE_DIR"


def lake_root(lake: str | Path | None = None) -> Path:
    """The lake folder: the argument when given, else the TRUTHLAG_LAKE_DIR variable."""
    value = lake if lake is not None else os.environ.get(ENV_VAR)
    if not value:
        raise RuntimeError(f"No lake folder. Pass lake=... or set {ENV_VAR}.")
    return Path(value).expanduser().resolve()


# Set at CREATE. The defaults delete commit files after 30 days at the next checkpoint
# (then time travel to them fails) and let VACUUM delete data files after 7 days.
KEEP_HISTORY = {
    "delta.logRetentionDuration": "interval 3650 days",
    "delta.deletedFileRetentionDuration": "interval 3650 days",
    "delta.enableExpiredLogCleanup": "false",
}

# File statistics only for the small envelope columns. raw_json is long text: no min / max for it.
BRONZE_STATS_COLUMNS = ["meta_id", "meta_dt", "stream", "wiki_id", "kafka_topic", "kafka_partition", "kafka_offset"]
BRONZE_PROPS = {**KEEP_HISTORY, "delta.appendOnly": "true",
                "delta.dataSkippingStatsColumns": ",".join(BRONZE_STATS_COLUMNS)}
SILVER_PROPS = {**KEEP_HISTORY}

BRONZE_COMPRESSION = "ZSTD"          # raw JSON text compresses much better with zstd than with snappy
BRONZE_COMPRESSION_LEVEL = 3
BRONZE_CHUNK_ROWS = 100_000          # rows per Bronze commit: keeps memory low on the first full load

# Both engines must be able to read and write every table, so these table features are forbidden.
FORBIDDEN_FEATURES = ["deletionVectors", "clustering", "identityColumns", "variantType", "inCommitTimestamp",
                      "columnMapping"]


def bronze_writer_properties() -> WriterProperties:
    return WriterProperties(compression=BRONZE_COMPRESSION, compression_level=BRONZE_COMPRESSION_LEVEL)
