#!/bin/sh
# Download the pinned Gitleaks release, check its digest, and scan.
set -eu

version="${GITLEAKS_VERSION:?gitleaks: version is required}"
checksum="${GITLEAKS_SHA256:?gitleaks: checksum is required}"
source_dir="${GITLEAKS_SOURCE:-.}"
config="${GITLEAKS_CONFIG:-}"

downloaded=0
attempt=1
while [ "$attempt" -le 5 ]; do
  if [ "$attempt" -gt 1 ]; then
    sleep $(( (attempt - 1) * 2 ))
  fi
  if curl -sSfL \
    "https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_linux_x64.tar.gz" \
    -o /tmp/gitleaks.tgz; then
    downloaded=1
    break
  fi
  attempt=$((attempt + 1))
done
test "$downloaded" = 1
echo "${checksum}  /tmp/gitleaks.tgz" | sha256sum -c -
tar -xzf /tmp/gitleaks.tgz -C /tmp gitleaks
if [ -n "$config" ]; then
  /tmp/gitleaks detect --source "$source_dir" --config "$config" --verbose --redact --no-banner
else
  /tmp/gitleaks detect --source "$source_dir" --verbose --redact --no-banner
fi
