#!/usr/bin/env bash
# Pack the derived data for teammates (so they can run the notebooks without the raw stream).
#
# What goes in: the cohort tables (data/tables/*.parquet), the SQLite file, the Neo4j CSV files
#               and DATA_VERSION. NOT the raw stream files and NOT the dump (link, don't upload).
# Run:          bash ec-hw2/release_data.sh              (makes data/release/truthlag-<version>.zip)
#               bash ec-hw2/release_data.sh --publish    (also uploads it as a GitHub Release
#                                                         in the private repo; Scott only)
# Teammates:    download the zip from the Releases page in the browser, unzip it in the repo
#               folder (it creates data/tables/... and data/neo4j/import/...), then run
#               python ec-hw2/check_setup.py
# License:      the History dump is CC0. EventStreams has no stated license; we share only
#               derived counts and labels, with human editor names kept (the Wikipedia edit
#               history is public), and the notebooks show pseudonyms.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
VERSION=$($PY -c "import sys; sys.path.insert(0,'ec-hw2'); import config; print(config.DATA_VERSION)")
echo "$VERSION" > data/tables/DATA_VERSION
mkdir -p data/release
ZIP="data/release/truthlag-$VERSION.zip"
rm -f "$ZIP"
FILES=(data/tables/DATA_VERSION data/tables/*.parquet data/tables/*.json data/tables/truthlag.sqlite data/neo4j/import/*.csv)
zip -q -9 "$ZIP" "${FILES[@]}"
( cd data/release && shasum -a 256 "truthlag-$VERSION.zip" > "truthlag-$VERSION.zip.sha256" )
echo "made $ZIP ($(du -h "$ZIP" | cut -f1)), sha256 in $ZIP.sha256"
unzip -l "$ZIP" | tail -n +4 | sed '$d' | sed '$d' | awk '{print "  " $4 "  (" $1 " bytes)"}'

if [[ "${1:-}" == "--publish" ]]; then
  NOTES="Derived data for EC HW2 ($VERSION). Unzip in the repo folder, then run: python ec-hw2/check_setup.py. Live numbers are PROVISIONAL in data-v1 and FINAL in data-v2."
  if gh release view "data-$VERSION" -R scottn66/truth-lag >/dev/null 2>&1; then
    gh release upload "data-$VERSION" "$ZIP" "$ZIP.sha256" --clobber -R scottn66/truth-lag
  else
    gh release create "data-$VERSION" "$ZIP" "$ZIP.sha256" -R scottn66/truth-lag \
      --target ec-hw2 --title "EC HW2 data ($VERSION)" --notes "$NOTES" --prerelease
  fi
  echo "published: https://github.com/scottn66/truth-lag/releases/tag/data-$VERSION"
fi
