# actions

Shared composite actions and pre-commit hooks for the `lx-software-ltd` product repositories.

Callers pin a full commit SHA:

```yaml
uses: lx-software-ltd/actions/require-jobs@<40-hex> # main <yyyy-mm-dd>
```

Pin a commit that is on `main`. `main-protection` applies, so a force-push cannot drop that commit. Do not pin a tag yet. `release-tags` applies and blocks creating, moving, and deleting `v*` tags. The owner will split creation into a separate ruleset before the first tag. Details are in `docs/plans/progress.md`.

The CI contract is `docs/ci-contract.md`. The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. Progress is `docs/plans/progress.md`.
