"""Step 1 extra: pandas <-> Spark conversion works in the one venv (pyspark 4.2.0, pandas 2.3.3, pyarrow 26.0.1).

Run: <venv>/bin/python step1/spark_pandas.py <home>
"""
import os
import sys

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
HOME = os.path.abspath(sys.argv[1])
import pandas as pd
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

b = (SparkSession.builder.master("local[2]").appName("fixture_pipeline_pandas")
     .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
     .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
     .config("spark.driver.memory", "4g").config("spark.sql.shuffle.partitions", "4")
     .config("spark.sql.session.timeZone", "UTC").config("spark.sql.warehouse.dir", HOME + "/warehouse")
     .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={HOME}/derby -Duser.timezone=UTC")
     .config("spark.local.dir", HOME + "/sparktmp").config("spark.jars.ivy", HOME + "/ivy")
     .config("spark.ui.enabled", "false").config("spark.ui.showConsoleProgress", "false"))
spark = configure_spark_with_delta_pip(b).getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
pdf = pd.DataFrame({"rev_id": [1, 2, 3], "known_at": pd.to_datetime(["2026-10-20T10:00:02.123456Z", "2026-10-21T00:00:00Z", None], utc=True, format="ISO8601"),
                    "lag_s": [1.5, None, 3.0], "kind": ["a", None, "c"]})
for arrow in ("true", "false"):
    spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", arrow)
    sdf = spark.createDataFrame(pdf)
    back = sdf.orderBy("rev_id").toPandas()
    print(f"arrow={arrow}: schema {sdf.schema.simpleString()} -> pandas dtypes {dict(back.dtypes.astype(str))}")
    assert back["rev_id"].tolist() == [1, 2, 3]
    assert back["known_at"].iloc[0] == pd.Timestamp("2026-10-20 10:00:02.123456"), back["known_at"].iloc[0]   # naive, UTC wall time
    assert pd.isna(back["known_at"].iloc[2]) and back["kind"].tolist()[0] == "a"
# a Python UDF runs in a worker of the same interpreter
from pyspark.sql import functions as F, types as T
n = spark.range(5).select(F.udf(lambda x: x * 2, T.LongType())("id").alias("y")).agg(F.sum("y")).first()[0]
assert n == 20
print("python udf ok:", n, "| worker python:", spark.range(1).select(F.udf(lambda x: __import__('sys').version.split()[0])("id")).first()[0])
spark.stop()
print("SPARK PANDAS OK")
