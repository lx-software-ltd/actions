# Shared actions plan — progress

**Status**: Done (CI scope)
**Zone**: yellow

The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. The approved plan is in that file in full. Recorded decisions at the top of that file win where they conflict with the approved text. Decision, owner-task, row, and step numbers keep the approved meanings. This file does not renumber them. An earlier progress table called the Node and macOS choices "O6". That was wrong. O6 is `AWS_ACCOUNT_ID`, and the decision is now that it stays a variable.

Named approvals, 20 Nov 2026:

- Gate G1 is approved for SA-304. The expected approving-review count is 0.
- Gate G2 is approved for SA-302 and for SA-307. The earlier approval for `findingalpha` `scripts/pii-denylist.sha256`, and for that file in this repository, still stands.
- The O3 tag split was edited on 20 Nov 2026. See the measurement below. The agent does not edit organisation rulesets and does not run `gh release create`.
- O5 is approved. The IAM trust narrowing is the owner's and blocks only Stage 5. The account id in the public `lx-software` trust-policy document is a separate one-file change. Do not copy the account id into this file.
- O6 stays a variable. Stage 5 reads `vars.AWS_ACCOUNT_ID` only. Do not assert or write `secrets.AWS_ACCOUNT_ID || vars.AWS_ACCOUNT_ID`. That line overrides decision D8 and the SA-501 sentence in the plan copy.

Gates G3, G4, and G5 stay closed.

## Owner tasks

Numbers are the approved plan's numbers.

| Id | Task | State on 20 Nov 2026, 21:30 Hong Kong |
| --- | --- | --- |
| O1 | Public `actions` repository, agent can push | Confirmed |
| O2 | Actions policy allows `lx-software-ltd/*` | Not read. The policy API returns 403. Observed: this repository's own gates resolved `lx-software-ltd/actions/require-jobs@1a3cca7` and the runs were green. |
| O3 | How `v*` tags get created | Organization admin is on the `release-tags-create` bypass list. The owner creates the tag. The agent does not. |
| O4 | Is zero approving reviews intended? | Decided. Yes. SA-304 checks for exactly 0. |
| O5 | Narrow `GitHubActionsRole` trust to the four product repositories | Approved, before Stage 5. Not started. Also remove the account id from the public trust-policy document. |
| O6 | `AWS_ACCOUNT_ID` | A variable. Stage 5 uses `vars.AWS_ACCOUNT_ID` only. Not started. |
| O7 | Hand-run each deploy workflow after its pull request merges | Open. Cannot start early. |
| O8 | Attach `main-protection` and `release-tags` to `actions` | Done. Both rulesets are returned for this repository. `main-protection` was updated `2026-11-20T13:17:29Z`. |

Node 26 and `macos-26` are the answers to the open questions, not owner tasks. They are C04 and C03.

## Rulesets, measured 20 Nov 2026, 21:30 Hong Kong

`GET /repos/lx-software-ltd/actions/rulesets` returns `main-protection` (id `27712218`, branch) and `release-tags` (id `27712299`, tag). Both `enforcement: active`. `bypass_actors` is null. `current_user_can_bypass` is `never`.

`main-protection` on `actions` `main`:

- Deletion and force-push blocked.
- Pull request required. `required_approving_review_count` is 0. That is intended (O4).
- Required checks are exactly `lint` and `test`, strict.

Measured again 20 Nov 2026, 23:40 Hong Kong.

`release-tags` (id `27712299`, updated `2026-11-20T15:37:16Z`) includes `refs/tags/v*` and has rules `deletion` and `update` only. `bypass_actors` is empty. Creation is no longer on this ruleset.

Measured again 20 Nov 2026, 16:11 UTC. `release-tags-create` (id `27737981`, updated `2026-11-20T16:11:54Z`) includes `refs/tags/v*`. Its only rule is `creation`. The earlier include `refs/tags/refs/tags/v*` and the `non_fast_forward` rule are gone.

Measured again 21 Nov 2026, 12:30 Hong Kong. Organization admin is on the bypass list of `release-tags-create`. `release-tags` still has no bypass, so update and deletion stay blocked for everyone. This token's read of ruleset `27737981` still returns `bypass_actors: null` and `current_user_can_bypass: never`. That field is hidden here. A null `bypass_actors` on this endpoint is not an empty bypass list.

Organization admin can create a `refs/tags/v*` tag. Other actors cannot. The agent does not run `gh release create`. Callers still pin commit SHAs until a release exists.

The same organisation rulesets apply to the four product repositories.

### O3, what the owner applies

In the organisation ruleset settings:

1. Edit `release-tags`. Keep "Restrict updates" and "Restrict deletions". Remove "Restrict creations". Leave the bypass list empty.
2. Add a tag ruleset, `release-tags-create`, with the same repository targeting and pattern `refs/tags/v*`, and only "Restrict creations". Organization admin is on its bypass list. Done.
3. Optionally turn on release immutability for `actions`. The agent does not change repository settings.

A ruleset bypass cannot apply to one rule inside a ruleset, which is why creation has to be its own ruleset. After the split, the owner tags with `gh release create`. The agent prepares the notes and does not run that command.

## PII denylist

The owner approved copying the 31 digests shared by `evolvesprouts` and `siutindei` (measured 20 Nov 2026). `lx-software` has 30 of those 31. This decision does not add the missing digest there.

`scripts/pii-denylist.sha256` in this repository now holds those 31 digests. No plaintext. `check_pii.py` passed against this tree and against `findingalpha` before the copy. `findingalpha`'s copy is a pull request in that repository, under the G2 approval for that file only.

## Versions

| Choice | Decision | When behaviour changes |
| --- | --- | --- |
| Node | 26, the major version | SA-301 sets it as the `setup-node` default. Each product repository moves on its own C04 pull request. `evolvesprouts` jobs pinned to 22.22.2 and `siutindei`'s jobs on 24 are the ones that change. |
| macOS | `macos-26` | Pair B's C03 pull request. `macos-latest` is this image today. |
| Python | 3.12, already the target | `siutindei`'s three 3.13 jobs move on C05. |

## Gate pin

| Pin | SHA |
| --- | --- |
| Merge that put `require-jobs` on `main` | `1a3cca7c38163f8164c262323601c34a4df5b7a4` |

That commit is still an ancestor of `main`. Force-push is blocked. The gates in this repository still pin it. Fixture jobs still use `uses: ./require-jobs`.

One product repository uses one actions SHA. The harness pull requests moved all four to `aab84b76383d5a44838f9617ac47b23cfff7fdaf`: `findingalpha` #77 at `0e93c2b`, `lx-software` #663 at `a4b7033`, `evolvesprouts` #2274 at `58ab636`, `siutindei` #925 at `0fb8b5d`. findingalpha merged first. The wave 1 merge is on `main` at `61b67ed4f686659433f6ca4cb10c80707e365cd0` (#24). That commit is the pin for the product waves.

## Dependabot

Unchanged from the earlier note. `cooldown.exclude` for `lx-software-ltd/actions/*` is an inference from the options reference, not a measured run. Do not mark C28 done. `container.image` digest bumps are not documented. Row C14 stays manual until a run shows otherwise.

## SA-103 — next `verify-rulesets` run

The action is on `actions` `main` at `61d2a58`. It fails unless the approving-review count is exactly 0 and the required checks are exactly `lint` and `test`. The four product workflows still run their local scripts. Pair A still warns and passes. Pair B still fails on Monday 23 Nov 2026 at 09:00 UTC until the rollout is on `main`.

## Measured commits, 20 Nov 2026, 23:20 Hong Kong

| Repository | Commit | Note |
| --- | --- | --- |
| `findingalpha` | `11407a5725c8ac97fb1d9b8ba92d3a69d195a34d` | SA-301 merge, #73. |
| `lx-software` | `326acc85fd7f80079b3fefb4551260590c6ef6aa` | SA-205 merge, #657. |
| `evolvesprouts` | `bdf7b0f22518361c0f79d27d35c53e29758b6cab` | SA-205 merge, #2270. |
| `siutindei` | `fe2c76663d4d26a5fb4409ca73ad4bf3ba543e58` | SA-205 merge, #920. |
| `actions` | `61d2a581a1d880533982bada88923ad1b6431700` | #13. `verify-rulesets` is on `main`. |

## Steps

| Step | State |
| --- | --- |
| SA-101 | Merged. `evolvesprouts` #2267, `siutindei` #917. |
| SA-102 | Merged. `findingalpha` #69, `lx-software` #656, `evolvesprouts` #2268, `siutindei` #918. |
| SA-103 | Reported above. No edit. |
| SA-201 | Merged. #1, included in `1a3cca7`. |
| SA-202 | Merged. #2, merge commit `1a3cca7`. Fixture jobs use `uses: ./require-jobs`. |
| SA-202 pin | Merged. #4. Gates pin `1a3cca7`. |
| Decisions | Parent pull request. O3, O4, C03, C04, and the denylist approval. |
| Denylist copy | Merged. #7 writes the 31 digests here. |
| SA-203 | Merged. `findingalpha` #72, merge `d924cc4`. |
| SA-205 | Merged. `lx-software` #657, `evolvesprouts` #2270, `siutindei` #920. |
| SA-301 | Merged. `actions` #9 at `c55e210`, then #11 at `c850872`. |
| SA-204 | Waiting on a `v*` release. The tag rulesets are measured above. Dependabot has nothing to move until a release exists. |
| SA-301 rollout | Merged at `61d2a58`: `findingalpha` #75, `lx-software` #661, `evolvesprouts` #2273, `siutindei` #923. Three of those pins moved again in SA-302. |
| SA-304 | Merged at `61d2a58`: `findingalpha` #74, `lx-software` #660, `evolvesprouts` #2272, `siutindei` #922. The stricter tag check is on `actions` `main` at `2ba4826` and is not that pin. |
| SA-302 | Merged. `actions` #19 at `f33bc37`. Product: `findingalpha` #76, `lx-software` #662, `siutindei` #924. `evolvesprouts` had no CI PII job at that pin. |
| SA-303, SA-305 | The actions are on `main` at `aab84b7`. Product call sites are the next wave. |
| SA-306 | Merged. `actions` #22 and #23 at `aab84b7`. Product: `findingalpha` #77, `lx-software` #663, `evolvesprouts` #2274, `siutindei` #925. Evidence is below. |
| SA-307 | This pull request publishes the hook definitions. Deleting the product script copies is Wave 2. |
| SA-308, SA-309 | This pull request. The audit actions and `workflow-conformance` in enforce mode here. |
| Later | Product waves pin `61b67ed4`. findingalpha is the first. Part B is deferred. G3, G4, and G5 stay closed. |
| uses: anchor | Merged. #26 at `9235676`. `_uses` is `^\s*(-\s*)?uses:`. Product pins stay `61b67ed4`. Quoted `"statuses"` keys stay until a later pin bump. |
| CI close-out | This pull request. The CI scope is done. Stages 5 and 6, SA-701, and SA-702 stay open. |

## SA-306 evidence

On each product `main`, the local scripts and `agent-harness` with that repository's `.github/harness.json` both exit 0 and report no findings.

Turning `alwaysApply` off on `00-repository-core.mdc` makes both exit 1. Both print `00-repository-core.mdc alwaysApply must be true`. Checked on `findingalpha`, `lx-software`, `evolvesprouts`, and `siutindei`.

`evolvesprouts` CI now also runs the file-length and test-focus checks, because they are in its harness config. Both pass on `main`. That extra coverage is accepted.

## Part B

Deferred. Stage 5 needs O5, G3, and O7. Stage 6 needs G4 and G5. This exercise closes at the CI scope.

## CI close-out, 22 Nov 2026

Waves 0, 1, 2, and 3 are merged. This pull request is wave 4, the last wave of the CI exercise.

| Wave | On `main` |
| --- | --- |
| 0 | Harness pull requests. The SA-306 evidence is above. |
| 1 | `actions` #24, merge `61b67ed4f686659433f6ca4cb10c80707e365cd0`. That SHA is still the product pin. |
| 2 | `findingalpha` #78, merge `7fd1553`. |
| 3 | `lx-software` #664, merge `ca04022`. `evolvesprouts` #2275, merge `fc2629f`. `siutindei` #926, merge `0f77d451`. |
| Checker | `actions` #26, merge `9235676`. Product pins stay `61b67ed4`. `lx-software` lighthouse still has `"statuses": write`. `siutindei` board merge still has `"statuses": read`. |

All four product `main` branches run `workflow-conformance` with `mode: enforce`. No caller passes `mode: warn`, `mode: ci`, or `allow-skipped`.

`findingalpha` #79 is open. It removes the repository-wide Semgrep urllib exclusion. It is not merged.

### Inputs that kept an older behaviour

Measured on the four `main` commits above.

`node-version` is still passed. Jobs a pull request runs pass `"26"`, the `setup-node` default. Workflows a pull request does not run keep the previous string in pair B: `lts/*` in `evolvesprouts`, and `"24"`, `'24'`, or `"lts/*"` in `siutindei`. `findingalpha` and `lx-software` pass `"26"` on those workflows too. C04 is not finished for the workflows pull-request CI does not run.

`python-version` is still passed. Every measured value is `"3.12"` or `'3.12'`, the `setup-python` default. No caller passes `3.13`.

`framework` is `cloudformation` in all four. Nobody passes an empty framework.

Semgrep `exclude-rules`: `findingalpha` `main` still excludes `python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected` for the whole repository. That removal is #79. `siutindei` excludes `yaml.github-actions.security.gha-curl-pipe-shell.gha-curl-pipe-shell` because the rule warns on `${{ }}` in `run:` blocks. `lx-software` and `evolvesprouts` pass no `exclude-rules`.

`flutter-version` stays. C06 makes it required. `evolvesprouts` passes `3.50.1`. `siutindei` passes `3.47.9`.

Stage 5 and Stage 6 actions are not called. Those workflows still contain their own AWS and deploy steps.

### Still open

- Stage 5, all of it. It needs O5, G3, and O7. G3 stays closed. O5 is approved and not started.
- Stage 6. SA-601 needs G4. SA-603 needs a design note and G5. Both gates stay closed. SA-602, `lighthouse-ci`, was not added. The product Lighthouse workflows are still inline.
- SA-701. The pair B mobile and promote workflows (`deploy-ios.yml`, `deploy-mobile.yml`, `promote-public-www.yml`, `smoke-public-www-staging.yml`) were not compared for a shared block of ten lines.
- SA-702. `mypy` where Python is linted, a type-check for every Node app, a coverage floor at the measured value, and OpenAPI lint where an OpenAPI file exists. Each is its own plan in the repository it changes.
- A later pin bump can move the products from `61b67ed4` to `9235676` and drop the quoted `"statuses"` keys. Not this pull request.
