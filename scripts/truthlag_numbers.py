"""Shared helpers for the number checks: load results.json, format a fact, render a template, find number tokens.

A fact is a named value in docs/final/results.json ("facts" or "constants"). Report text may show a number only
when a fact renders to it. Templates name facts as {{key}} or {{key|format}}; formats:
    (none)   int -> 17,818 ; float -> as stored ; text -> as is
    .Nf      N decimals                    {{el.live.stream.w1h.e_l|.4f}}  -> 0.4205
    pctN     value * 100 with N decimals   {{el.live.stream.w1h.share_known|pct2}} -> 57.95
    raw      no thousands separator
"""
from __future__ import annotations

import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "docs" / "final" / "results.json"
TEMPLATE = REPO / "docs" / "final" / "report_draft.template.md"
DRAFT = REPO / "docs" / "final" / "report_draft.md"
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*(?:\|\s*([A-Za-z0-9_.,]+)\s*)?\}\}")


def load_results(path: Path = RESULTS) -> dict:
    return json.loads(Path(path).read_text())


def all_values(results: dict) -> dict:
    """key -> value over facts and constants."""
    return {**results.get("constants", {}), **results.get("facts", {})}


def _q(value, decimals: int) -> str:
    return str(Decimal(repr(float(value))).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP))


def fmt(value, spec: str | None = None) -> str:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return str(value)
    if spec is None:
        return f"{value:,}" if isinstance(value, int) else repr(value)
    if spec == "raw":
        return str(value)
    m = re.fullmatch(r"\.(\d+)f", spec)
    if m:
        s = _q(value, int(m.group(1)))
        whole, _, frac = s.partition(".")
        sign = "-" if whole.startswith("-") else ""
        whole = f"{int(whole.lstrip('-') or 0):,}"
        return sign + whole + ("." + frac if frac else "")
    m = re.fullmatch(r"pct(\d+)", spec)
    if m:
        return _q(float(value) * 100, int(m.group(1)))
    raise ValueError(f"unknown format {spec!r}")


def render(template_text: str, results: dict) -> tuple[str, list[str]]:
    """Fill {{key|format}} placeholders. Returns (text, missing keys)."""
    values, missing = all_values(results), []

    def sub(m):
        key, spec = m.group(1), m.group(2)
        if key.startswith("meta."):
            return str(results["meta"].get(key[5:], f"<<MISSING {key}>>"))
        if key not in values:
            missing.append(key)
            return f"<<MISSING {key}>>"
        return fmt(values[key], spec)

    return PLACEHOLDER.sub(sub, template_text), missing


# ---------------------------------------------------------------------------- number tokens in free text
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
STRIP = [
    (re.compile(r"`[^`\n]*`"), " "),                                             # code spans: file names, commands, table names
    (re.compile(r"!\[[^\]]*\]\([^)]*\)|\]\([^)]*\)"), " "),                      # image and link targets
    (re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]"), " "),                            # citations [3], [4, 5]
    (re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z?)?"), " "),   # ISO dates and timestamps
    (re.compile(r"\b20\d{2}-\d{2}\b"), " "),                                     # snapshot ids such as 2026-10
    (re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:UTC|PT|AM|PM|GMT)?"), " "),     # clock times
    (re.compile(rf"\b{MONTH}\s+20\d{{2}}\b"), " "),                              # October 2026
    (re.compile(rf"\b{MONTH}\s+\d{{1,2}}(?!\d)(?:\s*(?:–|-|to|and)\s*(?:{MONTH}\s+)?\d{{1,2}}(?!\d))?(?:,?\s+20\d{{2}})?"), " "),  # Oct 20-22, Nov 8, 2026
    (re.compile(r"(?m)^#+\s*(?:Appendix\s+)?[A-Z]?\.?\d*(?:\.\d+)*\.?\s"), "# "),   # heading numbers
    (re.compile(r"(?m)^\s*\d+[.)]\s"), " "),                                     # numbered list markers
    (re.compile(r"\b(?:Fig\.|Figure|Table|Section|Sec\.|Phase|Step|Appendix|Notebook|notebook|Type|criterion|Criterion|Slide|slide|Page|page)\s+\d+[a-z]?\b"), " "),
    (re.compile(r"\b(?:H|E|D|R|Q)\d{1,2}\b"), " "),                              # H1..H4, E0..E7, D1..D20, R1..R7
    (re.compile(r"\bv\d+\b"), " "),                                              # Delta table versions
    (re.compile(r"\bp\s?(?:50|95)\b|\bE\(\s*\d+\s*(?:h|d|min)\s*\)"), " "),      # p50, p95, E(1 h)
    (re.compile(r"\b(?:blake2b|SHA-256|HMAC-SHA256|UTF-8|ISO 8601|x86|M\d|local\[\d+\]|page_change\.v1|DATA 226|Group 9|EC HW2|ns0|namespace 0)\b"), " "),
]
TOKEN = re.compile(r"(?<![\w.,/])([-+−–]?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(\s?%)?(?![\w]|\.\d|,\d)")


def strip_references(text: str) -> str:
    """Drop the References section (reference years and page numbers are not results)."""
    out, skip, level = [], False, 0
    for line in text.splitlines():
        h = re.match(r"^(#+)\s*(.*)", line)
        if h:
            if skip and len(h.group(1)) <= level:
                skip = False
            if re.match(r"(?i)^(?:[A-Z\d.]+\s+)?references\b", h.group(2).strip()):
                skip, level = True, len(h.group(1))
        if not skip:
            out.append(line)
        else:
            out.append("")
    return "\n".join(out)


def number_tokens(text: str) -> list[dict]:
    """Every number left in the text after dates, citations, identifiers and code spans are removed."""
    text = strip_references(text)
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines, 1):
        clean = line
        for rx, rep in STRIP:
            clean = rx.sub(rep, clean)
        for m in TOKEN.finditer(clean):
            whole, frac = m.group(2).replace(",", ""), m.group(3) or ""
            out.append({"line": i, "text": m.group(0).strip(), "value": float(whole + frac), "decimals": len(frac) - 1 if frac else 0,
                        "percent": bool(m.group(4)), "context": line.strip()[:120]})
    return out


def allowed(results: dict) -> list[tuple[str, float]]:
    return [(k, float(v)) for k, v in all_values(results).items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)]


def matches(token: dict, value: float) -> bool:
    """Does the token show this value (as is, or as a percentage of a 0..1 share), at the token's precision?"""
    d, t = token["decimals"], token["value"]
    for v in (abs(value), abs(value) * 100):
        try:
            if float(_q(v, d)) == t or round(v, d) == t:
                return True
        except Exception:
            pass
    return False


def explain_tokens(text: str, results: dict, limit: int = 3) -> list[dict]:
    """Each number token with the facts it equals (for a person to check that the intended fact is among them)."""
    vals = allowed(results)
    out = []
    for tok in number_tokens(text):
        keys = [k for k, v in vals if matches(tok, v)]
        out.append({**tok, "facts": keys[:limit], "n_facts": len(keys)})
    return out


def unmatched_tokens(text: str, results: dict) -> list[dict]:
    vals = allowed(results)
    bad = []
    for tok in number_tokens(text):
        if not any(matches(tok, v) for _, v in vals):
            bad.append(tok)
    return bad
