"""Draw the report charts (PNG) and the architecture picture.

Purpose
    1. Charts for the report and the notebooks, from the query results. Each chart
       has a title that states the finding, axes with units, a colour-blind-safe
       palette (checked with the dataviz validator: blue #2a78d6, orange #eb6834,
       aqua #1baf7a), a legend for 2+ series plus direct labels, and a light grid.
       Human editors never appear in a chart.
    2. The architecture picture: report/figures/architecture.mmd (Mermaid) is
       rendered to architecture.png with mermaid-cli and the installed Google
       Chrome. If that fails, a simpler matplotlib drawing is made instead.
    The notebooks call the chart functions (for example known_by_figure()) and
    show the PNG. main() makes every figure from the result files.

Inputs
    ec-hw2/results/mongo_q1..q5 CSV files (Mongo Q3 with its history, history_4d and live
    series), mongo_q5_risk_deciles.csv, comparison.csv and _SUCCESS_comparison.json,
    data/tables/history_summary.json, live_summary.json, late_reverts_summary.json,
    _SUCCESS_live.json, data/parsed/*.parquet (event times) and capture_gaps.csv,
    ec-hw2/report/figures/architecture.mmd.

Outputs (150 dpi PNG)
    ec-hw2/results/figures/fig_*.png and _SUCCESS_figures.json (rows plotted per figure);
    ec-hw2/report/figures/architecture.png.

Run (from the repo root; about 20 seconds, the first Mermaid run downloads mermaid-cli)
    .venv/bin/python ec-hw2/report/make_figures.py
    .venv/bin/python ec-hw2/report/make_figures.py --only architecture
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

FIG = config.FIGURES_DIR
REPORT_FIG = config.HW2_DIR / "report" / "figures"
MMD = REPORT_FIG / "architecture.mmd"
ARCH_PNG = REPORT_FIG / "architecture.png"
DPI = 150
MERMAID_CLI = "@mermaid-js/mermaid-cli@12.0.0"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Palette and ink (the dataviz reference palette, light mode).
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
COHORT_COLOR = {config.COHORT_HISTORY: BLUE, config.COHORT_LIVE: ORANGE}
KIND_COLOR = {"registered": BLUE, "temporary": ORANGE, "bot": AQUA}
ENGINE_COLOR = {"MongoDB": BLUE, "Neo4j": ORANGE, "SQLite": AQUA}

plt.rcParams.update({
    "font.family": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 9,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": INK2, "ytick.color": INK2, "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE, "legend.frameon": False,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.axisbelow": True,
    "lines.linewidth": 1.8, "lines.markersize": 5,
})

_ROWS: dict[str, int] = {}   # rows plotted per figure, for _SUCCESS_figures.json


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def live_provisional() -> bool:
    try:
        return bool(read_json(config.TABLES_DIR / "_SUCCESS_live.json").get("provisional", True))
    except FileNotFoundError:
        return True


def provisional_note() -> str:
    if not live_provisional():
        return "The stream labels of the live cohort are final."
    return (f"PROVISIONAL: the stream labels of the live cohort are final only after "
            f"{config.LIVE_FINAL_AFTER.strftime('%Y-%m-%d %H:%M')} UTC.")


def titled(fig, title: str, subtitle: str) -> None:
    """The finding as the title (top left), the data description under it."""
    fig.text(0.012, 0.985, title, ha="left", va="top", fontsize=12, fontweight="bold", color=INK)
    fig.text(0.012, 0.925, subtitle, ha="left", va="top", fontsize=8.5, color=INK2, linespacing=1.4)


def save(fig, name: str, rows: int, top: float = 0.80) -> Path:
    """Write <name>.tmp, then rename it, so a reader never sees half a PNG."""
    FIG.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(top=top)
    path = FIG / name
    tmp = path.with_name(path.name + ".tmp")
    fig.savefig(tmp, dpi=DPI, format="png")
    plt.close(fig)
    os.replace(tmp, path)
    _ROWS[name] = int(rows)
    return path


def pct_axis(ax, top: float | None = None) -> None:
    if top is not None:
        ax.set_ylim(0, top)
    small = ax.get_ylim()[1] < 5          # ticks like 0.5% need one decimal
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=1 if small else 0))


def bar_labels(ax, bars, fmt: str, inside: bool = False, color: str = INK, size: float = 8) -> None:
    for b in bars:
        v = b.get_height()
        ax.annotate(fmt.format(v), (b.get_x() + b.get_width() / 2, v), xytext=(0, 2),
                    textcoords="offset points", ha="center", va="bottom", fontsize=size, color=color)


# --------------------------------------------------------------------------
# Notebook 01: tags and capture coverage
# --------------------------------------------------------------------------
def tag_agreement_figure(history_summary: dict | None = None, live_summary: dict | None = None) -> Path:
    hs = history_summary or read_json(config.TABLES_DIR / "history_summary.json")
    ls = live_summary or read_json(config.TABLES_DIR / "live_summary.json")
    by = hs["tag_agreement"]["by_T_bucket"]
    labels = list(by)
    vals = [100 * by[b]["tag_share"] for b in labels]
    tc = ls["tag_confirmed_share_of_reverted"]
    depth = tc.get("mw_reverted_max_depth", 15)
    # The two size groups use complete ranges only; a range that starts before the capture
    # has an unknown size (range_size is a lower bound), so it gets its own bar.
    parts = [("range_size_le_max", f"{depth} or fewer\nrevisions"), ("range_size_gt_max", f"more than\n{depth}")]
    if "range_incomplete" in tc:
        parts.append(("range_incomplete", "size not known\n(starts before\nthe capture)"))
    live_lab = [lab for _, lab in parts]
    live_val = [100 * tc[p]["share"] for p, _ in parts]
    live_n = [tc[p]["n"] for p, _ in parts]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [3, 1.7]})
    b1 = a1.bar(range(len(labels)), vals, width=0.6, color=BLUE, edgecolor=SURFACE, linewidth=1)
    bar_labels(a1, b1, "{:.1f}%")
    a1.set_xticks(range(len(labels)), [f"{lab}\n(n={by[lab]['n']:,})" for lab in labels])
    a1.set_xlabel("History cohort: time to revert T in the dump")
    a1.set_ylabel("Revisions with the mw-reverted tag")
    a1.set_title("History: dump label vs tag", pad=8)
    pct_axis(a1, 108)
    xs = list(range(len(live_val)))
    b2 = a2.bar(xs, live_val, width=0.55, color=ORANGE, edgecolor=SURFACE, linewidth=1)
    bar_labels(a2, b2, "{:.1f}%")
    a2.set_xticks(xs, [f"{lab}\n(n={k:,})" for lab, k in zip(live_lab, live_n)], fontsize=7.5)
    a2.set_xlabel("Live cohort: revisions the revert covered")
    a2.set_title("Live: reverts confirmed by the tag", pad=8)
    pct_axis(a2, 108)
    titled(fig, f"The mw-reverted tag misses slow reverts and reverts of more than {depth} revisions",
           f"Left: share of history revisions with the tag, by the dump's time to revert (all {sum(b['n'] for b in by.values()):,} "
           f"revisions). Right: share of live reverted revisions (exact reverts within 4 days)\n"
           f"that got the tag, by the size of the revert (ranges inside the capture), and for reverts whose range starts "
           f"before the capture.\n{provisional_note()}")
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.24, wspace=0.18)
    return save(fig, "fig_tag_agreement.png", len(labels) + len(live_val), top=0.76)


def capture_coverage_figure() -> Path:
    streams = [(config.STREAM_PAGE_CHANGE, "page_change.parquet", "page_change (edits)", BLUE),
               (config.STREAM_TAGS, "tag_events.parquet", "revision-tags-change", ORANGE),
               (config.STREAM_REVERT_RISK, "revert_risk.parquet", "revert-risk score", AQUA)]
    fig, ax = plt.subplots(figsize=(10, 4))
    rows = 0
    for _, fname, label, color in streams:
        t = pd.read_parquet(config.PARSED_DIR / fname, columns=["meta_dt"])["meta_dt"]
        per_h = t.dt.floor("h").value_counts().sort_index()
        full = pd.date_range(per_h.index.min(), per_h.index.max(), freq="h", tz="UTC")
        per_h = per_h.reindex(full, fill_value=0)
        ax.plot(per_h.index, per_h.values, color=color, label=label, linewidth=1.6)
        rows += len(per_h)
    lo, hi = config.LIVE_WINDOW
    ymax = ax.get_ylim()[1] * 1.18
    ax.set_ylim(0, ymax)
    ax.axvspan(lo, hi, color=BLUE, alpha=0.07, linewidth=0)
    ax.text(lo + (hi - lo) / 2, ymax * 0.98, "live cohort window: 2026-10-20 to 2026-10-22 (UTC)",
            ha="center", va="top", fontsize=8, color=INK2)
    gaps = pd.read_csv(config.PARSED_DIR / "capture_gaps.csv", parse_dates=["gap_start", "gap_end"])
    for _, g in gaps.iterrows():
        ax.plot([g["gap_start"], g["gap_start"]], [0, ymax * 0.08], color=INK, linewidth=1.2)
    if len(gaps):
        g0 = gaps.iloc[0]
        ax.annotate(f"{len(gaps)} gaps in revert-risk ({gaps['gap_s'].sum():.0f} s in all)",
                    (g0["gap_start"], ymax * 0.08), xytext=(6, 2), textcoords="offset points",
                    fontsize=8, color=INK)
    ax.set_ylabel("Events per hour (enwiki, all namespaces)")
    ax.set_xlabel("Event time meta.dt (UTC)")
    ax.legend(loc="upper left", fontsize=8, ncol=3, bbox_to_anchor=(0, 0.93))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m-%d"))
    parsed = read_json(config.PARSED_DIR / "_SUCCESS_parsed.json")
    pc_gaps = parsed["streams"][config.STREAM_PAGE_CHANGE]["gaps"]
    titled(fig, f"The capture covers the live window: {pc_gaps} gaps in page_change, "
                f"{len(gaps)} short gaps in revert-risk",
           "Events per hour in the Mac copy of the VPS capture. A gap is two events of one topic more than "
           f"{int(parsed.get('gap_min_s', 120))} s apart.\n"
           "The last hours are still filling: the capture keeps running on the VPS.")
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.14)
    return save(fig, "fig_capture_coverage.png", rows)


# --------------------------------------------------------------------------
# Notebook 02: Mongo Q1, Q3, Q4
# --------------------------------------------------------------------------
def revert_rate_by_hour_figure(q1: pd.DataFrame | None = None) -> Path:
    q1 = q1 if q1 is not None else pd.read_csv(config.RESULTS_DIR / "mongo_q1_revert_rate_by_hour.csv")
    kinds = ["temporary", "registered", "bot"]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), sharex=True)
    for ax, kind in zip(axes, kinds):
        top = 0
        for cohort, color in COHORT_COLOR.items():
            d = q1[(q1["cohort"] == cohort) & (q1["user_kind"] == kind)].sort_values("hour_utc")
            if d.empty:
                continue
            y = 100 * d["revert_rate"]
            top = max(top, y.max())
            ax.plot(d["hour_utc"], y, color=color, marker="o", markersize=3.5,
                    label=f"{cohort} cohort")
        ax.set_title(kind, pad=6)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xlabel("Hour of the edit (UTC)")
        pct_axis(ax, top * 1.25 if top else None)
    axes[0].set_ylabel("Edits reverted (history: 20 d, live: 4 d)")
    axes[0].legend(loc="lower left", fontsize=8)
    g = q1[q1["cohort"] == config.COHORT_HISTORY].groupby("user_kind")[["edits", "reverted"]].sum()
    r = g["reverted"] / g["edits"]
    ratio = r["temporary"] / r["registered"]
    h = q1[q1["cohort"] == config.COHORT_HISTORY].pivot_table(index="hour_utc", columns="user_kind",
                                                               values="revert_rate")
    every_hour = bool((h["temporary"] > h["registered"]).all())
    titled(fig, f"Temporary accounts are reverted {ratio:.1f} times as often as registered users"
                + (", and more often in every hour" if every_hour else ""),
           f"Mongo Q1: revert rate by hour of day and user kind. History cohort: temporary {100 * r['temporary']:.1f}%, "
           f"registered {100 * r['registered']:.1f}%, bot {100 * r['bot']:.2f}%.\n"
           f"Each panel has its own y scale. {provisional_note()}")
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.15, wspace=0.25)
    return save(fig, "fig_revert_rate_by_hour.png", len(q1))


def time_to_revert_figure(q3: pd.DataFrame | None = None) -> Path:
    """Mongo Q3 with its 3 series. Left: history, 20-day horizon. Right: the common 4-day
    horizon, history_4d next to live (the only fair comparison of the two cohorts)."""
    q3 = q3 if q3 is not None else pd.read_csv(config.RESULTS_DIR / "mongo_q3_time_to_revert.csv")
    labels = config.LAG_LABELS
    in_4d = [lab for lab, lo in zip(labels, config.LAG_GRID_S) if lo < config.LIVE_FOLLOWUP_S]
    series = {c: q3[q3["cohort"] == c].set_index("bucket") for c in (config.COHORT_HISTORY, "history_4d",
                                                                        config.COHORT_LIVE)}
    n = {c: int(d["n"].sum()) for c, d in series.items()}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True,
                                 gridspec_kw={"width_ratios": [len(labels), len(in_4d) + 1]})
    # Left: the history cohort alone, every bucket up to 20 days.
    h = series[config.COHORT_HISTORY].reindex(labels)
    x = np.arange(len(labels))
    bars = a1.bar(x, 100 * h["share"].fillna(0), width=0.62, color=BLUE, edgecolor=SURFACE, linewidth=1)
    bar_labels(a1, bars, "{:.0f}%", size=7.5)
    a1.set_xticks(x, labels, fontsize=7.5, rotation=35, ha="right")
    a1.set_xlabel("Time to revert T (bucket, lower edge included)")
    a1.set_ylabel("Share of the series' reverts")
    a1.set_title(f"History cohort, reverts within 20 days (n = {n[config.COHORT_HISTORY]:,})", pad=6)
    # Right: the common 4-day horizon. Same colour per cohort as everywhere else.
    x4 = np.arange(len(in_4d))
    w = 0.38
    for i, (cohort, color, lab) in enumerate((
            ("history_4d", BLUE, f"history, within 4 days (n = {n['history_4d']:,})"),
            (config.COHORT_LIVE, ORANGE, f"live, within 4 days (n = {n[config.COHORT_LIVE]:,}; PROVISIONAL)"))):
        d = series[cohort].reindex(in_4d)
        bars = a2.bar(x4 + (i - 0.5) * w, 100 * d["share"].fillna(0), width=w, color=color, edgecolor=SURFACE,
                      linewidth=1, label=lab)
        bar_labels(a2, list(bars)[:1], "{:.0f}%", size=7.5)      # direct label on the first bucket only
    a2.set_xticks(x4, in_4d, fontsize=7.5, rotation=35, ha="right")
    a2.set_xlabel("Time to revert T (bucket, lower edge included)")
    a2.set_title("Same 4-day horizon: history vs live", pad=6)
    a2.legend(loc="upper right", fontsize=7.5)
    pct_axis(a1, max(100 * d["share"].max() for d in series.values()) * 1.25)

    def cum_at(cohort, edge):
        d = series[cohort]
        return float(d.loc[d["bucket_upper_s"] == edge, "cum_share"].iloc[0])
    h1, l1 = cum_at("history_4d", 3600), cum_at(config.COHORT_LIVE, 3600)
    h20_1h, h20_1d = cum_at(config.COHORT_HISTORY, 3600), cum_at(config.COHORT_HISTORY, 86400)
    titled(fig, f"On the same 4-day horizon, {100 * l1:.0f}% of the live reverts and {100 * h1:.0f}% of the "
                f"history reverts come within 1 hour",
           "Mongo Q3: time to revert ($bucket on the lag grid of config.py). Each series has its own horizon, and its "
           "shares add up to 100%.\n"
           f"Left: history reverts within 20 days ({100 * h20_1h:.0f}% within 1 hour, {100 * (1 - h20_1d):.0f}% after "
           "more than 1 day). Right: reverts within 4 days in both cohorts. Compare the live cohort only with this "
           "4-day history series.\n"
           f"The live follow-up is still short, so its late buckets are too small. {provisional_note()}")
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.2, wspace=0.06)
    return save(fig, "fig_time_to_revert.png", len(q3), top=0.76)


def bot_vs_human_figure(q4: pd.DataFrame | None = None) -> Path:
    q4 = q4 if q4 is not None else pd.read_csv(config.RESULTS_DIR / "mongo_q4_bot_vs_human.csv")
    made = q4[q4["part"] == "made_by_reverter_kind"].set_index("kind")
    recv = q4[q4["part"] == "received_by_author_kind"].set_index("kind")
    kinds = ["registered", "temporary", "bot"]
    rows = [(f"Revert actions made\n(n = {int(made['revert_actions'].sum()):,}, by the reverter's kind)", made),
            (f"Reverted revisions received\n(n = {int(recv['reverted_revisions'].sum()):,}, by the author's kind)", recv)]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for i, (label, d) in enumerate(rows):
        left, small = 0.0, []
        for kind in kinds:
            v = 100 * float(d.loc[kind, "share"]) if kind in d.index else 0.0
            ax.barh(i, v, left=left, height=0.4, color=KIND_COLOR[kind], edgecolor=SURFACE, linewidth=2,
                    label=kind if i == 0 else None)
            if v >= 15:     # the label fits inside the segment
                ax.text(left + v / 2, i, f"{kind} {v:.1f}%", ha="center", va="center", fontsize=8,
                        color="white")
            else:
                small.append(f"{kind} {v:.1f}%")
            left += v
        if small:
            ax.text(101, i, "\n".join(small), va="center", fontsize=8, color=INK)
    ax.set_yticks([0, 1], [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax.set_xlabel("Share (history cohort, reverts by another editor within 20 days)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=3, fontsize=8)
    bot_made = 100 * float(made.loc["bot", "share"])
    bot_recv = 100 * float(recv.loc["bot", "share"])
    titled(fig, f"Bots make {bot_made:.1f}% of the revert actions and receive {bot_recv:.1f}% of the reverts",
           "Mongo Q4 ($facet). Registered users make most revert actions; temporary accounts (logged-out editors) "
           "receive more than half of the reverts.")
    fig.subplots_adjust(left=0.24, right=0.89, bottom=0.36)
    return save(fig, "fig_bot_vs_human.png", len(made) + len(recv), top=0.72)


# --------------------------------------------------------------------------
# Notebook 04: the comparison
# --------------------------------------------------------------------------
def comparison_figure(cmp: pd.DataFrame | None = None) -> Path:
    """Lines of code AND characters of code (the line count depends on the layout), and the
    median time with its min-max range. 'Faster' comes only from comparison.csv faster_than
    (the ranges do not overlap); the figure never names a 'fastest' engine by the median."""
    cmp = cmp if cmp is not None else pd.read_csv(config.RESULTS_DIR / "comparison.csv")
    questions = list(dict.fromkeys(cmp["question"]))
    engines = list(ENGINE_COLOR)
    label = str(cmp["timing_label"].iloc[0])
    runs, rounds = int(cmp["runs"].iloc[0]), int(cmp["rounds"].iloc[0])

    def get(q, e, col):
        return cmp[(cmp["question"] == q) & (cmp["engine"] == e)][col].iloc[0]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3))
    w = 0.25
    panels = ((axes[0], "lines_of_code", "Lines of query code", "Lines of code"),
              (axes[1], "code_chars", "Characters of query code", "Characters of code"),
              (axes[2], "median_ms", "Median time (ms); thin bar: fastest to slowest run", f"Query time ({label})"))
    for ax, col, ylab, title in panels:
        for i, e in enumerate(engines):
            xs = np.arange(len(questions)) + (i - 1) * w
            vals = np.array([float(get(q, e, col)) for q in questions])
            bars = ax.bar(xs, vals, width=w, color=ENGINE_COLOR[e], edgecolor=SURFACE, linewidth=1, label=e)
            if col != "median_ms":
                bar_labels(ax, bars, "{:,.0f}", size=7.5)
                continue
            lo = np.array([float(get(q, e, "min_ms")) for q in questions])
            hi = np.array([float(get(q, e, "max_ms")) for q in questions])
            ax.errorbar(xs, vals, yerr=[vals - lo, hi - vals], fmt="none", ecolor=INK2, elinewidth=1, capsize=2)
            for x, v, top in zip(xs, vals, hi):      # the median, above the slowest run
                ax.annotate(f"{v:.1f}", (x, top), xytext=(0, 2), textcoords="offset points", ha="center",
                            va="bottom", fontsize=7.5, color=INK)
        ax.set_xticks(range(len(questions)), questions)
        ax.set_ylabel(ylab)
        ax.set_title(title, pad=6)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.12)
    axes[0].legend(loc="upper right", fontsize=8)
    same = bool(cmp["same_result"].astype(str).str.lower().eq("yes").all())
    mut = cmp[cmp["question"] == "mutual reverts"].set_index("engine")
    by_loc, by_chars = mut["lines_of_code"].idxmin(), mut["code_chars"].idxmin()
    shortest = (f"{by_loc} has the shortest mutual-reverts query ({int(mut.loc[by_loc, 'lines_of_code'])} lines, "
                f"{int(mut.loc[by_loc, 'code_chars']):,} characters)" if by_loc == by_chars else
                f"the shortest mutual-reverts query is {by_loc} by lines and {by_chars} by characters")
    titled(fig, ("All 3 engines give identical results; " if same else "The engines do NOT give identical results; ")
           + shortest,
           f"The same 2 questions in MongoDB, Neo4j and SQLite (history cohort). Median of {runs} runs ({rounds} rounds, "
           f"the engines take turns).\n{faster_text(cmp)}\n"
           f"Neo4j mutual reverts: {get('mutual reverts', 'Neo4j', 'input_note')}\n"
           + timing_label_text(label))
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.1, wspace=0.28)
    return save(fig, "fig_comparison.png", len(cmp), top=0.72)


def faster_text(cmp: pd.DataFrame) -> str:
    """'Faster' only where comparison.csv faster_than says so (the min-max ranges do not overlap)."""
    parts = []
    for q in dict.fromkeys(cmp["question"]):
        d = cmp[cmp["question"] == q]
        wins = [f"{r['engine']} than {r['faster_than'].replace('; ', ' and ')}" for _, r in d.iterrows()
                if isinstance(r["faster_than"], str) and r["faster_than"].strip()]
        parts.append(f"{q}: " + (", ".join(wins) if wins else "no engine (the ranges overlap)"))
    return "Faster, because the min-max ranges do not overlap: " + "; ".join(parts) + "."


def timing_label_text(label: str) -> str:
    if label == "final":
        return "Timings are labelled 'final'."
    load = ""
    try:
        sc = read_json(config.RESULTS_DIR / "_SUCCESS_comparison.json")
        if sc.get("load_average_start"):
            load = f" (1-minute load average {sc['load_average_start'][0]:.2f} at the start)"
    except FileNotFoundError:
        pass
    return (f"PROVISIONAL: timings are labelled '{label}'{load}; they will be measured again on an idle Mac "
            "(compare.py --final).")


# --------------------------------------------------------------------------
# Notebook 05: known-by curves, risk deciles, late reverts
# --------------------------------------------------------------------------
def known_by_figure(q5: pd.DataFrame | None = None) -> Path:
    q5 = q5 if q5 is not None else pd.read_csv(config.RESULTS_DIR / "mongo_q5_truth_lag_preview.csv")
    waits = list(config.WAIT_POINTS_S)
    x = np.arange(len(waits))
    panels = [("all", "all editors"), ("temporary", "temporary accounts"), ("registered", "registered users")]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4), sharey=True)
    at_1h = {}
    for ax, (kind, title) in zip(axes, panels):
        for cohort, color in COHORT_COLOR.items():
            d = q5[(q5["cohort"] == cohort) & (q5["user_kind"] == kind)].set_index("wait").reindex(waits)
            if d["share_known"].isna().all():
                continue
            y = 100 * d["share_known"]
            ax.plot(x, y, color=color, marker="o", markersize=4, label=f"{cohort} cohort")
            i1h = waits.index("1 h")
            if kind == "all":
                at_1h[cohort] = y.iloc[i1h]
            ax.annotate(f"{y.iloc[i1h]:.0f}%", (x[i1h], y.iloc[i1h]),
                        xytext=(6, -10 if cohort == config.COHORT_HISTORY else 6), textcoords="offset points",
                        fontsize=8, color=INK)
        ax.set_title(title, pad=6)
        ax.set_xticks(x, waits, rotation=0, fontsize=7.5)
        ax.set_xlabel("Wait after the edit")
        pct_axis(ax, 105)
    axes[0].set_ylabel("Share of 4-day reverts already visible")
    axes[0].legend(loc="lower right", fontsize=8)
    h, l = at_1h.get(config.COHORT_HISTORY, float("nan")), at_1h.get(config.COHORT_LIVE, float("nan"))
    titled(fig, f"After 1 hour, {h:.0f}% (history) and {l:.0f}% (live) of the eventual reverts are visible",
           "Mongo Q5, known-by curves. Eventual revert = reverted within 4 days (self-reverts count). History: "
           "visible at T (dump). Live: visible at T + K (stream delay).\n" + provisional_note()
           + " The live follow-up is shorter than 4 days, so the live curve is too high.")
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.14, wspace=0.08)
    return save(fig, "fig_known_by_curves.png", len(q5))


def risk_decile_figure(decision: pd.DataFrame | None = None) -> Path:
    if decision is None:
        from report import build_facts
        decision = build_facts.decision_table()
    d = decision[decision["group"] != "no score"].reset_index(drop=True)
    x = np.arange(len(d))
    labels = [g.replace("decile ", "") for g in d["group"]]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.2))
    bars = a1.bar(x, d["revert_rate_4d_pct"], width=0.6, color=BLUE, edgecolor=SURFACE, linewidth=1)
    for b in list(bars)[-2:]:
        a1.annotate(f"{b.get_height():.1f}%", (b.get_x() + b.get_width() / 2, b.get_height()), xytext=(0, 2),
                    textcoords="offset points", ha="center", fontsize=8, color=INK)
    a1.set_xticks(x, labels)
    a1.set_xlabel("Revert-risk decile at save time (1 = lowest score)")
    a1.set_ylabel("Edits reverted within 4 days")
    a1.set_title("Revert rate by risk decile", pad=6)
    pct_axis(a1)
    for wait, color, dx in (("1h", BLUE, -0.15), ("1d", ORANGE, 0.15)):
        y = d[f"visible_{wait}_pct"]
        err = [y - d[f"visible_{wait}_lo"], d[f"visible_{wait}_hi"] - y]
        a2.errorbar(x + dx, y, yerr=err, fmt="o", color=color, markersize=4, elinewidth=1, capsize=0,
                    label=f"after {wait.replace('h', ' h').replace('d', ' d')}")
    a2.set_xticks(x, labels)
    a2.set_xlabel("Revert-risk decile at save time (1 = lowest score)")
    a2.set_ylabel("Share of its 4-day reverts already visible")
    a2.set_title("What a wait buys (95% Wilson interval)", pad=6)
    pct_axis(a2, 105)
    a2.legend(loc="lower right", fontsize=8)
    top = d.iloc[-1]
    titled(fig, f"The riskiest 10% of edits: {top['revert_rate_4d_pct']:.0f}% are reverted, and "
                f"{top['visible_1h_pct']:.0f}% of those reverts are visible after 1 hour",
           "Live cohort, Wikimedia revert-risk score (10 equal groups, Mongo Q5 risk deciles). "
           f"Wide intervals in the low deciles: they have few reverts ({int(d.iloc[0]['reverts_4d'])} in decile 1).\n" + provisional_note())
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.14, wspace=0.22)
    return save(fig, "fig_risk_deciles.png", len(d))


def late_reverts_figure(summary: dict | None = None) -> Path:
    s = summary or read_json(config.TABLES_DIR / "late_reverts_summary.json")
    classes = config.LATE_CLASSES
    names = {"exact": "exact revert\n(dump label changed later)", "inexact_undo": "inexact undo\n(dump never counts it)",
             "method_unknown": "tag only\n(method not known)"}
    vals = [s["by_class"].get(c, 0) for c in classes]
    ns0 = [s.get("by_class_ns0", {}).get(c) for c in classes]
    inh = [s["in_history_cohort_by_class"].get(c, 0) for c in classes]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    y = np.arange(len(classes))
    bars = ax.barh(y, vals, height=0.4, color=BLUE, edgecolor=SURFACE, linewidth=1)
    for b, v, v0, k in zip(bars, vals, ns0, inh):
        in0 = f"{v0:,} in namespace 0; " if v0 is not None else ""
        ax.annotate(f"{v:,}  ({in0}{k} in the history cohort)", (b.get_width(), b.get_y() + b.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=INK)
    ax.set_yticks(y, [names[c] for c in classes])
    ax.invert_yaxis()
    ax.set_xlim(0, max(vals) * 1.6)
    ax.set_xlabel("September 2026 revisions, all namespaces (lower bound)")
    ax.grid(axis="y", visible=False)
    in_ns0 = f" ({s['rows_ns0']:,} in namespace 0)" if "rows_ns0" in s else ""
    titled(fig, f"At least {s['rows']:,} September edits{in_ns0} were reverted in October, after the dump was cut",
           "Late reverts: the 2026-09 dump says 'not reverted', but the October stream shows a revert (all namespaces). "
           "Nobody watched the stream from 2026-10-01 01:38 UTC\nuntil the capture started, so every count is a "
           "lower bound. " + provisional_note())
    fig.subplots_adjust(left=0.22, right=0.99, bottom=0.17)
    return save(fig, "fig_late_reverts.png", len(classes), top=0.76)


# --------------------------------------------------------------------------
# The architecture picture
# --------------------------------------------------------------------------
def render_architecture() -> Path:
    """Mermaid -> PNG with mermaid-cli and the installed Chrome; matplotlib if that fails."""
    REPORT_FIG.mkdir(parents=True, exist_ok=True)
    tmp = ARCH_PNG.with_name("architecture.tmp.png")
    npx = shutil.which("npx")
    if npx and Path(CHROME).exists():
        with tempfile.TemporaryDirectory() as td:
            pconf = Path(td) / "puppeteer.json"
            pconf.write_text(json.dumps({"executablePath": CHROME, "args": ["--no-sandbox"]}))
            env = {**os.environ, "PUPPETEER_SKIP_DOWNLOAD": "1"}
            cmd = [npx, "-y", MERMAID_CLI, "-i", str(MMD), "-o", str(tmp), "-p", str(pconf),
                   "-b", "white", "-s", "2", "-t", "neutral"]
            try:
                r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=240)
                if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 1000:
                    os.replace(tmp, ARCH_PNG)
                    _ROWS["architecture.png (mermaid-cli)"] = 1
                    return ARCH_PNG
                print("mermaid-cli failed:", (r.stderr or r.stdout)[-500:])
            except (OSError, subprocess.SubprocessError) as exc:
                print(f"mermaid-cli failed: {type(exc).__name__}: {exc}")
    return architecture_matplotlib()


def architecture_matplotlib() -> Path:
    """The fallback drawing: the same boxes and arrows as architecture.mmd, simpler."""
    boxes = {
        "es": (0.10, 0.80, "Wikimedia EventStreams\n3 streams"),
        "cap": (0.10, 0.60, "VPS: capture.py\n(2 systemd units)"),
        "dump": (0.10, 0.35, "MediaWiki History dump\n2026-09 (557 MB)"),
        "filt": (0.10, 0.15, "VPS: filter_history.py\n(once)"),
        "raw": (0.36, 0.60, "Mac: data/raw/\n.ndjson.gz"),
        "hist": (0.36, 0.15, "Mac: data/history/\nParquet"),
        "parse": (0.56, 0.38, "parse scripts\ningest/"),
        "tab": (0.56, 0.62, "Parquet tables\ndata/tables/"),
        "mongo": (0.76, 0.80, "MongoDB\n(documents)"),
        "csv": (0.76, 0.55, "CSV\ndata/neo4j/import/"),
        "neo": (0.93, 0.55, "Neo4j\n(graph)"),
        "sql": (0.76, 0.25, "SQLite\ntruthlag.sqlite"),
        "atlas": (0.93, 0.80, "Atlas M0\n(history)"),
    }
    arrows = [("es", "cap", ""), ("cap", "raw", "rsync"), ("dump", "filt", ""), ("filt", "hist", "rsync"),
              ("raw", "parse", ""), ("hist", "parse", ""), ("parse", "tab", ""), ("tab", "mongo", "load_mongo.py"),
              ("mongo", "csv", "export_graph.py"), ("csv", "neo", "load_neo4j.py"), ("tab", "sql", "load_sql.py"),
              ("mongo", "atlas", "")]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.set_axis_off()
    artists = {}
    for name, (x, y, text) in boxes.items():
        artists[name] = ax.text(x, y, text, ha="center", va="center", fontsize=8.5, color=INK, zorder=3,
                                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "edgecolor": AXIS})
    fig.canvas.draw()      # the box patches get their size here; the arrows stop at their edges
    for a, b, lab in arrows:
        (x1, y1, _), (x2, y2, _) = boxes[a], boxes[b]
        ax.annotate("", (x2, y2), (x1, y1), zorder=4,
                    arrowprops={"arrowstyle": "->", "color": INK2, "linewidth": 1,
                                "patchA": artists[a].get_bbox_patch(), "patchB": artists[b].get_bbox_patch()})
        if lab:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.03, lab, ha="center", fontsize=7.5, color=INK2)
    ax.set_title("EC HW2 data flow: VPS capture and dump filter, rsync to the Mac, then MongoDB, Neo4j and SQLite",
                 loc="left")
    tmp = ARCH_PNG.with_name("architecture.tmp.png")
    fig.savefig(tmp, dpi=DPI, format="png")
    plt.close(fig)
    os.replace(tmp, ARCH_PNG)
    _ROWS["architecture.png (matplotlib fallback)"] = len(boxes)
    return ARCH_PNG


# --------------------------------------------------------------------------
FIGURES = {
    "tag_agreement": tag_agreement_figure,
    "capture_coverage": capture_coverage_figure,
    "revert_rate_by_hour": revert_rate_by_hour_figure,
    "time_to_revert": time_to_revert_figure,
    "bot_vs_human": bot_vs_human_figure,
    "comparison": comparison_figure,
    "known_by": known_by_figure,
    "risk_deciles": risk_decile_figure,
    "late_reverts": late_reverts_figure,
    "architecture": render_architecture,
}


def write_success() -> None:
    path = FIG / "_SUCCESS_figures.json"
    old = read_json(path).get("rows", {}) if path.exists() else {}
    info = {"step": "figures", "data_version": config.DATA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "live_provisional": live_provisional(), "rows": {**old, **_ROWS}}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", choices=list(FIGURES), action="append",
                    help="make only this figure (can repeat)")
    args = ap.parse_args(argv)
    for name in args.only or FIGURES:
        path = FIGURES[name]()
        print(f"wrote {path.relative_to(config.REPO_ROOT)}")
    write_success()


if __name__ == "__main__":
    main()
