#!/bin/bash
# flutter pub get, then fail when pubspec.lock changes.
set -euo pipefail

dir="${FLUTTER_DIRECTORY:?flutter-lockfiles: working-directory is required}"
if [ ! -f "$dir/pubspec.yaml" ]; then
  echo "Skipping Flutter lockfile check ($dir/pubspec.yaml missing)"
  exit 0
fi
cd "$dir"
flutter pub get
if [ ! -f pubspec.lock ]; then
  echo "pubspec.lock is missing" >&2
  exit 1
fi
if ! git diff --exit-code -- pubspec.lock; then
  echo "pubspec.lock is out of sync with pubspec.yaml" >&2
  exit 1
fi
