#!/usr/bin/env bash
# Build the submission bundle in dist/ from a FRESH CLONE of this local repository (so only committed files go in).
#
#   bash scripts/make_bundle.sh [out_dir]          default out_dir: dist/ in the repository (git-ignored)
#
# dist/
#   truthlag_code_<commit>.zip   the code to upload: lake code, checks, notebooks, final docs, the EC HW2 modules it imports
#   truthlag_repo_<commit>.zip   every tracked file up to 1.2 MB (also the EC HW2 submission material; never data/)
#   notebooks/final, notebooks/fallback   the executed notebooks with their .py copies
#   figures/                      the report figures (PNG)
#   results.json, report_draft.md, RUBRIC_EVIDENCE.md, GENAI_LOG.md, GATE_MON.md
#   MANIFEST.txt                  commit hash, every file with size and SHA-256, excluded files, check results
#
# It commits nothing, pushes nothing and reads no data. It prints the commit hash at the end.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$REPO/dist}"
LIMIT_KB=1200
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone -q --no-hardlinks "$REPO" "$TMP/truth-lag"
cd "$TMP/truth-lag"
HASH="$(git rev-parse HEAD)"; SHORT="$(git rev-parse --short HEAD)"; BRANCH="$(git rev-parse --abbrev-ref HEAD)"
DIRTY="$(cd "$REPO" && git status --porcelain | wc -l | tr -d ' ')"

# never ship data: the only tracked file under data/ may be data/.gitkeep
if git ls-files data | grep -v '^data/.gitkeep$' | grep -q .; then
  echo "refused: tracked files under data/"; git ls-files data; exit 1
fi

rm -rf "$OUT"; mkdir -p "$OUT/notebooks/final" "$OUT/notebooks/fallback" "$OUT/figures"
: > "$TMP/keep.txt"; : > "$TMP/excluded.txt"
git ls-files | while IFS= read -r f; do
  [ -f "$f" ] || continue
  kb=$(( ($(wc -c < "$f") + 1023) / 1024 ))
  if [ "$kb" -gt "$LIMIT_KB" ]; then printf '%s\t%s KB\n' "$f" "$kb" >> "$TMP/excluded.txt"; else printf '%s\n' "$f" >> "$TMP/keep.txt"; fi
done
zip -q -X "$OUT/truthlag_repo_${SHORT}.zip" -@ < "$TMP/keep.txt"

# The code zip to upload: only what the final project needs (the lake code, its checks, notebooks, final docs, and
# the EC HW2 modules that the lake imports). The repo zip above also holds the EC HW2 submission material.
git ls-files -- etl scripts tests_lake notebooks/final notebooks/fallback docs/final ingest \
    ':(glob)docs/delta_lake_handoff/*.md' docs/delta_lake_handoff/requirements-lake.txt \
    ec-hw2/config.py ec-hw2/ingest ec-hw2/tests/__init__.py ec-hw2/tests/test_history.py ec-hw2/tests/test_stream.py \
    ec-hw2/STYLE.md ec-hw2/DATA_MODEL.md README.md requirements.txt .gitignore | grep -F -x -f "$TMP/keep.txt" > "$TMP/code.txt"
zip -q -X "$OUT/truthlag_code_${SHORT}.zip" -@ < "$TMP/code.txt"

cp notebooks/final/*.ipynb notebooks/final/*.py "$OUT/notebooks/final/"
cp notebooks/fallback/*.ipynb notebooks/fallback/*.py "$OUT/notebooks/fallback/" 2>/dev/null || true
cp notebooks/fallback/*.csv "$OUT/notebooks/fallback/" 2>/dev/null || true
cp docs/final/figures/*.png "$OUT/figures/"
for f in results.json report_draft.md RUBRIC_EVIDENCE.md GENAI_LOG.md GATE_MON.md; do
  [ -f "docs/final/$f" ] && cp "docs/final/$f" "$OUT/"
done

PY="$REPO/.venv-lake/bin/python"; [ -x "$PY" ] || PY=python3
# prove the code zip stands alone: unzip it and run the fixture tests from the unzipped copy
mkdir "$TMP/unzipped" && (cd "$TMP/unzipped" && unzip -q "$OUT/truthlag_code_${SHORT}.zip")
ZIPTESTS="$(cd "$TMP/unzipped" && TRUTHLAG_HW2_DIR="$PWD/ec-hw2" PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest tests_lake ec-hw2/tests/test_history.py ec-hw2/tests/test_stream.py -q -p no:cacheprovider 2>&1 | tail -1)"
NUMBERS="$("$PY" scripts/check_numbers.py --no-regen 2>&1 | tail -1)"
EVIDENCE="$("$PY" scripts/check_evidence.py --allow-missing-data 2>&1 | tail -1)"

{
  echo "TruthLag submission bundle"
  echo "commit:  $HASH"
  echo "branch:  $BRANCH"
  echo "built:   $(date -u +%Y-%m-%dT%H:%M:%SZ) from a fresh clone of the local repository"
  echo "working tree of the source repository: $DIRTY uncommitted path(s) (not in the bundle)"
  echo "results.json commit stamp: $(grep -m1 '"commit"' docs/final/results.json | sed 's/[", ]//g; s/commit://')"
  echo "check_numbers (in the clone, without the lake):  $NUMBERS"
  echo "check_evidence (in the clone, data outputs not present):  $EVIDENCE"
  echo
  echo "tests run from the unzipped code zip:  $ZIPTESTS"
  echo
  echo "code zip (upload this): truthlag_code_${SHORT}.zip  files: $(wc -l < "$TMP/code.txt" | tr -d ' ')  size: $(( $(wc -c < "$OUT/truthlag_code_${SHORT}.zip") / 1024 )) KB"
  echo "largest file inside the code zip: $(xargs ls -l < "$TMP/code.txt" 2>/dev/null | sort -k5 -n -r | head -1 | awk '{printf "%s (%d KB)", $NF, $5/1024}')"
  echo "repo zip (everything tracked, with the EC HW2 material): truthlag_repo_${SHORT}.zip  files: $(wc -l < "$TMP/keep.txt" | tr -d ' ')  size: $(( $(wc -c < "$OUT/truthlag_repo_${SHORT}.zip") / 1024 )) KB"
  echo "largest file inside the repo zip: $(xargs ls -l < "$TMP/keep.txt" 2>/dev/null | sort -k5 -n -r | head -1 | awk '{printf "%s (%d KB)", $NF, $5/1024}')"
  echo "tracked files left out of both zips (over ${LIMIT_KB} KB):"
  if [ -s "$TMP/excluded.txt" ]; then sed 's/^/  /' "$TMP/excluded.txt"; else echo "  none"; fi
  echo
  echo "files (bytes, sha256, path):"
  (cd "$OUT" && find . -type f ! -name MANIFEST.txt | sort | while IFS= read -r f; do
     printf '%10d  %s  %s\n' "$(wc -c < "$f")" "$(shasum -a 256 "$f" | cut -d' ' -f1)" "${f#./}"; done)
} > "$OUT/MANIFEST.txt"

echo "bundle: $OUT"
echo "files in dist: $(find "$OUT" -type f | wc -l | tr -d ' ')   total: $(du -sk "$OUT" | cut -f1) KB"
echo "largest file in dist: $(find "$OUT" -type f -exec ls -l {} + | sort -k5 -n -r | head -1 | awk '{printf "%s (%d KB)", $NF, $5/1024}')"
echo "code zip: truthlag_code_${SHORT}.zip ($(( $(wc -c < "$OUT/truthlag_code_${SHORT}.zip") / 1024 )) KB, $(wc -l < "$TMP/code.txt" | tr -d ' ') files); tests from the unzipped copy: $ZIPTESTS"
echo "check_numbers:  $NUMBERS"
echo "check_evidence: $EVIDENCE"
echo "commit: $HASH"
