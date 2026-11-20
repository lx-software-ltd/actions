# actions

Shared composite actions and pre-commit hooks for the `lx-software-ltd` product repositories.

Callers pin a full commit SHA:

```yaml
uses: lx-software-ltd/actions/require-jobs@<40-hex> # main <yyyy-mm-dd>
```

`main-protection` and `release-tags` both apply. A force-push is blocked, and this token cannot create or move a `v*` tag. Callers pin a commit SHA. The current `require-jobs` pin is in `docs/plans/progress.md`.

The CI contract is `docs/ci-contract.md`. The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. Progress is `docs/plans/progress.md`.
