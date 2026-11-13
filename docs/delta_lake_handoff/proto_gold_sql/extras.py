"""Extra probe: is a run with an OLDER as_of a no-op on tables that already hold a newer state? (It is not.)

Reads only. Run: <spark venv>/bin/python extras.py
"""
import json, os
from run_gold import BASE, GOLD, A1, A2, run_sql, view_step, one
from spark_session import LAB, get_spark

spark = get_spark("extras")
out = {}
view_step(spark, "20_page_obs_view.sql")
for as_of in (A2, A1):
    view_step(spark, "21_page_versions_view.sql", as_of=as_of)
    view_step(spark, "22_page_changes_view.sql")
    r = spark.sql("SELECT count(*) AS rows_the_merge_would_touch, count_if(valid_to IS NULL) AS would_be_set_current FROM v_page_changes").first().asDict()
    out[f"dim_page pre-filter at as_of {as_of}"] = r
out["dim_page versions newer than as_of 1 that an older run would leave behind"] = one(
    spark, f"SELECT count(*) FROM delta.`{{gold}}/dim_page` WHERE valid_from > TIMESTAMP '{A1}'")
# temp view + session variable: is the variable read when the view is queried, or frozen at CREATE VIEW?
spark.sql("DECLARE OR REPLACE VARIABLE v_as_of TIMESTAMP DEFAULT TIMESTAMP '2026-10-23 00:00:00'")
spark.sql(f"CREATE OR REPLACE TEMP VIEW v_var AS SELECT count(*) AS c FROM delta.`{GOLD}/dim_page` WHERE valid_from <= v_as_of")
a = spark.sql("SELECT c FROM v_var").first()[0]
spark.sql("SET VAR v_as_of = TIMESTAMP '2026-10-27 21:00:00'")
b = spark.sql("SELECT c FROM v_var").first()[0]
out["temp view over a session variable: count before / after SET VAR"] = [a, b]
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(LAB, "out", "extras.json"), "w"), indent=1)
spark.stop()
