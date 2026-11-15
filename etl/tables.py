"""Registry of the lake tables: name -> path, key columns, partition columns, Arrow schema.

The Silver schemas are taken from the old code (parse_stream, label_live, late_reverts),
so a column is defined in one place only. Two differences from the old Parquet files:
    1. page_change and tag_events get an `event_date` partition column (UTC date of meta_dt).
    2. The cohort tables store microsecond times (Delta has no nanosecond type); the old
       files store nanoseconds. Every value is a whole millisecond or second, so nothing is lost.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa

from . import lake_config
from .hw2 import config, label_live, late_reverts, parse_stream

TS = pa.timestamp("us", tz="UTC")


@dataclass(frozen=True)
class TableSpec:
    name: str                 # "<layer>/<table>", also the path below the lake root
    key: tuple                # columns that identify one row
    partition_by: tuple
    schema: pa.Schema
    properties: dict

    @property
    def layer(self) -> str:
        return self.name.split("/")[0]

    def path(self, lake: str | Path | None = None) -> str:
        return str(lake_config.lake_root(lake) / self.name)


def _with_event_date(schema: pa.Schema) -> pa.Schema:
    return pa.schema(list(schema) + [pa.field("event_date", pa.date32())])


def _micro(schema: pa.Schema) -> pa.Schema:
    fields = []
    for f in schema:
        t = pa.timestamp("us", tz=f.type.tz) if pa.types.is_timestamp(f.type) else f.type
        fields.append(pa.field(f.name, t))
    return pa.schema(fields)


# ---- Bronze: one row per complete captured line ----
BRONZE_SCHEMA = pa.schema([
    ("meta_id", pa.string()), ("meta_dt", TS), ("event_date", pa.date32()), ("stream", pa.string()),
    ("wiki_id", pa.string()), ("kafka_topic", pa.string()), ("kafka_partition", pa.int32()),
    ("kafka_offset", pa.int64()), ("raw_json", pa.string()), ("source_file", pa.string()),
    ("source_line", pa.int32()), ("capture_session", pa.string()), ("batch_id", pa.string()),
    ("loaded_at", TS),
])
BRONZE_NAMES = {
    config.STREAM_PAGE_CHANGE: "page_change_events",
    config.STREAM_REVERT_RISK: "revert_risk_events",
    config.STREAM_TAGS: "tags_events",
}
BRONZE = {stream: TableSpec(f"bronze/{name}", ("source_file", "source_line"), ("event_date",), BRONZE_SCHEMA,
                            lake_config.BRONZE_PROPS)
          for stream, name in BRONZE_NAMES.items()}

# ---- Silver: the old Parquet tables ----
REVERT_RISK_OUT_SCHEMA = pa.schema([parse_stream.REVERT_RISK_SCHEMA.field(c) for c in parse_stream.REVERT_RISK_COLUMNS])
TAG_OUT_SCHEMA = pa.schema([parse_stream.TAG_SCHEMA.field(c) for c in parse_stream.TAG_COLUMNS])
CAPTURE_GAPS_SCHEMA = pa.schema([("stream", pa.string()), ("topic", pa.string()), ("partition", pa.int32()),
                                 ("gap_start", TS), ("gap_end", TS), ("gap_s", pa.float64())])
# The schemas of the files that label_live.py and late_reverts.py read (data/parsed/*.parquet).
PARSED_SCHEMAS = {"page_change": parse_stream.PAGE_CHANGE_SCHEMA, "revert_risk": REVERT_RISK_OUT_SCHEMA,
                  "tag_events": TAG_OUT_SCHEMA}

_P = lake_config.SILVER_PROPS
SILVER = {
    "page_change": TableSpec("silver/page_change", ("meta_id",), ("event_date",),
                             _with_event_date(parse_stream.PAGE_CHANGE_SCHEMA), _P),
    "revert_risk": TableSpec("silver/revert_risk", ("rev_id",), (), REVERT_RISK_OUT_SCHEMA, _P),
    "tag_events": TableSpec("silver/tag_events", ("meta_id",), ("event_date",), _with_event_date(TAG_OUT_SCHEMA), _P),
    "capture_gaps": TableSpec("silver/capture_gaps", ("stream", "gap_start"), (), CAPTURE_GAPS_SCHEMA, _P),
    "live_revisions": TableSpec("silver/live_revisions", ("rev_id",), (), _micro(label_live.LIVE_REVISIONS_SCHEMA), _P),
    "live_revert_links": TableSpec("silver/live_revert_links", ("reverted_rev_id",), (),
                                   _micro(label_live.LINKS_SCHEMA), _P),
    "live_revert_links_all": TableSpec("silver/live_revert_links_all", ("reverted_rev_id", "reverting_rev_id"), (),
                                       _micro(label_live.LINKS_ALL_SCHEMA), _P),
    "late_reverts": TableSpec("silver/late_reverts", ("rev_id",), (), _micro(late_reverts.LATE_SCHEMA), _P),
}
# live_ext: the live rules (label_live, unchanged) on the longer window lake_config.LIVE_EXT_WINDOW.
for _n in ("live_revisions", "live_revert_links", "live_revert_links_all"):
    _s = SILVER[_n]
    SILVER[_n.replace("live_", "live_ext_", 1)] = TableSpec(_s.name.replace("live_", "live_ext_", 1), _s.key,
                                                           _s.partition_by, _s.schema, _s.properties)
STREAM_TABLES = ["page_change", "revert_risk", "tag_events", "capture_gaps"]
COHORT_TABLES = ["live_revisions", "live_revert_links", "live_revert_links_all", "late_reverts"]
EXT_TABLES = ["live_ext_revisions", "live_ext_revert_links", "live_ext_revert_links_all"]

ALL = {spec.name: spec for spec in [*BRONZE.values(), *SILVER.values()]}


def bronze_spec(stream: str) -> TableSpec:
    return BRONZE[stream]
