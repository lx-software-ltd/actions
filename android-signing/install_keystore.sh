#!/bin/sh
# Decode the release keystore. Missing signing secrets skip, which is
# what both pair B deploy-mobile workflows do.
set -eu

if [ -z "${ANDROID_KEYSTORE_BASE64:-}" ] || [ -z "${ANDROID_KEYSTORE_PASSWORD:-}" ] || [ -z "${ANDROID_KEY_PASSWORD:-}" ] || [ -z "${ANDROID_KEY_ALIAS:-}" ]; then
  echo "::warning::Skipping Android signing (missing secrets)"
  exit 0
fi

dest="${WORKING_DIRECTORY}/android/app"
mkdir -p "$dest"
printf '%s' "$ANDROID_KEYSTORE_BASE64" | base64 --decode > "$dest/keystore.p12"
chmod 600 "$dest/keystore.p12"
