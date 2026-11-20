# actions

Shared composite actions and pre-commit hooks for the `lx-software-ltd` product repositories.

Callers pin a full commit SHA:

```yaml
uses: lx-software-ltd/actions/require-jobs@<40-hex> # main 2026-11-20
```

Tags are `vMAJOR.MINOR.PATCH` and do not move. Until a tag exists, the comment is `# main <yyyy-mm-dd>`.

The CI contract is `docs/ci-contract.md`. Progress on the convergence plan is `docs/plans/progress.md`.
