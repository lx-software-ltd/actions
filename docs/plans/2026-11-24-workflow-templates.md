# Plan: workflow templates for the shared checks

**Status**: In progress
**Zone**: yellow

## Goal

Give the five shared check workflows one canonical text, and teach `workflow-conformance` to compare a product workflow with that text outside marked lines. The template check defaults to `enforce`.

## Non-goals

Gate workflows (`lint.yml`, `test.yml`, `security.yml`) and deploy workflows. Those stay on their current text. The template default is `enforce`.

## Files

- `docs/ci-contract.md` — target workflow table, the exact list of differences that stay, and the template rules.
- `docs/decisions.md` — alignment default, and the templates item that is still open.
- `templates/workflows/` — one template for each of the five check workflows.
- `workflow-conformance/` — `templates` input, default `enforce`.
- `flutter-lockfiles/action.yml` — Flutter `3.50.1` when the caller omits the version.

## Invariants this change preserves

- Gate job ids stay `lint`, `test`, and `security-summary`.
- `profile: producer` does not run the template check or the alignment checks.
- An actions pin is still one commit SHA with a `# main YYYY-MM-DD` comment. The template comparison ignores that SHA and that date.

## Done when

`python3 -m unittest discover -s tests -v` passes, including a template match and a template mismatch. `python3 scripts/check_action_layout.py` passes.

## Rollback

Revert this pull request. Product repositories still pin the previous commit, so they keep the previous checker.

## Open questions

None. The owner approved phase 0 and phase 1 on 24 Nov 2026.
