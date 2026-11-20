# Plan: Record the owner's decisions

**Status**: In progress
**Zone**: yellow

## Goal

Write down the decisions the owner confirmed in chat on 20 Nov 2026, and put the approved plan back into this repository in full. The copy that is here now is a shortened rewrite, and it reuses decision and owner-task numbers for different things.

## Non-goals

- No edit to `scripts/pii-denylist.sha256`. That file is red. The owner approved the digest copy, and the next pull request writes it.
- No product-repository change. `findingalpha`'s denylist is its own pull request, gate G2, for that file only.
- No tag, and no ruleset edit. The tag ruleset split is the owner's to apply.
- No `setup-node` action yet. SA-301 adds it. This pull request records that its default will be Node 26.

## Files

- `docs/plans/shared-actions-and-ci-convergence.md`
- `docs/plans/progress.md`
- `docs/ci-contract.md`
- `AGENTS.md`
- `README.md`
- Comments in `.github/workflows/lint.yml`, `test.yml`, and `security.yml` that still say no ruleset is attached

## Invariants this change preserves

- D1–D10, O1–O8, C01–C28, G1–G5, and the SA step numbers keep the meanings in the approved plan.
- No secret, account id, or personal data is added.
- Workflow behaviour does not change. The comments do.

## Done when

`python3 -m unittest discover -s tests -v` and `python3 scripts/check_action_layout.py` pass. The plan file contains the approved plan, not a summary of it.

## Rollback

Revert this pull request. The decisions stand in chat either way.
