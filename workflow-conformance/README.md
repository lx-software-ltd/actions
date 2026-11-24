# Workflow conformance

Checks the caller's workflows.

- Every `uses` is a 40-character commit SHA, or a local `./` action.
- `runs-on` is `ubuntu-26.04` or `macos-26`.
- Container and service `image` values are pinned by digest.
- Each workflow has top-level `permissions: contents: read`.
- `lint.yml`, `test.yml`, and `security.yml` exist. Their gates are `lint`, `test`, and `security-summary`.
- Each of those gates has `if: always()`, lists every other job in its file under `needs`, and pins `lx-software-ltd/actions/require-jobs` by commit SHA.
- `pull_request` on `lint.yml`, `test.yml`, and `security.yml` has no `paths` or `paths-ignore` filter.
- The repository uses one `lx-software-ltd/actions` commit, and that `uses` line has a `# main YYYY-MM-DD` comment.
- A `.pre-commit-config.yaml` block for this repository has its own `rev`, and that `rev` equals that commit.

`profile: product` also requires `security.yml` jobs `checkov`, `codeql`, `pii-denylist`, `secrets-scan`, `dependency-audit`, `bandit`, `npm-audit`, and `security-summary`, plus a `semgrep/ci` job. `profile: producer` is this repository.

`mode` is `enforce` or `warn`. Enforce exits 1 when there is a finding. Warn prints the findings and exits 0. The default is `enforce`.

`alignment` is `warn` or `enforce`. It applies to three product checks: no direct `actions/setup-node` or `actions/setup-python`, quoted or not; `cdk-diff` and `cdk-deploy` name the same `plan-file` or the same inline `plan` when both are used, including a step that puts `name:` before `uses:`; and no `describe-stacks`. `warn` prints `::warning::` and does not fail. `enforce` makes those findings fail for this caller when `mode` is `enforce`. The default is `enforce`.

`templates` is `off`, `warn`, or `enforce`. For `profile: product`, `warn` and `enforce` compare each file in `templates/workflows/` with `.github/workflows/` of the same name. A template whose first line is `# template:if-present` produces no finding when that product file is absent. When the file is present, the marker is ignored and the rest must match. A `# template:set` block may differ. It cannot contain a step, `continue-on-error:`, or `if:`. A marker counts at any indent. A `# template:optional <id>` block may be omitted; when it is present, its unmarked lines must match. The blank line that separates an optional block from the next job sits inside the block. A blank line between two steps that stay when the block is omitted sits after `# template:end`. An `lx-software-ltd/actions` pin and its `# main YYYY-MM-DD` comment are not compared. `warn` prints `::warning::` and does not fail. `enforce` makes a mismatch a finding. The default is `warn`. `profile: producer` skips the comparison.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | no | `enforce` | `enforce` or `warn`. |
| `profile` | no | `product` | `product` or `producer`. |
| `alignment` | no | `enforce` | `warn` or `enforce` for the three product alignment checks. |
| `templates` | no | `warn` | `off`, `warn`, or `enforce` for the workflow templates. |
| `root` | no | the workspace | Directory to check. |

## Permissions

`contents: read`.
