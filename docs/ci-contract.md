# CI contract

This is the shape every product repository is moving to. `workflow-conformance` checks the rules in the first list. The workflow files are the target, not a claim that every repository already has them.

## What conformance checks

- Every `uses` is a 40-character commit SHA, or a local `./` action.
- `runs-on` is `ubuntu-26.04` or `macos-26`.
- Each workflow has a top-level `permissions` block.
- `lint.yml` has a job named `lint`. `test.yml` has a job named `test`.
- Those two workflows have no `pull_request` path filter.
- A repository uses one `lx-software-ltd/actions` commit.
- When `.pre-commit-config.yaml` points at `lx-software-ltd/actions`, its `rev` is that commit.

`mode: warn` prints findings and exits 0. `mode: enforce` exits 1. This repository runs enforce.

## Target workflow files

| File | Jobs | Notes |
| --- | --- | --- |
| `lint.yml` | Per-stack lint jobs, `validate-agent-harness`, `workflow-conformance`, gate `lint` | No `pull_request` path filter |
| `test.yml` | Per-stack test jobs, gate `test` | No `pull_request` path filter |
| `security.yml` | `checkov`, `codeql`, `pii-denylist`, `secrets-scan`, `dependency-audit`, `bandit`, `npm-audit`, `security-summary` | Push, pull request, weekly |
| `semgrep.yml` | `semgrep/ci` | Skips Dependabot |
| `check-lockfiles.yml` | `node-lockfiles`, `python-requirements`, and in pair B `flutter-lockfiles`, `ios-lockfiles` | |
| `verify-rulesets.yml` | `verify-branch-protection` | Weekly, Monday |

Deploy, bootstrap, and key-management workflows stay manual. They are not part of this contract's rollout.

## Versions

Node 26 is the `setup-node` default. Python is 3.12. The runners are `ubuntu-26.04` and `macos-26`.
