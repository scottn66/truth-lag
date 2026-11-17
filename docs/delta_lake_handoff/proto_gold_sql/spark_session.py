"""SparkSession factory for the Gold SQL lab (copy of spark_lab/scripts/lab.py get_spark, folders changed).

Every side folder (warehouse, shuffle files, Derby home) is under the lab folder. The Ivy cache is the
one the spark_lab already filled, so nothing is downloaded.
"""
import os
import sys

LAB = os.environ.get(
    "GOLD_LAB",
    "/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/gold_sql_lab",
)
IVY = os.environ.get(
    "GOLD_IVY",
    "/tmp/claude-0/-home-user-truth-lag/05079947-a92e-556e-95f1-17427edba26f/scratchpad/plan_lab/spark_lab/ivy",
)


def get_spark(app="truthlag_gold", extra=None, driver_mem="4g", master="local[2]"):
    # Python workers must be the SAME interpreter as the driver (PATH python3 can be another minor version).
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    b = (SparkSession.builder.master(master).appName(app)
         .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
         .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
         .config("spark.driver.memory", driver_mem)
         .config("spark.sql.shuffle.partitions", "4")
         .config("spark.ui.enabled", "false")
         .config("spark.ui.showConsoleProgress", "false")
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.sql.warehouse.dir", LAB + "/warehouse")
         .config("spark.local.dir", LAB + "/sparktmp")
         .config("spark.jars.ivy", IVY)
         .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={LAB}/derby -Duser.timezone=UTC"))
    for k, v in (extra or {}).items():
        b = b.config(k, v)
    spark = configure_spark_with_delta_pip(b).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark
