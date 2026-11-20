# Plan: Copy the organisation PII denylist

**Status**: In progress
**Zone**: red

The owner approved this write in chat on 20 Nov 2026. The file is red on `docs/architecture/zones.md`. The approval was for this file only.

## Goal

`scripts/pii-denylist.sha256` holds the 31 digests shared by `evolvesprouts` and `siutindei`, and nothing else. The check then scans this repository for real.

## Non-goals

- No plaintext, and no new digest invented here.
- No change to `scripts/check_pii.py`.
- No product-repository edit. `findingalpha` is its own pull request.
- `lx-software` is missing one of the 31. This pull request does not add it there.

## Files

- `scripts/pii-denylist.sha256`
- The sentences in `AGENTS.md`, `docs/ci-contract.md`, and `docs/plans/progress.md` that said the file was empty

## Invariants this change preserves

- The file contains digests and comments only.
- A hit is reported as a path and a line number, never the matched text.
- No account id, secret, or hostname is added.

## Done when

`python3 scripts/check_pii.py` passes and does not print that the run checks nothing. `python3 -m unittest discover -s tests -v` passes.

## Rollback

Revert this pull request. The check goes back to checking nothing, and it says so.
