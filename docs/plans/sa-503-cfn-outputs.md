# Plan: SA-503 cfn-stack-outputs

**Status**: In progress. This pull request adds the action. findingalpha's deploy workflows are the next pull request, after this commit and the cdk-diff log fix are both on `main`, so that repository moves to one SHA.
**Zone**: yellow

## Goal

Add `cfn-stack-outputs`. It reads named CloudFormation outputs into one `json` step output. findingalpha `deploy-admin-web.yml` is the caller that reads named outputs. The https checks stay in that caller.

## Non-goals

- No workflow in this repository requests `id-token: write` or calls AWS. The pass fixture uses a stub `aws`. The fail fixture fails before `aws`.
- No product workflow is edited here. findingalpha's three deploy workflows are the next pull request, after this commit is on `main`. The missing-package warning in that repository's CDK Diff preparation step does not change the pin and is separate. `manage-api-keys.yml` is not a deploy or promote workflow.
- No deploy is dispatched. After the findingalpha pull request merges, the owner runs the workflow (O7). The other three repositories wait until that run is green.
- No account id in this repository. Tests use `123456789012` only inside a stub error, and assert it is not printed.
- No `v*` tag.

## Files

`cfn-stack-outputs/`, `tests/test_cfn_stack_outputs.py`, the fixture jobs in `.github/workflows/test.yml`, the compile list in `.github/workflows/lint.yml`, and `docs/plans/progress.md`.

## Invariants this change preserves

- Inputs reach the script through `env`. The `run` block does not interpolate `${{`.
- A missing region, stack, or output list does not call `aws`.
- A missing or empty output fails and names the key. It does not print values that were found.
- AWS error text is printed only after 12-digit numbers are replaced.
- A `lx-software-ltd/actions` pin has a `# main YYYY-MM-DD` comment.

## Done when

`python3 -m unittest discover -s tests -v` passes and `python3 scripts/check_action_layout.py` passes. The fixture jobs do not call AWS.

## Rollback

Revert this pull request. No product workflow pins this action yet.
