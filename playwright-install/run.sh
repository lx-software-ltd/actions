#!/bin/bash
# Install Playwright browsers. If apt packages cannot be installed, install
# the browser alone. Both attempts are bounded so a download that reaches
# 100% and then never exits cannot hold the runner.
set -euo pipefail

browsers="${PLAYWRIGHT_BROWSERS:?playwright-install: browsers are required}"
root="${PLAYWRIGHT_DIRECTORY:-}"
if [ -n "$root" ]; then
  cd "$root"
fi

run_install() {
  # shellcheck disable=SC2086
  timeout --kill-after=20s 600 npx playwright install $browsers "$@"
}

if ! run_install --with-deps; then
  echo "::warning::Could not install browser apt packages; continuing with the browser only."
  run_install
fi
