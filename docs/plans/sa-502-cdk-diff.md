# Plan: SA-502 cdk-bootstrap-check and cdk-diff

**Status**: Merged in actions #32. The findingalpha pilot is #84. The other three are not updated.
**Zone**: yellow

## Goal

Add `cdk-bootstrap-check` and `cdk-diff`. The check reads the bootstrap version from SSM and fails with a hint when it is missing. It does not run `cdk bootstrap`. The diff runs `cdk diff`, strips the account id from the log and the step summary, and keeps the diff's exit code.

The findingalpha pilot is merged at `24d9267` and pins `12ce754`. The other three keep their current triggers and are not updated. Callers that do not write a summary pass `summary: "false"`. Callers that do not name stacks pass an empty `stacks` list.

## Non-goals

- No workflow in this repository requests `id-token: write` or calls AWS. The pass fixtures use a stub `aws` and a stub `cdk`. The fail fixtures fail before either command.
- No deploy or promote edit. `aws-oidc` in those workflows is SA-503. Removing `cdk bootstrap` from pair B deploys is C24.
- No pull-request trigger added to a repository whose CDK Diff is manual. That is C25.
- No account id in this repository. Tests use `000000000000`.
- No `v*` tag.

## Files

`cdk-bootstrap-check/`, `cdk-diff/`, `tests/test_cdk_bootstrap_check.py`, `tests/test_cdk_diff.py`, the fixture jobs in `.github/workflows/test.yml`, the compile list in `.github/workflows/lint.yml`, and `docs/plans/progress.md`.

## Invariants this change preserves

- Inputs reach the script through `env`. The `run` block does not interpolate `${{`.
- A missing region does not call `aws`. A failed SSM read names the parameter and does not print an account id.
- An empty stack list passes no stack names. `args-file` is a null-delimited list and wins over `args`.
- `summary: "false"` writes no step summary. The diff's exit code is the step's exit code.
- The account id is removed from the log and the summary. An empty account id leaves the text unchanged and is not printed.
- A `lx-software-ltd/actions` pin has a `# main YYYY-MM-DD` comment.

## Done when

`python3 -m unittest discover -s tests -v` passes and `python3 scripts/check_action_layout.py` passes. The fixture jobs do not call AWS.

## Rollback

Revert this pull request. No product workflow pins these actions until the findingalpha pilot.
