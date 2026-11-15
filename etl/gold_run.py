"""Gold: the star schema and the E(L) marts, written with Spark SQL (D1).

Run
    python -m etl.gold_run --as-of 2026-10-27T20:59:59.999999Z --steps ddl,dims,facts,labels,marts

Based on proto_gold_sql/run_gold.py (helpers render, table_version, find_version, newest_as_of, run_sql,
write_step, view_step, one, dim_page_run). Differences from the lab runner:
  * any error stops the run with a non-zero exit code (write_step raises);
  * every SQL parameter comes from ec-hw2/config.py or etl/lake_config.py; the waits are a temp view;
  * guard 1: the commit metadata (step, as_of, snapshot) is set before every write;
  * guard 2: an as_of older than the newest as_of already committed to a table is refused;
  * guard 3: the as_of must equal data/lake/_runs/latest.json, and every Silver version listed there must
    still be current (the cohort build and Gold see the same data);
  * guard 4: the marts step stops when as_of < config.LIVE_FINAL_AFTER (live follow-up incomplete).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

from . import delta_io, lake_config, tables
from .hw2 import config
from .spark_session import get_spark

SQL_DIR = os.path.join(os.path.dirname(__file__), "sql")
UM = "spark.databricks.delta.commitInfo.userMetadata"
PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")
SAFE_VALUE = re.compile(r"^[A-Za-z0-9_ :./\-]*$")
METRIC_KEYS = ["numTargetRowsInserted", "numTargetRowsUpdated", "numTargetRowsDeleted", "numOutputRows",
               "numTargetRowsCopied", "numSourceRows", "executionTimeMs"]
TABLES = ["dim_cohort", "dim_snapshot", "dim_time", "dim_user", "dim_page", "fact_edit", "fact_revert_label",
          "mart_el_curve", "mart_el_by_burst"]
STEPS: list[dict] = []


def sql_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def base_params(lake=None) -> dict:
    root = lake_config.lake_root(lake)
    return {
        "silver": str(root / "silver"), "gold": str(root / "gold"),
        "horizon_s": config.LIVE_FOLLOWUP_S, "small_group_n": config.RISK_MIN_GROUP_N,
        "history_start": sql_ts(config.HISTORY_WINDOW[0]), "history_end": sql_ts(config.HISTORY_WINDOW[1]),
        "live_start": sql_ts(config.LIVE_WINDOW[0]), "live_end": sql_ts(config.LIVE_WINDOW[1]),
        "live_ext_start": sql_ts(lake_config.LIVE_EXT_WINDOW[0]), "live_ext_end": sql_ts(lake_config.LIVE_EXT_WINDOW[1]),
        "history_followup_days": config.HISTORY_FOLLOWUP_DAYS, "live_followup_days": config.LIVE_FOLLOWUP_DAYS,
        "dump_cutoff": sql_ts(config.HISTORY_DUMP_LAST_REVISION),
    }


BASE: dict = {}


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
    if not os.path.isdir(os.path.join(path, "_delta_log")):
        return None
    return spark.sql(f"DESCRIBE HISTORY delta.`{path}` LIMIT 1").first()["version"]


def _metas(spark, path: str):
    for h in spark.sql(f"DESCRIBE HISTORY delta.`{path}`").collect():
        try:
            yield h["version"], json.loads(h["userMetadata"] or "{}")
        except ValueError:
            continue


def find_version(spark, path: str, **match) -> int:
    """Newest version whose commit user metadata has all the given values. No timestamps involved (D9)."""
    hits = [v for v, m in _metas(spark, path) if all(m.get(k) == x for k, x in match.items())]
    if not hits:
        raise LookupError(f"no commit with {match} in {path}")
    return max(hits)


def newest_as_of(spark, path: str, step: str):
    if table_version(spark, path) is None:
        return None
    best = None
    for _, m in _metas(spark, path):
        if m.get("step") == step and m.get("as_of") and (best is None or m["as_of"] > best):
            best = m["as_of"]
    return best


def run_sql(spark, name: str, params: dict | None = None, meta: dict | None = None):
    sql = render(name, {**BASE, **(params or {})})
    if meta is not None:
        spark.conf.set(UM, json.dumps(meta, sort_keys=True))
    try:
        return spark.sql(sql).collect()
    finally:
        if meta is not None:
            spark.conf.unset(UM)


def write_step(spark, label: str, sql_name: str, table: str, as_of=None, snapshot=None, params=None,
               step=None) -> dict:
    """Run one writing statement. Raises on any error (the run stops)."""
    path = f"{BASE['gold']}/{table}"
    v0 = table_version(spark, path)
    meta = {"step": step or table, "as_of": as_of, "snapshot": snapshot}
    p = dict(params or {})
    if as_of is not None:
        p["as_of"] = sql_ts(datetime.fromisoformat(as_of.replace("Z", "+00:00")))
    if snapshot is not None:
        p["snapshot"] = snapshot
    newest = newest_as_of(spark, path, meta["step"]) if as_of is not None else None
    if newest is not None and as_of < newest:
        raise RuntimeError(f"refused: as_of {as_of} is older than the newest committed as_of {newest} of {table}")
    t0 = time.time()
    run_sql(spark, sql_name, p, meta=meta)
    rec = {"label": label, "sql": sql_name, "table": table, "as_of": as_of, "snapshot": snapshot,
           "seconds": round(time.time() - t0, 2), "version_before": v0, "version_after": table_version(spark, path)}
    rec["wrote_commit"] = rec["version_after"] != v0
    if rec["wrote_commit"]:
        h = spark.sql(f"DESCRIBE HISTORY delta.`{path}` LIMIT 1").first()
        om = h["operationMetrics"] or {}
        rec.update(operation=h["operation"], metrics={k: om[k] for k in METRIC_KEYS if k in om})
    STEPS.append(rec)
    print("STEP", json.dumps(rec, default=str), flush=True)
    return rec


def view_step(spark, sql_name: str, **params):
    t0 = time.time()
    run_sql(spark, sql_name, params)
    print(f"VIEW {sql_name} {time.time() - t0:.2f}s", flush=True)


def one(spark, sql: str):
    return spark.sql(PLACEHOLDER.sub(lambda m: str(BASE[m.group(1)]), sql)).first()[0]


def make_waits_view(spark) -> None:
    rows = [(label, int(s)) for label, s in config.WAIT_POINTS_S.items()]
    spark.createDataFrame(rows, "wait_label string, wait_s bigint").createOrReplaceTempView("v_waits")


def check_latest(as_of: str, lake=None) -> dict:
    """Guard 3."""
    from .silver_cohorts import latest_path
    p = latest_path(lake)
    if not p.exists():
        raise SystemExit(f"refused: {p} missing; run the cohort build first")
    doc = json.loads(p.read_text())
    if doc["as_of"] != as_of:
        raise SystemExit(f"refused: as_of {as_of} differs from the cohort build's {doc['as_of']} in {p}")
    root = lake_config.lake_root(lake)
    for name, v in doc["versions"].items():
        cur = delta_io.version(root / name)
        if cur != v:
            raise SystemExit(f"refused: {name} is at version {cur}, latest.json says {v}")
    return doc


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m etl.gold_run")
    ap.add_argument("--as-of", required=True, help="YYYY-MM-DDTHH:MM:SS.ffffffZ")
    ap.add_argument("--snapshot", default="2026-09")
    ap.add_argument("--steps", default="ddl,dims,facts,labels,marts")
    ap.add_argument("--lake", default=None)
    args = ap.parse_args(argv)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", args.as_of):
        raise SystemExit("as_of must be spelled YYYY-MM-DDTHH:MM:SS.ffffffZ")
    steps = set(args.steps.split(","))
    as_of = args.as_of
    as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if "marts" in steps and as_of_dt < config.LIVE_FINAL_AFTER:                       # guard 4
        raise SystemExit(f"refused: marts need as_of >= {config.LIVE_FINAL_AFTER.isoformat()}")
    latest = check_latest(as_of, args.lake)                                            # guard 3
    from .silver_cohorts import ensure_ext_tables
    ensure_ext_tables(args.lake)          # empty live_ext tables before the first extended build (Gold reads them)
    BASE.update(base_params(args.lake))
    t_all = time.time()
    spark = get_spark("truthlag_gold")
    print("INFO", json.dumps({"spark": spark.version, "as_of": as_of, "steps": sorted(steps),
                              "start_s": round(time.time() - t_all, 1)}), flush=True)
    G = BASE["gold"]

    if "ddl" in steps:
        for t in TABLES:
            write_step(spark, f"ddl {t}", f"ddl/{t}.sql", t, step=f"ddl:{t}")
    if "dims" in steps:
        write_step(spark, "dim_cohort", "10_dim_cohort_merge.sql", "dim_cohort")
        write_step(spark, "dim_snapshot", "11_dim_snapshot_merge.sql", "dim_snapshot", snapshot=args.snapshot,
                   params={"snapshot_cutoff": sql_ts(config.HISTORY_DUMP_LAST_REVISION)})
        write_step(spark, "dim_time", "12_dim_time_merge.sql", "dim_time", as_of=as_of)
        write_step(spark, "dim_user", "13_dim_user_merge.sql", "dim_user", as_of=as_of)
        view_step(spark, "20_page_obs_view.sql", as_of=sql_ts(as_of_dt))
        view_step(spark, "21_page_versions_view.sql", as_of=sql_ts(as_of_dt))
        view_step(spark, "22_page_changes_view.sql")
        write_step(spark, "dim_page", "23_dim_page_merge.sql", "dim_page", as_of=as_of)
    if "facts" in steps:
        write_step(spark, "fact_edit", "30_fact_edit_merge.sql", "fact_edit", as_of=as_of)
    if "labels" in steps:
        write_step(spark, f"fact_revert_label {args.snapshot}", "40_fact_revert_label_merge.sql", "fact_revert_label",
                   snapshot=args.snapshot)
    if "marts" in steps:
        make_waits_view(spark)
        view_step(spark, "55_reverts_view.sql")
        write_step(spark, "mart_el_curve", "60_mart_el_curve_overwrite.sql", "mart_el_curve", as_of=as_of)
        write_step(spark, "mart_el_by_burst", "61_mart_el_by_burst_overwrite.sql", "mart_el_by_burst", as_of=as_of)

    counts = {t: one(spark, f"SELECT count(*) FROM delta.`{G}/{t}`") for t in TABLES
              if table_version(spark, f"{G}/{t}") is not None}
    versions = {t: table_version(spark, f"{G}/{t}") for t in TABLES}
    out = {"as_of": as_of, "steps": STEPS, "row_counts": counts, "versions": versions,
           "silver_latest": latest, "seconds": round(time.time() - t_all, 1)}
    runs = lake_config.lake_root(args.lake) / "_runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"gold_{as_of.replace(':', '')}.json").write_text(json.dumps(out, indent=1, default=str))
    print("DONE", json.dumps({"row_counts": counts, "versions": versions, "seconds": out["seconds"]}), flush=True)
    spark.stop()


if __name__ == "__main__":
    main()
