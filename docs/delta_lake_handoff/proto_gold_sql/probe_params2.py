"""Probe 2: is the unbound-parameter error caused by the Delta SQL extension? Modes: plain | delta | delta_legacy.

Run: <spark venv>/bin/python probe_params2.py <mode>
"""
import json, os, sys
from spark_session import LAB, IVY

mode = sys.argv[1]
os.environ["PYSPARK_PYTHON"] = sys.executable
from pyspark.sql import SparkSession
b = (SparkSession.builder.master("local[2]").appName("probe2").config("spark.driver.memory", "2g")
     .config("spark.ui.enabled", "false").config("spark.sql.session.timeZone", "UTC")
     .config("spark.sql.warehouse.dir", LAB + "/warehouse").config("spark.local.dir", LAB + "/sparktmp")
     .config("spark.jars.ivy", IVY))
if mode != "plain":
    from delta import configure_spark_with_delta_pip
    b = (b.config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
          .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"))
    if mode == "delta_legacy":
        b = b.config("spark.sql.legacy.parameterSubstitution.constantsOnly", "true")
    b = configure_spark_with_delta_pip(b)
spark = b.getOrCreate()
spark.sparkContext.setLogLevel("OFF")
tests = [("SELECT :n AS n, CAST(:x AS TIMESTAMP) AS t", {"n": 7, "x": "2026-10-23 00:00:00"}),
         ("SELECT ? AS n", [7])]
if mode != "plain":
    P = os.path.join(LAB, "lake", "probe", "t")
    tests.append((f"MERGE INTO delta.`{P}` t USING (SELECT 2 AS id, :name AS name) s ON t.id = s.id WHEN MATCHED THEN UPDATE SET t.name = s.name", {"name": "bound"}))
for sql, args in tests:
    try:
        print(json.dumps({"mode": mode, "sql": sql[:60], "ok": True, "result": str(spark.sql(sql, args=args).collect())[:200]}))
    except Exception as e:
        print(json.dumps({"mode": mode, "sql": sql[:60], "ok": False, "error": f"{type(e).__name__}: {str(e).strip()[:260]}"}))
spark.stop()
