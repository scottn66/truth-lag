"""Load the graph CSV files into Neo4j: the local Docker database, or Neo4j Aura.

Purpose
    --target local   Runs queries/cypher/load.cypher, the same file Neo4j Desktop
                     users run by hand: it deletes everything in the database
                     (MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS), creates
                     the uniqueness constraints Editor.key and Page.id and 2 indexes,
                     then loads the 4 CSV files with
                     LOAD CSV ... CALL (row) { ... } IN TRANSACTIONS OF 10000 ROWS.
                     Each statement goes through session.run, which is an implicit
                     (auto-commit) transaction, as IN TRANSACTIONS needs. Neo4j reads
                     the files from its /import folder, which docker-compose.yml
                     mounts (read-only) from data/neo4j/import.
    --target aura    Aura cannot read files on this computer. So the script reads the
                     CSV files itself and sends them in batches of 5,000 rows with
                     UNWIND $rows AS row. The per-row Cypher is taken from load.cypher,
                     so the casts are the same. It needs --confirm-overwrite, because it
                     deletes everything in the Aura database first. Aura Free allows
                     200,000 nodes and 400,000 relationships; the full graph has more
                     nodes, so use --subset contested.
    --subset contested  Keep only the contested pages (Page.contested = true), their
                     EDITED relationships, the REVERTED relationships whose page_id is
                     a contested page, and the editors at the ends of those
                     relationships. Works with both targets.
    At the end it prints the node and relationship counts and checks them against the
    CSV row counts (exit code 1 if they differ).

Inputs
    data/neo4j/import/{editors,pages,edited,reverted}.csv and _SUCCESS_export_graph.json
    (made by export_graph.py). queries/cypher/load.cypher.
    local: config.NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD (from ec-hw2/.env).
    aura:  the environment variables NEO4J_AURA_URI, NEO4J_AURA_USER (default neo4j)
           and NEO4J_AURA_PASSWORD (put them in ec-hw2/.env; never commit it).

Outputs
    The graph in Neo4j (DATA_MODEL.md section 5), and
    data/neo4j/_SUCCESS_load_neo4j_<target>.json with the counts.

Run (from the repo root)
    .venv/bin/python ec-hw2/load_neo4j.py --target local                 (about 30 s)
    .venv/bin/python ec-hw2/load_neo4j.py --target local --subset contested
    .venv/bin/python ec-hw2/load_neo4j.py --target aura --subset contested --confirm-overwrite
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

LOAD_CYPHER = config.HW2_DIR / "queries" / "cypher" / "load.cypher"
CSV_NAMES = {"editors": "editors.csv", "pages": "pages.csv", "edited": "edited.csv",
             "reverted": "reverted.csv"}
EXPORT_SUCCESS = "_SUCCESS_export_graph.json"
AURA_BATCH = 5_000
AURA_MAX_NODES = 200_000
AURA_MAX_RELS = 400_000
LOAD_RE = re.compile(r"LOAD CSV WITH HEADERS FROM 'file:///([\w.-]+\.csv)' AS row\s*")
IN_TX_RE = re.compile(r"\}\s*IN TRANSACTIONS OF \d+ ROWS\s*$")


# --------------------------------------------------------------------------
# Cypher files (run_cypher.py uses these helpers too)
# --------------------------------------------------------------------------
def is_comment(line: str) -> bool:
    return line.strip().startswith("//")


def split_statements(text: str) -> list[str]:
    """Split a .cypher file into statements.

    A statement ends with ';' at the end of a line. Comment lines (starting with //)
    never end a statement, so a ';' inside a comment is safe. Statements that hold
    only comments are skipped. The comments before a statement stay with it.
    """
    out, cur = [], []
    for line in text.splitlines():
        if not is_comment(line) and line.rstrip().endswith(";"):
            cur.append(line.rstrip()[:-1])
            out.append("\n".join(cur).strip())
            cur = []
        else:
            cur.append(line)
    out.append("\n".join(cur).strip())
    return [s for s in out if code_of(s)]


def code_of(statement: str) -> str:
    """The statement without its comment lines and blank lines."""
    return "\n".join(l for l in statement.splitlines() if l.strip() and not is_comment(l)).strip()


def load_statements(path: Path = LOAD_CYPHER) -> list[str]:
    return [code_of(s) for s in split_statements(path.read_text(encoding="utf-8"))]


def csv_file_of(statement: str) -> str | None:
    """The CSV file a LOAD CSV statement reads, or None."""
    m = LOAD_RE.search(statement)
    return m.group(1) if m else None


def to_unwind(statement: str) -> str:
    """Turn 'LOAD CSV ... AS row CALL (row) {...} IN TRANSACTIONS ...' into 'UNWIND $rows AS row CALL (row) {...}'.

    The result runs inside one normal transaction per batch (for Aura).
    """
    if not csv_file_of(statement):
        raise ValueError("not a LOAD CSV statement")
    out = LOAD_RE.sub("UNWIND $rows AS row\n", statement, count=1)
    out, n = IN_TX_RE.subn("}", out)
    if n != 1:
        raise ValueError("expected one '} IN TRANSACTIONS OF n ROWS' at the end")
    return out


# --------------------------------------------------------------------------
# CSV files and the contested subset (pure Python)
# --------------------------------------------------------------------------
def read_csv_rows(path: Path) -> list[dict]:
    """CSV rows as dicts of strings; an empty field becomes None, as LOAD CSV does."""
    with open(path, encoding="utf-8", newline="") as f:
        return [{k: (v if v != "" else None) for k, v in r.items()} for r in csv.DictReader(f)]


def read_tables(folder: Path) -> dict[str, list[dict]]:
    return {name: read_csv_rows(folder / fname) for name, fname in CSV_NAMES.items()}


def contested_subset(tables: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Only the contested pages, the relationships on them, and the editors at their ends."""
    pages = [p for p in tables["pages"] if p["contested"] == "true"]
    ids = {p["id"] for p in pages}
    edited = [e for e in tables["edited"] if e["page_id"] in ids]
    reverted = [r for r in tables["reverted"] if r["page_id"] in ids]
    keys = ({e["editor_key"] for e in edited} | {r["reverter_key"] for r in reverted}
            | {r["author_key"] for r in reverted})
    editors = [e for e in tables["editors"] if e["key"] in keys]
    return {"editors": editors, "pages": pages, "edited": edited, "reverted": reverted}


def expected_counts(tables: dict[str, list[dict]]) -> dict[str, int]:
    return {"Editor": len(tables["editors"]), "Page": len(tables["pages"]),
            "EDITED": len(tables["edited"]), "REVERTED": len(tables["reverted"])}


def csv_row_count(path: Path) -> int:
    """Data rows of a CSV file (quoted fields may hold line breaks, so use the csv module)."""
    with open(path, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def batches(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


# --------------------------------------------------------------------------
# Neo4j
# --------------------------------------------------------------------------
COUNT_QUERIES = {
    "Editor": "MATCH (e:Editor) RETURN count(e) AS n",
    "Page": "MATCH (p:Page) RETURN count(p) AS n",
    "EDITED": "MATCH ()-[r:EDITED]->() RETURN count(r) AS n",
    "REVERTED": "MATCH ()-[r:REVERTED]->() RETURN count(r) AS n",
    "contested Page": "MATCH (p:Page {contested: true}) RETURN count(p) AS n",
}


def graph_counts(session) -> dict[str, int]:
    return {k: session.run(q).single()["n"] for k, q in COUNT_QUERIES.items()}


def connection_settings(target: str) -> tuple[str, str, str]:
    if target == "local":
        return config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD
    uri = os.environ.get("NEO4J_AURA_URI", "")
    if not uri:
        raise SystemExit("Set NEO4J_AURA_URI, NEO4J_AURA_USER and NEO4J_AURA_PASSWORD in ec-hw2/.env first.")
    return uri, os.environ.get("NEO4J_AURA_USER", "neo4j"), os.environ.get("NEO4J_AURA_PASSWORD", "")


def drop_our_projections(session) -> None:
    """Remove GDS graph projections left by run_cypher.py (they hold a copy of the old graph)."""
    try:
        names = [r["graphName"] for r in session.run("CALL gds.graph.list() YIELD graphName RETURN graphName")]
    except Exception:   # no GDS (Aura Free, or Desktop without the plugin)
        return
    for name in names:
        if name.startswith("cypher_"):
            session.run("CALL gds.graph.drop($name, false) YIELD graphName RETURN graphName",
                        name=name).consume()


def run_timed(session, label: str, query: str, **params) -> None:
    t = time.perf_counter()
    summary = session.run(query, **params).consume()
    c = summary.counters
    print(f"  {label}: {time.perf_counter() - t:6.1f} s  (nodes +{c.nodes_created} -{c.nodes_deleted}, "
          f"relationships +{c.relationships_created} -{c.relationships_deleted}, "
          f"constraints +{c.constraints_added}, indexes +{c.indexes_added})", flush=True)


def load_local(session, statements: list[str]) -> None:
    """Run load.cypher as it is: LOAD CSV reads the files from Neo4j's import folder."""
    for st in statements:
        first = st.splitlines()[0]
        run_timed(session, first[:60], st)


def load_rows(session, statements: list[str], tables: dict[str, list[dict]]) -> None:
    """Run load.cypher, but send the CSV rows with UNWIND $rows (Aura, or the subset)."""
    by_file = {fname: name for name, fname in CSV_NAMES.items()}
    for st in statements:
        fname = csv_file_of(st)
        if fname is None:
            run_timed(session, st.splitlines()[0][:60], st)
            continue
        rows = tables[by_file[fname]]
        query = to_unwind(st)
        t = time.perf_counter()
        for batch in batches(rows, AURA_BATCH):
            session.execute_write(lambda tx, b=batch: tx.run(query, rows=b).consume())
        print(f"  UNWIND {fname}: {len(rows):,} rows in {time.perf_counter() - t:6.1f} s", flush=True)


def write_success(target: str, data: dict) -> Path:
    path = config.DATA_DIR / "neo4j" / f"_SUCCESS_load_neo4j_{target}.json"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Load the graph CSV files into Neo4j.")
    p.add_argument("--target", choices=["local", "aura"], required=True)
    p.add_argument("--subset", choices=["contested"], default=None,
                   help="load only the contested pages, their editors and the edges among them")
    p.add_argument("--confirm-overwrite", action="store_true",
                   help="needed for --target aura: it deletes everything in the Aura database")
    args = p.parse_args(argv)
    t0 = time.time()

    folder = config.NEO4J_IMPORT_DIR
    missing = [f for f in [*CSV_NAMES.values(), EXPORT_SUCCESS] if not (folder / f).exists()]
    if missing:
        raise SystemExit(f"Missing in {folder}: {missing}. Run first: .venv/bin/python ec-hw2/export_graph.py")
    export = json.loads((folder / EXPORT_SUCCESS).read_text(encoding="utf-8"))
    if args.target == "aura" and not args.confirm_overwrite:
        raise SystemExit("--target aura deletes everything in the Aura database. Add --confirm-overwrite.")

    statements = load_statements()
    tables = None
    if args.target == "aura" or args.subset:
        tables = read_tables(folder)
        if args.subset == "contested":
            tables = contested_subset(tables)
        expected = expected_counts(tables)
    else:
        expected = {"Editor": csv_row_count(folder / "editors.csv"),
                    "Page": csv_row_count(folder / "pages.csv"),
                    "EDITED": csv_row_count(folder / "edited.csv"),
                    "REVERTED": csv_row_count(folder / "reverted.csv")}
        for name, fname in CSV_NAMES.items():
            key = {"editors": "Editor", "pages": "Page", "edited": "EDITED", "reverted": "REVERTED"}[name]
            if export["rows"].get(fname) != expected[key]:
                raise SystemExit(f"{fname}: {expected[key]} rows, but the export wrote "
                                 f"{export['rows'].get(fname)}. Run export_graph.py again.")
    print(f"Target: {args.target}" + (f", subset: {args.subset}" if args.subset else "")
          + f". Expected: {expected}")
    if args.target == "aura":
        n_nodes = expected["Editor"] + expected["Page"]
        n_rels = expected["EDITED"] + expected["REVERTED"]
        if n_nodes > AURA_MAX_NODES or n_rels > AURA_MAX_RELS:
            raise SystemExit(f"{n_nodes:,} nodes / {n_rels:,} relationships is over the Aura Free "
                             f"limit ({AURA_MAX_NODES:,} / {AURA_MAX_RELS:,}). Use --subset contested.")

    uri, user, password = connection_settings(args.target)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    with driver.session() as session:
        drop_our_projections(session)
        if tables is None:
            load_local(session, statements)
        else:
            load_rows(session, statements, tables)
        counts = graph_counts(session)
    driver.close()

    print("Counts in Neo4j:")
    for k, v in counts.items():
        print(f"  {k:15s} {v:>9,}")
    ok = all(counts[k] == expected[k] for k in expected)
    print("Check: counts = CSV rows:", "OK" if ok else "DIFFERENT")
    path = write_success(args.target, {
        "step": "load_neo4j", "target": args.target, "subset": args.subset,
        "data_version": config.DATA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "expected": expected, "counts": counts, "ok": ok, "seconds": round(time.time() - t0, 1)})
    print(f"Wrote {path}. Done in {time.time() - t0:.1f} s. "
          "Next: .venv/bin/python ec-hw2/queries/run_cypher.py")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
