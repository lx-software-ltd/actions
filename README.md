# actions

Shared composite actions and pre-commit hooks for the `lx-software-ltd` product repositories.

Callers pin a full commit SHA:

```yaml
uses: lx-software-ltd/actions/require-jobs@<40-hex> # main <yyyy-mm-dd>
```

Do not pin a tag from this repository. `release-tags` does not apply here, so a `v*` tag can be created and can be moved. `main-protection` does not apply either, so a force-push can drop a commit callers have pinned. Both gaps are written up in `docs/plans/progress.md`.

The CI contract is `docs/ci-contract.md`. The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. Progress is `docs/plans/progress.md`.
