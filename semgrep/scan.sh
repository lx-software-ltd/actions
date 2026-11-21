#!/bin/sh
# semgrep scan, then an empty SARIF if the scan wrote nothing, then the
# in-source suppression filter. shell is sh because the Semgrep image is
# the job container.
set -eu

rules="${SEMGREP_RULES:?semgrep: rules are required}"
excludes="${SEMGREP_EXCLUDE_RULES:-}"
source_dir="${SEMGREP_SOURCE:-.}"
output="${SEMGREP_OUTPUT:-semgrep-results.sarif}"
mode="${SEMGREP_MODE:-scan}"

if [ "$mode" != "scan" ] && [ "$mode" != "ci" ]; then
  echo "semgrep: mode must be scan or ci" >&2
  exit 1
fi
if [ "$mode" = "ci" ]; then
  set -- semgrep ci --sarif --output="$output"
else
  set -- semgrep scan --sarif --sarif-output="$output"
fi
for rule in $rules; do
  set -- "$@" --config "$rule"
done
for rule in $excludes; do
  set -- "$@" --exclude-rule "$rule"
done
set -- "$@" "$source_dir"

"$@" || true
if [ ! -f "$output" ]; then
  printf '%s\n' '{"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json","runs":[]}' > "$output"
fi

lib="$GITHUB_ACTION_PATH/../lib/filter_sarif.py"
if [ ! -f "$lib" ]; then
  echo "semgrep: $lib does not resolve" >&2
  exit 1
fi
SARIF_INPUT="$output" SARIF_OUTPUT="$output" python3 "$lib"
