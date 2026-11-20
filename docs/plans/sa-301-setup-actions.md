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

`setup-node/`, `setup-python/`, `fixtures/setup-node/`, `fixtures/setup-python/`, `tests/test_setup_actions.py`, and the two fixture jobs in `.github/workflows/test.yml`.

## Invariants this change preserves

- Third-party actions stay pinned by full SHA with a version comment.
- The `test` gate stays pinned at `1a3cca7` and lists the new jobs in `needs`.
- Callers can override both defaults.

## Done when

`python3 -m unittest discover -s tests -v` passes, and `python3 scripts/check_action_layout.py` passes. The fixture jobs install Node at the default and Python at the default.

## Rollback

Revert this pull request. No caller pins these actions yet.
