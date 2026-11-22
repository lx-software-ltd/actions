# Plan: SA-501 aws-oidc

**Status**: In progress
**Zone**: yellow

## Goal

Add `aws-oidc`. It masks the account id, checks that the account id and region are set, reads the job token's `sub` claim, and assumes `GitHubActionsRole` with a session name. `ready` is true after that check and before the role is assumed. The claim must be the ID form. There is no subject input. The caller passes `secrets.AWS_ACCOUNT_ID` only. The findingalpha pilot re-pins to this pull request's merge commit.

## Non-goals

- No workflow in this repository requests `id-token: write` or calls AWS. The fixture jobs take the skip and reject paths only.
- No deploy or promote edit. That is SA-503.
- No account id in this repository.
- No `v*` tag.

## Files

`aws-oidc/`, `tests/test_aws_oidc.py`, the fixture jobs in `.github/workflows/test.yml`, the compile list in `.github/workflows/lint.yml`, and `docs/plans/progress.md`.

## Invariants this change preserves

- Inputs reach the script through `env`. The `run` block does not interpolate `${{`.
- `aws-actions/configure-aws-credentials` stays pinned at `e1253824e5c10ff9df46874f81ed3ec929e19cfd` with a version comment, and runs only when `ready` is true.
- `required` false and a missing account or region set `ready` to false and exit 0. `required` true fails the step.
- The name-form subject and a `*` pattern fail. Tests use the token claim `repo:lx-software-ltd@321652495/findingalpha@1456774357:pull_request`.
- A `lx-software-ltd/actions` pin has a `# main YYYY-MM-DD` comment.

## Done when

`python3 -m unittest discover -s tests -v` passes and `python3 scripts/check_action_layout.py` passes. The fixture jobs do not assume a role.

## Rollback

Revert this pull request. No product workflow pins the action until the findingalpha pilot.
