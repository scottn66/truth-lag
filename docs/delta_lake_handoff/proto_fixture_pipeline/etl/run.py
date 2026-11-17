"""Command line for the Bronze and Silver steps.

Run (TRUTHLAG_HW2_DIR and TRUTHLAG_LAKE_DIR must be set)
    python -m etl.run bronze  [--raw-dir DIR] [--include-open]
    python -m etl.run silver  [--dates 2026-10-20,2026-10-21]      # default: every event date in Bronze
    python -m etl.run cohorts [--as-of 2026-10-27T00:05:00Z] [--history-dir DIR] [--history-revisions FILE]
    python -m etl.run all     [--raw-dir DIR] [--as-of ISO] [--history-dir DIR]

`all` runs bronze, then silver for the event dates that bronze touched, then cohorts.
Without --as-of the cohort step uses the newest meta_dt in Silver, so a re-run without new
data writes nothing.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

from . import bronze_stream, silver_cohorts, silver_stream
from .hw2 import config


def _show(obj) -> None:
    print(json.dumps(obj, indent=2, default=lambda o: sorted(str(x) for x in o) if isinstance(o, set) else str(o)))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m etl.run", description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["bronze", "silver", "cohorts", "all"])
    ap.add_argument("--lake", type=Path, default=None, help="lake root (default: TRUTHLAG_LAKE_DIR)")
    ap.add_argument("--raw-dir", type=Path, default=config.RAW_STREAM_DIR)
    ap.add_argument("--include-open", action="store_true",
                    help="also read part files changed in the last OPEN_FILE_GRACE_S seconds")
    ap.add_argument("--dates", default=None, help="silver: comma-separated event dates (default: all)")
    ap.add_argument("--as-of", default=None, help="cohorts: use events with meta_dt <= this UTC time")
    ap.add_argument("--history-dir", type=Path, default=config.HISTORY_DIR)
    ap.add_argument("--history-revisions", type=Path, default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", stream=sys.stdout)

    dates = None
    if args.step in ("bronze", "all"):
        b = bronze_stream.run(args.raw_dir, lake=args.lake, include_open=args.include_open)
        dates = b["dates"]
        _show({"bronze": b["streams"]})
    if args.step in ("silver", "all"):
        if args.step == "silver" and args.dates:
            days = {date.fromisoformat(d) for d in args.dates.split(",")}
            dates = {s: days for s in config.STREAM_DIRS}
        _show({"silver": silver_stream.build(dates, lake=args.lake)})
    if args.step in ("cohorts", "all"):
        _show({"cohorts": silver_cohorts.build(args.as_of, history_dir=args.history_dir, lake=args.lake,
                                               history_revisions=args.history_revisions)})


if __name__ == "__main__":
    main()
