# Plan: Add setup-node and setup-python

**Status**: In progress
**Zone**: yellow

## Goal

Publish `setup-node` with default Node 26 and `setup-python` with default Python 3.12. A caller passes the version that repository uses today. This pull request does not change a product workflow.

## Non-goals

- No C04 or C05 edit in a product repository.
- No `v*` tag. `release-tags` still blocks creation. SA-204 waits until the owner applies the tag-ruleset split.
- No change to the `require-jobs` pin.

## Files

`setup-node/`, `setup-python/`, `fixtures/setup-node/`, `fixtures/setup-node-no-lock/`, `fixtures/setup-python/`, `tests/test_setup_actions.py`, and the pass and fail fixture jobs in `.github/workflows/test.yml`.

## Invariants this change preserves

- Third-party actions stay pinned by full SHA with a version comment.
- The `test` gate stays pinned at `1a3cca7` and lists the new jobs in `needs`.
- `working-directory` and `cache` default empty, so a call site that only selects a Node version does not gain a cache or `npm ci`.
- Callers can override both version defaults.

## Done when

`python3 -m unittest discover -s tests -v` passes, and `python3 scripts/check_action_layout.py` passes. The pass fixtures set up Node 26 with no cache and Python 3.12 with no cache, and also install from the lockfile and the requirements file. The fail fixtures fail: npm cache against a directory with no lockfile, and pip cache against a requirements path that is not there.

## Rollback

Revert this pull request. No caller pins these actions yet.
