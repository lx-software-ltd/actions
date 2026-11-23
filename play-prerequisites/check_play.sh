#!/bin/sh
# Decide whether the Play upload should run. Missing config or signing
# secrets set should_upload=false and exit 0.
set -eu

if [ -z "${GOOGLE_PLAY_SERVICE_ACCOUNT:-}" ] || [ -z "${ANDROID_RELEASE_TRACK:-}" ]; then
  echo "Skipping Play Store upload (missing config)"
  echo "should_upload=false" >> "$GITHUB_OUTPUT"
  exit 0
fi

if [ -z "${ANDROID_KEYSTORE_BASE64:-}" ] || [ -z "${ANDROID_KEYSTORE_PASSWORD:-}" ] || [ -z "${ANDROID_KEY_PASSWORD:-}" ] || [ -z "${ANDROID_KEY_ALIAS:-}" ]; then
  echo "Skipping Play Store upload (missing Android signing secrets)"
  echo "should_upload=false" >> "$GITHUB_OUTPUT"
  exit 0
fi

echo "should_upload=true" >> "$GITHUB_OUTPUT"
