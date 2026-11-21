# Agent harness

Checks agent rules, file length, and test focus. `.github/harness.json` holds the lists that differ between repositories: required rules and skills, size limits, scan roots, and the allowlist path. A repository that does not run the file-length check omits that object.

`rules.extra-rules` is `full` when every rule file is checked, which is what `findingalpha` and `lx-software` do. It is `always-only` when extra rules are only forbidden from `alwaysApply: true`, which is what `evolvesprouts` and `siutindei` do. `rules.verify-why-commits` checks that a `[why:]` tag names `convention` or a commit that exists. `rules.skills` is `all` or `required`.

`test-focus.mode` is `test-names` or `all-sources`.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `config` | no | `.github/harness.json` | Config path. |
| `root` | no | the workspace | Directory to scan. |

## Permissions

`contents: read`. The why-commit check runs `git cat-file` and needs the commits in the checkout.
