#!/bin/bash
# Run Bandit. Findings fail the step.
set -euo pipefail

paths="${BANDIT_PATHS:?bandit: paths are required}"
skip="${BANDIT_SKIP:-}"
root="${BANDIT_ROOT:-}"
python3 -m pip install --disable-pip-version-check 'bandit[toml]==1.9.4'
user_bin="$(python3 -m site --user-base)/bin"
export PATH="${user_bin}:$PATH"
if [ -n "$root" ]; then
  cd "$root"
fi
if [ -n "$skip" ]; then
  # shellcheck disable=SC2086
  bandit -r $paths -f txt --skip "$skip"
else
  # shellcheck disable=SC2086
  bandit -r $paths -f txt
fi
