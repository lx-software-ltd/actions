# Plan: Add require-jobs

**Status**: Merged as pull request #2. Ruleset sentences below were the measurement when this note was written. The current measurement is the preface of `docs/plans/shared-actions-and-ci-convergence.md`.
**Zone**: yellow

## Goal

Publish `require-jobs` with unit tests and two fixtures. The pass fixture calls the action and succeeds. The fail fixture calls it with `continue-on-error` and checks that the step outcome is `failure`. The `test` gate lists both fixture jobs, and the gate itself stays the inline step from SA-201.

## Non-goals

- Do not change the `lint`, `test`, or `security-summary` gates to `uses: ./require-jobs`. That loads the pull request's copy of the action. The follow-up, after this commit is on `main`, pins `lx-software-ltd/actions/require-jobs` at that SHA and records the SHA in `docs/plans/progress.md`.
- No `v*` tag. `release-tags` does not apply, so a tag can move.
- No product-repository call site. That is SA-203, and it waits until the pin is a commit on `main` and `main-protection` applies (owner task O8).

## Files

`require-jobs/`, `fixtures/require-jobs/`, `tests/test_require_jobs.py`, the fixture jobs in `.github/workflows/test.yml`.

## Invariants this change preserves

- The required checks are still decided by the inline gates, not by the action under test.
- The action reads no secret and calls no API. The caller needs `python3` on `PATH`.
- No personal data, account id, or hostname is added.

## Done when

`python3 -m unittest discover -s tests -v` passes, and `python3 scripts/check_action_layout.py` passes. The layout check accepts the fixture jobs and rejects a local action on a gate.

## Rollback

Revert this pull request. The scaffold's inline gates keep working. Callers do not pin this action yet, and a force-push can still orphan a SHA until owner task O8 is done.
