"""Tests for the scale-out part (sharding demo). No database is needed.

The explain() fixtures are small copies of what mongos (MongoDB 8.0.34) really
returned in the demo, with the same field names: queryPlanner.winningPlan.stage =
SINGLE_SHARD / SHARD_MERGE, executionStats.executionStages.shards[], and for an
aggregate: mergeType, splitPipeline.shardsPart / mergerPart, shards{}.

Run (from the repo root)
    .venv/bin/python -m pytest ec-hw2/tests/test_scaleout.py -q
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")   # PyYAML comes with jupyter; skip if it is missing

HW2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW2))
sys.path.insert(0, str(HW2 / "scaleout"))
import demo_sharding as ds  # noqa: E402

COMPOSE = HW2 / "scaleout" / "docker-compose.sharded.yml"
INIT = HW2 / "scaleout" / "init_sharded.sh"


# --------------------------------------------------------------------------
# Fixtures: explain() output in the real shape
# --------------------------------------------------------------------------
def ixscan(index):
    return {"stage": "IXSCAN", "indexName": index, "keyPattern": {"page.id": 1, "ts": 1}}


def find_explain(stage, shards):
    """shards: {name: (n_returned, docs_examined, winning plan)}"""
    return {
        "queryPlanner": {"mongosPlannerVersion": 1, "winningPlan": {
            "stage": stage,
            "shards": [{"shardName": n, "winningPlan": plan} for n, (_, _, plan) in shards.items()]}},
        "executionStats": {
            "nReturned": sum(v[0] for v in shards.values()),
            "executionStages": {"stage": stage, "shards": [
                {"shardName": n, "nReturned": r, "totalDocsExamined": d, "totalKeysExamined": d}
                for n, (r, d, _) in shards.items()]}},
    }


def pushed_down_shard(n_groups, docs, plan):
    """A shard part where the whole $group was pushed into the query layer (8.0)."""
    return {"host": "x:27018", "queryPlanner": {"winningPlan": {"isCached": False, "queryPlan": plan}},
            "executionStats": {"nReturned": n_groups, "totalDocsExamined": docs}}


SINGLE = find_explain("SINGLE_SHARD", {
    "shard2rs": (261, 261, {"stage": "FETCH", "inputStage": ixscan("page.id_1_ts_1")})})
MERGE = find_explain("SHARD_MERGE", {
    "shard1rs": (4307, 4307, {"stage": "SHARDING_FILTER", "inputStage": {
        "stage": "FETCH", "inputStage": ixscan("user.id_1")}}),
    "shard2rs": (4328, 4328, {"stage": "SHARDING_FILTER", "inputStage": {
        "stage": "FETCH", "inputStage": ixscan("user.id_1")}}),
})
GROUP_PLAN = {"stage": "GROUP", "inputStage": {"stage": "SHARDING_FILTER",
                                              "inputStage": {"stage": "COLLSCAN"}}}
AGG = {
    "mergeType": "mongos",
    "splitPipeline": {"shardsPart": [{"$group": {"_id": "$page.id"}}],
                      "mergerPart": [{"$mergeCursors": {}}, {"$group": {}}, {"$sort": {}}]},
    "shards": {"shard1rs": pushed_down_shard(82772, 147462, GROUP_PLAN),
               "shard2rs": pushed_down_shard(82643, 147554, GROUP_PLAN)},
}


# --------------------------------------------------------------------------
# Reading explain() output
# --------------------------------------------------------------------------
def test_plan_stages_classic_sbe_and_branches():
    assert ds.plan_stages({"stage": "FETCH", "inputStage": ixscan("a")}) == ["FETCH", "IXSCAN"]
    sbe = {"isCached": False, "queryPlan": GROUP_PLAN}
    assert ds.plan_stages(sbe) == ["GROUP", "SHARDING_FILTER", "COLLSCAN"]
    branch = {"stage": "OR", "inputStages": [ixscan("a"), {"stage": "COLLSCAN"}]}
    assert ds.plan_stages(branch) == ["OR", "(IXSCAN + COLLSCAN)"]
    assert ds.plan_stages({}) == [] and ds.plan_stages(None) == []


def test_plan_index_finds_the_index_or_none():
    assert ds.plan_index({"stage": "FETCH", "inputStage": ixscan("user.id_1")}) == "user.id_1"
    assert ds.plan_index({"queryPlan": GROUP_PLAN}) is None


def test_summarize_find_single_shard():
    s = ds.summarize_find_explain(SINGLE)
    assert s["stage"] == "SINGLE_SHARD" and s["shards"] == ["shard2rs"] and s["n_shards"] == 1
    assert s["n_returned"] == 261
    assert s["per_shard"][0]["plan"] == "FETCH > IXSCAN"
    assert s["per_shard"][0]["index"] == "page.id_1_ts_1"
    assert ds.routing_label(s) == "SINGLE_SHARD"


def test_summarize_find_shard_merge():
    s = ds.summarize_find_explain(MERGE)
    assert s["stage"] == "SHARD_MERGE" and s["shards"] == ["shard1rs", "shard2rs"]
    assert [p["docs_examined"] for p in s["per_shard"]] == [4307, 4328]
    assert s["n_returned"] == 8635


def test_summarize_find_without_execution_stats():
    exp = {"queryPlanner": SINGLE["queryPlanner"]}
    s = ds.summarize_find_explain(exp)
    assert s["n_shards"] == 1 and s["per_shard"][0]["plan"] == "FETCH > IXSCAN"


def test_summarize_agg_pushed_down():
    s = ds.summarize_agg_explain(AGG)
    assert s["merge_type"] == "mongos" and s["n_shards"] == 2
    assert s["shards_part"] == ["$group"]
    assert s["merger_part"] == ["$mergeCursors", "$group", "$sort"]
    assert [p["n_returned"] for p in s["per_shard"]] == [82772, 82643]
    assert s["per_shard"][0]["plan"] == "GROUP > SHARDING_FILTER > COLLSCAN"
    assert ds.routing_label(s) == "both shards, merged by mongos"


def test_summarize_agg_with_cursor_stage_on_one_shard():
    """The older shape: the shard part is a list of stages that starts with $cursor."""
    exp = {"mergeType": "mongos", "splitPipeline": None, "shards": {"shard1rs": {
        "stages": [{"$cursor": {"queryPlanner": {"winningPlan": {"stage": "COLLSCAN"}},
                                "executionStats": {"nReturned": 7, "totalDocsExamined": 7}}},
                   {"$group": {}}]}}}
    s = ds.summarize_agg_explain(exp)
    assert s["n_shards"] == 1 and s["merger_part"] == [] and s["shards_part"] == []
    assert s["per_shard"][0]["stages"] == ["$cursor", "$group"]
    assert s["per_shard"][0]["plan"] == "COLLSCAN"
    assert s["per_shard"][0]["docs_examined"] == 7
    assert ds.routing_label(s) == "one shard (no merge)"


# --------------------------------------------------------------------------
# Privacy and the results page
# --------------------------------------------------------------------------
def test_example_user_shows_bots_and_hides_humans():
    bot = ds.example_user({"_id": 29639097, "name": "ZackBot", "kind": "bot", "n": 8635})
    assert bot["shown_id"] == 29639097 and "ZackBot" in bot["shown_as"]
    human = ds.example_user({"_id": 12345, "name": "Some Person", "kind": "registered", "n": 9})
    assert human["shown_id"] == ds.HIDDEN
    assert "Some Person" not in human["shown_as"] and "12345" not in human["shown_as"]


def fake_result(user_row, page_ok=True):
    """A result dict in the shape main() builds, from the fixtures above."""
    q_page = {"name": "history of one page", "code": 'db.revisions.find({"page.id": 54168882})',
              "expect": "SINGLE_SHARD", "summary": ds.summarize_find_explain(SINGLE)}
    if not page_ok:
        q_page["summary"] = ds.summarize_find_explain(MERGE)
    user = ds.example_user(user_row)
    queries = [
        q_page,
        {"name": "all edits of one editor", "expect": "SHARD_MERGE",
         "code": f'db.revisions.find({{"user.id": {user["shown_id"]}}})',
         "summary": ds.summarize_find_explain(MERGE)},
        {"name": "a range of page ids", "expect": "SHARD_MERGE", "code": "...",
         "summary": ds.summarize_find_explain(MERGE)},
        {"name": "revert rate by hour of day", "expect": "both shards", "code": "...",
         "summary": {**ds.summarize_agg_explain(AGG), "n_returned": 24}},
        {"name": "the 20 pages with the most revisions", "expect": "both shards", "code": "...",
         "summary": {**ds.summarize_agg_explain(AGG), "n_returned": 20}},
    ]
    for q in queries:
        q["label"] = ds.routing_label(q["summary"])
        q["ok"] = q["label"] == q["expect"] or (q["expect"] == "both shards"
                                                and q["summary"]["n_shards"] == 2)
    return {
        "created_at_text": "2026-10-24 08:00 UTC", "data_version": "data-v1",
        "mongo_version": "8.0.34", "limit": None, "batch": 5000, "copied": 295016,
        "copy_seconds": 3.4, "source_count": 295016,
        "indexes": ["_id_", "page.id_hashed", "page.id_1_ts_1"],
        "shards": [{"id": "shard1rs", "host": "shard1rs/shard1:27018"},
                   {"id": "shard2rs", "host": "shard2rs/shard2:27018"}],
        "distribution": [
            {"shard": "shard1rs", "owned_docs": 147462, "owned_mb": 91.3, "orphaned_docs": 0},
            {"shard": "shard2rs", "owned_docs": 147554, "owned_mb": 91.3, "orphaned_docs": 0}],
        "collstats": [{"shard": "shard1rs", "count": 147462, "data_mb": 91.3, "storage_mb": 30.0,
                       "index_mb": 13.5}],
        "chunks": {"shard1rs": 1, "shard2rs": 1}, "distinct_pages": 165415,
        "examples": {"page": {"id": 54168882, "title": "List_of_2018_albums", "revisions": 261},
                     "user": user},
        "queries": queries,
        "checks": [{"name": "a check", "ok": True, "detail": "fine"}],
    }


def test_render_markdown_has_numbers_and_stage_names():
    md = ds.render_markdown(fake_result({"_id": 29639097, "name": "ZackBot", "kind": "bot",
                                         "n": 8635}))
    for text in ("SINGLE_SHARD", "SHARD_MERGE", "147,462", "49.98%", "List_of_2018_albums",
                 "ZackBot", "82,772 + 82,643 = 165,415", "no page is split", "$mergeCursors",
                 "OK: a check", '{"page.id": "hashed"}'):
        assert text in md, text


def test_render_markdown_never_shows_a_human_editor():
    md = ds.render_markdown(fake_result({"_id": 777001, "name": "Jane Example",
                                         "kind": "registered", "n": 50}))
    assert "Jane Example" not in md and "777001" not in md
    assert ds.HIDDEN in md and "name and id hidden" in md


def test_render_markdown_says_when_routing_is_not_as_expected():
    md = ds.render_markdown(fake_result({"_id": 1, "name": "XBot", "kind": "bot", "n": 5},
                                        page_ok=False))
    assert "We expected SINGLE_SHARD for 'history of one page'" in md


def test_write_text_safely_leaves_no_tmp(tmp_path):
    out = tmp_path / "sub" / "sharding.md"
    ds.write_text_safely(out, "hello\n")
    ds.write_text_safely(out, "again\n")
    assert out.read_text() == "again\n"
    assert not list(out.parent.glob("*.tmp"))


def test_connect_mongos_refuses_a_plain_mongod(monkeypatch):
    """The script drops a database, so it must stop if the URI is not a mongos."""
    class Admin:
        def command(self, name, *a, **k):
            return {"isWritablePrimary": True} if name == "hello" else {}

    class Client:
        admin = Admin()

    monkeypatch.setattr(ds.load_mongo, "connect", lambda uri, timeout_ms=5000: Client())
    with pytest.raises(SystemExit, match="not a mongos"):
        ds.connect_mongos()


def test_connect_mongos_needs_two_shards(monkeypatch):
    class Admin:
        def command(self, name, *a, **k):
            if name == "hello":
                return {"msg": "isdbgrid"}
            return {"shards": [{"_id": "shard1rs", "host": "shard1rs/shard1:27018"}]}

    class Client:
        admin = Admin()

    monkeypatch.setattr(ds.load_mongo, "connect", lambda uri, timeout_ms=5000: Client())
    with pytest.raises(SystemExit, match="needs 2"):
        ds.connect_mongos()


# --------------------------------------------------------------------------
# The compose file and the init script
# --------------------------------------------------------------------------
def test_compose_file_matches_the_plan():
    c = yaml.safe_load(COMPOSE.read_text())
    assert c["name"] == "truthlag-sharded"
    sv = c["services"]
    assert set(sv) == {"cfg", "shard1", "shard2", "mongos"}
    for name in sv:
        assert sv[name]["image"] == "mongo:8.0"
    cfg = sv["cfg"]["command"]
    assert "--configsvr" in cfg and cfg[cfg.index("--replSet") + 1] == "cfgrs"
    assert cfg[cfg.index("--port") + 1] == "27019"
    for name, rs in (("shard1", "shard1rs"), ("shard2", "shard2rs")):
        cmd = sv[name]["command"]
        assert "--shardsvr" in cmd and cmd[cmd.index("--replSet") + 1] == rs
        assert cmd[cmd.index("--port") + 1] == "27018"
        assert "ports" not in sv[name]        # shards are reachable only inside Docker
    for name in ("cfg", "shard1", "shard2"):
        cmd = sv[name]["command"]
        assert cmd[cmd.index("--wiredTigerCacheSizeGB") + 1] == "0.25"
        assert sv[name]["mem_limit"] == "600m"
    m = sv["mongos"]
    assert m["command"][0] == "mongos" and "cfgrs/cfg:27019" in m["command"]
    assert m["ports"] == ["127.0.0.1:27020:27017"] and m["mem_limit"] == "256m"
    assert set(c["volumes"]) == {"cfg_data", "shard1_data", "shard2_data"}
    # the main project's volumes are never used here
    text = COMPOSE.read_text()
    assert "mongo_data" not in text and "neo4j_data" not in text


def test_sharded_port_matches_config():
    assert ds.config.SHARDED_URI.endswith(":27020") or "27020" in ds.config.SHARDED_URI


def test_init_script_syntax_and_safe_rerun_steps():
    subprocess.run(["bash", "-n", str(INIT)], check=True)
    text = INIT.read_text()
    assert "set -euo pipefail" in text
    assert "NotYetInitialized" in text          # rs.initiate only when not started yet
    assert "configsvr: true" in text
    assert "isWritablePrimary" in text          # waits for a primary
    assert "listShards" in text and "sh.addShard" in text   # addShard only when missing
    assert text.count("init_replset ") >= 3 and text.count("add_shard ") >= 2
    assert "down -v" not in text.replace('Never run "down -v"', "")
