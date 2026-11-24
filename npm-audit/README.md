# npm audit

Runs `npm audit` in each directory. The default level is `high` and the default omit is `dev`. A registry 503 is retried up to four times. Any other failure, including a finding, stops at once. A listed directory with no `package.json` fails.

The caller installs dependencies first.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `directories` | yes | | Newline-separated directories. |
| `audit-level` | no | `high` | `--audit-level`. |
| `omit` | no | `dev` | `--omit`. |

## Permissions

`contents: read`. The audit reaches the npm registry.
