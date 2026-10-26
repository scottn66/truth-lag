"""Run the Cypher query files on the local Neo4j and save the results.

Purpose
    For each query file in queries/cypher/ (Cypher Q1-Q5 and compare_top_contested;
    load.cypher is run by load_neo4j.py instead):
    1. split it into statements (';' at the end of a line; comment-only parts skipped);
    2. run the statements in order, with the parameters from config.py ($top_n,
       $contested_min_edits, ...);
    3. save every statement that has a "// result: <label>" line:
       label main -> results/cypher_<file>.csv and .md,
       other label -> results/cypher_<file>_<label>.csv and .md.
    A read-only result statement runs 1 warm-up + 7 timed times; we report the median.
    A statement that writes (GDS project/drop, gds.louvain.write) runs once.
    Before a statement that calls gds.pageRank.stream, it runs gds.pageRank.stats with
    the same graph and the same settings, and stops with an error if didConverge is
    false (the scores would not be final).
    compare_top_contested has no rank column (as Mongo Q2); this script adds it to the
    result file, as run_mongo.py does.
    Then it checks the results:
    - compare_top_contested = results/mongo_q2_top_contested_pages.csv (same 20
      page_ids in the same order, scores rounded to 6 digits);
    - Cypher Q1 = results/mongo_compare_mutual_reverts.csv (the full ordered list);
    - Cypher Q3: Louvain wrote communityId on every editor, community_sizes has the same
      total as louvain_stats, and the WCC sizes add up;
    - the stored counts on Editor and Page nodes match the relationships;
    - every human Editor.alias is the shared pseudonym of its key (the function in
      ingest/build_documents.py that MongoDB and SQL also use), so a stale graph is found;
    - no output shows an editor key, and every editor column shows an alias.
    Last, it draws results/figures/neo4j_edit_war_example.png: one page where editors
    reverted each other, drawn with matplotlib (pseudonyms only). It is a backup in
    case Neo4j Browser screenshots fail.

Inputs
    The local Neo4j graph (load_neo4j.py --target local), queries/cypher/*.cypher,
    results/mongo_q2_top_contested_pages.csv and results/mongo_compare_mutual_reverts.csv
    (from queries/run_mongo.py; a check is skipped when its file is missing), and the
    editor keys in data/tables/*_revisions.parquet and *_revert_links.parquet (for the
    alias check).

Outputs
    results/cypher_*.csv and .md, results/cypher_summary.csv and .md (timings),
    results/figures/neo4j_edit_war_example.png, results/_SUCCESS_cypher_queries.json.
    Cypher Q3 also writes the property communityId on every Editor node.

Run (from the repo root)
    .venv/bin/python ec-hw2/queries/run_cypher.py                (about 1 minute)
    .venv/bin/python ec-hw2/queries/run_cypher.py --runs 1       (quick, no warm-up timing)
    .venv/bin/python ec-hw2/queries/run_cypher.py --only q1_mutual_reverts
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import load_neo4j  # noqa: E402  (split_statements, code_of, drop_our_projections)

CYPHER_DIR = Path(__file__).resolve().parent / "cypher"
QUERY_FILES = ["q1_mutual_reverts", "q2_central_reverters", "q3_conflict_communities",
               "q4_pages_most_warring_editors", "q5_two_hop_contested", "compare_top_contested"]
PARAMS = {"top_n": config.TOP_N,
          "contested_min_edits": config.CONTESTED_MIN_EDITS,
          "contested_min_editors": config.CONTESTED_MIN_EDITORS,
          "contested_min_actions": config.CONTESTED_MIN_ACTIONS,
          "contested_min_score": config.CONTESTED_MIN_SCORE}
DEFAULT_RUNS = 7
MD_ROWS = 30
RESULT_RE = re.compile(r"^\s*//\s*result:\s*(\w+)\s*$", re.MULTILINE)
PARAMS_RE = re.compile(r":params\s*(\{.*\})")
WRITE_RE = re.compile(r"\.write\b|\.mutate\b|gds\.graph\.(project|drop)\b"
                      r"|\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP|LOAD CSV)\b")
KEY_RE = re.compile(r"^(u:\d+|t:~)")          # an editor key must never be in a result
EDITOR_COLUMNS = {"editor", "editor_a", "editor_b", "top_reverters"}
MONGO_Q2 = config.RESULTS_DIR / "mongo_q2_top_contested_pages.csv"
MONGO_MUTUAL = config.RESULTS_DIR / "mongo_compare_mutual_reverts.csv"
FIGURE = config.FIGURES_DIR / "neo4j_edit_war_example.png"
FIGURE_MAX_EDITORS = 10   # keep the drawing small enough to read
# Result files that get a rank column here, because the query has none (as Mongo Q2).
ADD_RANK = {("compare_top_contested", "main")}
# gds.pageRank.stream('<graph>', {<settings>}): the settings map has no nested braces.
PAGERANK_RE = re.compile(r"gds\.pageRank\.stream\(\s*'(\w+)'\s*,\s*(\{[^{}]*\})\s*\)")


# --------------------------------------------------------------------------
# Query files
# --------------------------------------------------------------------------
def header_lines(text: str) -> list[str]:
    """The comment block at the top of a file, without the '//' marks."""
    out = []
    for line in text.splitlines():
        if not line.strip():
            break
        if not load_neo4j.is_comment(line):
            break
        out.append(line.strip()[2:].strip())
    return out


def browser_params(text: str) -> dict:
    """The ':params {...}' line of a file header, as a dict (to check it against config)."""
    m = PARAMS_RE.search(text)
    if not m:
        return {}
    body = re.sub(r"(\w+)\s*:", r'"\1":', m.group(1))
    return json.loads(body)


def result_label(statement: str) -> str | None:
    m = RESULT_RE.search(statement)
    return m.group(1) if m else None


def is_read_only(statement: str) -> bool:
    return WRITE_RE.search(load_neo4j.code_of(statement)) is None


def output_stem(name: str, label: str) -> str:
    return f"cypher_{name}" if label == "main" else f"cypher_{name}_{label}"


def pagerank_calls(code: str) -> list[tuple[str, str]]:
    """(graph name, settings map text) of every gds.pageRank.stream call in a statement."""
    return PAGERANK_RE.findall(code)


def with_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Add rank = 1, 2, ... in the row order of the query (as run_mongo.py does for Mongo Q2)."""
    out = df.copy()
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def parse_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    statements = []
    for st in load_neo4j.split_statements(text):
        statements.append({"code": load_neo4j.code_of(st), "label": result_label(st),
                           "read_only": is_read_only(st)})
    labels = [s["label"] for s in statements if s["label"]]
    if len(labels) != len(set(labels)):
        raise ValueError(f"{path.name}: two statements have the same result label")
    return {"name": path.stem, "path": path, "header": header_lines(text),
            "params": browser_params(text), "statements": statements}


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------
def plain(v):
    """A value that CSV and Markdown can show: lists joined with ' | ', times as ISO text."""
    if isinstance(v, list):
        return " | ".join(str(plain(x)) for x in v)
    if hasattr(v, "iso_format"):
        return v.iso_format()
    return v


def run_once(session, code: str) -> tuple[list[str], list[list], float]:
    t = time.perf_counter()
    result = session.run(code, PARAMS)
    records = list(result)
    keys = list(result.keys())
    result.consume()
    return keys, [[plain(r[k]) for k in keys] for r in records], (time.perf_counter() - t) * 1000


def check_pagerank_converged(session, graph: str, settings: str) -> dict:
    """Run gds.pageRank.stats with the same graph and settings as the stream call.

    Stops the script when PageRank did not converge, because then the scores and the
    order of the top 20 still change with more iterations."""
    rec = session.run(f"CALL gds.pageRank.stats('{graph}', {settings}) "
                      "YIELD didConverge, ranIterations "
                      "RETURN didConverge AS converged, ranIterations AS iterations").single()
    if not rec["converged"]:
        raise SystemExit(f"STOP: PageRank on '{graph}' with {settings} did not converge "
                         f"({rec['iterations']} iterations). Raise maxIterations in the .cypher file.")
    return {"name": f"PageRank converged ('{graph}', {settings})", "ok": True,
            "iterations": rec["iterations"]}


def run_statement(session, st: dict, runs: int) -> dict:
    if st["label"] and st["read_only"] and runs > 1:
        run_once(session, st["code"])                    # warm-up, not timed
        times, last = [], None
        for _ in range(runs):
            keys, rows, ms = run_once(session, st["code"])
            times.append(ms)
            last = (keys, rows)
        keys, rows = last
    else:
        keys, rows, ms = run_once(session, st["code"])
        times = [ms]
    return {"df": pd.DataFrame(rows, columns=keys), "times": times}


def check_privacy(df: pd.DataFrame, allowed_names: set[str], where: str) -> None:
    """Stop if a result shows an editor key, or an editor column shows a non-alias."""
    for col in df.columns:
        for v in df[col]:
            if isinstance(v, str) and KEY_RE.match(v):
                raise SystemExit(f"{where}: column {col} shows an editor key. Fix the query.")
        if col in EDITOR_COLUMNS:
            for v in df[col]:
                names = [] if v is None else str(v).split(" | ")
                bad = [n for n in names if n and n not in allowed_names]
                if bad:
                    raise SystemExit(f"{where}: column {col} shows a name that is not an alias.")


def write_safely(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def md_text(header: list[str], label: str, stem: str, df: pd.DataFrame, timing: dict,
            query_file: str) -> str:
    title = header[0] if header else stem
    if label != "main":
        title += f" (result {label})"
    notes = [l.lstrip() for l in header[1:] if l and not l.startswith("Neo4j Browser:")]
    lines = [f"# {title}", "", "\n".join(notes), ""]
    runs = timing["runs"]
    lines.append(f"Rows: {len(df):,}. " + (
        f"Median time: {timing['median_ms']:,.1f} ms ({runs} warm runs after 1 warm-up)."
        if runs > 1 else f"Time: {timing['median_ms']:,.1f} ms (1 run)."))
    lines.append(f"Made by `ec-hw2/queries/run_cypher.py` on "
                 f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC "
                 f"({config.DATA_VERSION}). Query: `queries/cypher/{query_file}`. "
                 f"Full table: `{stem}.csv`.")
    lines += ["", tabulate(df.head(MD_ROWS), headers="keys", tablefmt="github", showindex=False,
                           floatfmt=".6g"), ""]
    if len(df) > MD_ROWS:
        lines.append(f"(first {MD_ROWS} of {len(df):,} rows)")
    return "\n".join(lines) + "\n"


def save_result(q: dict, label: str, out: dict) -> dict:
    stem = output_stem(q["name"], label)
    df = out["df"]
    t = out["times"]
    timing = {"median_ms": statistics.median(t), "min_ms": min(t), "max_ms": max(t), "runs": len(t)}
    write_safely(df.to_csv(index=False), config.RESULTS_DIR / f"{stem}.csv")
    write_safely(md_text(q["header"], label, stem, df, timing, q["path"].name),
                 config.RESULTS_DIR / f"{stem}.md")
    return {"query": q["name"], "result": label, "file": f"{stem}.csv", "result_rows": len(df),
            "median_ms": round(timing["median_ms"], 1), "min_ms": round(timing["min_ms"], 1),
            "max_ms": round(timing["max_ms"], 1), "runs": timing["runs"]}


def run_file(session, q: dict, runs: int, allowed_names: set[str],
             checks: list[dict] | None = None) -> tuple[list[dict], dict]:
    """Run the statements of one file in order. PageRank checks are added to `checks`."""
    print(f"=== {q['name']}", flush=True)
    summary, frames, done = [], {}, set()
    for i, st in enumerate(q["statements"], start=1):
        for call in pagerank_calls(st["code"]):
            if call not in done:          # one check per graph and settings
                c = check_pagerank_converged(session, *call)
                done.add(call)
                print(f"  check: {c['name']}: OK ({c['iterations']} iterations)", flush=True)
                if checks is not None:
                    checks.append(c)
        out = run_statement(session, st, runs)
        if (q["name"], st["label"]) in ADD_RANK:
            out["df"] = with_rank(out["df"])
        if st["label"]:
            check_privacy(out["df"], allowed_names, f"{q['name']} result {st['label']}")
            row = save_result(q, st["label"], out)
            frames[st["label"]] = out["df"]
            summary.append(row)
            print(f"  result {st['label']:14s} {row['result_rows']:>6,} rows  "
                  f"median {row['median_ms']:9.1f} ms ({row['runs']} runs) -> {row['file']}", flush=True)
        else:
            first = out["df"].head(1).to_dict("records")
            print(f"  statement {i}: {out['times'][0]:8.1f} ms  {first[0] if first else ''}", flush=True)
    return summary, frames


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def check_top_contested(cy: pd.DataFrame, path: Path = MONGO_Q2) -> dict | None:
    if not path.exists():
        print(f"  (no {path.name}: skipped the top-contested check)")
        return None
    mongo = pd.read_csv(path)
    a = [(int(p), round(float(s), config.SCORE_ROUND)) for p, s in zip(cy["page_id"], cy["score"])]
    b = [(int(p), round(float(s), config.SCORE_ROUND)) for p, s in zip(mongo["page_id"], mongo["score"])]
    cols = ["edits", "revert_actions", "reverted_editors"]
    same_counts = (len(cy) == len(mongo)
                   and all((cy[c].astype(int).values == mongo[c].astype(int).values).all() for c in cols))
    print("Top contested pages (page_id, score rounded to 6): Cypher | Mongo Q2")
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else (None, float("nan"))
        y = b[i] if i < len(b) else (None, float("nan"))
        print(f"  {i + 1:2d}. {x[0]!s:>10} {x[1]:.6f} | {y[0]!s:>10} {y[1]:.6f}"
              f"{'' if x == y else '   <-- DIFFERENT'}")
    print(f"  same edits, revert_actions and reverted_editors: {'yes' if same_counts else 'NO'}")
    return {"name": "compare_top_contested = Mongo Q2 (same 20 page_ids, scores rounded to 6)",
            "ok": a == b, "same_counts": bool(same_counts)}


def check_mutual(cy: pd.DataFrame, total: pd.DataFrame | None, path: Path = MONGO_MUTUAL) -> list[dict]:
    out = []
    if total is not None and len(total):
        out.append({"name": "Cypher Q1 total = number of Cypher Q1 rows",
                    "ok": int(total["mutual_pairs"].iloc[0]) == len(cy)})
    if not path.exists():
        print(f"  (no {path.name}: skipped the mutual-revert check)")
        return out
    mongo = pd.read_csv(path)
    cols = ["page_id", "editor_a", "editor_b", "a_reverted_b", "b_reverted_a"]
    a = [tuple(r) for r in cy[cols].astype(str).values.tolist()]
    b = [tuple(r) for r in mongo[cols].astype(str).values.tolist()]
    first_diff = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    print(f"Mutual pairs: Cypher {len(a):,} rows | Mongo {len(b):,} rows; "
          + ("identical ordered list" if a == b else f"first difference at row {first_diff}"))
    out.append({"name": "Cypher Q1 = Mongo compare_mutual_reverts (full ordered list)", "ok": a == b,
                "rows": len(a)})
    return out


INTEGRITY = {
    "Editor.reverts_made = sum of outgoing REVERTED.count":
        "MATCH (e:Editor) OPTIONAL MATCH (e)-[r:REVERTED]->() "
        "WITH e, coalesce(sum(r.count), 0) AS s WHERE s <> e.reverts_made RETURN count(e) AS bad",
    "Editor.reverts_received = sum of incoming REVERTED.count":
        "MATCH (e:Editor) OPTIONAL MATCH (e)<-[r:REVERTED]-() "
        "WITH e, coalesce(sum(r.count), 0) AS s WHERE s <> e.reverts_received RETURN count(e) AS bad",
    "Page.revert_actions = distinct reverting_rev_id on its EDITED relationships":
        "MATCH (p:Page) OPTIONAL MATCH (p)<-[e:EDITED]-() "
        "WITH p, count(DISTINCT CASE WHEN e.within_followup AND e.reverted_by_other "
        "THEN e.reverting_rev_id END) AS n WHERE n <> p.revert_actions RETURN count(p) AS bad",
    "values have real types (Page.score FLOAT, EDITED.ts ZONED DATETIME, REVERTED.count INTEGER)":
        "MATCH (p:Page) WHERE p.score IS NOT NULL WITH p LIMIT 1 "
        "MATCH ()-[e:EDITED]->() WITH p, e LIMIT 1 MATCH ()-[r:REVERTED]->() WITH p, e, r LIMIT 1 "
        "RETURN CASE WHEN valueType(p.score) STARTS WITH 'FLOAT' "
        "AND valueType(e.ts) STARTS WITH 'ZONED DATETIME' "
        "AND valueType(r.count) STARTS WITH 'INTEGER' THEN 0 ELSE 1 END AS bad",
}


def check_integrity(session) -> list[dict]:
    out = []
    for name, q in INTEGRITY.items():
        bad = session.run(q).single()["bad"]
        out.append({"name": name, "ok": bad == 0, "bad": bad})
    return out


def check_q3(session, frames: dict) -> list[dict]:
    out = []
    n_editors = session.run("MATCH (e:Editor) RETURN count(e) AS n").single()["n"]
    with_id = session.run("MATCH (e:Editor) WHERE e.communityId IS NOT NULL RETURN count(e) AS n").single()["n"]
    out.append({"name": "Louvain wrote communityId on every Editor", "ok": with_id == n_editors})
    sizes = frames.get("wcc_sizes")
    if sizes is not None:
        out.append({"name": "WCC component sizes add up to all Editor nodes",
                    "ok": int(sizes["editors"].sum()) == n_editors})
    stats, csz = frames.get("louvain_stats"), frames.get("community_sizes")
    if stats is not None and csz is not None and len(stats) and len(csz):
        c = csz.iloc[0]
        out.append({"name": "community_sizes: same total as louvain_stats, and 2+ editors + 1 editor = total",
                    "ok": int(c["communities"]) == int(stats["communities"].iloc[0])
                    and int(c["communities_2plus"]) + int(c["communities_1"]) == int(c["communities"]),
                    "communities": int(c["communities"]), "communities_2plus": int(c["communities_2plus"])})
    return out


def check_aliases(session) -> dict:
    """Every human Editor.alias = the shared pseudonym of its key (ingest/build_documents.py).

    MongoDB and SQL results use the same function, so a graph that was built with an older
    rule (and not exported and loaded again) shows up here. Bots keep their names."""
    from ingest import build_documents as bd   # the shared pseudonym rule
    n_hex = bd.alias_length(bd.all_editor_keys())   # reads the editor keys of both cohorts
    rows = session.run("MATCH (e:Editor) WHERE e.kind <> 'bot' "
                       "RETURN e.key AS key, e.kind AS kind, e.alias AS alias").data()
    bad = [r for r in rows if r["alias"] != bd.public_name(r["kind"], r["key"], None, n_hex)]
    return {"name": "every human Editor.alias = the shared pseudonym (ingest/build_documents.py)",
            "ok": not bad, "editors_checked": len(rows), "different": len(bad)}


# --------------------------------------------------------------------------
# The figure: one edit war, drawn with matplotlib only
# --------------------------------------------------------------------------
def pick_war_page(q4: pd.DataFrame) -> int | None:
    """The page with the most warring editors that is still small enough to draw."""
    small = q4[q4["editors_in_any_revert"] <= FIGURE_MAX_EDITORS]
    if small.empty:
        return None
    small = small.sort_values(["warring_editors", "mutual_pairs", "page_id"],
                              ascending=[False, False, True])
    return int(small["page_id"].iloc[0])


def war_edges(session, page_id: int) -> tuple[str, pd.DataFrame]:
    title = session.run("MATCH (p:Page {id: $id}) RETURN p.title AS t", id=page_id).single()["t"]
    rows = session.run(
        "MATCH (x:Editor)-[r:REVERTED]->(y:Editor) WHERE r.page_id = $id "
        "RETURN x.key AS src_key, x.alias AS src, x.kind AS src_kind, "
        "y.key AS dst_key, y.alias AS dst, y.kind AS dst_kind, r.count AS n "
        "ORDER BY src_key, dst_key", id=page_id).data()
    return title, pd.DataFrame(rows)


def crossings(order: list, pairs: set[frozenset]) -> int:
    """How many pairs of chords cross when the nodes sit on a circle in this order."""
    at = {k: i for i, k in enumerate(order)}
    chords = [tuple(sorted(at[k] for k in p)) for p in pairs]
    n = 0
    for i, (a, b) in enumerate(chords):
        for c, d in chords[i + 1:]:
            if len({a, b, c, d}) == 4 and (a < c < b) != (a < d < b):
                n += 1
    return n


def circle_order(keys: list, pairs: set[frozenset]) -> list:
    """A node order with few crossing arrows: the best of all orders for up to 8 nodes,
    otherwise a greedy order (each next node has the most links to the nodes already placed)."""
    import itertools
    keys = sorted(keys)
    if len(keys) <= 8:
        best, best_n = keys, crossings(keys, pairs)
        for rest in itertools.permutations(keys[1:]):     # the first node is fixed: rotations are equal
            order = [keys[0], *rest]
            n = crossings(order, pairs)
            if n < best_n:
                best, best_n = order, n
        return best
    links = {k: {o for p in pairs if k in p for o in p if o != k} for k in keys}
    order = [max(keys, key=lambda k: (len(links[k]), k))]
    while len(order) < len(keys):
        placed = set(order)
        order.append(max((k for k in keys if k not in placed),
                         key=lambda k: (len(links[k] & placed), len(links[k]), k)))
    return order


def draw_edit_war(title: str, edges: pd.DataFrame, path: Path = FIGURE) -> Path:
    """A circle layout: one node per editor, one arrow per REVERTED relationship."""
    import math

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import FancyArrowPatch

    ink, ink2, muted, surface = "#0b0b0b", "#52514e", "#a3a29d", "#fcfcfb"
    human_c, bot_c = "#2a78d6", "#eb6834"      # categorical slots 1 and 2
    nodes = {}
    for _, r in edges.iterrows():
        nodes[r["src_key"]] = (r["src"], r["src_kind"])
        nodes[r["dst_key"]] = (r["dst"], r["dst_kind"])
    pairs = set(zip(edges["src_key"], edges["dst_key"]))
    # keys only fix the order around the circle; they are never shown
    keys = circle_order(list(nodes), {frozenset(p) for p in pairs})
    n = len(keys)
    pos = {k: (math.cos(math.pi / 2 - 2 * math.pi * i / n), math.sin(math.pi / 2 - 2 * math.pi * i / n))
           for i, k in enumerate(keys)}

    rad = 0.18                                  # how much each arrow bends
    fig, ax = plt.subplots(figsize=(8.5, 8), dpi=150)
    fig.patch.set_facecolor(surface)
    ax.set_facecolor(surface)
    for _, r in edges.iterrows():
        mutual = (r["dst_key"], r["src_key"]) in pairs
        (x1, y1), (x2, y2) = pos[r["src_key"]], pos[r["dst_key"]]
        arrow = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                                connectionstyle=f"arc3,rad={rad}", shrinkA=17, shrinkB=17,
                                color=ink if mutual else muted, lw=2.2 if mutual else 1.4,
                                zorder=2)
        ax.add_patch(arrow)
        # arc3 bends through the control point mid + rad * (dy, -dx); the middle of the
        # curve is half way there, so the count sits on its own arrow
        dx, dy = x2 - x1, y2 - y1
        mx, my = (x1 + x2) / 2 + 0.5 * rad * dy, (y1 + y2) / 2 - 0.5 * rad * dx
        ax.text(mx, my, str(int(r["n"])), ha="center", va="center", fontsize=10,
                color=ink, zorder=4,
                bbox={"boxstyle": "round,pad=0.2", "fc": surface, "ec": "none"})
    for k in keys:
        name, kind = nodes[k]
        x, y = pos[k]
        ax.scatter([x], [y], s=520, color=bot_c if kind == "bot" else human_c,
                   edgecolors=surface, linewidths=2, zorder=3)
        # the label goes outside the circle: to the side for side nodes, above/below otherwise
        if x > 0.35:
            ax.text(x + 0.11, y, name, ha="left", va="center", fontsize=10, color=ink, zorder=4)
        elif x < -0.35:
            ax.text(x - 0.11, y, name, ha="right", va="center", fontsize=10, color=ink, zorder=4)
        else:
            ax.text(x, y + (0.15 if y > 0 else -0.15), name, ha="center",
                    va="bottom" if y > 0 else "top", fontsize=10, color=ink, zorder=4)
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.axis("off")
    shown = title.replace("_", " ")
    fig.suptitle(f"One edit war in the history cohort: who reverted whom on \u201c{shown}\u201d",
                 fontsize=13, color=ink, y=0.97)
    ax.set_title("English Wikipedia, revisions of 2026-09-08 to 2026-09-10 (UTC). "
                 "An arrow A \u2192 B means A reverted B within 20 days.\n"
                 "The number on an arrow is the count of revert actions. "
                 "Human editors are shown by pseudonym; bots keep their names.",
                 fontsize=9, color=ink2, pad=8)
    legend = [Line2D([0], [0], marker="o", color="none", markerfacecolor=human_c, markersize=11,
                     label="human editor (pseudonym)"),
              Line2D([0], [0], marker="o", color="none", markerfacecolor=bot_c, markersize=11,
                     label="bot (real name)"),
              Line2D([0], [0], color=ink, lw=2.2, label="mutual revert (both directions)"),
              Line2D([0], [0], color=muted, lw=1.4, label="one-way revert")]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=2,
              frameon=False, fontsize=9, labelcolor=ink2)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.png")
    fig.savefig(tmp, facecolor=surface, bbox_inches="tight")
    plt.close(fig)
    os.replace(tmp, path)
    return path


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def write_summary(rows: list[dict], checks: list[dict], version: str) -> None:
    df = pd.DataFrame(rows)
    write_safely(df.to_csv(index=False), config.RESULTS_DIR / "cypher_summary.csv")
    ok_text = "; ".join(f"{c['name']}: {'OK' if c['ok'] else 'DIFFERENT'}" for c in checks)
    lines = ["# Neo4j (Cypher) query timings", "",
             f"Target: local Neo4j {version}. Each read-only result ran 7 warm times after 1 warm-up "
             "(unless --runs says otherwise); median_ms is the median of those runs. Statements that "
             "write (gds.louvain.write) ran once. Checks: " + ok_text + ".", "",
             f"Rows: {len(df):,}.",
             f"Made by `ec-hw2/queries/run_cypher.py` on "
             f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC ({config.DATA_VERSION}). "
             "Full table: `cypher_summary.csv`.", "",
             tabulate(df, headers="keys", tablefmt="github", showindex=False, floatfmt=".6g"), ""]
    write_safely("\n".join(lines) + "\n", config.RESULTS_DIR / "cypher_summary.md")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run the Cypher query files and save the results.")
    p.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                   help="timed warm runs for each read-only result (default 7; 1 = no warm-up)")
    p.add_argument("--only", nargs="*", default=None, help="run only these query files (names without .cypher)")
    p.add_argument("--no-figure", action="store_true", help="do not draw the edit-war figure")
    args = p.parse_args(argv)
    t0 = time.time()
    names = args.only or QUERY_FILES
    unknown = [n for n in names if n not in QUERY_FILES]
    if unknown:
        raise SystemExit(f"Unknown query files: {unknown}. Choose from {QUERY_FILES}.")
    queries = [parse_file(CYPHER_DIR / f"{n}.cypher") for n in names]
    for q in queries:
        if q["params"] != PARAMS:
            raise SystemExit(f"{q['name']}: the ':params' line in the header does not match config.py "
                             f"({q['params']} vs {PARAMS}). Update the file header.")
    config.ensure_dirs()

    driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
    driver.verify_connectivity()
    summary, frames, checks, failed = [], {}, [], []
    with driver.session() as session:
        version = session.run("CALL dbms.components() YIELD name, versions "
                              "WHERE name = 'Neo4j Kernel' RETURN versions[0] AS v").single()["v"]
        n_editors = session.run("MATCH (e:Editor) RETURN count(e) AS n").single()["n"]
        if n_editors == 0:
            raise SystemExit("The graph is empty. Run: .venv/bin/python ec-hw2/load_neo4j.py --target local")
        allowed = set(session.run("MATCH (e:Editor) RETURN collect(e.alias) AS a").single()["a"])
        for q in queries:
            try:
                rows, fr = run_file(session, q, args.runs, allowed, checks)
            except Exception as exc:   # report and go on, so one bad file does not hide the others
                print(f"  FAILED: {type(exc).__name__}: {exc}")
                failed.append(q["name"])
                continue
            summary += rows
            frames[q["name"]] = fr
        load_neo4j.drop_our_projections(session)   # in case a file stopped before its drop

        print("=== checks")
        if "compare_top_contested" in frames:
            c = check_top_contested(frames["compare_top_contested"]["main"])
            if c:
                checks.append(c)
        if "q1_mutual_reverts" in frames:
            checks += check_mutual(frames["q1_mutual_reverts"]["main"],
                                   frames["q1_mutual_reverts"].get("total"))
        if "q3_conflict_communities" in frames:
            checks += check_q3(session, frames["q3_conflict_communities"])
        checks += check_integrity(session)
        checks.append(check_aliases(session))
        for c in checks:
            print(f"  {c['name']}: {'OK' if c['ok'] else 'DIFFERENT'}")

        figure = None
        if not args.no_figure and "q4_pages_most_warring_editors" in frames:
            page_id = pick_war_page(frames["q4_pages_most_warring_editors"]["main"])
            if page_id is not None:
                title, edges = war_edges(session, page_id)
                check_privacy(edges[["src", "dst"]].rename(columns={"src": "editor", "dst": "editor_a"}),
                              allowed, "figure")
                figure = draw_edit_war(title, edges)
                print(f"=== figure: {figure} (page {page_id}, {title}, "
                      f"{len(set(edges['src_key']) | set(edges['dst_key']))} editors, {len(edges)} arrows)")
    driver.close()

    if args.only:
        # a partial run must not replace the summary of the full run
        print("=== partial run (--only): cypher_summary.* and _SUCCESS_cypher_queries.json not changed")
        return 1 if failed or not all(c["ok"] for c in checks) else 0
    if summary:
        write_summary(summary, checks, version)
    success = {"step": "cypher_queries", "data_version": config.DATA_VERSION,
               "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "neo4j_version": version, "runs": args.runs,
               "rows": {r["file"]: r["result_rows"] for r in summary},
               "median_ms": {r["file"]: r["median_ms"] for r in summary},
               "checks": checks, "failed_files": failed,
               "figure": str(figure.relative_to(config.HW2_DIR)) if figure else None,
               "seconds": round(time.time() - t0, 1)}
    write_safely(json.dumps(success, indent=2) + "\n", config.RESULTS_DIR / "_SUCCESS_cypher_queries.json")
    print(f"=== summary: {len(summary)} results, {len(failed)} failed files, "
          f"{sum(not c['ok'] for c in checks)} failed checks, {time.time() - t0:.1f} s")
    for r in summary:
        print(f"  {r['file']:52s} {r['result_rows']:>6,} rows {r['median_ms']:>10.1f} ms")
    return 1 if failed or not all(c["ok"] for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
