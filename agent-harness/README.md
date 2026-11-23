# Agent harness

Checks agent rules, file length, and test focus. `.github/harness.json` holds the lists that differ between repositories: required rules and skills, size limits, scan roots, and the allowlist path. A repository that does not run the file-length check omits that object.

`rules.extra-rules` is `full`: every rule file is checked. `rules.verify-why-commits` checks that a `[why:]` tag names `convention` or a commit that exists. `rules.skills` is `all` or `required`.

`file-length.mode` is `typed`. Alembic `versions` and dot directories are skipped. `test-focus.mode` is `test-names`. It scans every file with a listed suffix and reports a focused test, an unconditional skip, and `@pytest.mark.skip`.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `config` | no | `.github/harness.json` | Config path. |
| `root` | no | the workspace | Directory to scan. |

## Permissions

`contents: read`. The why-commit check runs `git cat-file` and needs the commits in the checkout.
