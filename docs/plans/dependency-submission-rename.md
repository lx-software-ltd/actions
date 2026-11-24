# Plan: Rename dependency-graph to dependency-submission

**Status**: Draft
**Zone**: yellow

## Goal

The action directory, workflow file, fixtures, composite action name, notes, and README use `dependency-submission`. The Actions tab name is already Dependency Submission.

## Non-goals

- GitHub's snapshot API path `/dependency-graph/snapshots`. That URL is GitHub's.
- Detector `lx-software-dependency-graph` and correlator `lx-dependency-graph`. A new detector would show a second source under Insights, Dependency graph.
- Job ids `check` and `submit`.
- Product `uses:` lines. A pin `lx-software-ltd/actions/dependency-graph@<sha>` still resolves when that sha contains the old directory. Callers switch the path and the sha together after this commit is on `main`.
- `sync-labels`.

## Files

- `dependency-graph/` becomes `dependency-submission/`. Composite `name:` becomes `Dependency submission`.
- `.github/workflows/dependency-graph.yml` becomes `dependency-submission.yml`. `uses:` points at `./dependency-submission`.
- `fixtures/dependency-graph/` becomes `fixtures/dependency-submission/`. Dependabot and `test.yml` follow.
- `README.md`, `dependency-submission/README.md`, `docs/ci-contract.md`, and `docs/plans/workflow-display-names.md`.

## Invariants this change preserves

Old pins of the previous directory keep working. The snapshot payload's detector and correlator stay. No secret, account id, or personal data.

## Done when

`python3 -m unittest discover -s tests -v`, `python3 scripts/check_action_layout.py`, and `python3 scripts/check_pii.py` pass.

## Rollback

Revert this pull request. Callers that still pin the old directory are unchanged.
