# CI contract

`workflow-conformance` checks a repository against this file. Product repositories and this repository run `mode: enforce`.

The `actions` repository is the producer. It is not a product caller. Which of these rules apply to it is in [This repository](#this-repository) below.

## Workflow files

Every product repository has these files. Top-level keys run `name`, `on`, `permissions`, `concurrency`, `jobs`, and strings use double quotes. A repository adds the stack jobs named in [Differences that stay](#differences-that-stay).

### In place

These check and deploy workflows match `templates/workflows/`. The comparison ignores marked lines. A template whose first line is `# template:if-present <capability>` is present exactly when that capability's probe exists. `!<capability>` is present exactly when the probe does not. A bare `# template:if-present` still allows the file to be absent.

| File | Jobs | Triggers |
| --- | --- | --- |
| `verify-rulesets.yml` | `verify-branch-protection` | Monday 09:00 UTC, `workflow_dispatch` |
| `sync-labels.yml` | `sync` | `push` to `main`, Monday 08:00 UTC, `workflow_dispatch`. Applies the catalogue to the calling repository. Not a required check |
| `dependabot-batch.yml` | `batch` | `workflow_dispatch` and `15 */2 * * 1-5`. Opens one batch pull request. Not a required check |
| `dependency-submission.yml` | `check`, `submit` | `pull_request`, `push` to `main`, `workflow_dispatch` |
| `cdk-bootstrap.yml` | `bootstrap` | `workflow_dispatch` only |
| `security.yml` | `checkov`, `codeql`, `pii-denylist`, `secrets-scan`, `dependency-audit`, `bandit`, `npm-audit`, `semgrep` named `semgrep/ci`, `security-summary` | `push` to `main`, `pull_request` with no path filter, Monday 08:00 UTC, `workflow_dispatch` |
| `lint.yml` | `validate-agent-harness`, `repo-checks`, `lint-python`, one `lint-<app>` per Node app, `lint-cdk`, `type-check`, `workflow-conformance`, `node-lockfiles`, `python-requirements`, gate `lint`. Mobile repositories also `lint-openapi`, `lint-dart`, and `flutter-lockfiles`. `ios-lockfiles` when a tracked `Podfile` exists (none today) | `pull_request` and `push` to `main`, neither with a path filter, plus `workflow_dispatch` |
| `test.yml` | `test-python`, one `test-<app>` per Node app, `test-infrastructure`, gate `test`. Playwright repositories also `e2e-<app>`. Mobile repositories also `test-flutter` and `build-android` | `pull_request` and `push` to `main`, neither with a path filter, plus `workflow_dispatch` |
| `cdk-diff.yml` | `diff` (main, `environment: production`, `GitHubActionsRole`) and `pull-request` (read-only role) | Pull requests that touch infrastructure, `repository_dispatch`, `workflow_dispatch` |
| `deploy-backend.yml` | `deploy` | `main` only, `environment: production` |
| `deploy-admin-web.yml` | `deploy` | `main` only, `environment: production`. The web pair also runs after Deploy Backend |
| `lighthouse-public-www.yml` | `lighthouse` | Pull requests that touch the public site, Monday 06:15 UTC, `workflow_dispatch` |
| `manage-api-keys.yml` | `manage` | `workflow_dispatch`. Present on the web pair |
| `deploy-public-www.yml` | `build-and-deploy` | `main` only, `environment: production`. Present on the direct pair |
| `deploy-public-www-staging.yml` | `build-and-deploy` | evolvesprouts pushes `main`. siutindei pushes `staging`. `environment: staging`. No main-branch guard |
| `smoke-public-www-staging.yml` | `smoke` | `workflow_dispatch`, `environment: staging` |
| `promote-public-www.yml` | `prepare`, `promote` | `main` only, `environment: production`. siutindei also runs at 04:00 Hong Kong time |
| `deploy-ios.yml` | `build-and-deploy` | `main` only, `macos-26`, `environment: production` |
| `deploy-mobile.yml` | `build-and-deploy` | `main` only, `environment: production` |

The `batch` job sets `actions: write`, `contents: write`, and `pull-requests: write` at job level.

`templates/workflows/` holds that canonical text. `scripts/ci/` and `scripts/deploy/` are the per-repository seam. Gate jobs call `scripts/ci/`. Deploy jobs call `scripts/deploy/`. `lint-python` runs `scripts/ci/mypy.sh` after pre-commit. findingalpha and lx-software type-check each Lambda directory, `scripts`, and `.cursor/hooks` with mypy 1.8.0. evolvesprouts and siutindei run mypy 1.8.0 on the directories that pass and list the rest in a `# mypy pending:` comment.

Bandit has no skip list. Tests that sit next to the scanned code are passed in `exclude`. An assert that remains in application code carries `# nosec`. CodeQL uses the matrix languages `python` and `javascript-typescript`, and the category is `/language:` plus that language. Checkov synthesizes with `npm run synth:ci`. The public-site certificate stays a CloudFormation parameter. Deploy reads it from `secrets.CDK_PARAM_PUBLIC_WEBSITE_CERTIFICATE_ARN`.

All four repositories run `cdk bootstrap` from a manual `cdk-bootstrap.yml`. `cdk-diff.yml` has two jobs in all four. `diff` runs on main with `environment: production` and `GitHubActionsRole`. `pull-request` uses the read-only role. `AWS_DIFF_ROLE_NAME` is unset as a repository variable everywhere, so pull-request diffs warn and do not call AWS. That gap is in `docs/decisions.md`. QEMU is set up in `cdk-diff.yml` and `deploy-backend.yml` in all four. The deployment region comes from `scripts/deploy/cdk-prepare.sh region`.

Web deploy is S3 and CloudFront. Public-site release is two profiles. The staged pair (`evolvesprouts`, `siutindei`) uses `deploy-public-www-staging.yml`, `smoke-public-www-staging.yml`, and `promote-public-www.yml`. The direct pair (`findingalpha`, `lx-software`) uses `deploy-public-www.yml`. Production deploy jobs set `if: github.ref == 'refs/heads/main'` and `environment: production`. Staging jobs do not add a main-branch guard, because siutindei deploys staging from the staging branch. Admin SPA settings come from stack outputs on the web pair and from repository variables on the mobile pair.

A workflow that runs on pull requests or writes to AWS has a concurrency group. Semgrep is the `semgrep` job in `security.yml`, named `semgrep/ci`, and uploads with category `semgrep`. It runs for every actor. A skip would fail `security-summary`. Lockfile jobs are in `lint.yml`: `node-lockfiles` and `python-requirements` in every product, `flutter-lockfiles` when `mobile` matches, and `ios-lockfiles` when `ios-pods` matches. `repository_dispatch` has been removed from the check workflows above. It remains on `cdk-diff.yml`, `deploy-*.yml`, and `promote-public-www.yml`, with the file stem as the event type.

## Gates

The gate job id is `lint` in `lint.yml`, `test` in `test.yml`, and `security-summary` in `security.yml`. A gate has `if: always()`, lists every other job in that file in `needs`, and fails unless those jobs succeeded. A skipped job is a failure.

`pull_request` on `lint.yml`, `test.yml`, and `security.yml` has no path filter. A required workflow with a path filter never reports, and the ruleset then blocks the merge. `push` to `main` on `lint.yml` and `test.yml` has no path filter either. The checker rejects a `pull_request` path filter. A `push` path filter is not part of that check yet.

`main-protection` requires `lint`, `test`, and `security-summary`. `lint` needs every lockfile job present in `lint.yml`. `security-summary` needs `semgrep`. `check-lockfiles.yml` and `semgrep.yml` are not workflows.

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

These are not workflow text. A block that exists only in some repositories is a capability, not a row here.

| Kind | What | Where |
| --- | --- | --- |
| Value blocks | Stack names, app directories, requirement files, dated ignores, env lists, path filters, Lighthouse page lists, S3 profiles, Bandit and CodeQL inputs, gate `needs` lists | All four |
| Repository seam | `scripts/ci/` holds the checks `lint.yml` and `test.yml` call. `scripts/deploy/` holds the deploy commands | All four |
| Release profile | Staged (`deploy-public-www-staging.yml`, smoke, promote) or direct (`deploy-public-www.yml`) | Mobile pair, web pair |
| Admin build settings | Stack outputs on the web pair. Repository variables on the mobile pair | Web pair, mobile pair |
| Parameter source | `CDK_PARAM_*` or `P_*`. Same step order | Mobile pair, web pair |
| Secret names | Per-product secret and variable names inside value blocks | All four |
| Product workflows | `deploy-training.yml`, `figma-refresh-token.yml`, `figma-token-studio-sync.yml` | `evolvesprouts` |
| Product workflows | `mint-openrouter-keys.yml` | `lx-software` |
| Product workflows | `board-agent.yml`, `board-merge-staging.yml`, `board-promote.yml`, `close-note-tag-issues.yml`. These names stay, because `lx-software` dispatches them by filename | `siutindei` |

### Capabilities

`templates/capabilities.json` maps each capability to a probe path. A `# template:optional` id is that capability name. The block is present exactly when the probe matches, and the same id may repeat in one file.

| Capability | Probe | Repositories today |
| --- | --- | --- |
| `mobile` | `apps/*/pubspec.yaml` | evolvesprouts, siutindei |
| `ios-pods` | `apps/*/ios/Podfile` | none |
| `openapi` | `docs/api/*.yaml` | evolvesprouts, siutindei |
| `database` | `backend/db` | evolvesprouts, siutindei |
| `migration-recovery` | `scripts/check_stack_invariants.py` | siutindei |
| `training` | `apps/training/package.json` | evolvesprouts |
| `search-fixture` | `scripts/codegen/sync-activity-search-staging-fixture.sh` | siutindei |
| `playwright-admin` | `apps/admin_web/playwright.config.*` | findingalpha, lx-software, siutindei |
| `playwright-public` | `apps/public_www/playwright.config.*` | evolvesprouts, siutindei |
| `next-admin` | `apps/admin_web/next.config.*` | evolvesprouts, siutindei |
| `next-public` | `apps/public_www/next.config.*` | evolvesprouts, siutindei |
| `public-build-env` | `scripts/deploy/resolve-public-www-build-env.sh` | evolvesprouts, siutindei |
| `admin-stack-settings` | `scripts/deploy/check-admin-spa-settings.sh` | findingalpha, lx-software |
| `amplify` | `scripts/deploy/build_amplify_config.py` | siutindei |
| `catalogue` | `scripts/deploy/fetch-public-www-catalogue-snapshot.sh` | siutindei |
| `indexnow` | `scripts/deploy/indexnow.py` | siutindei |
| `edge-verify` | `scripts/deploy/report_public_www_edge_verify.sh` | evolvesprouts |
| `staged-release` | `scripts/deploy/deploy-public-www.sh` | evolvesprouts, siutindei |
| `public-api-keys` | `scripts/deploy/create-api-key.sh` | findingalpha, lx-software |

`deploy-backend.yml` offers `destroy_before_deploy` for `migration-recovery`. That probe is the stack-invariant check, present in the only repository that passes `destroy`. `force_migration_run` and `run_seed_data` follow `database`. `deploy-ios.yml` and `deploy-mobile.yml` follow `mobile`. The staged public-site workflows follow `staged-release`. `deploy-public-www.yml` follows `!staged-release`. `manage-api-keys.yml` follows `public-api-keys`. A workflow with no template is listed in `templates/untemplated-workflows.txt`.

## This repository

`workflow-conformance` runs here as well as in the four product repositories. These rules apply to `actions` itself:

| Applies here | Rule |
| --- | --- |
| Yes | Top-level `permissions: contents: read`. A job that needs more sets its own block. |
| Yes | Third-party actions pinned by full SHA, with a version comment on the same line. |
| Yes | Linux jobs use `ubuntu-26.04`. |
| Yes | Gate jobs use `if: always()`, list every other job in that file, and fail unless those jobs succeeded. |
| Yes | `pull_request` on `lint.yml`, `test.yml`, and `security.yml` has no path filter. |
| No | `verify-rulesets.yml`, `cdk-diff.yml`, deploy workflows, and the product job ids (`checkov`, `bandit`, `semgrep`, `node-lockfiles`, `validate-agent-harness`, and the rest). |
| No | A `v*` tag. Organization admin can create one through the `release-tags-create` bypass. Update and deletion stay blocked. Callers pin commit SHAs. |

Workflows and jobs:

| File | Jobs |
| --- | --- |
| `lint.yml` | `lint-python` (compile, layout check, Ruff), `workflow-conformance`, gate `lint` |
| `test.yml` | `unit`, one fixture job per action case, gate `test` |
| `security.yml` | `pii-denylist`, `secrets-scan`, `codeql` (languages `python` and `actions`), gate `security-summary` |
| `dependency-submission.yml` | `check`, `submit` |
| `sync-labels.yml` | `sync` |
| `dependabot-batch.yml` | `report` |

`dependency-submission.yml` is named Dependency Submission. `check` runs unless the event is a push to `main`. `submit` runs on a push to `main` and sets `contents: write`. The display name keeps this workflow apart from GitHub's Dependency Graph entry.

`sync-labels.yml` applies `sync-labels/labels.json` to this repository on a push to `main`, every Monday, and `workflow_dispatch`. The catalogue includes `mobile`. The job sets `issues: write`. It is not a required check. `github.token` writes labels on this repository.

`dependabot-batch.yml` reports the five repositories on `workflow_dispatch` and `15 */2 * * 1-5`. The `report` job sets `checks: read` and `pull-requests: read`. It does not write. It is not a required check.

The `lint`, `test`, and `security-summary` gates pin `lx-software-ltd/actions/require-jobs@1a3cca7c38163f8164c262323601c34a4df5b7a4` (`# main 2026-11-20`). They must not use `uses: ./require-jobs`. A local action is loaded from the pull request, so a change that always exits 0 would turn the required check green while the fail fixture goes red. Fixture jobs may use `uses: ./require-jobs` to test the pull request's copy. The layout check rejects a local action on a gate job. The calling job needs `python3` on `PATH`.

`security-summary` aggregates `security.yml`. `main-protection` requires it, with `lint` and `test`. PII and Gitleaks run in `security.yml`.

`scripts/pii-denylist.sha256` holds the 31 organisation digests. The owner approved the copy on 20 Nov 2026. The file has no plaintext. The PII job scans tracked source against them.

CodeQL scans Python and GitHub Actions. The Actions language is the one that covers the workflow files and composite actions in this repository.

## Checked by workflow-conformance

The action checks the pin, runner, permission, image-digest, gate, path-filter, one-commit, `# main YYYY-MM-DD` comment, and pre-commit `rev` rules above. A `pull_request` `paths-ignore` is a path filter. A gate job has `if: always()`, lists every other job in that file under `needs`, and pins `require-jobs` by commit SHA. `security-summary` is that gate in `security.yml`. `lint.yml`, `test.yml`, and `security.yml` must exist, and none of them may filter `pull_request` by path. Top-level permissions are `contents: read`. Container and service images are pinned by digest.

`profile: product` also requires the `security.yml` job ids in the table above, including `semgrep` named `semgrep/ci`, and the `lint.yml` jobs `node-lockfiles` and `python-requirements`. A `check-lockfiles.yml` or `semgrep.yml` file is a finding. `profile: producer` is this repository, which does not have those product job ids. `mode: enforce` exits 1 when there is a finding. `mode: warn` prints findings and exits 0. The default mode is `enforce`.

Three product checks follow `alignment`. The default is `enforce`. `warn` prints `::warning::` and does not fail.

- A workflow does not call `actions/setup-node` or `actions/setup-python`. A quoted `uses` counts.
- When both `cdk-diff` and `cdk-deploy` are used, they name the same `plan-file` or the same inline `plan`. The value runs to the end of the line, or through the block body. A `${{ }}` path is the whole value. A step written as `name:`, then `uses:`, then `with:` is read the same way as one that starts at `uses:`.
- A workflow does not call `describe-stacks`.

`templates` compares each file in `templates/workflows/` with the product workflow of the same name. A bare `# template:if-present` produces no finding when that product file is absent. `# template:if-present <capability>` and `!<capability>` follow the probe in both directions: the file is required when the probe says so, and a finding when the file exists and the probe says it must not. When the file is present, the marker is ignored and the rest must match. The default is `enforce`. A mismatch is a finding when `mode` is `enforce`. `off` skips the comparison. `profile: producer` skips it.

A `# template:set` line opens a block and `# template:end` closes it. The lines between the markers may differ, including how many there are. They hold values: stack names, app directories, requirement files, dated ignores, env lists, path filters, Lighthouse page lists, S3 profiles, Bandit and CodeQL inputs, and gate `needs` lists. A marked block cannot contain a step (`- name:`, `- uses:`, `- run:`, or `- id:`), a bare `run:` or `id:`, a comment, a single-quoted scalar, `continue-on-error:`, `type:`, `options:`, `needs:`, or `if:`. A `with:` or `env:` with no mapping under it is a finding, because an empty value block there is null and GitHub rejects the workflow. The gate still reads the job ids inside the `needs` value block. A step that only some repositories run is a `# template:optional <capability>` block. The id is a name in `templates/capabilities.json` and may repeat in one file. The block count matches the probe: present when the probe matches, absent when it does not. The marker lines stay. A marker counts at any indent, so it can sit inside a YAML block. The blank line that separates an optional block from the next job sits inside the block, so omitting the block does not leave that blank behind. A blank line between two steps that stay when the block is omitted sits after `# template:end`. When the block is present, its unmarked lines match the template. Nested `# template:set` blocks inside it follow the same rule. Product names (`evolvesprouts`, `findingalpha`, `lxsoftware`, `lx-software`, `siutindei`) stay out of unmarked template text. `lx-software-ltd` is the organisation pin, not a product name. The comparison treats every `lx-software-ltd/actions/<name>@<sha> # main YYYY-MM-DD` as the same pin. The pin check above still requires one real SHA and a real date. An `on.*.paths` entry whose literal prefix does not exist is a finding. A workflow with no template must be listed in `templates/untemplated-workflows.txt`.
