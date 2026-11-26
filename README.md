# Actions

Shared composite actions and pre-commit hooks for the `lx-software-ltd` product repositories.

The four product repositories (`evolvesprouts`, `findingalpha`, `lx-software`, and `siutindei`) follow one CI contract: the same gates, scanners, and deploy steps, and the same rules for pins and permissions. This repository is where that contract is written and where it is implemented once. A check or a deploy step is fixed here, tested here against fixtures, and then pinned by commit in each product.

It is not a product and it deploys nothing. No workflow here calls AWS.

This repository is public. Nothing private goes in it: no secret, account id, internal hostname, or personal data.

## What is here

| Path | What it is |
| --- | --- |
| `<name>/` | One composite action: `action.yml`, its payload, and a `README.md`. The [catalogue](#catalogue) lists them. |
| [`lib/`](lib/) | Payload that more than one action shares. |
| [`hooks/`](hooks/) and [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) | The pre-commit hooks the product repositories run. |
| [`fixtures/`](fixtures/) | Passing and failing input for the action tests. |
| [`scripts/`](scripts/) | The layout check, the personal-data check, and the pin bump. |
| [`tests/`](tests/) | Unit tests for the payload and the scripts. |
| [`docs/`](docs/) | The CI contract, the API contract, the decisions that still bind, the zone map, and the architecture notes. |

## Working here

Read [`AGENTS.md`](AGENTS.md) before changing anything. The zone map, [`docs/architecture/zones.md`](docs/architecture/zones.md), says which paths need a plan or an approval first.

Payload is `"$GITHUB_ACTION_PATH/..."`. Shared payload is `"$GITHUB_ACTION_PATH/../lib/..."`. An action does not call another action in this repository.

### Add an action

1. Add `<name>/action.yml` (`runs.using: composite`) and `<name>/README.md`.
2. Add a passing fixture and a failing fixture under `fixtures/<name>/`.
3. Add a passing job and a failing job to [`.github/workflows/test.yml`](.github/workflows/test.yml), and list both in the `test` gate `needs`. Conformance fails when a job is missing from that list.
4. Run the three checks below.

### Checks

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```

Python payload uses the standard library and runs on Python 3.12.

## Use an action

An action cannot read `secrets` or `vars`. Callers pass those as inputs.

### Pin a commit

```yaml
uses: lx-software-ltd/actions/require-jobs@<40-hex> # main <yyyy-mm-dd>
```

Pin a commit that is on `main`. `main-protection` blocks a force-push, so that commit stays reachable. One product repository uses one SHA. The pre-commit `rev` for this repository is that same SHA. Conformance fails when they differ.

`release-tags` blocks update and deletion of `v*` tags. `release-tags-create` blocks creation. Callers pin the commit SHA.

### Move a pin

From a product checkout:

```sh
python3 /path/to/actions/scripts/bump_pins.py . <40-hex> --date <yyyy-mm-dd>
```

The script rewrites every `lx-software-ltd/actions` pin, the `# main YYYY-MM-DD` comment, and the pre-commit `rev`. Review the diff and open one pull request. The SHA has to be on `main` before that pull request merges. The script is [`scripts/bump_pins.py`](scripts/bump_pins.py).

## Catalogue

A green check means a workflow in that repository calls the action. Fixture jobs in `test.yml` here are not callers.

Product repositories call [`dependency-submission`](dependency-submission/README.md) by that directory name. Commits through `48ffe6dadb6c1540b8992e8e8edfda4f8aa0933e` keep the old directory name `dependency-graph`.

| Action | Purpose | actions | findingalpha | lx-software | evolvesprouts | siutindei |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| [`require-jobs`](require-jobs/README.md) | Fail unless every job in `needs` succeeded. | ✅ | ✅ | ✅ | ✅ | ✅ |
| [`workflow-conformance`](workflow-conformance/README.md) | Check workflows against [`docs/ci-contract.md`](docs/ci-contract.md). | ✅ | ✅ | ✅ | ✅ | ✅ |
| [`verify-rulesets`](verify-rulesets/README.md) | Fail unless `main-protection` requires the three gates and zero reviews, and the tag rulesets block `v*`. | | ✅ | ✅ | ✅ | ✅ |
| [`sync-labels`](sync-labels/README.md) | Create and update the shared issue labels, including `mobile`. Other labels stay. | ✅ | | | | |
| [`agent-harness`](agent-harness/README.md) | Check agent rules, file length, and test focus from `.github/harness.json`. | | ✅ | ✅ | ✅ | ✅ |
| [`pii-denylist`](pii-denylist/README.md) | Fail when tracked source matches a SHA-256 denylist. The match text is not printed. | ✅ | ✅ | ✅ | ✅ | ✅ |
| [`gitleaks`](gitleaks/README.md) | Secret scan with the gitleaks CLI. | ✅ | ✅ | ✅ | ✅ | ✅ |
| [`checkov-cloudformation`](checkov-cloudformation/README.md) | Checkov on synthesised CloudFormation, then a SARIF upload. | | ✅ | ✅ | ✅ | ✅ |
| [`codeql`](codeql/README.md) | CodeQL init and analyze. | ✅ | ✅ | ✅ | ✅ | ✅ |
| [`semgrep`](semgrep/README.md) | `semgrep scan`, then a SARIF upload. | | ✅ | ✅ | ✅ | ✅ |
| [`bandit`](bandit/README.md) | Bandit on the caller's paths. | | ✅ | ✅ | ✅ | ✅ |
| [`pip-audit`](pip-audit/README.md) | `pip-audit` on requirements files. | | ✅ | ✅ | ✅ | ✅ |
| [`dependency-submission`](dependency-submission/README.md) | Submit pinned requirements and npm lockfiles. Check workflow uses without submitting them. | ✅ | ✅ | ✅ | ✅ | ✅ |
| [`npm-audit`](npm-audit/README.md) | `npm audit` at the caller's level. | | ✅ | ✅ | ✅ | ✅ |
| [`setup-node`](setup-node/README.md) | Node 26, and `npm ci --no-audit --no-fund` when a working directory is set. | | ✅ | ✅ | ✅ | ✅ |
| [`setup-python`](setup-python/README.md) | Python 3.12, and a pip cache when a requirements file is set. | | ✅ | ✅ | ✅ | ✅ |
| [`node-lockfiles`](node-lockfiles/README.md) | Fail when `package-lock.json` is out of date. | | ✅ | ✅ | ✅ | ✅ |
| [`python-requirements-pins`](python-requirements-pins/README.md) | Fail when a requirements file is unpinned. | | ✅ | ✅ | ✅ | ✅ |
| [`flutter-lockfiles`](flutter-lockfiles/README.md) | Fail when `pubspec.lock` is out of date. | | | | ✅ | ✅ |
| [`setup-flutter`](setup-flutter/README.md) | Install Flutter 3.50.1. | | | | ✅ | ✅ |
| [`pod-lockfiles`](pod-lockfiles/README.md) | Fail when `Podfile.lock` changes after `pod install`. | | | | ✅ | ✅ |
| [`playwright-install`](playwright-install/README.md) | Install Playwright browsers. | | ✅ | ✅ | ✅ | ✅ |
| [`aws-oidc`](aws-oidc/README.md) | Check the account id and region the caller passed, and mask the account id. | | ✅ | ✅ | ✅ | ✅ |
| [`cdk-bootstrap-check`](cdk-bootstrap-check/README.md) | Read the CDK bootstrap version from SSM. It does not bootstrap. | | ✅ | ✅ | ✅ | ✅ |
| [`cdk-bootstrap`](cdk-bootstrap/README.md) | Run `cdk bootstrap` for the account and region the caller passes. | | ✅ | ✅ | ✅ | ✅ |
| [`cdk-diff`](cdk-diff/README.md) | Run `cdk diff` and write the summary. | | ✅ | ✅ | ✅ | ✅ |
| [`cdk-deploy`](cdk-deploy/README.md) | Deploy the stacks in a plan JSON from a parameters file. | | ✅ | ✅ | ✅ | ✅ |
| [`cfn-stack-outputs`](cfn-stack-outputs/README.md) | Read named CloudFormation outputs. | | ✅ | ✅ | ✅ | ✅ |
| [`s3-cloudfront-deploy`](s3-cloudfront-deploy/README.md) | Sync a build to S3 and invalidate CloudFront. | | ✅ | ✅ | ✅ | ✅ |
| [`ios-export-options`](ios-export-options/README.md) | Write `ExportOptions.plist`. | | | | ✅ | ✅ |
| [`appstore-api-key`](appstore-api-key/README.md) | Load the App Store Connect API key into the environment. | | | | ✅ | ✅ |
| [`android-signing`](android-signing/README.md) | Install the upload keystore. | | | | ✅ | ✅ |
| [`play-prerequisites`](play-prerequisites/README.md) | Skip the Play upload when a signing or track secret is missing. | | | | ✅ | ✅ |
| [`lighthouse-ci`](lighthouse-ci/README.md) | Run Lighthouse against the caller's page list. The bypass header is not left in the workspace. | | ✅ | ✅ | ✅ | ✅ |

## Documentation

- [`docs/ci-contract.md`](docs/ci-contract.md): the CI contract that `workflow-conformance` checks.
- [`docs/api-contract.md`](docs/api-contract.md): the API shape the four product repositories serve.
- [`docs/decisions.md`](docs/decisions.md): the decisions that still bind.
- [`docs/architecture/zones.md`](docs/architecture/zones.md): the zone map.
- [`docs/architecture/cdk-deploy.md`](docs/architecture/cdk-deploy.md): the design of `cdk-deploy` and the plan JSON.
- [`docs/architecture/public-site-release.md`](docs/architecture/public-site-release.md): the design of the public-site release in `evolvesprouts` and `siutindei`.
- Each action directory has its own `README.md`, linked from the [catalogue](#catalogue).

## Security

To report a vulnerability, follow [`SECURITY.md`](SECURITY.md). Do not open a public issue.

## Licence

Licensed under the Apache License, Version 2.0. The full text is in [`LICENSE`](LICENSE).
