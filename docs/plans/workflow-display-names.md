# Workflow display names

## Scope

Change only the workflow `name:` and the job `name:` values.

Leave these alone:

- Workflow file names (`dependency-graph.yml`, `sync-labels.yml`).
- Job ids (`check`, `submit`, `sync`).
- The `dependency-graph/` and `sync-labels/` action directories. Renaming them breaks every pin.
- The composite actions' own `name:` lines. All 34 actions use sentence case, such as "Setup Node" and "CDK diff". Those names appear in step logs, not in the Actions tab sidebar.

## Why

GitHub's built-in "Dependency Graph" entry sits next to ours. The Actions tab uses title case.

## Change

- `.github/workflows/dependency-graph.yml`: the workflow is Dependency Submission. Job `check` is Check Dependency Submission. Job `submit` is Submit Dependency Submission.
- `.github/workflows/sync-labels.yml`: the workflow and job `sync` are Sync Labels.
- `docs/ci-contract.md`: add the `dependency-graph.yml` row. The table already lists `sync-labels.yml`.
- `dependency-graph/README.md`: one sentence after the `update-pip-graph` sentence. The caller's workflow is named "Dependency Submission", so it isn't confused with GitHub's "Dependency Graph".

## How to check

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```

After merge, the Actions tab sidebar shows Dependency Submission as ours and Dependency Graph as GitHub's. This repository also shows Sync Labels. Old runs keep the name they started with until they expire, so "Dependency graph" can still appear for a while. The first push to `main` should run Submit Dependency Submission successfully. Insights, Dependency graph, Dependencies should show one snapshot from `lx-software-dependency-graph`.
