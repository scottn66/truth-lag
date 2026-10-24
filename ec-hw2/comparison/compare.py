"""Compare MongoDB, Neo4j and SQLite on the same two questions (spec section 5).

Purpose
    The two questions are "top contested pages" and "mutual reverts". For each
    question and each engine, this script does the following:
    1. It reads the query text ONLY from these files (no query is typed here):
       - MongoDB: queries/mongo/q2_top_contested_pages.json, queries/mongo/compare_mutual_reverts.json
       - Neo4j:   queries/cypher/compare_top_contested.cypher, queries/cypher/q1_mutual_reverts.cypher
                  (the statement marked "// result: main")
       - SQLite:  queries/sql/compare_top_contested.sql, queries/sql/compare_mutual_reverts.sql
       The parameters (top_n, thresholds) in the Cypher and SQL files must equal config.py.
       The 3 top-contested queries do the same steps: group the revert links per page,
       keep the pages with 2 or more reverted editors, and only then count the human
       edits of those pages.
    2. It checks that the 3 outputs are identical: the full ordered list, with scores
       rounded to config.SCORE_ROUND (6) digits.
       - top contested pages: (page_id, score), and also edits, revert_actions,
         reverted_editors and contested. The 3 queries must also return the same
         columns: no query computes a rank (run_mongo.py, run_cypher.py and run_sql.py
         add it in Python).
       - mutual reverts: (page_id, a, b, a_reverted_b, b_reverted_a).
       Neo4j shows editor aliases, so its rows are turned back into editor keys with
       the graph's own key/alias map (one alias per key is checked).
    3. It times each query: 1 warm-up run, then 3 rounds of 7 timed runs (21 runs). The
       engines take turns and the order rotates after every run, so a busy moment on
       the Mac hits every engine. The time runs in Python until every result row is in
       memory. We report the median, the min-max range of the 21 runs and the median of
       each round. We call engine A faster than engine B only when the two min-max
       ranges do not overlap. It records the machine (macOS, CPU, RAM, the Colima VM,
       the database versions and memory settings) and the load average at the start
       and at the end.
    4. An extra row, which is not one of the compared queries: mutual reverts in SQLite
       on PRE-AGGREGATED input (queries/sql/compare_mutual_reverts_preaggregated.sql).
       Cypher Q1 reads REVERTED relationships that export_graph.py grouped before the
       query runs, while MongoDB and SQLite group the raw revert links inside the timed
       query. The extra row builds the same grouping as a TEMP table in memory (not
       timed) and then times the self-join, so the reader sees the effect of the input.
    5. MongoDB input: revert_links and revisions also hold the live cohort, and both
       pipelines filter on cohort = "history". The script shows the query plan of the
       first $match (collection scan or index). When revert_links has the index
       {cohort: 1, page_id: 1}, it also times each pipeline with that index and with a
       forced collection scan (hint {$natural: 1}), to show whether the index helps.
    6. It measures query size: lines of code (non-blank lines that are not comments)
       and code characters (no spaces). For a JSON file it counts the "pipeline" array;
       for a .cypher file, the "main" statement only. Lines depend on the layout, so
       both numbers are shown side by side, and the CSV also counts the MongoDB lines
       that hold only brackets or commas.
    7. It reads the "modeling pain" scores (1-5, with a one-line reason) from
       comparison/pain.csv (question, engine, score, reason, scored_by) and shows who
       scored them. The scores in that file are a draft by Claude Code until the
       Comparison+viz owner re-scores them.
    The timings are labelled "draft" unless you pass --final. --final refuses to run
    when the 1-minute load average is above IDLE_LOAD (2.0): it prints the load and
    exits with code 2. Run --final only when nothing else runs on the Mac.

Inputs
    The local MongoDB (load_mongo.py), the local Neo4j (load_neo4j.py),
    data/tables/truthlag.sqlite (load_sql.py; opened read-only), the 6 query files
    above, queries/sql/compare_mutual_reverts_preaggregated.sql, comparison/pain.csv,
    and data/neo4j/import/_SUCCESS_export_graph.json (the time of the export step).

Outputs
    results/comparison.csv (the 6 compared rows), results/comparison_extra.csv (the extra
    row), results/comparison.md and results/_SUCCESS_comparison.json.
    Exit code 1 if an engine failed or the outputs are not identical; 2 if --final
    was refused.

Run (from the repo root; about 1 minute)
    .venv/bin/python ec-hw2/comparison/compare.py            (timings labelled "draft")
    .venv/bin/python ec-hw2/comparison/compare.py --final    (only when the Mac is idle)
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import platform
import re
import sqlite3
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from queries import run_cypher, run_mongo, run_sql  # noqa: E402

QUERIES_DIR = config.HW2_DIR / "queries"
ENGINES = ["MongoDB", "Neo4j", "SQLite"]
LANGUAGE = {"MongoDB": "aggregation pipeline (JSON)", "Neo4j": "Cypher", "SQLite": "SQL"}
TOP, MUTUAL = "top contested pages", "mutual reverts"
QUESTIONS = [TOP, MUTUAL]
QUERY_FILES = {
    TOP: {"MongoDB": QUERIES_DIR / "mongo" / "q2_top_contested_pages.json",
          "Neo4j": QUERIES_DIR / "cypher" / "compare_top_contested.cypher",
          "SQLite": QUERIES_DIR / "sql" / "compare_top_contested.sql"},
    MUTUAL: {"MongoDB": QUERIES_DIR / "mongo" / "compare_mutual_reverts.json",
             "Neo4j": QUERIES_DIR / "cypher" / "q1_mutual_reverts.cypher",
             "SQLite": QUERIES_DIR / "sql" / "compare_mutual_reverts.sql"},
}
EXTRA_NAME = "SQLite, pre-aggregated input"
EXTRA_FILE = QUERIES_DIR / "sql" / "compare_mutual_reverts_preaggregated.sql"
PAIN_FILE = config.HW2_DIR / "comparison" / "pain.csv"
PAIN_COLUMNS = ["question", "engine", "score", "reason", "scored_by"]
EXPORT_SUCCESS = config.NEO4J_IMPORT_DIR / "_SUCCESS_export_graph.json"
DEFAULT_RUNS = 7
DEFAULT_ROUNDS = 3
OUT_CSV = config.RESULTS_DIR / "comparison.csv"
OUT_EXTRA_CSV = config.RESULTS_DIR / "comparison_extra.csv"
OUT_MD = config.RESULTS_DIR / "comparison.md"
OUT_SUCCESS = config.RESULTS_DIR / "_SUCCESS_comparison.json"
CONTAINERS = {"MongoDB": "truthlag-mongo-1", "Neo4j": "truthlag-neo4j-1"}   # docker-compose.yml, project "truthlag"
IDLE_LOAD = 2.0     # --final refuses to run when the 1-minute load average is above this
COHORT_PAGE_INDEX = [("cohort", 1), ("page_id", 1)]   # the revert_links index that load_mongo.py adds
INDEX_CHECK_RUNS = 7


# --------------------------------------------------------------------------
# Query files and query size
# --------------------------------------------------------------------------
def code_lines(text: str, comment_prefix: str | None) -> list[str]:
    """Non-blank lines that are not comment lines."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or (comment_prefix and s.startswith(comment_prefix)):
            continue
        out.append(line)
    return out


def code_chars(lines: list[str]) -> int:
    """Characters of code without spaces, tabs or line ends (less sensitive to layout)."""
    return sum(len(re.sub(r"\s", "", line)) for line in lines)


def bracket_only_lines(lines: list[str]) -> int:
    """Lines that hold only brackets and commas, such as '},' (they come from the layout)."""
    return sum(1 for line in lines if re.fullmatch(r"[\[\]{}(),;]+", line.strip()))


def json_array_text(text: str, key: str) -> str:
    """The text of the JSON array under `key`, from the key to its closing ']'."""
    m = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
    if not m:
        raise ValueError(f'no "{key}" array in the JSON text')
    depth, in_str, esc = 0, False, False
    for i in range(m.end() - 1, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                start = text.rfind("\n", 0, m.start()) + 1
                return text[start:i + 1]
    raise ValueError(f'the "{key}" array is not closed')


def count_key(obj, key: str) -> int:
    """How many times a key (such as '$lookup') appears anywhere in a pipeline."""
    if isinstance(obj, dict):
        return sum((k == key) + count_key(v, key) for k, v in obj.items())
    if isinstance(obj, list):
        return sum(count_key(v, key) for v in obj)
    return 0


def split_sql(text: str) -> list[str]:
    """The statements of a .sql file: a ';' at the end of a line ends a statement.
    Comment lines and blank lines are left out."""
    out, cur = [], []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        cur.append(line)
        if s.endswith(";"):
            out.append("\n".join(cur).rstrip().rstrip(";").rstrip())
            cur = []
    if cur:
        out.append("\n".join(cur).strip())
    return out


def load_mongo_query(path: Path) -> dict:
    spec = run_mongo.load_query(path)         # MongoDB Extended JSON, as run_mongo.py runs it
    text = path.read_text(encoding="utf-8")
    code = code_lines(json_array_text(text, "pipeline"), None)
    return {"engine": "MongoDB", "path": path, "collection": spec["collection"],
            "pipeline": spec["pipeline"], "code": code,
            "stats": {"stages": len(spec["pipeline"]), "lookups": count_key(spec["pipeline"], "$lookup")}}


def load_cypher_query(path: Path) -> dict:
    q = run_cypher.parse_file(path)
    if q["params"] != run_cypher.PARAMS:
        raise SystemExit(f"{path.name}: the ':params' line does not match config.py "
                         f"({q['params']} vs {run_cypher.PARAMS}).")
    main = [s for s in q["statements"] if s["label"] == "main"]
    if len(main) != 1 or not main[0]["read_only"]:
        raise SystemExit(f"{path.name}: needs exactly one read-only '// result: main' statement.")
    code = main[0]["code"]
    return {"engine": "Neo4j", "path": path, "cypher": code, "code": code_lines(code, "//"),
            "stats": {"matches": len(re.findall(r"\bMATCH\b", code))}}


def load_sql_query(path: Path) -> dict:
    q = run_sql.read_query(path)              # stops if the params block differs from config.py
    return {"engine": "SQLite", "path": path, "sql": q["text"], "code": code_lines(q["text"], "--"),
            "stats": {"joins": len(re.findall(r"\bJOIN\b", q["text"], re.IGNORECASE))}}


LOADERS = {"MongoDB": load_mongo_query, "Neo4j": load_cypher_query, "SQLite": load_sql_query}


def load_queries() -> dict:
    return {(qn, e): LOADERS[e](QUERY_FILES[qn][e]) for qn in QUESTIONS for e in ENGINES}


def load_extra_query(path: Path = EXTRA_FILE) -> dict:
    """The pre-aggregated SQLite variant: setup statements (not timed) + the last SELECT (timed)."""
    statements = split_sql(path.read_text(encoding="utf-8"))
    if len(statements) < 2 or not statements[-1].lstrip().upper().startswith("SELECT"):
        raise SystemExit(f"{path.name}: needs setup statements and then one SELECT at the end.")
    setup_code = [line for s in statements[:-1] for line in code_lines(s, "--")]
    return {"engine": "SQLite", "path": path, "setup": statements[:-1], "sql": statements[-1],
            "code": code_lines(statements[-1], "--"), "setup_lines": len(setup_code), "stats": {}}


def load_pain(path: Path = PAIN_FILE) -> dict:
    """(question, engine) -> score, reason and scored_by, from comparison/pain.csv."""
    if not path.exists():
        raise SystemExit(f"STOP: {path} is missing (columns {', '.join(PAIN_COLUMNS)}).")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(df.columns) != PAIN_COLUMNS:
        raise SystemExit(f"STOP: {path.name} must have the columns {PAIN_COLUMNS}, not {list(df.columns)}.")
    want = {(q, e) for q in QUESTIONS for e in ENGINES}
    out = {}
    for r in df.itertuples(index=False):
        key = (r.question.strip(), r.engine.strip())
        if key not in want or key in out:
            raise SystemExit(f"STOP: {path.name}: unknown or repeated row {key}.")
        try:
            score = int(r.score)
        except ValueError:
            raise SystemExit(f"STOP: {path.name}: score {r.score!r} for {key} is not a whole number.")
        if not 1 <= score <= 5 or not r.reason.strip() or not r.scored_by.strip():
            raise SystemExit(f"STOP: {path.name}: {key} needs a score 1-5, a reason and scored_by.")
        out[key] = {"score": score, "reason": r.reason.strip(), "scored_by": r.scored_by.strip()}
    if set(out) != want:
        raise SystemExit(f"STOP: {path.name} has no row for {sorted(want - set(out))}.")
    return out


# --------------------------------------------------------------------------
# Engines
# --------------------------------------------------------------------------
class Engines:
    """Open connections to the 3 engines. A missing engine is recorded, not fatal."""

    def __init__(self):
        self.errors: dict[str, str] = {}
        self.mongo_client = self.db = self.driver = self.session = self.sqlite = None
        self.sqlite_extra = None
        try:
            from load_mongo import connect
            self.mongo_client = connect(config.MONGO_URI)
            self.db = self.mongo_client[config.MONGO_DB]
        except Exception as exc:   # report it and go on with the other engines
            self.errors["MongoDB"] = f"{type(exc).__name__}: {exc}"
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(config.NEO4J_URI,
                                               auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
            self.driver.verify_connectivity()
            self.session = self.driver.session()
        except Exception as exc:
            self.errors["Neo4j"] = f"{type(exc).__name__}: {exc}"
        try:
            self.sqlite = run_sql.connect_ro()
        except (Exception, SystemExit) as exc:
            self.errors["SQLite"] = f"{type(exc).__name__}: {exc}"

    def close(self) -> None:
        for closer in (self.session, self.driver, self.mongo_client, self.sqlite, self.sqlite_extra):
            try:
                if closer is not None:
                    closer.close()
            except Exception:
                pass

    def runner(self, q: dict):
        """A function that runs the query once and returns its rows as dicts."""
        e = q["engine"]
        if e == "MongoDB":
            coll, pipeline = self.db[q["collection"]], q["pipeline"]
            return lambda: list(coll.aggregate(pipeline))
        if e == "Neo4j":
            session, code = self.session, q["cypher"]

            def run_cypher_once():
                result = session.run(code, run_cypher.PARAMS)
                rows = [r.data() for r in result]
                result.consume()
                return rows
            return run_cypher_once
        return sql_runner(self.sqlite, q["sql"])

    def extra_runner(self, q: dict) -> tuple:
        """Build the TEMP table of the pre-aggregated variant (timed once, for the notes,
        but not part of the query time) on its own read-only connection, so its settings
        never touch the main SQLite timing. Returns (runner, setup milliseconds)."""
        self.sqlite_extra = run_sql.connect_ro()
        t = time.perf_counter()
        for st in q["setup"]:
            self.sqlite_extra.execute(st)
        setup_ms = (time.perf_counter() - t) * 1000
        return sql_runner(self.sqlite_extra, q["sql"]), setup_ms

    def alias_to_key(self) -> dict:
        """The graph's own alias -> key map (helper query, not timed)."""
        rows = self.session.run("MATCH (e:Editor) RETURN e.key AS key, e.alias AS alias").data()
        out = {r["alias"]: r["key"] for r in rows}
        if len(out) != len(rows) or len({r["key"] for r in rows}) != len(rows):
            raise SystemExit("Neo4j: two editors share an alias or a key; cannot map aliases back to keys.")
        return out


def sql_runner(con: sqlite3.Connection, sql: str):
    def run_sql_once():
        cur = con.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    return run_sql_once


def measure(runners: dict, runs: int, rounds: int = 1) -> dict:
    """1 warm-up run each (when runs > 1), then `rounds` rounds of `runs` timed runs.

    The engines take turns, and the order rotates after every run, so a busy moment on
    the Mac hits every engine. Each engine gets its times, the median of each round,
    its last rows and its error (if it failed)."""
    names = list(runners)
    out = {n: {"times": [], "round_medians": [], "rows": None, "error": None} for n in names}
    if runs > 1:
        for n in names:
            try:
                runners[n]()
            except Exception as exc:
                out[n]["error"] = f"{type(exc).__name__}: {exc}"
    turn = 0
    for _ in range(rounds):
        this_round = {n: [] for n in names}
        for _ in range(runs):
            order = names[turn % len(names):] + names[:turn % len(names)]
            turn += 1
            for n in order:
                if out[n]["error"]:
                    continue
                try:
                    t = time.perf_counter()
                    rows = runners[n]()
                    ms = (time.perf_counter() - t) * 1000
                    out[n]["times"].append(ms)
                    this_round[n].append(ms)
                    out[n]["rows"] = rows
                except Exception as exc:
                    out[n]["error"] = f"{type(exc).__name__}: {exc}"
        for n in names:
            if this_round[n] and not out[n]["error"]:
                out[n]["round_medians"].append(statistics.median(this_round[n]))
    return out


def timing_stats(r: dict) -> dict:
    """Median, min and max of the timed runs (empty when the engine failed)."""
    t = r["times"]
    if not t or r["error"]:
        return {"median_ms": None, "min_ms": None, "max_ms": None, "runs": 0, "round_medians_ms": ""}
    return {"median_ms": round(statistics.median(t), 1), "min_ms": round(min(t), 1),
            "max_ms": round(max(t), 1), "runs": len(t),
            "round_medians_ms": " | ".join(f"{m:.1f}" for m in r["round_medians"])}


def faster_than(stats: dict[str, dict]) -> dict[str, list[str]]:
    """For each engine: the engines it is faster than. A is faster than B only when A's
    slowest run is faster than B's fastest run (the min-max ranges do not overlap)."""
    out = {}
    for e, s in stats.items():
        out[e] = [o for o, t in stats.items()
                  if o != e and s["max_ms"] is not None and t["min_ms"] is not None
                  and s["max_ms"] < t["min_ms"]]
    return out


def speed_sentences(stats: dict[str, dict]) -> list[str]:
    """One plain sentence per pair of engines."""
    out = []
    for a, b in itertools.combinations(list(stats), 2):
        sa, sb = stats[a], stats[b]
        if sa["median_ms"] is None or sb["median_ms"] is None:
            continue
        ra = f"{sa['min_ms']:,.1f}-{sa['max_ms']:,.1f} ms"
        rb = f"{sb['min_ms']:,.1f}-{sb['max_ms']:,.1f} ms"
        if sa["max_ms"] < sb["min_ms"]:
            out.append(f"{a} is faster than {b} ({ra} vs {rb}; the ranges do not overlap).")
        elif sb["max_ms"] < sa["min_ms"]:
            out.append(f"{b} is faster than {a} ({rb} vs {ra}; the ranges do not overlap).")
        else:
            out.append(f"{a} and {b}: the ranges overlap ({ra} vs {rb}), so we do not call either one faster.")
    return out


# --------------------------------------------------------------------------
# Equality
# --------------------------------------------------------------------------
def r6(x) -> float:
    return round(float(x), config.SCORE_ROUND)


def norm_top(rows: list[dict]) -> dict:
    """The compared list (page_id, score) and the full list with the counts."""
    key = [(int(r["page_id"]), r6(r["score"])) for r in rows]
    full = [(int(r["page_id"]), int(r["edits"]), int(r["revert_actions"]),
             int(r["reverted_editors"]), r6(r["score"]), bool(r["contested"])) for r in rows]
    return {"key": key, "full": full}


def norm_mutual(rows: list[dict], alias_to_key: dict | None = None) -> dict:
    """(page_id, a, b, a_reverted_b, b_reverted_a) with editor keys."""
    out = []
    for r in rows:
        if "a" in r:
            a, b = r["a"], r["b"]
        else:                                   # Neo4j shows aliases
            a, b = alias_to_key[r["editor_a"]], alias_to_key[r["editor_b"]]
        out.append((int(r["page_id"]), a, b, int(r["a_reverted_b"]), int(r["b_reverted_a"])))
    return {"key": out, "full": out}


def first_difference(a: list, b: list) -> int | None:
    return run_sql.first_difference(a, b)


def same_result(question: str, norm: dict) -> dict:
    """For each engine: 'yes', or 'no' with where it differs from the others."""
    out = {}
    for e in ENGINES:
        if e not in norm:
            out[e] = {"same": None, "text": "not checked (engine failed)", "difference": ""}
            continue
        diffs, count_diffs = [], []
        for o in ENGINES:
            if o == e or o not in norm:
                continue
            i = first_difference(norm[e]["key"], norm[o]["key"])
            if i is not None:
                n_e, n_o = len(norm[e]["key"]), len(norm[o]["key"])
                where = (f"row {i + 1}: page_id {norm[e]['key'][i][0] if i < n_e else '-'} "
                         f"vs {norm[o]['key'][i][0] if i < n_o else '-'}")
                diffs.append(f"differs from {o} ({n_e} vs {n_o} rows; first at {where})")
                continue
            j = first_difference(norm[e]["full"], norm[o]["full"])
            if j is not None:
                count_diffs.append(f"counts differ from {o} at row {j + 1} "
                                   f"(page_id {norm[e]['full'][j][0]})")
        missing = [o for o in ENGINES if o != e and o not in norm]
        if diffs:
            out[e] = {"same": False, "text": "no", "difference": "; ".join(diffs)}
        elif count_diffs:
            out[e] = {"same": True, "text": "yes (page_id + score); counts differ",
                      "difference": "; ".join(count_diffs)}
        else:
            what = "yes" if not missing else f"yes (vs {', '.join(o for o in ENGINES if o != e and o in norm)} only)"
            out[e] = {"same": True, "text": what, "difference": ""}
    return out


def column_sets(outs: dict, question: str) -> dict[str, list[str]]:
    """The output columns of each engine for one question (sorted)."""
    return {e: sorted(outs[(question, e)][0]) for e in ENGINES if outs.get((question, e))}


# --------------------------------------------------------------------------
# Machine and context numbers
# --------------------------------------------------------------------------
def run_cmd(args: list[str]) -> str | None:
    try:
        r = subprocess.run(args, capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except Exception:
        return None


def sysctl(name: str) -> str | None:
    return run_cmd(["sysctl", "-n", name])


def gib(n) -> str:
    return f"{int(n) / 2**30:.1f} GiB"


def machine_info(eng: Engines) -> dict:
    """Facts about the computer and the databases (never a password or a URI)."""
    m = {}
    m["macOS"] = f"{platform.mac_ver()[0] or platform.platform()} ({platform.machine()})"
    cpu = sysctl("machdep.cpu.brand_string")
    p_cores, e_cores = sysctl("hw.perflevel0.physicalcpu"), sysctl("hw.perflevel1.physicalcpu")
    cores = sysctl("hw.physicalcpu") or str(os.cpu_count())
    m["CPU (host)"] = f"{cpu}, {cores} cores" + (f" ({p_cores} performance + {e_cores} efficiency)"
                                                 if p_cores and e_cores else "")
    mem = sysctl("hw.memsize")
    m["RAM (host)"] = gib(mem) if mem else "unknown"
    info = run_cmd(["docker", "info", "--format", "{{.NCPU}}|{{.MemTotal}}|{{.OperatingSystem}}"])
    if info:
        ncpu, memtotal, osname = info.split("|", 2)
        m["Colima VM (MongoDB + Neo4j)"] = f"{ncpu} CPUs, {gib(memtotal)} RAM, {osname}"
    else:
        m["Colima VM (MongoDB + Neo4j)"] = "unknown (docker info failed); planned: 4 CPUs, 6 GB"
    for e, name in CONTAINERS.items():
        lim = run_cmd(["docker", "inspect", "--format", "{{.HostConfig.Memory}}", name])
        m[f"{e} container memory limit"] = gib(lim) if lim and lim != "0" else "unknown"
    if eng.mongo_client is not None:
        try:
            m["MongoDB version"] = eng.mongo_client.server_info()["version"]
            cache = eng.mongo_client.admin.command("serverStatus")["wiredTiger"]["cache"]
            m["MongoDB WiredTiger cache"] = gib(cache["maximum bytes configured"])
        except Exception as exc:
            m["MongoDB version"] = f"unknown ({type(exc).__name__})"
    if eng.session is not None:
        try:
            comp = eng.session.run("CALL dbms.components() YIELD name, versions, edition "
                                   "WHERE name = 'Neo4j Kernel' RETURN versions[0] AS v, edition AS ed").single()
            m["Neo4j version"] = f"{comp['v']} {comp['ed']}"
            sets = eng.session.run("SHOW SETTINGS YIELD name, value WHERE name IN "
                                   "['server.memory.heap.max_size', 'server.memory.pagecache.size'] "
                                   "RETURN name, value").data()
            vals = {s["name"]: s["value"] for s in sets}
            m["Neo4j memory"] = (f"heap {vals.get('server.memory.heap.max_size', '?')}, "
                                 f"page cache {vals.get('server.memory.pagecache.size', '?')}")
        except Exception as exc:
            m["Neo4j version"] = f"unknown ({type(exc).__name__})"
    m["SQLite version"] = f"{sqlite3.sqlite_version} (in the Python process on the host)"
    try:
        import neo4j
        import pymongo
        m["Python and drivers"] = (f"Python {platform.python_version()}, pymongo {pymongo.version}, "
                                   f"neo4j driver {neo4j.__version__}")
    except Exception:
        m["Python and drivers"] = f"Python {platform.python_version()}"
    return m


def load_text(load: tuple) -> str:
    return f"{load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"


def context_numbers(eng: Engines) -> dict:
    """Sizes of what each engine reads, and facts for the findings (helper queries, not timed)."""
    c = {}
    if eng.sqlite is not None:
        q = eng.sqlite.execute
        used = "cohort = 'history' AND within_followup = 1 AND by_other = 1"
        c["sqlite_revisions"] = q("SELECT COUNT(*) FROM revisions").fetchone()[0]
        c["sqlite_links"] = q("SELECT COUNT(*) FROM revert_links").fetchone()[0]
        c["sqlite_links_used"] = q(f"SELECT COUNT(*) FROM revert_links WHERE {used}").fetchone()[0]
        c["top_step1_pages"] = q(
            f"SELECT COUNT(*) FROM (SELECT page_id FROM revert_links WHERE {used} GROUP BY page_id "
            "HAVING COUNT(DISTINCT author_key) >= ?)", (config.CONTESTED_MIN_EDITORS,)).fetchone()[0]
        c["triples"], c["triples_a_lt_b"] = q(
            "SELECT COUNT(*), SUM(reverter_key < author_key) FROM (SELECT DISTINCT reverter_key, "
            f"author_key, page_id FROM revert_links WHERE {used} "
            "AND reverter_key IS NOT NULL AND author_key IS NOT NULL)").fetchone()
        c["keyless_revisions"] = q("SELECT COUNT(*) FROM revisions WHERE user_key IS NULL").fetchone()[0]
        c["keyless_pages"] = [r[0] for r in q("SELECT DISTINCT page_id FROM revisions "
                                              "WHERE user_key IS NULL ORDER BY page_id")]
        kinds = q("SELECT reverter_key, reverter_kind FROM revert_links WHERE reverter_key IS NOT NULL "
                  "UNION SELECT author_key, author_kind FROM revert_links WHERE author_key IS NOT NULL")
        c["kind_of"] = dict(kinds.fetchall())
        c["sqlite_mb"] = config.SQLITE_PATH.stat().st_size / 1e6
    if eng.db is not None:
        links, revs = eng.db[config.COL_REVERT_LINKS], eng.db[config.COL_REVISIONS]
        c["mongo_links"] = links.estimated_document_count()
        c["mongo_links_history"] = links.count_documents({"cohort": config.COHORT_HISTORY})
        c["mongo_revisions"] = revs.estimated_document_count()
        c["mongo_revisions_history"] = revs.count_documents({"cohort": config.COHORT_HISTORY})
    if eng.session is not None:
        s = eng.session
        c["neo4j_edited"] = s.run("MATCH ()-[r:EDITED]->() RETURN count(r) AS n").single()["n"]
        c["neo4j_reverted"] = s.run("MATCH ()-[r:REVERTED]->() RETURN count(r) AS n").single()["n"]
        c["neo4j_editors"] = s.run("MATCH (e:Editor) RETURN count(e) AS n").single()["n"]
        c["neo4j_pages"] = s.run("MATCH (p:Page) RETURN count(p) AS n").single()["n"]
    if EXPORT_SUCCESS.exists():
        try:
            secs = json.loads(EXPORT_SUCCESS.read_text(encoding="utf-8"))["stats"]["pipeline_seconds"]
            c["export_reverted_s"] = secs.get("reverted")
        except (KeyError, ValueError):
            pass
    return c


# --------------------------------------------------------------------------
# MongoDB: the cohort filter and the {cohort, page_id} index
# --------------------------------------------------------------------------
def first_scan(explain: dict) -> dict:
    """The access path of the pipeline's first stage: COLLSCAN, or IXSCAN with its index.

    It reads the winning plan of the $cursor stage (or of the whole query when MongoDB
    pushed every stage down) and skips the rejected plans."""
    root = explain["stages"][0].get("$cursor", explain) if explain.get("stages") else explain
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("stage") in ("COLLSCAN", "IXSCAN", "EXPRESS_IXSCAN"):
                found.append({"stage": o["stage"], "index": o.get("indexName")})
            for k, v in o.items():
                if k not in ("rejectedPlans", "executionStats", "allPlansExecution"):
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(root.get("queryPlanner", root))
    stats = root.get("executionStats") or explain.get("executionStats") or {}
    scan = found[0] if found else {"stage": "unknown", "index": None}
    return {**scan, "docs_examined": stats.get("totalDocsExamined")}


def has_cohort_page_index(coll) -> str | None:
    """The name of the {cohort: 1, page_id: 1} index on the collection, if there is one."""
    for name, info in coll.index_information().items():
        if [(k, int(v)) for k, v in info["key"]] == COHORT_PAGE_INDEX:
            return name
    return None


def mongo_index_check(eng: Engines, queries: dict, runs: int = INDEX_CHECK_RUNS) -> dict:
    """For both MongoDB comparison pipelines: the plan of the first $match, and, when the
    {cohort: 1, page_id: 1} index exists, the median time with it and with a forced
    collection scan (hint {$natural: 1}). Helper runs, not part of the comparison."""
    out = {"index": None, "pipelines": {}}
    if eng.db is None:
        return out
    coll = eng.db[config.COL_REVERT_LINKS]
    out["index"] = has_cohort_page_index(coll)
    for qn in QUESTIONS:
        q = queries[(qn, "MongoDB")]
        cmd = {"aggregate": q["collection"], "pipeline": q["pipeline"], "cursor": {}}
        info = first_scan(eng.db.command("explain", cmd, verbosity="executionStats"))
        if out["index"]:
            c = eng.db[q["collection"]]
            for label, hint in (("with_index_ms", None), ("collection_scan_ms", {"$natural": 1})):
                kw = {"hint": hint} if hint else {}
                list(c.aggregate(q["pipeline"], **kw))                 # warm-up
                times = []
                for _ in range(runs):
                    t = time.perf_counter()
                    list(c.aggregate(q["pipeline"], **kw))
                    times.append((time.perf_counter() - t) * 1000)
                info[label] = round(statistics.median(times), 1)
        out["pipelines"][qn] = info
    return out


# --------------------------------------------------------------------------
# Notes and findings
# --------------------------------------------------------------------------
def modeling_note(question: str, q: dict, ctx: dict) -> str:
    """One plain sentence per (question, engine), from the query text and the data."""
    st, e = q["stats"], q["engine"]
    n_pages = ctx.get("top_step1_pages")
    pages = f"the {n_pages:,} kept pages" if n_pages else "the kept pages"
    if question == TOP:
        if e == "MongoDB":
            return (f"{st['stages']} stages: group the links per page and keep pages with 2+ reverted "
                    f"editors; then a $lookup into revisions counts the human edits of {pages} only.")
        if e == "Neo4j":
            n = ctx.get("neo4j_edited")
            return ("Two MATCH steps: the first filters " + (f"all {n:,} " if n else "all ") +
                    "EDITED relationships on the revert flags (there is no separate revert-link "
                    f"table), the second counts the edits of {pages} only.")
        return (f"GROUP BY with HAVING, then one correlated COUNT per kept page ({pages}); "
                "the score is 1.0 * a / b to avoid whole-number division.")
    if e == "MongoDB":
        n = ctx.get("triples_a_lt_b")
        return ("The reverse direction needs a self-$lookup with let and $expr, run once per "
                f"a < b triple ({n:,} times)." if n else
                "The reverse direction needs a self-$lookup with let and $expr.")
    if e == "Neo4j":
        n = ctx.get("neo4j_reverted")
        return ("The pattern (a)-[:REVERTED]->(b)-[:REVERTED]->(a) is one line, but it needs page_id "
                f"on all {n:,} REVERTED relationships." if n else
                "The pattern is one line, but it needs page_id on the REVERTED relationships.")
    return "A CTE of (reverter, author, page) triples is joined to itself with the roles swapped."


def input_note(question: str, engine: str, ctx: dict) -> str:
    """What the timed query reads, so the reader knows what is (not) inside the time."""
    if engine == "MongoDB":
        live = ""
        if ctx.get("mongo_links") is not None:
            live = (f" ({ctx['mongo_links'] - ctx['mongo_links_history']:,} of the "
                    f"{ctx['mongo_links']:,} revert_links documents are live)")
        return ("The collections also hold the live cohort" + live + "; the pipeline filters "
                "cohort = 'history'. It groups the raw revert links inside the timed query.")
    if engine == "Neo4j":
        if question == MUTUAL:
            return ("Reads the REVERTED relationships that export_graph.py pre-aggregated (one per "
                    "reverter, reverted editor and page, with count); that grouping is NOT inside "
                    "the timed query.")
        return ("Reads the revert flags that export_graph.py copied onto the EDITED relationships; "
                "history cohort only.")
    return "History cohort only; it groups the raw revert links inside the timed query."


def runs_text(runs: int, rounds: int = 1) -> str:
    if runs <= 1:
        return f"{rounds} run{'s' if rounds > 1 else ''}, no warm-up"
    if rounds > 1:
        return f"1 warm-up, then {rounds} rounds of {runs} timed runs ({rounds * runs} runs per query)"
    return f"{runs} warm runs after 1 warm-up"


def fmt_ms(x) -> str:
    return "-" if x is None else f"{x:,.1f}"


def fmt_range(r: dict) -> str:
    return "-" if r.get("min_ms") is None else f"{r['min_ms']:,.1f}-{r['max_ms']:,.1f}"


def median_and_range(r: dict) -> str:
    return f"{fmt_ms(r['median_ms'])} ({fmt_range(r)})"


def findings(rows: list[dict], outs: dict, ctx: dict, label: str, runs: int, rounds: int,
             extra: dict | None = None, mongo_idx: dict | None = None) -> list[str]:
    """Facts with numbers only (no conclusions), for the Comparison+viz owner."""
    by = {(r["question"], r["engine"]): r for r in rows}
    f = []

    top = outs.get((TOP, "SQLite")) or outs.get((TOP, "MongoDB")) or outs.get((TOP, "Neo4j"))
    same_top = all(by[(TOP, e)]["same_result"].startswith("yes") for e in ENGINES)
    if top:
        r1 = top[0]
        f.append(f"Top contested pages: the outputs are {'identical' if same_top else 'NOT identical'} in "
                 f"MongoDB, Neo4j and SQLite ({len(top)} rows, in order, scores to {config.SCORE_ROUND} digits). "
                 f"Rank 1 is page {int(r1['page_id'])} ({r1['page_title']}): {int(r1['revert_actions'])} revert "
                 f"actions / {int(r1['edits'])} human edits = {r6(r1['score']):.6f}.")
        if ctx.get("top_step1_pages") is not None:
            f.append(f"Top contested pages, step 1 keeps {ctx['top_step1_pages']:,} pages with "
                     f"{config.CONTESTED_MIN_EDITORS}+ reverted editors; all 3 engines count the human "
                     f"edits for these pages only.")
        scores = [r6(r["score"]) for r in top]
        tied = [s for s in sorted(set(scores), reverse=True) if scores.count(s) > 1]
        n_tied = sum(scores.count(s) for s in tied)
        if tied:
            f.append(f"{n_tied} of the top {len(top)} pages share a score with another page "
                     f"(scores {', '.join(f'{s:.6f}' for s in tied)}). The tie order uses revert_actions, "
                     f"then edits, then page_id, in all 3 engines.")

    mut = outs.get((MUTUAL, "SQLite")) or outs.get((MUTUAL, "MongoDB"))
    same_mut = all(by[(MUTUAL, e)]["same_result"].startswith("yes") for e in ENGINES)
    if mut:
        pages = {int(r["page_id"]) for r in mut}
        editors = {r["a"] for r in mut} | {r["b"] for r in mut}
        kind = ctx.get("kind_of", {})
        bot_pairs = sum(1 for r in mut if kind.get(r["a"]) == "bot" or kind.get(r["b"]) == "bot")
        f.append(f"Mutual reverts: the outputs are {'identical' if same_mut else 'NOT identical'} in the "
                 f"3 engines: {len(mut):,} pairs on {len(pages):,} pages, with {len(editors):,} distinct "
                 f"editors; {bot_pairs:,} pairs include a bot.")
        if top:
            top_ids = [int(r["page_id"]) for r in top]
            hit = [p for p in top_ids if p in pages]
            n_pairs = sum(1 for r in mut if int(r["page_id"]) in set(top_ids))
            f.append(f"{len(hit)} of the top {len(top_ids)} contested pages have at least one mutual pair; "
                     f"together they hold {n_pairs:,} of the {len(mut):,} pairs.")

    def per_engine(question, fn):
        return ", ".join(f"{e} {fn(by[(question, e)])}" for e in ENGINES)

    def size(r):
        return f"{r['code_chars']:,} characters / {r['lines_of_code']} lines"
    mongo_brackets = by[(TOP, "MongoDB")]["bracket_only_lines"] + by[(MUTUAL, "MongoDB")]["bracket_only_lines"]
    mongo_lines = by[(TOP, "MongoDB")]["lines_of_code"] + by[(MUTUAL, "MongoDB")]["lines_of_code"]
    f.append(f"Query size (code characters without spaces / lines of code): top contested pages: "
             f"{per_engine(TOP, size)}; mutual reverts: {per_engine(MUTUAL, size)}. Line counts depend on "
             f"the layout: {mongo_brackets} of the {mongo_lines} MongoDB lines hold only brackets or commas.")
    f.append(f"Median time in ms with the min-max range ({label}, {runs_text(runs, rounds)}): top contested "
             f"pages: {per_engine(TOP, median_and_range)}; mutual reverts: "
             f"{per_engine(MUTUAL, median_and_range)}.")
    for qn in QUESTIONS:
        stats = {e: by[(qn, e)] for e in ENGINES}
        f.append(f"Speed, {qn}: " + " ".join(speed_sentences(stats)))
    if extra and extra.get("median_ms") is not None:
        raw, neo = by[(MUTUAL, "SQLite")], by[(MUTUAL, "Neo4j")]
        f.append(f"Mutual reverts on pre-aggregated input (extra row): SQLite takes {fmt_ms(extra['median_ms'])} ms "
                 f"({fmt_range(extra)}) when it reads triples grouped beforehand, against "
                 f"{fmt_ms(raw['median_ms'])} ms ({fmt_range(raw)}) on the raw revert links; Neo4j, which reads "
                 f"the REVERTED relationships grouped by export_graph.py, takes {fmt_ms(neo['median_ms'])} ms "
                 f"({fmt_range(neo)}). Building the TEMP table took {extra['setup_ms']:,.1f} ms (not timed).")
    if ctx.get("sqlite_links") is not None and ctx.get("neo4j_reverted") is not None:
        f.append(f"Input sizes: SQLite revert_links has {ctx['sqlite_links']:,} rows "
                 f"({ctx['sqlite_links_used']:,} pass within_followup and by_other), which make "
                 f"{ctx['triples']:,} (reverter, author, page) triples; {ctx['triples_a_lt_b']:,} of them "
                 f"have a < b, so the MongoDB self-$lookup runs {ctx['triples_a_lt_b']:,} times. MongoDB "
                 f"revert_links has {ctx.get('mongo_links', 0):,} documents ({ctx.get('mongo_links_history', 0):,} "
                 f"history). Neo4j has {ctx['neo4j_reverted']:,} REVERTED relationships and "
                 f"{ctx['neo4j_edited']:,} EDITED relationships.")
    if mongo_idx and mongo_idx.get("pipelines"):
        parts = []
        for qn, p in mongo_idx["pipelines"].items():
            scan = p["stage"] + (f" {p['index']}" if p.get("index") else "")
            s = f"{qn}: {scan}, {p['docs_examined']:,} documents examined" if p.get("docs_examined") is not None \
                else f"{qn}: {scan}"
            if p.get("with_index_ms") is not None:
                s += (f", median {p['with_index_ms']:,.1f} ms with the default plan (the index "
                      f"exists) vs {p['collection_scan_ms']:,.1f} ms with a forced collection scan")
            parts.append(s)
        f.append("MongoDB first $match (cohort = 'history'): " + "; ".join(parts) + "."
                 + ("" if mongo_idx.get("index") else
                    " revert_links has no {cohort: 1, page_id: 1} index yet."))
    if ctx.get("keyless_pages") is not None and top:
        kp = ctx["keyless_pages"]
        in_top = [p for p in kp if p in {int(r['page_id']) for r in top}]
        f.append(f"{ctx['keyless_revisions']} history revisions have no editor key (pages "
                 f"{', '.join(str(p) for p in kp)}). SQLite and MongoDB count them as human edits; Neo4j "
                 f"has no EDITED relationship for them. "
                 + (f"None of these pages is in the top {len(top)}." if not in_top else
                    f"{len(in_top)} of these pages are in the top {len(top)}: {', '.join(map(str, in_top))}."))
    return f


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
def write_safely(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def shown(path: Path) -> str:
    """A path for the log: relative to the repo root when it is inside it."""
    try:
        return str(path.relative_to(config.REPO_ROOT))
    except ValueError:
        return str(path)


def md_cell(s) -> str:
    return str(s).replace("|", "\\|")


def label_line(label: str, loads: tuple) -> str:
    """The timing label with the MEASURED load averages (never fixed words such as 'idle')."""
    start, end = load_text(loads[0]), load_text(loads[1])
    if label == "draft":
        return (f"**Timing label: draft.** Load average (1 / 5 / 15 min): {start} at the start and {end} at "
                f"the end. Other jobs may have been running. `--final` runs only when the 1-minute load "
                f"average is at most {IDLE_LOAD}. The equality checks and the query sizes do not depend "
                f"on the timing.")
    return (f"**Timing label: final.** Load average (1 / 5 / 15 min): {start} at the start and {end} at the "
            f"end. `--final` runs only when the 1-minute load average is at most {IDLE_LOAD}.")


def md_report(rows: list[dict], machine: dict, facts: list[str], label: str, run_at: str,
              loads: tuple, errors: dict, runs: int, rounds: int = 1, extra: dict | None = None,
              mongo_idx: dict | None = None, ctx: dict | None = None) -> str:
    ctx = ctx or {}
    L = ["# Three-engine comparison: MongoDB, Neo4j and SQLite", "", label_line(label, loads)]
    L += ["", f"Made by `ec-hw2/comparison/compare.py` on {run_at} UTC ({config.DATA_VERSION}). "
          f"Full tables: `comparison.csv` (the 6 compared rows) and `comparison_extra.csv` (the extra row). "
          f"Both questions use the history cohort and the shared definitions in `DATA_MODEL.md` section 7.", ""]
    if errors:
        L += ["**Engines that failed:** " + "; ".join(f"{e}: {msg}" for e, msg in errors.items()), ""]

    L += ["## Results", "",
          "| question | engine | lines of code | code characters | median ms | min-max ms | same result? "
          "| modeling note |",
          "|---|---|---:|---:|---:|---:|---|---|"]
    for r in rows:
        L.append(f"| {r['question']} | {r['engine']} | {r['lines_of_code']} | {r['code_chars']:,} | "
                 f"{fmt_ms(r['median_ms'])} | {fmt_range(r)} | {md_cell(r['same_result'])} | "
                 f"{md_cell(r['modeling_note'])} |")
    if extra:
        L.append(f"| {extra['question']} | {extra['engine']} (extra row, not compared) | {extra['lines_of_code']} "
                 f"| {extra['code_chars']:,} | {fmt_ms(extra['median_ms'])} | {fmt_range(extra)} | "
                 f"{md_cell(extra['same_result'])} | {md_cell(extra['modeling_note'])} |")
    diffs = [r for r in rows if r["difference"]]
    if diffs:
        L += ["", "Differences:"] + [f"- {r['question']}, {r['engine']}: {r['difference']}" for r in diffs]

    L += ["", "**Speed.** We call an engine faster only when its min-max range does not overlap the other "
          "engine's range.", ""]
    for qn in QUESTIONS:
        stats = {r["engine"]: r for r in rows if r["question"] == qn}
        for s in speed_sentences(stats):
            L.append(f"- {qn}: {s}")
    if extra and extra.get("median_ms") is not None:
        neo = next(r for r in rows if r["question"] == MUTUAL and r["engine"] == "Neo4j")
        for s in speed_sentences({extra["engine"]: extra, "Neo4j": neo}):
            L.append(f"- mutual reverts, extra row: {s}")

    L += ["", "## What each timed query reads", ""]
    neo_mut = next((r for r in rows if r["question"] == MUTUAL and r["engine"] == "Neo4j"), None)
    if neo_mut:
        export = (f" In MongoDB, the export_graph.py step that builds these relationships took "
                  f"{ctx['export_reverted_s']:.2f} s (from `_SUCCESS_export_graph.json`)."
                  if ctx.get("export_reverted_s") is not None else "")
        L.append(f"- **Neo4j, mutual reverts:** {neo_mut['input_note']}{export} MongoDB and SQLite do this "
                 "grouping inside the timed query, so the Neo4j time is not like for like.")
    if extra:
        L.append(f"- **Extra row:** `{extra['query_file']}` gives SQLite the same head start. It builds the "
                 f"grouped triples once as a TEMP table in memory ({extra['setup_ms']:,.1f} ms, not timed; "
                 f"{extra['setup_lines']} lines of setup code), then times only the self-join. Its result is "
                 f"compared with the SQLite raw-link result: {extra['same_result']}.")
    if ctx.get("mongo_links") is not None:
        L.append(f"- **MongoDB:** revert_links holds {ctx['mongo_links']:,} documents "
                 f"({ctx['mongo_links_history']:,} history, {ctx['mongo_links'] - ctx['mongo_links_history']:,} "
                 f"live) and revisions holds {ctx['mongo_revisions']:,} documents "
                 f"({ctx['mongo_revisions_history']:,} history). Both pipelines start with $match "
                 f"cohort = 'history', so the live documents are filtered out inside the timed query.")
    if mongo_idx and mongo_idx.get("pipelines"):
        idx = mongo_idx.get("index")
        for qn, p in mongo_idx["pipelines"].items():
            scan = p["stage"] + (f" on index {p['index']}" if p.get("index") else "")
            line = f"  - {qn}: query plan of the first $match: {scan}"
            if p.get("docs_examined") is not None:
                line += f", {p['docs_examined']:,} documents examined"
            if p.get("with_index_ms") is not None:
                line += (f"; median {p['with_index_ms']:,.1f} ms with this default plan and "
                         f"{p['collection_scan_ms']:,.1f} ms with a forced collection scan "
                         f"(hint {{$natural: 1}}, {INDEX_CHECK_RUNS} runs each, helper runs)")
            L.append(line + ".")
        if not idx:
            L.append("  - revert_links has no {cohort: 1, page_id: 1} index yet, so the first $match reads "
                     "every document, live ones included.")
    L.append("- **SQLite and Neo4j** hold the history cohort only.")

    pain_by = sorted({r["pain_scored_by"] for r in rows})
    L += ["", "## Modeling pain (1 = easy, 5 = hard)", "",
          f"Scored by: {'; '.join(pain_by)}. The scores and reasons come from `comparison/pain.csv`. "
          "They are not the team's judgment until the Comparison+viz owner re-scores them in that file "
          "and writes their name in scored_by.", "",
          "| question | engine | pain | reason | scored by |", "|---|---|---:|---|---|"]
    for r in rows:
        L.append(f"| {r['question']} | {r['engine']} | {r['modeling_pain']} | {md_cell(r['pain_reason'])} | "
                 f"{md_cell(r['pain_scored_by'])} |")

    L += ["", "## Candidate findings for 'Comparison top 5'", "",
          "Facts with numbers only. The Comparison+viz owner turns them into findings in their own words.", ""]
    L += [f"- {x}" for x in facts]

    L += ["", "## How we measured", "",
          "1. **Same result?** We compare the full ordered list. Top contested pages: (page_id, score "
          f"rounded to {config.SCORE_ROUND} digits), as `config.py` says. We also compare edits, "
          "revert_actions, reverted_editors and contested, and the 3 top-contested queries must return the "
          "same columns. No query computes a rank: `run_mongo.py`, `run_cypher.py` and `run_sql.py` add it in "
          "Python, so it is not timed in any engine. Mutual reverts: (page_id, a, b, a_reverted_b, "
          "b_reverted_a). Neo4j shows aliases, so we turn them back into editor keys with the graph's own "
          "key/alias map. \"yes\" means equal to both other engines.",
          f"2. **Time.** {runs_text(runs, rounds)}. The engines take turns, and the order changes after "
          "every run. The time runs in Python from sending the query until every row is in memory, so it "
          "includes the network hop and decoding for MongoDB and Neo4j. We report the median and the "
          "min-max range of all timed runs; `comparison.csv` also has the median of each round "
          "(round_medians_ms). We call an engine faster only when the ranges do not overlap. This file and "
          "`comparison.csv` are the one timing source for the comparison; the times in the "
          "`results/mongo_*`, `cypher_*` and `sql_*` files are single-engine runs, not for the comparison.",
          "3. **Query size.** Lines of code are non-blank lines that are not comments; code characters "
          "are the characters without spaces. MongoDB: the \"pipeline\" array in the JSON file, as "
          "`run_mongo.py` writes it. Neo4j: the \"main\" statement only (Cypher Q1 also has a \"total\" "
          "statement, which is not counted). SQLite: the whole statement, with its params block. Line counts "
          "depend on the layout (the CSV column bracket_only_lines counts lines with only brackets or "
          "commas), so read both numbers together.",
          "4. **Where the engines run.** MongoDB and Neo4j run in Docker in a Colima VM. SQLite runs inside "
          "the Python process on the host, with no network hop. So the times compare whole setups, not only "
          "the database engines.",
          "5. **Modeling pain** is a draft until the owner re-scores it (see above). The numbers in the "
          "modeling notes come from this run.",
          "", "## Machine", "", "| item | value |", "|---|---|"]
    for k, v in machine.items():
        L.append(f"| {k} | {md_cell(v)} |")
    L.append(f"| load average (1 / 5 / 15 min), start | {load_text(loads[0])} |")
    L.append(f"| load average (1 / 5 / 15 min), end | {load_text(loads[1])} |")
    L.append(f"| --final load threshold (1 min) | {IDLE_LOAD} |")

    L += ["", "## Query files", ""]
    for qn in QUESTIONS:
        L.append(f"- {qn}: " + ", ".join(f"{e} `{QUERY_FILES[qn][e].relative_to(config.HW2_DIR)}`"
                                          for e in ENGINES))
    if extra:
        L.append(f"- extra row: `{extra['query_file']}`")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Compare MongoDB, Neo4j and SQLite on the 2 questions.")
    p.add_argument("--final", action="store_true",
                   help=f'label the timings "final" (refused when the 1-minute load average is above {IDLE_LOAD})')
    p.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="timed runs per round (default 7)")
    p.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="rounds (default 3)")
    args = p.parse_args(argv)
    label = "final" if args.final else "draft"
    t0 = time.time()

    load_start = os.getloadavg()
    if args.final and load_start[0] > IDLE_LOAD:
        print(f"STOP: --final needs a quiet Mac, but the 1-minute load average is {load_start[0]:.2f} "
              f"(threshold {IDLE_LOAD}; 1 / 5 / 15 min: {load_text(load_start)}). Nothing was written. "
              "Wait until other jobs finish and try again, or run without --final (draft).")
        return 2
    config.ensure_dirs()
    queries = load_queries()
    extra_q = load_extra_query()
    pain = load_pain()

    eng = Engines()
    for e, msg in eng.errors.items():
        print(f"WARNING: {e} is not available: {msg}")
    extra = None
    try:
        machine = machine_info(eng)
        ctx = context_numbers(eng)
        alias_map = eng.alias_to_key() if eng.session is not None else None
        run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        results, outs, extra_res = {}, {}, None
        for qn in QUESTIONS:
            runners = {e: eng.runner(queries[(qn, e)]) for e in ENGINES if e not in eng.errors}
            setup_ms = None
            if qn == MUTUAL and "SQLite" not in eng.errors:
                # the extra row takes turns with the 3 engines, so it meets the same busy moments
                runners[EXTRA_NAME], setup_ms = eng.extra_runner(extra_q)
            print(f"=== {qn}: {', '.join(runners)} ({runs_text(args.runs, args.rounds)})", flush=True)
            res = measure(runners, args.runs, args.rounds)
            if EXTRA_NAME in res:
                extra_res = (res.pop(EXTRA_NAME), setup_ms)
            norm = {}
            for e, r in res.items():
                if r["error"]:
                    eng.errors[f"{e} ({qn})"] = r["error"]
                    print(f"  {e}: FAILED {r['error']}")
                    continue
                outs[(qn, e)] = r["rows"]
                norm[e] = norm_top(r["rows"]) if qn == TOP else norm_mutual(r["rows"], alias_map)
                print(f"  {e:8s} {len(r['rows']):>5,} rows  median {statistics.median(r['times']):9.1f} ms")
            results[qn] = (res, same_result(qn, norm), norm)
        print("=== MongoDB: query plans of the first $match (helper runs)", flush=True)
        try:
            mongo_idx = mongo_index_check(eng, queries)
        except Exception as exc:   # a helper; the comparison does not depend on it
            mongo_idx = {"index": None, "pipelines": {}, "error": f"{type(exc).__name__}: {exc}"}
            print(f"  skipped: {mongo_idx['error']}")
        load_end = os.getloadavg()
    finally:
        eng.close()

    rows = []
    for qn in QUESTIONS:
        res, same, _ = results[qn]
        for e in ENGINES:
            q = queries[(qn, e)]
            r = res.get(e, {"times": [], "round_medians": [], "rows": None, "error": "not run"})
            pn = pain[(qn, e)]
            rows.append({
                "timing_label": label, "run_at_utc": run_at, "question": qn, "engine": e,
                "language": LANGUAGE[e], "query_file": str(q["path"].relative_to(config.HW2_DIR)),
                "lines_of_code": len(q["code"]), "code_chars": code_chars(q["code"]),
                "bracket_only_lines": bracket_only_lines(q["code"]),
                **timing_stats(r), "rounds": args.rounds if r["times"] else 0,
                "result_rows": len(r["rows"]) if r["rows"] is not None and not r["error"] else None,
                "same_result": same[e]["text"], "difference": same[e]["difference"],
                "faster_than": "",
                "input_note": input_note(qn, e, ctx),
                "modeling_note": modeling_note(qn, q, ctx),
                "modeling_pain": pn["score"], "pain_reason": pn["reason"], "pain_scored_by": pn["scored_by"],
            })
    for qn in QUESTIONS:
        group = {r["engine"]: r for r in rows if r["question"] == qn}
        for e, others in faster_than(group).items():
            group[e]["faster_than"] = "; ".join(others)

    if extra_res is not None:
        r, setup_ms = extra_res
        sqlite_norm = results[MUTUAL][2].get("SQLite")
        if r["error"]:
            same_text = f"not checked ({r['error']})"
        elif sqlite_norm is None:
            same_text = "not checked (SQLite failed)"
        else:
            same_text = ("yes (same rows as the SQLite raw-link query)"
                         if norm_mutual(r["rows"])["key"] == sqlite_norm["key"] else "no")
        extra = {
            "timing_label": label, "run_at_utc": run_at, "question": MUTUAL, "engine": EXTRA_NAME,
            "variant": "extra row, not compared: TEMP table of grouped triples built before timing",
            "language": LANGUAGE["SQLite"], "query_file": str(extra_q["path"].relative_to(config.HW2_DIR)),
            "lines_of_code": len(extra_q["code"]), "code_chars": code_chars(extra_q["code"]),
            "setup_lines": extra_q["setup_lines"], "setup_ms": round(setup_ms, 1),
            **timing_stats(r), "rounds": args.rounds if r["times"] else 0,
            "result_rows": len(r["rows"]) if r["rows"] is not None and not r["error"] else None,
            "same_result": same_text,
            "input_note": ("Reads a TEMP table of (reverter, author, page) triples with their distinct revert "
                           "actions, built in memory before the timing, like the REVERTED relationships of Neo4j."),
            "modeling_note": "The same self-join as the SQLite query, on the pre-aggregated TEMP table.",
        }
        if extra["same_result"] == "no":
            eng.errors[f"{EXTRA_NAME} ({MUTUAL})"] = "the result differs from the SQLite raw-link query"

    top_cols = column_sets(outs, TOP)
    same_cols = len({tuple(c) for c in top_cols.values()}) == 1 and len(top_cols) == len(ENGINES)
    if top_cols and not same_cols:
        eng.errors["columns"] = f"the top-contested queries return different columns: {top_cols}"
    facts = findings(rows, outs, ctx, label, args.runs, args.rounds, extra, mongo_idx)

    write_safely(pd.DataFrame(rows).to_csv(index=False), OUT_CSV)
    write_safely(pd.DataFrame([extra] if extra else []).to_csv(index=False), OUT_EXTRA_CSV)
    write_safely(md_report(rows, machine, facts, label, run_at, (load_start, load_end), eng.errors,
                           args.runs, args.rounds, extra, mongo_idx, ctx), OUT_MD)
    all_same = all(r["same_result"].startswith("yes") for r in rows) and not eng.errors

    print("=== results")
    for r in rows + ([extra] if extra else []):
        print(f"  {r['question']:20s} {r['engine']:28s} LOC {r['lines_of_code']:>3}  chars {r['code_chars']:>5,}  "
              f"median {fmt_ms(r['median_ms']):>9} ms ({fmt_range(r)})  same: {r['same_result']}")
    print(f"load average start {load_text(load_start)}, end {load_text(load_end)}")
    print(f"wrote {shown(OUT_CSV)}, {shown(OUT_EXTRA_CSV)} and {shown(OUT_MD)} "
          f"(timing label: {label}) in {time.time() - t0:.1f} s")
    if not all_same:
        print("NOT OK: an engine failed or the outputs differ; _SUCCESS_comparison.json was not written.")
        return 1
    write_safely(json.dumps({
        "step": "comparison", "data_version": config.DATA_VERSION, "timing_label": label,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs": args.runs, "rounds": args.rounds,
        "rows": {"comparison.csv": len(rows), "comparison_extra.csv": 1 if extra else 0},
        "result_rows": {f"{r['question']} / {r['engine']}": r["result_rows"] for r in rows},
        "median_ms": {f"{r['question']} / {r['engine']}": r["median_ms"] for r in rows},
        "range_ms": {f"{r['question']} / {r['engine']}": [r["min_ms"], r["max_ms"]] for r in rows},
        "faster_than": {f"{r['question']} / {r['engine']}": r["faster_than"] for r in rows},
        "extra": ({k: extra[k] for k in ("engine", "median_ms", "min_ms", "max_ms", "setup_ms", "same_result")}
                  if extra else None),
        "mongo_index_check": mongo_idx,
        "top_columns_equal": same_cols,
        "pain_scored_by": sorted({r["pain_scored_by"] for r in rows}),
        "all_identical": all_same,
        "load_average_start": list(load_start), "load_average_end": list(load_end),
        "idle_load_threshold": IDLE_LOAD,
    }, indent=2, default=str) + "\n", OUT_SUCCESS)
    print(f"wrote {shown(OUT_SUCCESS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
