#!/bin/bash
# npm audit, retried only when the registry returns 503.
set -euo pipefail

directories="${NPM_AUDIT_DIRECTORIES:?npm-audit: directories are required}"
level="${NPM_AUDIT_LEVEL:-high}"
omit="${NPM_AUDIT_OMIT:-dev}"

run_npm_audit() {
  dir="$1"
  attempt=1
  max_attempts=4
  delay=8
  while [ "$attempt" -le "$max_attempts" ]; do
    echo "npm audit (attempt ${attempt}/${max_attempts}) in ${dir}"
    set +e
    audit_output="$(cd "$dir" && npm audit --omit="$omit" --audit-level="$level" 2>&1)"
    audit_status=$?
    set -e
    printf '%s\n' "$audit_output"
    if [ "$audit_status" -eq 0 ]; then
      return 0
    fi
    if printf '%s' "$audit_output" | grep -Eq '503 Service Unavailable|audit endpoint returned an error'; then
      if [ "$attempt" -lt "$max_attempts" ]; then
        echo "npm audit registry unavailable; retrying in ${delay}s..."
        sleep "$delay"
        delay=$((delay * 2))
        attempt=$((attempt + 1))
        continue
      fi
    fi
    return "$audit_status"
  done
}

while IFS= read -r dir; do
  dir="${dir%$'\r'}"
  if [ -z "$dir" ]; then
    continue
  fi
  if [ ! -f "$dir/package.json" ]; then
    echo "npm-audit: $dir has no package.json" >&2
    exit 1
  fi
  run_npm_audit "$dir"
done << EOF
$directories
EOF
