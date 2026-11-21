# Workflow conformance

Checks the caller's workflows.

- Every `uses` is a 40-character commit SHA, or a local `./` action.
- `runs-on` is `ubuntu-26.04` or `macos-26`.
- Container and service `image` values are pinned by digest.
- Each workflow has a top-level `permissions` block.
- `lint.yml` has a `lint` job, `test.yml` has a `test` job, and `security.yml` has `security-summary` when that file exists.
- Each of those gates has `if: always()`, lists every other job in its file under `needs`, and pins `lx-software-ltd/actions/require-jobs` by commit SHA.
- `pull_request` on `lint.yml` and `test.yml` has no `paths` or `paths-ignore` filter.
- The repository uses one `lx-software-ltd/actions` commit.
- A `.pre-commit-config.yaml` block for this repository has its own `rev`, and that `rev` equals that commit.

`profile: product` also requires `security.yml` jobs `checkov`, `codeql`, `pii-denylist`, `secrets-scan`, `dependency-audit`, `bandit`, `npm-audit`, and `security-summary`, plus a `semgrep/ci` job. `profile: producer` is this repository.

`mode` is `warn` or `enforce`. Warn prints the findings and exits 0.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | no | `warn` | `warn` or `enforce`. |
| `profile` | no | `product` | `product` or `producer`. |
| `root` | no | the workspace | Directory to check. |

## Permissions

`contents: read`.
