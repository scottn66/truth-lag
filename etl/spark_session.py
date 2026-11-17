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


def _start_quietly(builder, app: str):
    """Start the JVM with its console output (Ivy resolution, start-up warnings) sent to a log file.

    The JVM inherits file descriptors 1 and 2 from Python when it starts, so they point at the log file only
    while the session is created; Python's own output goes back to the terminal right after. Errors still reach
    Python as exceptions. Set TRUTHLAG_SPARK_VERBOSE=1 to see everything on the terminal instead.
    """
    log_dir = SPARK_HOME_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{app}.log"
    sys.stdout.flush()
    sys.stderr.flush()
    saved_out, saved_err = os.dup(1), os.dup(2)
    with open(log_path, "w") as log:
        os.dup2(log.fileno(), 1)
        os.dup2(log.fileno(), 2)
        try:
            spark = builder.getOrCreate()
        finally:
            os.dup2(saved_out, 1)
            os.dup2(saved_err, 2)
            os.close(saved_out)
            os.close(saved_err)
    return spark, log_path


def get_spark(app: str = "truthlag", extra: dict | None = None, driver_mem: str = "6g",
              master: str = "local[4]", shuffle_partitions: int = 8, quiet: bool = False):
    """quiet=True (used by the demo programs) keeps Spark's start-up output out of the terminal."""
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
    builder = configure_spark_with_delta_pip(b)
    if quiet and not os.environ.get("TRUTHLAG_SPARK_VERBOSE"):
        t0 = time.time()
        print("Starting Spark with Delta Lake ...", flush=True)
        try:
            spark, log_path = _start_quietly(builder, app)
        except Exception:
            print(f"Spark did not start; its output is in {SPARK_HOME_DIR / 'logs' / (app + '.log')}", flush=True)
            raise
        print(f"Spark {spark.version} ready in {time.time() - t0:.0f} s (start-up log: {log_path})\n", flush=True)
    else:
        spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark
