# Bandit

Installs Bandit and runs it on the caller's paths. `skip` is passed to `--skip`.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `paths` | yes | | Space-separated paths. |
| `skip` | no | empty | Test ids to skip. |
| `root` | no | the workspace | Working directory. |

## Permissions

`contents: read`.
