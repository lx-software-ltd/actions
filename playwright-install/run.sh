#!/bin/bash
# Install Playwright browsers. If apt packages cannot be installed, install
# the browser alone.
set -euo pipefail

browsers="${PLAYWRIGHT_BROWSERS:?playwright-install: browsers are required}"
root="${PLAYWRIGHT_DIRECTORY:-}"
if [ -n "$root" ]; then
  cd "$root"
fi
if ! timeout 180 npx playwright install $browsers --with-deps; then
  echo "::warning::Could not install browser apt packages; continuing with the browser only."
  # shellcheck disable=SC2086
  npx playwright install $browsers
fi
