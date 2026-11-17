"""Fill the templates (report_draft.template.md, slides_outline.template.md) from docs/final/results.json.

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
    bad = 0
    for template, out in tn.DOCS:
        text, missing = tn.render(template.read_text(), results)
        out.write_text(text)
        print(f"wrote {out.relative_to(tn.REPO)} ({len(text):,} characters) from results.json at commit {results['meta']['commit_short']}")
        for k in sorted(set(missing)):
            print("MISSING fact:", k)
        bad += len(missing)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
