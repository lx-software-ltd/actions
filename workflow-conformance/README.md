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

Three product checks print `::warning::` and do not fail `enforce` yet: no direct `actions/setup-node` or `actions/setup-python`, `cdk-diff` and `cdk-deploy` name the same `plan-file` when both are used, and no `describe-stacks` except `.github/workflows/import-legacy-crm.yml`. The pin bump after the workflows comply turns those warnings into failures.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | no | `enforce` | `enforce` or `warn`. |
| `profile` | no | `product` | `product` or `producer`. |
| `root` | no | the workspace | Directory to check. |

## Permissions

`contents: read`.
