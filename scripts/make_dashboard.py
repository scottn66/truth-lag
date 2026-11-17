"""Build docs/final/dashboard.html: one self-contained page that shows the finished project.

Every number on the page is a fact or constant of docs/final/results.json, formatted by truthlag_numbers.fmt.
Nothing is typed by hand, no data file is read, and the page needs no network (inline CSS, SVG and script).

Run
    .venv-lake/bin/python scripts/make_dashboard.py            write the page, then check it
    .venv-lake/bin/python scripts/make_dashboard.py --check    check the page on disk only
The check fails (exit 1) when the page on disk is not what this script renders, or when a number in its visible
text is not in results.json. Axis tick labels are scale marks, not results, and are left out of the check.
Limit (the same as check_numbers.py): a number passes when it equals ANY fact at the precision shown.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import truthlag_numbers as tn  # noqa: E402

OUT = tn.REPO / "docs" / "final" / "dashboard.html"
R = tn.load_results()
VALS = tn.all_values(R)
WAITS = ["w0", "w1min", "w5min", "w15min", "w1h", "w6h", "w1d", "w2d", "w4d"]


def V(key):
    if key not in VALS:
        raise KeyError(f"not in results.json: {key}")
    return VALS[key]


def F(key, spec=None):
    return tn.fmt(V(key), spec)


def esc(s):
    return html.escape(str(s), quote=True)


def wait_labels():
    """The nine waits, written from constants (no typed number)."""
    one, two = F("one"), F("two")
    return [F("zero"), f"{one} min", f"{F('wait_5')} min", f"{F('wait_15')} min", f"{one} h", f"{F('wait_6')} h",
            f"{one} d", f"{two} d", f"{F('horizon_days')} d"]


# ------------------------------------------------------------------------------------------------ charts
W, H, ML, MR, MT, MB = 720, 300, 46, 18, 14, 34


def line_chart(cid, title, series, xlabels, ymax, ticks, unit, xtitle, ref=None):
    """series: [(name, slot, [raw values], [shown strings])]. ticks: [(raw, label)] (axis marks). ref: (raw, label)."""
    n = len(xlabels)
    pw, ph = W - ML - MR, H - MT - MB
    xs = [ML + pw * i / (n - 1) for i in range(n)]

    def y(v):
        return MT + ph * (1 - v / ymax)

    p = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">']
    for raw, lab in ticks:
        p.append(f'<line class="grid" x1="{ML}" x2="{W - MR}" y1="{y(raw):.1f}" y2="{y(raw):.1f}"/>')
        p.append(f'<text class="ax" x="{ML - 8}" y="{y(raw) + 4:.1f}" text-anchor="end">{esc(lab)}</text>')
    for i, lab in enumerate(xlabels):
        p.append(f'<text class="ax" x="{xs[i]:.1f}" y="{H - MB + 18}" text-anchor="middle">{esc(lab)}</text>')
    p.append(f'<text class="axt" x="{W - MR}" y="{H - 2}" text-anchor="end">{esc(xtitle)}</text>')
    if ref:
        p.append(f'<line class="ref" x1="{ML}" x2="{W - MR}" y1="{y(ref[0]):.1f}" y2="{y(ref[0]):.1f}"/>')
        p.append(f'<text class="reft" x="{ML + 6}" y="{y(ref[0]) - 6:.1f}">{esc(ref[1])}</text>')
    for name, slot, raw, _shown in series:
        pts = " ".join(f"{xs[i]:.1f},{y(v):.1f}" for i, v in enumerate(raw))
        p.append(f'<polyline class="ln s{slot}" points="{pts}"/>')
        for i, v in enumerate(raw):
            p.append(f'<circle class="pt s{slot}" cx="{xs[i]:.1f}" cy="{y(v):.1f}" r="4"/>')
    p.append(f'<line class="cross" x1="0" x2="0" y1="{MT}" y2="{H - MB}"/>')
    band = pw / (n - 1)
    for i in range(n):
        x0, x1 = max(ML - 6, xs[i] - band / 2), min(W - MR + 6, xs[i] + band / 2)
        p.append(f'<rect class="hit" data-i="{i}" data-x="{xs[i]:.1f}" x="{x0:.1f}" y="{MT}" '
                 f'width="{x1 - x0:.1f}" height="{ph}"/>')
    p.append("</svg>")
    tip = {"x": xlabels, "unit": unit, "rows": [{"name": nm, "slot": sl, "vals": sh} for nm, sl, _r, sh in series]}
    legend = "".join(f'<span class="lg"><i class="sw s{sl}"></i>{esc(nm)}</span>' for nm, sl, _r, _s in series)
    head = "".join(f"<th>{esc(x)}</th>" for x in xlabels)
    rows = "".join(f"<tr><th>{esc(nm)}</th>" + "".join(f"<td>{esc(v)}{esc(unit)}</td>" for v in sh) + "</tr>"
                   for nm, _sl, _r, sh in series)
    return (f'<figure class="chart" id="{cid}" data-tip="{esc(json.dumps(tip))}">'
            f'<figcaption>{esc(title)}</figcaption><div class="legend">{legend}</div>'
            f'<div class="plot">{"".join(p)}<div class="tip" hidden></div></div>'
            f'<details><summary>Table view</summary><div class="scroll"><table class="data"><tr><th>{esc(xtitle)}</th>{head}</tr>'
            f'{rows}</table></div></details></figure>')


def interval_chart(title, rows, lo, hi, threshold, tlabel):
    """rows: [(label, point, low, high, shown)]. One dot with its interval per row, against a threshold line."""
    rh, left, right, top = 34, 190, 250, 26
    w = 720
    pw = w - left - right
    h = top + rh * len(rows) + 8

    def x(v):
        return left + pw * (v - lo) / (hi - lo)

    p = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">',
         f'<line class="ref" x1="{x(threshold):.1f}" x2="{x(threshold):.1f}" y1="{top - 8}" y2="{h - 4}"/>',
         f'<text class="reft" x="{x(threshold):.1f}" y="{top - 12}" text-anchor="middle">{esc(tlabel)}</text>']
    for i, (label, pt, a, b, shown) in enumerate(rows):
        cy = top + rh * i + rh / 2
        p.append(f'<text class="rowl" x="{left - 12}" y="{cy + 4:.1f}" text-anchor="end">{esc(label)}</text>')
        p.append(f'<line class="grid" x1="{left}" x2="{left + pw}" y1="{cy:.1f}" y2="{cy:.1f}"/>')
        p.append(f'<line class="ci" x1="{x(a):.1f}" x2="{x(b):.1f}" y1="{cy:.1f}" y2="{cy:.1f}"/>')
        p.append(f'<circle class="pt s1" cx="{x(pt):.1f}" cy="{cy:.1f}" r="5"><title>{esc(label)}: {esc(shown)}</title></circle>')
        p.append(f'<text class="rowv" x="{left + pw + 12}" y="{cy + 4:.1f}">{esc(shown)}</text>')
    p.append("</svg>")
    return f'<figure class="chart"><figcaption>{esc(title)}</figcaption><div class="plot">{"".join(p)}</div></figure>'


def el_series(prefix, name, slot):
    raw = [V(f"{prefix}.{w}.share_known") for w in WAITS]
    shown = [F(f"{prefix}.{w}.share_known", "pct1") for w in WAITS]
    return (f"{name} ({F(prefix + '.w0.n_eventual')} reverts)", slot, [v * 100 for v in raw], shown)


def tile(value, label, note=""):
    return (f'<div class="tile"><div class="tv">{value}</div><div class="tl">{esc(label)}</div>'
            + (f'<div class="tn">{note}</div>' if note else "") + "</div>")


def ok(text):
    return f'<span class="ok">&#10003; {esc(text)}</span>'


def table(head, rows, cls="data"):
    return ('<div class="scroll"><table class="' + cls + '"><tr>' + "".join(f"<th>{esc(h)}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table></div>")


# ------------------------------------------------------------------------------------------------ page
def build() -> str:
    xl = wait_labels()
    pct_ticks = [(0, "0%"), (25, "25%"), (50, "50%"), (75, "75%"), (100, "100%")]
    one, two = F("one"), F("two")

    curve_all = line_chart(
        "c-all", "Share of eventual reverts already known, by wait after the edit (all editors)",
        [el_series("el.live.stream.all", "live, stream labels", 1),
         el_series("el.live_ext.stream.all", "live_ext, stream labels", 2),
         el_series("el.live.dump.all", "live, dump labels", 3),
         el_series("el.history.dump.all", "history, dump labels", 4)],
        xl, 100, pct_ticks, "%", "wait after the edit")

    def bar(key):
        return (f'<div class="bar"><i style="width:{V(key) * 100:.1f}%"></i></div><span>{F(key, "pct1")}%</span>')

    kind_rows = []
    for cid, src in [("live", "stream"), ("live_ext", "stream"), ("history", "dump")]:
        for kind, lab in [("all", "all editors"), ("registered", "registered"), ("temporary", "temporary accounts"), ("bot", "bots")]:
            k = f"el.{cid}.{src}.{kind}"
            kind_rows.append([f"{cid}, {src} labels" if kind == "all" else "", lab, F(k + ".w1h.n_eventual"),
                              bar(k + ".w1h.share_known"), bar(k + ".w1d.share_known")])
    kind_table = table(["Cohort", "Editor kind", "Eventual reverts", f"Known after {one} hour", f"Known after {one} day"], kind_rows, "data bars")

    cohorts = [("live", "live (primary)"), ("live_ext", "live_ext"), ("live_ext_october", "live_ext, October only"), ("history", "history")]

    def h1_rows(w):
        return [(lab, V(f"h1.{c}.known_{w}_pct"), V(f"h1.{c}.known_{w}_lo"), V(f"h1.{c}.known_{w}_hi"),
                 f"{F(f'h1.{c}.known_{w}_pct', '.2f')}% ({F(f'h1.{c}.known_{w}_lo', '.2f')} to {F(f'h1.{c}.known_{w}_hi', '.2f')})")
                for c, lab in cohorts]
    t1, t48 = V("h1_threshold_1h_pct"), V("h1_threshold_48h_pct")
    h1a = interval_chart(f"Known after {one} hour, with {F('ci_level_pct')}% intervals", h1_rows("1h"), t1 - 8, t1 + 2, t1,
                         f"threshold {F('h1_threshold_1h_pct')}%")
    h1b = interval_chart(f"Known after {F('h1_wait_long_h')} hours, with {F('ci_level_pct')}% intervals", h1_rows("48h"), t48 - 4, t48 + 1, t48,
                         f"threshold {F('h1_threshold_48h_pct')}%")
    r1, r48 = h1_rows("1h"), h1_rows("48h")
    h1_verdicts = table(["Cohort", "Pages", "Eventual reverts", f"Known after {one} hour", f"Known after {F('h1_wait_long_h')} hours", "Verdict"],
                        [[esc(lab), F(f"h1.{c}.pages"), F(f"h1.{c}.eventual_reverts"), esc(r1[i][4]), esc(r48[i][4]), esc(V(f"h1.{c}.verdict"))]
                         for i, (c, lab) in enumerate(cohorts)])

    h3 = table(["Group of edits (live cohort)", "Reverts", f"E(L) after {one} hour", f"{F('ci_level_pct')}% interval"],
               [[f"Edits made during a burst, on {F('h3.live.w1h.burst_pages')} pages", F("h3.live.w1h.burst_reverts"), F("h3.live.w1h.e_burst", ".4f"),
                 f"{F('h3.live.w1h.e_burst_lo', '.4f')} to {F('h3.live.w1h.e_burst_hi', '.4f')}"],
                ["All other edits", F("h3.live.w1h.rest_reverts"), F("h3.live.w1h.e_rest", ".4f"),
                 f"{F('h3.live.w1h.e_rest_lo', '.4f')} to {F('h3.live.w1h.e_rest_hi', '.4f')}"]])
    h4 = table(["Cohort", "Pages", "Pages with an edit under an older title", "Share", "Verdict"],
               [[c, F(f"h4.{c}.pages"), F(f"h4.{c}.pages_affected"), F(f"h4.{c}.pages_affected_pct") + "%", esc(V(f"h4.{c}.verdict"))]
                for c in ("history", "live_ext")])

    rates = ["rate1000", "rate2500", "rate5000", "rate10000", "rate20000"]
    sss = line_chart(
        "c-sss", "Structured Streaming: latency by input rate (events per second)",
        [("median latency", 1, [V(f"sss.{r}.latency_p50_s") for r in rates], [F(f"sss.{r}.latency_p50_s") for r in rates]),
         ("95th percentile latency", 2, [V(f"sss.{r}.latency_p95_s") for r in rates], [F(f"sss.{r}.latency_p95_s") for r in rates])],
        [F(f"sss.{r}.rate") for r in rates], 6, [(i, f"{i} s") for i in range(0, 7, 2)], " s", "input rate, events per second",
        ref=(V("e5_latency_limit_s"), f"limit: {F('e5_latency_limit_s')} s"))

    hll = table(["Sketch", "Memory (bytes)", "Distinct pages: mean error", "Distinct editors: mean error"],
                [[name, F(f"algos.{k}.pages.bytes"), F(f"algos.{k}.pages.mean_err_pct", ".2f") + "%", F(f"algos.{k}.editors.mean_err_pct", ".2f") + "%"]
                 for name, k in [("HyperLogLog", "hll_p10"), ("HyperLogLog", "hll_p12"), ("HyperLogLog", "hll_p14"),
                                 ("Flajolet-Martin", "fm_m64"), ("Flajolet-Martin", "fm_m1024")]])
    ams = table(["AMS variables", f"Mean absolute error of the second moment ({F('moments.seeds')} seeds)"],
                [[F(f"moments.ams.{v}.variables"), F(f"moments.ams.{v}.mean_abs_error_pct") + "%"] for v in ("v100", "v1000", "v10000")])
    lap = table(["Series", "Eventual reverts", f"epsilon {F('privacy.eps_low')}", f"epsilon {F('privacy.eps_mid')}", f"epsilon {F('privacy.eps_high')}"],
                [[lab, F(f"privacy.laplace.{k}.n")] + [F(f"privacy.laplace.{k}.mae.{e}", ".5f") for e in ("eps_low", "eps_mid", "eps_high")]
                 for lab, k in [("live_ext, all editors", "live_ext.stream.all"), ("live, all editors", "live.stream.all"),
                                ("live, temporary accounts", "live.stream.temporary"), ("live, bots", "live.stream.bot")]])
    recon = table(["Stream label", "Dump label", "Revisions", "Share"],
                  [["reverted", "reverted", F("recon.live.both_reverted"), F("recon.live.both_reverted.pct") + "%"],
                   ["not reverted", "not reverted", F("recon.live.neither"), F("recon.live.neither.pct") + "%"],
                   ["reverted", "not reverted", F("recon.live.stream_only"), F("recon.live.stream_only.pct") + "%"],
                   ["not reverted", "reverted", F("recon.live.dump_only"), F("recon.live.dump_only.pct") + "%"]])

    m = R["meta"]
    body = f"""
<header>
  <p class="eyebrow">DATA 226 · Group 9 · term project</p>
  <h1>TruthLag: how fast do live Wikipedia revert counts catch up with the truth?</h1>
  <p class="lede">An edit that will be reverted looks fine at first. This page shows how long a live count has to wait
  before it agrees with the reconciled history, measured on a Bronze, Silver and Gold Delta lake built from the captured
  event streams and two History snapshots.</p>
  <p class="stamp">Every number is filled from <code>docs/final/results.json</code> at commit <code>{esc(m['commit_short'])}</code>
  (generated {esc(m['generated_at_utc'])}). Technique sections marked "fallback" are replaced when a teammate's notebook arrives.</p>
</header>

<section class="tiles">
  {tile(F('h1.live.known_1h_pct') + '%', f'of eventual reverts are known {one} hour after the edit', f"live cohort, {F('h1.live.eventual_reverts')} reverts")}
  {tile(F('h1.live.known_48h_pct') + '%', f"are known after {F('h1_wait_long_h')} hours", f"horizon: {F('horizon_days')} days")}
  {tile(F('recon.live.agreement_pct') + '%', 'of live revisions get the same label from the stream and from the dump', f"{F('recon.live.total')} revisions")}
  {tile(F('gold_checks.ext.passed') + ' of ' + F('gold_checks.ext.total'), 'Gold checks pass', ok(f"{F('tests.passed')} automated tests pass"))}
</section>

<section>
  <h2>The pipeline</h2>
  <div class="flow">
    <div class="box"><b>Raw files</b><span>{F('streams')} captured event streams</span><span>{F('snapshots')} History snapshots</span></div>
    <div class="arrow" aria-hidden="true">&rarr;</div>
    <div class="box"><b>Bronze</b><span>{F('bronze.stream_rows_total')} stream lines, nothing dropped</span><span>{F('bronze.history_slim.rows')} dump rows</span><em>delta-rs</em></div>
    <div class="arrow" aria-hidden="true">&rarr;</div>
    <div class="box"><b>Silver</b><span>{F('silver.page_change.rows')} parsed page changes</span><span>{F('silver.live_ext_revisions.rows')} revisions in the largest cohort</span><em>delta-rs</em></div>
    <div class="arrow" aria-hidden="true">&rarr;</div>
    <div class="box"><b>Gold</b><span>{F('gold.tables')} tables, star schema</span><span>{F('gold.fact_edit.rows')} edit facts, {F('gold.dim_page.rows')} page versions</span><em>Spark SQL</em></div>
  </div>
  <p class="note">Gold is built "as of" {F('asof_builds')} knowledge dates, so the lake can answer what it believed then against what it believes now.
  A rebuild into an empty lake folder took {F('runtime.rebuild_e2e_s')} seconds (the dump filter step and the extras were skipped).</p>
</section>

<section>
  <h2>Is the lake right?</h2>
  <ul class="checks">
    <li>{ok('Bronze')} line counts inside the published parse cut equal the published ones for all {F('parity.bronze.streams_equal')} streams.</li>
    <li>{ok('Silver and cohorts')} {F('parity.silver.tables_equal')} Silver tables and {F('parity.cohort.tables_equal')} of {F('parity.cohort.tables')} cohort tables, at the published cut, equal the published tables value for value ({F('zero')} differences).</li>
    <li>{ok('Gold')} {F('gold_checks.ext.passed')} of {F('gold_checks.ext.total')} checks pass at the latest build, {F('gold_checks.parity.passed')} of {F('gold_checks.parity.total')} at the parity build.</li>
    <li>{ok('Second snapshot')} {F('snapshot.late_reverts.exact.confirmed')} of {F('snapshot.late_reverts.exact.n')} late reverts of the exact class (reverts the stream marked exactly) are confirmed by the newer dump.</li>
  </ul>
</section>

<section>
  <h2>The truth-lag curve</h2>
  <p class="note">The error E(L) is one minus the share shown: the part of the eventual reverts that a count taken after wait L still misses.
  The horizontal positions are the {F('wait_points')} measured waits, evenly spaced, not a time scale.</p>
  {curve_all}
  <h3>By editor kind</h3>
  {kind_table}
  <p class="note">Reverts of bot edits are few (see the counts), so their shares are rough.</p>
</section>

<section>
  <h2>Hypotheses</h2>
  <h3>H1: the lag has a long tail (fewer than {F('h1_threshold_1h_pct')}% of eventual reverts known after {one} hour, and fewer than {F('h1_threshold_48h_pct')}% after {F('h1_wait_long_h')} hours)</h3>
  <p class="note">Intervals come from a bootstrap over pages ({F('bootstrap_B')} resamples). The dashed line is the threshold set before the data was seen. "Not falsified" means both shares stay below their line; a share above its line falsifies H1.</p>
  {h1a}{h1b}{h1_verdicts}
  <h3>H3: edits made during a burst are slower to settle</h3>
  {h3}
  <p class="note">A burst means the page had {F('burst_min_edits')} or more edits in the hour before. Verdict for the live cohort: {esc(V('h3.live.w1h.verdict'))}. The burst estimate is lower, not higher, but the intervals overlap. In the larger cohorts the verdicts are: live_ext, {esc(V('h3.live_ext.w1h.verdict'))}; history, {esc(V('h3.history.w1h.verdict'))}.</p>
  <h3>H4: keeping page versions changes the counts</h3>
  {h4}
  <p class="note">The floor was {F('h4_floor_pct')}% of pages. It was set after seeing the data, which the report states as a limitation.</p>
</section>

<section>
  <h2>Then against now</h2>
  <div class="tiles">
    {tile(F('tt.asof.early.reverted_known') + ' &rarr; ' + F('tt.asof.parity.reverted_known'), 'reverts known in the live cohort, early build against later build', f"{F('tt.asof.updates')} rows in the change data feed")}
    {tile(F('tt.snapshot.2026_09.reverted_then') + ' &rarr; ' + F('tt.snapshot.2026_09.reverted_now'), 'reverts in the history cohort, first snapshot against second', f"{F('tt.snapshot.added_reverted')} added")}
    {tile(F('snapshot.label_change.became_reverted'), 'revisions in the whole dump (all namespaces) became reverted between the snapshots', f"{F('snapshot.label_change.became_unreverted')} went the other way")}
  </div>
  <h3>Stream labels against dump labels, live cohort</h3>
  {recon}
</section>

<section>
  <h2>Streaming algorithms against exact answers</h2>
  <p class="note">Exact answers on the same stream: {F('algos.exact.pages')} distinct pages and {F('algos.exact.editors')} distinct editors. Errors are means over {F('hash_salts')} hash functions.</p>
  {hll}
  <ul>
    <li>Bloom filter: all {F('algos.bloom.fp001.exact_repeats')} repeated events found, {F('algos.bloom.fp001.false_negatives')} missed.</li>
    <li>DGIM, reverts in the last hour: mean error {F('algos.dgim.wiki.r4.mean_rel_error_pct')}% with at most {F('algos.dgim.wiki.r4.max_buckets')} buckets.</li>
    <li>Reservoir sample of {F('reservoir_k')} edits: revert share {F('algos.reservoir.sample_pct')}% against the exact {F('algos.reservoir.exact_pct')}%.</li>
  </ul>
  {ams}
</section>

<section>
  <h2>Structured Streaming</h2>
  {sss}
  <p class="note">Without a rate limit the query drains {F('sss.drain.events')} events at {F('sss.drain.throughput_eps')} events per second and its output equals
  the batch tables ({F('sss.drain.differing')} differing rows). The captured stream itself averages about {F('sss.capture_mean_eps')} events per second.</p>
</section>

<section>
  <h2>Locality-sensitive hashing <span class="tag">fallback</span></h2>
  <div class="tiles">
    {tile(F('lsh.recall_pct.tables5') + '%', f"recall against an exact join with {F('lsh.hash_tables')} hash tables, on a sample of {F('lsh.sample_texts')} texts", f"{F('lsh.seconds.tables5')} seconds against {F('lsh.exact_join_seconds')}")}
    {tile(F('lsh.labels.by_group.same_pattern') + ' of ' + F('lsh.labels.by_group.pairs'), 'labeled pairs are the same edit pattern (one pair per group)', f"{F('lsh.labels.by_band.same_pattern')} of {F('lsh.labels.by_band.pairs')} by similarity band")}
    {tile(F('lsh.not_reverted.reuses_pct') + '%', 'of edits that were not reverted reuse a summary', f"{F('lsh.reverted.reuses_pct')}% of reverted edits")}
  </div>
  <p class="note">MinHash LSH on {F('lsh.distinct_texts')} distinct edit summaries. The pairs were labeled by Claude Code, not by a person ({F('lsh.labels.by_person')} re-checked so far); this is disclosed in the GenAI log.</p>
</section>

<section>
  <h2>Privacy <span class="tag">fallback</span></h2>
  <div class="tiles">
    {tile(F('privacy.grid.k5.rows_below_pct') + '%', f"of hourly cells have fewer than {F('privacy.k')} editors", f"suppressing them keeps {F('privacy.grid.k5.edits_kept_pct')}% of edits")}
    {tile(F('privacy.page.single_editor_pct') + '%', 'of page-level rows have a single editor', 'the page-level table is not safe to release as it is')}
    {tile(F('privacy.suppress.live_ext.ruleA.true_revert_rate_pct') + '% &rarr; ' + F('privacy.suppress.live_ext.ruleA.released_revert_rate_pct') + '%', 'revert rate before and after suppressing small page rows', 'suppression alone biases the release upward')}
  </div>
  <h3>Mean absolute error of E(L) under Laplace noise</h3>
  {lap}
  <p class="note">{F('privacy.laplace.trials')} trials per epsilon. The noise barely moves the main series and swamps the bot series.</p>
</section>

<section>
  <h2>Run it yourself</h2>
  <p class="note">From the repository root, with <code>TRUTHLAG_HW2_DIR=$PWD/ec-hw2</code> set.</p>
  <ul class="cmds">
    <li><code>.venv-lake/bin/python -m etl.time_travel</code> then against now, on the real tables</li>
    <li><code>.venv-lake/bin/python -m etl.stream_sss</code> the Bronze-to-Silver step as a streaming query</li>
    <li><code>.venv-lake/bin/python scripts/check_numbers.py</code> every reported number against the lake</li>
    <li><code>bash etl/build_all.sh</code> the whole lake from the raw files</li>
  </ul>
</section>

<footer>Built by <code>scripts/make_dashboard.py</code>. Edit comments and editor names are not shown anywhere on this page.</footer>
"""
    return PAGE.replace("@@BODY@@", body)


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TruthLag Results</title>
<style>
:root{--bg:#f6f5f1;--surface:#fcfcfb;--text:#0b0b0b;--text2:#52514e;--muted:#898781;--grid:#e1e0d9;--border:#dddbd2;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--good:#006300;--accent:#184f95}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#121211;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--border:#33332f;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--good:#0ca30c;--accent:#86b6ef}}
:root[data-theme="dark"]{--bg:#121211;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--border:#33332f;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--good:#0ca30c;--accent:#86b6ef}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
header{margin-bottom:28px}
.eyebrow{margin:0 0 8px;color:var(--text2);font-size:13px;letter-spacing:.06em;text-transform:uppercase}
h1{margin:0 0 12px;font-size:clamp(26px,4.2vw,38px);line-height:1.15;letter-spacing:-.01em;text-wrap:balance}
h2{margin:0 0 14px;font-size:22px}
h3{margin:22px 0 10px;font-size:16px}
.lede{margin:0 0 10px;max-width:68ch;font-size:18px;color:var(--text2)}
.stamp,.note,footer{color:var(--text2);font-size:14px;max-width:80ch}
section{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:22px;margin:0 0 18px}
section.tiles{background:none;border:0;padding:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px}
section .tile{background:var(--bg)}
.tv{font-size:28px;font-weight:650;line-height:1.1;font-variant-numeric:tabular-nums}
.tl{margin-top:6px;font-size:14px}
.tn{margin-top:6px;font-size:13px;color:var(--text2)}
.ok{color:var(--good);font-weight:600}
.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px}
.box{flex:1 1 170px;border:1px solid var(--border);border-radius:8px;padding:12px;background:var(--bg);display:flex;flex-direction:column;gap:4px;font-size:14px}
.box b{font-size:16px}.box em{margin-top:auto;color:var(--text2);font-size:12px;font-style:normal;text-transform:uppercase;letter-spacing:.05em}
.arrow{align-self:center;color:var(--muted);font-size:20px}
.checks,.cmds{padding-left:0;list-style:none;margin:0}.checks li,.cmds li{margin:6px 0}
figure{margin:14px 0}figcaption{font-weight:600;margin-bottom:6px}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--text2);margin-bottom:4px}
.lg{display:inline-flex;align-items:center;gap:6px}.sw{width:14px;height:3px;border-radius:2px;display:inline-block}
.plot{position:relative}svg{display:block;width:100%;height:auto;overflow:visible}
.grid{stroke:var(--grid);stroke-width:1}.ax,.axt{fill:var(--text2);font-size:11px}.rowl,.rowv{fill:var(--text);font-size:12px}
.rowv{font-variant-numeric:tabular-nums}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}.pt{stroke:var(--surface);stroke-width:2}
.s1{stroke:var(--s1)}.s2{stroke:var(--s2)}.s3{stroke:var(--s3)}.s4{stroke:var(--s4)}
circle.s1,i.s1{fill:var(--s1);background:var(--s1)}circle.s2,i.s2{fill:var(--s2);background:var(--s2)}
circle.s3,i.s3{fill:var(--s3);background:var(--s3)}circle.s4,i.s4{fill:var(--s4);background:var(--s4)}
circle.pt{stroke:var(--surface)}
.ref{stroke:var(--text2);stroke-width:1;stroke-dasharray:4 4}.reft{fill:var(--text2);font-size:11px}
.ci{stroke:var(--s1);stroke-width:2;stroke-linecap:round}
.cross{stroke:var(--muted);stroke-width:1;visibility:hidden}.hit{fill:transparent}
.tip{position:absolute;top:8px;pointer-events:none;background:var(--surface);border:1px solid var(--border);border-radius:8px;
padding:8px 10px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.14);min-width:190px;max-width:calc(100% - 8px);z-index:2}
.tip b{display:block;margin-bottom:4px}.tip div{display:flex;align-items:center;gap:6px}.tip span{white-space:nowrap}
.tip span{margin-left:auto;padding-left:12px;font-variant-numeric:tabular-nums;font-weight:600}
details{margin-top:6px;font-size:13px}summary{cursor:pointer;color:var(--accent)}
.scroll{overflow-x:auto}
table{border-collapse:collapse;font-size:14px;margin:6px 0;min-width:100%}
th,td{padding:6px 10px;border-bottom:1px solid var(--grid);text-align:left;vertical-align:top}
td{font-variant-numeric:tabular-nums}tr:first-child th{color:var(--text2);font-weight:600;font-size:13px}
.bars td{white-space:nowrap}.bar{display:inline-block;vertical-align:middle;width:min(180px,32vw);height:8px;background:var(--grid);border-radius:4px;margin-right:8px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--s1);border-radius:0 4px 4px 0}
.tabs{display:flex;gap:6px;margin:18px 0 0}
.tab{font:inherit;font-size:13px;padding:5px 12px;border-radius:999px;border:1px solid var(--border);background:var(--bg);color:var(--text);cursor:pointer}
.tab[aria-pressed="true"]{background:var(--text);color:var(--surface);border-color:var(--text)}
.tab:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tag{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;border:1px solid var(--border);border-radius:999px;padding:2px 8px;color:var(--text2);vertical-align:middle}
code{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:1px 5px;overflow-wrap:anywhere}
footer{margin-top:20px}
@media (max-width:640px){.arrow{display:none}section{padding:16px}}
</style>
</head>
<body>
<main>
@@BODY@@
</main>
<script>
document.querySelectorAll('figure.chart[data-tip]').forEach(function (fig) {
  var d = JSON.parse(fig.dataset.tip), tip = fig.querySelector('.tip'), cross = fig.querySelector('.cross'),
      svg = fig.querySelector('svg'), plot = fig.querySelector('.plot');
  function hide() { tip.hidden = true; cross.style.visibility = 'hidden'; }
  fig.querySelectorAll('.hit').forEach(function (r) {
    r.addEventListener('pointerenter', function () {
      var i = +r.dataset.i, x = +r.dataset.x;
      cross.setAttribute('x1', x); cross.setAttribute('x2', x); cross.style.visibility = 'visible';
      tip.textContent = '';
      var b = document.createElement('b'); b.textContent = d.x[i]; tip.appendChild(b);
      d.rows.forEach(function (row) {
        var div = document.createElement('div'), sw = document.createElement('i'), v = document.createElement('span');
        sw.className = 'sw s' + row.slot; v.textContent = row.vals[i] + d.unit;
        div.appendChild(sw); div.appendChild(document.createTextNode(row.name)); div.appendChild(v); tip.appendChild(div);
      });
      tip.hidden = false;
      var w = plot.clientWidth, px = x / svg.viewBox.baseVal.width * w, tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(w - tw, px > w / 2 ? px - tw - 12 : px + 12)) + 'px';
    });
  });
  svg.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse') hide(); });
  document.addEventListener('pointerdown', function (e) { if (!fig.contains(e.target)) hide(); });
});
document.querySelectorAll('.tab').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.tab').forEach(function (b) { b.setAttribute('aria-pressed', String(b === btn)); });
    document.querySelectorAll('.pane').forEach(function (p) { p.hidden = p.dataset.pane !== btn.dataset.show; });
  });
});
</script>
</body>
</html>
"""


def visible_text(page: str) -> str:
    """The page as a reader sees it: no style or script, no axis tick labels, code spans kept as code."""
    t = re.sub(r"(?s)<(style|script)\b.*?</\1>", " ", page)
    t = re.sub(r'(?s)<text class="ax"[^>]*>.*?</text>', " ", t)
    t = re.sub(r"(?s)<code>(.*?)</code>", lambda m: "`" + re.sub(r"\s+", " ", m.group(1)) + "`", t)
    t = re.sub(r"</t[dh]>", " | ", t)
    t = re.sub(r"<(?:/p|/li|/h\d|/tr|/div|/figcaption|/text|/summary|br)\b[^>]*>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(t)


def check(page: str) -> int:
    bad = 0
    if not OUT.exists() or OUT.read_text() != page:
        print(f"MISMATCH {OUT.name} is not what scripts/make_dashboard.py renders from results.json: run it again")
        bad += 1
    text = visible_text(page)
    toks = tn.number_tokens(text)
    for b in tn.unmatched_tokens(text, R):
        print(f"MISMATCH {OUT.name}: {b['text']!r} is not in results.json   | {b['context']}")
        bad += 1
    kb = len(page.encode()) / 1024
    print(f"{'ok ' if not bad else 'BAD'} {OUT.relative_to(tn.REPO)}: {kb:.0f} KB, {len(toks)} number tokens, "
          f"{bad} problems, results.json at commit {R['meta']['commit_short']}")
    return 1 if bad else 0


def main() -> int:
    page = build()
    if "--check" not in sys.argv:
        OUT.write_text(page)
    return check(page)


if __name__ == "__main__":
    raise SystemExit(main())
