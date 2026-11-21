# CI contract

Written form of "the product repositories do the same thing". `workflow-conformance` (step SA-309) checks a repository against this file. This draft is the target. Mode stays `warn` until a repository has no open convergence row.

The `actions` repository is the producer. It is not a product caller. Which of these rules apply to it is in [This repository](#this-repository) below. `workflow-conformance` (SA-309) runs there too.

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

The gate job id is `lint` in `lint.yml`, `test` in `test.yml`, and `security-summary` in `security.yml`. A gate has `if: always()`, lists every other job in that file in `needs`, and fails unless those jobs succeeded.

`allow-skipped` defaults to false. It may be `true` in two cases, and both require a `changes` job in `needs` with every job listed on the gate:

- `security-summary`
- the `lint` and `test` gates in pair B (`evolvesprouts`, `siutindei`), which is the cost control in convergence row C07

A skipped job is a failure otherwise. Pair A does not use `allow-skipped`.

`pull_request` on `lint.yml` and `test.yml` has no path filter. `push` may filter by path.

## Runners

Linux jobs use `ubuntu-26.04`. macOS jobs use `macos-26`. The owner chose that label on 20 Nov 2026 (convergence row C03). It is what `macos-latest` selects today, so pinning it changes nothing until GitHub moves `macos-latest`.

## Pins and permissions

- Third-party actions are pinned by full 40-character SHA, with a version comment.
- `uses` of `lx-software-ltd/actions/<name>` is pinned by the same SHA the pre-commit `rev` uses.
- Every workflow has top-level `permissions: contents: read`. A job that needs more sets its own block.
- No workflow adds a long-lived AWS key. Deploy jobs use OIDC.

## Versions passed by callers

The organisation default for Node is major version 26. The owner chose it on 20 Nov 2026 (row C04). `setup-node` uses 26 as its default when SA-301 adds that action. Python's default is 3.12. Callers keep passing their current Node version until each repository's C04 pull request. `lts/*` is not the default: it would move on the next long-term-support release.

## Differences that stay

Hosting, mobile workflows, extra triggers (`repository_dispatch`, `board-*`, Figma sync, key management, the legacy import, the apex redirect probe), stack names, parameters, app directories, and rule exclusions. `findingalpha` has no Lighthouse run.

## This repository

`workflow-conformance` runs here as well as in the four product repositories. These rules apply to `actions` itself:

| Applies here | Rule |
| --- | --- |
| Yes | Top-level `permissions: contents: read`. A job that needs more sets its own block. |
| Yes | Third-party actions pinned by full SHA, with a version comment on the same line. |
| Yes | Linux jobs use `ubuntu-26.04`. |
| Yes | Gate jobs use `if: always()`, list every other job in that file, and fail unless those jobs succeeded. |
| Yes | `pull_request` on `lint.yml` and `test.yml` has no path filter. |
| No | `check-lockfiles.yml`, `semgrep.yml`, `verify-rulesets.yml`, `cdk-diff.yml`, deploy workflows, and the product job ids (`checkov`, `bandit`, `validate-agent-harness`, and the rest). |
| No | `allow-skipped`. Nothing in this repository is skipped as cost control. |
| No | A `v*` tag. Organization admin can create one through the `release-tags-create` bypass. Update and deletion stay blocked. Callers pin commit SHAs until a release exists. |

Workflows and jobs:

| File | Jobs |
| --- | --- |
| `lint.yml` | `lint-python` (compile, layout check, PII denylist, Gitleaks), gate `lint` |
| `test.yml` | `unit`, `require-jobs-pass`, `require-jobs-fail`, gate `test` |
| `security.yml` | `pii-denylist`, `secrets-scan`, `codeql` (languages `python` and `actions`), gate `security-summary` |

The `lint`, `test`, and `security-summary` gates pin `lx-software-ltd/actions/require-jobs@1a3cca7c38163f8164c262323601c34a4df5b7a4` (`# main 2026-11-20`). They must not use `uses: ./require-jobs`. A local action is loaded from the pull request, so a change that always exits 0 would turn the required check green while the fail fixture goes red. Fixture jobs may use `uses: ./require-jobs` to test the pull request's copy. The layout check rejects a local action on a gate job. The calling job needs `python3` on `PATH`.

`security-summary` aggregates `security.yml` only. `main-protection` applies to this repository and requires `lint` and `test`. It does not require `security-summary`, so a failure that exists only in `security.yml` does not block a merge. PII and Gitleaks also run inside `lint-python`, so those two fail the required `lint` check.

`scripts/pii-denylist.sha256` holds the 31 organisation digests. The owner approved the copy on 20 Nov 2026. The file has no plaintext. The PII job scans tracked source against them.

CodeQL scans Python and GitHub Actions. The Actions language is the one that covers the workflow files and composite actions in this repository.


## Checked by workflow-conformance

The action checks the pin, runner, permission, gate, path-filter, one-commit, and pre-commit `rev` rules above. `mode: warn` prints findings and exits 0. `mode: enforce` exits 1. This repository runs enforce on its own workflows. Product repositories start in warn and switch to enforce on their last close-out commit.
