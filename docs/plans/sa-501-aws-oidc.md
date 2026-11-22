# Plan: SA-501 aws-oidc

**Status**: In progress
**Zone**: yellow

## Goal

Add `aws-oidc`. It masks the account id, checks that the account id and region are set, and assumes `GitHubActionsRole` with a session name. Output `ready`. A subject, when the caller passes one, must be the ID form `repo:<org>@<org-id>/<repo>@<repo-id>:...`. The findingalpha `cdk-diff.yml` pilot is the next pull request and pins this merge.

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
- The name-form subject `repo:lx-software-ltd/findingalpha:pull_request` fails. Tests use `repo:lx-software-ltd@321652495/findingalpha@1456774357:*`.

## Done when

`python3 -m unittest discover -s tests -v` passes and `python3 scripts/check_action_layout.py` passes. The fixture jobs do not assume a role.

## Rollback

Revert this pull request. No product workflow pins the action until the findingalpha pilot.
