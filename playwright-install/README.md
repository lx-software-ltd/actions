# Playwright install

Runs `npx playwright install <browsers> --with-deps` with a 180 second limit. If that fails, it installs the browser without apt packages, which is the fallback `siutindei` uses when the apt mirrors cannot be reached.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | no | the workspace | Directory that has Playwright. |
| `browsers` | no | `chromium` | Browser names. |

## Permissions

`contents: read`.
