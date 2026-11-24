# Close remaining workflow gaps

LX Software · Internal plan · 24 November 2026.

Approved. The finishing pull request deletes this note.

Source report: https://workflow-differences-across-lx-software-urxw.pages.cursorusercontent.com/

Repo shorthand: es = evolvesprouts, fa = findingalpha, lx = lx-software, sd = siutindei.

## 1. Abstract

Conformance is green because every difference was wrapped in a marker, not because the workflows converged. Byte-identical workflows are not reachable while the products differ. The target is that every remaining difference is either a block that exists exactly when a named capability's probe path exists, or a value block that holds only values.

This document is the one-shot plan for an executing agent covering `actions` and the four product repositories. Approving it is the explicit approval the red-zone rules ask for.

## 2. Review of the report

### Accurate

- All four products pin `actions@7274dbb`, which is current `main`, and all four pass conformance.
- The four files it calls identical (`cdk-bootstrap.yml`, `dependency-submission.yml`, `semgrep.yml`, `verify-rulesets.yml`) are byte-identical.
- The eight single-repo workflows and the job tables match.

### Stale or wrong

- `evolvesprouts` has moved to `f78346e`; the only change is the `figma-refresh-token.yml` rename.
- The `PYSEC-2025-183` ignore is in evolvesprouts and siutindei, not evolvesprouts alone.
- The Bandit split is evolvesprouts + siutindei versus findingalpha + lx-software.

### What it misses

| Measure across the 19 templates | Today |
| --- | --- |
| Optional blocks present in some repos and absent in others | 53 of 54 |
| Value blocks whose content differs across repos | 112 of 117 |
| Product names in shared, unmarked template text | 12 |

- Nothing ties a block to a reason. Any repo can delete any optional block and still pass.
- Value blocks hold commands: `run:` bodies, step ids, and comments, not just values.
- Some blocks are one product's job pasted into the template (`promote-direct`, `promote-refresh`, `lighthouse-pull-request`).
- Dead paths: `packages/*` directories that do not exist are listed in siutindei audit and lockfile inputs and in evolvesprouts/siutindei path filters; they are skipped silently.
- `ios-lockfiles` runs on `macos-26` in two repos, but neither has a tracked `Podfile`.
- In findingalpha and lx-software the `diff` job has no environment, so variables that exist only on `production` are empty during diff.
- Stale docs in `actions`: `docs/decisions.md` still says template enforcement is open, and `docs/plans/2026-11-24-workflow-templates.md` still says In progress.

## 3. Target and done criteria

Done means a new `scripts/check_template_drift.py`, run over the four checkouts, reports zero for each of:

- optional blocks not bound to a capability;
- value blocks containing `run:`, `id:`, or comment lines;
- value blocks identical in every repo that has the file;
- product names in unmarked template text.

## 4. Preflight

Confirm these heads. If any moved, re-run the drift measurement before editing.

| Repository | SHA | Note |
| --- | --- | --- |
| actions | 7274dbbda035e283bf0d2a78c98d45deae348344 | origin/main |
| evolvesprouts | f78346e | Moved after the report; only figma-refresh-token.yml renamed. Re-measured at 9ae6ac5: lighthouse gained one env line |
| findingalpha | d7c3223 | Matches the report |
| lx-software | d3c7b02 | Matches the report |
| siutindei | daf7684 | Matches the report. Re-measured at 6f8bc62: untemplated board workflow titles only |

## 5. Checker and contract (`actions`)

Changes go in `workflow-conformance/check_workflows.py`, with one test per rule in `tests/test_workflow_conformance.py`.

- Capabilities. Add templates/capabilities.json mapping capability to probe glob. An optional id must be a capability name and may repeat within a file. Block present without the probe, or probe present without the block, is a finding.
- File presence. # template:if-present <capability> (or !<capability>) makes file presence follow the probe in both directions.
- Value blocks. Also reject run:, id:, comment lines, and single-quoted scalars.
- Product names. evolvesprouts, findingalpha, lxsoftware, lx-software, and siutindei may not appear in unmarked template text.
- Untemplated files. A workflow file with no template must be listed in templates/untemplated-workflows.txt.
- Path filters. An on.*.paths entry whose literal prefix does not exist is a finding.
- Missing directories. node-lockfiles/check.sh and npm-audit/run.sh fail on a listed directory with no package.json instead of skipping.

Untemplated files to allow-list:

| Repository | Files |
| --- | --- |
| evolvesprouts | deploy-training.yml, figma-refresh-token.yml, figma-token-studio-sync.yml |
| findingalpha | none |
| lx-software | mint-openrouter-keys.yml |
| siutindei | board-agent.yml, board-merge-staging.yml, board-promote.yml, close-note-tag-issues.yml (names stay: lx-software dispatches them by filename) |

- Update fixtures to match the new templates.
- Update docs/ci-contract.md: marker rules, capability table, Differences that stay.
- Update docs/decisions.md: record the capability rule and the two-job diff, and strike the stale template line.
- Delete docs/plans/2026-11-24-workflow-templates.md.
- Add this plan as docs/plans/<date>-close-workflow-gaps.md. The finishing pull request deletes it.

## 6. Capabilities

| Capability | Probe | Repos today |
| --- | --- | --- |
| mobile | `apps/*/pubspec.yaml` | es, sd |
| ios-pods | `apps/*/ios/Podfile` | none today |
| openapi | `docs/api/*.yaml` | es, sd |
| database | `backend/db` | es, sd |
| training | `apps/training/package.json` | es |
| search-fixture | `scripts/codegen/sync-activity-search-staging-fixture.sh` | sd |
| playwright-admin | `apps/admin_web/playwright.config.*` | fa, lx, sd |
| playwright-public | `apps/public_www/playwright.config.*` | es, sd |
| next-admin | `apps/admin_web/next.config.*` | es, sd |
| next-public | `apps/public_www/next.config.*` | es, sd |
| public-build-env | `scripts/deploy/resolve-public-www-build-env.sh` | es, sd |
| admin-stack-settings | `scripts/deploy/check-admin-spa-settings.sh` | fa, lx |
| amplify | `scripts/deploy/build_amplify_config.py` | sd |
| catalogue | `scripts/deploy/fetch-public-www-catalogue-snapshot.sh` | sd |
| indexnow | `scripts/deploy/indexnow.py` | sd |
| edge-verify | `scripts/deploy/report_public_www_edge_verify.sh` | es |
| staged-release | `scripts/deploy/deploy-public-www.sh` | es, sd |
| public-api-keys | `scripts/deploy/create-api-key.sh` | fa, lx |

File-level bindings:

| Files | Capability |
| --- | --- |
| deploy-ios.yml, deploy-mobile.yml | mobile |
| deploy-public-www-staging.yml, smoke-public-www-staging.yml, promote-public-www.yml | staged-release |
| deploy-public-www.yml | !staged-release |
| manage-api-keys.yml | public-api-keys |

## 7. Optional blocks

| Template | Block | Change |
| --- | --- | --- |
| cdk-diff | production-diff, pull-request-diff | Unmark. All four get two jobs: diff (main, not a pull request, environment: production) and pull-request (read-only role). |
| cdk-diff | diff-role-guard, diff-role, diff-note | Delete from diff, which uses GitHubActionsRole directly. Guard and note stay in pull-request, unmarked. |
| cdk-diff, deploy-backend | waf-region | Delete. Add a universal step `bash scripts/deploy/cdk-prepare.sh region` with `id: region`. Every `region:` input reads that output. |
| cdk-diff, deploy-backend | qemu | Unmark. The step runs in all four repositories. |
| cdk-diff, deploy-backend, lint, security, test | search-fixture, e2e-search-fixture | Bind to search-fixture. `lfs: true` checkouts become a separate Pull Git LFS objects step inside the block. |
| deploy-backend | edge-verify, edge-verify-report | Bind to edge-verify. Condition becomes `steps.prep.outputs.edge_verify == 'true'`. Stack name moves to a value. |
| check-lockfiles | flutter-lockfiles | Bind to mobile. |
| check-lockfiles | ios-lockfiles | Bind to ios-pods. The job leaves es and sd, because neither has a tracked Podfile. |
| deploy-admin-web | workflow-run, admin-settings | Bind to admin-stack-settings. |
| deploy-admin-web | next-cache | Bind to next-admin. |
| deploy-ios, deploy-mobile | oidc, amplify | Bind both to amplify. |
| deploy-public-www-staging | staging-prep, landing-calendar | Delete. Add universal steps `bash scripts/deploy/public-www-checks.sh pre-build` and `post-build`. Fixture sync stays as a search-fixture block. |
| deploy-public-www-staging | catalogue-check | Bind to catalogue. |
| deploy-public-www-staging | optimize-images | Unmark. |
| deploy-public-www-staging | function-switch, staging-invalidate | Merge into one unmarked step, Finish the staging release. They already run the same script; only the stack name differs, and that becomes a value. |
| lighthouse-public-www | production-environment, lighthouse-pull-request | Delete. lx uses the single job the other three use. |
| lighthouse-public-www | public-origin | Bind to public-build-env. |
| lighthouse-public-www | next-cache | Bind to next-public. |
| lint | hook-deps | Unmark. The step runs `bash scripts/ci/hook-deps.sh`. |
| lint | training, mobile, openapi | Bind to the same-named capabilities. |
| promote-public-www | nightly-promote, catalogue-check | Bind to catalogue, including pack, upload, and download of promotion inputs, which never run in es. |
| promote-public-www | promote-direct, promote-refresh | Merge into one promote job: checkout, set up Node, pre-build checks, build, post-build checks, IndexNow key (indexnow), AWS credentials, promote, record live build (catalogue), notify (indexnow), summary. prepare outputs deploy, maintenance_mode, skip, build_sha, and release_id in both repos. |
| test | database, training, mobile, playwright-admin, playwright-public | Bind to the same-named capabilities. |
| test | coverage-upload | Unmark with `if-no-files-found: ignore`. Uploads nothing in fa and lx, whose tests write no coverage.xml. |
| test | public-origin | Replace the es inline resolver with the public-build-env block. |
| test | admin-e2e-build | Delete. sd adds `pretest:e2e: npm run build` to `apps/admin_web/package.json`. |
| test | admin-e2e-report | Unmark inside playwright-admin. fa and lx gain the report upload. |
| test | sqlite | Delete. The install moves into `scripts/ci/test-flutter.sh`. |

## 8. Value blocks

- Keep only values: stack names, app directories, requirement files, dated ignores, env lists of secrets and variables, path filters, Lighthouse page lists, S3 profiles, Bandit and CodeQL inputs, and gate needs lists.
- `id: aws` and `resolve_public_site_config` become unmarked and the same everywhere.
- `fetch-depth: 0` is unmarked in lint-python and test-python.
- The Next.js cache uses one key format.
- Loops over app directories become `apps/*/pubspec.yaml` globs or `scripts/ci/test-flutter.sh`.
- OpenAPI lint uses `docs/api/*.yaml`.
- Choose promotion mode moves into `resolve-release-id.sh`.
- The release build moves to `scripts/deploy/build-mobile-release.sh <ipa|appbundle>`. The Amplify key is passed through env, not inline in `run`.
- Staging and smoke summaries move to `scripts/deploy/publish-staging-summary.sh`.
- `deploy-backend` `cdk_stacks` becomes `type: choice` in all four, with options as values.
- The 12 product names in shared text move into value blocks or disappear with the merged blocks.
- Single quotes become double quotes. Comments leave value blocks.

## 9. Product repositories

Each product gets one pull request containing the pin bump (`scripts/bump_pins.py`), the regenerated workflow text, and the script changes below.

| Repo | Script and file changes |
| --- | --- |
| All four | New `scripts/ci/hook-deps.sh` holding today's inline commands. `scripts/deploy/cdk-prepare.sh` gains the `region` subcommand. Remove path-filter entries that point at nothing. |
| evolvesprouts | `cdk-prepare.sh deploy` writes `edge_verify`. New `public-www-checks.sh` (post-build runs the calendar validation), `test-flutter.sh`, `build-mobile-release.sh`, `publish-staging-summary.sh`. `resolve-release-id.sh` writes `deploy`, `skip`, and `build_sha` and takes over the mode choice. Remove the ios-lockfiles job. |
| siutindei | `cdk-prepare.sh region` holds the current WAF region logic. `deploy-public-www.sh` accepts `PUBLIC_WWW_PHASE=optimize` as a no-op. `public-www-checks.sh` pre-build runs the wizard check, scope validation, and env contract. Same new scripts as evolvesprouts; `test-flutter.sh` installs SQLite. Add `pretest:e2e`. Remove `packages/*` from audit and lockfile inputs. Remove the ios-lockfiles job. |
| findingalpha, lx-software | diff gains `environment: production`. `cdk_stacks` becomes a choice. The admin e2e job gains the report upload. lx-software Lighthouse drops the production environment and the separate pull-request job. |

## 10. Rollout, verification, rollback

1. Open the `actions` pull request. Tests, `lint`, `test`, and `security-summary` must be green; then merge.
2. Open one pull request per product against the merged SHA. For each: `CONFORMANCE_ROOT=<repo> python3 workflow-conformance/check_workflows.py` passes; the step list per job, before and after, shows no command lost except the changes named above; all three gates are green.
3. Run the drift script over the four merged heads; all four counts must be zero.
4. Open a last `actions` pull request that deletes the plan note.

Rollback is reverting the product pull request, which restores the old pin and the old text together.

## 11. What stays different

These are not workflow text, so they stay declared in `docs/ci-contract.md`:

- staged versus direct public release;
- parameter source (`CDK_PARAM_*` versus `P_*`);
- admin build settings from stack outputs versus repository variables;
- per-product secret names.

The other open items in the Not finished list in `docs/decisions.md` are the same in all four repos, so they are not divergences and this plan leaves them alone. `AWS_DIFF_ROLE_NAME` is one of them: it is unset as a repository variable everywhere, so pull-request diffs run nowhere today. Org-level variables could not be read.

## 12. Decisions you may reverse

- **Two-job diff everywhere.** es, fa, and lx lose manual diffs from non-main branches, because `production` only allows `main`. In return, diff and deploy see the same variables.
- **QEMU everywhere.** This adds a QEMU setup step to es and sd diff and deploy that they do not need. The alternative is a marker file as the probe for an `arm64-bundling` capability.
- **`cdk_stacks` as a choice.** fa and lx lose free-text entry.
- **The promote merge is the riskiest change.** It rewrites both production promotion jobs and has no dry run, so the first promotion in each repo should be watched.

Unrelated, worth checking: siutindei has a repository variable named `FIREBASE_ANDROID_ID_APP`, while its workflows read `vars.FIREBASE_ANDROID_APP_ID`.

## 13. Red-zone files

Most of each product pull request is red-zone. Approving this plan is the explicit approval the zone rules ask for. Quote this document in each pull request.

| Repository | Red-zone files touched |
| --- | --- |
| All four products | every deploy-*.yml |
| siutindei | also promote-*.yml, board-*.yml, verify-rulesets.yml, scripts/deploy/**, scripts/ci/**, .pre-commit-config.yaml, backend/infrastructure/** |
| lx-software | also manage-api-keys.yml, mint-openrouter-keys.yml, verify-rulesets.yml |
| evolvesprouts | also verify-rulesets.yml |
