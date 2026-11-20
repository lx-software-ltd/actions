# Shared actions plan — progress

**Status**: In progress
**Zone**: yellow

The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. Where that file and an older note disagree, the plan copy wins. Gates G1 to G5 are closed. No red path has been edited.

## What was actually confirmed

| Owner task | State |
| --- | --- |
| O1. Public `actions` repository | Confirmed. The repository exists and this agent can push to it. The first commit was a README only. The Apache-2.0 licence is added in the scaffold pull request. |
| O2. Actions policy allows `lx-software-ltd/*` | Not re-verified. The owner said this was done. The policy API still returns 403 for this token, so this file does not record it as confirmed. |
| O3. Tag decision | Open. No decision is recorded. See the ruleset section: a `v*` tag here can be created and can move, so this repository will not create one. |
| O4. Is zero approving reviews intended? | Open. Not answered. The live product ruleset asks for zero. SA-103 below says what the next weekly run will do with that ruleset. It is not an owner decision. |
| O5. Trust policy for deploy roles | Open. Not changed here. |
| O6. Node default and macOS label (C04, C03) | Open. Not answered. |
| O7. Hand-run each deploy workflow after its pull request merges | Open. This cannot be done ahead of those merges. None of those pull requests exist yet. |
| O8. Attach `main-protection` and `release-tags` to `actions` | Open. The agent cannot edit organisation rulesets, and the repository condition is hidden from this token. |

The kickoff said owner tasks were done. That is not recorded as fact. O7 cannot have been done, and O3 and O4 were not answered.

## Rulesets, measured again on 20 Nov 2026

`GET /repos/lx-software-ltd/actions/rulesets` returns `[]`. No ruleset is attached.

`GET /repos/lx-software-ltd/findingalpha/rulesets` returns both organisation rulesets. The same pair is attached to `lx-software`, `evolvesprouts`, and `siutindei`.

`main-protection` (id `27712218`, updated `2026-11-20T10:19:28Z`, source Organisation):

- Targets `~DEFAULT_BRANCH`, enforcement active.
- Required checks are exactly `lint` and `test`, strict.
- `required_approving_review_count` is 0.
- Blocks deletion and force-push.
- `bypass_actors` is null in the payload this token can read. `current_user_can_bypass` is `never`.

`release-tags` (id `27712299`) blocks creation, update, and deletion of `refs/tags/v*`. No bypass actor is visible on the product repositories.

The organisation ruleset list itself is 403 for this token. The repository condition that selects the product repositories and not `actions` is hidden. Do not read an empty ruleset list on a product repository the same way: a 403 on the organisation endpoint is not "no ruleset".

### What the missing ruleset means

The plan's old "Live problems" item 4 said `actions` inherits both rulesets. That is wrong.

- Nothing requires `lint` or `test` before a merge into `actions`. The workflows run, and a failing check does not block the merge.
- A force-push to `main` can orphan a commit. The rollback promise that old SHAs stay valid because a ruleset blocks force-pushes is void until O8 is done. Callers must not pin this repository until then.
- `release-tags` does not apply here. A `v*` tag can be created, and it can also be moved. The earlier reason for not tagging ("the ruleset blocks tags") was backwards. Do not tag, because a tag would not be immovable.
- `security-summary` is not a required check anywhere. PII and Gitleaks also run as steps of `lint-python`, so they fail the `lint` check, and that still does not block a merge until O8.

## PII denylist

`scripts/pii-denylist.sha256` contains no digests. `scripts/check_pii.py` exits 0 and prints that the run checks nothing. The job stays, so the owner can add organisation-level hashes without a new workflow. This file does not invent hashes.

## Gate pin

The spec's self-test uses `uses: ./require-jobs`, which loads the action from the pull request checkout. A pull request that makes `require_jobs.py` always return 0 turns a gate written that way green. The fail fixture still goes red, and that fixture is not a required check. That is a gap in the spec. The layout check rejects a local action on the `lint`, `test`, and `security-summary` jobs.

Those three gates pin `lx-software-ltd/actions/require-jobs` at the merge SHA below. Fixture jobs still use `uses: ./require-jobs`. Do not point a gate at `./`.

| Pin | SHA |
| --- | --- |
| Merge that put `require-jobs` on `main` | `1a3cca7c38163f8164c262323601c34a4df5b7a4` |

That commit is the merge of #2 onto the previous `main` (`a4f81f0`), with parent `e9c01fe`. Its tree matches `e9c01fe`. GitHub reports the same merge commit for #1 and #2. `main-protection` still does not apply, so a force-push can orphan it. Product callers wait for owner task O8.

## Dependabot

Checked against the options reference, not against a Dependabot run:

- `directories` supports `*`. For `github-actions`, directory `/` scans `.github/workflows` and a root `action.yml` only. This repository also lists `/*` so each action subdirectory is scanned.
- `cooldown.exclude` supports wildcards, and `*` matches across `/`. The reference says a product repository can exclude `lx-software-ltd/actions/*` from the 7-day cooldown (row C28). That is an inference from the documentation. It is not proven until a Dependabot run updates an `actions/*` pin inside the cooldown window. Do not treat C28 as done.
- The options reference does not document updates of a `container.image` digest inside a workflow file. Row C14 stays a manual bump until a Dependabot run shows otherwise.

## SA-103 — next `verify-rulesets` run

Not edited. Pair A (`findingalpha`, `lx-software`) warns when the approving-review count is below one and does not fail on that warning. Both repositories have job ids `lint` and `test`, the required contexts match job names, and `release-tags` is active. The next weekly run passes, with the warning that `main` does not require an approving review.

Pair B (`evolvesprouts`, `siutindei`) treats a review count below one as an error. The live ruleset asks for zero. The next weekly run fails with `main ruleset does not require at least 1 approving review.` The lint and test context checks pass, because those contexts are on the ruleset. SA-304 replaces this script and is behind gate G1.

Whether zero approving reviews is intended is O4, and it is unanswered. `actions` has no `verify-rulesets` workflow and no ruleset, so there is nothing to run here.

## Measured commits on 20 Nov 2026

| Repository | Commit | Note |
| --- | --- | --- |
| `findingalpha` | `11e6caa` | Two Cognito merges after `2cbc059`. Workflow files were not part of those merges. |
| `lx-software` | `186d7fb` | Unchanged from the plan. |
| `evolvesprouts` | `c1d4686` | Unchanged from the plan. |
| `siutindei` | `87b1915` | Unchanged from the plan. |
| `actions` | `1a3cca7` | No rulesets. #1 and #2 are merged. This pull request pins the gates at that SHA. |

## Steps

| Step | State |
| --- | --- |
| SA-101 | Open. `evolvesprouts` #2267, `siutindei` #917. |
| SA-102 | Open. `findingalpha` #69, `lx-software` #656, `evolvesprouts` #2268 stacked on #2267, `siutindei` #918 stacked on #917. |
| SA-103 | Reported above. No edit. |
| SA-201 | Merged. #1, included in `1a3cca7`. |
| SA-202 | Merged. #2, merge commit `1a3cca7`. Fixture jobs use `uses: ./require-jobs`. |
| SA-202 pin | This pull request. The SHA above is recorded, and the three gates pin `require-jobs` at it. |
| SA-203 onward | Not started. The pin SHA is on `main`. Still waits on O8 and on red gates G1 to G5. |
