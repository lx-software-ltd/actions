#!/bin/sh
# semgrep, then an empty SARIF only when the command exits 0 and writes
# nothing, then the in-source suppression filter. shell is sh because the
# Semgrep image is the job container.
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
  # Pair A passes packs through SEMGREP_RULES. semgrep ci reads that
  # variable. --config and a positional directory are scan flags.
  # Semgrep 1.185 exits 0 after a bad config unless --no-suppress-errors
  # is set, which would publish an empty SARIF.
  set -- semgrep ci --no-suppress-errors --sarif --output="$output"
else
  set -- semgrep scan --sarif --sarif-output="$output"
  for rule in $rules; do
    set -- "$@" --config "$rule"
  done
  set -- "$@" "$source_dir"
fi
for rule in $excludes; do
  set -- "$@" --exclude-rule "$rule"
done

set +e
"$@"
status=$?
set -e
if [ "$status" -ne 0 ] && [ "$status" -ne 1 ]; then
  echo "semgrep: exited $status" >&2
  exit "$status"
fi
if [ ! -f "$output" ]; then
  if [ "$status" -ne 0 ]; then
    echo "semgrep: exited $status and wrote no SARIF" >&2
    exit "$status"
  fi
  printf '%s\n' '{"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json","runs":[]}' > "$output"
fi

lib="$GITHUB_ACTION_PATH/../lib/filter_sarif.py"
if [ ! -f "$lib" ]; then
  echo "semgrep: $lib does not resolve" >&2
  exit 1
fi
SARIF_INPUT="$output" SARIF_OUTPUT="$output" python3 "$lib"
