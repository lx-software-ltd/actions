# Plan: Pin the merge gates at the main SHA

**Status**: Merged as pull request #4 (`b1d436a`). This is not an open pull request. Ruleset sentences below were the measurement when this note was written. The current measurement is the preface of `docs/plans/shared-actions-and-ci-convergence.md`.
**Zone**: yellow

## Goal

Record the merge SHA of #2 and point `lint`, `test`, and `security-summary` at `lx-software-ltd/actions/require-jobs` at that commit. A later pull request that edits `require_jobs.py` no longer supplies the code for those checks.

## Non-goals

- No `v*` tag.
- No product-repository call site. `main-protection` still does not apply, so a force-push can orphan the SHA. Product callers wait for owner task O8.
- Fixture jobs keep `uses: ./require-jobs`.

## Files

`.github/workflows/lint.yml`, `.github/workflows/test.yml`, `.github/workflows/security.yml`, `docs/plans/progress.md`, `docs/ci-contract.md`, `require-jobs/README.md`.

## Invariants this change preserves

- The pin is `1a3cca7c38163f8164c262323601c34a4df5b7a4`, which is on `main` and has the same tree as `e9c01fe`.
- The layout check still rejects `uses: ./` on a gate job.
- The calling job needs `python3` on `PATH`. These jobs use `ubuntu-26.04`, which provides it.

## Done when

`python3 -m unittest discover -s tests -v` passes, and `python3 scripts/check_action_layout.py` passes.

## Rollback

Revert this pull request. The gates return to the inline step. The recorded SHA in `progress.md` stays, because the merge itself is not reverted.
