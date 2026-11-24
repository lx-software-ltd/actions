# Workflow display names

## Scope

Workflow and job display names use title case. The dependency action's directory, workflow file, fixtures, and composite name are `dependency-submission`.

Leave these alone:

- Job ids (`check`, `submit`, `sync`).
- The `sync-labels/` directory and `sync-labels.yml`.
- GitHub's snapshot API path `/dependency-graph/snapshots`, the detector `lx-software-dependency-graph`, and the correlator `lx-dependency-graph`. A new detector would show a second source under Insights, Dependency graph.
- A pin `lx-software-ltd/actions/dependency-graph@<sha>` still resolves when that sha contains the old directory. Callers switch the path and the sha together.
- The other composite actions' `name:` lines. They stay in sentence case, such as "Setup Node" and "CDK diff". Those names appear in step logs.

## Why

GitHub's built-in "Dependency Graph" entry sits next to ours. The Actions tab uses title case.

## Change

- `.github/workflows/dependency-submission.yml`: the workflow is Dependency Submission. Job `check` is Check Dependency Submission. Job `submit` is Submit Dependency Submission. The file calls `./dependency-submission`.
- `.github/workflows/sync-labels.yml`: the workflow and job `sync` are Sync Labels.
- `docs/ci-contract.md` lists `dependency-submission.yml`.
- `dependency-submission/README.md` and the catalogue use that name. The composite action name is Dependency submission.

## How to check

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```

After merge, the Actions tab sidebar shows Dependency Submission as ours and Dependency Graph as GitHub's. This repository also shows Sync Labels. Old runs keep the name they started with until they expire. Insights, Dependency graph, Dependencies should show one snapshot from `lx-software-dependency-graph`.
