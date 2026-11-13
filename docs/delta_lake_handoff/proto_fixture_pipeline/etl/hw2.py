"""Import shim for the old pandas pipeline (the ec-hw2 folder).

Purpose
    ec-hw2 has a hyphen, so it cannot be a package. Its modules expect the ec-hw2
    folder itself on sys.path (`import config`, `from ingest import parse_stream`).
    This module puts that folder on sys.path once and re-exports the modules, so
    the rest of the package writes `from .hw2 import config, parse_stream`.

Inputs
    TRUTHLAG_HW2_DIR   path of the ec-hw2 folder. If it is not set, the folder
                       `ec-hw2` next to this package is used (the repo layout).

Do not name a new package `ingest`, `config` or `tests`: the old code owns these names.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_VAR = "TRUTHLAG_HW2_DIR"


def _find_hw2_dir() -> Path:
    value = os.environ.get(ENV_VAR)
    p = Path(value).expanduser() if value else Path(__file__).resolve().parents[1] / "ec-hw2"
    p = p.resolve()
    if not (p / "config.py").is_file() or not (p / "ingest" / "parse_stream.py").is_file():
        raise ImportError(f"{p} is not the ec-hw2 folder (config.py and ingest/parse_stream.py not found). "
                          f"Set {ENV_VAR} to the ec-hw2 folder.")
    return p


HW2_DIR = _find_hw2_dir()
if str(HW2_DIR) not in sys.path:
    sys.path.insert(0, str(HW2_DIR))

import config  # noqa: E402
from ingest import history_columns, label_live, late_reverts, parse_history, parse_stream  # noqa: E402

# Another module named `config` or `ingest` earlier on sys.path would be used silently. Stop if so.
for _mod, _want in ((config, HW2_DIR), (parse_stream, HW2_DIR / "ingest")):
    if Path(_mod.__file__).resolve().parent != _want:
        raise ImportError(f"{_mod.__name__} was imported from {_mod.__file__}, not from {_want}")

__all__ = ["HW2_DIR", "config", "history_columns", "label_live", "late_reverts", "parse_history", "parse_stream"]
