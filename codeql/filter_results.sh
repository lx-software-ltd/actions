#!/usr/bin/env bash
# Code scanning does not read a SARIF suppression. Drop in-source results
# before the upload, which is what closes the alert.
set -euo pipefail
dir="${SARIF_DIR:-}"
if [ -z "$dir" ] || [ ! -d "$dir" ]; then
  echo "codeql: SARIF directory is missing" >&2
  exit 1
fi
found=0
for file in "$dir"/*.sarif; do
  if [ ! -f "$file" ]; then
    continue
  fi
  found=1
  filtered="$(mktemp)"
  SARIF_INPUT="$file" SARIF_OUTPUT="$filtered" python3 "$GITHUB_ACTION_PATH/../lib/filter_sarif.py"
  mv "$filtered" "$file"
done
if [ "$found" -eq 0 ]; then
  echo "codeql: no SARIF file to filter" >&2
  exit 1
fi
