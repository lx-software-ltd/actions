# Verify rulesets

Fails unless the active ruleset on `main` matches the caller's contract.

The default contract is zero approving reviews and required checks exactly `lint` and `test`. Each of those names must be a job id or a job-level `name` in `.github/workflows`. The ruleset must block deletion and force-push. Active rulesets whose include protects `refs/tags/v*` must, together, block creation, update, and deletion. Those three rules may be split across rulesets. A pattern such as `refs/tags/refs/tags/v*` does not count.

This is the pair A script with the approved G1 change. A review count other than the expected count is an error. A required-check list that is not an exact match is an error. Pair B's legacy branch-protection fallback is not part of this action.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `token` | no | empty | `github.token` when the action reads GitHub. Ignored when `rulesets-json` is set. |
| `required-checks` | no | `lint test` | Exact set of required status checks. |
| `expected-reviews` | no | `0` | Exact `required_approving_review_count`. |
| `repository` | no | calling repository | `owner/name` to read. |
| `rulesets-json` | no | empty | Ruleset objects for a fixture. Skips the GitHub API. |

## Permissions

The calling job needs `contents: read`. `github.token` with that permission can read the repository's rulesets. The runner needs `python3` and `gh` on `PATH`. The current Ubuntu runners provide both. Do not add `setup-python`.

## Example

```yaml
      - uses: lx-software-ltd/actions/verify-rulesets@<40-hex> # main <yyyy-mm-dd>
        with:
          token: ${{ github.token }}
          expected-reviews: "0"
          required-checks: lint test
```
