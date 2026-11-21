# Checkov CloudFormation

Runs Checkov on a directory the caller has already synthesised. Findings whose SARIF suppression kind is `inSource` are removed. The SARIF upload uses `continue-on-error`, so an upload failure does not fail the scan.

The calling job needs `contents: read`, `security-events: write`, and `actions: read` when it uploads. The caller keeps its own synth step.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `directory` | yes | | Synthesised template directory. |
| `config-file` | no | empty | Checkov config. |
| `framework` | no | `cloudformation` | Passed to Checkov. |
| `skip-if-missing` | no | `false` | A missing directory writes an empty SARIF and passes. |
| `upload` | no | `true` | `false` skips the SARIF upload. |

Checkov is `bridgecrewio/checkov-action` `3f0caf0c3aa9f56ade6b49f6e60b63aaeafb75a3` (`v12.3141.0`).

## Permissions

`security-events: write` for the upload. `actions: read` is what the upload action asks for.
