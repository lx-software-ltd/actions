# Plan: Restore the hand-off plan

**Status**: In progress
**Zone**: yellow

## Goal

Put the original hand-off plan back under `docs/plans/`, with its register rows, catalog, stages, rollout steps, and invariants. Record the measurements that override a sentence, including O8 and the `check_pii.py` difference, without giving an old step id a new meaning.

## Non-goals

- No new action and no product-repository edit.
- No change to `scripts/check_pii.py`. SA-302 chooses the source later.

## Files

`docs/plans/shared-actions-and-ci-convergence.md`, `docs/plans/progress.md`, the CI contract, the READMEs, and the three workflow comments that still said the ruleset was absent.

## Done when

The original plan text is embedded unchanged, C01 through C28 are present, and `python3 scripts/check_action_layout.py` passes.

## Rollback

Revert this pull request. The shortened plan comes back.
