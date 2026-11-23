# One harness mode

Zone: yellow. The note stays in this pull request.

`file-length` is `typed`. `test-focus` is `test-names`. `rules.extra-rules` is `full`. The other modes are rejected.

`test-names` scans test files only, with the pair A patterns. `fit(` is not applied to Python, so `ImageOps.fit(` is not a focused test. `test.skip(condition, "reason")` is not a failure. The check does not ban every `test.skip(`.

A Python repository omits `typescript-app-prefix` and `typescript-lib-prefix`. An omitted prefix is not scanned. A placeholder prefix is not required. Typed length skips Alembic `versions` and dot directories.

Product `harness.json` files stay as they are until this commit is on `main`.
