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

## Evidence

The fixture jobs ran on this pull request. Bandit, npm audit, and pip-audit passed and failed as required. `pip-audit` could not be smoked on the agent machine because it has no `python3-venv`.

Playwright 1.49.1's Chromium download on `ubuntu-26.04` reached 100% and then did not exit. The fallback command had no timeout, so the pass job sat from 15:14 to 21:14 and was cancelled, and the `test` gate failed. Both attempts are now limited to 180 seconds and the process is killed if it ignores the first signal. The pass job stubs `npx` so it checks the success exit without that download. The fail job still uses the real CLI. The shell tests cover the apt fallback.

## Out of scope

Part B. G3, G4, and G5 stay closed. No deploy, bootstrap, or key-management workflow is triggered.
