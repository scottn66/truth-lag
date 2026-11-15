"""Fill docs/final/report_draft.template.md from docs/final/results.json and write docs/final/report_draft.md.

Run
    .venv-lake/bin/python scripts/render_report.py
Edit the template, never the draft: scripts/check_numbers.py fails when the draft is not the rendered template.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import truthlag_numbers as tn  # noqa: E402


def main() -> int:
    results = tn.load_results()
    text, missing = tn.render(tn.TEMPLATE.read_text(), results)
    tn.DRAFT.write_text(text)
    print(f"wrote {tn.DRAFT.relative_to(tn.REPO)} ({len(text):,} characters) from results.json at commit {results['meta']['commit_short']}")
    for k in sorted(set(missing)):
        print("MISSING fact:", k)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
