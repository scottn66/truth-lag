#!/usr/bin/env bash
# Refresh the LIVE cohort with the newest capture and rebuild everything that depends on it.
#
# When:   after Mon 2026-10-26 5:05 PM PT (= 2026-10-27 00:05 UTC). Then every live edit
#         (2026-10-20 to 2026-10-22 UTC) has its full 4-day follow-up, and the live
#         numbers become FINAL (data-v2).
# Run:    bash ec-hw2/refresh_live.sh            (stops if the capture is not past the cutoff)
#         bash ec-hw2/refresh_live.sh --force    (runs anyway; the live numbers stay PROVISIONAL)
# Needs:  colima + the two containers running; ssh access to vps-coin (read-only rsync).
# Safety: rsync never uses --delete; nothing here touches the VPS capture units.
#         The history cohort and the graph (history only) are not rebuilt.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
JUP=.venv/bin/jupyter
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

step() { echo; echo "=== $1 ==="; }

step "1/11 copy the newest raw files from the VPS (rsync -az --partial, never --delete)"
rsync -az --partial vps-coin:/opt/truthlag/data/raw/ data/raw/

step "2/11 parse the raw stream files"
$PY ec-hw2/ingest/parse_stream.py

step "3/11 check that the capture is past the cutoff"
FINAL=$($PY - <<'EOF'
import sys; sys.path.insert(0, "ec-hw2")
import pandas as pd, config
newest = pd.read_parquet(config.PARSED_DIR / "page_change.parquet", columns=["meta_dt"])["meta_dt"].max()
print("yes" if newest >= pd.Timestamp(config.LIVE_FINAL_AFTER) else "no")
print(f"newest page_change meta.dt = {newest}, cutoff = {config.LIVE_FINAL_AFTER}", file=sys.stderr)
EOF
)
if [[ "$FINAL" != "yes" && "$FORCE" != "1" ]]; then
  echo "The capture is not past 2026-10-27 00:05 UTC yet. Stop here (use --force for a PROVISIONAL refresh)."
  exit 1
fi
if [[ "$FINAL" == "yes" ]]; then
  echo "Past the cutoff: the live numbers will be FINAL (data-v2)."
  sed -i '' 's/^DATA_VERSION = "data-v1"/DATA_VERSION = "data-v2"/' ec-hw2/config.py
else
  echo "Not past the cutoff: --force run, the live numbers stay PROVISIONAL."
fi

step "4/11 keep a copy of the old FACTS.md (for the change list at the end)"
cp ec-hw2/report/FACTS.md data/logs/FACTS_before_refresh.md

step "5/11 live cohort labels and the late-revert case study"
$PY ec-hw2/ingest/label_live.py
$PY ec-hw2/ingest/late_reverts.py

step "6/11 reload MongoDB (local) and the live counters"
$PY ec-hw2/load_mongo.py --target local
$PY ec-hw2/speed_layer.py

step "7/11 re-run all queries (Mongo, Cypher, SQL), then the 3-engine comparison"
$PY ec-hw2/queries/run_all.py
# MongoDB now holds the new live documents, so the comparison is timed again.
# Draft timing: run "compare.py --final" by hand later, when nothing else runs on the Mac.
$PY ec-hw2/comparison/compare.py

step "8/11 facts, figures, report skeleton, the numbers in the notebook text"
$PY ec-hw2/report/build_facts.py
$PY ec-hw2/report/make_figures.py
$PY ec-hw2/report/build_skeleton.py
$PY ec-hw2/report/sync_notebook_text.py

step "9/11 re-run the notebooks that show live numbers or the new comparison timings"
for nb in 01_data 02_mongodb 04_comparison 05_truth_lag; do
  $JUP nbconvert --to notebook --execute --inplace "ec-hw2/notebooks/$nb.ipynb"
done

step "10/11 Atlas chart collections (only if ATLAS_URI is set)"
if $PY -c "import sys; sys.path.insert(0,'ec-hw2'); import config; sys.exit(0 if config.ATLAS_URI else 1)"; then
  $PY ec-hw2/load_mongo.py --target atlas --confirm-overwrite
  $PY ec-hw2/queries/run_mongo.py --target atlas
else
  echo "ATLAS_URI is empty: skipped. Load Atlas later with guides/ATLAS_SETUP.md."
fi

step "11/11 what changed in FACTS.md"
$PY - <<'EOF'
import re
def facts(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] and not set(cells[0]) <= set("-: ") and cells[0] != "key":
            out[cells[0].strip("`")] = cells[1]
    return out
old, new = facts("data/logs/FACTS_before_refresh.md"), facts("ec-hw2/report/FACTS.md")
changed = [(k, old[k], new[k]) for k in new if k in old and old[k] != new[k]]
print(f"{len(changed)} facts changed:")
for k, a, b in changed[:60]:
    print(f"  {k}: {a}  ->  {b}")
EOF
echo
echo "Done. Next: bash ec-hw2/release_data.sh   (packs the data release for the team)"
