# Shared actions plan — progress

**Status**: In progress
**Zone**: yellow

The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. Where that file and an older note disagree, the plan copy wins. Gates G1 to G5 are closed. No red path has been edited.

## What was actually confirmed

| Owner task | State |
| --- | --- |
| O1. Public `actions` repository | Confirmed. The repository exists and this agent can push to it. The first commit was a README only. The Apache-2.0 licence is added in the scaffold pull request. |
| O2. Actions policy allows `lx-software-ltd/*` | Not re-verified. The owner said this was done. The policy API still returns 403 for this token, so this file does not record it as confirmed. |
| O3. Tag decision | Open as a choice of who creates a release. `release-tags` now applies, and this token cannot create or move a `v*` tag. |
| O4. Is zero approving reviews intended? | Open. Not answered. The live product ruleset asks for zero. SA-103 below says what the next weekly run will do with that ruleset. It is not an owner decision. |
| O5. Trust policy for deploy roles | Open. Not changed here. |
| O6. Node default and macOS label (C04, C03) | Open. Not answered. |
| O7. Hand-run each deploy workflow after its pull request merges | Open. This cannot be done ahead of those merges. None of those pull requests exist yet. |
| O8. Attach `main-protection` and `release-tags` to `actions` | Confirmed on 20 Nov 2026 at 13:17 UTC. Both rulesets are on this repository. Details are below. |

The kickoff said owner tasks were done. That is not recorded as fact. O7 cannot have been done, and O3 and O4 were not answered.

## Rulesets, measured 20 Nov 2026 at 13:17 UTC

`GET /repos/lx-software-ltd/actions/rulesets` returns `main-protection` and `release-tags`. The same pair is on `findingalpha`, `lx-software`, `evolvesprouts`, and `siutindei`. Earlier the same day the `actions` list was empty. Live problems item 4 in the hand-off plan is true as of this measurement.

`main-protection` (id `27712218`, updated `2026-11-20T13:17:29Z`, source Organisation):

- Targets `~DEFAULT_BRANCH`, enforcement active.
- Required checks are exactly `lint` and `test`, strict.
- `required_approving_review_count` is 0.
- Blocks deletion and force-push.
- `bypass_actors` is null in the payload this token can read. `current_user_can_bypass` is `never`.

`release-tags` (id `27712299`, updated `2026-11-20T13:17:45Z`) blocks creation, update, and deletion of `refs/tags/v*`. Same bypass result.

The organisation ruleset list itself is 403 for this token. A 403 on that endpoint is not "no ruleset". Read the repository's own ruleset list.

Old SHAs stay reachable: the ruleset blocks force-pushes. This token cannot create or move a `v*` tag. `security-summary` is still not a required check. PII and Gitleaks also run inside `lint-python`, so they fail the `lint` check, and that check now blocks a merge.

## PII denylist

`scripts/pii-denylist.sha256` contains no digests. `scripts/check_pii.py` exits 0 and prints that the run checks nothing. The job stays, so the owner can add organisation-level hashes without a new workflow. This file does not invent hashes.

That script is not the product copy. The four product copies of `scripts/check_pii.py` match each other (`d7dd4c7405105dc9568f1e8f1df3f54aee7e875512c80eb7d539ed442fe5c41f`). This copy (`97409722de37ffaddcf21040d960649f03d3c3c9056e3b93bc1fbb1206c85d99`) adds an early return when the denylist is empty. SA-302 chooses which file is the source. It does not treat them as the same script.

## Gate pin

The spec's self-test uses `uses: ./require-jobs`, which loads the action from the pull request checkout. A pull request that makes `require_jobs.py` always return 0 turns a gate written that way green. The fail fixture still goes red, and that fixture is not a required check. That is a gap in the spec. The layout check rejects a local action on the `lint`, `test`, and `security-summary` jobs.

Those three gates pin `lx-software-ltd/actions/require-jobs` at the merge SHA below. Fixture jobs still use `uses: ./require-jobs`. Do not point a gate at `./`.

| Pin | SHA |
| --- | --- |
| Merge that put `require-jobs` on `main` | `1a3cca7c38163f8164c262323601c34a4df5b7a4` |

That commit is the merge of #2 onto the previous `main` (`a4f81f0`), with parent `e9c01fe`. Its tree matches `e9c01fe`. GitHub reports the same merge commit for #1 and #2. Pull request #4, merge `b1d436a`, points the three gates at it.

A pull request can still edit a gate's `needs` list or its pin. The workflow file comes from the pull request, and nothing in this repository can stop that edit. Review and `main-protection` are what stand outside the repository. The ruleset requires the check names and blocks a force-push. It asks for zero approving reviews, so it does not itself require a person to approve the edit.

## Dependabot

Checked against the options reference, not against a Dependabot run:

- `directories` supports `*`. For `github-actions`, directory `/` scans `.github/workflows` and a root `action.yml` only. This repository also lists `/*` so each action subdirectory is scanned.
- `cooldown.exclude` supports wildcards, and `*` matches across `/`. The reference says a product repository can exclude `lx-software-ltd/actions/*` from the 7-day cooldown (row C28). That is an inference from the documentation. It is not proven until a Dependabot run updates an `actions/*` pin inside the cooldown window. Do not treat C28 as done.
- The options reference does not document updates of a `container.image` digest inside a workflow file. Row C14 stays a manual bump until a Dependabot run shows otherwise.

## SA-103 — next `verify-rulesets` run

Not edited. Pair A (`findingalpha`, `lx-software`) warns when the approving-review count is below one and does not fail on that warning. Both repositories have job ids `lint` and `test`, the required contexts match job names, and `release-tags` is active. The next weekly run passes, with the warning that `main` does not require an approving review.

Pair B (`evolvesprouts`, `siutindei`) treats a review count below one as an error. The live ruleset asks for zero. The next weekly run fails with `main ruleset does not require at least 1 approving review.` The lint and test context checks pass, because those contexts are on the ruleset. SA-304 replaces this script and is behind gate G1.

Whether zero approving reviews is intended is O4, and it is unanswered. `actions` has no `verify-rulesets` workflow, so there is nothing to run here. The ruleset itself is now attached.

## Measured commits on 20 Nov 2026

| Repository | Commit | Note |
| --- | --- | --- |
| `findingalpha` | `11e6caa` | Two Cognito merges after `2cbc059`. Workflow files were not part of those merges. |
| `lx-software` | `186d7fb` | Unchanged from the plan. |
| `evolvesprouts` | `c1d4686` | Unchanged from the plan. |
| `siutindei` | `87b1915` | Unchanged from the plan. |
| `actions` | `b1d436a` | Both organisation rulesets are attached. #4 pins the gates at `1a3cca7`. |

## Steps

| Step | State |
| --- | --- |
| SA-101 | Open. `evolvesprouts` #2267, `siutindei` #917. |
| SA-102 | Open. `findingalpha` #69, `lx-software` #656, `evolvesprouts` #2268 stacked on #2267, `siutindei` #918 stacked on #917. |
| SA-103 | Reported above. No edit. |
| SA-201 | Merged. #1, included in `1a3cca7`. |
| SA-202 | Merged. #2, merge commit `1a3cca7`. Fixture jobs use `uses: ./require-jobs`. |
| SA-202 pin | Merged. #4, merge commit `b1d436a`. The gates pin `require-jobs` at `1a3cca7`. |
| SA-203 onward | Not started. The pin SHA is on `main` and O8 is done. Red gates G1 to G5 are still closed. |
