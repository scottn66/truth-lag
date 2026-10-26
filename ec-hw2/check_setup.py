"""Check that your computer is ready for EC HW2. It prints one line per check.

What it is for:
    Run this before you open the notebooks. It checks Python, the packages,
    the ec-hw2/.env file, the data files and the database connections.
    Each line starts with OK, FAIL or SKIP. FAIL and SKIP lines end with a hint
    in plain English. If you need help, copy ALL the lines and paste them into
    the group chat. The output never shows a password or a connection string.

Reads:
    - ec-hw2/.env: only to see that it exists and which settings are filled in.
      It never prints a value.
    - data/tables/*.parquet, data/tables/truthlag.sqlite, data/tables/DATA_VERSION
      and data/neo4j/import/*.csv: it opens them only to count rows.
    - the local MongoDB, MongoDB Atlas and Neo4j: one short test connection each.
    - ec-hw2/results/figures/: it only looks whether the required screenshots and
      Atlas Charts PNGs exist (the "Figures" lines). Owners make them in the UI.
Writes:
    nothing (screen output only).

Run it from the repo folder (truth-lag):
    Mac:          python3 ec-hw2/check_setup.py
    Windows:      python ec-hw2\\check_setup.py
    Scott's Mac:  .venv/bin/python ec-hw2/check_setup.py

It never stops with an error, and the exit code is always 0.
It uses only pathlib and Python code (no shell commands), so it works on Windows and Mac.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import platform
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

HW2_DIR = Path(__file__).resolve().parent      # .../truth-lag/ec-hw2
REPO_ROOT = HW2_DIR.parent                       # .../truth-lag
sys.path.insert(0, str(HW2_DIR))

OK, FAIL, SKIP = "OK", "FAIL", "SKIP"

# (import name, name for pip, what we use it for)
PACKAGES = [
    ("pandas", "pandas", "tables"),
    ("pyarrow", "pyarrow", "Parquet files"),
    ("pymongo", "pymongo", "MongoDB"),
    ("neo4j", "neo4j", "Neo4j"),
    ("dotenv", "python-dotenv", "reads ec-hw2/.env"),
    ("matplotlib", "matplotlib", "figures"),
    ("tabulate", "tabulate", "text tables"),
]

# Data files from DATA_MODEL.md (sections 3, 5 and 6).
TABLE_FILES = [
    "history_revisions.parquet",
    "live_revisions.parquet",
    "history_revert_links.parquet",
    "live_revert_links.parquet",
    "late_reverts.parquet",
    "truthlag.sqlite",
]
NEO4J_CSV_FILES = ["editors.csv", "pages.csv", "edited.csv", "reverted.csv"]
SQLITE_TABLES = ["revisions", "revert_links"]

ENV_KEYS = ["MONGO_URI", "MONGO_DB", "ATLAS_URI", "ATLAS_DB", "SHARDED_URI",
            "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]

# The PNG files that owners make in a UI (named in guides/*.md and in the report skeleton).
# (group name, guide that says how, files). One printed line per group keeps each line short.
REQUIRED_FIGURES = [
    ("Figures: Atlas screenshots", "guides/ATLAS_SETUP.md, part F (Data+MongoDB)",
     ["atlas_cluster_m0.png", "atlas_indexes.png", "atlas_sample_document.png",
      "atlas_mongo_q1.png", "atlas_mongo_q2.png", "atlas_mongo_q3.png", "atlas_mongo_q4.png",
      "mongo_q5_local.png"]),
    ("Figures: Atlas Charts", "guides/ATLAS_CHARTS.md (Comparison+viz)",
     ["chart_q1_hour_kind.png", "chart_q3_time_to_revert.png"]),
    ("Figures: Neo4j graph screenshots", "guides/NEO4J_SCREENSHOTS.md, part C (Neo4j)",
     ["neo4j_schema.png", "neo4j_mutual_reverts.png", "neo4j_contested_page.png",
      "neo4j_largest_community.png"]),
    ("Figures: Neo4j query tables", "guides/NEO4J_SCREENSHOTS.md, part D (Neo4j)",
     [f"neo4j_cypher_q{i}_table.png" for i in range(1, 6)]),
]

HINT_DATA = ("Only needed for way 3 (Python). Download the data release files into data/ "
             "exactly (README, 'Three ways to check your part'). Scott's Mac: run the pipeline.")
HINT_DOCKER = ("Only needed if you run the databases yourself. Start them: 'colima start', then "
               "'docker compose -f ec-hw2/docker-compose.yml --env-file ec-hw2/.env up -d'. "
               "If you use only Atlas or GitHub, ignore this line.")


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
class Result:
    """One printed line: status, what was checked, what we found, and a hint."""

    def __init__(self, status: str, name: str, detail: str = "", hint: str = ""):
        self.status, self.name, self.detail, self.hint = status, name, detail, hint

    def line(self) -> str:
        text = f"{self.status:<5}{self.name}: {self.detail}".rstrip()
        if self.hint and self.status != OK:
            text += f"  Hint: {self.hint}"
        return text


_URI_LOGIN = re.compile(r"(//)[^/@\s]+@")


def clean(text, secrets=()) -> str:
    """Make an error message safe to paste: no passwords, no logins in URIs, one line."""
    text = str(text)
    for s in sorted({s for s in secrets if s and len(s) >= 3}, key=len, reverse=True):
        text = text.replace(s, "***")
    text = _URI_LOGIN.sub(r"\1***@", text)
    text = " ".join(text.split())
    return text if len(text) <= 220 else text[:217] + "..."


def secrets_from(settings: dict) -> list[str]:
    """Every value that must never be printed: the Neo4j password and passwords inside URIs."""
    out = [settings.get("NEO4J_PASSWORD", "")]
    for key in ("MONGO_URI", "ATLAS_URI", "SHARDED_URI", "NEO4J_URI"):
        uri = settings.get(key, "") or ""
        try:
            pw = urlsplit(uri).password
        except ValueError:
            pw = None
        if pw:
            out += [pw, unquote(pw)]
    return [s for s in out if s]


def show_path(path: Path) -> str:
    """Path relative to the repo, with '/' on every computer (easier to read in chat)."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def read_env_file(path: Path) -> dict:
    """Read KEY=VALUE lines from a .env file. Used only when python-dotenv is missing."""
    values = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:          # a comment after the value
            value = value.split(" #", 1)[0].strip()
        values[key.strip()] = value
    return values


def get_settings() -> tuple[dict, str]:
    """Paths and connection settings from config.py (falls back to safe defaults)."""
    data_dir = REPO_ROOT / "data"
    s = {
        "TABLES_DIR": data_dir / "tables",
        "FIGURES_DIR": HW2_DIR / "results" / "figures",
        "NEO4J_IMPORT_DIR": data_dir / "neo4j" / "import",
        "SQLITE_PATH": data_dir / "tables" / "truthlag.sqlite",
        "DATA_VERSION": "",
        "COL_REVISIONS": "revisions",
        "MONGO_URI": os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
        "MONGO_DB": os.environ.get("MONGO_DB", "truthlag"),
        "ATLAS_URI": os.environ.get("ATLAS_URI", ""),
        "ATLAS_DB": os.environ.get("ATLAS_DB", "truthlag"),
        "SHARDED_URI": os.environ.get("SHARDED_URI", ""),
        "NEO4J_URI": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "NEO4J_USER": os.environ.get("NEO4J_USER", "neo4j"),
        "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", ""),
    }
    problem = ""
    try:
        import config  # noqa: WPS433 (import here so a broken config cannot crash us)
        for key in list(s):
            if hasattr(config, key):
                s[key] = getattr(config, key)
    except Exception as exc:  # config.py missing or broken: keep the defaults
        problem = f"{type(exc).__name__}: {exc}"
    # Without python-dotenv, config.py cannot read ec-hw2/.env, so we read it here.
    if importlib.util.find_spec("dotenv") is None:
        for key, value in read_env_file(HW2_DIR / ".env").items():
            if key in ENV_KEYS and value:
                s[key] = value
    return s, problem


# --------------------------------------------------------------------------
# The checks. Each returns a Result or a list of Results.
# --------------------------------------------------------------------------
def python_status(version_info=None) -> Result:
    """3.12 is recommended, 3.11 works, older is a FAIL."""
    vi = tuple(version_info or sys.version_info)[:3]
    text = ".".join(str(x) for x in vi)
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    venv = "venv active" if in_venv else "no venv active: see README, way 3, step 4"
    name = "Python version"
    if vi >= (3, 13):
        return Result(OK, name, f"{text} ({venv}). 3.12 is recommended; if a package will not install, use 3.12")
    if vi >= (3, 12):
        return Result(OK, name, f"{text}, recommended ({venv})")
    if vi >= (3, 11):
        return Result(OK, name, f"{text} works; 3.12 is recommended ({venv})")
    return Result(FAIL, name, f"{text} is too old",
                  "Install Python 3.12 from python.org. On Windows, tick 'Add python.exe to PATH'.")


def check_package(import_name: str, pip_name: str, used_for: str) -> Result:
    name = f"Package {import_name}"
    try:
        module = importlib.import_module(import_name)
    except Exception as exc:
        return Result(FAIL, name, f"cannot import ({type(exc).__name__}); needed for {used_for}",
                      "Turn on the venv, then run: pip install -r ec-hw2/requirements.txt")
    version = getattr(module, "__version__", "") or getattr(module, "version", "")
    if not isinstance(version, str) or not version:
        try:
            from importlib.metadata import version as dist_version
            version = dist_version(pip_name)
        except Exception:
            version = "version unknown"
    return Result(OK, name, f"{version} ({used_for})")


def check_env_file(settings: dict) -> Result:
    """The file must exist. We list which settings are filled in, never their values."""
    name = "File ec-hw2/.env"
    path = HW2_DIR / ".env"
    if not path.is_file():
        if (HW2_DIR / ".env.txt").is_file():
            return Result(FAIL, name, "missing, but ec-hw2/.env.txt exists",
                          "Rename ec-hw2/.env.txt to .env (Windows hides the .txt ending).")
        return Result(FAIL, name, "missing",
                      "Copy ec-hw2/.env.example to ec-hw2/.env (Mac: cp, Windows: copy). Never commit it.")
    in_file = read_env_file(path)
    filled = [k for k in ENV_KEYS if in_file.get(k)]
    empty = [k for k in ENV_KEYS if k in in_file and not in_file.get(k)]
    detail = f"found; filled in: {', '.join(filled) or 'none'}"
    if empty:
        detail += f"; empty: {', '.join(empty)}"
    return Result(OK, name, detail + " (values are never shown)")


def _count_csv_rows(path: Path) -> int:
    lines = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            lines += chunk.count(b"\n")
    return max(lines - 1, 0)   # minus the header line


def check_data_file(path: Path, kind: str) -> Result:
    """kind is 'parquet', 'sqlite' or 'csv'. We count rows to prove the file is not broken."""
    name = f"Data {show_path(path)}"
    if not path.is_file():
        return Result(FAIL, name, "missing", HINT_DATA)
    size_mb = path.stat().st_size / 1e6
    try:
        if kind == "parquet":
            try:
                import pyarrow.parquet as pq
            except Exception:
                return Result(OK, name, f"{size_mb:.1f} MB (install pyarrow to count rows)")
            rows = pq.read_metadata(path).num_rows
            return Result(OK, name, f"{rows:,} rows, {size_mb:.1f} MB")
        if kind == "sqlite":
            uri = path.resolve().as_uri() + "?mode=ro"
            con = sqlite3.connect(uri, uri=True)
            try:
                tables = {r[0] for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'")}
                missing = [t for t in SQLITE_TABLES if t not in tables]
                if missing:
                    return Result(FAIL, name, f"tables missing: {', '.join(missing)}",
                                  "Download truthlag.sqlite again from the data release.")
                n = con.execute("SELECT COUNT(*) FROM revisions").fetchone()[0]
            finally:
                con.close()
            return Result(OK, name, f"tables {', '.join(SQLITE_TABLES)}; revisions = {n:,} rows, {size_mb:.1f} MB")
        if kind == "csv":
            return Result(OK, name, f"{_count_csv_rows(path):,} rows, {size_mb:.1f} MB")
        return Result(FAIL, name, f"unknown file kind {kind!r}")
    except Exception as exc:
        return Result(FAIL, name, f"cannot read it ({clean(type(exc).__name__ + ': ' + str(exc))})",
                      "The file may be broken or only half downloaded. Download it again.")


def check_data_version(tables_dir: Path, expected: str) -> Result:
    name = "Data version"
    path = tables_dir / "DATA_VERSION"
    if not path.is_file():
        return Result(SKIP, name, f"no {show_path(path)} file (the code expects {expected or 'unknown'})",
                      "Fine on Scott's Mac. The data release has this file; put it in data/tables/.")
    found = path.read_text(encoding="utf-8", errors="replace").strip()
    if expected and found != expected:
        return Result(FAIL, name, f"your data is {found}, but the code expects {expected}",
                      "Download the newest data release, or get the newest code from branch ec-hw2.")
    return Result(OK, name, f"{found} (same as the code)")


def check_required_figures(fig_dir: Path, name: str, guide: str, files: list[str]) -> Result:
    """SKIP (not FAIL) while a figure is missing: owners make them in the UI, Sun-Tue."""
    missing = [f for f in files if not (Path(fig_dir) / f).is_file()]
    if not missing:
        return Result(OK, name, f"all {len(files)} found in {show_path(Path(fig_dir))}")
    return Result(SKIP, name, f"{len(missing)} of {len(files)} not made yet: {', '.join(missing)}",
                  f"Made by the owner in the UI: {guide}. Then upload to ec-hw2/results/figures/.")


def _mongo_summary(uri: str, db_name: str, col: str, timeout_ms: int, where: str = "") -> str:
    from pymongo import MongoClient
    client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms, connectTimeoutMS=timeout_ms)
    try:
        version = client.server_info().get("version", "?")
        names = client[db_name].list_collection_names()
        text = f"MongoDB {version}{' at ' + where if where else ''}; database {db_name} has {len(names)} collections"
        if col in names:
            text += f"; {col} = about {client[db_name][col].estimated_document_count():,} documents"
        elif names:
            text += f" (no {col} collection yet)"
        else:
            text += " (nothing loaded yet)"
        return text
    finally:
        client.close()


def check_mongo_local(settings: dict) -> Result:
    name = "MongoDB local"
    try:
        import pymongo  # noqa: F401
    except Exception:
        return Result(SKIP, name, "pymongo is not installed", "Install the packages first (see the lines above).")
    uri = settings["MONGO_URI"]
    try:
        host = urlsplit(uri).hostname or "?"
        port = urlsplit(uri).port or 27017
    except ValueError:
        host, port = "?", "?"
    try:
        text = _mongo_summary(uri, settings["MONGO_DB"], settings["COL_REVISIONS"], 2000, f"{host}:{port}")
        return Result(OK, name, text)
    except Exception as exc:
        return Result(FAIL, name, f"cannot connect to {host}:{port} in 2 s "
                      f"({clean(type(exc).__name__ + ': ' + str(exc), secrets_from(settings))})", HINT_DOCKER)


def check_atlas(settings: dict) -> Result:
    name = "MongoDB Atlas"
    uri = (settings.get("ATLAS_URI") or "").strip()
    if not uri:
        return Result(SKIP, name, "ATLAS_URI is empty in ec-hw2/.env",
                      "Ask the Data+MongoDB owner for the read-only connection string (guides/ATLAS_SETUP.md).")
    if "<" in uri or ">" in uri:
        return Result(SKIP, name, "ATLAS_URI still has example text in angle brackets < >",
                      "Put the real connection string into ec-hw2/.env.")
    try:
        import pymongo  # noqa: F401
    except Exception:
        return Result(SKIP, name, "pymongo is not installed", "Install the packages first (see the lines above).")
    try:
        text = _mongo_summary(uri, settings["ATLAS_DB"], settings["COL_REVISIONS"], 5000)
        return Result(OK, name, text)
    except Exception as exc:
        return Result(FAIL, name, f"cannot connect in 5 s ({clean(type(exc).__name__ + ': ' + str(exc), secrets_from(settings))})",
                      "Check 1) your IP is in Atlas > Network Access, 2) the user and password in "
                      "ATLAS_URI, 3) your internet. Then paste this line in the group chat.")


def check_neo4j(settings: dict) -> list[Result]:
    name, gds_name = "Neo4j", "Neo4j GDS plugin"
    if not settings.get("NEO4J_PASSWORD"):
        why = "NEO4J_PASSWORD is empty in ec-hw2/.env"
        hint = ("Only needed if you run Neo4j yourself (Docker or Neo4j Desktop). "
                "Put your Neo4j password into ec-hw2/.env.")
        return [Result(SKIP, name, why, hint), Result(SKIP, gds_name, "Neo4j was not checked", hint)]
    try:
        from neo4j import GraphDatabase
    except Exception:
        hint = "Install the packages first (see the lines above)."
        return [Result(SKIP, name, "the neo4j package is not installed", hint),
                Result(SKIP, gds_name, "Neo4j was not checked", hint)]
    uri = settings["NEO4J_URI"]
    try:
        where = f"{urlsplit(uri).hostname}:{urlsplit(uri).port or 7687}"
    except ValueError:
        where = "?"
    secrets = secrets_from(settings)
    driver = None
    try:
        driver = GraphDatabase.driver(uri, auth=(settings["NEO4J_USER"], settings["NEO4J_PASSWORD"]),
                                      connection_timeout=3.0, connection_acquisition_timeout=3.0,
                                      max_transaction_retry_time=0.0)
        driver.verify_connectivity()
        with driver.session() as session:
            # dbms.components() can list more than one component; we want the database itself.
            rec = session.run("CALL dbms.components() YIELD name, versions, edition "
                              "WHERE name = 'Neo4j Kernel' "
                              "RETURN versions[0] AS version, edition LIMIT 1").single()
            if rec is None:
                rec = {"version": "?", "edition": "?"}
            nodes = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
        text = f"Neo4j {rec['version']} ({rec['edition']}) at {where}; {nodes:,} nodes"
        if nodes == 0:
            text += " (graph not loaded yet)"
        results = [Result(OK, name, text)]
        try:
            with driver.session() as session:   # a new session: a failed query cannot spoil the first one
                gds = session.run("RETURN gds.version() AS v").single()["v"]
            results.append(Result(OK, gds_name, f"GDS {gds} (Cypher Q2 PageRank, Cypher Q3 Louvain and WCC)"))
        except Exception as exc:
            results.append(Result(FAIL, gds_name, f"not found ({clean(type(exc).__name__, secrets)})",
                                  "Cypher Q2 and Q3 need it. Neo4j Desktop: install Graph Data Science "
                                  "from the Plugins tab, then restart the database."))
        return results
    except Exception as exc:
        kind = type(exc).__name__
        if kind == "AuthError":
            hint = "The password in ec-hw2/.env does not match your Neo4j password."
        else:
            hint = ("Start Neo4j: Scott's Mac 'colima start' + docker compose (README); "
                    "Neo4j Desktop: press Start on your database.")
        return [Result(FAIL, name, f"cannot connect to {where} in 3 s ({clean(kind + ': ' + str(exc), secrets)})", hint),
                Result(SKIP, gds_name, "Neo4j is not reachable", hint)]
    finally:
        if driver is not None:
            try:
                driver.close()
            except Exception:
                pass


# --------------------------------------------------------------------------
# Running the checks
# --------------------------------------------------------------------------
def run_check(label: str, func, *args, secrets=()) -> list[Result]:
    """Run one check. Any error becomes a FAIL line with the reason (no secrets)."""
    try:
        out = func(*args)
        return out if isinstance(out, list) else [out]
    except Exception as exc:
        return [Result(FAIL, label, f"the check itself failed ({clean(type(exc).__name__ + ': ' + str(exc), secrets)})",
                       "Paste this line in the group chat.")]


def all_checks(settings: dict) -> list[tuple]:
    """(label, function, args) for every check, in the printed order."""
    checks = [("Python version", python_status)]
    checks += [(f"Package {imp}", check_package, imp, pip, why) for imp, pip, why in PACKAGES]
    checks.append(("File ec-hw2/.env", check_env_file, settings))
    tables_dir = Path(settings["TABLES_DIR"])
    for fname in TABLE_FILES:
        path = Path(settings["SQLITE_PATH"]) if fname.endswith(".sqlite") else tables_dir / fname
        kind = "sqlite" if fname.endswith(".sqlite") else "parquet"
        checks.append((f"Data {fname}", check_data_file, path, kind))
    for fname in NEO4J_CSV_FILES:
        checks.append((f"Data {fname}", check_data_file, Path(settings["NEO4J_IMPORT_DIR"]) / fname, "csv"))
    checks.append(("Data version", check_data_version, tables_dir, settings.get("DATA_VERSION", "")))
    for name, guide, files in REQUIRED_FIGURES:
        checks.append((name, check_required_figures, Path(settings["FIGURES_DIR"]), name, guide, files))
    checks.append(("MongoDB local", check_mongo_local, settings))
    checks.append(("MongoDB Atlas", check_atlas, settings))
    checks.append(("Neo4j", check_neo4j, settings))
    return checks


def main() -> list[Result]:
    try:   # Old Windows consoles cannot print every character; never crash on that.
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    settings, config_problem = get_settings()
    secrets = secrets_from(settings)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"EC HW2 setup check, {now}")
    print(f"Computer: {platform.system()} {platform.release()} ({platform.machine()}); "
          f"the code expects data version {settings.get('DATA_VERSION') or 'unknown'}")
    print("-" * 72)
    results: list[Result] = []
    if config_problem:
        res = Result(FAIL, "File ec-hw2/config.py", f"cannot load it ({clean(config_problem, secrets)})",
                     "Get the code again from branch ec-hw2. Default paths are used below.")
        results.append(res)
        print(res.line(), flush=True)
    hints_shown: set[str] = set()
    for label, func, *args in all_checks(settings):
        for res in run_check(label, func, *args, secrets=secrets):
            res.detail, res.hint = clean(res.detail, secrets), clean(res.hint, secrets)
            results.append(res)
            if res.hint and res.status != OK:
                if res.hint in hints_shown:      # a long hint once is enough
                    res = Result(res.status, res.name, res.detail, "the same as above")
                else:
                    hints_shown.add(res.hint)
            print(res.line(), flush=True)
    counts = {s: sum(r.status == s for r in results) for s in (OK, FAIL, SKIP)}
    print("-" * 72)
    print(f"Result: {counts[OK]} OK, {counts[FAIL]} FAIL, {counts[SKIP]} SKIP.")
    print("A FAIL matters only for the way you work (README, 'Three ways to check your part').")
    print("Need help? Copy ALL the lines above and paste them into the group chat. "
          "They contain no passwords.")
    return results


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:   # even Ctrl-C or a bug here must not end with an error code
        print(f"FAIL check_setup.py stopped early ({type(exc).__name__}). "
              "Paste everything above into the group chat.")
    sys.exit(0)
