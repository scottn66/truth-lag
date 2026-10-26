"""Light tests for ec-hw2/check_setup.py (the setup check for teammates).

Purpose: check that the script never crashes, never prints a secret, reads the
data files correctly and always ends with exit code 0.
Inputs: tiny synthetic files in a pytest temporary folder. The Parquet fixture
uses columns from DATA_MODEL.md (cohort, rev_id, page_id, ts, reverted).
One test runs the real script once (it may connect to the local databases).
Outputs: none.
Run (from the repo root):
    .venv/bin/python -m pytest ec-hw2/tests/test_check_setup.py -q
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HW2_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW2_DIR))
import check_setup as cs  # noqa: E402
import config  # noqa: E402


def test_python_version_rule():
    assert cs.python_status((3, 12, 13)).status == cs.OK
    assert cs.python_status((3, 11, 9)).status == cs.OK
    assert cs.python_status((3, 13, 1)).status == cs.OK
    old = cs.python_status((3, 10, 14))
    assert old.status == cs.FAIL and "3.12" in old.hint


def test_clean_hides_passwords_and_logins():
    msg = "auth failed for mongodb+srv://reader:pa55word@cluster0.example.net/truthlag\nline two"
    out = cs.clean(msg, secrets=["pa55word"])
    assert "pa55word" not in out
    assert "reader:" not in out
    assert "\n" not in out          # always one line
    assert len(cs.clean("x" * 1000)) <= 220


def test_secrets_from_settings():
    settings = {"NEO4J_PASSWORD": "neo-secret-1", "ATLAS_URI": "mongodb+srv://u:p%40ss@h/x",
                "MONGO_URI": "mongodb://localhost:27017"}
    found = cs.secrets_from(settings)
    assert "neo-secret-1" in found and "p@ss" in found and "p%40ss" in found


def test_env_file_parser(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nMONGO_DB=truthlag\nNEO4J_PASSWORD='abc def'\nATLAS_URI=\n"
                   "export NEO4J_USER=neo4j  # the user\n", encoding="utf-8")
    values = cs.read_env_file(env)
    assert values["MONGO_DB"] == "truthlag"
    assert values["NEO4J_PASSWORD"] == "abc def"
    assert values["ATLAS_URI"] == ""
    assert values["NEO4J_USER"] == "neo4j"
    assert cs.read_env_file(tmp_path / "missing.env") == {}


def _tiny_revisions_table() -> pa.Table:
    ts = [datetime(2026, 9, 8, h, tzinfo=timezone.utc) for h in (1, 2, 3)]
    return pa.table({
        "cohort": ["history"] * 3,
        "rev_id": pa.array([1373793295, 1373793296, 1373793297], pa.int64()),
        "page_id": pa.array([10, 10, 11], pa.int64()),
        "ts": pa.array(ts, pa.timestamp("us", tz="UTC")),
        "reverted": [True, False, False],
    })


def test_data_file_checks(tmp_path):
    good = tmp_path / "history_revisions.parquet"
    pq.write_table(_tiny_revisions_table(), good)
    res = cs.check_data_file(good, "parquet")
    assert res.status == cs.OK and "3 rows" in res.detail

    assert cs.check_data_file(tmp_path / "live_revisions.parquet", "parquet").status == cs.FAIL

    broken = tmp_path / "late_reverts.parquet"
    broken.write_text("<html>Not Found</html>", encoding="utf-8")   # a failed download
    res = cs.check_data_file(broken, "parquet")
    assert res.status == cs.FAIL and "Download it again" in res.hint

    csv = tmp_path / "editors.csv"
    csv.write_text("key,alias,kind\nu:1,editor_7f3a2b1c9d,registered\nu:2,ClueBot NG,bot\n", encoding="utf-8")
    res = cs.check_data_file(csv, "csv")
    assert res.status == cs.OK and "2 rows" in res.detail


def test_sqlite_check(tmp_path):
    db = tmp_path / "truthlag.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE revisions (rev_id INTEGER, page_id INTEGER, ts TEXT)")
    con.execute("INSERT INTO revisions VALUES (1, 10, '2026-09-08T01:00:00+00:00')")
    con.commit()
    con.close()
    res = cs.check_data_file(db, "sqlite")
    assert res.status == cs.FAIL and "revert_links" in res.detail   # one table is missing

    con = sqlite3.connect(db)
    con.execute("CREATE TABLE revert_links (reverted_rev_id INTEGER, reverting_rev_id INTEGER)")
    con.commit()
    con.close()
    res = cs.check_data_file(db, "sqlite")
    assert res.status == cs.OK and "1 rows" in res.detail


def test_data_version(tmp_path):
    assert cs.check_data_version(tmp_path, "data-v1").status == cs.SKIP
    (tmp_path / "DATA_VERSION").write_text("data-v1\n", encoding="utf-8")
    assert cs.check_data_version(tmp_path, "data-v1").status == cs.OK
    res = cs.check_data_version(tmp_path, "data-v2")
    assert res.status == cs.FAIL and "data-v2" in res.detail


def test_a_broken_check_becomes_a_fail_line():
    def broken():
        raise RuntimeError("boom with secret-xyz inside")
    out = cs.run_check("Broken check", broken, secrets=["secret-xyz"])
    assert len(out) == 1 and out[0].status == cs.FAIL
    assert "boom" in out[0].detail and "secret-xyz" not in out[0].detail


def test_atlas_and_neo4j_skip_without_settings():
    settings = {"ATLAS_URI": "", "ATLAS_DB": "truthlag", "COL_REVISIONS": "revisions",
                "NEO4J_PASSWORD": "", "NEO4J_URI": "bolt://localhost:7687", "NEO4J_USER": "neo4j"}
    assert cs.check_atlas(settings).status == cs.SKIP
    assert all(r.status == cs.SKIP for r in cs.check_neo4j(settings))
    settings["ATLAS_URI"] = "mongodb+srv://reader:<password>@cluster0.example.net"
    assert cs.check_atlas(settings).status == cs.SKIP


def test_required_figures_check(tmp_path):
    name, guide, files = cs.REQUIRED_FIGURES[0]
    res = cs.check_required_figures(tmp_path, name, guide, files)
    assert res.status == cs.SKIP                          # missing figures are SKIP, not FAIL
    assert all(f in res.detail for f in files)            # every missing PNG is named
    assert "made by the owner in the ui" in res.hint.lower()
    assert len(cs.clean(res.detail)) == len(res.detail)   # short enough that no name is cut off
    for f in files[:-1]:
        (tmp_path / f).write_bytes(b"\x89PNG")
    res = cs.check_required_figures(tmp_path, name, guide, files)
    assert res.status == cs.SKIP and res.detail.endswith(files[-1])
    (tmp_path / files[-1]).write_bytes(b"\x89PNG")
    assert cs.check_required_figures(tmp_path, name, guide, files).status == cs.OK


def test_required_figures_match_the_guides_and_the_skeleton():
    """Every PNG the check asks for is named in a guide and has a slot in the report skeleton."""
    want = {"atlas_cluster_m0.png", "atlas_indexes.png", "atlas_sample_document.png",
            "atlas_mongo_q1.png", "atlas_mongo_q2.png", "atlas_mongo_q3.png", "atlas_mongo_q4.png",
            "mongo_q5_local.png", "neo4j_schema.png", "neo4j_mutual_reverts.png",
            "neo4j_contested_page.png", "neo4j_largest_community.png",
            "chart_q1_hour_kind.png", "chart_q3_time_to_revert.png"}
    want |= {f"neo4j_cypher_q{i}_table.png" for i in range(1, 6)}
    got = {f for _, _, files in cs.REQUIRED_FIGURES for f in files}
    assert got == want
    guides = " ".join(p.read_text(encoding="utf-8") for p in (HW2_DIR / "guides").glob("*.md"))
    skeleton = (HW2_DIR / "report" / "skeleton_template.md").read_text(encoding="utf-8")
    for f in sorted(got):
        assert f in guides, f"{f} is not named in guides/"
        assert f"{{{{figure: ../results/figures/{f}" in skeleton, f"{f} has no figure slot in the skeleton"


def test_no_shell_commands_in_the_script():
    src = (HW2_DIR / "check_setup.py").read_text(encoding="utf-8")
    for bad in ("subprocess", "os.system", "shell=True", "os.popen"):
        assert bad not in src, f"check_setup.py must not use {bad} (it must work on Windows)"


def test_real_run_exit_0_and_no_secrets():
    """Run the real script once, as a teammate would."""
    proc = subprocess.run([sys.executable, str(HW2_DIR / "check_setup.py")],
                          capture_output=True, text=True, cwd=str(HW2_DIR.parent))
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    lines = [ln for ln in proc.stdout.splitlines() if ln[:5] in ("OK   ", "FAIL ", "SKIP ")]
    assert len(lines) >= 20                       # one line per check
    assert "paste them into the group chat" in out
    secrets = cs.secrets_from({k: getattr(config, k, "") for k in cs.ENV_KEYS})
    leaked = any(s in out for s in secrets if len(s) >= 3)
    assert not leaked, "a secret value appeared in the output"
