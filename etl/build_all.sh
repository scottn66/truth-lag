#!/usr/bin/env bash
# End-to-end build of the TruthLag lake, in knowledge order, with every check.
# Usage (from the repository root):   bash etl/build_all.sh [lake_dir]      default lake_dir: data/lake
# Needs: .venv-lake (docs/final/STATUS.md), data/raw and data/history (rsync from the VPS), data/parity_ref.
# Writes only under the lake folder (and data/exports, docs/final/figures, notebooks/final at the end).
set -euo pipefail
cd "$(dirname "$0")/.."
export TRUTHLAG_HW2_DIR="$PWD/ec-hw2"
export TRUTHLAG_LAKE_DIR="$(cd "$(dirname "${1:-data/lake}")" && pwd)/$(basename "${1:-data/lake}")"
PY=.venv-lake/bin/python
EARLY=2026-10-24T00:00:00.000000Z
PARITY=2026-10-27T20:59:59.999999Z
EXT=2026-11-13T23:59:59.999999Z
R="$TRUTHLAG_LAKE_DIR/_runs"; mkdir -p "$R"
step() { echo "=== $(date -u +%H:%M:%S) $*"; }

step bronze;            $PY -m etl.run bronze --raw-dir data/raw
step silver;            $PY -m etl.run silver
step history;           $PY -m etl.history all
step parity bronze;     $PY -m etl.parity bronze  > "$R/bronze_parity.json"
step parity silver;     $PY -m etl.parity silver  > "$R/silver_parity.json"
step cohorts early;     $PY -m etl.run cohorts --as-of $EARLY
step gold early;        $PY -m etl.gold_run --as-of $EARLY --steps ddl,dims,facts,labels
step cohorts parity;    $PY -m etl.run cohorts --as-of $PARITY
step parity cohorts;    $PY -m etl.parity cohorts > "$R/cohort_parity.json"
step gold parity;       $PY -m etl.gold_run --as-of $PARITY
step checks parity;     $PY -m etl.gold_checks --out "$R/gold_checks_parity.json"
step cohorts ext;       $PY -m etl.run cohorts --as-of $EXT
step cohorts_ext;       $PY -m etl.run cohorts_ext --as-of $EXT
step gold ext;          $PY -m etl.gold_run --as-of $EXT
step checks ext;        $PY -m etl.gold_checks --out "$R/gold_checks_ext.json"
step hypotheses;        $PY -m etl.hypotheses > /dev/null
# second History snapshot (2026-10): needs data/history_raw/2026-10/*.tsv.bz2 (public dump files)
if ls data/history_raw/2026-10/2026-10.enwiki.*.tsv.bz2 >/dev/null 2>&1; then
  for f in data/history_raw/2026-10/2026-10.enwiki.*.tsv.bz2; do
    m=$(basename "$f" .tsv.bz2); m=${m##*.}
    [ -f "data/history_slim/2026-10/enwiki_rev_all_${m}_slim.parquet" ] || { step "filter $f"; $PY -m etl.history_slim "$f"; }
  done
  step history 2026-10;   $PY -m etl.history bronze --snapshot 2026-10 && $PY -m etl.history silver --snapshot 2026-10
  step gold 2026-10;      $PY -m etl.gold_run --as-of $EXT --snapshot 2026-10 --steps ddl,dims,labels,label_change,recon,marts
  step snapshot checks;   $PY -m etl.snapshot_checks
  step checks ext again;  $PY -m etl.gold_checks --out "$R/gold_checks_ext.json"
fi
step time travel;       $PY -m etl.time_travel
if [ "${SKIP_EXTRAS:-0}" != "1" ]; then
  step streaming algos; $PY -m etl.streaming_algos > /dev/null
  step structured streaming; $PY -m etl.stream_sss
  step exports;         $PY -m etl.exports > /dev/null
  step figures;         $PY -m etl.figures
  step notebooks;       $PY notebooks/final/make_notebooks.py
  step fallback notebooks; $PY notebooks/fallback/make_fallback.py
  step results.json;    $PY scripts/make_results.py && $PY scripts/render_report.py
  step number check;    $PY scripts/check_numbers.py
  step evidence check;  $PY scripts/check_evidence.py || true     # dist/MANIFEST.txt exists only after scripts/make_bundle.sh
fi
step done
