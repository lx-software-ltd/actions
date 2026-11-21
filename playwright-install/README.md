# Playwright install

Runs `npx playwright install <browsers> --with-deps` with a 180 second limit. If that command does not exit 0, it installs the browser without apt packages, which is the fallback `siutindei` uses when the apt mirrors cannot be reached. The second attempt has the same limit. `timeout --kill-after` stops a download that ignores the first signal.

On `ubuntu-26.04`, Playwright 1.49.1's Chromium download reached 100% and then did not exit. The pass fixture therefore stubs `npx` and checks that the action exits 0. The fail fixture still calls the real CLI with an unknown browser name.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | no | the workspace | Directory that has Playwright. |
| `browsers` | no | `chromium` | Browser names. |

## Permissions

`contents: read`.
