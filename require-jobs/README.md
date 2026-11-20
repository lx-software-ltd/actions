# Require jobs

Fails unless every job in `needs` succeeded. Writes a result table to the step summary.

The calling job needs `python3` on `PATH`. The action runs `python3 "$GITHUB_ACTION_PATH/require_jobs.py"` and does not install it. A container job, such as the Semgrep-style setup, does not have `python3` unless the image provides it.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `needs-json` | yes | | JSON object. Either `{"job-id":"success"}` or the object `toJson(needs)` returns. Must be non-empty. |
| `allow-skipped` | no | `false` | When `true`, `skipped` counts as success. |

A result other than `success` fails the step. With `allow-skipped`, `skipped` also passes. `failure` and `cancelled` always fail.

## Permissions

The calling job needs no token permissions. The action does not call the GitHub API.

## Example

Pin a commit that is on `main`. Do not pin a tag, and do not point a merge gate at `uses: ./require-jobs`. A local path loads the pull request's copy, so a copy that always exits 0 turns the required check green.

```yaml
  lint:
    name: lint
    runs-on: ubuntu-26.04
    needs: [lint-python]
    if: always()
    steps:
      - uses: lx-software-ltd/actions/require-jobs@1a3cca7c38163f8164c262323601c34a4df5b7a4 # main 2026-11-20
        with:
          needs-json: ${{ toJson(needs) }}
```

In this repository the pass and fail fixture jobs use `uses: ./require-jobs` so they test the pull request's copy. The `lint`, `test`, and `security-summary` gates pin the SHA recorded in `docs/plans/progress.md`. `main-protection` still does not apply, so a force-push can orphan that SHA. Product repositories should wait for owner task O8 before they pin it.
