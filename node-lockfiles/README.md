# Node lockfiles

Runs `npm ci` in each listed directory and fails when `package-lock.json` is missing or `git diff` shows it changed. A directory with no `package.json` is skipped.

The caller runs `setup-node` first. This action does not install Node.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `directories` | yes | | Newline-separated directories. |

## Permissions

`contents: read` for the checkout. No token calls.
