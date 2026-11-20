# Shared actions plan — progress

**Status**: In progress
**Zone**: yellow

The owner approved the design in chat on 20 Nov 2026 and, in the session that started this repository, said owner tasks O1 through O7 are done. That approval does not by itself approve a red gate. Gates G1 to G5 are still closed. No red path has been edited.

## Measured again on 20 Nov 2026

| Repository | Commit | Note |
| --- | --- | --- |
| `findingalpha` | `11e6caa` | Two Cognito merges after `2cbc059`. Workflow files were not part of those merges. |
| `lx-software` | `186d7fb` | Unchanged from the plan. |
| `evolvesprouts` | `c1d4686` | Unchanged from the plan. |
| `siutindei` | `87b1915` | Unchanged from the plan. |
| `actions` | this branch | Created with a README. No rulesets are attached. |

`main-protection` on the product repositories (ruleset id `27712218`, updated `2026-11-20T10:19:28Z`):

- Targets `~DEFAULT_BRANCH`, enforcement active.
- Required checks are exactly `lint` and `test`, strict.
- `required_approving_review_count` is 0.
- Blocks deletion and force-push.
- `bypass_actors` is null in the payload this token can read. `current_user_can_bypass` is `never`.

`release-tags` (id `27712299`) blocks creation, update, and deletion of `refs/tags/v*`. No bypass actor is visible. This repository will not create a `v*` tag. Callers pin a commit SHA and comment `# main <yyyy-mm-dd>` until the owner tags a release.

## SA-103 — next `verify-rulesets` run

Not edited. Pair A (`findingalpha`, `lx-software`) warns when the approving-review count is below one and does not fail on that warning. Both repositories have job ids `lint` and `test`, the required contexts match job names, and `release-tags` is active. The next weekly run passes, with the warning that `main` does not require an approving review.

Pair B (`evolvesprouts`, `siutindei`) treats a review count below one as an error. The live ruleset asks for zero. The next weekly run fails with `main ruleset does not require at least 1 approving review.` The lint and test context checks pass, because those contexts are on the ruleset. SA-304 replaces this script and is behind gate G1.

`actions` has no `verify-rulesets` workflow yet, and no ruleset is attached to it, so there is nothing to run here.

## Dependabot, checked against the options reference

- `directories` supports `*`. For `github-actions`, directory `/` scans `.github/workflows` and a root `action.yml` only. This repository also lists `/*` so each action subdirectory is scanned.
- `cooldown.exclude` supports wildcards, and `*` matches across `/`. Product repositories can exclude `lx-software-ltd/actions/*` from the 7-day cooldown (row C28). That change is not made in this pull request.
- The options reference does not document updates of a `container.image` digest inside a workflow file. Row C14 stays a manual bump until a Dependabot run shows otherwise.

## Steps

| Step | State |
| --- | --- |
| SA-101 | Patches prepared for `evolvesprouts` and `siutindei`. Pull requests are opened from those repositories. |
| SA-102 | Same session. `permissions: contents: read` on the workflows the plan names. Pair B is stacked on SA-101. |
| SA-103 | Reported above. No edit. |
| SA-201 | This pull request. Layout, workflows, licence, Dependabot, this progress file. |
| SA-202 | This pull request. `require-jobs`, unit tests, pass and fail fixtures. The repository gates call `uses: ./require-jobs`. No tag. The pin comment is the merge commit once it is on `main`. |
| SA-203 onward | Not started. Red gates G1 to G5 are not approved. |
