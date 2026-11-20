# Plan: Shared actions repository and CI convergence

**Status**: In progress. Measured facts below were checked on 20 Nov 2026.
**Zone**: red for the program (it reaches deploy and rulesets). A single pull request uses the zone of the files it touches. G1 to G5 are closed.

This is the copy SA-201 required under `docs/plans/`. Executing agents correct a measured fact here when it no longer holds, then act on the corrected text. `docs/plans/progress.md` is the status page. Where they disagree, this file wins.

## Corrections that override the original draft

These were wrong in the draft this file replaces. Do not reintroduce them.

1. **`actions` does not inherit the organisation rulesets.** `GET /repos/lx-software-ltd/actions/rulesets` returns `[]`. The product repositories return `main-protection` and `release-tags`. The organisation ruleset list is 403 for the agent token, and the repository condition is hidden, so the agent cannot attach the rulesets. Owner task O8 is that attachment. Until it is done:
   - A force-push to `actions` `main` can orphan a SHA a caller has pinned. Rollback text that says old SHAs stay valid because the ruleset blocks force-pushes is void.
   - Nothing requires `lint` or `test` before a merge. The workflows are still worth running. They do not gate the merge.
   - `release-tags` does not apply, so a `v*` tag can be created and can be moved. Do not create one. The draft's reason ("the ruleset blocks tags, and no bypass is visible") described the product repositories, not this one.
2. **Owner tasks are not done as a set.** Confirmed: O1, the public repository exists and the agent can push. O2 was stated by the owner and was not re-verified (policy API 403). O3, O4, O5, O6, and O7 are open. O7 is a hand-run of each deploy workflow after its pull request merges, so it cannot be done early. O4 (whether zero approving reviews is intended) is unanswered. SA-103 reports the live ruleset. It does not answer O4.
3. **`allow-skipped: true` is allowed** on `security-summary`, and on pair B's `lint` and `test` gates, when a `changes` job is in `needs` and the gate lists every job. That is C07. The contract must not forbid it. Pair A does not use it. This repository does not use it.
4. **Do not point a gate at `uses: ./require-jobs`.** The spec's self-test does that, and it is a hole: the pull request's copy of `require_jobs.py` is the code that decides the required check. A copy that always returns 0 turns `test` green while the fail fixture, which is not required, goes red. SA-201 uses an inline step. SA-202 adds the action and uses `./` only on fixture jobs. After that merge is on `main`, record the SHA and pin the gates at `lx-software-ltd/actions/require-jobs@<sha>`. One concern per pull request. SA-201 and SA-202 are not the same pull request.
5. **The PII denylist has no digests.** The job checks nothing until the owner supplies organisation-level hashes. Say so. Do not invent hashes.
6. **`findingalpha` `main` is `11e6caa`**, not `2cbc059`. The two later merges are Cognito work. They did not change workflow files. The other three product tips are unchanged: `lx-software` `186d7fb`, `evolvesprouts` `c1d4686`, `siutindei` `87b1915`.

## Goal

One public composite-action repository, `lx-software-ltd/actions`. The four product repositories call those actions and delete their copies. Workflows converge on the same checks, tool versions, and failure behaviour, with the same job names, except for declared inputs and the differences that stay. `workflow-conformance` fails when a repository drifts from `docs/ci-contract.md`.

## Non-goals

- No reusable workflows. `workflow_call` renames checks, and the product ruleset requires checks named exactly `lint` and `test`.
- No deploy or hosting change in the secret-free stages. Pair A stays S3 and CloudFront. Pair B stays Amplify.
- The agent does not change organisation rulesets, IAM, secrets, or repository settings.
- Triggers stay per repository.
- `ai-cxo` is out of scope. It has no workflows and is under the same product ruleset. The owner should know that.
- Do not create a `v*` tag on `actions`.
- Do not print an AWS account id.
- Do not write a red path unless the gate named for that path was approved in chat.

## Repositories

| Pair | Repository | Hosting | Notes |
| --- | --- | --- | --- |
| A | `findingalpha` | S3 and CloudFront | `ubuntu-26.04`. Actions were pinned by tag. |
| A | `lx-software` | S3 and CloudFront | Same shape as `findingalpha`. |
| B | `evolvesprouts` | Amplify, Flutter, Postgres | SHA pins. `ubuntu-24.04`. |
| B | `siutindei` | Amplify, Flutter, Postgres | SHA pins. `ubuntu-latest`. |
| | `actions` | none | This repository. Not covered by the organisation rulesets. |

## Decisions that still stand

- D1. One public repository `lx-software-ltd/actions`, composite actions, not reusable workflows.
- D2. Callers pin a full commit SHA and a version comment. A tag is not a pin until `release-tags` applies here and the tag cannot move.
- D3. Required check names stay `lint` and `test` in the product repositories.
- D4. Pair A and pair B keep their hosting. Convergence does not merge those workflows into one.
- D5. Versions that are not agreed (Node, the macOS label) are inputs. The action default is the target once the owner chooses.
- D6. Python payload is the standard library on 3.12. Tests are `unittest` in `tests/test_*.py`.
- D7. An action does not read `secrets` or `vars`, does not set `permissions`, and does not set a job container. Callers pass inputs. The README states the caller's permissions.
- D8. An action does not call another action. `uses: ./x` inside an action resolves to the caller's checkout.
- D9. Nothing private in `actions`: no secret, account id, internal hostname, or personal data.
- D10. One concern per pull request. `findingalpha` is first when a change is proved in one product repository.

## Current state

Measured 20 Nov 2026. See the corrections for the commits.

Product `main-protection` (id `27712218`, updated `2026-11-20T10:19:28Z`): branch target `~DEFAULT_BRANCH`, enforcement active, deletion and non-fast-forward blocked, pull request required, `required_approving_review_count` 0, stale reviews dismissed, extra approval for unattributed changes, merge methods merge squash and rebase, required status checks exactly `lint` and `test`, strict, `bypass_actors` null, `current_user_can_bypass` `never`.

Product `release-tags` (id `27712299`): tag target `refs/tags/v*`, rules deletion, creation, and update.

`actions` has neither. O8 asks the owner to add it to both, or to an equivalent pair. The agent does not edit rulesets.

Check names are the job `name` when set, otherwise the job id. Gates that the ruleset requires must be named exactly `lint` and `test`.

## Live problems

1. Pair B has no jobs named `lint` and `test`, so the required checks never run. SA-101 adds them. Pair A already has them.
2. Several workflows have no top-level `permissions`. SA-102 sets `contents: read` on the files the stage names.
3. Pair B's `verify-rulesets` fails the weekly run because the review count is zero. Pair A's script warns. SA-103 reports that. SA-304, behind G1, replaces the pair B script. Do not edit those scripts in the secret-free stages.
4. **`actions` is outside both organisation rulesets.** The draft said it inherited them. It does not. Consequences are in the corrections section. Do not call a SHA on `actions` `main` immutable, and do not tell callers to pin one, until O8 is done.
5. Copies of the same composite steps differ by pin style, runner label, and whether a gate exists.
6. `findingalpha` moved from `2cbc059` to `11e6caa` after the draft was written. Re-measure before editing that repository.
7. The PII denylist in `actions` has no digests. The job checks nothing.

## Owner tasks

| Id | Task | State on 20 Nov 2026 |
| --- | --- | --- |
| O1 | Create the public `actions` repository | Confirmed |
| O2 | Actions policy allows `lx-software-ltd/*` | Stated, not re-verified |
| O3 | Decide how `actions` is tagged | Open. Do not tag meanwhile |
| O4 | Say whether zero approving reviews is intended | Open. SA-103 does not decide this |
| O5 | Trust policy for the deploy roles | Open |
| O6 | Node default (C04) and macOS label (C03) | Open |
| O7 | After each deploy pull request merges, run that deploy workflow by hand | Open. Cannot start early |
| O8 | Attach `main-protection` and `release-tags` to `actions` | Open. Agent cannot do this |

## Action rules

- `runs.using` is `composite`. Every `run` step sets `shell`.
- No expression inside `run`. Pass inputs through `env`. An `env:` key after `run:` is not part of the run body.
- Payload via `$GITHUB_ACTION_PATH`. Shared payload via `$GITHUB_ACTION_PATH/../lib`.
- Third-party actions are pinned by 40-character SHA plus a version comment on the same line.
- `tests/test_*.py` only. A test under `scripts/` does not count.
- The calling job needs `python3` on `PATH`. Say so in the action README. Container jobs, including a Semgrep-style job, do not have it unless the image provides it.
- Each action directory has a `README.md` that states the caller's permissions.
- The layout check enforces the rules above, including a step indent other than four spaces, and it rejects `uses: ./` inside an action and on the gate jobs `lint`, `test`, and `security-summary`.

## CI contract

`docs/ci-contract.md` is the written form. `workflow-conformance` (SA-309) checks a repository against it, including this repository. Mode stays `warn` until that repository has no open convergence row.

The contract says which rules apply to `actions` itself. CodeQL in this repository scans Python and GitHub Actions (`languages: actions`), because the workflows and action files are the main content.

## Convergence register

Rows the secret-free stages touch:

| Row | Subject | Notes |
| --- | --- | --- |
| C02 | Runner label | Pair B keeps `ubuntu-24.04` (`evolvesprouts`) and `ubuntu-latest` (`siutindei`) until a later row. Do not change them in SA-101. |
| C03 | macOS label | Open. O6. |
| C04 | Node default | Open. O6. Callers pass their current version. |
| C07 | `changes` job and `allow-skipped` | Pair B's `lint` and `test` gates may set `allow-skipped: true` when a `changes` job is in `needs`. The contract allows this. |
| C09 | Checkout ref | Pair B often checks out `github.event.pull_request.head.sha`. Do not change that in SA-101 or SA-102. |
| C14 | Container image digests | Dependabot's options reference does not document digest bumps inside a workflow. Manual until a Dependabot run shows otherwise. |
| C28 | Dependabot cooldown | The options reference says `cooldown.exclude` can exclude `lx-software-ltd/actions/*`. That is documentation, not a measured Dependabot run. Do not mark C28 done until a run updates such a pin inside the cooldown window. |

## Differences that stay

Hosting, mobile workflows, extra triggers (`repository_dispatch`, `board-*`, Figma sync, key management, the legacy import, the apex redirect probe), stack names, parameters, app directories, and rule exclusions. `findingalpha` has no Lighthouse run.

Push path filters stay. `pull_request` path filters on `lint.yml` and `test.yml` come off, with the `findingalpha` comment that a skipped required check blocks the pull request. That comment describes the product repositories, where the ruleset exists. It does not describe `actions` today.

## Approval gates

Do not edit these paths unless the named gate was approved in chat.

| Gate | Paths |
| --- | --- |
| G1 | `verify-rulesets` scripts and workflows |
| G2 | PII scripts, pre-commit, Cursor hooks, in the product repositories |
| G3 | Credential and AWS steps |
| G4 | Web deploy workflows |
| G5 | `cdk-deploy` and the deploy role |

`scripts/pii-denylist.sha256` in this repository is red on the zone map. Adding hashes is an owner action. The empty file and the sentence that the job checks nothing are the recorded state, not a new denylist.

## Stages

Secret-free stages may proceed. Later stages wait on the gates and on O5, O7, and O8.

| Stage | What | State |
| --- | --- | --- |
| SA-101 | Add `lint` and `test` gates on `evolvesprouts` and `siutindei`. Pair B runners stay. | Pull requests open |
| SA-102 | `permissions: contents: read` on `lint.yml`, `test.yml`, `check-lockfiles.yml` in all four, plus `siutindei` `e2e-admin-web.yml`. No job overrides. | Pull requests open. Pair B stacked on SA-101 |
| SA-103 | Report the next `verify-rulesets` run. No edit. | Reported in `progress.md`. Pair A passes with a warning. Pair B fails on the review count only |
| SA-201 | Scaffold `actions`: licence, contract, zone map, this plan, workflows, Dependabot, inline `lint` and `test` gates. | This work |
| SA-202 | Add `require-jobs`, unit tests, pass and fail fixtures. Fixture jobs may use `uses: ./require-jobs`. Gates stay inline. | Next pull request. Not combined with SA-201 |
| SA-202 pin | Record the merge SHA. Point the gates at `require-jobs` at that SHA. | After SA-202 is on `main` |
| SA-203 | Pilot `require-jobs` in `findingalpha` only. | After a SHA is on `main` and O8 is done. A squash merge orphans a pre-merge pin |
| SA-302, SA-307 | Product PII and hooks | Behind G2 |
| SA-304 | Replace pair B `verify-rulesets` | Behind G1 |
| SA-309 | `workflow-conformance`, mode `warn` until no open row, including this repository | After the contract is the source of truth |
| Stage 5 and 6 | Deploy and credentials | Behind G3, G4, G5, O5, O7 |

SA-101 copies the `findingalpha` inline gate. `if: always()`, `needs` every other job, fail unless every result is `success`. Remove `pull_request` path filters. Keep push path filters. Keep pair B runners.

SA-102 inserts, after the `name:` line, with a blank line above and below:

```yaml
permissions:
  contents: read
```

Those files did not reference `GITHUB_TOKEN`. `upload-artifact` needs no broader token.

## Rollout procedure

For a product change: record the check-run names on `main`, make the change, compare the names, and open the pull request with that repository's template (zone, gate, rollback). Do not trigger deploy, bootstrap, or key workflows. Never print an AWS account id.

`findingalpha` and `lx-software` use the "Docs and contracts" template. `evolvesprouts` and `siutindei` use "Docs and seed data". `siutindei` also has a content zone. `siutindei` board policy refuses `.github/**` to board agents. This work is a normal agent session.

Yellow and red product changes need a short plan from `docs/plans/_template.md` in that repository.

## Zones in this repository

`docs/architecture/zones.md` is the map. It is not itself green. `docs/ci-contract.md` is yellow: conformance enforces it in four repositories and here. `AGENTS.md`, `.github/dependabot.yml`, and `scripts/**` are mapped. The denylist is red. `fixtures/**` is yellow, because a must-fail fixture is part of a gate.

## Executing-agent rules

- Stages in order. One concern per pull request. `findingalpha` first when proving a change.
- SHA pins with version comments.
- Never trigger deploy, bootstrap, or key workflows.
- If a measured fact no longer holds, measure it again and correct this file before acting.
- Do not weaken a check to get a green run.
- Never write a red path without the gate named in chat.
- Do not tag `actions`. Do not tell a caller that a SHA or a tag here is immovable until O8 is done.

## Done when

- The four product repositories call the shared actions and the copies are gone.
- The same check names, tool versions, and failure behaviour hold, except declared inputs and the differences that stay.
- `workflow-conformance` is clean against `docs/ci-contract.md`.
- `actions` is on `main-protection` and `release-tags` (O8), the PII denylist is either hashes from the owner or still explicitly empty, and the gate pin is a SHA that is on `main`.

## Rollback

Revert the pull request that introduced the change. In a product repository, `main-protection` blocks a force-push, so the previous SHA stays reachable.

That sentence is false for `actions`. Reverting a pull request does not stop a later force-push from orphaning the commit a caller pinned. Do not send callers to a pin in this repository until O8 is done. Do not move a tag to roll back. Tags are not protected here, and moving one is the failure mode O8 exists to prevent.

## Risks

- Pinning `actions` before O8. A force-push or a moved tag silently changes what callers run.
- A gate implemented as `uses: ./require-jobs`. The pull request under test supplies the gate.
- An empty PII denylist that is described as if it scanned something.
- Marking C28 done from the Dependabot documentation alone.
- Combining SA-201 and SA-202, which ships the local-action gate in the first merge.
- Editing `verify-rulesets` or a deploy workflow without the gate.

## Open questions

- O4, O5, O6, O8, as in the owner-task table.
- C03 and C04, which are O6.
- Whether `security-summary` should become a required check once O8 is done. Until then it does not block a merge. PII and Gitleaks also run under the `lint` job so they fail that check when the ruleset eventually requires it.
