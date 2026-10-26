"""Run every query set: MongoDB, then Cypher, then SQL.

Purpose
    One command for all the query outputs in ec-hw2/results/. It runs
    queries/run_mongo.py first. Then it runs queries/run_cypher.py and
    queries/run_sql.py, but only if those files exist (other parts write them).
    Each script runs as its own process, so one failure does not hide the others.
    At the end it prints one line per script and exits with 1 if any script failed.

Inputs
    The loaded databases (MongoDB, Neo4j, SQLite) and the query files in queries/.

Outputs
    Whatever each script writes (results/mongo_*, results/cypher_*, results/sql_*).

Run (from the repo root)
    .venv/bin/python ec-hw2/queries/run_all.py
    .venv/bin/python ec-hw2/queries/run_all.py --runs 1      (quick: passed on to run_mongo.py)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config  # noqa: E402

SCRIPTS = ["run_mongo.py", "run_cypher.py", "run_sql.py"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run the Mongo, Cypher and SQL queries.")
    p.add_argument("--runs", type=int, default=None,
                   help="timed warm runs for run_mongo.py (default: its own default, 7)")
    args = p.parse_args(argv)
    status = []
    for name in SCRIPTS:
        path = HERE / name
        if not path.exists():
            status.append((name, "not there yet (skipped)", 0.0))
            continue
        cmd = [sys.executable, str(path)]
        if name == "run_mongo.py" and args.runs is not None:
            cmd += ["--runs", str(args.runs)]
        print(f"=== {name}", flush=True)
        t = time.time()
        rc = subprocess.run(cmd, cwd=config.REPO_ROOT).returncode
        status.append((name, "OK" if rc == 0 else f"FAILED (exit {rc})", time.time() - t))
    print("=== summary")
    for name, st, secs in status:
        print(f"  {name:16s} {st:26s} {secs:7.1f} s")
    return 1 if any(st.startswith("FAILED") for _, st, _ in status) else 0


if __name__ == "__main__":
    sys.exit(main())
