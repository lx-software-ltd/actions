# Gitleaks

Downloads the pinned Gitleaks release, checks the sha256, and scans. The download is retried. This does not use the licensed Gitleaks GitHub Action. Callers do not set `GITLEAKS_LICENSE`. No repository in `lx-software-ltd` keeps that secret.

The calling job needs `contents: read` and a checkout. Full history is the caller's choice (`fetch-depth: 0`).

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `version` | no | `8.30.1` | Release to download. |
| `checksum` | no | the 8.30.1 linux x64 digest | sha256 of that tarball. |
| `config-path` | no | empty | Passed as `--config` when set. |
| `source` | no | `.` | Directory passed to `--source`. |

## Permissions

No extra token permissions. The action does not call the GitHub API.

## Example

```yaml
      - uses: lx-software-ltd/actions/gitleaks@<40-hex> # main YYYY-MM-DD
```
