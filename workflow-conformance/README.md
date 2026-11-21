# Workflow conformance

Checks the caller's workflows.

- Every `uses` is a 40-character commit SHA, or a local `./` action.
- `runs-on` is `ubuntu-26.04` or `macos-26`.
- Each workflow has a top-level `permissions` block.
- `lint.yml` has a `lint` job and `test.yml` has a `test` job.
- Those two files have no `pull_request` path filter.
- The repository uses one `lx-software-ltd/actions` commit.
- A `.pre-commit-config.yaml` `rev` for this repository equals that commit.

`mode` is `warn` or `enforce`. Warn prints the findings and exits 0.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | no | `warn` | `warn` or `enforce`. |
| `root` | no | the workspace | Directory to check. |

## Permissions

`contents: read`.
