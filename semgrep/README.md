# Semgrep

Runs `semgrep scan` with the caller's rule packs. Exit 0 means no findings and exit 1 means findings. Any other exit fails the action. An empty SARIF is written only when the command exits 0 and writes no file. The action then removes results suppressed in source and uploads with the `category` input, which defaults to `semgrep`. The upload step does not fail the job.

Every `run` step uses `shell: sh`. The calling job sets `container: semgrep/semgrep`. The shared filter is `$GITHUB_ACTION_PATH/../lib/filter_sarif.py`. The fixture job runs inside that container and fails if that path does not resolve.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `rules` | yes | | Space-separated configs, passed as `--config`. |
| `exclude-rules` | no | empty | Space-separated `--exclude-rule` values. |
| `source` | no | `.` | Directory to scan. |
| `upload` | no | `true` | `false` skips the SARIF upload. |
| `category` | no | `semgrep` | SARIF category. |

## Permissions

`security-events: write` and `actions: read` for the upload. `contents: read` for the checkout.
