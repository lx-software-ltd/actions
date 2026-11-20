# CI contract

Written form of "the product repositories do the same thing". `workflow-conformance` (step SA-309) checks a repository against this file. This draft is the target. Mode stays `warn` until a repository has no open convergence row.

The `actions` repository is the producer. It is not a product caller. Its own workflows are `lint.yml`, `test.yml`, and `security.yml`.

## Workflow files

Every product repository has these files and job ids. A repository adds its own stack jobs under `lint.yml` and `test.yml`.

| File | Jobs | Fixed triggers | Free triggers |
| --- | --- | --- | --- |
| `lint.yml` | Per-stack lint jobs, `validate-agent-harness`, `workflow-conformance`, gate `lint` | `pull_request` with no path filter, `push` to `main` | `workflow_dispatch`, and a repository's own extra events |
| `test.yml` | Per-stack test jobs, gate `test` | `pull_request` with no path filter, `push` to `main` | `workflow_dispatch`, and a repository's own extra events |
| `security.yml` | `checkov`, `codeql`, `pii-denylist`, `secrets-scan`, `dependency-audit`, `bandit`, `npm-audit`, `security-summary` | `push` to `main`, `pull_request`, weekly | `workflow_dispatch` |
| `semgrep.yml` | `semgrep/ci` | `push` to `main`, `pull_request` | Skips Dependabot |
| `check-lockfiles.yml` | `node-lockfiles`, `python-requirements`. Pair B also `flutter-lockfiles`, `ios-lockfiles` | `pull_request`, `push` to `main` | `workflow_dispatch` |
| `verify-rulesets.yml` | `verify-branch-protection` | Weekly, Monday | `workflow_dispatch` |
| `cdk-diff.yml` | `diff` | Pull requests that touch infrastructure paths | |
| `cdk-bootstrap.yml` | `bootstrap` | Manual only | |
| `deploy-backend.yml` | `deploy` | `main` only, `environment: production` | |

Web deploy workflows stay per hosting model.

## Gates

The gate job id is `lint` in `lint.yml`, `test` in `test.yml`, and `security-summary` in `security.yml`. A gate has `if: always()`, lists every other job in that file in `needs`, and fails unless those jobs succeeded. `security-summary` may pass `allow-skipped` only when a `changes` job is in `needs` and skipping is the intended cost control.

`pull_request` on `lint.yml` and `test.yml` has no path filter. `push` may filter by path.

## Runners

Linux jobs use `ubuntu-26.04`. The macOS label is not chosen yet (convergence row C03).

## Pins and permissions

- Third-party actions are pinned by full 40-character SHA, with a version comment.
- `uses` of `lx-software-ltd/actions/<name>` is pinned by the same SHA the pre-commit `rev` uses.
- Every workflow has top-level `permissions: contents: read`. A job that needs more sets its own block.
- No workflow adds a long-lived AWS key. Deploy jobs use OIDC.

## Versions passed by callers

Node and Python versions are inputs until the organisation default is chosen. The action defaults are the target: Python 3.12, and the Node version recorded in `setup-node` once the owner picks it (row C04). Callers pass their current value until then.

## Differences that stay

Hosting, mobile workflows, extra triggers (`repository_dispatch`, `board-*`, Figma sync, key management, the legacy import, the apex redirect probe), stack names, parameters, app directories, and rule exclusions. `findingalpha` has no Lighthouse run.
