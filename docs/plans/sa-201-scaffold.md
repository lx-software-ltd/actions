# Plan: Scaffold the actions repository

**Status**: Merged as pull request #1. Ruleset sentences below were the measurement when this note was written. The current measurement is the preface of `docs/plans/shared-actions-and-ci-convergence.md`.
**Zone**: yellow

## Goal

This pull request is SA-201 only. The repository has the licence, the CI contract, the zone map, the plan copy, and workflows whose gate jobs are named `lint` and `test`. Those gates are inline Python in the workflow file.

## Non-goals

- `require-jobs` is not in this pull request. That is the next pull request, SA-202. Combining them is what would let the first merge load the gate from the pull request checkout.
- No `v*` tag. `release-tags` does not apply to this repository, so a tag can be created and can move. Do not tag until that ruleset applies.
- No AWS credentials and no `id-token: write`.
- No product-repository call site. That is SA-203, and it waits until a commit is on `main` and `main-protection` applies. A force-push can still orphan a SHA.
- Red gates G1 to G5 stay closed.

## Files

`LICENSE`, `README.md`, `AGENTS.md`, `docs/ci-contract.md`, `docs/architecture/zones.md`, `docs/plans/shared-actions-and-ci-convergence.md`, `docs/plans/progress.md`, `.github/workflows/lint.yml`, `.github/workflows/test.yml`, `.github/workflows/security.yml`, `.github/dependabot.yml`, `scripts/check_action_layout.py`, `scripts/check_pii.py`.

## Invariants this change preserves

- No secret, account id, or personal data is added. The denylist file holds no digests, and the PII job checks nothing.
- Third-party actions are pinned by full SHA with a version comment.
- Gate job ids are `lint` and `test`, and they do not use `uses: ./`.
- CodeQL scans Python and GitHub Actions.

## Done when

`python3 -m unittest discover -s tests -v` passes, and `python3 scripts/check_action_layout.py` passes.

## Rollback

Revert the pull request. Callers do not pin this repository yet. Revert is not enough to keep an old SHA reachable: nothing blocks a force-push to `main`.
