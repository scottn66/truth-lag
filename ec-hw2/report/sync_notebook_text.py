"""Copy the numbers of report/FACTS.md into the text of the 5 notebooks.

Purpose
    The summary boxes and the 'You should see' lines of the notebooks must show the
    same numbers as FACTS.md, so they can never drift again. In the markdown cells,
    every number that FACTS.md holds sits inside a fact marker:
        <!--fact:history_revisions-->295,016<!--/fact-->
    The marker is an HTML comment, so Jupyter and GitHub show only the number.
    This script rewrites the value inside every marker with the value in FACTS.md.
      - It changes markdown cells only (never code cells or outputs).
      - A value written in backticks (`PB&J_Otter`) keeps its backticks.
      - A "|" in a value is written as "\\|", so a table row stays a table row.
      - If a marker names a key that FACTS.md does not have, it stops with a clear
        message (notebook, cell, key) and changes no file.
    The notebooks call check_markers() in their last cell. It prints OK or
    DIFFERENT for every marker of that notebook.

Inputs
    ec-hw2/report/FACTS.md (run build_facts.py first), ec-hw2/notebooks/[0-9][0-9]_*.ipynb

Outputs
    The same notebooks, changed in place (written as <name>.tmp, then renamed), only
    when a value changed. One line per notebook: markers found, values changed.

Run (from the repo root; about 1 second)
    .venv/bin/python ec-hw2/report/sync_notebook_text.py
    .venv/bin/python ec-hw2/report/sync_notebook_text.py --check    (changes nothing; exit 1 if a value differs)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import nbformat
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from report import build_facts as bf  # noqa: E402

NOTEBOOK_DIR = config.HW2_DIR / "notebooks"
MARKER = re.compile(r"<!--fact:([A-Za-z0-9_]+)-->(.*?)<!--/fact-->")


def notebooks() -> list[Path]:
    """The 5 notebooks, in order (01_data ... 05_truth_lag)."""
    return sorted(NOTEBOOK_DIR.glob("[0-9][0-9]_*.ipynb"))


def shown_value(fact_value: str, old_text: str) -> str:
    """The text to put inside a marker: the FACTS value, in backticks if the old text had them."""
    v = fact_value.replace("|", "\\|")
    if len(old_text) >= 2 and old_text.startswith("`") and old_text.endswith("`"):
        return f"`{v}`"
    return v


def plain(text: str) -> str:
    """The value inside a marker, without backticks and escapes (to compare with FACTS)."""
    t = text.strip()
    if len(t) >= 2 and t.startswith("`") and t.endswith("`"):
        t = t[1:-1]
    return t.replace("\\|", "|")


def markers(nb) -> list[tuple[int, str, str]]:
    """(cell index, key, text inside the marker) for every marker in the markdown cells."""
    out = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "markdown":
            out += [(i, m.group(1), m.group(2)) for m in MARKER.finditer(cell.source)]
    return out


def sync_notebook(nb, facts: dict) -> tuple[int, int, list[str]]:
    """Rewrite every marker value of one notebook (in memory).

    Returns (markers, values changed, missing keys as 'cell N: key').
    """
    found, changed, missing = 0, 0, []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "markdown":
            continue

        def put(m, i=i):
            nonlocal found, changed
            found += 1
            key, old = m.group(1), m.group(2)
            if key not in facts:
                missing.append(f"cell {i}: {key}")
                return m.group(0)
            new = shown_value(facts[key]["value"], old)
            if new != old:
                changed += 1
            return f"<!--fact:{key}-->{new}<!--/fact-->"

        cell.source = MARKER.sub(put, cell.source)
    return found, changed, missing


def write_safely(nb, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    nbformat.write(nb, str(tmp))
    os.replace(tmp, path)


def sync(paths: list[Path] | None = None, facts_path: Path = bf.FACTS_PATH, write: bool = True) -> dict:
    """Sync the markers of all notebooks. Stops (and writes nothing) if a key is missing."""
    facts = bf.read_facts(facts_path)
    paths = paths or notebooks()
    loaded, report, missing = {}, {}, []
    for p in paths:
        nb = nbformat.read(str(p), as_version=4)
        found, changed, miss = sync_notebook(nb, facts)
        loaded[p] = nb
        report[p.name] = {"markers": found, "changed": changed}
        missing += [f"{p.name} {m}" for m in miss]
    if missing:
        raise SystemExit("STOP: these fact markers name keys that are not in report/FACTS.md "
                         f"(fix the marker or add the key in build_facts.py): {'; '.join(missing)}")
    if write:
        for p, nb in loaded.items():
            if report[p.name]["changed"]:
                write_safely(nb, p)
    return report


def check_markers(path: Path, facts_path: Path = bf.FACTS_PATH) -> pd.DataFrame:
    """For the notebook's last cell: is every number in its text equal to FACTS.md?

    Prints one line per marker (OK or DIFFERENT) and a total line.
    """
    from tabulate import tabulate
    facts = bf.read_facts(facts_path)
    nb = nbformat.read(str(path), as_version=4)
    rows = []
    for i, key, text in markers(nb):
        want = facts.get(key, {}).get("value")
        rows.append({"cell": i, "key": key, "text": plain(text),
                     "FACTS.md": "(missing)" if want is None else want,
                     "result": "OK" if want is not None and plain(text) == want else "DIFFERENT"})
    df = pd.DataFrame(rows, columns=["cell", "key", "text", "FACTS.md", "result"])
    print(f"Numbers in the text of {Path(path).name} (fact markers):")
    print(tabulate(df, headers="keys", tablefmt="github", showindex=False, disable_numparse=True))
    print()
    bad = int((df["result"] != "OK").sum())
    print(f"OK: all {len(df)} numbers in the text match FACTS.md" if bad == 0 else
          f"DIFFERENT: {bad} of {len(df)} numbers in the text do not match FACTS.md "
          "(run report/sync_notebook_text.py)")
    return df


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if a value differs")
    args = ap.parse_args(argv)
    report = sync(write=not args.check)
    for name, r in report.items():
        verb = "differ" if args.check else "changed"
        print(f"{name}: {r['markers']} fact markers, {r['changed']} values {verb}")
    if args.check and any(r["changed"] for r in report.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
