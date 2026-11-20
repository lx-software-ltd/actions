# SA-304 — verify-rulesets

**Status**: This pull request
**Zone**: yellow

## Intent

Build `verify-rulesets` so the weekly check expects exactly 0 approving reviews and required checks exactly `lint` and `test`. Pair B fails on Monday 23 Nov 2026 at 09:00 UTC until this action is on those repositories' `main`.

## What this pull request changes

`verify-rulesets/`, its fixtures, `tests/test_verify_rulesets.py`, and two jobs in `.github/workflows/test.yml`.

A review count other than 0 is an error. A required-check list that is not exactly `lint` and `test` is an error. Each expected check must be a job id or a job-level name. Deletion and force-push must be blocked. An active ruleset must protect `refs/tags/v*`. `refs/tags/refs/tags/v*` does not count.

The pass fixture is the live contract. The fail fixture asks for 1 review. Neither fixture calls GitHub.

## What it does not change

Product workflows. This repository's own gates. Organisation rulesets.

## Checks

`python3 -m unittest discover -s tests -v` passes. `python3 scripts/check_action_layout.py` passes. `python3 scripts/check_pii.py` passes.

## Rollback

Revert this pull request. The product copies of the script stay until the rollout.
