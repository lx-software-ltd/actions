#!/bin/bash
# Audit requirements files. A non-zero pip-audit status fails the step.
set -euo pipefail

files="${PIP_AUDIT_FILES:?pip-audit: requirements are required}"
ignores="${PIP_AUDIT_IGNORE:-}"
python3 -m pip install --disable-pip-version-check pip-audit==2.10.1
user_bin="$(python3 -m site --user-base)/bin"
export PATH="${user_bin}:$PATH"
ignore_args=""
for vuln in $ignores; do
  ignore_args="$ignore_args --ignore-vuln $vuln"
done
while IFS= read -r req; do
  req="${req%$'\r'}"
  if [ -z "$req" ]; then
    continue
  fi
  if [ -n "${PIP_AUDIT_REPORT:-}" ]; then
    # shellcheck disable=SC2086
    pip-audit -r "$req" --desc on $ignore_args 2>&1 | tee -a "$PIP_AUDIT_REPORT"
  else
    # shellcheck disable=SC2086
    pip-audit -r "$req" --desc on $ignore_args
  fi
done << EOF
$files
EOF
