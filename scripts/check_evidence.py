"""Check docs/final/RUBRIC_EVIDENCE.md (rows in the order of the Canvas rubric, docs/final/CANVAS_SPEC.md).

A row whose command cell says TODO is OPEN: its evidence is a person's to supply or it is judged live. Open rows are
listed and counted, never passed. Every other row must have a runnable command and an output file that exist, and
its notebooks (if any; the cell may say n/a) must be executed and have a .py copy. Exit 0 only when no checked row fails.

For each row of the "Evidence table":
  command   every command in backticks must name something that exists: the module after `python -m` (as a file),
            a script path (.py, .sh), or git. At least one command per row.
  output    every path in backticks must exist. At least one per row.
  notebook  every .ipynb must exist, hold at least one executed code cell, and have a .py copy next to it.

Run (on the Mac, where data/lake is)
    .venv-lake/bin/python scripts/check_evidence.py
In a clone without the data, outputs under data/ and dist/ cannot exist; pass --allow-missing-data to list them
as "not on this machine" instead of failing.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "final" / "RUBRIC_EVIDENCE.md"
CODE = re.compile(r"`([^`]+)`")


def command_targets(cmd: str) -> tuple[list[Path], str | None]:
    """Files a command needs. Returns (paths, error)."""
    parts = cmd.split()
    if not parts:
        return [], "empty command"
    if parts[0] == "git":
        return [], None if shutil.which("git") else "git not found"
    targets: list[Path] = []
    if "-m" in parts:
        mod = parts[parts.index("-m") + 1]
        if mod != "pytest":
            targets.append(REPO / (mod.replace(".", "/") + ".py"))
    for p in parts[1:]:
        if re.search(r"\.(py|sh|ipynb|sql)$", p) or (p.startswith(("tests_lake", "ec-hw2/tests")) and "/" in p or p == "tests_lake"):
            targets.append(REPO / p)
    if not targets:
        return [], "no script, module or path found in the command"
    return targets, None


def notebook_ok(path: Path) -> str | None:
    if not path.exists():
        return "missing"
    nb = json.loads(path.read_text())
    code = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    if not any(c.get("outputs") or c.get("execution_count") for c in code):
        return "not executed (no outputs)"
    if not path.with_suffix(".py").exists():
        return "no .py copy"
    return None


def main() -> int:
    allow = "--allow-missing-data" in sys.argv
    rows, in_table = [], False
    for line in DOC.read_text().splitlines():
        if line.startswith("## "):
            in_table = line.strip().lower() == "## evidence table"
            continue
        if in_table and line.startswith("|") and not re.match(r"^\|\s*(#|---)", line):
            cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
            if len(cells) == 5:
                rows.append(cells)
    if not rows:
        print("no rows found in the Evidence table")
        return 1
    failures = 0
    open_rows = []
    for num, line, cmds, outs, nbs in rows:
        problems, notes = [], []
        if "TODO" in cmds:
            open_rows.append(num)
            print(f"OPEN {num:>2}  {line[:70]}  (needs a person)")
            continue
        commands = CODE.findall(cmds)
        if not commands:
            problems.append("no command")
        for c in commands:
            targets, err = command_targets(c)
            if err:
                problems.append(f"command `{c}`: {err}")
            for t in targets:
                if not t.exists():
                    problems.append(f"command `{c}`: {t.relative_to(REPO)} does not exist")
        outputs = CODE.findall(outs)
        if not outputs:
            problems.append("no output file")
        for o in outputs:
            if not (REPO / o).exists():
                if allow and o.startswith(("data/", "dist/")):
                    notes.append(f"{o} not on this machine")
                else:
                    problems.append(f"output {o} does not exist")
        notebooks = [n for n in CODE.findall(nbs) if n.endswith(".ipynb")]
        if not notebooks and nbs.strip().lower() != "n/a":
            problems.append("no notebook (write n/a if none fits)")
        for n in notebooks:
            err = notebook_ok(REPO / n)
            if err:
                problems.append(f"notebook {n}: {err}")
        status = "FAIL" if problems else "ok  "
        print(f"{status} {num:>2}  {line[:70]}  ({len(commands)} commands, {len(outputs)} outputs, {len(notebooks)} notebooks)")
        for p in problems:
            print(f"        - {p}")
        for n in notes:
            print(f"        ~ {n}")
        failures += bool(problems)
    print(f"{len(rows)} rubric lines: {len(rows) - len(open_rows) - failures} checked ok, "
          f"{len(open_rows)} open (need a person), {failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
