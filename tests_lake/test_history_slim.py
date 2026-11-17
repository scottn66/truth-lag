"""etl.history_slim on made-up .tsv.bz2 files (78 columns): a page row, an empty field, the literal NA, a short row."""
from __future__ import annotations

import bz2

import pyarrow.parquet as pq
import pytest

from etl import history_slim as hs


def _row(**vals) -> str:
    row = {c: "x" for c in hs.COLS}
    row.update(vals)
    return "\t".join(row[c] for c in hs.COLS)


def _write(path, lines):
    with bz2.open(path, "wt", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")


def test_cut_keeps_revisions_and_literal_na(tmp_path):
    src = tmp_path / "2026-10.enwiki.2026-09.tsv.bz2"
    _write(src, [
        _row(event_entity="page", revision_id="1"),
        _row(event_entity="revision", revision_id="2", event_user_text="", event_user_text_historical="NA",
             event_timestamp="2026-09-08 00:00:01.0"),
        _row(event_entity="revision", revision_id="3", event_user_text="NULL"),
    ])
    stats = hs.cut(src, out_root=tmp_path / "slim")
    out = tmp_path / "slim" / "2026-10" / "enwiki_rev_all_2026-09_slim.parquet"
    t = pq.read_table(out)
    assert t.column_names == hs.SLIM
    assert t.column("revision_id").to_pylist() == ["2", "3"]
    assert t.column("event_user_text").to_pylist() == [None, "NULL"]          # only the empty field is null
    assert t.column("event_user_text_historical").to_pylist() == ["NA", "x"]  # literal NA stays a string
    assert stats["rows_in"] == 3 and stats["revision_rows_out"] == 2 and stats["rows_by_entity"] == {"page": 1, "revision": 2}
    with pytest.raises(SystemExit, match="never replaces"):
        hs.cut(src, out_root=tmp_path / "slim")


def test_cut_stops_on_a_short_row(tmp_path):
    src = tmp_path / "2026-10.enwiki.2026-10.tsv.bz2"
    good = _row(event_entity="revision", revision_id="5")
    short = "\t".join(good.split("\t")[:77])
    _write(src, [good, short])
    with pytest.raises(Exception, match="78|columns"):
        hs.cut(src, out_root=tmp_path / "slim")
    assert not (tmp_path / "slim" / "2026-10" / "enwiki_rev_all_2026-10_slim.parquet").exists()
    assert not list((tmp_path / "slim" / "2026-10").glob("*.tmp"))


def test_cut_refuses_data_history(tmp_path):
    src = tmp_path / "2026-10.enwiki.2026-09.tsv.bz2"
    _write(src, [_row(event_entity="revision", revision_id="7")])
    with pytest.raises(SystemExit, match="data/history"):
        hs.cut(src, out_root=hs.FORBIDDEN / "x" / "..")
