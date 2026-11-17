"""etl.atlas_charts: the listing skips a collection name the driver refuses. No Atlas connection is made."""
from __future__ import annotations

import pytest

from etl import atlas_charts


class InvalidName(Exception):
    """Stands in for pymongo.errors.InvalidName (matched by class name)."""


class FakeCollection:
    def __init__(self, n):
        self.n = n

    def estimated_document_count(self):
        return self.n


class FakeDb:
    def __init__(self, counts):
        self.counts = counts

    def __getitem__(self, name):
        if name.startswith(".") or name.endswith("."):
            raise InvalidName(f"collection names must not start or end with '.': {name!r}")
        if name == "boom":
            raise RuntimeError("another failure")
        return FakeCollection(self.counts[name])


def test_invalid_name_is_skipped_with_a_warning():
    db = FakeDb({"final_h1": 4, "revisions": 1234})
    lines = atlas_charts.collection_lines(db, ["final_h1", "privacy_k_summary 4.", "revisions"])
    assert len(lines) == 3
    assert lines[0].strip() == "final_h1: 4 documents"
    assert "WARNING" in lines[1] and "privacy_k_summary 4." in lines[1]
    assert lines[2].strip() == "revisions: 1,234 documents"


def test_other_errors_are_not_hidden():
    with pytest.raises(RuntimeError):
        atlas_charts.collection_lines(FakeDb({}), ["boom"])
