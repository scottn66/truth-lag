"""Collect every reportable number into docs/final/results.json, stamped with the commit hash.

Sources: the run records that the etl commands wrote (data/lake/_runs/*.json), the Gold and Silver Delta tables at
their current versions, the export manifest, the timing lines of the build logs, the constants of ec-hw2/config.py
and etl/lake_config.py, a pytest run, and the committed result files of the teammates' analyses (facts named
wanru.* and zhenni.*; see teammates()). Nothing is typed in by hand: a number that is not produced by a command
is not in the file.

Run (lake environment, from the repository root)
    .venv-lake/bin/python scripts/make_results.py            # write docs/final/results.json
    .venv-lake/bin/python scripts/make_results.py --check    # exit 1 when a fresh collection differs from the file
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
os.environ.setdefault("TRUTHLAG_HW2_DIR", str(REPO / "ec-hw2"))

from deltalake import DeltaTable  # noqa: E402

from etl import delta_io, lake_config  # noqa: E402
from etl.hw2 import config  # noqa: E402

LAKE = lake_config.lake_root()
RUNS = LAKE / "_runs"
LOGS = REPO / "data" / "logs" / "lake"
OUT = REPO / "docs" / "final" / "results.json"
WAIT_KEY = {"0": "w0", "1 min": "w1min", "5 min": "w5min", "15 min": "w15min", "1 h": "w1h", "6 h": "w6h",
            "1 d": "w1d", "2 d": "w2d", "4 d": "w4d"}
STREAM_KEY = {config.STREAM_PAGE_CHANGE: "page_change", config.STREAM_REVERT_RISK: "revert_risk", config.STREAM_TAGS: "tags"}


def run(name: str):
    p = RUNS / name
    return json.loads(p.read_text()) if p.exists() else None


def count(table: str, where: str = "") -> int:
    q = "SELECT count(*) AS n FROM t" + (f" WHERE {where}" if where else "")
    return int(delta_io.sql(str(LAKE / table), q).column("n")[0].as_py())


def version(table: str) -> int:
    return DeltaTable(str(LAKE / table)).version()


def real_seconds(log: str) -> float | None:
    p = LOGS / log
    if not p.exists():
        return None
    m = re.findall(r"^\s*([\d.]+) real", p.read_text(errors="replace"), flags=re.M)
    return float(m[-1]) if m else None


def constants() -> dict:
    c = {
        "horizon_days": config.LIVE_FOLLOWUP_DAYS, "horizon_s": config.LIVE_FOLLOWUP_S,
        "history_followup_days": config.HISTORY_FOLLOWUP_DAYS, "wait_points": len(config.WAIT_POINTS_S),
        "h1_threshold_1h_pct": 60, "h1_threshold_48h_pct": 95, "h4_floor_pct": 1,
        "burst_min_edits": 10, "small_group_n": config.RISK_MIN_GROUP_N, "bootstrap_B": 2000, "seed": 226,
        "ci_level_pct": 95, "streams": len(config.STREAM_DIRS), "layers": 3, "engines": 2, "snapshots": 2,
        "gap_min_s": 120, "history_window_days": 3, "live_window_days": 3,
        "live_ext_window_days": (lake_config.LIVE_EXT_WINDOW[1] - lake_config.LIVE_EXT_WINDOW[0]).days,
        "slim_columns": len(config.HISTORY_SLIM_COLUMNS), "dump_columns": 78, "hash_salts": 5,
        "hll_p_small": 10, "hll_p_mid": 12, "hll_p_large": 14, "fm_m_small": 64, "fm_m_mid": 256, "fm_m_large": 1024,
        "dgim_window_s": 3600, "dgim_window_h": 1, "dgim_eval_every_min": 10, "dgim_r_small": 2, "dgim_r_large": 4,
        "dgim_top_pages": 200, "reservoir_k": 10000, "sss_seconds_per_rate": 30, "sss_trigger_s": 1,
        "e5_latency_limit_s": 5, "e5_target_eps": 2500, "team_size": 4, "one": 1, "two": 2, "zero": 0, "hundred": 100,
        "clocks": 4, "el_series": 4, "asof_builds": 3, "h1_wait_long_h": 48, "wait_5": 5, "wait_15": 15, "wait_6": 6,
        "ams_vars_small": 100, "ams_vars_large": 1000, "proposal_horizon_days": 30, "lsh_tables_large": 20,
        "text.history_window": "2026-09-08 to 2026-09-10", "text.live_window": "2026-10-20 to 2026-10-22",
        "text.live_ext_window": "2026-10-20 to 2026-11-08", "text.early_as_of": lake_config.EARLY_AS_OF,
        "text.parity_as_of": lake_config.PARITY_AS_OF, "text.ext_as_of": lake_config.EXT_AS_OF,
    }
    return c


def _notebook_text(path: Path) -> str:
    """All stored text outputs of a committed notebook (the notebook is read, not run)."""
    out = []
    for c in json.loads(path.read_text())["cells"]:
        for o in c.get("outputs", []):
            out.append("".join(o.get("text", [])) or "".join(o.get("data", {}).get("text/plain", [])))
    return "\n".join(out)


def _csv(path: Path) -> list[dict]:
    import csv
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _num(x: str):
    v = float(x)
    return int(v) if v == int(v) and "." not in x and "e" not in x.lower() else v


def teammates() -> dict:
    """Numbers of the teammates' own analyses, read from files they committed. Nothing is recomputed here, and no
    lake number is replaced: the keys are separate (wanru.*, zhenni.*).

    Wanru  Neo4j     ec-hw2/results/cypher_*.csv and the stored output of notebooks/neo4j_history_edit_wars_wanru.ipynb
           MinHash   the stored output of notebooks/lsh_minhash_wanru.ipynb
    Zhenni privacy   notebooks/privacy_zhenni/outputs/k_anonymity/*.csv and outputs/laplace/*
    """
    f: dict = {}
    res = REPO / "ec-hw2" / "results"

    def need(m, what):
        if not m:
            raise SystemExit(f"teammate source changed: cannot find {what}")
        return m

    # ---- Wanru, Neo4j
    t = _notebook_text(REPO / "notebooks" / "neo4j_history_edit_wars_wanru.ipynb")
    for label, key in (("Editor", "editors"), ("Page", "pages"), ("EDITED", "edited_rels"), ("REVERTED", "reverted_rels"),
                       ("contested Page", "contested_pages")):
        f[f"wanru.neo4j.graph.{key}"] = int(need(re.search(rf"\|\s*{label}\s*\|\s*(\d+)\s*\|", t), label).group(1))
    r = _csv(res / "cypher_q1_mutual_reverts_total.csv")[0]
    f["wanru.neo4j.mutual_pairs"], f["wanru.neo4j.mutual_pages"] = int(r["mutual_pairs"]), int(r["pages"])
    f["wanru.neo4j.mutual_editors"], f["wanru.neo4j.mutual_pairs_with_bot"] = int(r["editors"]), int(r["pairs_with_bot"])
    r = _csv(res / "cypher_q3_conflict_communities_louvain_stats.csv")[0]
    f["wanru.neo4j.louvain.communities"], f["wanru.neo4j.louvain.modularity"] = int(r["communities"]), float(r["modularity"])
    f["wanru.neo4j.louvain.editors"] = int(r["editors_written"])
    r = _csv(res / "cypher_q3_conflict_communities_community_sizes.csv")[0]
    f["wanru.neo4j.louvain.communities_2plus"], f["wanru.neo4j.louvain.communities_single"] = int(r["communities_2plus"]), int(r["communities_1"])
    f["wanru.neo4j.louvain.editors_without_revert"] = int(r["editors_without_revert"])
    r = _csv(res / "cypher_q3_conflict_communities.csv")[0]
    f["wanru.neo4j.largest_community.editors"], f["wanru.neo4j.largest_community.reverts"] = int(r["editors"]), int(r["reverts"])
    f["wanru.neo4j.largest_community.bots"] = int(r["bots"])
    f["wanru.neo4j.largest_community.top_reverter_share_pct"] = round(100 * float(r["star_share"]), 1)
    r = _csv(res / "cypher_q4_pages_most_warring_editors.csv")[0]
    for k in ("warring_editors", "mutual_pairs", "editors_in_any_revert", "revert_actions", "edits"):
        f[f"wanru.neo4j.top_page.{k}"] = int(r[k])

    # ---- Wanru, MinHash LSH (numbers printed by her notebook)
    t = _notebook_text(REPO / "notebooks" / "lsh_minhash_wanru.ipynb")
    m = need(re.search(r"edits in the export: (\d+) \| edits kept: (\d+) \| by label: \{0: (\d+), 1: (\d+)\}", t), "lsh edits line")
    f["wanru.lsh.edits_in_export"], f["wanru.lsh.edits_kept"] = int(m.group(1)), int(m.group(2))
    f["wanru.lsh.not_reverted.edits"], f["wanru.lsh.reverted.edits"] = int(m.group(3)), int(m.group(4))
    m = need(re.search(r"distinct texts: (\d+) .*?share their exact text with another edit: (\d+)", t), "lsh texts line")
    f["wanru.lsh.distinct_texts"], f["wanru.lsh.edits_sharing_exact_text"] = int(m.group(1)), int(m.group(2))
    m = need(re.search(r"pairs compared: (\d+) \| exact near-duplicate pairs: (\d+) \| seconds: ([\d.]+)", t), "lsh exact join line")
    f["wanru.lsh.sample_pairs_compared"], f["wanru.lsh.sample_exact_pairs"], f["wanru.lsh.exact_join_seconds"] = int(m.group(1)), int(m.group(2)), float(m.group(3))
    rows = re.findall(r"(?m)^\s*\d+\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", t)
    need(len(rows) >= 5, "lsh recall table")
    for tables, returned, found, recall, agree, secs in rows:
        b = f"wanru.lsh.tables{tables}"
        f[b + ".pairs_returned"], f[b + ".true_pairs_found"] = int(returned), int(found)
        f[b + ".recall_pct"], f[b + ".seconds"] = float(recall), float(secs)
    f["wanru.lsh.sample_texts"] = round((1 + (1 + 8 * f["wanru.lsh.sample_pairs_compared"]) ** 0.5) / 2)
    m = need(re.search(r"near-duplicate pairs among \d+ distinct texts: (\d+) \| seconds: ([\d.]+)", t), "lsh full join line")
    f["wanru.lsh.near_dup_pairs"], f["wanru.lsh.full_join_seconds"] = int(m.group(1)), float(m.group(2))
    m = need(re.search(r"texts with a near-duplicate: (\d+) \| groups: (\d+) \| largest group: (\d+) texts", t), "lsh groups line")
    f["wanru.lsh.texts_with_near_dup"], f["wanru.lsh.groups"], f["wanru.lsh.largest_group_texts"] = (int(x) for x in m.groups())
    for name, key in (("not reverted (label 0)", "not_reverted"), ("reverted (label 1)", "reverted")):
        m = need(re.search(rf"(?m)^{re.escape(name)}\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", t), f"lsh {key} row")
        f[f"wanru.lsh.{key}.exact_dup_pct"], f[f"wanru.lsh.{key}.near_dup_pct"], f[f"wanru.lsh.{key}.reuses_pct"] = (float(x) for x in m.groups()[1:])
    for name in ("by_band", "by_group", "all"):
        m = need(re.search(rf"{name}: human-labeled pairs (\d+) \| same edit pattern (\d+) \| precision ([\d.]+)% "
                           r"\(Wilson 95% interval ([\d.]+) to ([\d.]+)\)", t), f"lsh labels {name}")
        b = f"wanru.lsh.labels.{name}"
        f[b + ".pairs"], f[b + ".same_pattern"] = int(m.group(1)), int(m.group(2))
        f[b + ".precision_pct"], f[b + ".precision_lo"], f[b + ".precision_hi"] = float(m.group(3)), float(m.group(4)), float(m.group(5))

    # ---- Zhenni, privacy
    out = REPO / "notebooks" / "privacy_zhenni" / "outputs"
    tkey = {"kind x date x hour": "grid", "page summary": "page"}
    for r in _csv(out / "k_anonymity" / "k_summary.csv"):
        b = f"zhenni.privacy.{tkey[r['table']]}.k{r['k']}"
        f[f"zhenni.privacy.{tkey[r['table']]}.rows"] = int(r["rows"])
        f[b + ".rows_below"], f[b + ".rows_below_pct"] = int(r["rows_below_k"]), float(r["rows_below_k_pct"])
        f[b + ".edits_below_pct"] = float(r["edits_in_those_rows_pct"])
        f[b + ".edits_kept_pct"] = round(100 - float(r["edits_in_those_rows_pct"]), 2)      # derived: 100 minus the column above
    for r in _csv(out / "k_anonymity" / "l_diversity_summary.csv"):
        b = f"zhenni.privacy.{tkey[r['table']]}.l2"
        f[b + ".two_diverse_pct"], f[b + ".all_reverted_rows"] = float(r["two_diverse_pct"]), int(r["all_reverted_rows"])
        f[b + ".all_reverted_pct"], f[b + ".none_reverted_pct"] = float(r["all_reverted_pct"]), float(r["none_reverted_pct"])
        f[b + ".all_reverted_single_editor"] = int(r["all_reverted_and_single_editor"])
    for r in _csv(out / "k_anonymity" / "suppression_summary.csv"):
        b = f"zhenni.privacy.suppress.{r['cohort']}.rule{r['rule']}"
        for k in ("rows_kept_pct", "edits_kept_pct", "reverts_kept_pct", "true_revert_rate_pct", "released_revert_rate_pct", "bias_points"):
            f[f"{b}.{k}"] = float(r[k])
    for r in _csv(out / "laplace" / "laplace_summary.csv"):
        b = f"zhenni.privacy.laplace.{r['cohort_id']}.{r['label_source']}.{r['user_kind']}"
        f[b + ".n"] = int(r["eventual_reverts"])
        for eps in ("0.1", "0.5", "1.0"):
            f[f"{b}.mae.eps{eps.replace('.', '_')}"] = float(r[f"mae_eps_{eps}"])
            f[f"{b}.p95.eps{eps.replace('.', '_')}"] = float(r[f"p95_eps_{eps}"])
    md = json.loads((out / "laplace" / "laplace_metadata.json").read_text())
    f["zhenni.privacy.laplace.trials"], f["zhenni.privacy.laplace.seed"] = md["trials"], md["seed"]
    f["zhenni.privacy.laplace.epsilons"], f["zhenni.privacy.laplace.series"] = len(md["epsilons"]), len(md["analyzed_series"])
    return f


def lake_check_of_graph() -> dict:
    """The sizes of Wanru's Neo4j graph, recomputed from the lake's Silver tables for the history cohort (same rule as
    the graph: a revert by another editor inside the 20-day follow-up). New keys only; used to compare, not to replace."""
    import pandas as pd
    rev = DeltaTable(str(LAKE / "silver/history_revisions")).to_pandas(columns=["page_id", "user_key"])
    ln = DeltaTable(str(LAKE / "silver/history_revert_links")).to_pandas(columns=["page_id", "author_key", "reverter_key", "by_other", "within_followup"])
    d = ln[(ln.by_other == True) & (ln.within_followup == True)]          # noqa: E712  (nullable booleans)
    g = d.groupby(["page_id", "reverter_key", "author_key"]).size().reset_index(name="n")
    back = g.rename(columns={"reverter_key": "author_key", "author_key": "reverter_key"})
    m = g.merge(back, on=["page_id", "reverter_key", "author_key"])
    m = m[m.reverter_key < m.author_key]
    return {
        "lakecheck.graph.editors": len(set(rev.user_key.dropna()) | set(d.reverter_key.dropna()) | set(d.author_key.dropna())),
        "lakecheck.graph.pages": int(rev.page_id.nunique()),
        "lakecheck.graph.edited_rels": int(rev.user_key.notna().sum()),
        "lakecheck.graph.reverted_rels": int(len(g)),
        "lakecheck.graph.mutual_pairs": int(len(m)), "lakecheck.graph.mutual_pages": int(m.page_id.nunique()),
        "lakecheck.graph.mutual_editors": int(pd.concat([m.reverter_key, m.author_key]).nunique()),
    }


# teammate fact -> the lake or fallback fact that measures the same thing (for the comparison table in RESULTS.md)
def teammate_pairs(facts: dict) -> list[tuple[str, str]]:
    pairs = []
    swap = {"tables1.recall_pct": "recall_pct.tables1", "tables5.recall_pct": "recall_pct.tables5", "tables20.recall_pct": "recall_pct.tables20",
            "tables1.seconds": "seconds.tables1", "tables5.seconds": "seconds.tables5", "tables20.seconds": "seconds.tables20"}
    for k in facts:
        other = None
        if k.startswith("wanru.lsh."):
            tail = k[len("wanru.lsh."):]
            other = "lsh." + swap.get(tail, tail)
        elif k.startswith("wanru.neo4j.graph.") or k.startswith("wanru.neo4j.mutual_"):
            other = "lakecheck.graph." + k.split(".")[-1]
        elif k.startswith("zhenni.privacy.laplace.") and k.endswith(".n"):
            c, src, kind = k.split(".")[3:6]
            other = f"el.{c}.{src}.{kind}.w1h.n_eventual"
        elif k.startswith("zhenni.privacy.laplace.") and ".mae.eps" in k:
            other = k.replace("zhenni.", "").replace("eps0_1", "eps_low").replace("eps0_5", "eps_mid").replace("eps1_0", "eps_high")
        elif k.startswith("zhenni.privacy."):
            other = k.replace("zhenni.", "").replace(".l2.", ".").replace("all_reverted_single_editor", "all_reverted_single_editor")
        if other and other in facts and other != k:
            pairs.append((k, other))
    return pairs


def agree(a, b) -> bool:
    """Equal, or equal once the more precise value is rounded to the decimals of the less precise one."""
    if isinstance(a, int) and isinstance(b, int):
        return a == b
    da, db = (len(repr(float(x)).split(".")[1]) if "e" not in repr(float(x)) else 12 for x in (a, b))
    d = min(da, db)
    return abs(round(float(a), d) - round(float(b), d)) < 10 ** -(d + 3) or abs(float(a) - float(b)) <= 0.5000001 * 10 ** -d


BEGIN, END = "<!-- teammates:begin (written by scripts/make_results.py; do not edit by hand) -->", "<!-- teammates:end -->"


def teammates_md(doc: dict) -> str:
    """The "Teammates' analyses" section of docs/final/RESULTS.md, written from the collected facts."""
    f = doc["facts"]
    n = lambda k: f"{f[k]:,}" if isinstance(f[k], int) else repr(f[k])          # noqa: E731
    L = [BEGIN, "", f"## Teammates' analyses, collected into results.json ({doc['meta']['generated_at_utc']})", "",
         "`python scripts/make_results.py` reads these numbers from files the teammates committed. Nothing is recomputed and no lake "
         "number is replaced: the keys are `wanru.*` and `zhenni.*`. Sources: `ec-hw2/results/cypher_*.csv`, the stored outputs of "
         "`notebooks/neo4j_history_edit_wars_wanru.ipynb` and `notebooks/lsh_minhash_wanru.ipynb`, and "
         "`notebooks/privacy_zhenni/outputs/`.", "",
         "### Wanru: Neo4j graph of the history cohort (20-day follow-up, as in EC HW2)", "",
         "| What | Value | Same number recomputed from the lake's Silver tables |", "| --- | --- | --- |"]
    for label, k in (("Editor nodes", "graph.editors"), ("Page nodes", "graph.pages"), ("EDITED relationships", "graph.edited_rels"),
                     ("REVERTED relationships", "graph.reverted_rels"), ("Mutual-revert pairs", "mutual_pairs"),
                     ("Pages with a mutual-revert pair", "mutual_pages"), ("Editors in mutual-revert pairs", "mutual_editors")):
        L.append(f"| {label} | {n('wanru.neo4j.' + k)} | {n('lakecheck.graph.' + k.split('.')[-1])} |")
    L += ["", "| What | Value |", "| --- | --- |"]
    for label, k in (("Contested pages", "graph.contested_pages"), ("Mutual-revert pairs with a bot", "mutual_pairs_with_bot"),
                     ("Louvain communities", "louvain.communities"), ("Louvain modularity", "louvain.modularity"),
                     ("Communities with two or more editors", "louvain.communities_2plus"), ("Communities of one editor", "louvain.communities_single"),
                     ("Largest community: editors", "largest_community.editors"), ("Largest community: revert actions", "largest_community.reverts"),
                     ("Largest community: bots", "largest_community.bots"),
                     ("Largest community: share of REVERTED relationships that touch its top reverter, %", "largest_community.top_reverter_share_pct"),
                     ("Page with the most warring editors: warring editors", "top_page.warring_editors"),
                     ("Same page: mutual pairs", "top_page.mutual_pairs"), ("Same page: revert actions", "top_page.revert_actions"),
                     ("Same page: edits", "top_page.edits")):
        L.append(f"| {label} | {n('wanru.neo4j.' + k)} |")
    L += ["", "### Wanru: MinHash LSH on edit comments", "", "| What | Value |", "| --- | --- |"]
    for label, k in (("Edits in the export", "edits_in_export"), ("Edits kept", "edits_kept"), ("Distinct cleaned texts", "distinct_texts"),
                     ("Texts in the exact-join sample", "sample_texts"), ("Pairs compared in the exact join", "sample_pairs_compared"),
                     ("True near-duplicate pairs in the sample", "sample_exact_pairs"), ("Exact join, seconds", "exact_join_seconds"),
                     ("Near-duplicate pairs on all texts", "near_dup_pairs"), ("Texts with a near-duplicate", "texts_with_near_dup"),
                     ("Groups", "groups"), ("Largest group, texts", "largest_group_texts"),
                     ("Reverted edits that reuse a summary, %", "reverted.reuses_pct"), ("Not-reverted edits that reuse a summary, %", "not_reverted.reuses_pct"),
                     ("Labeled pairs", "labels.all.pairs"), ("Labeled pairs with the same edit pattern", "labels.all.same_pattern"),
                     ("Precision, %", "labels.all.precision_pct"), ("Precision, Wilson 95% low", "labels.all.precision_lo"),
                     ("Precision, Wilson 95% high", "labels.all.precision_hi"),
                     ("By similarity band: same pattern", "labels.by_band.same_pattern"), ("By group: same pattern", "labels.by_group.same_pattern")):
        L.append(f"| {label} | {n('wanru.lsh.' + k)} |")
    L += ["", "| Hash tables | Pairs returned | True pairs found | Recall, % | Seconds |", "| --- | --- | --- | --- | --- |"]
    for t in sorted({int(k.split(".")[2][6:]) for k in f if k.startswith("wanru.lsh.tables")}):
        b = f"wanru.lsh.tables{t}"
        L.append(f"| {t} | {n(b + '.pairs_returned')} | {n(b + '.true_pairs_found')} | {n(b + '.recall_pct')} | {n(b + '.seconds')} |")
    L += ["", "### Zhenni: k-anonymity, l-diversity, suppression", "",
          "| Table | Rows | k | Rows below k | Rows below k, % | Edits in those rows, % | Edits kept if those rows are dropped, % (100 minus the column before) |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for t, name in (("grid", "kind x date x hour"), ("page", "page summary")):
        for k in (2, 5, 10, 20):
            b = f"zhenni.privacy.{t}.k{k}"
            L.append(f"| {name} | {n(f'zhenni.privacy.{t}.rows')} | {k} | {n(b + '.rows_below')} | {n(b + '.rows_below_pct')} | {n(b + '.edits_below_pct')} | {n(b + '.edits_kept_pct')} |")
    L += ["", "| Table | Rows with both labels, % | Rows with only reverted edits | Those, % | Rows with no reverted edit, % | Only-reverted rows from a single editor |",
          "| --- | --- | --- | --- | --- | --- |"]
    for t, name in (("grid", "kind x date x hour"), ("page", "page summary")):
        b = f"zhenni.privacy.{t}.l2"
        L.append(f"| {name} | {n(b + '.two_diverse_pct')} | {n(b + '.all_reverted_rows')} | {n(b + '.all_reverted_pct')} | {n(b + '.none_reverted_pct')} | {n(b + '.all_reverted_single_editor')} |")
    L += ["", "| Cohort | Rule | Rows kept, % | Edits kept, % | Reverts kept, % | True revert rate, % | Released revert rate, % | Bias, points |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in ("history", "live", "live_ext"):
        for r in "ABC":
            b = f"zhenni.privacy.suppress.{c}.rule{r}"
            L.append(f"| {c} | {r} | " + " | ".join(n(f"{b}.{k}") for k in ("rows_kept_pct", "edits_kept_pct", "reverts_kept_pct", "true_revert_rate_pct",
                                                                         "released_revert_rate_pct", "bias_points")) + " |")
    L += ["", f"### Zhenni: Laplace noise on the E(L) counts ({n('zhenni.privacy.laplace.trials')} trials, seed {n('zhenni.privacy.laplace.seed')})", "",
          "Mean absolute error of E(L) over seven waits, shown to six decimals.", "",
          "| Cohort | Label source | Editor kind | Eventual reverts | MAE at epsilon 0.1 | MAE at epsilon 0.5 | MAE at epsilon 1.0 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    series = sorted({tuple(k.split(".")[3:6]) for k in f if k.startswith("zhenni.privacy.laplace.") and k.endswith(".n")},
                    key=lambda x: -f["zhenni.privacy.laplace." + ".".join(x) + ".n"])
    for c, src, kind in series:
        b = f"zhenni.privacy.laplace.{c}.{src}.{kind}"
        L.append(f"| {c} | {src} | {kind} | {n(b + '.n')} | " + " | ".join(f"{f[f'{b}.mae.eps{e}']:.6f}" for e in ("0_1", "0_5", "1_0")) + " |")
    pairs = teammate_pairs(f)
    bad = [(a, b) for a, b in pairs if not agree(f[a], f[b])]
    L += ["", "### Teammate numbers against the lake and the fallback notebooks", "",
          f"{len(pairs)} teammate numbers have a lake or fallback number that measures the same thing "
          f"(`lsh.*`, `privacy.*`, `el.*.n_eventual`, `lakecheck.graph.*`). Compared at the precision of the less precise of the two: "
          f"{len(pairs) - len(bad)} agree, {len(bad)} disagree."]
    if bad:
        L += ["", "| Teammate fact | Value | Lake or fallback fact | Value |", "| --- | --- | --- | --- |"]
        L += [f"| `{a}` | {n(a)} | `{b}` | {n(b)} |" for a, b in bad]
    L += ["", END]
    return "\n".join(L)


def write_results_md(doc: dict) -> None:
    path = REPO / "docs" / "final" / "RESULTS.md"
    text, block = path.read_text(), teammates_md(doc)
    if BEGIN in text and END in text:
        text = text[:text.index(BEGIN)] + block + text[text.index(END) + len(END):]
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    path.write_text(text)


def collect() -> dict:
    f: dict = {}

    # ---------------- Bronze, Silver, cohorts
    bp = run("bronze_parity.json")
    for s, d in bp.items():
        k = STREAM_KEY[s]
        f[f"bronze.{k}.rows"] = d["bronze_rows"]
        f[f"bronze.{k}.lines_in_published_cut"] = d["bronze_lines_in_cut"]
        f[f"bronze.{k}.lines_published"] = d["lines_published"]
        f[f"bronze.{k}.files_in_published_cut"] = d["files_in_cut"]
        f[f"bronze.{k}.event_dates"] = len(d["bronze_rows_per_day"])
    f["bronze.stream_rows_total"] = sum(d["bronze_rows"] for d in bp.values())
    f["bronze.history_slim.rows"] = count("bronze/history_slim")
    f["bronze.history_full.rows"] = count("bronze/history_full")
    for t in ("page_change", "revert_risk", "tag_events", "capture_gaps", "history_revisions", "history_revert_links",
              "live_ext_revisions", "live_ext_revert_links"):
        f[f"silver.{t}.rows"] = count(f"silver/{t}")
    for snap in ("2026-09", "2026-10"):
        f[f"silver.history_slim.rows.{snap.replace('-', '_')}"] = count("silver/history_slim", f"snapshot = '{snap}'")
    sp = run("silver_parity.json")
    for t, d in sp.items():
        f[f"parity.silver.{t}.rows"] = d["rows_lake"]
        f[f"parity.silver.{t}.rows_published"] = d["rows_ref"]
        f[f"parity.silver.{t}.differences"] = d["only_in_lake"] + d["only_in_ref"] + (0 if d["same_content"] else 1)
    cp = run("cohort_parity.json")
    for t, d in cp.items():
        f[f"parity.cohort.{t}.rows"] = d["rows_lake"]
        f[f"parity.cohort.{t}.differences"] = d["only_in_lake"] + d["only_in_ref"] + (0 if d["same_content"] else 1)
    f["parity.cohort.tables"] = len(cp)
    f["parity.cohort.tables_equal"] = sum(1 for d in cp.values() if d["same_content"])
    f["parity.silver.tables_equal"] = sum(1 for d in sp.values() if d["same_content"])
    f["parity.bronze.streams_equal"] = sum(1 for d in bp.values() if d["match"])

    # ---------------- Gold tables
    gold = ["dim_cohort", "dim_snapshot", "dim_time", "dim_user", "dim_page", "fact_edit", "fact_revert_label",
            "mart_el_curve", "mart_el_by_burst", "mart_label_change", "mart_reconciliation", "recon_mismatch"]
    for t in gold:
        f[f"gold.{t}.rows"] = count(f"gold/{t}")
    f["gold.tables"] = len(gold)
    for c in ("history", "live", "live_ext"):
        f[f"gold.fact_edit.rows.{c}"] = count("gold/fact_edit", f"cohort_id = '{c}'")
    f["gold.dim_page.pages"] = int(delta_io.sql(str(LAKE / "gold/dim_page"), "SELECT count(DISTINCT page_id) AS n FROM t").column("n")[0].as_py())
    for name in ("gold_checks_parity.json", "gold_checks_ext.json"):
        g = run(name)
        k = name.split("_")[2].split(".")[0]
        f[f"gold_checks.{k}.passed"], f[f"gold_checks.{k}.total"] = g["passed"], g["total"]

    el = DeltaTable(str(LAKE / "gold/mart_el_curve")).to_pandas()
    for r in el.itertuples():
        base = f"el.{r.cohort_id}.{r.label_source}.{r.user_kind}.{WAIT_KEY[r.wait_label]}"
        if r.user_kind == "all" or r.wait_label in ("1 h", "1 d"):
            f[base + ".n_known"], f[base + ".n_eventual"] = int(r.n_known), int(r.n_eventual)
            f[base + ".share_known"], f[base + ".e_l"] = float(r.share_known), float(r.e_l)
    eb = DeltaTable(str(LAKE / "gold/mart_el_by_burst")).to_pandas()
    for r in eb[eb.wait_label.isin(["1 h", "1 d"])].itertuples():
        g = {"10+": "burst10", "5-9": "g5_9", "2-4": "g2_4", "1": "g1", "0": "g0", "all": "all", "unknown": "unknown"}[r.burst_group]
        base = f"elburst.{r.cohort_id}.{r.label_source}.{g}.{WAIT_KEY[r.wait_label]}"
        f[base + ".n_eventual"], f[base + ".e_l"] = int(r.n_eventual), float(r.e_l)

    # ---------------- Hypotheses
    h = run("hypotheses.json")
    for r in h["H1"]:
        b = f"h1.{r['series']}"
        f[b + ".eventual_reverts"], f[b + ".pages"] = r["eventual_reverts"], r["pages"]
        f[b + ".known_1h_pct"], f[b + ".known_1h_lo"], f[b + ".known_1h_hi"] = r["known_1h_pct"], *r["known_1h_ci"]
        f[b + ".known_48h_pct"], f[b + ".known_48h_lo"], f[b + ".known_48h_hi"] = r["known_48h_pct"], *r["known_48h_ci"]
        f[b + ".verdict"] = r["verdict"]
    for r in h["H3"]:
        b = f"h3.{r['series']}.{WAIT_KEY[r['L']]}"
        f[b + ".burst_reverts"], f[b + ".rest_reverts"], f[b + ".burst_pages"] = r["burst_reverts"], r["rest_reverts"], r["burst_pages"]
        f[b + ".e_burst"], f[b + ".e_burst_lo"], f[b + ".e_burst_hi"] = r["E_burst"], *r["E_burst_ci"]
        f[b + ".e_rest"], f[b + ".e_rest_lo"], f[b + ".e_rest_hi"] = r["E_rest"], *r["E_rest_ci"]
        f[b + ".diff"], f[b + ".diff_lo"], f[b + ".diff_hi"] = r["diff_burst_minus_rest"], *r["diff_ci"]
        f[b + ".verdict"] = r["verdict"]
    for c in ("history", "live_ext"):
        d = h["H4"][c]
        b = f"h4.{c}"
        f[b + ".facts"], f[b + ".facts_title_differs"] = d["n"], d["moved"]
        f[b + ".facts_title_differs_pct"] = d["share_facts_title_differs_pct"]
        f[b + ".pages"], f[b + ".pages_affected"], f[b + ".pages_affected_pct"] = d["pages"], d["pages_moved"], d["share_pages_affected_pct"]
        f[b + ".titles"], f[b + ".titles_changed"] = d["titles"], d["titles_changed"]
        f[b + ".titles_changed_pct"] = d["share_titles_metric_changed_pct"]
        f[b + ".titles_rate_changed"], f[b + ".titles_reverts_changed"] = d["titles_rate_changed"], d["titles_reverts_changed"]
        f[b + ".titles_rate_changed_pct"] = round(100 * d["titles_rate_changed"] / d["titles"], 3)
        f[b + ".titles_reverts_changed_pct"] = round(100 * d["titles_reverts_changed"] / d["titles"], 3)
        f[b + ".reverts_moved"] = d["reverts_moved"]
        f[b + ".verdict"] = d["verdict"]
    f["h4.history_revisions_title_differs"] = h["H4"]["history_revisions_title_differs_from_historical"]

    # ---------------- Time travel
    tt = run("time_travel.json")
    for k, r in zip(("early", "parity", "ext"), tt["then_and_now"]):
        f[f"tt.asof.{k}.reverted_known"], f[f"tt.asof.{k}.pct_reverted"] = r["reverted_as_known"], r["pct_reverted"]
        f[f"tt.asof.{k}.fact_edit_version"] = r["fact_edit_version"]
    u = tt["early_to_parity_updates"]
    f["tt.asof.updates"], f["tt.asof.became_reverted"] = u["updated_rows"], u["became_reverted"]
    f["tt.asof.median_known_after_s"] = u["median_known_after_s"]
    f["tt.asof.median_known_after_days"] = round(u["median_known_after_s"] / 86400, 2)
    for r in tt["silver_live_revert_links_by_version"]:
        f[f"tt.silver_links.v{r['version']}.links"], f[f"tt.silver_links.v{r['version']}.within_followup"] = r["links"], r["within_followup"]
    for r in tt.get("snapshot_axis", {}).get("then_and_now", []):
        b = f"tt.snapshot.{r['snapshot'].replace('-', '_')}"
        f[b + ".reverted_then"], f[b + ".reverted_now"], f[b + ".label_version"] = r["reverted_as_known_then"], r["reverted_now"], r["label_version"]
    if "tt.snapshot.2026_09.reverted_then" in f:
        f["tt.snapshot.added_reverted"] = f["tt.snapshot.2026_10.reverted_then"] - f["tt.snapshot.2026_09.reverted_then"]

    # ---------------- Second snapshot
    sc = run("snapshot_checks.json")
    if sc:
        C = {c["check"]: c["got"] for c in sc["checks"]}
        f["snapshot.checks_passed"], f["snapshot.checks_failed"] = sc["passed"], sc["failed"]
        a = C["history cohort at the 2026-09 load: reverted / within 20 d / within 4 d"]
        b2 = C["history cohort at the 2026-10 load: reverted / within 20 d / within 4 d"]
        for k, x, y in zip(("reverted_any", "reverted_20d", "reverted_4d"), a, b2):
            f[f"snapshot.history_cohort.2026_09.{k}"], f[f"snapshot.history_cohort.2026_10.{k}"] = x, y
        cdf = C["change feed of the 2026-10 load: insert / update_preimage / update_postimage"]
        f["snapshot.label_merge.inserted"], f["snapshot.label_merge.updated"] = cdf["insert"], cdf["update_postimage"]
        for k, v in C["mart_label_change rows by class"].items():
            f[f"snapshot.label_change.{k}"] = v
        for k, v in C["label changes among history-cohort revisions, by class"].items():
            f[f"snapshot.label_change.history_cohort.{k}"] = v
        for c in ("live", "live_ext"):
            short, n = C[f"{c}: revisions with less than 4 days between edit and the 2026-10 cutoff (of all)"]
            f[f"snapshot.followup_short.{c}"], f[f"snapshot.followup_short.{c}.of"] = short, n
        for r in C["late_reverts (parity as_of, silver v2) vs the 2026-10 dump, by class"]:
            f[f"snapshot.late_reverts.{r['class']}.n"], f[f"snapshot.late_reverts.{r['class']}.confirmed"] = r["n"], r["became_reverted"]
        f["snapshot.late_reverts.exact.confirmed_pct"] = round(
            100 * f["snapshot.late_reverts.exact.confirmed"] / f["snapshot.late_reverts.exact.n"], 1)
        rec = {r["recon_class"]: r for r in C["mart_reconciliation (live vs 2026-10)"]}
        tot = sum(r["n_revisions"] for r in rec.values())
        for k, r in rec.items():
            f[f"recon.live.{k}"], f[f"recon.live.{k}.pct"] = r["n_revisions"], round(100 * r["n_revisions"] / tot, 3)
        f["recon.live.total"] = tot
        f["recon.live.agreement_pct"] = round(100 * (rec["both_reverted"]["n_revisions"] + rec["neither"]["n_revisions"]) / tot, 2)
        f["recon.live.dump_reverts"] = rec["both_reverted"]["n_revisions"] + rec["dump_only"]["n_revisions"]
        f["recon.live.stream_reverts"] = rec["both_reverted"]["n_revisions"] + rec["stream_only"]["n_revisions"]
        f["recon.live.stream_found_of_dump_pct"] = round(100 * rec["both_reverted"]["n_revisions"] / f["recon.live.dump_reverts"], 1)
        f["recon.live.dump_confirms_of_stream_pct"] = round(100 * rec["both_reverted"]["n_revisions"] / f["recon.live.stream_reverts"], 1)
        ds = {r["snapshot"]: r for r in C["dim_snapshot"]}
        f["text.snapshot_2026_10.cutoff"] = ds["2026-10"]["snapshot_cutoff"] + " UTC"
        f["text.snapshot_2026_09.cutoff"] = ds["2026-09"]["snapshot_cutoff"] + " UTC"
        f["text.snapshot_2026_10.published"] = ds["2026-10"]["snapshot_published_at"] + " UTC"
        for m in ("2026-09", "2026-10", "2026-11"):
            p = lake_config.HISTORY_SLIM_DIR / "2026-10" / f"enwiki_rev_all_{m}_slim.stats.json"
            if p.exists():
                s = json.loads(p.read_text())
                f[f"snapshot.filter.{m.replace('-', '_')}.rows_in"], f[f"snapshot.filter.{m.replace('-', '_')}.revisions"] = s["rows_in"], s["revision_rows_out"]

    # ---------------- Streaming algorithms
    sa = run("streaming_algos.json")
    f["algos.stream_events"], f["algos.revert_events"] = sa["stream"]["events"], sa["stream"]["revert_events"]
    f["algos.exact.pages"], f["algos.exact.editors"] = sa["exact_distinct"]["pages"], sa["exact_distinct"]["editors"]
    for r in sa["distinct"]:
        sk = r["sketch"].replace("HLL p=", "hll_p").replace("FM-PCSA m=", "fm_m")
        b = f"algos.{sk}.{r['item']}"
        f[b + ".estimate"], f[b + ".bytes"], f[b + ".exact_bytes_est"] = r["estimate_salt0"], r["sketch_bytes"], r["exact_bytes_est"]
        f[b + ".mean_err_pct"], f[b + ".sd_err_pct"], f[b + ".max_abs_err_pct"] = r["mean_rel_error_5_salts_pct"], r["sd_rel_error_5_salts_pct"], r["max_abs_error_5_salts_pct"]
        f[b + ".theory_se_pct"] = r["theory_se_pct"]
    f["algos.hll_p14.bytes_kb"] = round(f["algos.hll_p14.pages.bytes"] / 1024)
    f["algos.exact.pages_bytes_mb_est"] = round(f["algos.hll_p14.pages.exact_bytes_est"] / 1e6, 1)
    for r in sa["spark_approx_count_distinct"]:
        b = f"algos.spark_hll.rsd{str(r['rsd']).replace('0.', '')}"
        f[b + ".pages"], f[b + ".editors"] = r["pages"], r["editors"]
        f[b + ".pages_err_pct"] = round(100 * (r["pages"] - f["algos.exact.pages"]) / f["algos.exact.pages"], 2)
        f[b + ".editors_err_pct"] = round(100 * (r["editors"] - f["algos.exact.editors"]) / f["algos.exact.editors"], 2)
    m = sa["editors_merged_daily_hll12"]
    f["algos.merged_daily.estimate"], f["algos.merged_daily.err_pct"], f["algos.merged_daily.sum_of_daily_exact"] = m["estimate"], m["rel_error_pct"], m["sum_of_daily_exact"]
    for r in sa["bloom_meta_id"]:
        b = f"algos.bloom.fp{str(r['target_fp_rate']).replace('0.', '')}"
        for k in ("bits", "hashes", "bloom_bytes", "events", "exact_repeats", "flagged", "true_repeats_found", "false_positives",
                  "false_negatives", "observed_fp_rate", "exact_set_bytes_est"):
            f[f"{b}.{k}"] = r[k]
        f[b + ".bloom_mb"], f[b + ".exact_set_mb_est"] = round(r["bloom_bytes"] / 1e6, 1), round(r["exact_set_bytes_est"] / 1e6, 1)
        f[b + ".target_fp_pct"], f[b + ".observed_fp_pct"] = r["target_fp_rate"] * 100, round(100 * r["observed_fp_rate"], 4)
        f[b + ".flagged_pct"] = round(100 * r["flagged"] / r["events"], 4)
    for r in sa["dgim_reverts_last_hour"]:
        b = "algos.dgim." + ("wiki" if r["scope"] == "wiki-wide" else "page") + f".r{r['r']}"
        for k in ("eval_points", "mean_rel_error_pct", "p95_rel_error_pct", "max_rel_error_pct", "bound_pct", "max_buckets"):
            f[f"{b}.{k}"] = r[k]
        if "dgim_bytes_est" in r:
            f[b + ".bytes_est"], f[b + ".exact_window_bytes_est"] = r["dgim_bytes_est"], r["exact_window_bytes_est"]
    rv = sa["reservoir_edits"]
    f["algos.reservoir.stream_edits"], f["algos.reservoir.exact_pct"], f["algos.reservoir.sample_pct"] = rv["stream_edits"], rv["exact_revert_event_share_pct"], rv["sample_share_pct"]
    f["algos.reservoir.ci_lo"], f["algos.reservoir.ci_hi"] = rv["sample_95ci_pct"]
    for r in sa["ams_f2_edits_per_page"]:
        b = f"algos.ams.vars{r['variables']}"
        f[b + ".estimate"], f[b + ".err_pct"], f["algos.ams.exact_f2"] = r["estimate"], r["rel_error_pct"], r["exact_f2"]

    # ---------------- Structured Streaming
    ss = run("stream_sss.json")
    for r in ss["rates"]:
        b = f"sss.rate{r['target_rate_eps']}"
        f[b + ".rate"] = r["target_rate_eps"]
        for k in ("events", "micro_batches", "throughput_eps", "latency_p50_s", "latency_p95_s", "latency_max_s", "mean_batch_merge_s"):
            f[f"{b}.{k}"] = r[k]
    d = ss["drain"]
    f["sss.drain.events"], f["sss.drain.micro_batches"], f["sss.drain.wall_s"], f["sss.drain.throughput_eps"] = d["events"], d["micro_batches"], d["wall_s"], d["throughput_eps"]
    f["sss.drain.only_in_stream"], f["sss.drain.differing"] = d["parity_with_batch_silver"]["only_stream"], d["parity_with_batch_silver"]["differing"]
    f["sss.capture_mean_eps"] = round(f["bronze.page_change.rows"] / (26.4 * 86400), 1)

    # ---------------- Fallback notebooks (present once they ran)
    for name in ("fallback_lsh.json", "fallback_privacy.json", "fallback_moments.json"):
        d = run(name)
        if d:
            for k, v in d.get("facts", {}).items():
                f[k] = v

    # ---------------- Teammates' analyses (their committed result files; separate keys)
    f.update(teammates())
    f.update(lake_check_of_graph())

    # ---------------- Exports, timings, tests
    man = REPO / "data" / "exports" / "manifest.json"
    if man.exists():
        for name, v in json.loads(man.read_text())["files"].items():
            f[f"exports.{name}.rows"] = v["rows"]
            f[f"exports.{name}.mb"] = round(v["bytes"] / 1e6, 1)
    for k, log in (("bronze_load", "bronze_run1.log"), ("bronze_rerun", "bronze_run2.log"), ("silver_build", "silver_run1.log"),
                   ("rebuild_e2e", "build_all_e2e2.log"), ("sss_total", "stream_sss.log")):
        s = real_seconds(log)
        if s is not None:
            f[f"runtime.{k}_s"] = round(s)
    if "runtime.rebuild_e2e_s" in f:
        f["runtime.rebuild_e2e_min"] = round(f["runtime.rebuild_e2e_s"] / 60)
    return f


def run_tests() -> int:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([sys.executable, "-m", "pytest", "tests_lake", "ec-hw2/tests/test_history.py", "ec-hw2/tests/test_stream.py",
                        "-q", "-p", "no:cacheprovider"], capture_output=True, text=True, cwd=REPO, env=env)
    m = re.search(r"(\d+) passed", r.stdout)
    if r.returncode != 0 or not m:
        raise SystemExit("pytest failed:\n" + r.stdout[-2000:])
    return int(m.group(1))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO).stdout.strip()


def build() -> dict:
    facts = collect()
    facts["tests.passed"] = run_tests()
    tables = sorted(str(p.parent.relative_to(LAKE)) for p in LAKE.glob("*/*/_delta_log") if p.parent.parent.name in ("bronze", "silver", "gold"))
    meta = {"commit": git("rev-parse", "HEAD"), "commit_short": git("rev-parse", "--short", "HEAD"),
            "working_tree_dirty": bool(git("status", "--porcelain")), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": "scripts/make_results.py",
            "lake_versions": {t: version(t) for t in tables},
            "run_records": {p.name: datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                            for p in sorted(RUNS.glob("*.json"))}}
    return {"meta": meta, "constants": constants(), "facts": dict(sorted(facts.items()))}


def main() -> None:
    doc = build()
    if "--check" in sys.argv:
        old = json.loads(OUT.read_text())
        diff = [k for k in sorted(set(doc["facts"]) | set(old["facts"])) if doc["facts"].get(k) != old["facts"].get(k)]
        diff += [f"constants.{k}" for k in sorted(set(doc["constants"]) | set(old["constants"])) if doc["constants"].get(k) != old["constants"].get(k)]
        diff += [f"lake_versions.{k}" for k in sorted(set(doc["meta"]["lake_versions"]) | set(old["meta"]["lake_versions"]))
                 if doc["meta"]["lake_versions"].get(k) != old["meta"]["lake_versions"].get(k)]
        for k in diff[:40]:
            print("DIFFERS", k, "file:", old["facts"].get(k), "fresh:", doc["facts"].get(k))
        print(f"results.json check: {len(doc['facts'])} facts, {len(diff)} differ from a fresh collection")
        raise SystemExit(1 if diff else 0)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    write_results_md(doc)
    print(f"wrote {OUT.relative_to(REPO)}: {len(doc['facts'])} facts, {len(doc['constants'])} constants, commit {doc['meta']['commit_short']}"
          f"{' (working tree dirty)' if doc['meta']['working_tree_dirty'] else ''}")


if __name__ == "__main__":
    main()
