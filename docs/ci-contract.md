# CI contract

`workflow-conformance` checks a repository against this file. Product repositories and this repository run `mode: enforce`.

The `actions` repository is the producer. It is not a product caller. Which of these rules apply to it is in [This repository](#this-repository) below.

## Workflow files

Every product repository has these files. Top-level keys run `name`, `on`, `permissions`, `concurrency`, `jobs`, and strings use double quotes. A repository adds the stack jobs named in [Differences that stay](#differences-that-stay).

### In place

These five check workflows match `templates/workflows/`. The comparison ignores marked lines.

| File | Jobs | Triggers |
| --- | --- | --- |
| `semgrep.yml` | `semgrep` named `semgrep/ci` | `push` to `main`, `pull_request`, Monday 08:00 UTC, `workflow_dispatch`. Skips Dependabot |
| `check-lockfiles.yml` | `node-lockfiles`, `python-requirements`. Mobile repositories also `flutter-lockfiles` and `ios-lockfiles` | `pull_request`, `push` to `main`, `workflow_dispatch` |
| `verify-rulesets.yml` | `verify-branch-protection` | Monday 09:00 UTC, `workflow_dispatch` |
| `dependency-submission.yml` | `check`, `submit` | `pull_request`, `push` to `main`, `workflow_dispatch` |
| `cdk-bootstrap.yml` | `bootstrap` | `workflow_dispatch` only |
| `security.yml` | `checkov`, `codeql`, `pii-denylist`, `secrets-scan`, `dependency-audit`, `bandit`, `npm-audit`, `security-summary` | `push` to `main`, `pull_request` with no path filter, Monday 08:00 UTC, `workflow_dispatch` |

`templates/workflows/` holds that canonical text. `lint.yml`, `test.yml`, and the deploy workflows are not templated yet.

Bandit has no skip list. A reviewed line carries `# nosec`. CodeQL uses the matrix languages `python` and `javascript-typescript`, and the category is `/language:` plus that language. Checkov synthesizes with `npm run synth:ci`.

All four repositories run `cdk bootstrap` from a manual `cdk-bootstrap.yml`. `cdk-diff.yml` runs on pull requests in `findingalpha`, `lx-software`, and `evolvesprouts`. A `siutindei` pull request warns and does not call AWS until `AWS_DIFF_ROLE_NAME` names a read-only role. That gap is in `docs/decisions.md`.

Web deploy is S3 and CloudFront. Public-site release is two profiles, staged (`evolvesprouts`, `siutindei`) and direct (`findingalpha`, `lx-software`). Both profiles still use the filename `deploy-public-www.yml`.

A workflow that runs on pull requests or writes to AWS has a concurrency group. Semgrep uploads with category `semgrep`. `repository_dispatch` has been removed from the check workflows above. It remains on the CDK diff, deploy, and promote workflows that already declared it.

### Phase 2 target: gate workflows

These rows are the target. They are not the files in the product repositories today. `evolvesprouts` still calls the harness job `validate-agent-rules`. `findingalpha` and `lx-software` still call `build-cdk`. `findingalpha` and `lx-software` still run Ruff and mypy directly, and `evolvesprouts` and `siutindei` do not run mypy in `lint.yml`.

| File | Jobs | Triggers |
| --- | --- | --- |
| `lint.yml` | `validate-agent-harness`, `workflow-conformance`, `lint-python`, one `lint-<app>` per Node app, `lint-cdk`, `type-check`, `repo-checks`, gate `lint`. Mobile repositories also `lint-openapi` and `lint-dart` | `pull_request` and `push` to `main`, neither with a path filter, plus `workflow_dispatch` |
| `test.yml` | `test-python`, one `test-<app>` per Node app, `test-infrastructure`, gate `test`. Playwright repositories also `e2e-<app>`. Mobile repositories also `test-flutter` and `build-android` | `pull_request` and `push` to `main`, neither with a path filter, plus `workflow_dispatch` |

### Phase 3 target: deploy workflows

These rows are the target. They are not the files in the product repositories today. Only `findingalpha` sets `if: github.ref == 'refs/heads/main'` on its production deploy jobs. The staged public-site file is still named `deploy-public-www.yml`.

| File | Jobs | Triggers |
| --- | --- | --- |
| `cdk-diff.yml` | `diff`, and `pull-request` where the read-only role is the only way to pass deploy parameters | Pull requests that touch infrastructure, and a manual run |
| `deploy-backend.yml` | `deploy` | `main` only, `environment: production` |

The target adds `if: github.ref == 'refs/heads/main'` on every production deploy job, as well as the environment. The target renames the staged public-site file to `deploy-public-www-staging.yml`. `repository_dispatch` is accepted on `cdk-diff.yml`, `deploy-*.yml`, and `promote-public-www.yml`, with the file stem as the event type.

## Gates

The gate job id is `lint` in `lint.yml`, `test` in `test.yml`, and `security-summary` in `security.yml`. A gate has `if: always()`, lists every other job in that file in `needs`, and fails unless those jobs succeeded. A skipped job is a failure.

`pull_request` on `lint.yml`, `test.yml`, and `security.yml` has no path filter. A required workflow with a path filter never reports, and the ruleset then blocks the merge. `push` to `main` on `lint.yml` and `test.yml` has no path filter either. The checker rejects a `pull_request` path filter. A `push` path filter is not part of that check yet.

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

A difference that is not in this list is not a shared workflow. Templates ignore only the marked lines below. The other rows are whole jobs or whole files.

| Kind | What | Where |
| --- | --- | --- |
| Marked lines | App directories, stack and output names, requirement files, dated audit ignores, coverage floor, build environment blocks, deploy path filters, Lighthouse page list | All four |
| Stack: mobile | `flutter-lockfiles`, `ios-lockfiles`, `lint-dart`, `test-flutter`, `build-android`, `deploy-ios.yml`, `deploy-mobile.yml` | `evolvesprouts`, `siutindei` |
| Stack: database | Postgres service in `test-python`. Seed and migration inputs on `deploy-backend.yml` | `evolvesprouts`, `siutindei` |
| Stack: OpenAPI | `lint-openapi` | `evolvesprouts`, `siutindei` |
| Stack: Docker arm64 bundling | QEMU step in `cdk-diff.yml` and `deploy-backend.yml` | `findingalpha`, `lx-software` |
| Stack: Playwright | `e2e-<app>` jobs | `findingalpha`, `lx-software`, `siutindei` |
| Stack: LFS and search fixture | `lfs: true` checkouts, the fixture sync before synth, the sqlite and Amplify steps | `siutindei` |
| Release profile | Staged (staging deploy, smoke, promote) or direct (`deploy-public-www.yml`). Phase 3 renames the staged file to `deploy-public-www-staging.yml` | Mobile pair, web pair |
| Parameter source | `params/production.json` with `CDK_PARAM_*`, or `P_*` variables. Same step order | Mobile pair, web pair |
| Product workflows | `deploy-training.yml`, `figma-refresh-token.yml`, `figma-token-studio-sync.yml` | `evolvesprouts` |
| Product workflows | `mint-openrouter-keys.yml` | `lx-software` |
| Product workflows | `board-agent.yml`, `board-merge-staging.yml`, `board-promote.yml`, `close-note-tag-issues.yml`. These names stay, because `lx-software` dispatches them by filename | `siutindei` |

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

Three product checks follow `alignment`. The default is `enforce`. `warn` prints `::warning::` and does not fail.

- A workflow does not call `actions/setup-node` or `actions/setup-python`. A quoted `uses` counts.
- When both `cdk-diff` and `cdk-deploy` are used, they name the same `plan-file` or the same inline `plan`. The value runs to the end of the line, or through the block body. A `${{ }}` path is the whole value. A step written as `name:`, then `uses:`, then `with:` is read the same way as one that starts at `uses:`.
- A workflow does not call `describe-stacks`.

`templates` compares each file in `templates/workflows/` with the product workflow of the same name. The default is `warn`. `enforce` makes a mismatch a finding when `mode` is `enforce`. `off` skips the comparison. `profile: producer` skips it.

A `# template:set` line opens a block and `# template:end` closes it. The lines between the markers may differ, including how many there are. The marker lines stay. A marker counts at any indent, so it can sit inside a YAML block. A `# template:optional <id>` block may be absent. The blank line that separates it from the next job sits inside the block, so omitting the block does not leave that blank behind. When the block is present, its unmarked lines match the template. Nested `# template:set` blocks inside it follow the same rule. The comparison treats every `lx-software-ltd/actions/<name>@<sha> # main YYYY-MM-DD` as the same pin. The pin check above still requires one real SHA and a real date.
