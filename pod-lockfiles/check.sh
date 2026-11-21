#!/bin/bash
# pod install, then fail when Podfile.lock changes.
set -euo pipefail

dir="${POD_DIRECTORY:?pod-lockfiles: working-directory is required}"
if [ ! -f "$dir/Podfile" ]; then
  echo "Skipping iOS lockfile check ($dir/Podfile missing)"
  exit 0
fi
cd "$dir"
if [ ! -f Podfile.lock ]; then
  echo "Podfile.lock is missing" >&2
  exit 1
fi
pod install --repo-update
if ! git diff --exit-code -- Podfile.lock; then
  echo "Podfile.lock is out of sync with Podfile" >&2
  exit 1
fi
