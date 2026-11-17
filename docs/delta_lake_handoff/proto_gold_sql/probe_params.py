"""Probe: where do named parameters (:name) and SQL session variables work with Delta 4.4.1 on Spark 4.2.0?

Run: <spark venv>/bin/python probe_params.py      (about 40 s; writes only under <lab>/lake/probe)
"""
import shutil, os, json
from spark_session import LAB, get_spark

P = os.path.join(LAB, "lake", "probe", "t")
shutil.rmtree(os.path.join(LAB, "lake", "probe"), ignore_errors=True)
spark = get_spark("probe_params")
spark.sql(f"CREATE TABLE delta.`{P}` (id BIGINT, name STRING, ts TIMESTAMP) USING DELTA")
spark.sql(f"INSERT INTO delta.`{P}` VALUES (1, 'a', TIMESTAMP '2026-10-20 00:00:00'), (2, 'b', TIMESTAMP '2026-10-25 00:00:00')")
ARGS = {"x": "2026-10-23 00:00:00", "n": 7, "name": "zz"}
TESTS = [
    ("01 SELECT with :named parameters", f"SELECT count(*) AS c, :n AS n FROM delta.`{P}` WHERE ts <= CAST(:x AS TIMESTAMP)", ARGS),
    ("02 INSERT ... SELECT with :named parameters", f"INSERT INTO delta.`{P}` SELECT :n, :name, CAST(:x AS TIMESTAMP)", ARGS),
    ("03 UPDATE with :named parameters", f"UPDATE delta.`{P}` SET name = :name WHERE id = 1 AND ts <= CAST(:x AS TIMESTAMP)", ARGS),
    ("04 MERGE, parameter in ON / SET only", f"MERGE INTO delta.`{P}` t USING (SELECT 1 AS id) s ON t.id = s.id AND t.ts <= CAST(:x AS TIMESTAMP) WHEN MATCHED THEN UPDATE SET t.name = :name", ARGS),
    ("05 MERGE, parameter inside the USING subquery", f"MERGE INTO delta.`{P}` t USING (SELECT 2 AS id, :name AS name) s ON t.id = s.id WHEN MATCHED THEN UPDATE SET t.name = s.name", ARGS),
    ("06 CREATE TEMP VIEW with a :named parameter", "CREATE OR REPLACE TEMP VIEW v_p AS SELECT CAST(:x AS TIMESTAMP) AS as_of", ARGS),
    ("07 DECLARE a SQL session variable", "DECLARE OR REPLACE VARIABLE v_as_of TIMESTAMP DEFAULT TIMESTAMP '2026-10-23 00:00:00'", None),
    ("08 SELECT with the session variable", f"SELECT count(*) AS c FROM delta.`{P}` WHERE ts <= v_as_of", None),
    ("09 MERGE, session variable inside the USING subquery", f"MERGE INTO delta.`{P}` t USING (SELECT id, 'var' AS name FROM delta.`{P}` WHERE ts <= v_as_of AND id = 2) s ON t.id = s.id WHEN MATCHED THEN UPDATE SET t.name = s.name", None),
    ("10 CREATE TEMP VIEW that reads the session variable", f"CREATE OR REPLACE TEMP VIEW v_var AS SELECT * FROM delta.`{P}` WHERE ts <= v_as_of", None),
    ("11 EXECUTE IMMEDIATE MERGE with USING ... AS", f"EXECUTE IMMEDIATE 'MERGE INTO delta.`{P}` t USING (SELECT 2 AS id, :name AS name) s ON t.id = s.id WHEN MATCHED THEN UPDATE SET t.name = s.name' USING 'exec' AS name", None),
    ("12 SELECT ... FROM (DESCRIBE HISTORY ...)", f"SELECT max(version) AS v FROM (DESCRIBE HISTORY delta.`{P}`)", None),
    ("13 DESCRIBE HISTORY ... LIMIT 1", f"DESCRIBE HISTORY delta.`{P}` LIMIT 1", None),
]
out = []
for name, sql, args in TESTS:
    try:
        rows = (spark.sql(sql, args=args) if args else spark.sql(sql)).collect()
        res = {"test": name, "ok": True, "result": str([r.asDict() for r in rows][:2])[:300]}
    except Exception as e:
        res = {"test": name, "ok": False, "error": f"{type(e).__name__}: {str(e).strip()[:400]}"}
    out.append(res)
    print(json.dumps(res), flush=True)
print("FINAL ROWS", [r.asDict() for r in spark.sql(f"SELECT id, name FROM delta.`{P}` ORDER BY id").collect()])
json.dump(out, open(os.path.join(LAB, "out", "probe_params.json"), "w"), indent=1)
spark.stop()
