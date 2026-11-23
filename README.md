# actions

Shared composite actions and pre-commit hooks for the `lx-software-ltd` product repositories.

An action cannot read `secrets` or `vars`. Callers pass those as inputs. Payload is `"$GITHUB_ACTION_PATH/..."`. Shared payload is `"$GITHUB_ACTION_PATH/../lib/..."`. An action does not call another action in this repository.

Decisions that still bind are `docs/decisions.md`. The CI contract is `docs/ci-contract.md`. The zone map is `docs/architecture/zones.md`.

## Pin a commit

```yaml
uses: lx-software-ltd/actions/require-jobs@<40-hex> # main <yyyy-mm-dd>
```

Pin a commit that is on `main`. `main-protection` blocks a force-push, so that commit stays reachable. One product repository uses one SHA. The pre-commit `rev` for this repository is that same SHA. Conformance fails when they differ.

`release-tags` blocks update and deletion of `v*` tags. `release-tags-create` blocks creation. Callers pin the commit SHA.

## Move a pin

From a product checkout:

```sh
python3 /path/to/actions/scripts/bump_pins.py . <40-hex> --date <yyyy-mm-dd>
```

The script rewrites every `lx-software-ltd/actions` pin, the `# main YYYY-MM-DD` comment, and the pre-commit `rev`. Review the diff and open one pull request. The SHA has to be on `main` before that pull request merges.

## Add an action

1. Add `<name>/action.yml` (`runs.using: composite`) and `<name>/README.md`.
2. Add a passing fixture and a failing fixture under `fixtures/<name>/`.
3. Add a passing job and a failing job to `.github/workflows/test.yml`, and list both in the `test` gate `needs`. Conformance fails when a job is missing from that list.
4. Run the three checks below.

## Checks

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```

Python payload uses the standard library and runs on Python 3.12.

## Catalogue

| Action | Purpose | Callers |
| --- | --- | --- |
| `require-jobs` | Fail unless every job in `needs` succeeded. | All four product repositories, and the gates in this repository. |
| `workflow-conformance` | Check workflows against `docs/ci-contract.md`. | All four, and `lint.yml` here. |
| `verify-rulesets` | Fail unless `main-protection` requires the three gates and zero reviews, and the tag rulesets block `v*`. | All four, weekly. |
| `agent-harness` | Check agent rules, file length, and test focus from `.github/harness.json`. | All four. |
| `pii-denylist` | Fail when tracked source matches a SHA-256 denylist. The match text is not printed. | All four, and `security.yml` here. |
| `gitleaks` | Secret scan with the gitleaks CLI. | All four, and `security.yml` here. |
| `checkov-cloudformation` | Checkov on synthesised CloudFormation, then a SARIF upload. | All four. |
| `codeql` | CodeQL init and analyze. | All four, and `security.yml` here. |
| `semgrep` | `semgrep scan`, then a SARIF upload. | All four. |
| `bandit` | Bandit on the caller's paths. | All four. |
| `pip-audit` | `pip-audit` on requirements files. | All four. |
| `dependency-graph` | Submit pinned requirements, npm lockfiles, and pinned actions uses to the dependency graph. | This repository and all four product repositories. |
| `npm-audit` | `npm audit` at the caller's level. | All four. |
| `setup-node` | Node 26, and `npm ci` when a working directory is set. | All four. |
| `setup-python` | Python 3.12, and a pip cache when a requirements file is set. | All four. |
| `node-lockfiles` | Fail when `package-lock.json` is out of date. | All four. |
| `python-requirements-pins` | Fail when a requirements file is unpinned. | All four. |
| `flutter-lockfiles` | Fail when `pubspec.lock` is out of date. | `evolvesprouts`, `siutindei`. |
| `setup-flutter` | Install Flutter 3.50.1. | No caller yet. Adopt after this commit is on main. |
| `pod-lockfiles` | Fail when `Podfile.lock` changes after `pod install`. | `evolvesprouts`, `siutindei`. |
| `playwright-install` | Install Playwright browsers. | The repositories that run browser tests. |
| `aws-oidc` | Check the account id and region the caller passed, and mask the account id. | All four. |
| `cdk-bootstrap-check` | Read the CDK bootstrap version from SSM. It does not bootstrap. | All four, on diff. |
| `cdk-diff` | Run `cdk diff` and write the summary. | All four. |
| `cdk-deploy` | Deploy the stacks in a plan JSON from a parameters file. | All four, on backend deploy. |
| `cfn-stack-outputs` | Read named CloudFormation outputs. | The repositories that read stack outputs. |
| `s3-cloudfront-deploy` | Sync a build to S3 and invalidate CloudFront. | All four, on web deploy. |
| `ios-export-options` | Write `ExportOptions.plist`. | `evolvesprouts` and `siutindei`, in `deploy-ios.yml`. |
| `appstore-api-key` | Load the App Store Connect API key into the environment. | `evolvesprouts` and `siutindei`, in `deploy-ios.yml`. |
| `android-signing` | Install the upload keystore. | `evolvesprouts` and `siutindei`, in `deploy-mobile.yml`. |
| `play-prerequisites` | Skip the Play upload when a signing or track secret is missing. | `evolvesprouts`, in `deploy-mobile.yml`. siutindei Play stays inline. |
| `lighthouse-ci` | Run Lighthouse against the caller's page list. The bypass header is not left in the workspace. | No caller yet. Adopt after this commit is on main. |
