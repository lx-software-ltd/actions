# CI contract

`workflow-conformance` checks a repository against this file. Product repositories and this repository run `mode: enforce`.

The `actions` repository is the producer. It is not a product caller. Which of these rules apply to it is in [This repository](#this-repository) below.

## Workflow files

Every product repository has these files and job ids. A repository adds its own stack jobs under `lint.yml` and `test.yml`.

| File | Jobs | Fixed triggers | Free triggers |
| --- | --- | --- | --- |
| `lint.yml` | Per-stack lint jobs, `validate-agent-harness`, `workflow-conformance`, gate `lint` | `pull_request` with no path filter, `push` to `main` | `workflow_dispatch`, and a repository's own extra events |
| `test.yml` | Per-stack test jobs, gate `test` | `pull_request` with no path filter, `push` to `main` | `workflow_dispatch`, and a repository's own extra events |
| `security.yml` | `checkov`, `codeql`, `pii-denylist`, `secrets-scan`, `dependency-audit`, `bandit`, `npm-audit`, `security-summary` | `push` to `main`, `pull_request` with no path filter, weekly | `workflow_dispatch` |
| `semgrep.yml` | `semgrep/ci` | `push` to `main`, `pull_request` | Skips Dependabot. The job runs Semgrep in `scan` mode. |
| `check-lockfiles.yml` | `node-lockfiles`, `python-requirements`. Mobile repositories also `flutter-lockfiles`, `ios-lockfiles` | `pull_request`, `push` to `main` | `workflow_dispatch` |
| `verify-rulesets.yml` | `verify-branch-protection` | Weekly, Monday | `workflow_dispatch` |
| `cdk-diff.yml` | `diff` | Pull requests that touch infrastructure paths | |
| `cdk-bootstrap.yml` | `bootstrap` | Manual only | |
| `deploy-backend.yml` | `deploy` | `main` only, `environment: production` | |

All four repositories run `cdk bootstrap` from a manual `cdk-bootstrap.yml`. `cdk-diff.yml` runs on pull requests in `findingalpha`, `lx-software`, and `evolvesprouts`. A `siutindei` pull request warns and does not call AWS until `AWS_DIFF_ROLE_NAME` names a read-only role. That gap is in `docs/decisions.md`.

`evolvesprouts` names the harness job `validate-agent-rules`. The contract name is `validate-agent-harness`.

Web deploy is S3 and CloudFront. The public-site release workflows stay in the two repositories that have them.

## Gates

The gate job id is `lint` in `lint.yml`, `test` in `test.yml`, and `security-summary` in `security.yml`. A gate has `if: always()`, lists every other job in that file in `needs`, and fails unless those jobs succeeded. A skipped job is a failure.

`pull_request` on `lint.yml`, `test.yml`, and `security.yml` has no path filter. A required workflow with a path filter never reports, and the ruleset then blocks the merge. `push` may filter by path.

`main-protection` requires `lint`, `test`, and `security-summary`.

## Runners

Linux jobs use `ubuntu-26.04`. macOS jobs use `macos-26`.

## Pins and permissions

- Third-party actions are pinned by full 40-character SHA, with a version comment.
- `uses` of `lx-software-ltd/actions/<name>` is pinned by the same SHA the pre-commit `rev` uses. The same line has a `# main YYYY-MM-DD` comment, and that commit is on `main`.
- Every workflow has top-level `permissions: contents: read`. A job that needs more sets its own block.
- No workflow adds a long-lived AWS key. Deploy jobs use OIDC.

Several product workflows still grant more than `contents: read` at the top level. Conformance reports that.

## Versions passed by callers

Node is major version 26. Python is 3.12. `lts/*` is not a version pin: it moves on the next long-term-support release. Callers omit an input that only restates the action default.

## Differences that stay

Hosting details, mobile workflows, extra triggers (`repository_dispatch`, `board-*`, Figma sync, key management, the legacy import, the apex redirect probe), stack names, parameters, app directories, and rule exclusions. `findingalpha` has no Lighthouse run.

## This repository

`workflow-conformance` runs here as well as in the four product repositories. These rules apply to `actions` itself:

| Applies here | Rule |
| --- | --- |
| Yes | Top-level `permissions: contents: read`. A job that needs more sets its own block. |
| Yes | Third-party actions pinned by full SHA, with a version comment on the same line. |
| Yes | Linux jobs use `ubuntu-26.04`. |
| Yes | Gate jobs use `if: always()`, list every other job in that file, and fail unless those jobs succeeded. |
| Yes | `pull_request` on `lint.yml`, `test.yml`, and `security.yml` has no path filter. |
| No | `check-lockfiles.yml`, `semgrep.yml`, `verify-rulesets.yml`, `cdk-diff.yml`, deploy workflows, and the product job ids (`checkov`, `bandit`, `validate-agent-harness`, and the rest). |
| No | A `v*` tag. Organization admin can create one through the `release-tags-create` bypass. Update and deletion stay blocked. Callers pin commit SHAs. |

Workflows and jobs:

| File | Jobs |
| --- | --- |
| `lint.yml` | `lint-python` (compile, layout check, Ruff), `workflow-conformance`, gate `lint` |
| `test.yml` | `unit`, one fixture job per action case, gate `test` |
| `security.yml` | `pii-denylist`, `secrets-scan`, `codeql` (languages `python` and `actions`), gate `security-summary` |
| `dependency-submission.yml` | `check`, `submit` |
| `sync-labels.yml` | `sync` |

`dependency-submission.yml` is named Dependency Submission. `check` runs unless the event is a push to `main`. `submit` runs on a push to `main` and sets `contents: write`. The display name keeps this workflow apart from GitHub's Dependency Graph entry.

`sync-labels.yml` applies `sync-labels/labels.json` to this repository on a push to `main`, every Monday, and `workflow_dispatch`. The catalogue includes `mobile`. The job sets `issues: write`. It is not a required check. `github.token` writes labels on this repository.

The `lint`, `test`, and `security-summary` gates pin `lx-software-ltd/actions/require-jobs@1a3cca7c38163f8164c262323601c34a4df5b7a4` (`# main 2026-11-20`). They must not use `uses: ./require-jobs`. A local action is loaded from the pull request, so a change that always exits 0 would turn the required check green while the fail fixture goes red. Fixture jobs may use `uses: ./require-jobs` to test the pull request's copy. The layout check rejects a local action on a gate job. The calling job needs `python3` on `PATH`.

`security-summary` aggregates `security.yml`. `main-protection` requires it, with `lint` and `test`. PII and Gitleaks run in `security.yml`.

`scripts/pii-denylist.sha256` holds the 31 organisation digests. The owner approved the copy on 20 Nov 2026. The file has no plaintext. The PII job scans tracked source against them.

CodeQL scans Python and GitHub Actions. The Actions language is the one that covers the workflow files and composite actions in this repository.

## Checked by workflow-conformance

The action checks the pin, runner, permission, image-digest, gate, path-filter, one-commit, `# main YYYY-MM-DD` comment, and pre-commit `rev` rules above. A `pull_request` `paths-ignore` is a path filter. A gate job has `if: always()`, lists every other job in that file under `needs`, and pins `require-jobs` by commit SHA. `security-summary` is that gate in `security.yml`. `lint.yml`, `test.yml`, and `security.yml` must exist, and none of them may filter `pull_request` by path. Top-level permissions are `contents: read`. Container and service images are pinned by digest.

`profile: product` also requires the `security.yml` job ids in the table above and a `semgrep/ci` job. `profile: producer` is this repository, which does not have those product job ids. `mode: enforce` exits 1 when there is a finding. `mode: warn` prints findings and exits 0. The default mode is `enforce`.

Three product checks follow `alignment`. The default is `warn`: they print `::warning::` and do not fail `enforce`. All four product repositories set `alignment: enforce`.

- A workflow does not call `actions/setup-node` or `actions/setup-python`. A quoted `uses` counts.
- When both `cdk-diff` and `cdk-deploy` are used, they name the same `plan-file` or the same inline `plan`. The value runs to the end of the line, or through the block body. A `${{ }}` path is the whole value. A step written as `name:`, then `uses:`, then `with:` is read the same way as one that starts at `uses:`.
- A workflow does not call `describe-stacks`. `import-legacy-crm.yml` is the allow-list, because that import stays inline.
