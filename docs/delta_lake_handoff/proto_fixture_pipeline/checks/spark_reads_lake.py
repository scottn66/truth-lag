"""Extra check: Spark (same venv) reads the lake that the delta-rs prototype wrote.

Run: TRUTHLAG_HW2_DIR=<ec-hw2> <venv>/bin/python step1/spark_reads_lake.py <proto dir> <home> <work dir>
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
PROTO, HOME, WORK = sys.argv[1], os.path.abspath(sys.argv[2]), Path(sys.argv[3]).resolve()
sys.path.insert(0, PROTO)
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from etl import bronze_stream, delta_io, silver_cohorts, silver_stream, tables
from etl.hw2 import config
from tests import test_stream as ts

shutil.rmtree(WORK, ignore_errors=True)
raw, hist, lake = WORK / "raw", WORK / "history", WORK / "lake"
pc, tags, risk = ts.scenario_events()
ts.write_part(raw, config.STREAM_PAGE_CHANGE, pc)
ts.write_part(raw, config.STREAM_PAGE_CHANGE, [pc[4]], session="20261024T010000-bbbbbb")
ts.write_part(raw, config.STREAM_TAGS, tags)
ts.write_part(raw, config.STREAM_REVERT_RISK, risk)
hist.mkdir(parents=True)
pq.write_table(pa.Table.from_pandas(ts.slim_frame(), schema=pa.schema([(c, pa.string()) for c in config.HISTORY_SLIM_COLUMNS]),
                                    preserve_index=False), hist / config.HISTORY_SLIM_FILE)
b = bronze_stream.run(raw, lake=lake)
silver_stream.build(b["dates"], lake=lake)
MID = ts.T0 + 45 * ts.S
c_mid = silver_cohorts.build(MID, history_dir=hist, lake=lake)
c_end = silver_cohorts.build(None, history_dir=hist, lake=lake)

from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
t0 = time.time()
builder = (SparkSession.builder.master("local[2]").appName("fixture_pipeline_lake")
           .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
           .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
           .config("spark.driver.memory", "4g").config("spark.sql.shuffle.partitions", "4")
           .config("spark.sql.session.timeZone", "UTC")
           .config("spark.sql.warehouse.dir", HOME + "/warehouse")
           .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={HOME}/derby -Duser.timezone=UTC")
           .config("spark.local.dir", HOME + "/sparktmp").config("spark.jars.ivy", HOME + "/ivy")
           .config("spark.ui.enabled", "false").config("spark.ui.showConsoleProgress", "false"))
spark = configure_spark_with_delta_pip(builder).getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print(f"spark {spark.version} started in {time.time() - t0:.1f} s")

# 1. every table: Spark row count == delta-rs row count
counts = {}
for name, spec in tables.ALL.items():
    n_spark = spark.read.format("delta").load(spec.path(lake)).count()
    n_rs = delta_io.read_table(spec.path(lake)).num_rows
    assert n_spark == n_rs, (name, n_spark, n_rs)
    counts[name] = n_spark
print("row counts, Spark == delta-rs:", counts)

# 2. values: page_change (after two delta-rs MERGE commits), tag lists, cohort times
def spark_pdf(name, cols, order):
    rows = spark.read.format("delta").load(tables.ALL[name].path(lake)).select(*cols).orderBy(*order).collect()
    return [tuple(r) for r in rows]

def rs_rows(name, cols, order):
    df = delta_io.read_pandas(tables.ALL[name].path(lake), columns=cols, sort_by=order)
    out = []
    for rec in df.itertuples(index=False):
        row = []
        for v in rec:
            if isinstance(v, pd.Timestamp):
                v = v.tz_convert("UTC").tz_localize(None).to_pydatetime()      # Spark collect() gives naive UTC datetimes
            elif hasattr(v, "tolist"):
                v = v.tolist()
            elif v is not None and not isinstance(v, (str, list)) and pd.isna(v):
                v = None
            elif isinstance(v, float) and v == int(v) and False:
                v = int(v)
            row.append(v)
        out.append(tuple(row))
    return out

checks = {"silver/page_change": (["meta_id", "meta_dt", "rev_dt", "kind", "is_bot", "revert_method", "event_date"], ["meta_id"]),
          "silver/tag_events": (["meta_id", "meta_dt", "tags", "added", "mw_reverted_added"], ["meta_id"]),
          "silver/live_revert_links": (["reverted_rev_id", "reverting_rev_id", "reverted_ts", "known_at", "K_s", "method", "by_other"], ["reverted_rev_id"]),
          "bronze/page_change_events": (["source_file", "source_line", "meta_id", "meta_dt", "raw_json", "event_date"], ["source_file", "source_line"])}
for name, (cols, order) in checks.items():
    a, b_ = spark_pdf(name, cols, order), rs_rows(name, cols, order)
    assert a == b_, (name, [x for x in zip(a, b_) if x[0] != x[1]][:2])
    print(f"values equal in Spark and delta-rs: {name} {cols} ({len(a)} rows)")

# 3. column names that are SQL words
pcp = tables.ALL["silver/page_change"].path(lake)
for q in (f"SELECT partition, offset, topic FROM delta.`{pcp}` LIMIT 1",
          f"SELECT class, count(*) AS n FROM delta.`{tables.ALL['silver/late_reverts'].path(lake)}` GROUP BY class ORDER BY class",
          f"SELECT stream, partition, gap_s FROM delta.`{tables.ALL['silver/capture_gaps'].path(lake)}` ORDER BY gap_s"):
    try:
        print("OK  ", q.split(" FROM ")[0], "->", [tuple(r) for r in spark.sql(q).collect()])
    except Exception as e:
        print("FAIL", q.split(" FROM ")[0], "->", type(e).__name__, str(e).splitlines()[0][:300])

# 4. time travel from Spark, version found through the commit metadata
links = tables.ALL["silver/live_revert_links"].path(lake)
hist_df = spark.sql(f"DESCRIBE HISTORY delta.`{links}`")
rows = hist_df.selectExpr("version", "operation", "engineInfo", "get_json_object(userMetadata, '$.as_of') AS as_of",
                          "get_json_object(userMetadata, '$.rows') AS rows").orderBy("version").collect()
print("Spark DESCRIBE HISTORY of live_revert_links:", [tuple(r) for r in rows])
print("Spark DESCRIBE HISTORY columns:", hist_df.columns)
print("delta-rs history keys of the same commit:", sorted(delta_io.history(links)[0]))
v_mid = hist_df.where(f"get_json_object(userMetadata, '$.as_of') = '{c_mid['as_of']}'").selectExpr("max(version) AS v").first().v
assert v_mid == delta_io.find_version(links, {"as_of": c_mid["as_of"]}) == 1
at_mid = {r.reverted_rev_id for r in spark.sql(f"SELECT reverted_rev_id FROM delta.`{links}` VERSION AS OF {v_mid}").collect()}
at_end = {r.reverted_rev_id for r in spark.sql(f"SELECT reverted_rev_id FROM delta.`{links}`").collect()}
print("Spark: reverted revisions known at", c_mid["as_of"], sorted(at_mid), "; known only later:", sorted(at_end - at_mid))
assert sorted(at_end - at_mid) == [102, 103, 9001]

# 5. the partition filter prunes in Spark, and Spark sees the table properties
n = spark.sql(f"SELECT count(*) AS n FROM delta.`{pcp}` WHERE event_date = DATE'2026-10-19'").first().n
det = spark.sql(f"DESCRIBE DETAIL delta.`{tables.ALL['bronze/page_change_events'].path(lake)}`").first()
print("page_change rows on 2026-10-19:", n, "| bronze detail: reader", det.minReaderVersion, "writer", det.minWriterVersion,
      "features", det.tableFeatures, "partitions", det.partitionColumns)
assert n == 1
spark.stop()
after = {name: delta_io.version(spec.path(lake)) for name, spec in tables.ALL.items()}
print("versions after the Spark reads (unchanged by reading):", after)
print("SPARK READS LAKE OK")
