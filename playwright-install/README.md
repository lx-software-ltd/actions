# Playwright install

Runs `npx playwright install <browsers> --with-deps`. If that command does not exit 0, it installs the browser without apt packages, which is the fallback `siutindei` uses when the apt mirrors cannot be reached. Each attempt is limited to 10 minutes, and `timeout --kill-after` stops a download that ignores the first signal. A cold apt install can take longer than three minutes, so the shorter cap was dropped.

The pass fixture installs Chromium with Playwright 1.65.1, the version the product repositories use. The earlier hang was Playwright 1.49.1. The fail fixture calls the real CLI with an unknown browser name.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | no | the workspace | Directory that has Playwright. |
| `browsers` | no | `chromium` | Browser names. |

## Permissions

`contents: read`.
