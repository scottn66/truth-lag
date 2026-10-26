"""Tests for the report part: report/build_facts.py, build_skeleton.py, make_figures.py,
sync_notebook_text.py.

Run (from the repo root):
    .venv/bin/python -m pytest ec-hw2/tests/test_report.py -q

The fixtures are tiny made-up tables with the same column names and types as the real
files (data/tables/history_revisions.parquet, late_reverts.parquet,
data/parsed/page_change.parquet, results/mongo_q5_risk_deciles.csv). They are written to
a temporary folder, and the module paths are pointed there, so no test reads or writes
the real data, results or report files. ALIAS_SECRET is set to a test value, so the
pseudonyms do not depend on ec-hw2/.env.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

HW2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW2))
import config  # noqa: E402
from report import build_facts as bf  # noqa: E402
from report import build_skeleton as bs  # noqa: E402
from report import make_figures as mf  # noqa: E402
from report import sync_notebook_text as snt  # noqa: E402
from ingest import build_documents as bd  # noqa: E402

UTC = timezone.utc
N_HEX = config.ALIAS_HEX
TEST_SECRET = "test-secret-for-report-tests"


@pytest.fixture(autouse=True)
def alias_secret(monkeypatch):
    """Every test uses the same known secret, not the one in ec-hw2/.env."""
    monkeypatch.setattr(config, "ALIAS_SECRET", TEST_SECRET)


def alias(key: str) -> str:
    """The shared pseudonym rule (ingest/build_documents.py): keyed HMAC-SHA256, ALIAS_HEX digits."""
    return bd.editor_alias(key)


def test_alias_rule_is_keyed_and_fixed_length(monkeypatch):
    a = alias("u:5")
    assert a.startswith("editor_") and len(a) == len("editor_") + 10
    assert bf.alias_hex() == 10
    monkeypatch.setattr(config, "ALIAS_SECRET", "another-secret")
    assert alias("u:5") != a                     # the alias depends on the secret


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
def history_rows() -> pd.DataFrame:
    """Page 10: a human edit reverted by a bot after 30 s, then a human back-and-forth.
    Page 20: one bot edit (not reverted)."""
    t = lambda h, m, s=0: pd.Timestamp(datetime(2026, 9, 8, h, m, s, tzinfo=UTC))  # noqa: E731
    rows = [
        # rev_id, page_id, ts, user_kind, user_key, user_name, size_delta, is_revert, reverted, T, reverter
        (101, 10, t(1, 0), "temporary", "t:~2026-1", "~2026-1", 12, False, True, 30, ("bot", "u:9", "GoodBot")),
        (102, 10, t(1, 0, 30), "bot", "u:9", "GoodBot", -12, True, False, None, None),
        (103, 10, t(2, 0), "registered", "u:5", "Alice", -17, False, True, 3600, ("registered", "u:6", "Bob")),
        (104, 10, t(3, 0), "registered", "u:6", "Bob", 17, True, True, 7200, ("registered", "u:5", "Alice")),
        (105, 10, t(5, 0), "registered", "u:5", "Alice", -17, True, False, None, None),
        (201, 20, t(4, 0), "bot", "u:9", "GoodBot", 5, False, False, None, None),
    ]
    out = []
    for rid, pid, ts, kind, key, name, sd, is_rev, rv, secs, rver in rows:
        out.append({
            "cohort": "history", "wiki_db": "enwiki", "rev_id": rid, "parent_id": rid - 1, "page_id": pid,
            "page_title": "Example_page" if pid == 10 else "Other_page", "page_ns": 0, "ts": ts,
            "seen_ts": pd.NaT, "hour_utc": ts.hour, "size": 100, "size_delta": sd, "comment": "x",
            "tags": [], "mw_reverted_tag": rv, "mw_reverted_at": pd.NaT, "is_revert": is_rev,
            "revert_method": None, "user_id": int(key[2:]) if key.startswith("u:") else None,
            "user_name": name, "user_kind": kind, "user_key": key, "is_bot": kind == "bot",
            "is_temp": kind == "temporary", "is_anon": kind == "temporary", "edit_count": 10,
            "sha1": "ab", "revert_risk": None, "page_edits_prev_1h": 0, "followup_s": 10**6,
            "reverted": rv, "reverted_any": rv, "secs_to_revert": secs,
            "reverting_rev_id": rid + 1 if rv else None,
            "reverter_key": rver[1] if rver else None, "reverter_name": rver[2] if rver else None,
            "reverter_kind": rver[0] if rver else None, "reverted_by_other": rv,
        })
    df = pd.DataFrame(out)
    for c in ("parent_id", "size", "size_delta", "user_id", "edit_count", "secs_to_revert", "reverting_rev_id"):
        df[c] = df[c].astype("Int64")
    for c in ("cohort", "wiki_db", "page_title", "comment", "revert_method", "user_name", "user_kind",
              "user_key", "sha1", "reverter_key", "reverter_name", "reverter_kind"):
        df[c] = df[c].astype("string")
    df["revert_risk"] = df["revert_risk"].astype("Float64")
    for c in ("ts", "seen_ts", "mw_reverted_at"):
        df[c] = pd.to_datetime(df[c], utc=True).astype("datetime64[ns, UTC]")
    return df


def deciles_frame() -> pd.DataFrame:
    """Two deciles and 'no score', with the columns of results/mongo_q5_risk_deciles.csv."""
    rows = [
        {"group": "decile 1", "decile": 1, "risk_min": 0.0, "risk_max": 0.5, "n": 1000, "n_reverted_4d": 10,
         "revert_rate_4d": 0.01, "median_T_s": 100.0},
        {"group": "decile 2", "decile": 2, "risk_min": 0.5, "risk_max": 1.0, "n": 1000, "n_reverted_4d": 200,
         "revert_rate_4d": 0.2, "median_T_s": 50.0},
        {"group": "no score", "decile": None, "risk_min": None, "risk_max": None, "n": 100, "n_reverted_4d": 0,
         "revert_rate_4d": 0.0, "median_T_s": None},
    ]
    after = {"decile 1": (10, 4, 1), "decile 2": (200, 50, 5), "no score": (0, 0, 0)}
    for r in rows:
        k_now, k_1h, k_1d = after[r["group"]]
        for tag, k in (("now", k_now), ("1h", k_1h), ("1d", k_1d)):
            at_risk = r["n"] - (r["n_reverted_4d"] - k)
            r[f"at_risk_{tag}"] = at_risk
            r[f"reverted_after_{tag}"] = k
            r[f"p_{tag}"] = k / at_risk
            r[f"ci_lo_{tag}"] = max(0.0, k / at_risk - 0.01)
            r[f"ci_hi_{tag}"] = min(1.0, k / at_risk + 0.01)
    return pd.DataFrame(rows)


@pytest.fixture
def tables(tmp_path, monkeypatch):
    """Tiny Parquet tables in a temporary folder; build_facts reads them instead of data/."""
    t, p = tmp_path / "tables", tmp_path / "parsed"
    t.mkdir()
    p.mkdir()
    history_rows().to_parquet(t / "history_revisions.parquet", index=False)
    late = pd.DataFrame({
        "rev_id": [101, 103, 105], "page_id": [10, 10, 10],
        "rev_ts": pd.to_datetime(["2026-09-08 01:00", "2026-09-08 02:00", "2026-09-08 05:00"], utc=True),
        "first_signal_at": pd.to_datetime(["2026-10-21 10:00", "2026-10-21 11:00", "2026-10-21 12:00"], utc=True),
        "via": [["page_change", "tag"], ["page_change"], ["tag"]],
        "class": ["exact", "inexact_undo", "method_unknown"],
        "reverting_rev_id": pd.array([900, 901, None], dtype="Int64"),
        "method": ["rollback", "undo", None], "age_days": [43.4, 43.4, 43.3],
        "age_upper_bound": [False, False, True], "restored_later": [False, False, None],
        "in_history_cohort": [True, True, True]})
    late.to_parquet(t / "late_reverts.parquet", index=False)
    pc = pd.DataFrame({"rev_id": [900, 901], "rev_dt": pd.to_datetime(["2026-10-21", "2026-10-21"], utc=True),
                       "user_id": pd.array([9, None], dtype="Int64"), "user_name": ["GoodBot", "~2026-77"],
                       "is_bot": [True, False], "is_temp": [False, True]})
    pc.to_parquet(p / "page_change.parquet", index=False)
    monkeypatch.setattr(bf, "T", t)
    monkeypatch.setattr(bf, "P", p)
    monkeypatch.setattr(bf, "alias_hex", lambda: N_HEX)
    return t


# --------------------------------------------------------------------------
# build_facts: comparing values, reading and writing FACTS.md
# --------------------------------------------------------------------------
@pytest.mark.parametrize("fact, computed, ok", [
    ("295,016", 295016, True),
    ("295,016", 295017, False),
    ("7.43", 7.4289, True),          # rounded to the decimals that FACTS shows
    ("7.43", 7.4351, False),
    ("+0.59", 0.5897, True),
    ("-1.27", -1.2669, True),
    ("0.928571", 13 / 14, True),
    ("World_Figure_Skating_Championships", "World_Figure_Skating_Championships", True),
    ("PB&J_Otter", "PB&J Otter", False),
    ("yes", True, True),
    ("12 of 12", "12 of 12", True),
])
def test_same_value(fact, computed, ok):
    assert bf.same_value(fact, computed)[0] is ok


def test_number_helpers():
    assert bf.n(295016.4) == "295,016"
    assert bf.pct(0.074289) == "7.43"
    assert bf.pct(0.0059, sign=True) == "+0.59"
    assert bf.dec(1234.56, 1) == "1,234.6"
    assert [bf.hours_text(s) for s in (6, 358, 14452, 200000)] == ["6 s", "6 min", "4.0 h", "2.3 d"]
    assert bf.utc_text("2026-10-23T13:52:21.379000Z") == "2026-10-23T13:52:21Z"


def test_facts_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bf, "live_status", lambda: bf.PROVISIONAL)
    monkeypatch.setattr(bf, "read_json", lambda path: {"newest_meta_dt": "2026-10-23T13:52:21Z"})
    rows = [("s", bf.Fact("a_count", "1,234", "rows", "x.json", bf.FINAL)),
            ("s", bf.Fact("a_title", "A|B", "", "y.csv", bf.FINAL)),
            ("s", bf.Fact("a_rate_pct", "5.95", "%", "z.json", bf.PROVISIONAL))]
    path = tmp_path / "FACTS.md"
    path.write_text(bf.render(rows), encoding="utf-8")
    facts = bf.read_facts(path)
    assert facts["a_count"] == {"value": "1,234", "unit": "rows", "source": "x.json", "status": "FINAL"}
    assert facts["a_title"]["value"] == "A|B"          # a pipe inside a value survives the table
    assert facts["a_rate_pct"]["status"] == "PROVISIONAL"
    df = bf.check({"a_count": 1234, "a_rate_pct": 5.9, "missing_key": 1}, path)
    assert list(df["result"]) == ["OK", "DIFFERENT", "DIFFERENT"]
    assert "DIFFERENT: 2 of 3" in capsys.readouterr().out


def test_render_has_one_table_with_five_columns(monkeypatch):
    monkeypatch.setattr(bf, "live_status", lambda: bf.FINAL)
    monkeypatch.setattr(bf, "read_json", lambda path: {"newest_meta_dt": "2026-10-27T01:00:00Z"})
    text = bf.render([("s", bf.Fact("k", "1", "u", "src", bf.FINAL))])
    header = [l for l in text.splitlines() if l.startswith("| key")]
    assert header == ["| key | value | unit | source file | status |"]


# --------------------------------------------------------------------------
# build_facts: tables for the notebooks
# --------------------------------------------------------------------------
def test_decision_table_shares_and_intervals():
    dt = bf.decision_table(deciles_frame())
    d2 = dt[dt["group"] == "decile 2"].iloc[0]
    # 200 eventual reverts, 50 still to come after 1 h -> 150 visible = 75%
    assert d2["visible_1h_pct"] == pytest.approx(75.0)
    assert d2["visible_1d_pct"] == pytest.approx(100 * 195 / 200)
    assert d2["visible_1h_lo"] < 75.0 < d2["visible_1h_hi"]
    assert d2["later_1h_pct"] == pytest.approx(100 * 50 / (1000 - 150))
    assert "visible_now_pct" not in dt.columns          # a wait of 0 shows nothing by definition
    no = dt[dt["group"] == "no score"].iloc[0]
    assert no["risk_score"] == "none" and pd.isna(no["visible_1h_pct"])
    text = bf.decision_table_text(dt[dt["group"] != "no score"])
    assert text.iloc[1]["visible after 1 h [95% CI]"].startswith("75.0% (")
    assert text.iloc[1]["edits (n)"] == "1,000"


def test_page_timeline_uses_pseudonyms(tables):
    tl = bf.page_timeline(10, N_HEX)
    assert list(tl["time_utc"]) == sorted(tl["time_utc"])          # in time order
    assert len(tl) == 5
    shown = set(tl["editor"]) | set(tl["reverted_by"].dropna())
    assert "Alice" not in shown and "Bob" not in shown and "~2026-1" not in shown
    assert alias("u:5") in shown and alias("t:~2026-1") in shown
    assert "GoodBot" in shown                            # bots keep their real names
    assert tl.loc[0, "time_to_revert"] == "30 s" and tl.loc[2, "time_to_revert"] == "1.0 h"
    s = bf.timeline_summary(tl)
    assert (s["edits"], s["reverted"], s["T_min_s"], s["T_max_s"]) == (5, 3, 30, 7200)
    assert s["first_utc"] == "2026-09-08 01:00 UTC"
    assert s["last_revert_utc"] == "2026-09-08 05:00 UTC"   # 03:00 + 2 h
    assert s["first_steps"].count(";") == 2 and "Alice" not in s["first_steps"]


def test_late_examples_one_per_class(tables):
    ex = bf.late_examples(N_HEX)
    assert list(ex["class"]) == config.LATE_CLASSES
    row = ex.set_index("class")
    assert row.loc["exact", "reverter"] == "GoodBot (bot)"
    assert row.loc["inexact_undo", "reverter"] == f"{alias('t:~2026-77')} (temporary)"
    assert row.loc["method_unknown", "reverter"] == "not known (tag only)"
    assert row.loc["inexact_undo", "author"] == f"{alias('u:5')} (registered)"
    assert not ex.astype(str).apply(lambda c: c.str.contains("Alice|Bob")).any().any()


# --------------------------------------------------------------------------
# build_skeleton
# --------------------------------------------------------------------------
FACTS = {"k_one": {"value": "1,234", "unit": "rows", "source": "x", "status": "FINAL"},
         "k_two": {"value": "5.95", "unit": "%", "source": "y", "status": "PROVISIONAL"}}


def test_skeleton_fills_placeholders(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "REPORT", tmp_path)
    tpl = "\n".join(["## Abstract", "{{facts: k_one, k_two}}", "Dump: {{dump_url}} ({{dump_bytes}} bytes)",
                     "{{figure: missing.png | made in the UI}}", "## Motivation"])
    out = bs.build(tpl, FACTS)
    assert "| `k_one` | 1,234" in out and "PROVISIONAL" in out
    assert config.HISTORY_SOURCE_URL in out and f"{config.HISTORY_SOURCE_BYTES:,}" in out
    assert "Figure not made yet" in out and "made in the UI" in out
    assert "{{" not in out


def test_skeleton_stops_on_unknown_key():
    with pytest.raises(SystemExit):
        bs.build("{{facts: k_one, not_a_key}}", FACTS)
    with pytest.raises(SystemExit):
        bs.build("{{no_such_placeholder}}", FACTS)


def test_skeleton_filter_and_table():
    df = pd.DataFrame({"cohort": ["history", "live", "live"], "wait": ["1 h", "1 h", "1 d"],
                       "share": [0.55661, 0.617, 0.95]})
    f = bs.apply_filter(df, "cohort=live; wait=1 h,2 d")
    assert len(f) == 1 and f.iloc[0]["share"] == 0.617
    table = bs.md_table(pd.DataFrame({"a": ["x|y"], "b": [0.123456]}))
    assert "x/y" in table and "0.1235" in table


def test_template_headings_are_the_spec_headings():
    """The skeleton template keeps the spec section 7 headings, word for word and in order."""
    want = ["Abstract", "Motivation", "Data + links", "Architecture/workflow diagram", "Mongo section",
            "Neo4j section", "Results/insights", "Comparison top 5", "Technical difficulties",
            "Best practices + key learnings", "Criteria map table", "Reuse note", "Mandatory GenAI Q&A"]
    text = (HW2 / "report" / "skeleton_template.md").read_text(encoding="utf-8")
    got = [l[3:].strip() for l in text.splitlines() if l.startswith("## ")]
    assert got == want
    for heading in want:            # every section has an owner line
        block = text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
        assert "Owner" in block, heading


# --------------------------------------------------------------------------
# make_figures
# --------------------------------------------------------------------------
def test_known_by_figure_writes_png(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "FIG", tmp_path)
    monkeypatch.setattr(mf, "live_provisional", lambda: True)
    rows = []
    for cohort in ("history", "live"):
        for kind in ("all", "temporary", "registered"):
            for i, (w, s) in enumerate(config.WAIT_POINTS_S.items()):
                rows.append({"cohort": cohort, "user_kind": kind, "wait": w, "wait_s": s, "n_edits": 100,
                             "n_reverted_4d": 10, "revert_rate_4d": 0.1, "known": i,
                             "share_known": i / (len(config.WAIT_POINTS_S) - 1)})
    path = mf.known_by_figure(pd.DataFrame(rows))
    assert path.exists() and path.read_bytes()[:4] == b"\x89PNG"
    assert not list(tmp_path.glob("*.tmp"))             # the .tmp file was renamed
    assert mf._ROWS["fig_known_by_curves.png"] == len(rows)


def test_risk_decile_figure_writes_png(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "FIG", tmp_path)
    monkeypatch.setattr(mf, "live_provisional", lambda: False)
    path = mf.risk_decile_figure(bf.decision_table(deciles_frame()))
    assert path.exists() and path.stat().st_size > 1000


def test_faster_text_only_from_faster_than():
    cmp = pd.DataFrame({"question": ["q", "q", "q"], "engine": ["MongoDB", "Neo4j", "SQLite"],
                        "faster_than": [None, "", "MongoDB; Neo4j"]})
    assert mf.faster_text(cmp) == ("Faster, because the min-max ranges do not overlap: "
                                   "q: SQLite than MongoDB and Neo4j.")
    cmp["faster_than"] = None
    assert "no engine (the ranges overlap)" in mf.faster_text(cmp)


def comparison_frame(label: str = "final") -> pd.DataFrame:
    rows = []
    for q in ("top contested pages", "mutual reverts"):
        for i, e in enumerate(("MongoDB", "Neo4j", "SQLite")):
            rows.append({"timing_label": label, "question": q, "engine": e, "lines_of_code": 10 + i,
                         "code_chars": 300 + 10 * i, "median_ms": 20.0 + i, "min_ms": 19.0 + i, "max_ms": 25.0 + i,
                         "runs": 21, "rounds": 3, "same_result": "yes", "faster_than": None,
                         "input_note": "pre-aggregated by the loader" if e == "Neo4j" else "raw links"})
    return pd.DataFrame(rows)


def test_comparison_figure_writes_png(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "FIG", tmp_path)
    path = mf.comparison_figure(comparison_frame())
    assert path.exists() and path.read_bytes()[:4] == b"\x89PNG"
    assert mf._ROWS["fig_comparison.png"] == 6


def test_timing_label_text(monkeypatch):
    monkeypatch.setattr(mf, "read_json", lambda path: {"load_average_start": [3.456, 3.5, 3.1]})
    assert mf.timing_label_text("final") == "Timings are labelled 'final'."
    t = mf.timing_label_text("draft")
    assert t.startswith("PROVISIONAL") and "3.46" in t


def test_time_to_revert_figure_three_series(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "FIG", tmp_path)
    monkeypatch.setattr(mf, "live_provisional", lambda: True)
    rows = []
    for cohort, last in (("history", 11), ("history_4d", 8), ("live", 8)):
        for i in range(last):
            lo, hi = config.LAG_GRID_S[i], config.LAG_GRID_S[i + 1]
            rows.append({"cohort": cohort, "bucket": config.LAG_LABELS[i], "bucket_lower_s": lo,
                         "bucket_upper_s": hi, "n": 10, "share": 1 / last, "cum_share": (i + 1) / last})
    path = mf.time_to_revert_figure(pd.DataFrame(rows))
    assert path.exists() and path.stat().st_size > 1000


# --------------------------------------------------------------------------
# build_facts: comparison helpers
# --------------------------------------------------------------------------
@pytest.mark.parametrize("scored_by, draft", [
    ("draft by Claude Code; Comparison+viz owner to re-score", True),
    ("Claude Code", True),
    ("", True),
    (None, True),
    ("Mei Chen, 2026-10-26", False),
])
def test_pain_is_draft(scored_by, draft):
    assert bf.pain_is_draft(scored_by) is draft


# --------------------------------------------------------------------------
# sync_notebook_text
# --------------------------------------------------------------------------
def facts_file(tmp_path, monkeypatch, values: dict) -> Path:
    monkeypatch.setattr(bf, "live_status", lambda: bf.PROVISIONAL)
    monkeypatch.setattr(bf, "read_json", lambda path: {"newest_meta_dt": "2026-10-24T07:59:59Z"})
    rows = [("s", bf.Fact(k, v, "", "x", bf.FINAL)) for k, v in values.items()]
    path = tmp_path / "FACTS.md"
    path.write_text(bf.render(rows), encoding="utf-8")
    return path


def small_notebook(tmp_path) -> Path:
    import nbformat
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_markdown_cell("| **Answer** | <!--fact:k_rows-->1<!--/fact--> rows; top page "
                                      "<!--fact:k_title-->`old`<!--/fact--> |"),
        nbformat.v4.new_code_cell("x = '<!--fact:k_rows-->1<!--/fact-->'   # code cells are not changed"),
        nbformat.v4.new_markdown_cell("Pairs: <!--fact:k_pair-->?<!--/fact-->."),
    ]
    path = tmp_path / "01_test.ipynb"
    nbformat.write(nb, str(path))
    return path


def test_sync_rewrites_markdown_markers_only(tmp_path, monkeypatch, capsys):
    import nbformat
    facts = facts_file(tmp_path, monkeypatch, {"k_rows": "295,016", "k_title": "PB&J_Otter", "k_pair": "a|b"})
    path = small_notebook(tmp_path)
    report = snt.sync([path], facts)
    assert report[path.name] == {"markers": 3, "changed": 3}
    nb = nbformat.read(str(path), as_version=4)
    assert nb.cells[0].source == ("| **Answer** | <!--fact:k_rows-->295,016<!--/fact--> rows; top page "
                                  "<!--fact:k_title-->`PB&J_Otter`<!--/fact--> |")     # backticks kept
    assert "<!--fact:k_rows-->1<!--/fact-->" in nb.cells[1].source                    # code cell unchanged
    assert nb.cells[2].source == "Pairs: <!--fact:k_pair-->a\\|b<!--/fact-->."         # a pipe is escaped
    assert snt.sync([path], facts)[path.name]["changed"] == 0                          # a second run changes nothing
    df = snt.check_markers(path, facts)
    assert list(df["result"]) == ["OK", "OK", "OK"]
    assert "OK: all 3 numbers in the text match FACTS.md" in capsys.readouterr().out


def test_check_markers_finds_a_stale_number(tmp_path, monkeypatch, capsys):
    path = small_notebook(tmp_path)
    facts = facts_file(tmp_path, monkeypatch, {"k_rows": "1", "k_title": "new", "k_pair": "?"})
    df = snt.check_markers(path, facts)
    assert list(df["result"]) == ["OK", "DIFFERENT", "OK"]
    assert "DIFFERENT: 1 of 3" in capsys.readouterr().out


def test_sync_stops_on_a_missing_key_and_writes_nothing(tmp_path, monkeypatch):
    facts = facts_file(tmp_path, monkeypatch, {"k_rows": "295,016", "k_title": "x"})
    path = small_notebook(tmp_path)
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SystemExit, match="k_pair"):
        snt.sync([path], facts)
    assert path.read_text(encoding="utf-8") == before
