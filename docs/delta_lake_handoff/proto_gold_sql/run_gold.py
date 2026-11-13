"""Small runner for the Gold SQL files (one statement per .sql file under sql/).

Purpose : build the Gold layer (star schema, SCD2 dim_page, label fact with Change Data Feed, marts)
          from the Silver Delta tables with Spark SQL, record what every step did, and run the checks.
Inputs  : <lab>/lake/silver/* (made by gen_silver.py), <lab>/planted.json, <lab>/sql/*.sql
Outputs : <lab>/lake/gold/* (path-based Delta tables), <lab>/out/run_gold.json (steps, checks, protocol)
Run     : <spark venv>/bin/python run_gold.py          (local[2], spark.driver.memory=4g)

Rules the runner keeps:
- {placeholders} in a .sql file are replaced from a dict; values are checked against a safe pattern.
  Files that use :named parameters get them through spark.sql(text, args={...}).
- Before each write the commit user metadata is set to JSON {"step", "as_of", "snapshot"} and unset after.
- A table version is found through that metadata in DESCRIBE HISTORY, never through a timestamp.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

from spark_session import LAB, get_spark

SQL_DIR = os.path.join(LAB, "sql")
LAKE = os.path.join(LAB, "lake")
OUT = os.path.join(LAB, "out")
UM = "spark.databricks.delta.commitInfo.userMetadata"
PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")
SAFE_VALUE = re.compile(r"^[A-Za-z0-9_ :./\-]*$")
BASE = {"silver": LAKE + "/silver", "gold": LAKE + "/gold", "horizon_s": 345600, "small_group_n": 100}
GOLD = BASE["gold"]
# The two runs of the lab, the first dim_user run (history rows only), and the cohort rules of config.py.
A1, A2, AU1 = "2026-10-23 00:00:00", "2026-10-27 21:00:00", "2026-10-01 00:00:00"
COHORT_ARGS = {"history_start": "2026-09-08 00:00:00", "history_end": "2026-09-11 00:00:00", "history_followup_days": 20,
               "live_start": "2026-10-20 00:00:00", "live_end": "2026-10-23 00:00:00", "live_followup_days": 4}
TABLES = ["dim_cohort", "dim_snapshot", "dim_time", "dim_user", "dim_page", "dim_page_classic", "fact_edit",
          "fact_revert_label", "mart_label_change", "mart_el_curve", "mart_reconciliation", "recon_mismatch"]
METRIC_KEYS = ["numTargetRowsInserted", "numTargetRowsUpdated", "numTargetRowsDeleted", "numTargetRowsCopied",
               "numSourceRows", "numOutputRows", "numTargetFilesAdded", "numTargetFilesRemoved", "numFiles",
               "numTargetChangeFilesAdded", "executionTimeMs"]
STEPS: list[dict] = []
CHECKS: list[dict] = []


def render(name: str, params: dict) -> str:
    text = open(os.path.join(SQL_DIR, name)).read()

    def sub(m):
        key = m.group(1)
        if key not in params:
            raise KeyError(f"{name}: no value for {{{key}}}")
        val = str(params[key])
        if not SAFE_VALUE.match(val):
            raise ValueError(f"{name}: unsafe value for {{{key}}}: {val!r}")
        return val

    return PLACEHOLDER.sub(sub, text)


def table_version(spark, path: str):
    """Latest version of a path-based table, or None when it does not exist yet."""
    if not os.path.isdir(os.path.join(path, "_delta_log")):
        return None
    return spark.sql(f"DESCRIBE HISTORY delta.`{path}` LIMIT 1").first()["version"]


def find_version(spark, path: str, **match) -> int:
    """Newest version whose commit user metadata (JSON) has all the given values. No timestamps involved."""
    hits = []
    for h in spark.sql(f"DESCRIBE HISTORY delta.`{path}`").collect():
        try:
            meta = json.loads(h["userMetadata"] or "{}")
        except ValueError:
            continue
        if all(meta.get(k) == v for k, v in match.items()):
            hits.append(h["version"])
    if not hits:
        raise LookupError(f"no commit with {match} in {path}")
    return max(hits)


def newest_as_of(spark, path: str, step: str):
    """Newest as_of among the commits that this step wrote (from the commit user metadata), or None."""
    best = None
    if table_version(spark, path) is None:
        return None
    for h in spark.sql(f"DESCRIBE HISTORY delta.`{path}`").collect():
        try:
            meta = json.loads(h["userMetadata"] or "{}")
        except ValueError:
            continue
        if meta.get("step") == step and meta.get("as_of") and (best is None or meta["as_of"] > best):
            best = meta["as_of"]
    return best


def run_sql(spark, name: str, params: dict | None = None, meta: dict | None = None, args: dict | None = None):
    """Run one .sql file. meta is given for a statement that writes: it becomes the commit user metadata."""
    sql = render(name, {**BASE, **(params or {})})
    if meta is not None:
        spark.conf.set(UM, json.dumps(meta, sort_keys=True))
    try:
        df = spark.sql(sql, args=args) if args else spark.sql(sql)
        return df.collect()
    finally:
        if meta is not None:
            spark.conf.unset(UM)


def write_step(spark, label: str, sql_name: str, table: str, as_of=None, snapshot=None, params=None, args=None,
               step=None) -> dict:
    """Run a writing statement and record: seconds, version before / after, operation metrics, error."""
    path = f"{GOLD}/{table}"
    v0 = table_version(spark, path)
    meta = {"step": step or table, "as_of": as_of, "snapshot": snapshot}
    p = dict(params or {})
    if as_of is not None:
        p["as_of"] = as_of
    if snapshot is not None:
        p["snapshot"] = snapshot
    t0, err, rows = time.time(), None, None
    try:
        # The MERGE statements move a table to its state "as of" a time. An older as_of would move it back
        # (dim_page: closed versions would be opened again), so it is refused.
        newest = newest_as_of(spark, path, meta["step"]) if as_of is not None else None
        if newest is not None and as_of < newest:
            raise RuntimeError(f"refused: as_of {as_of} is older than the newest committed as_of {newest} of {table}")
        rows = run_sql(spark, sql_name, p, meta=meta, args=args)
    except Exception as e:  # recorded, the run goes on (some failures are expected and wanted)
        err = f"{type(e).__name__}: {str(e)[:900]}"
    rec = {"label": label, "sql": sql_name, "table": table, "as_of": as_of, "snapshot": snapshot,
           "seconds": round(time.time() - t0, 2), "version_before": v0, "version_after": table_version(spark, path),
           "error": err}
    rec["wrote_commit"] = rec["version_after"] != v0
    if rec["wrote_commit"]:
        h = spark.sql(f"DESCRIBE HISTORY delta.`{path}` LIMIT 1").first()
        om = h["operationMetrics"] or {}
        rec.update(operation=h["operation"], userMetadata=h["userMetadata"],
                   metrics={k: om[k] for k in METRIC_KEYS if k in om})
    if rows and len(rows) == 1:
        rec["result"] = rows[0].asDict()
    STEPS.append(rec)
    print("STEP", json.dumps(rec, default=str), flush=True)
    return rec


def view_step(spark, sql_name: str, **params):
    t0 = time.time()
    run_sql(spark, sql_name, params)
    print(f"VIEW {sql_name} {params} {time.time() - t0:.2f}s", flush=True)


def check(name: str, got, want, note: str = "") -> bool:
    ok = got == want
    CHECKS.append({"check": name, "got": got, "want": want, "ok": ok, "note": note})
    print(("PASS " if ok else "FAIL ") + f"{name}: got={got} want={want} {note}", flush=True)
    return ok


def one(spark, sql: str):
    """First column of the first row of a query (placeholders are filled from BASE)."""
    return spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), sql)).first()[0]


def jvm_peak_rss_mb():
    """Peak resident memory (VmHWM) of the Spark driver JVM: the java process below this Python process."""
    out = subprocess.run(["ps", "-eo", "pid,ppid,comm"], capture_output=True, text=True).stdout.splitlines()[1:]
    rows = [ln.split(None, 2) for ln in out]
    kids, todo = set(), [str(os.getpid())]
    while todo:
        cur = todo.pop()
        for pid, ppid, _ in rows:
            if ppid == cur and pid not in kids:
                kids.add(pid)
                todo.append(pid)
    best = None
    for pid, _, comm in rows:
        if pid in kids and comm.strip().startswith("java"):
            for ln in open(f"/proc/{pid}/status"):
                if ln.startswith("VmHWM"):
                    best = max(best or 0, int(ln.split()[1]) / 1024)
    return None if best is None else round(best, 1)


def dim_page_run(spark, label: str, as_of: str) -> dict:
    view_step(spark, "21_page_versions_view.sql", as_of=as_of)
    view_step(spark, "22_page_changes_view.sql")
    return write_step(spark, label, "23_dim_page_merge.sql", "dim_page", as_of=as_of)


def dim_page_classic_run(spark, label: str, as_of: str) -> dict:
    view_step(spark, "21_page_versions_view.sql", as_of=as_of)
    view_step(spark, "24_page_classic_changed_view.sql")
    return write_step(spark, label, "25_dim_page_classic_merge.sql", "dim_page_classic", as_of=as_of)


FACT_JOIN_SQL = """
WITH r AS (
  SELECT wiki_db, rev_id, page_id, ts, page_title_historical AS title_at_edit FROM delta.`{silver}/history_revisions`
  UNION ALL
  SELECT wiki_db, rev_id, page_id, ts, page_title AS title_at_edit FROM delta.`{silver}/live_revisions`
),
j AS (
  SELECT r.rev_id, count(p.page_key) AS n_match, max(p.page_key) AS page_key,
         max(p.title) AS title, max(r.title_at_edit) AS title_at_edit
  FROM r LEFT JOIN delta.`{gold}/%s` p
    ON p.wiki_db = r.wiki_db AND p.page_id = r.page_id AND r.ts >= p.valid_from AND (p.valid_to IS NULL OR r.ts < p.valid_to)
  GROUP BY r.rev_id
)
SELECT count(*) AS facts, count_if(j.n_match = 1) AS exactly_one, count_if(j.n_match = 0) AS no_version,
       count_if(j.n_match > 1) AS many_versions, count_if(NOT (j.title <=> j.title_at_edit)) AS title_differs,
       count_if(j.page_key <=> f.page_key) AS same_key_as_fact_edit
FROM j JOIN delta.`{gold}/fact_edit` f ON f.rev_id = j.rev_id
"""


def main() -> None:
    t_all = time.time()
    planted = json.load(open(os.path.join(LAB, "planted.json")))
    spark = get_spark()
    info = {"spark": spark.version, "python": sys.version.split()[0], "delta": None,
            "session_timezone": spark.conf.get("spark.sql.session.timeZone"), "master": spark.sparkContext.master,
            "driver_memory": spark.conf.get("spark.driver.memory"), "start_seconds": round(time.time() - t_all, 1)}
    try:
        from importlib.metadata import version
        info["delta"] = version("delta-spark")
        info["pyspark"] = version("pyspark")
    except Exception as e:
        info["delta"] = f"unknown ({e})"
    print("INFO", json.dumps(info), flush=True)

    # ---- 0. DDL: CREATE TABLE IF NOT EXISTS, path-based ------------------------------------------------
    for t in TABLES:
        ddl = "dim_page" if t.startswith("dim_page") else t
        write_step(spark, f"ddl {t}", f"ddl/{ddl}.sql", t, params={"dim_page": t}, step=f"ddl:{t}")

    # ---- 1. dim_cohort ---------------------------------------------------------------------------------
    r = write_step(spark, "dim_cohort", "10_dim_cohort_merge.sql", "dim_cohort", params=COHORT_ARGS)
    check("dim_cohort written", r["error"], None)
    r = write_step(spark, "dim_cohort re-run", "10_dim_cohort_merge.sql", "dim_cohort", params=COHORT_ARGS)
    check("dim_cohort re-run writes no commit", r["wrote_commit"], False)
    check("dim_cohort rows", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_cohort`"), 2)

    # ---- 2. first run, as_of 1 ---------------------------------------------------------------------------
    view_step(spark, "20_page_obs_view.sql")
    r1 = dim_page_run(spark, "dim_page run 1", A1)
    n1 = one(spark, "SELECT count(*) FROM delta.`{gold}/dim_page`")
    check("dim_page run 1: distinct pages", one(spark, "SELECT count(DISTINCT page_id) FROM delta.`{gold}/dim_page`"),
          planted["sizes"]["pages_total"] - planted["sizes"]["pages_first_seen_after_as_of_1"])
    check("dim_page run 1: pages without exactly one current row",
          one(spark, "SELECT count(*) FROM (SELECT page_id, count_if(is_current) AS c FROM delta.`{gold}/dim_page` GROUP BY wiki_db, page_id) WHERE c <> 1"), 0)
    dim_page_classic_run(spark, "dim_page_classic run 1", A1)
    ru1 = write_step(spark, "dim_user run 1 (history rows only)", "13_dim_user_merge.sql", "dim_user", as_of=AU1)
    check("dim_user run 1 inserted", int(ru1["metrics"]["numTargetRowsInserted"]), planted["dim_user"]["rows_run_1"])
    write_step(spark, "dim_time run 1", "12_dim_time_merge.sql", "dim_time", as_of=A1)
    rf1 = write_step(spark, "fact_edit run 1", "30_fact_edit_merge.sql", "fact_edit", as_of=A1)
    check("fact_edit run 1 inserted", int(rf1["metrics"]["numTargetRowsInserted"]), planted["fact_edit"]["rows"])
    check("fact_edit live_revert_flag true after run 1",
          one(spark, "SELECT count_if(live_revert_flag) FROM delta.`{gold}/fact_edit`"), planted["fact_edit"]["live_flag_true_at_as_of_1"])

    # ---- 3. second run, as_of 2 --------------------------------------------------------------------------
    r2 = dim_page_run(spark, "dim_page run 2", A2)
    n2 = one(spark, "SELECT count(*) FROM delta.`{gold}/dim_page`")
    check("dim_page run 2 closed some rows and inserted new versions",
          int(r2["metrics"]["numTargetRowsUpdated"]) > 0 and int(r2["metrics"]["numTargetRowsInserted"]) > 0, True,
          f"updated={r2['metrics']['numTargetRowsUpdated']} inserted={r2['metrics']['numTargetRowsInserted']} rows {n1} -> {n2}")
    r3 = dim_page_run(spark, "dim_page run 3 (same as_of)", A2)
    check("dim_page run 3 with the same as_of writes no commit", r3["wrote_commit"], False,
          f"version stays {r3['version_after']}")
    # classic form: first the 'all versions' demo (expected to fail), then the one-row-per-page run
    view_step(spark, "21_page_versions_view.sql", as_of=A2)
    rdemo = write_step(spark, "dim_page_classic all-versions demo (expected to fail)",
                       "26_dim_page_classic_all_versions_merge.sql", "dim_page_classic", as_of=A2)
    check("classic MERGE fed with several versions per page fails", rdemo["error"] is not None and not rdemo["wrote_commit"], True,
          (rdemo["error"] or "")[:160])
    dim_page_classic_run(spark, "dim_page_classic run 2", A2)
    rc3 = dim_page_classic_run(spark, "dim_page_classic run 3 (same as_of)", A2)
    check("dim_page_classic run 3 writes no commit", rc3["wrote_commit"], False)

    ru2 = write_step(spark, "dim_user run 2", "13_dim_user_merge.sql", "dim_user", as_of=A2)
    check("dim_user run 2 updated", int(ru2["metrics"]["numTargetRowsUpdated"]), planted["dim_user"]["updated_by_run_2"])
    check("dim_user run 2 inserted", int(ru2["metrics"]["numTargetRowsInserted"]), planted["dim_user"]["inserted_by_run_2"])
    r = write_step(spark, "dim_user re-run", "13_dim_user_merge.sql", "dim_user", as_of=A2)
    check("dim_user re-run writes no commit", r["wrote_commit"], False)
    r = write_step(spark, "dim_time run 2", "12_dim_time_merge.sql", "dim_time", as_of=A2)
    check("dim_time run 2 (no new minute) writes no commit", r["wrote_commit"], False)
    rf2 = write_step(spark, "fact_edit run 2", "30_fact_edit_merge.sql", "fact_edit", as_of=A2)
    check("fact_edit run 2 updated", int(rf2["metrics"]["numTargetRowsUpdated"]), planted["fact_edit"]["rows_updated_by_run_2"])
    check("fact_edit run 2 inserted", int(rf2["metrics"]["numTargetRowsInserted"]), 0)
    r = write_step(spark, "fact_edit re-run", "30_fact_edit_merge.sql", "fact_edit", as_of=A2)
    check("fact_edit re-run writes no commit", r["wrote_commit"], False)

    # ---- 4. label fact: two snapshots ---------------------------------------------------------------------
    rl = {}
    for snap in ("2026-09", "2026-10"):
        write_step(spark, f"dim_snapshot {snap}", "11_dim_snapshot_merge.sql", "dim_snapshot", snapshot=snap)
        rl[snap] = write_step(spark, f"fact_revert_label {snap}", "40_fact_revert_label_merge.sql", "fact_revert_label", snapshot=snap)
    fl = planted["fact_revert_label"]
    check("fact_revert_label 2026-09 inserted", int(rl["2026-09"]["metrics"]["numTargetRowsInserted"]), fl["rows_after_2026-09"])
    check("fact_revert_label 2026-10 is ONE commit", rl["2026-10"]["version_after"] - rl["2026-10"]["version_before"], 1)
    check("fact_revert_label 2026-10 updated", int(rl["2026-10"]["metrics"]["numTargetRowsUpdated"]), fl["updated_by_2026-10"])
    check("fact_revert_label 2026-10 inserted", int(rl["2026-10"]["metrics"]["numTargetRowsInserted"]), fl["inserted_by_2026-10"])
    r = write_step(spark, "fact_revert_label 2026-10 re-run", "40_fact_revert_label_merge.sql", "fact_revert_label", snapshot="2026-10")
    check("fact_revert_label re-run of 2026-10 writes no commit", r["wrote_commit"], False)
    r = write_step(spark, "fact_revert_label 2026-09 re-run after 2026-10", "40_fact_revert_label_merge.sql", "fact_revert_label", snapshot="2026-09")
    check("fact_revert_label re-run of the OLDER snapshot 2026-09 writes no commit", r["wrote_commit"], False)
    r = write_step(spark, "dim_snapshot 2026-10 re-run", "11_dim_snapshot_merge.sql", "dim_snapshot", snapshot="2026-10")
    check("dim_snapshot re-run writes no commit", r["wrote_commit"], False)

    # versions through commit user metadata
    label_path = f"{GOLD}/fact_revert_label"
    v09 = find_version(spark, label_path, step="fact_revert_label", snapshot="2026-09")
    v10 = find_version(spark, label_path, step="fact_revert_label", snapshot="2026-10")
    check("versions found by userMetadata", [v09, v10], [rl["2026-09"]["version_after"], rl["2026-10"]["version_after"]])
    sql_only = None
    try:
        sql_only = spark.sql(
            f"SELECT max(version) FROM (DESCRIBE HISTORY delta.`{label_path}`) "
            "WHERE get_json_object(userMetadata, '$.step') = 'fact_revert_label' "
            "AND get_json_object(userMetadata, '$.snapshot') = '2026-09'").first()[0]
    except Exception as e:
        sql_only = f"{type(e).__name__}: {str(e)[:300]}"
    check("probe: SELECT ... FROM (DESCRIBE HISTORY ...) is NOT supported (ParseException), so the lookup stays in Python",
          str(sql_only).startswith("ParseException"), True, str(sql_only)[:120].replace("\n", " "))

    # Change Data Feed between the two versions, two ways, by path
    cdf_sql = {r["_change_type"]: r["n"] for r in spark.sql(
        f"SELECT _change_type, count(*) AS n FROM table_changes_by_path('{label_path}', {v09 + 1}, {v10}) GROUP BY _change_type").collect()}
    cdf_opt = {r["_change_type"]: r["count"] for r in (
        spark.read.format("delta").option("readChangeFeed", "true").option("startingVersion", v09 + 1)
        .option("endingVersion", v10).load(label_path).groupBy("_change_type").count().collect())}
    want_cdf = {"insert": fl["inserted_by_2026-10"], "update_postimage": 700, "update_preimage": 700}
    check("CDF table_changes_by_path between the two label versions", dict(sorted(cdf_sql.items())), want_cdf)
    check("CDF readChangeFeed option by path", dict(sorted(cdf_opt.items())), want_cdf)

    # ---- 5. mart_label_change from the change feed ---------------------------------------------------------
    def label_change_run(label: str, start=None):
        last = one(spark, "SELECT coalesce(max(commit_version), 0) FROM delta.`{gold}/mart_label_change`")
        start_v = last + 1 if start is None else start
        end_v = table_version(spark, label_path)
        if start_v > end_v:
            print(f"SKIP {label}: change feed already read up to version {last}", flush=True)
            return None
        return write_step(spark, label, "50_mart_label_change_merge.sql", "mart_label_change",
                          params={"start_version": start_v, "end_version": end_v})

    rm = label_change_run("mart_label_change")
    check("mart_label_change inserted", int(rm["metrics"]["numTargetRowsInserted"]), 700)
    check("mart_label_change second run is skipped (nothing new in the feed)", label_change_run("mart_label_change re-run"), None)
    r = label_change_run("mart_label_change forced re-read from version 1", start=1)
    check("mart_label_change forced re-read writes no commit", r["wrote_commit"], False)
    got = {r["change_class"]: r["n"] for r in spark.sql(
        f"SELECT change_class, count(*) AS n FROM delta.`{GOLD}/mart_label_change` GROUP BY change_class").collect()}
    lc = planted["label_changes"]
    check("mart_label_change classes", dict(sorted(got.items())),
          {"became_reverted": lc["became_reverted"], "became_unreverted": lc["became_unreverted"],
           "reverter_or_time_changed": lc["reverter_or_time_changed"]})
    check("mart_label_change from/to snapshot", [tuple(r) for r in spark.sql(
        f"SELECT DISTINCT from_snapshot, to_snapshot, commit_version FROM delta.`{GOLD}/mart_label_change`").collect()],
        [("2026-09", "2026-10", v10)])

    # ---- 6. time travel: as known then against now ---------------------------------------------------------
    tt = [r.asDict() for r in run_sql(spark, "80_time_travel_then_and_now.sql", {"v_2026_09": v09, "v_2026_10": v10})]
    print("TIME TRAVEL", json.dumps(tt), flush=True)
    check("time travel: history-cohort reverted, then and now",
          [(r["snapshot"], r["label_version"], r["reverted_as_known_then"], r["reverted_now"]) for r in tt],
          [("2026-09", v09, fl["history_cohort_reverted_any_as_of_2026-09"], fl["history_cohort_reverted_any_as_of_2026-10"]),
           ("2026-10", v10, fl["history_cohort_reverted_any_as_of_2026-10"], fl["history_cohort_reverted_any_as_of_2026-10"])])
    check("VERSION AS OF reads the 2026-09 load", one(spark, f"SELECT count(*) FROM delta.`{label_path}` VERSION AS OF {v09} WHERE last_changed_snapshot = '2026-09'"),
          fl["rows_after_2026-09"])

    # ---- 7. marts ------------------------------------------------------------------------------------------
    r = write_step(spark, "mart_el_curve", "60_mart_el_curve_overwrite.sql", "mart_el_curve", as_of=A2, snapshot="2026-10")
    check("mart_el_curve written", r["error"], None)
    rp = {"cohort_id": "live", "label_version": v10}
    view_step(spark, "69_recon_view.sql", snapshot="2026-10", **rp)
    r = write_step(spark, "mart_reconciliation", "70_mart_reconciliation_replace.sql", "mart_reconciliation", snapshot="2026-10", params=rp)
    check("mart_reconciliation written (INSERT INTO ... REPLACE WHERE)", r["error"], None)
    r = write_step(spark, "recon_mismatch", "71_recon_mismatch_replace.sql", "recon_mismatch", snapshot="2026-10", params=rp)
    check("recon_mismatch written (INSERT INTO ... REPLACE WHERE)", r["error"], None)
    rec = planted["reconciliation_live_vs_2026-10"]
    got = {r["recon_class"]: r["n_revisions"] for r in spark.sql(f"SELECT recon_class, n_revisions FROM delta.`{GOLD}/mart_reconciliation`").collect()}
    check("mart_reconciliation class counts", dict(sorted(got.items())),
          {k: rec[k] for k in sorted(["both_reverted", "dump_only", "neither", "not_in_dump", "stream_only"])})
    got = {r["recon_class"]: r["n"] for r in spark.sql(f"SELECT recon_class, count(*) AS n FROM delta.`{GOLD}/recon_mismatch` GROUP BY recon_class").collect()}
    check("recon_mismatch rows per class", dict(sorted(got.items())), {"dump_only": rec["dump_only"], "not_in_dump": rec["not_in_dump"], "stream_only": rec["stream_only"]})

    # ---- 8. checks on the finished tables ------------------------------------------------------------------
    view_step(spark, "21_page_versions_view.sql", as_of=A2)
    check("dim_page: distinct pages", one(spark, "SELECT count(DISTINCT page_id) FROM delta.`{gold}/dim_page`"), planted["sizes"]["pages_total"])
    check("dim_page: pages without exactly one current row",
          one(spark, "SELECT count(*) FROM (SELECT page_id, count_if(is_current) AS c FROM delta.`{gold}/dim_page` GROUP BY wiki_db, page_id) WHERE c <> 1"), 0)
    check("dim_page: gaps or overlaps (valid_to <> next valid_from)",
          one(spark, "SELECT count(*) FROM (SELECT valid_to, lead(valid_from) OVER (PARTITION BY wiki_db, page_id ORDER BY valid_from) AS nf "
                     "FROM delta.`{gold}/dim_page`) WHERE NOT (valid_to <=> nf)"), 0)
    check("dim_page: empty or negative intervals", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_page` WHERE valid_to <= valid_from"), 0)
    check("dim_page: pages whose first version does not start at the sentinel",
          one(spark, "SELECT count(*) FROM (SELECT min(valid_from) AS m FROM delta.`{gold}/dim_page` GROUP BY wiki_db, page_id) WHERE m <> TIMESTAMP '1900-01-01 00:00:00'"), 0)
    check("dim_page: is_current <> (valid_to IS NULL)", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_page` WHERE is_current <> (valid_to IS NULL)"), 0)
    check("dim_page: duplicate page_key", one(spark, "SELECT count(*) - count(DISTINCT page_key) FROM delta.`{gold}/dim_page`"), 0)
    check("dim_page: rows that differ from the computed version list (both directions)",
          one(spark, "SELECT (SELECT count(*) FROM (SELECT * FROM delta.`{gold}/dim_page` EXCEPT SELECT * FROM v_page_versions)) + "
                     "(SELECT count(*) FROM (SELECT * FROM v_page_versions EXCEPT SELECT * FROM delta.`{gold}/dim_page`))"), 0)
    fj = spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), FACT_JOIN_SQL % "dim_page")).first().asDict()
    check("fact_edit as-of join to dim_page", fj, {"facts": 80000, "exactly_one": 80000, "no_version": 0, "many_versions": 0,
                                                    "title_differs": 0, "same_key_as_fact_edit": 80000})
    fjc = spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), FACT_JOIN_SQL % "dim_page_classic")).first().asDict()
    print("CLASSIC FACT JOIN", json.dumps(fjc), flush=True)
    cmp_sql = ("SELECT (SELECT count(*) FROM delta.`{gold}/dim_page`) AS rows_method_1, (SELECT count(*) FROM delta.`{gold}/dim_page_classic`) AS rows_classic, "
               "(SELECT count(*) FROM (SELECT * FROM delta.`{gold}/dim_page` EXCEPT SELECT * FROM delta.`{gold}/dim_page_classic`)) AS only_in_method_1, "
               "(SELECT count(*) FROM (SELECT * FROM delta.`{gold}/dim_page_classic` EXCEPT SELECT * FROM delta.`{gold}/dim_page`)) AS only_in_classic, "
               "(SELECT count(DISTINCT page_id) FROM (SELECT * FROM delta.`{gold}/dim_page` EXCEPT SELECT * FROM delta.`{gold}/dim_page_classic`)) AS pages_that_differ, "
               "(SELECT count(*) FROM (SELECT page_id FROM delta.`{gold}/dim_page_classic` GROUP BY page_id HAVING count_if(is_current) <> 1)) AS classic_pages_not_one_current")
    scd_cmp = spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), cmp_sql)).first().asDict()
    print("SCD2 COMPARISON", json.dumps(scd_cmp), flush=True)
    # which pages differ: pages with 2 or more new versions inside one run
    multi = spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), f"""
        SELECT count_if(v_run1 >= 2) AS pages_2plus_versions_in_run_1, count_if(v_run2 >= 2) AS pages_2plus_new_versions_in_run_2,
               count_if(v_run1 >= 2 OR v_run2 >= 2) AS pages_2plus_in_any_run
        FROM (SELECT page_id, count_if(valid_from <= TIMESTAMP '{A1}') AS v_run1, count_if(valid_from > TIMESTAMP '{A1}') AS v_run2
              FROM delta.`{{gold}}/dim_page` GROUP BY page_id)""")).first().asDict()
    print("SCD2 MULTI-CHANGE PAGES", json.dumps(multi), flush=True)
    check("SCD2: pages that differ between the methods = pages with 2+ new versions in one run",
          scd_cmp["pages_that_differ"], multi["pages_2plus_in_any_run"])

    check("dim_user rows", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_user`"), planted["dim_user"]["rows_run_2"])
    check("dim_user: duplicate user_key", one(spark, "SELECT count(*) - count(DISTINCT user_key) FROM delta.`{gold}/dim_user`"), 0)
    check("fact_edit rows without a dim_user row", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` f LEFT ANTI JOIN delta.`{gold}/dim_user` u ON u.user_key = f.user_key"), 0)
    check("fact_edit rows with user_key 'unknown'", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` WHERE user_key = 'unknown'"), planted["fact_edit"]["user_key_unknown_rows"])
    check("dim_time rows", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_time`"), planted["dim_time"]["rows"])
    check("fact_edit rows without a dim_time row", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` f LEFT ANTI JOIN delta.`{gold}/dim_time` d ON d.time_key = f.time_key"), 0)
    check("dim_time rows not used by fact_edit", one(spark, "SELECT count(*) FROM delta.`{gold}/dim_time` d LEFT ANTI JOIN delta.`{gold}/fact_edit` f ON d.time_key = f.time_key"), 0)
    check("dim_time: minute_start matches time_key, Monday = 1",
          one(spark, "SELECT count(*) FROM delta.`{gold}/dim_time` WHERE time_key <> CAST(date_format(minute_start, 'yyyyMMddHHmm') AS BIGINT) "
                     "OR hour <> hour(minute_start) OR date <> CAST(minute_start AS DATE) OR day_of_week <> dayofweek(minute_start - INTERVAL 1 DAY)"), 0)
    check("fact_edit rows", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit`"), planted["fact_edit"]["rows"])
    check("fact_edit: duplicate (wiki_db, rev_id)", one(spark, "SELECT count(*) - count(DISTINCT wiki_db, rev_id) FROM delta.`{gold}/fact_edit`"), 0)
    check("fact_edit rows per cohort", {r[0]: r[1] for r in spark.sql(f"SELECT cohort_id, count(*) FROM delta.`{GOLD}/fact_edit` GROUP BY cohort_id ORDER BY 1").collect()},
          {"history": 40000, "live": 40000})
    check("fact_edit live_revert_flag true after run 2", one(spark, "SELECT count_if(live_revert_flag) FROM delta.`{gold}/fact_edit`"), planted["fact_edit"]["live_flag_true_at_as_of_2"])
    check("fact_edit history rows have a NULL live flag", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` WHERE cohort_id = 'history' AND live_revert_flag IS NOT NULL"), 0)
    check("fact_edit rows whose page_key is not in dim_page", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_edit` f LEFT ANTI JOIN delta.`{gold}/dim_page` p ON p.page_key = f.page_key"), 0)
    fe_path = f"{GOLD}/fact_edit"
    cdf_fe = {r["_change_type"]: r["n"] for r in spark.sql(
        f"SELECT _change_type, count(*) AS n FROM table_changes_by_path('{fe_path}', {rf2['version_after']}, {rf2['version_after']}) GROUP BY _change_type").collect()}
    check("fact_edit CDF of run 2", dict(sorted(cdf_fe.items())), {"update_postimage": planted["fact_edit"]["rows_updated_by_run_2"], "update_preimage": planted["fact_edit"]["rows_updated_by_run_2"]})
    check("fact_revert_label rows", one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label`"), fl["rows_after_2026-10"])
    check("fact_revert_label: duplicate (wiki_db, rev_id)", one(spark, "SELECT count(*) - count(DISTINCT wiki_db, rev_id) FROM delta.`{gold}/fact_revert_label`"), 0)
    check("fact_revert_label: reverted rows without label_dt, or not reverted rows with one",
          one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label` WHERE is_identity_reverted <> (label_dt IS NOT NULL)"), 0)
    check("fact_revert_label: first_reverted_snapshot kept for rows that became unreverted",
          one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label` WHERE NOT is_identity_reverted AND first_reverted_snapshot = '2026-09'"), lc["became_unreverted"])
    check("fact_revert_label: September revisions first reverted in 2026-10",
          one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label` f JOIN delta.`{silver}/history_slim` s ON s.snapshot = '2026-09' AND s.revision_id = f.rev_id "
                     "WHERE f.first_reverted_snapshot = '2026-10'"), lc["became_reverted"])
    check("fact_revert_label: rows of the 2026-09 load with last_changed_snapshot 2026-10",
          one(spark, "SELECT count(*) FROM delta.`{gold}/fact_revert_label` f JOIN delta.`{silver}/history_slim` s ON s.snapshot = '2026-09' AND s.revision_id = f.rev_id "
                     "WHERE f.last_changed_snapshot = '2026-10'"), 700)
    check("dim_snapshot rows", [tuple(r) for r in spark.sql(f"SELECT snapshot, revision_rows FROM delta.`{GOLD}/dim_snapshot` ORDER BY snapshot").collect()],
          [("2026-09", 150000), ("2026-10", 300000)])
    check("mart_el_curve rows (3 series x 5 user kinds x 9 waits)", one(spark, "SELECT count(*) FROM delta.`{gold}/mart_el_curve`"), 135)
    check("commits without the JSON user metadata, all Gold tables", sum(
        sum(1 for h in spark.sql(f"DESCRIBE HISTORY delta.`{GOLD}/{t}`").collect() if not (h["userMetadata"] or "").startswith("{"))
        for t in TABLES), 0)
    check("user metadata conf is unset after the run", spark.conf.get(UM, None) in (None, ""), True)
    r = write_step(spark, "dim_page with an OLDER as_of (must be refused)", "23_dim_page_merge.sql", "dim_page", as_of=A1)
    check("a run with an older as_of is refused and writes no commit", (r["error"] or "").startswith("RuntimeError: refused") and not r["wrote_commit"], True,
          (r["error"] or "")[:140])

    # ---- 9. protocol, counts, memory ------------------------------------------------------------------------
    protocol, counts = {}, {}
    for t in TABLES:
        d = spark.sql(f"DESCRIBE DETAIL delta.`{GOLD}/{t}`").first().asDict()
        protocol[t] = {"minReaderVersion": d["minReaderVersion"], "minWriterVersion": d["minWriterVersion"],
                       "tableFeatures": sorted(d["tableFeatures"] or []), "properties": dict(d["properties"] or {}),
                       "numFiles": d["numFiles"], "sizeInBytes": d["sizeInBytes"], "partitionColumns": d["partitionColumns"],
                       "clusteringColumns": d.get("clusteringColumns"), "version": table_version(spark, f"{GOLD}/{t}")}
        counts[t] = spark.sql(f"SELECT count(*) FROM delta.`{GOLD}/{t}`").first()[0]
        print("PROTOCOL", t, json.dumps(protocol[t]), flush=True)
    # small samples for the report
    for title, q in [
        ("EL CURVE (user_kind = all)", "SELECT * FROM delta.`{gold}/mart_el_curve` WHERE user_kind = 'all' ORDER BY cohort_id, label_source, wait_s"),
        ("EL CURVE (small groups, 1 h)", "SELECT * FROM delta.`{gold}/mart_el_curve` WHERE wait_s = 3600 ORDER BY cohort_id, label_source, user_kind"),
        ("RECONCILIATION", "SELECT * FROM delta.`{gold}/mart_reconciliation` ORDER BY n_revisions DESC"),
        ("RECON MISMATCH sample", "SELECT * FROM delta.`{gold}/recon_mismatch` ORDER BY recon_class, rev_id LIMIT 6"),
        ("DIM_PAGE sample (page with most versions)", "SELECT * FROM delta.`{gold}/dim_page` WHERE page_id = (SELECT page_id FROM delta.`{gold}/dim_page` GROUP BY page_id ORDER BY count(*) DESC, page_id LIMIT 1) ORDER BY valid_from"),
        ("DIM_PAGE versions per page", "SELECT n_versions, count(*) AS pages FROM (SELECT page_id, count(*) AS n_versions FROM delta.`{gold}/dim_page` GROUP BY page_id) GROUP BY n_versions ORDER BY n_versions"),
        ("DIM_PAGE current rows", "SELECT is_deleted, namespace, count(*) AS n FROM delta.`{gold}/dim_page` WHERE is_current GROUP BY is_deleted, namespace ORDER BY 1, 2"),
        ("LABEL CHANGE sample", "SELECT * FROM delta.`{gold}/mart_label_change` ORDER BY change_class, rev_id LIMIT 5"),
        ("DIM tables", "SELECT * FROM delta.`{gold}/dim_cohort` ORDER BY cohort_id"),
        ("DIM snapshot", "SELECT * FROM delta.`{gold}/dim_snapshot` ORDER BY snapshot"),
    ]:
        print(f"\n--- {title}", flush=True)
        spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), q)).show(60, truncate=False)
    peak = jvm_peak_rss_mb()
    rt = spark._jvm.java.lang.Runtime.getRuntime()
    mem = {"jvm_peak_rss_mb": peak, "jvm_heap_max_mb": round(rt.maxMemory() / 2**20), "jvm_heap_total_mb": round(rt.totalMemory() / 2**20)}
    result = {"info": info, "steps": STEPS, "checks": CHECKS, "protocol": protocol, "counts": counts, "memory": mem,
              "time_travel": tt, "scd2_comparison": scd_cmp, "scd2_multi_change": multi, "classic_fact_join": fjc,
              "fact_join": fj, "versions": {"fact_revert_label_2026-09": v09, "fact_revert_label_2026-10": v10},
              "total_seconds": round(time.time() - t_all, 1)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "run_gold.json"), "w") as f:
        json.dump(result, f, indent=1, default=str)
    n_fail = sum(1 for c in CHECKS if not c["ok"])
    print(f"\nMEMORY {json.dumps(mem)}")
    print(f"CHECKS {len(CHECKS) - n_fail} passed, {n_fail} failed; total {result['total_seconds']} s", flush=True)
    spark.stop()


if __name__ == "__main__":
    main()
