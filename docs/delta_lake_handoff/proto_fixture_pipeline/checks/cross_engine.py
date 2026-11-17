"""Step 1 (c): one venv, both engines. delta-rs writes -> Spark reads; Spark writes -> delta-rs reads.

Run: <venv>/bin/python step1/cross_engine.py <home>
<home> is a scratch folder for the tables, the warehouse, derby, the Ivy cache and Spark temp files.
"""
import datetime as dt
import json
import os
import shutil
import sys
import time

os.environ["PYSPARK_PYTHON"] = sys.executable          # else the workers start PATH python3 (3.13 here)
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

HOME = os.path.abspath(sys.argv[1])
T = HOME + "/tables"
shutil.rmtree(T, ignore_errors=True)
os.makedirs(T)
UTC = dt.timezone.utc
KEEP = {"delta.logRetentionDuration": "interval 3650 days",
        "delta.deletedFileRetentionDuration": "interval 3650 days",
        "delta.enableExpiredLogCleanup": "false"}

# ---- 1. delta-rs writes a partitioned table with the planned properties ----
schema = pa.schema([("meta_id", pa.string()), ("meta_dt", pa.timestamp("us", tz="UTC")),
                    ("event_date", pa.date32()), ("rev_id", pa.int64()), ("tags", pa.list_(pa.string()))])
rows = pa.table({
    "meta_id": ["a", "b", "c"],
    "meta_dt": [dt.datetime(2026, 10, 20, 23, 59, 59, 999999, tzinfo=UTC), dt.datetime(2026, 10, 21, 0, 0, 0, 1, tzinfo=UTC),
                dt.datetime(2026, 10, 21, 12, 0, 0, tzinfo=UTC)],
    "event_date": [dt.date(2026, 10, 20), dt.date(2026, 10, 21), dt.date(2026, 10, 21)],
    "rev_id": [1, 2, None], "tags": [["x", "y"], [], None]}, schema=schema)
rs_path = T + "/rs_written"
DeltaTable.create(rs_path, schema=schema, partition_by=["event_date"], mode="ignore",
                  configuration={**KEEP, "delta.appendOnly": "true", "delta.dataSkippingStatsColumns": "meta_id,meta_dt"})
write_deltalake(rs_path, rows, mode="append")
p = DeltaTable(rs_path).protocol()
print("delta-rs table protocol:", p.min_reader_version, p.min_writer_version, p.reader_features, p.writer_features)

# ---- 2. Spark session from the same venv ----
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
import pyspark

t0 = time.time()
b = (SparkSession.builder.master("local[2]").appName("fixture_pipeline_step1")
     .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
     .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
     .config("spark.driver.memory", "4g")
     .config("spark.sql.shuffle.partitions", "4")
     .config("spark.sql.session.timeZone", "UTC")
     .config("spark.sql.warehouse.dir", HOME + "/warehouse")
     .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={HOME}/derby -Duser.timezone=UTC")
     .config("spark.local.dir", HOME + "/sparktmp")
     .config("spark.jars.ivy", HOME + "/ivy")
     .config("spark.ui.enabled", "false")
     .config("spark.ui.showConsoleProgress", "false"))
spark = configure_spark_with_delta_pip(b).getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print(f"spark {spark.version} (pyspark {pyspark.__version__}) started in {time.time() - t0:.1f} s; session tz", spark.conf.get("spark.sql.session.timeZone"))

df = spark.read.format("delta").load(rs_path)
got = sorted([(r.meta_id, r.meta_dt.isoformat(), str(r.event_date), r.rev_id, r.tags) for r in df.collect()])
print("Spark reads the delta-rs table:", got)
assert got == [("a", "2026-10-20T23:59:59.999999", "2026-10-20", 1, ["x", "y"]),
               ("b", "2026-10-21T00:00:00.000001", "2026-10-21", 2, []),
               ("c", "2026-10-21T12:00:00", "2026-10-21", None, None)], got
n = spark.sql(f"SELECT count(*) AS n FROM delta.`{rs_path}` WHERE event_date = DATE'2026-10-21'").first().n
assert n == 2, n
det = spark.sql(f"DESCRIBE DETAIL delta.`{rs_path}`").first()
print("Spark DESCRIBE DETAIL of the delta-rs table: reader", det.minReaderVersion, "writer", det.minWriterVersion,
      "features", det.tableFeatures, "partitions", det.partitionColumns, "properties", det.properties)

# ---- 3. Spark writes a table, delta-rs reads it ----
sp_path = T + "/spark_written"
spark.sql(f"""CREATE TABLE delta.`{sp_path}` (wiki_db STRING, rev_id BIGINT, known_at TIMESTAMP, lag_s DOUBLE, event_date DATE)
USING DELTA PARTITIONED BY (event_date)
TBLPROPERTIES ('delta.logRetentionDuration'='interval 3650 days', 'delta.deletedFileRetentionDuration'='interval 3650 days',
               'delta.enableExpiredLogCleanup'='false')""")
spark.sql(f"""INSERT INTO delta.`{sp_path}` VALUES
 ('enwiki', 101, TIMESTAMP'2026-10-20 10:00:02.123456', 2.5, DATE'2026-10-20'),
 ('enwiki', 102, TIMESTAMP'2026-10-21 00:00:00', NULL, DATE'2026-10-21')""")
spark.stop()

t = DeltaTable(sp_path)
p = t.protocol()
print("Spark table protocol seen by delta-rs:", p.min_reader_version, p.min_writer_version, p.reader_features, p.writer_features)
pdf = t.to_pandas().sort_values("rev_id").reset_index(drop=True)
print("delta-rs reads the Spark table:\n", pdf, "\n", pdf.dtypes.to_dict())
assert pdf["rev_id"].tolist() == [101, 102]
assert str(pdf["known_at"].dtype) == "datetime64[us, UTC]", pdf["known_at"].dtype
assert pdf["known_at"].iloc[0].isoformat() == "2026-10-20T10:00:02.123456+00:00"
assert t.metadata().partition_columns == ["event_date"]
print("history of the Spark table (delta-rs):", [(h["version"], h.get("operation"), h.get("engineInfo")) for h in t.history()])
print("history of the delta-rs table:", [(h["version"], h.get("operation"), h.get("engineInfo")) for h in DeltaTable(rs_path).history()])
side = [x for x in os.listdir(os.getcwd()) if x in ("spark-warehouse", "metastore_db", "derby.log")]
print("side files in cwd:", side)
print("STEP1C OK")
