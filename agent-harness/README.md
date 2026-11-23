# Agent harness

Checks agent rules, file length, and test focus. `.github/harness.json` holds the lists that differ between repositories: required rules and skills, size limits, scan roots, and the allowlist path. A repository that does not run the file-length check omits that object.

`rules.extra-rules` is `full`. `rules.verify-why-commits` checks that a `[why:]` tag names `convention` or a commit that exists. `rules.skills` is `all` or `required`.

`file-length.mode` is `typed`. Omit `typescript-app-prefix` and `typescript-lib-prefix` when the repository has no TypeScript to scan. An omitted prefix is not scanned. A prefix containing `__not_scanned__` fails. Alembic `versions` and directories whose name starts with `.` are skipped.

`python3 check_harness.py --help` prints usage. A config path and `--root` override the environment. The action passes neither, and uses `HARNESS_CONFIG` and `HARNESS_ROOT`.

`test-focus.mode` is `test-names`. It scans test files only. Python does not treat `fit(` as a focused test. `test.skip(condition, "reason")` is allowed. `test.skip("reason")` is not.

`evolvesprouts` and `siutindei` still use `always-only`, `python-counted` or `python-names`, and `all-sources`. The pull request that pins this checker must change `harness.json` in the same commit: `extra-rules` `full`, `file-length.mode` `typed` with `python-prefix` and `python-limit`, and `test-focus.mode` `test-names`. Omit the TypeScript prefix keys.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `config` | no | `.github/harness.json` | Config path. |
| `root` | no | the workspace | Directory to scan. |

## Permissions

`contents: read`. The why-commit check runs `git cat-file` and needs the commits in the checkout.
