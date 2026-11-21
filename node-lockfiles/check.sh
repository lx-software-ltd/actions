#!/bin/bash
# npm ci, then fail when package-lock.json changes.
set -euo pipefail

if [ -z "${LOCKFILE_DIRECTORIES:-}" ]; then
  echo "node-lockfiles: directories are required" >&2
  exit 1
fi

while IFS= read -r dir; do
  dir="${dir%$'\r'}"
  if [ -z "$dir" ]; then
    continue
  fi
  if [ ! -f "$dir/package.json" ]; then
    echo "Skipping Node lockfile check for $dir"
    continue
  fi
  if [ ! -f "$dir/package-lock.json" ]; then
    echo "Missing package-lock.json in $dir" >&2
    exit 1
  fi
  (cd "$dir" && npm ci)
  if ! git diff --exit-code -- "$dir/package-lock.json"; then
    echo "package-lock.json is out of sync in $dir" >&2
    exit 1
  fi
done << EOF
$LOCKFILE_DIRECTORIES
EOF
