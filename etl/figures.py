"""Figures for the report and slides (docs/final/figures/, PNG, each well under 1 MB).

  flow.png      the data flow: sources -> Bronze -> Silver -> Gold -> analyses (same content as docs/final/flow.mmd)
  el_curve.png  E(L) by wait for history, live and live_ext, from gold/mart_el_curve (current version)

Run
    python -m etl.figures
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from deltalake import DeltaTable

from . import lake_config

FIG = lake_config.REPO_DIR / "docs" / "final" / "figures"
COLS = {"Sources": "#e8e8e8", "Bronze": "#e9c99b", "Silver": "#d5d9de", "Gold": "#f2d675", "Analyses": "#cfe3cf"}


def flow() -> None:
    lanes = [
        ("Sources", ["EventStreams capture (VPS)\npage_change, revert_risk, tags", "MediaWiki History dump\nsnapshot 2026-09 (filtered)"]),
        ("Bronze", ["page_change_events 4.87 M", "revert_risk_events 3.11 M", "tags_events 4.34 M",
                    "history_slim 5.27 M\nhistory_full 0.30 M"]),
        ("Silver", ["page_change, revert_risk,\ntag_events, capture_gaps", "history_slim, history_revisions,\nhistory_revert_links",
                    "live_*, late_reverts, live_ext_*\n(rebuilt per as_of)"]),
        ("Gold", ["dim_cohort, dim_snapshot,\ndim_time, dim_user", "dim_page (SCD Type 2)", "fact_edit, fact_revert_label\n(Change Data Feed)",
                  "mart_el_curve,\nmart_el_by_burst"]),
        ("Analyses", ["H1, H3, H4\n(bootstrap intervals)", "time travel: then vs now", "streaming algorithms\nHLL, FM, Bloom, DGIM",
                      "Structured Streaming\nreplay (E5)", "data/exports\n(LSH, privacy, charts)"]),
    ]
    sub = {"Sources": "", "Bronze": "delta-rs, append-only", "Silver": "delta-rs + EC HW2 rules", "Gold": "Spark SQL, MERGE",
           "Analyses": "Python + Spark"}
    fig, ax = plt.subplots(figsize=(15, 6.2), dpi=110)
    ax.set_xlim(0, 15)
    ax.set_ylim(-0.5, 6.2)
    ax.axis("off")
    w, h = 2.55, 0.82
    centers = {}
    for i, (lane, boxes) in enumerate(lanes):
        x = 0.25 + i * 3.0
        ax.text(x + w / 2, 5.95, lane, ha="center", va="center", fontsize=13, weight="bold")
        ax.text(x + w / 2, 5.62, sub[lane], ha="center", va="center", fontsize=9, color="#555555")
        gap = 5.25 / len(boxes)
        for j, label in enumerate(boxes):
            y = 5.2 - (j + 1) * gap + (gap - h) / 2
            ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                        fc=COLS[lane], ec="#444444", lw=1))
            ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=8.6)
            centers[(i, j)] = (x, y + h / 2)
    for i in range(len(lanes) - 1):
        x0 = 0.25 + i * 3.0 + w
        x1 = 0.25 + (i + 1) * 3.0
        ax.annotate("", xy=(x1 - 0.05, 2.75), xytext=(x0 + 0.05, 2.75),
                    arrowprops=dict(arrowstyle="-|>", lw=2.2, color="#333333"))
    ax.text(7.5, -0.3, "One engine writes each table. Builds take an as_of; versions are found by commit metadata. "
            "Kafka, Airflow and dbt were cut (stated deviation).", ha="center", fontsize=9, color="#333333")
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "flow.png", bbox_inches="tight")
    plt.close(fig)


def el_curve() -> None:
    df = DeltaTable(str(lake_config.lake_root() / "gold" / "mart_el_curve")).to_pandas()
    df = df[df.user_kind == "all"].sort_values("wait_s")
    fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=120)
    names = {"history": "history (Sep 8-10, dump labels)", "live": "live (Oct 20-22, stream)",
             "live_ext": "live_ext (Oct 20 - Nov 8, stream)"}
    for c, style in (("history", "o-"), ("live", "s-"), ("live_ext", "^--")):
        g = df[df.cohort_id == c]
        ax.plot(range(len(g)), g.e_l, style, label=f"{names[c]}, n = {int(g.n_eventual.iloc[0]):,}")
    ax.set_xticks(range(9))
    ax.set_xticklabels(df[df.cohort_id == "live"].wait_label)
    ax.set_xlabel("wait L after the edit")
    ax.set_ylabel("E(L): share of eventual reverts not yet known")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8.5)
    ax.set_title("Truth lag E(L), 4-day horizon (gold/mart_el_curve)")
    fig.savefig(FIG / "el_curve.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    flow()
    el_curve()
    for f in sorted(FIG.glob("*.png")):
        print(f, f.stat().st_size)
