"""Run the SQL comparison queries on SQLite and save the results.

Purpose
    For each file in queries/sql/ (compare_top_contested.sql, compare_mutual_reverts.sql):
    1. check that the numbers in its "params" block (if it has one) equal config.py;
    2. run the file text exactly as it is on data/tables/truthlag.sqlite, opened
       read-only: 1 warm-up run, then 7 timed runs; we report the median;
    3. write results/sql_<file>.csv and .md (the .md shows the first rows as a table).
       compare_top_contested.sql has no rank column (as Mongo Q2), so this script adds
       rank = 1, 2, ... in the row order, as run_mongo.py does.
       Human editors appear only as pseudonyms: the same aliases as the Mongo and
       Cypher result files. Bots keep their names.
    Then it checks the results:
    - compare_top_contested = pandas on the Parquet tables, and = the Mongo Q2 and
      Cypher result files (the same 20 page_ids in the same order, scores rounded to
      6 digits, the same edits, revert_actions and reverted_editors);
    - compare_mutual_reverts = pandas (the full ordered list of editor keys), and = the
      Mongo and Cypher result files (the full ordered list of aliases);
    - no result file shows an editor key.
    A check is skipped (and says so) when the Mongo or Cypher file is missing.

Inputs
    data/tables/truthlag.sqlite and _SUCCESS_sqlite.json (from load_sql.py),
    queries/sql/*.sql, data/tables/history_*.parquet (for the pandas checks and the
    aliases), results/mongo_q2_top_contested_pages.csv, results/mongo_compare_mutual_reverts.csv,
    results/cypher_compare_top_contested.csv and results/cypher_q1_mutual_reverts.csv.

Outputs
    results/sql_compare_top_contested.csv and .md, results/sql_compare_mutual_reverts.csv
    and .md, and results/_SUCCESS_sql_queries.json (rows, timings, checks). The
    _SUCCESS file is written only when every check passes (exit code 0).

Run (from the repo root; about 10 seconds)
    .venv/bin/python ec-hw2/queries/run_sql.py
    .venv/bin/python ec-hw2/queries/run_sql.py --runs 1      (quick, no warm-up)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

SQL_DIR = Path(__file__).resolve().parent / "sql"
QUERY_FILES = ["compare_top_contested", "compare_mutual_reverts"]
# The same names as the Cypher parameters ($top_n, ...), with the values from config.py.
PARAMS = {"top_n": config.TOP_N,
          "contested_min_edits": config.CONTESTED_MIN_EDITS,
          "contested_min_editors": config.CONTESTED_MIN_EDITORS,
          "contested_min_actions": config.CONTESTED_MIN_ACTIONS,
          "contested_min_score": config.CONTESTED_MIN_SCORE}
DEFAULT_RUNS = 7
MD_ROWS = 30
SQLITE_SUCCESS = config.SQLITE_PATH.parent / "_SUCCESS_sqlite.json"
KEY_RE = re.compile(r"^(u:\d+|t:~)")          # an editor key must never be in a result file
PARAMS_BLOCK_RE = re.compile(r"\bparams\s+AS\s*\(\s*SELECT\b(.*?)\)", re.IGNORECASE | re.DOTALL)
PARAM_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s+AS\s+(\w+)", re.IGNORECASE)
OTHER_FILES = {
    "compare_top_contested": {"Mongo Q2": "mongo_q2_top_contested_pages.csv",
                              "Cypher": "cypher_compare_top_contested.csv"},
    "compare_mutual_reverts": {"Mongo": "mongo_compare_mutual_reverts.csv",
                               "Cypher Q1": "cypher_q1_mutual_reverts.csv"},
}
TOP_COUNTS = ["edits", "revert_actions", "reverted_editors"]
MUTUAL_COLUMNS = ["page_id", "editor_a", "editor_b", "a_reverted_b", "b_reverted_a"]


# --------------------------------------------------------------------------
# Query files
# --------------------------------------------------------------------------
def is_comment(line: str) -> bool:
    return line.strip().startswith("--")


def header_lines(text: str) -> list[str]:
    """The comment block at the top of a file, without the '--' marks."""
    out = []
    for line in text.splitlines():
        if not line.strip() or not is_comment(line):
            break
        body = line.strip()[2:]
        out.append(body[1:] if body.startswith(" ") else body)   # keep the indentation after "-- "
    return out


def file_params(text: str) -> dict:
    """The numbers in the 'WITH params AS (SELECT 20 AS top_n, ...)' block, as a dict."""
    m = PARAMS_BLOCK_RE.search(text)
    if not m:
        return {}
    out = {}
    for value, name in PARAM_RE.findall(m.group(1)):
        out[name] = float(value) if "." in value else int(value)
    return out


def check_params(name: str, params: dict) -> None:
    """Stop if a params block has a number that is not the config.py value."""
    for k, v in params.items():
        if k not in PARAMS:
            raise SystemExit(f"{name}.sql: unknown parameter {k!r} in the params block.")
        if v != PARAMS[k]:
            raise SystemExit(f"{name}.sql: params says {k} = {v}, config.py says {PARAMS[k]}. "
                             "Update the params block in the .sql file.")


def read_query(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    params = file_params(text)
    check_params(path.stem, params)
    return {"name": path.stem, "path": path, "text": text, "header": header_lines(text),
            "params": params}


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------
def connect_ro(path: Path = config.SQLITE_PATH) -> sqlite3.Connection:
    """Open the SQLite file read-only (a query can never change it)."""
    if not path.exists():
        raise SystemExit(f"STOP: {path} is missing. Run: .venv/bin/python ec-hw2/load_sql.py")
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def run_once(con: sqlite3.Connection, sql: str) -> tuple[list[str], list[tuple], float]:
    """Run the SQL text and fetch every row. Returns columns, rows and milliseconds."""
    t = time.perf_counter()
    cur = con.execute(sql)
    rows = cur.fetchall()
    ms = (time.perf_counter() - t) * 1000
    return [d[0] for d in cur.description], rows, ms


def timed(con: sqlite3.Connection, sql: str, runs: int) -> tuple[pd.DataFrame, dict]:
    """Median of `runs` warm runs after 1 warm-up (runs = 1: one run, no warm-up)."""
    if runs > 1:
        run_once(con, sql)
    times, cols, rows = [], [], []
    for _ in range(runs):
        cols, rows, ms = run_once(con, sql)
        times.append(ms)
    timing = {"median_ms": round(statistics.median(times), 1), "min_ms": round(min(times), 1),
              "max_ms": round(max(times), 1), "runs": runs}
    return pd.DataFrame(rows, columns=cols), timing


def tidy_top(df: pd.DataFrame) -> pd.DataFrame:
    """Add rank in the row order (as run_mongo.py does for Mongo Q2), and show 'contested'
    as True/False like the other files (SQLite gives true/false as 1/0)."""
    out = df.copy()
    out["contested"] = out["contested"].astype(bool)
    if "rank" not in out.columns:
        out.insert(0, "rank", range(1, len(out) + 1))
    return out


def page_titles(con: sqlite3.Connection, page_ids) -> dict:
    """page_id -> the title of its newest history revision (the rule of Mongo Q2)."""
    ids = sorted({int(p) for p in page_ids})
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = con.execute(f"SELECT page_id, page_title FROM revisions WHERE page_id IN ({marks}) "
                       "AND page_title IS NOT NULL ORDER BY page_id, ts, rev_id", ids).fetchall()
    return dict(rows)   # the last (newest) title of each page wins


def pseudonymize_pairs(df: pd.DataFrame, titles: dict) -> pd.DataFrame:
    """Keys a, b -> editor_a, editor_b (aliases for humans, names for bots), as Mongo does."""
    from queries import run_mongo   # imported here: it is slow, and the tests do not need it
    return run_mongo.pseudonymize_pairs(df, titles)


def check_privacy(df: pd.DataFrame, where: str) -> None:
    for col in df.columns:
        for v in df[col]:
            if isinstance(v, str) and KEY_RE.match(v):
                raise SystemExit(f"{where}: column {col} shows an editor key. Stop.")


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
def write_safely(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def md_text(q: dict, stem: str, df: pd.DataFrame, timing: dict) -> str:
    header = q["header"]
    title = header[0] if header else stem
    notes = [line for line in header[1:] if not line.startswith("DB Browser")
             and not line.startswith('"Execute SQL"')]
    lines = [f"# {title}", "", "```text", "\n".join(notes), "```", ""]
    lines.append(f"Rows: {len(df):,}. " + (
        f"Median time: {timing['median_ms']:,.1f} ms ({timing['runs']} warm runs after 1 warm-up)."
        if timing["runs"] > 1 else f"Time: {timing['median_ms']:,.1f} ms (1 run)."))
    lines.append(f"Made by `ec-hw2/queries/run_sql.py` on "
                 f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC "
                 f"({config.DATA_VERSION}, SQLite {sqlite3.sqlite_version}). "
                 f"Query: `queries/sql/{q['path'].name}`. Full table: `{stem}.csv`.")
    lines += ["", tabulate(df.head(MD_ROWS), headers="keys", tablefmt="github", showindex=False,
                           floatfmt=".6g"), ""]
    if len(df) > MD_ROWS:
        lines.append(f"(first {MD_ROWS} of {len(df):,} rows)")
    return "\n".join(lines) + "\n"


def save(q: dict, df: pd.DataFrame, timing: dict) -> dict:
    stem = f"sql_{q['name']}"
    check_privacy(df, stem)
    write_safely(df.to_csv(index=False), config.RESULTS_DIR / f"{stem}.csv")
    write_safely(md_text(q, stem, df, timing), config.RESULTS_DIR / f"{stem}.md")
    return {"query": q["name"], "file": f"{stem}.csv", "result_rows": len(df), **timing}


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def top_key(df: pd.DataFrame) -> list[tuple]:
    """(page_id, score rounded to 6 digits): what the engines are compared on."""
    return [(int(p), round(float(s), config.SCORE_ROUND)) for p, s in zip(df["page_id"], df["score"])]


def top_counts(df: pd.DataFrame) -> list[tuple]:
    return [tuple(int(x) for x in row) for row in df[["page_id"] + TOP_COUNTS].values.tolist()]


def first_difference(a: list, b: list) -> int | None:
    """The first row (0-based) where two ordered lists differ, or None if they are equal."""
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def check_top(sql_df: pd.DataFrame) -> list[dict]:
    from queries import run_mongo
    checks = []
    pdf = run_mongo.pandas_q2()
    checks.append({"name": "SQL top contested = pandas (page_id, score to 6; counts)",
                   "ok": top_key(sql_df) == top_key(pdf) and top_counts(sql_df) == top_counts(pdf)})
    for who, fname in OTHER_FILES["compare_top_contested"].items():
        path = config.RESULTS_DIR / fname
        if not path.exists():
            print(f"  (no {fname}: skipped the check against {who})")
            continue
        other = pd.read_csv(path)
        same = top_key(sql_df) == top_key(other)
        same_counts = top_counts(sql_df) == top_counts(other)
        checks.append({"name": f"SQL top contested = {who} ({fname})", "ok": same and same_counts,
                       "same_page_and_score": same, "same_counts": same_counts})
    return checks


def check_mutual(keys_df: pd.DataFrame, public_df: pd.DataFrame) -> list[dict]:
    from queries import run_mongo
    checks = []
    cols = ["page_id", "a", "b", "a_reverted_b", "b_reverted_a"]
    pdf = run_mongo.pandas_mutual()
    a = [tuple(r) for r in keys_df[cols].itertuples(index=False)]
    b = [tuple(r) for r in pdf[cols].itertuples(index=False)]
    checks.append({"name": "SQL mutual reverts = pandas (full ordered list of keys)", "ok": a == b,
                   "rows": len(a)})
    mine = [tuple(r) for r in public_df[MUTUAL_COLUMNS].astype(str).values.tolist()]
    for who, fname in OTHER_FILES["compare_mutual_reverts"].items():
        path = config.RESULTS_DIR / fname
        if not path.exists():
            print(f"  (no {fname}: skipped the check against {who})")
            continue
        other = pd.read_csv(path)
        theirs = [tuple(r) for r in other[MUTUAL_COLUMNS].astype(str).values.tolist()]
        diff = first_difference(mine, theirs)
        checks.append({"name": f"SQL mutual reverts = {who} ({fname}, full ordered list)",
                       "ok": diff is None, "rows": len(mine), "first_difference_row": diff})
    return checks


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run the SQL comparison queries on SQLite.")
    p.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                   help="timed warm runs per query (default 7; 1 = no warm-up)")
    args = p.parse_args(argv)
    t0 = time.time()
    config.ensure_dirs()
    if not SQLITE_SUCCESS.exists():
        raise SystemExit(f"STOP: {SQLITE_SUCCESS.name} is missing. Run: .venv/bin/python ec-hw2/load_sql.py")
    queries = {n: read_query(SQL_DIR / f"{n}.sql") for n in QUERY_FILES}

    con = connect_ro()
    summary, checks = [], []
    try:
        q = queries["compare_top_contested"]
        df, timing = timed(con, q["text"], args.runs)
        df = tidy_top(df)
        summary.append(save(q, df, timing))
        print(f"{q['name']:24s} {len(df):>5,} rows  median {timing['median_ms']:8.1f} ms ({timing['runs']} runs)")
        checks += check_top(df)

        q = queries["compare_mutual_reverts"]
        keys_df, timing = timed(con, q["text"], args.runs)
        public = pseudonymize_pairs(keys_df, page_titles(con, keys_df["page_id"]))
        summary.append(save(q, public, timing))
        print(f"{q['name']:24s} {len(public):>5,} rows  median {timing['median_ms']:8.1f} ms ({timing['runs']} runs)")
        checks += check_mutual(keys_df, public)
    finally:
        con.close()

    print("=== checks")
    for c in checks:
        print(f"  {c['name']}: {'OK' if c['ok'] else 'DIFFERENT'}")
    ok = all(c["ok"] for c in checks)
    if not ok:
        print("Some checks are DIFFERENT: _SUCCESS_sql_queries.json was not written.")
        return 1
    success = {"step": "sql_queries", "data_version": config.DATA_VERSION,
               "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "sqlite_version": sqlite3.sqlite_version, "runs": args.runs,
               "rows": {r["file"]: r["result_rows"] for r in summary},
               "median_ms": {r["file"]: r["median_ms"] for r in summary},
               "results": summary, "checks": checks,
               "seconds": round(time.time() - t0, 1)}
    write_safely(json.dumps(success, indent=2) + "\n", config.RESULTS_DIR / "_SUCCESS_sql_queries.json")
    print(f"wrote results/sql_*.csv, .md and _SUCCESS_sql_queries.json in {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
