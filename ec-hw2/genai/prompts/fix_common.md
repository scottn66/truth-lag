# Common instructions for the fix agents (after the review), 2026-10-24

Tool: Claude Code (claude-opus-5-5), Agent tool. Every fix agent got this text plus its own file `fix_<part>.md`.

```text
You are fixing one part of the Truth Lag EC HW2 project (SJSU DATA 226, Group 9) after an independent review. Repo: /Users/scottnelson/Desktop/226/truth-lag, branch ec-hw2. Work ONLY in the files your part owns (listed in your part's instructions).

Read first: ec-hw2/config.py, ec-hw2/DATA_MODEL.md, ec-hw2/STYLE.md, and the review findings in data/verify/REVIEW_FINDINGS.txt (the sections named in your instructions). Each finding has evidence and a proposed fix; check the evidence yourself before you change code, and choose the smallest correct fix.

Environment: Python 3.12 venv at .venv (run .venv/bin/python from the repo root). MongoDB (mongodb://localhost:27017, db truthlag) and Neo4j (bolt://localhost:7687; credentials via config.py, never print them) run in Docker. Data in data/ (git-ignored). config.py now has ALIAS_SECRET (from ec-hw2/.env) and ALIAS_HEX = 10 for pseudonyms.

Rules:
- No git writes. No package installs. Never "docker compose down -v". Never ssh or rsync. Never open Wikimedia EventStreams. Do not use the "timeout" command (not on macOS).
- Never delete or rewrite data/raw or data/history.
- Do NOT run the full pipeline (the lead will re-run everything in order after all fixes). You MAY run your own scripts on the real data to test your change, and you MUST run the tests for your part: .venv/bin/python -m pytest ec-hw2/tests/<your test files> -q. Update tests when a definition changes on purpose.
- Keep the plain-English style (STYLE.md). Never type a number in docs that FACTS.md will change; name the FACTS key instead (for example "late_reverts_rows in report/FACTS.md").
- If you need a change in a file you do not own, describe it in your final answer under "Requests for other parts" instead of editing it.

Final answer (plain text, short): what you changed (file: one line each), what you tested and the result, any finding you did NOT fix and why, and requests for other parts.
```
