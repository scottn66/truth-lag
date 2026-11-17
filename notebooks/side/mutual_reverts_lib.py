"""Mutually reverting editor pairs: the functions behind notebooks/side/mutual_reverts.ipynb.

SIDE ANALYSIS. Nothing here feeds docs/final/results.json, the report, the slides or the dashboard.

Definitions (after Yasseri, Sumi, Rung, Kornai, Kertesz 2012, "Dynamics of conflicts in Wikipedia", PLoS ONE 7(6) e38869):
    revert link   one row per reverted revision: (page, reverting editor, reverted editor)
    mutual pair   two editors A and B on ONE page where A reverted B and B reverted A
    M             E * sum over the page's mutual pairs, leaving out the pair with the largest value, of min(N_A, N_B);
                  E = number of editors in mutual pairs on the page, N = the editor's edit count on the page.
                  Here N can only be counted inside the data window, so this is a "window M", not the published M.

Editor keys are compared for equality only. No function returns or prints a key, a name or a comment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WAITS = ((3600, "1 h"), (86400, "1 d"))


def usable_links(links: pd.DataFrame, *, no_bots: bool = False, registered_only: bool = False,
                 single_only: bool = False, followup_only: bool = False) -> pd.DataFrame:
    """Links that can form a pair: both editors known, and the reverter is not the author (no self-reverts)."""
    d = links[links.author_key.notna() & links.reverter_key.notna() & (links.author_key != links.reverter_key)]
    if no_bots:
        d = d[(d.author_kind != "bot") & (d.reverter_kind != "bot")]
    if registered_only:
        d = d[(d.author_kind == "registered") & (d.reverter_kind == "registered")]
    if single_only:  # the revert undid exactly one revision, so nobody was caught in a multi-edit rollback
        d = d[d.range_size == 1]
    if followup_only:
        d = d[d.within_followup.fillna(False).astype(bool)]
    return d


def mutual_pairs(d: pd.DataFrame) -> pd.DataFrame:
    """One row per (page, unordered editor pair) where each reverted the other on that page.

    Columns: page_id, a, b (a < b), n_ab (times a reverted b), n_ba, a_kind, b_kind, pair_kind.
    """
    dp = d.groupby(["page_id", "reverter_key", "author_key"]).size().rename("n_ab").reset_index()
    back = dp.rename(columns={"reverter_key": "author_key", "author_key": "reverter_key", "n_ab": "n_ba"})
    m = dp.merge(back, on=["page_id", "reverter_key", "author_key"])
    m = m[m.reverter_key < m.author_key].rename(columns={"reverter_key": "a", "author_key": "b"}).reset_index(drop=True)
    kinds = pd.concat([d[["author_key", "author_kind"]].set_axis(["k", "kind"], axis=1),
                       d[["reverter_key", "reverter_kind"]].set_axis(["k", "kind"], axis=1)]).drop_duplicates("k").set_index("k").kind
    m["a_kind"] = m.a.map(kinds).fillna("unknown")
    m["b_kind"] = m.b.map(kinds).fillna("unknown")
    m["pair_kind"] = [" vs ".join(sorted(p)) for p in zip(m.a_kind, m.b_kind)]
    return m


def directed_pairs(d: pd.DataFrame) -> int:
    return int(len(d.groupby(["page_id", "reverter_key", "author_key"]).size()))


def window_m(m: pd.DataFrame, n_edits: pd.Series) -> tuple[pd.Series, int]:
    """Window M per page. n_edits is indexed by (page_id, editor key). An editor with no edit counted inside the
    window (the revert itself fell outside it) is given N = 1; the number of such pairs is returned as well."""
    if m.empty:
        return pd.Series(dtype=float), 0
    na = pd.Series(n_edits.reindex(pd.MultiIndex.from_frame(m[["page_id", "a"]])).to_numpy(), index=m.index)
    nb = pd.Series(n_edits.reindex(pd.MultiIndex.from_frame(m[["page_id", "b"]])).to_numpy(), index=m.index)
    missing = int((na.isna() | nb.isna()).sum())
    mn = np.minimum(na.fillna(1), nb.fillna(1))
    g = m.assign(mn=mn)
    editors = pd.concat([g[["page_id", "a"]].set_axis(["page_id", "k"], axis=1),
                         g[["page_id", "b"]].set_axis(["page_id", "k"], axis=1)]).groupby("page_id").k.nunique()
    s = g.groupby("page_id").mn.agg(["sum", "max"])
    return (editors * (s["sum"] - s["max"])).rename("M"), missing


def counts(links: pd.DataFrame, **kw) -> dict:
    d = usable_links(links, **kw)
    m = mutual_pairs(d)
    pages_rev = int(d.page_id.nunique())
    per_page = m.groupby("page_id").size()
    return {"link_rows": int(len(links)), "usable_links": int(len(d)), "directed_pairs": directed_pairs(d),
            "mutual_pairs": int(len(m)), "mutual_pages": int(m.page_id.nunique()), "pages_with_a_revert_by_another_editor": pages_rev,
            "mutual_pages_pct_of_reverted_pages": round(100 * m.page_id.nunique() / pages_rev, 2) if pages_rev else None,
            "pages_with_one_pair": int((per_page == 1).sum()), "pages_with_2plus_pairs": int((per_page >= 2).sum())}


def el_split(frame: pd.DataFrame, group_of_page: pd.Series, groups: list[str], ref: str, default: str, rng, poisson_ci, poisson_diff_ci) -> list[dict]:
    """E(L) = share of eventual reverts NOT yet known after waiting L, per page group, with page-level Poisson-bootstrap
    intervals, and the difference of each group from the reference group (joint bootstrap over the same pages).

    frame: one row per eventual revert with page_id and known_after_s. group_of_page: page_id -> group label; a page
    that is not in it gets the `default` label. `ref` is the group the others are compared with.
    """
    out = []
    f = frame.assign(grp=frame.page_id.map(group_of_page).fillna(default))
    for L, label in WAITS:
        by = f.assign(u=(f.known_after_s > L).astype(int)).groupby(["page_id", "grp"]).agg(n=("u", "size"), u=("u", "sum")).reset_index()
        n_ref = np.where(by.grp == ref, by.n, 0)
        u_ref = np.where(by.grp == ref, by.u, 0)
        for g in groups:
            sel = (by.grp == g).to_numpy()
            if not sel.any():
                continue
            e = poisson_ci(by.u.to_numpy()[sel], by.n.to_numpy()[sel], rng)
            row = {"L": label, "group": g, "pages": int(sel.sum()), "reverts": int(by.n.to_numpy()[sel].sum()),
                   "E": round(e[0], 4), "E_lo": round(e[1], 4), "E_hi": round(e[2], 4)}
            if g != ref:
                dci = poisson_diff_ci(np.where(sel, by.u, 0), np.where(sel, by.n, 0), u_ref, n_ref, rng)
                row.update({"diff_vs_ref": round(dci[0], 4), "diff_lo": round(dci[1], 4), "diff_hi": round(dci[2], 4),
                            "diff_interval_excludes_0": bool(dci[1] > 0 or dci[2] < 0)})
            out.append(row)
    return out


def self_test() -> None:
    """Small hand-made cases with known answers."""
    L = pd.DataFrame([
        # page 1: x reverts y twice, y reverts x once -> one mutual pair
        (1, "x", "y", "registered", "temporary"), (1, "x", "y", "registered", "temporary"), (1, "y", "x", "temporary", "registered"),
        # page 2: one direction only -> no pair
        (2, "x", "y", "registered", "temporary"),
        # pages 3 and 4: the two directions are on different pages -> no pair
        (3, "p", "q", "registered", "registered"), (4, "q", "p", "registered", "registered"),
        # page 5: three editors, pairs (a,b), (a,c); plus a self-revert and a bot pair
        (5, "a", "b", "registered", "registered"), (5, "b", "a", "registered", "registered"),
        (5, "a", "c", "registered", "registered"), (5, "c", "a", "registered", "registered"),
        (5, "a", "a", "registered", "registered"),
        (5, "bot", "c", "bot", "registered"), (5, "c", "bot", "registered", "bot"),
    ], columns=["page_id", "reverter_key", "author_key", "reverter_kind", "author_kind"])
    L["range_size"] = 1
    L["within_followup"] = True
    m = mutual_pairs(usable_links(L))
    assert len(m) == 4 and set(m.page_id) == {1, 5}, m
    assert m[m.page_id == 1].iloc[0][["n_ab", "n_ba"]].tolist() == [2, 1]
    assert m[m.page_id == 1].pair_kind.iloc[0] == "registered vs temporary"
    assert len(mutual_pairs(usable_links(L, no_bots=True))) == 3
    assert len(mutual_pairs(usable_links(L, registered_only=True))) == 2
    c = counts(L)
    assert c["mutual_pages"] == 2 and c["pages_with_a_revert_by_another_editor"] == 5 and c["pages_with_2plus_pairs"] == 1
    # window M on page 5 without the bot: pairs (a,b) min(4,3)=3 and (a,c) min(4,2)=2; E=3; M = 3 * (5 - 3) = 6
    n = pd.Series({(5, "a"): 4, (5, "b"): 3, (5, "c"): 2, (1, "x"): 5})
    M, missing = window_m(mutual_pairs(usable_links(L, no_bots=True)), n)
    assert M.loc[5] == 6 and M.loc[1] == 0 and missing == 1, (M, missing)
    # E(L): group g has 2 of 4 reverts unknown after 1 h, the reference 1 of 4
    fr = pd.DataFrame({"page_id": [1, 1, 2, 2, 3, 3, 4, 4], "known_after_s": [10, 4000, 10, 4000, 10, 10, 10, 90000]})

    def ci(num, den, rng, b=0):
        return (num.sum() / den.sum(), 0.0, 1.0)

    def dci(an, ad, bn, bd, rng, b=0):
        return (an.sum() / ad.sum() - bn.sum() / bd.sum(), -1.0, 1.0)

    r = el_split(fr, pd.Series({1: "g", 2: "g", 3: "rest"}), ["g", "rest", "other"], "rest", "other", None, ci, dci)
    e = {(x["L"], x["group"]): x for x in r}
    # page 3 is the reference (0 of 2 unknown); page 4 is in no group, so it must land in "other", not in the reference
    assert e[("1 h", "g")]["E"] == 0.5 and e[("1 h", "rest")]["E"] == 0.0 and e[("1 h", "g")]["diff_vs_ref"] == 0.5
    assert e[("1 h", "other")]["pages"] == 1 and e[("1 h", "other")]["E"] == 0.5 and e[("1 d", "other")]["E"] == 0.5
    assert e[("1 d", "g")]["E"] == 0.0 and e[("1 d", "rest")]["E"] == 0.0
    print("self-test ok")


if __name__ == "__main__":
    self_test()
