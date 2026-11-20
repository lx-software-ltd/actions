# Require jobs

Fails unless every job in `needs` succeeded. Writes a result table to the step summary.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `needs-json` | yes | | JSON object. Either `{"job-id":"success"}` or the object `toJson(needs)` returns. Must be non-empty. |
| `allow-skipped` | no | `false` | When `true`, `skipped` counts as success. |

A result other than `success` fails the step. With `allow-skipped`, `skipped` also passes. `failure` and `cancelled` always fail.

## Permissions

The calling job needs no token permissions. The action does not call the GitHub API.

## Example

```yaml
  lint:
    name: lint
    runs-on: ubuntu-26.04
    needs: [lint-python]
    if: always()
    steps:
      - uses: lx-software-ltd/actions/require-jobs@<40-hex> # main 2026-11-20
        with:
          needs-json: ${{ toJson(needs) }}
```

Inside this repository the call is `uses: ./require-jobs`.
