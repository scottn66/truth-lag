"""Check that every number in the report text comes from docs/final/results.json. Exit 0 only with zero mismatches.

Checks
  1. results.json is stamped with a commit that is HEAD or an ancestor of HEAD.
  2. A fresh collection from the lake and the run records equals results.json (skipped with a note when data/lake
     is not on this machine, for example in the submitted bundle).
  3. docs/final/report_draft.md is exactly the template docs/final/report_draft.template.md filled from results.json
     (no placeholder without a fact).
  4. Every number token in report_draft.md, and in any text file given with --text (the report PDF or the slides
     exported to text), equals a fact or constant of results.json at the precision shown. Dates, citations,
     identifiers such as H1 or v3, code spans and the References section are not numbers of the results.
  5. Report only (does not fail): which numbers used in the draft do not also appear in docs/final/RESULTS.md.

Limit of check 4: a number in free text passes when it equals ANY fact at the precision shown, so a wrong number
that happens to equal another fact is not caught (more decimals make this rarer). For text that people typed
(report, slides), also read the listing of  --explain FILE : each number with the facts it matched.

Run
    .venv-lake/bin/python scripts/check_numbers.py [--text report.txt slides.txt] [--no-regen]
Export a PDF or PPTX to text first, for example:  pdftotext -layout report.pdf report.txt
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import truthlag_numbers as tn  # noqa: E402

REPO = tn.REPO


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", nargs="*", default=[], help="extra text files to check (report or slides exported to text)")
    ap.add_argument("--no-regen", action="store_true", help="skip the fresh collection from the lake")
    ap.add_argument("--explain", metavar="FILE", help="list every number of FILE with the facts it matched, then exit")
    args = ap.parse_args()
    if args.explain:
        res = tn.load_results()
        for t in tn.explain_tokens(Path(args.explain).read_text(errors="replace"), res):
            what = ", ".join(t["facts"]) + (f" (+{t['n_facts'] - len(t['facts'])} more)" if t["n_facts"] > len(t["facts"]) else "")
            print(f"{Path(args.explain).name}:{t['line']}: {t['text']:>12}  ->  {what or 'NOT IN results.json'}")
        return 0
    problems = 0
    results = tn.load_results()
    meta = results["meta"]
    print(f"results.json: {len(results['facts'])} facts, {len(results['constants'])} constants, commit {meta['commit_short']}, "
          f"generated {meta['generated_at_utc']}")

    # 1. commit stamp
    r = subprocess.run(["git", "merge-base", "--is-ancestor", meta["commit"], "HEAD"], cwd=REPO, capture_output=True)
    if r.returncode != 0:
        print(f"MISMATCH commit: {meta['commit']} is not HEAD or an ancestor of HEAD")
        problems += 1
    else:
        print("ok  1 commit stamp is HEAD or an ancestor")

    # 2. fresh collection
    if args.no_regen or not (REPO / "data" / "lake" / "_runs").is_dir():
        print("skip 2 fresh collection (no lake on this machine, or --no-regen)")
    else:
        import make_results
        fresh = make_results.collect()
        fresh["tests.passed"] = results["facts"].get("tests.passed")          # the pytest run is not repeated here
        diff = [k for k in sorted(set(fresh) | set(results["facts"])) if fresh.get(k) != results["facts"].get(k)]
        cdiff = [k for k, v in make_results.constants().items() if results["constants"].get(k) != v]
        for k in (diff + cdiff)[:30]:
            print(f"MISMATCH fact {k}: file {results['facts'].get(k, results['constants'].get(k))!r}, fresh {fresh.get(k)!r}")
        problems += len(diff) + len(cdiff)
        print(f"{'ok ' if not diff and not cdiff else 'BAD'} 2 fresh collection: {len(diff) + len(cdiff)} of {len(fresh)} facts differ")

    # 3. the draft is the rendered template
    template = tn.TEMPLATE.read_text()
    rendered, missing = tn.render(template, results)
    for k in sorted(set(missing)):
        print(f"MISMATCH placeholder without a fact: {k}")
    problems += len(set(missing))
    draft = tn.DRAFT.read_text() if tn.DRAFT.exists() else ""
    if draft != rendered:
        print("MISMATCH report_draft.md is not the rendered template (run scripts/render_report.py)")
        problems += 1
    else:
        print(f"ok  3 report_draft.md = template filled from results.json ({len(tn.PLACEHOLDER.findall(template))} placeholders)")

    # 4. number tokens
    for path in [tn.DRAFT, *map(Path, args.text)]:
        text = Path(path).read_text(errors="replace")
        toks = tn.number_tokens(text)
        bad = tn.unmatched_tokens(text, results)
        for b in bad[:60]:
            print(f"MISMATCH {Path(path).name}:{b['line']}: {b['text']!r} is not in results.json   | {b['context']}")
        problems += len(bad)
        print(f"{'ok ' if not bad else 'BAD'} 4 {Path(path).name}: {len(toks)} number tokens, {len(bad)} not in results.json")

    # 5. report only: draft numbers that RESULTS.md does not show
    rmd = (REPO / "docs" / "final" / "RESULTS.md").read_text()
    rtoks = tn.number_tokens(rmd)
    values = tn.all_values(results)
    used = {m.group(1) for m in tn.PLACEHOLDER.finditer(template) if isinstance(values.get(m.group(1)), (int, float))
            and not isinstance(values.get(m.group(1)), bool) and m.group(1) in results["facts"]}
    absent = sorted(k for k in used if not any(tn.matches(t, float(values[k])) for t in rtoks))
    print(f"info 5 facts used in the draft: {len(used)}; not shown in RESULTS.md: {len(absent)}" + (": " + ", ".join(absent[:25]) if absent else ""))

    print(f"{'ZERO MISMATCHES' if problems == 0 else str(problems) + ' MISMATCHES'}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
