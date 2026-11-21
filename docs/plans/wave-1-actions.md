# Wave 1 actions

Yellow. One pull request on `actions`. One commit per step. Product repositories pin the merge commit of this pull request after it is on `main`.

## Steps

1. Semgrep `mode` is `scan` (default) or `ci`.
2. An empty Checkov `framework` is omitted. The SARIF is written under `runner.temp`.
3. `flutter-version` is required and the action fails when it is empty.
4. SA-308: `pip-audit`, `bandit`, `npm-audit`, `playwright-install`. Each has a passing fixture and a must-fail fixture.
5. SA-307: `.pre-commit-hooks.yaml` with `check-pii`, `validate-agent-rules`, `check-file-length`, and `check-test-focus`. Each hook finds the repository root from the working directory and reads `.github/harness.json`.
6. SA-309: `workflow-conformance` with `warn` and `enforce`. This repository runs `enforce`.
7. `docs/ci-contract.md` is the target workflow shape. The short replacement was restored.
8. `docs/plans/progress.md` records the harness evidence and that Part B is deferred.

## Evidence still open

The fixture jobs run in this pull request's checks. A local Bandit and npm-audit smoke passed. `pip-audit` could not be smoked here because this machine has no `python3-venv`. The action was not changed to skip that.

## Out of scope

Part B. G3, G4, and G5 stay closed. No deploy, bootstrap, or key-management workflow is triggered.
