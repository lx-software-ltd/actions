# Semgrep

Runs `semgrep scan` with the caller's rule packs. If the scan writes no SARIF file, the action writes an empty SARIF 2.1 document. It then removes results suppressed in source and uploads with category `semgrep`. The upload step does not fail the job.

Every `run` step uses `shell: sh`. The calling job sets `container: semgrep/semgrep`. The shared filter is `$GITHUB_ACTION_PATH/../lib/filter_sarif.py`. The fixture job runs inside that container and fails if that path does not resolve.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `rules` | yes | | Space-separated `--config` values. |
| `exclude-rules` | no | empty | Space-separated `--exclude-rule` values. |
| `source` | no | `.` | Directory to scan. |

## Permissions

`security-events: write` and `actions: read` for the upload. `contents: read` for the checkout.
