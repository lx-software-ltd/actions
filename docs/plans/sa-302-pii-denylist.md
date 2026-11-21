# SA-302 — shared PII check

**Status**: This pull request
**Zone**: yellow

## Intent

Run `check_pii.py` from `pii-denylist` in CI. The caller's hash list stays in the caller. Local `scripts/check_pii.py` and `scripts/check-pii.sh` stay until SA-307.

## What changed

`pii-denylist` scans tracked files under `root` and fails when a line matches the hashed denylist. This repository's `lint.yml` and `security.yml` call `uses: ./pii-denylist`. The pass and fail fixtures are in `test.yml`.

`findingalpha` is the pilot. That pull request replaces `python3 scripts/check_pii.py` and moves every `lx-software-ltd/actions` pin to this commit. The local script and its unit test stay.

## Rollback

Revert this pull request.
