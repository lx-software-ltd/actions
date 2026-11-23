# One harness mode

Zone: yellow. The note stays in this pull request.

`file-length` is `typed`. `test-focus` is `test-names`. `rules.extra-rules` is `full`. The other modes are rejected.

`test-names` scans test files only, with the pair A patterns. `fit(` is not applied to Python, so `ImageOps.fit(` is not a focused test. `test.skip(condition, "reason")` is not a failure. The check does not ban every `test.skip(`.

A Python repository omits `typescript-app-prefix` and `typescript-lib-prefix`. An omitted prefix is not scanned. A prefix containing `__not_scanned__` fails the check. Typed length skips Alembic `versions` and dot directories.

`python3 check_harness.py --help` prints usage. A config path and `--root` are read. The action still uses the environment variables.

The pin bump for `evolvesprouts` and `siutindei` must change `harness.json` in the same pull request. `extra-rules` becomes `full`, `file-length.mode` becomes `typed` with `python-prefix` and `python-limit`, and `test-focus.mode` becomes `test-names`. The TypeScript prefix keys are omitted. Product files stay unchanged until that pin is a commit on `main`.
