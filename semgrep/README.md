# Semgrep

Runs Semgrep with the caller's rule packs. Exit 0 means no findings and exit 1 means findings. Any other exit fails the action, so a rejected flag or a missing config is not replaced with an empty SARIF. An empty SARIF is written only when the command exits 0 and writes no file. The action then removes results suppressed in source and uploads with category `semgrep`. The upload step does not fail the job.

Every `run` step uses `shell: sh`. The calling job sets `container: semgrep/semgrep`. The shared filter is `$GITHUB_ACTION_PATH/../lib/filter_sarif.py`. The fixture job runs inside that container and fails if that path does not resolve.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | no | `scan` | `scan` runs `semgrep scan --config`. `ci` runs `semgrep ci` and passes `rules` through `SEMGREP_RULES`, which is how pair A invokes it. |
| `rules` | yes | | Space-separated configs. Scan mode uses `--config`. ci mode uses `SEMGREP_RULES`. |
| `exclude-rules` | no | empty | Space-separated `--exclude-rule` values. |
| `source` | no | `.` | Directory to scan. |
| `upload` | no | `true` | `false` skips the SARIF upload. |

## Permissions

`security-events: write` and `actions: read` for the upload. `contents: read` for the checkout.
