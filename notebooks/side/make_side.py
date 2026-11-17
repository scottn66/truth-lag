"""Build, run and export the side notebook on mutually reverting editor pairs.

SIDE ANALYSIS: outside the checked numbers. It writes notebooks/side/mutual_reverts_results.json and nothing under
data/lake/_runs, so scripts/make_results.py, the report, the slides and the dashboard do not see it. It is not in
the code zip or in dist/notebooks (scripts/make_bundle.sh lists notebooks/final and notebooks/fallback only). The repo
zip holds every tracked file, so it would include notebooks/side once these files are committed.

Run (from the repository root, lake environment)
    .venv-lake/bin/python notebooks/side/make_side.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).resolve().parent
NBCONVERT = str(Path(sys.executable).parent / "jupyter-nbconvert")

CELLS = [
    ("md", """# Side analysis: mutually reverting editor pairs

**Status.** Side analysis, written with Claude Code. It is **not** part of the checked numbers: nothing here is in `docs/final/results.json`, the report, the slides or the dashboard. Results are saved to `notebooks/side/mutual_reverts_results.json`.

**Question.** On pages where two editors revert each other, do revert labels become known sooner or later than elsewhere?

**Definitions** (after Yasseri, Sumi, Rung, Kornai, Kertesz 2012, *Dynamics of conflicts in Wikipedia*, PLoS ONE 7(6) e38869).
- *Mutual pair*: two editors A and B on one page where A reverted B and B reverted A.
- *M*: E x the sum over the page's mutual pairs, leaving out the largest, of min(N_A, N_B). E = editors in mutual pairs, N = the editor's edit count on the page.

**Where this differs from the paper.**
- N is counted only inside the data window (3 days, 20 days or 7 weeks), not over the page's whole history. It is a "window M".
- Stream cohorts take reverts from MediaWiki revert events (undo, rollback, manual). The dump takes them from identical page content (SHA-1).
- A pair is seen only if both reverted edits fall inside the window.

**Data.** Silver revert-link tables (one row per reverted revision, with the reverting and the reverted editor) and `silver/history_slim` (dump, September and October 2026). English Wikipedia, article namespace.

**Privacy.** Editor keys in the lake are not hashed. They are used here only to test whether two rows have the same editor. No key, name, comment or page title is printed or saved; every output is a count or a share."""),
    ("code", """import json, os, sys
from pathlib import Path
REPO = Path.cwd().resolve().parents[1] if Path.cwd().name == 'side' else Path.cwd()
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / 'notebooks' / 'side'))
os.environ.setdefault('TRUTHLAG_HW2_DIR', str(REPO / 'ec-hw2'))
os.environ['TZ'] = 'UTC'
import numpy as np, pandas as pd
import pyarrow.compute as pc
from deltalake import DeltaTable
pd.set_option('display.width', 200); pd.set_option('display.max_columns', 30)
import mutual_reverts_lib as mr
from etl.hypotheses import poisson_ci, poisson_diff_ci, SEED, B, BURST_MIN
from etl.hw2 import config
SILVER = REPO / 'data' / 'lake' / 'silver'
H = config.LIVE_FOLLOWUP_S
rng = np.random.default_rng(SEED)
FACTS = {}
mr.self_test()
TABLES = ['history_revert_links', 'live_revert_links', 'live_ext_revert_links', 'history_revisions', 'live_revisions', 'live_ext_revisions', 'history_slim']
VERSIONS = {t: DeltaTable(str(SILVER / t)).version() for t in TABLES}
print('Delta table versions read:', VERSIONS)
print('bootstrap draws:', B, '| seed:', SEED, '| follow-up window:', H, 's')"""),
    ("md", """## 1. How many mutual pairs

`history` is the dump cohort (edits of Sep 8-10). `live_ext` is the stream cohort (edits of Oct 20 - Nov 8). `live` (Oct 20-22) is the first three days of `live_ext`, so it is not an independent sample; it shows the effect of a shorter window.

Rows of the table: the base count, then the same count under stricter rules."""),
    ("code", """LCOLS = ['reverted_rev_id', 'reverting_rev_id', 'page_id', 'author_key', 'author_kind', 'reverter_key', 'reverter_kind', 'T_s', 'K_s', 'by_other', 'within_followup', 'range_size']
COHORTS = {'history': ('history_revert_links', 'history_revisions'), 'live': ('live_revert_links', 'live_revisions'), 'live_ext': ('live_ext_revert_links', 'live_ext_revisions')}
links, revs = {}, {}
for c, (lt, rt) in COHORTS.items():
    links[c] = DeltaTable(str(SILVER / lt)).to_pandas(columns=LCOLS)
    revs[c] = DeltaTable(str(SILVER / rt)).to_pandas(columns=['rev_id', 'page_id', 'user_key', 'page_edits_prev_1h'])
    assert not links[c].reverted_rev_id.duplicated().any()
    assert (links[c].by_other.fillna(False).astype(bool) == (links[c].author_key.notna() & links[c].reverter_key.notna() & (links[c].author_key != links[c].reverter_key))).all()

VARIANTS = [('base: reverter is not the author', {}), ('no bots', {'no_bots': True}), ('registered editors only', {'registered_only': True}),
            ('revert undid exactly one revision', {'single_only': True}), ('revert inside the 4-day follow-up', {'followup_only': True})]
rows = []
for c in COHORTS:
    for name, kw in VARIANTS:
        if kw.get('single_only') and links[c].range_size.isna().all():
            continue   # the dump has no range size
        r = mr.counts(links[c], **kw)
        rows.append({'cohort': c, 'rule': name, **r})
        FACTS[f'{c}.{name}'] = r
counts_df = pd.DataFrame(rows).drop(columns=['link_rows'])
for c in COHORTS:
    FACTS[f'{c}.cohort_pages'] = int(revs[c].page_id.nunique())
    print(c, '| link rows', len(links[c]), '| cohort pages', FACTS[f'{c}.cohort_pages'])
counts_df"""),
    ("md", """## 2. Who is in the pairs, and how many pairs per page

Pairs are split by the account kind of the two editors. The data does not say what a pair disagreed about. Temporary accounts can change key over time, so pairs with them are undercounted."""),
    ("code", """kind_rows = []
for c in COHORTS:
    m = mr.mutual_pairs(mr.usable_links(links[c]))
    vc = m.pair_kind.value_counts()
    for k, v in vc.items():
        kind_rows.append({'cohort': c, 'pair kind': k, 'mutual pairs': int(v), 'share %': round(100 * v / len(m), 1)})
    FACTS[f'{c}.pair_kinds'] = {k: int(v) for k, v in vc.items()}
pd.DataFrame(kind_rows).pivot(index='pair kind', columns='cohort', values='mutual pairs').fillna(0).astype(int)[list(COHORTS)]"""),
    ("code", """m_rows = []
for c in COHORTS:
    m = mr.mutual_pairs(mr.usable_links(links[c]))
    n_edits = revs[c].groupby(['page_id', 'user_key']).size()
    M, missing = mr.window_m(m, n_edits)
    pos = M[M > 0]
    r = {'cohort': c, 'mutual pages': int(len(M)), 'pages with window M = 0': int((M == 0).sum()), 'pages with window M > 0': int(len(pos)),
         'median M where > 0': float(pos.median()) if len(pos) else None, 'largest M': float(M.max()),
         'pairs where an editor has no counted edit (N set to 1)': missing}
    m_rows.append(r); FACTS[f'{c}.window_M'] = r
print('Window M is 0 on any page with a single mutual pair, because the formula leaves out the largest pair.')
pd.DataFrame(m_rows)"""),
    ("md", """## 3. Truth lag on pages with a mutual pair (flag from the same window)

E(L) is the share of eventual reverts **not yet known** after waiting L. Lower means known sooner. Intervals are 95% Poisson-bootstrap intervals over pages, with the project's own code (`etl.hypotheses.poisson_ci`).

Three page groups: pages with a mutual pair; other pages with two or more revert events by another editor (a mutual pair needs at least two revert events; a rollback of several edits is one event); all remaining pages (one such event, or only self-reverts). The difference column compares against the two-or-more group. The flag uses every link in the table, including reverts after the 4-day follow-up.

The second table shows how the groups differ in who wrote the reverted edits and in the share of self-reverts. E(L) differs by both, so a difference between groups cannot be put down to the flag alone.

**Read with care.** The flag is built from the same reverts that are being measured, so this is a description, not a test. For `history`, the dump gives the time to revert; only the stream cohorts measure when a label became known."""),
    ("code", """def frame_for(c):
    l = links[c]
    f = l[(l.T_s >= 0) & (l.T_s <= H)].merge(revs[c][['rev_id', 'page_edits_prev_1h']], left_on='reverted_rev_id', right_on='rev_id')
    return f.assign(known_after_s=f.T_s.astype(float) + f.K_s.fillna(0).astype(float))

def composition(f, group_of_page, default):
    g = f.assign(group=f.page_id.map(group_of_page).fillna(default), temp=f.author_kind == 'temporary', reg=f.author_kind == 'registered',
                 bot=f.author_kind == 'bot', self_rev=~f.by_other.fillna(False).astype(bool))
    t = g.groupby('group').agg(reverts=('temp', 'size'), temporary_author_pct=('temp', 'mean'), registered_author_pct=('reg', 'mean'),
                               bot_author_pct=('bot', 'mean'), self_revert_pct=('self_rev', 'mean'))
    t[t.columns[1:]] = (100 * t[t.columns[1:]]).round(1)
    return t.reset_index()
COMP_COLS = ['cohort', 'group', 'reverts', 'temporary_author_pct', 'registered_author_pct', 'bot_author_pct', 'self_revert_pct']

G3 = ['mutual pair', 'no mutual pair, 2+ revert events', 'all other pages']
def groups_in_window(c):
    d = mr.usable_links(links[c])
    mp = set(mr.mutual_pairs(d).page_id)
    n = d.groupby('page_id').reverting_rev_id.nunique()
    g = pd.Series(G3[1], index=n.index[n >= 2])
    g = pd.concat([g[~g.index.isin(mp)], pd.Series(G3[0], index=sorted(mp))])
    return g

frames = {c: frame_for(c) for c in COHORTS}
split_rows, comp_rows = [], []
for c in COHORTS:
    res = mr.el_split(frames[c], groups_in_window(c), G3, G3[1], G3[2], rng, poisson_ci, poisson_diff_ci)
    FACTS[f'{c}.E_by_in_window_flag'] = res
    split_rows += [{'cohort': c, 'measure': 'time to revert' if c == 'history' else 'time until the label is known', **r} for r in res]
    comp = composition(frames[c], groups_in_window(c), G3[2]); FACTS[f'{c}.composition_in_window_groups'] = comp.to_dict('records')
    comp_rows.append(comp.assign(cohort=c))
    print(c, '| eventual reverts in the frame:', len(frames[c]), '| pages:', frames[c].page_id.nunique())
pd.DataFrame(split_rows)"""),
    ("code", "pd.concat(comp_rows)[COMP_COLS]"),
    ("md", """## 4. Flag pages from an earlier period

Pages are flagged from the dump for **Sep 1 - Oct 19** (both the reverted edit and the revert before Oct 20). Truth lag is then measured on stream edits from **Oct 20** on. The flag uses no information from the measured period.

Groups: pages with a mutual pair in the earlier period; other pages with two or more revert events by another editor in the earlier period; all remaining pages. The last group includes pages with no edit at all in the earlier period (count printed below). The difference column compares against the two-or-more group."""),
    ("code", """CUT = pd.Timestamp('2026-10-20', tz='UTC')
assert all(DeltaTable(str(SILVER / t)).to_pandas(columns=['reverted_ts']).reverted_ts.min() >= CUT for t in ('live_revert_links', 'live_ext_revert_links'))
ds = DeltaTable(str(SILVER / 'history_slim')).to_pyarrow_dataset()
hs = ds.to_table(filter=(pc.field('snapshot') == '2026-10') & (pc.field('page_namespace') == 0),
                 columns=['revision_id', 'page_id', 'event_timestamp', 'revision_first_identity_reverting_revision_id', 'event_user_id', 'event_user_text', 'event_user_is_bot_by']).to_pandas()
assert not hs.revision_id.duplicated().any()
uid = hs.event_user_id.astype('Int64').astype('string')
hs['key'] = ('u:' + uid).where(hs.event_user_id.notna(), 't:' + hs.event_user_text)
is_bot = hs.event_user_is_bot_by.fillna('').str.len() > 0
# simpler rule than the lake's: any bot flag is a bot, any name starting with ~ is a temporary account
hs['kind'] = np.select([is_bot, hs.event_user_text.fillna('').str.startswith('~'), hs.event_user_id.notna()], ['bot', 'temporary', 'registered'], 'unknown')
print('dump revisions, article namespace, snapshot 2026-10:', len(hs), '| from', hs.event_timestamp.min(), 'to', hs.event_timestamp.max())
print('editor kinds:', hs.kind.value_counts().to_dict())

rv = hs[hs.revision_first_identity_reverting_revision_id.notna() & (hs.event_timestamp < CUT)]
look = hs.set_index('revision_id')[['key', 'kind', 'event_timestamp']].rename(columns={'key': 'reverter_key', 'kind': 'reverter_kind', 'event_timestamp': 'reverting_ts'})
pre = rv.rename(columns={'key': 'author_key', 'kind': 'author_kind'}).join(look, on='revision_first_identity_reverting_revision_id', how='left')
n_all = len(pre); n_missing = int(pre.reverting_ts.isna().sum()); n_late = int((pre.reverting_ts >= CUT).sum())
pre = pre[pre.reverting_ts < CUT].assign(range_size=np.nan, within_followup=True)
pre_use = mr.usable_links(pre)
pre_m = mr.mutual_pairs(pre_use)
pre_counts = mr.counts(pre)
n_pre = hs[hs.event_timestamp < CUT].groupby(['page_id', 'key']).size()
M, missing = mr.window_m(pre_m, n_pre)
FACTS['pre_period'] = {'window': 'reverted edit and revert both before 2026-10-20, dump snapshot 2026-10', 'first_dump_edit': str(hs.event_timestamp.min()),
                       'reverted_edits_before_cut': n_all, 'reverting_revision_not_in_table': n_missing, 'reverted_after_cut_dropped': n_late,
                       **pre_counts, 'pair_kinds': {k: int(v) for k, v in pre_m.pair_kind.value_counts().items()},
                       'pages_with_window_M_gt_0': int((M > 0).sum()), 'largest_window_M': float(M.max())}
print('reverted edits before Oct 20:', n_all, '| reverting revision not in the table:', n_missing, '| reverted on or after Oct 20 (dropped):', n_late)
print({k: v for k, v in pre_counts.items() if k != 'link_rows'})
print('pair kinds:', FACTS['pre_period']['pair_kinds'])
print('pages with window M > 0:', FACTS['pre_period']['pages_with_window_M_gt_0'], 'of', len(M), '| largest window M:', FACTS['pre_period']['largest_window_M'])"""),
    ("code", """P3 = ['mutual pair before Oct 20', 'no mutual pair, 2+ revert events before Oct 20', 'all other pages']
n = pre_use.groupby('page_id').revision_first_identity_reverting_revision_id.nunique()
pre_group = pd.Series(P3[1], index=n.index[n >= 2])
pre_group = pd.concat([pre_group[~pre_group.index.isin(set(pre_m.page_id))], pd.Series(P3[0], index=sorted(set(pre_m.page_id)))])
assert not pre_group.index.duplicated().any()
pre_rows, pre_comp = [], []
edited_before = set(hs[hs.event_timestamp < CUT].page_id)
for c in ('live_ext', 'live'):
    res = mr.el_split(frames[c], pre_group, P3, P3[1], P3[2], rng, poisson_ci, poisson_diff_ci)
    FACTS[f'{c}.E_by_pre_period_flag'] = res
    pre_rows += [{'cohort': c, **r} for r in res]
    comp = composition(frames[c], pre_group, P3[2]); FACTS[f'{c}.composition_pre_period_groups'] = comp.to_dict('records')
    pre_comp.append(comp.assign(cohort=c))
    fp = set(frames[c].page_id)
    FACTS[f'{c}.frame_pages_with_no_dump_edit_before_cut'] = len(fp - edited_before)
    print(c, '| pages in the frame:', len(fp), '| of those with no edit in the dump before Oct 20 (all in the last group):', len(fp - edited_before))
pd.DataFrame(pre_rows)"""),
    ("code", "pd.concat(pre_comp)[COMP_COLS]"),
    ("md", """## 5. Overlap with the burst flag of H3

H3 calls an edit a burst edit when its page had at least 10 edits in the hour before. A page counts here as a burst page if it has at least one reverted burst edit in the frame."""),
    ("code", """ov = []
for c in COHORTS:
    f = frames[c]
    burst_pages = set(f[f.page_edits_prev_1h.fillna(-1) >= BURST_MIN].page_id)
    mut_pages = set(mr.mutual_pairs(mr.usable_links(links[c])).page_id) & set(f.page_id)
    r = {'cohort': c, 'pages in the frame': int(f.page_id.nunique()), 'burst pages': len(burst_pages), 'mutual-pair pages': len(mut_pages), 'both': len(burst_pages & mut_pages)}
    if c != 'history':
        pm = set(pre_m.page_id) & set(f.page_id)
        r.update({'pages with a mutual pair before Oct 20': len(pm), 'of those, also a mutual pair in the window': len(pm & mut_pages)})
    ov.append(r); FACTS[f'{c}.overlap'] = r
pd.DataFrame(ov)"""),
    ("code", """out_path = REPO / 'notebooks' / 'side' / 'mutual_reverts_results.json'
out_path.write_text(json.dumps({'note': 'Side analysis. Not part of docs/final/results.json or any checked number.',
                                'delta_versions': VERSIONS, 'bootstrap_draws': B, 'seed': SEED, 'facts': FACTS}, indent=1, default=str))
print('wrote', out_path.relative_to(REPO), 'with', len(FACTS), 'entries')"""),
    ("md", """## Limits

- Side analysis: the numbers are not in `results.json` and are not covered by `scripts/check_numbers.py`.
- The flag in section 3 is built from the reverts it is compared on. Section 4 avoids this.
- `live` is part of `live_ext`. The independent samples are the September dump cohort and the October-November stream cohort.
- A pair is found only when both reverted edits are inside the window, so pairs are undercounted, more so in short windows.
- Temporary accounts can hold several keys over time, so pairs that involve them are undercounted.
- A rollback of several edits makes a link to each reverted author. The "exactly one revision" row in section 1 shows the count without these.
- Window M uses edit counts inside the window only and is 0 on every page with a single pair. It is not comparable with published values of M.
- Partial reverts that carry no revert tag and do not restore identical content are not seen.
- Section 3 compares groups in three cohorts (two of them overlap) at two waits, and section 4 in two cohorts at two waits, with no correction for multiple comparisons.
- The page groups differ in the kind of author and in the share of self-reverts (tables in sections 3 and 4), and E(L) differs by both. A group difference is not an effect of the flag.
- For `history`, E(L) is the share not yet reverted after L (time to revert). The dump has no label delay.
- The flag in section 4 misses pairs that began before Sep 1 or that straddle Oct 20, and pages with no edit before Oct 20 can only be in the last group.
- Section 4 labels editor kinds from the dump with a simpler rule than the lake (any bot flag is a bot; any name starting with ~ is a temporary account). Pair and page counts do not use the kind.
- Interval ends come from a finite number of bootstrap draws (printed in the first cell), so they carry some Monte Carlo noise.
- No edit text is used. A mutual pair shows that two editors undid each other, not what they disagreed about."""),
]


def build() -> None:
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "truthlag-lake", "display_name": "TruthLag lake (.venv-lake)", "language": "python"}
    nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in CELLS]
    path = HERE / "mutual_reverts.ipynb"
    nbf.write(nb, path)
    subprocess.run([NBCONVERT, "--to", "notebook", "--execute", "--inplace", "--ExecutePreprocessor.timeout=3600",
                    "--ExecutePreprocessor.kernel_name=truthlag-lake", str(path)], check=True, cwd=HERE)
    subprocess.run([NBCONVERT, "--to", "script", str(path)], check=True, cwd=HERE)
    print("ok ", path.relative_to(HERE.parents[1]))


if __name__ == "__main__":
    build()
