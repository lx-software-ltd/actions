# Plan: Scaffold actions and require-jobs

**Status**: In progress
**Zone**: yellow

## Goal

This repository can merge a pull request with checks named `lint` and `test`, and it publishes `require-jobs` with tests and two fixtures. `security.yml` runs the PII denylist, Gitleaks, and CodeQL for Python.

## Non-goals

- No `v*` tag. The release-tags ruleset blocks them and no bypass is visible.
- No AWS credentials and no `id-token: write`.
- No product-repository call site in this pull request. That is SA-203, after this commit is on `main`.
- Red gates G1 to G5 stay closed.

## Files

The layout in `docs/plans/progress.md`. The first action is `require-jobs/`.

## Invariants this change preserves

- No secret, account id, or personal data is added. The denylist file holds no digests.
- Third-party actions are pinned by full SHA.
- Gate job ids are `lint` and `test`.

## Done when

`python3 -m unittest discover -s tests -v` passes, and `python3 scripts/check_action_layout.py` passes.

## Rollback

Revert the pull request. Callers do not pin this repository yet.
