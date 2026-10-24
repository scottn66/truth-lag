"""Build report/REPORT_SKELETON.md (and .docx) from report/skeleton_template.md.

Purpose
    The skeleton is the frame of the EC HW2 report: the spec section 7 headings,
    and for each heading the owner role, a word target, a facts box, figure files,
    guiding questions and an [OWNER: ...] line. It has NO narrative paragraphs.
    This script fills the placeholders of the template with mechanical content:
      {{built}}                       when it was built and the live status
      {{facts: key, key, ...}}        a facts box from report/FACTS.md (value, unit, status)
      {{figure: path | note}}         an embedded PNG (path relative to report/), or a
                                      "not made yet" line with the note
      {{mongo: name | rows | filter}} a Mongo query block: the pipeline from
                                      queries/mongo/<name>.json + the first result rows
      {{cypher: name | rows}}         a Cypher query block: the code of
                                      queries/cypher/<name>.cypher + the first result rows
      {{timeline: slow|fast}}         the example page timeline (pseudonyms)
      {{decision}}                    the RAG-crawler decision table (notebook 05)
      {{gap_table}}                   the gap table, copied from report/references.md
      {{sample_doc}}                  one history document from results/sample_documents.json
      {{dump_url}}, {{dump_bytes}}    from config.py
    A filter is "col=v1,v2; col2=v3". Then pandoc turns the Markdown into a .docx
    with the PNG figures embedded, for Google Docs.

Inputs
    ec-hw2/report/skeleton_template.md, report/FACTS.md (run build_facts.py first),
    report/references.md, queries/mongo/*.json, queries/cypher/*.cypher,
    results/*.csv, results/sample_documents.json, results/figures/*.png,
    report/figures/architecture.png, data/tables/ (timeline, decision table).

Outputs
    ec-hw2/report/REPORT_SKELETON.md, ec-hw2/report/REPORT_SKELETON.docx and
    ec-hw2/report/_SUCCESS_skeleton.json.

Run (from the repo root; needs pandoc for the .docx; about 5 seconds)
    .venv/bin/python ec-hw2/report/build_facts.py
    .venv/bin/python ec-hw2/report/build_skeleton.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from report import build_facts as bf  # noqa: E402

REPORT = config.HW2_DIR / "report"
TEMPLATE = REPORT / "skeleton_template.md"
OUT_MD = REPORT / "REPORT_SKELETON.md"
OUT_DOCX = REPORT / "REPORT_SKELETON.docx"
SUCCESS = REPORT / "_SUCCESS_skeleton.json"
PLACEHOLDER = re.compile(r"^\{\{\s*(\w+)\s*(?::\s*(.*?))?\s*\}\}\s*$")
INLINE = re.compile(r"\{\{\s*(dump_url|dump_bytes)\s*\}\}")
DRAFT_TAG = "`[drafted by Claude Code; checked by <name>, <date>]`"

_counts = {"facts_boxes": 0, "figures": 0, "figures_missing": 0, "query_blocks": 0}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def md_table(df: pd.DataFrame) -> str:
    """A pipe table that both GitHub and pandoc show; floats get 4 significant digits."""
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = [("" if pd.isna(v) else f"{v:.4g}") for v in df[c]]
    df = df.astype(str).replace({"nan": "", "<NA>": "", "None": ""})
    df = df.apply(lambda col: col.str.replace("|", "/", regex=False))
    return tabulate(df, headers="keys", tablefmt="github", showindex=False, disable_numparse=True)


def apply_filter(df: pd.DataFrame, spec: str | None) -> pd.DataFrame:
    """'col=v1,v2; col2=v3' keeps the rows whose col is v1 or v2 and col2 is v3."""
    if not spec:
        return df
    for part in spec.split(";"):
        col, _, vals = part.strip().partition("=")
        df = df[df[col.strip()].astype(str).isin([v.strip() for v in vals.split(",")])]
    return df


def args_of(text: str | None) -> list[str]:
    return [a.strip() for a in (text or "").split("|")]


# --------------------------------------------------------------------------
# Placeholder renderers
# --------------------------------------------------------------------------
def r_built(_: str | None, facts: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status = bf.live_status()
    return (f"*Built by `ec-hw2/report/build_skeleton.py` on {now} from `report/FACTS.md` "
            f"({config.DATA_VERSION}). Live cohort: **{status}** until "
            f"{config.LIVE_FINAL_AFTER.strftime('%Y-%m-%d %H:%M')} UTC.*")


def r_facts(arg: str, facts: dict) -> str:
    keys = [k.strip() for k in arg.split(",") if k.strip()]
    missing = [k for k in keys if k not in facts]
    if missing:
        raise SystemExit(f"STOP: the template asks for keys that are not in FACTS.md: {missing}")
    rows = [{"key": f"`{k}`", "value": facts[k]["value"], "unit": facts[k]["unit"],
             "status": facts[k]["status"]} for k in keys]
    _counts["facts_boxes"] += 1
    return md_table(pd.DataFrame(rows))


def r_figure(arg: str, facts: dict) -> str:
    a = args_of(arg)
    rel_path, note = a[0], (a[1] if len(a) > 1 else "")
    path = (REPORT / rel_path).resolve()
    shown = bf.rel(path).replace("ec-hw2/", "", 1)
    if path.exists():
        _counts["figures"] += 1
        return (f"![{path.name}]({rel_path})\n\n"
                f"*Figure file: `{shown}`.* [OWNER: write the caption in your own words.]")
    _counts["figures_missing"] += 1
    return f"*Figure not made yet: `{shown}`. {note}*"


def _first_rows(csv_path: Path, n: int, filt: str | None) -> tuple[str, int]:
    df = pd.read_csv(csv_path)
    total = len(df)
    df = apply_filter(df, filt)
    return md_table(df.head(n)), total


def r_mongo(arg: str, facts: dict) -> str:
    from comparison import compare
    a = args_of(arg)
    name, n, filt = a[0], int(a[1]) if len(a) > 1 and a[1] else 8, a[2] if len(a) > 2 else None
    qpath = config.HW2_DIR / "queries" / "mongo" / f"{name}.json"
    spec = json.loads(qpath.read_text(encoding="utf-8"))
    code = compare.json_array_text(qpath.read_text(encoding="utf-8"), "pipeline").strip()
    code = code.split(":", 1)[1].strip() if code.startswith('"pipeline"') else code
    csv = config.RESULTS_DIR / f"mongo_{name}.csv"
    table, total = _first_rows(csv, n, filt)
    title = (config.RESULTS_DIR / f"mongo_{name}.md").read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
    ms_fact = facts.get(f"mongo_ms_{name}", {})
    ms = ms_fact.get("value")
    _counts["query_blocks"] += 1
    shown_rows = f"the first rows{' where ' + filt if filt else ''}"
    return "\n".join([
        f"**{title}**",
        "",
        f"Collection `{spec['collection']}`. File `queries/mongo/{name}.json`."
        + (f" Median time {ms} {ms_fact.get('unit', 'ms')}, local MongoDB." if ms else ""),
        "",
        "```json",
        code,
        "```",
        "",
        f"Result: {shown_rows} (of {total:,} rows in `results/mongo_{name}.csv`):",
        "",
        table,
    ])


def r_cypher(arg: str, facts: dict) -> str:
    from queries import run_cypher
    a = args_of(arg)
    name, n = a[0], int(a[1]) if len(a) > 1 and a[1] else 8
    q = run_cypher.parse_file(config.HW2_DIR / "queries" / "cypher" / f"{name}.cypher")
    code = ";\n\n".join(s["code"].strip() for s in q["statements"]) + ";"
    table, total = _first_rows(config.RESULTS_DIR / f"cypher_{name}.csv", n, None)
    title = (config.RESULTS_DIR / f"cypher_{name}.md").read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
    ms_fact = facts.get(f"cypher_ms_{name}", {})
    ms = ms_fact.get("value")
    _counts["query_blocks"] += 1
    return "\n".join([
        f"**{title}**",
        "",
        f"File `queries/cypher/{name}.cypher` ({len(q['statements'])} statements)."
        + (f" Median time of the main result {ms} {ms_fact.get('unit', 'ms')}, local Neo4j." if ms else ""),
        "",
        "```cypher",
        code,
        "```",
        "",
        f"Result: the first rows (of {total:,} rows in `results/cypher_{name}.csv`):",
        "",
        table,
    ])


def r_timeline(arg: str, facts: dict) -> str:
    pid = bf.EXAMPLE_SLOW_PAGE_ID if arg.strip() == "slow" else bf.EXAMPLE_FAST_PAGE_ID
    tl = bf.page_timeline(pid)
    cols = ["time_utc", "editor", "editor_kind", "size_delta", "is_revert", "reverted_20d",
            "time_to_revert", "reverted_by"]
    return f"Page `{tl['page_title'].iloc[0]}` (page id {pid}):\n\n" + md_table(tl[cols])


def r_decision(_: str | None, facts: dict) -> str:
    return md_table(bf.decision_table_text(bf.decision_table()))


def r_gap_table(_: str | None, facts: dict) -> str:
    lines = (REPORT / "references.md").read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == "## Gap table")
    table = []
    for line in lines[start + 1:]:
        if line.startswith("|"):
            table.append(line)
        elif table:
            break
    if not table:
        raise SystemExit("STOP: no gap table found in report/references.md")
    return "\n".join(table)


def r_sample_doc(_: str | None, facts: dict) -> str:
    doc = json.loads((config.RESULTS_DIR / "sample_documents.json").read_text(encoding="utf-8"))["history"]
    return "```json\n" + json.dumps(doc, indent=2, ensure_ascii=False) + "\n```"


RENDER = {"built": r_built, "facts": r_facts, "figure": r_figure, "mongo": r_mongo, "cypher": r_cypher,
          "timeline": r_timeline, "decision": r_decision, "gap_table": r_gap_table,
          "sample_doc": r_sample_doc}


def build(template: str, facts: dict) -> str:
    out = []
    for line in template.splitlines():
        m = PLACEHOLDER.match(line)
        if m:
            name, arg = m.group(1), m.group(2)
            if name not in RENDER:
                raise SystemExit(f"STOP: unknown placeholder {{{{{name}}}}}")
            out.append(RENDER[name](arg, facts))
            continue
        out.append(INLINE.sub(lambda mm: config.HISTORY_SOURCE_URL if mm.group(1) == "dump_url"
                              else f"{config.HISTORY_SOURCE_BYTES:,}", line))
    text = "\n".join(out) + "\n"
    left = re.findall(r"\{\{.*?\}\}", text)
    if left:
        raise SystemExit(f"STOP: placeholders left in the output: {left[:3]}")
    return text


def write_text_safely(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def make_docx(md_path: Path, docx_path: Path) -> bool:
    """pandoc, run in report/ so the relative image paths resolve and the PNGs are embedded."""
    pandoc = shutil.which("pandoc")
    if not pandoc:
        print("pandoc is not installed: skipped the .docx (brew install pandoc)")
        return False
    tmp = docx_path.with_name(docx_path.stem + ".tmp.docx")
    r = subprocess.run([pandoc, md_path.name, "-f", "gfm", "-t", "docx", "-o", tmp.name,
                        "--resource-path", "."], cwd=md_path.parent, capture_output=True, text=True)
    if r.returncode != 0:
        print("pandoc failed:", r.stderr[-800:])
        return False
    if r.stderr.strip():
        print("pandoc:", r.stderr.strip()[-800:])
    os.replace(tmp, docx_path)
    return True


def main() -> None:
    facts = bf.read_facts()
    text = build(TEMPLATE.read_text(encoding="utf-8"), facts)
    write_text_safely(text, OUT_MD)
    ok = make_docx(OUT_MD, OUT_DOCX)
    headings = [l[3:] for l in text.splitlines() if l.startswith("## ")]
    info = {"step": "skeleton", "data_version": config.DATA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rows": {"REPORT_SKELETON.md lines": text.count("\n"), "headings": len(headings),
                     **_counts}, "docx": ok, "headings": headings}
    write_text_safely(json.dumps(info, indent=2) + "\n", SUCCESS)
    print(f"wrote {bf.rel(OUT_MD)} ({len(headings)} headings, {_counts['facts_boxes']} facts boxes, "
          f"{_counts['query_blocks']} query blocks, {_counts['figures']} figures, "
          f"{_counts['figures_missing']} figures not made yet)")
    if ok:
        print(f"wrote {bf.rel(OUT_DOCX)}")


if __name__ == "__main__":
    main()
