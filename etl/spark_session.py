"""SparkSession factory for the lake (Spark SQL writes Gold; it also runs the streaming demos).

Based on proto_gold_sql/spark_session.py of the hand-off kit, with the fixes that made Spark
start on Scott's Mac (macOS, OpenJDK 21, pyspark 4.2.0, delta-spark 4.4.1) on 2026-11-15:

  1. Netty failed with "setsockopt() failed: Invalid argument" when the driver bound to the
     LAN address. Fix: bind the driver to 127.0.0.1 and use the NIO transport.
  2. Python turned Spark timestamps into local wall-clock times (7 h off in PDT). Fix: TZ=UTC
     for the Python process, plus the UTC session time zone.
  3. JAVA_HOME is set to Homebrew's openjdk@21 when it is not set.

Side folders (Ivy jars, Derby, shuffle files, warehouse) live in data/spark_home/.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from .lake_config import SPARK_HOME_DIR

BREW_JDK21 = "/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"


def prepare_env() -> None:
    """Environment fixes that must be in place before the JVM starts."""
    os.environ["TZ"] = "UTC"
    time.tzset()
    if not os.environ.get("JAVA_HOME") and Path(BREW_JDK21).is_dir():
        os.environ["JAVA_HOME"] = BREW_JDK21
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    os.environ["PYSPARK_PYTHON"] = sys.executable          # workers must be the driver's interpreter
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable


def get_spark(app: str = "truthlag", extra: dict | None = None, driver_mem: str = "6g",
              master: str = "local[4]", shuffle_partitions: int = 8):
    prepare_env()
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    home = str(SPARK_HOME_DIR)
    b = (SparkSession.builder.master(master).appName(app)
         .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
         .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
         .config("spark.driver.memory", driver_mem)
         .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
         .config("spark.ui.enabled", "false")
         .config("spark.ui.showConsoleProgress", "false")
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.driver.host", "127.0.0.1")
         .config("spark.driver.bindAddress", "127.0.0.1")
         .config("spark.rpc.io.mode", "NIO")
         .config("spark.shuffle.io.mode", "NIO")
         .config("spark.network.io.mode", "NIO")
         .config("spark.sql.warehouse.dir", home + "/warehouse")
         .config("spark.local.dir", home + "/sparktmp")
         .config("spark.jars.ivy", home + "/ivy")
         .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={home}/derby -Duser.timezone=UTC"))
    for k, v in (extra or {}).items():
        b = b.config(k, v)
    spark = configure_spark_with_delta_pip(b).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark
