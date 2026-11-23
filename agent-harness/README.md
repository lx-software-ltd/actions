# Agent harness

Checks agent rules, file length, and test focus. `.github/harness.json` holds the lists that differ between repositories: required rules and skills, size limits, scan roots, and the allowlist path. A repository that does not run the file-length check omits that object.

`rules.extra-rules` is `full`. `rules.verify-why-commits` checks that a `[why:]` tag names `convention` or a commit that exists. `rules.skills` is `all` or `required`.

`file-length.mode` is `typed`. Omit `typescript-app-prefix` and `typescript-lib-prefix` when the repository has no TypeScript to scan. An omitted prefix is not scanned. Alembic `versions` and directories whose name starts with `.` are skipped.

`test-focus.mode` is `test-names`. It scans test files only. Python does not treat `fit(` as a focused test. `test.skip(condition, "reason")` is allowed. `test.skip("reason")` is not.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `config` | no | `.github/harness.json` | Config path. |
| `root` | no | the workspace | Directory to scan. |

## Permissions

`contents: read`. The why-commit check runs `git cat-file` and needs the commits in the checkout.
