# SA-306 — agent harness

**Status**: This pull request
**Zone**: yellow

## Intent

One harness checker, configured by `.github/harness.json`. The file holds required rules and skills, size limits, scan roots, the file-length allowlist path, and which test-focus rules apply. A repository that does not check file length omits that object.

## Same result

`extra-rules: full` with `verify-why-commits: true` and `skills: all` is the `findingalpha` and `lx-software` check. `extra-rules: always-only` is the `evolvesprouts` and `siutindei` check. `verify-why-commits` is false for `evolvesprouts` and true for `siutindei`. `test-focus.mode` is `test-names` or `all-sources`. The unit tests keep the old messages, including the body line number `evolvesprouts` prints for a missing `[why:]`.

Product pull requests add `.github/harness.json` from each repository's current constants and compare the old script with this action on `main`.

## Rollback

Revert this pull request.
