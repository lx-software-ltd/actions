# Shared actions plan — progress

**Status**: C04 is merged. Post-CI phases are in progress. G3 and G4 are approved. G5 is approved for the cdk-deploy design note only.
**Zone**: yellow

The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. The approved plan is in that file in full. Recorded decisions at the top of that file win where they conflict with the approved text. Decision, owner-task, row, and step numbers keep the approved meanings. This file does not renumber them. An earlier progress table called the Node and macOS choices "O6". That was wrong. O6 is `AWS_ACCOUNT_ID`. On 22 Nov 2026 the owner made it a repository secret and removed the variable.

Named approvals, 20 Nov 2026:

- Gate G1 is approved for SA-304. The expected approving-review count is 0.
- Gate G2 is approved for SA-302 and for SA-307. The earlier approval for `findingalpha` `scripts/pii-denylist.sha256`, and for that file in this repository, still stands.
- The O3 tag split was edited on 20 Nov 2026. See the measurement below. The agent does not edit organisation rulesets and does not run `gh release create`.
- O5 is approved. The IAM trust narrowing is the owner's and blocks only Stage 5. The account id in the public `lx-software` trust-policy document is a separate one-file change. Do not copy the account id into this file.
- O6 was a variable. On 22 Nov 2026 the owner changed it: `AWS_ACCOUNT_ID` is a repository secret, and the variable is removed. Callers pass `secrets.AWS_ACCOUNT_ID` only. Do not also pass `vars.AWS_ACCOUNT_ID`. A variable is printed in the step header before masking. The account id is not written into this file.

22 Nov 2026, owner-approved:

- G3 is approved, including C24, which removes `cdk bootstrap` from pair B deploys. Bootstrap stays in `cdk-bootstrap.yml`.
- G4 is approved for SA-601.
- G5 is approved for writing `docs/plans/cdk-deploy.md` only. Implementation waits for a second G5 approval on that note.
- SA-501 passes `secrets.AWS_ACCOUNT_ID` only. The earlier `secrets.AWS_ACCOUNT_ID || vars.AWS_ACCOUNT_ID` line is withdrawn. The account id is not written into this file.
- Red steps are one repository at a time. After each merge the owner runs the affected deploy (O7) before the next repository starts.

## Owner tasks

Numbers are the approved plan's numbers.

| Id | Task | State on 20 Nov 2026, 21:30 Hong Kong |
| --- | --- | --- |
| O1 | Public `actions` repository, agent can push | Confirmed |
| O2 | Actions policy allows `lx-software-ltd/*` | Not read. The policy API returns 403. Observed: this repository's own gates resolved `lx-software-ltd/actions/require-jobs@1a3cca7` and the runs were green. |
| O3 | How `v*` tags get created | Organization admin is on the `release-tags-create` bypass list. The owner creates the tag. The agent does not. |
| O4 | Is zero approving reviews intended? | Decided. Yes. SA-304 checks for exactly 0. |
| O5 | Narrow `GitHubActionsRole` trust to the four product repositories | The owner reported this complete on 22 Nov 2026. The account id stays out of this file. |
| O6 | `AWS_ACCOUNT_ID` | A repository secret, as of 22 Nov 2026. The variable was removed. Callers pass `secrets.AWS_ACCOUNT_ID` only. |
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
| SA-501 | Merged. `actions` #30 at `839efa2`. `findingalpha` #83 at `a007feb`. CDK Diff on that pull request passed (`45038363292`), and the `main` dispatch `45039311163` passed. The credentials step masked the account id and the diff summary was written. `findingalpha-admin-web` had differences. The job passed. |
| SA-502 | Merged. `actions` #32 at `12ce754`. `findingalpha` #84 at `24d9267`. CDK Diff run `45040680793` on that pull request passed: the bootstrap check read the SSM version, the credentials step masked the account id, and the diff summary was written. `findingalpha-admin-web` had differences. The job passed. `lx-software`, `evolvesprouts`, and `siutindei` stay on `9235676200771b2f93bc01ac85f3de1392133182` and keep their current triggers. |
| CI close-out | Merged. #27. Done (CI scope) except C04. |
| C04 and pin | Merged. `findingalpha` #80 `e829c7900d496cd7aaaa98619807ed28dd46a3c8`. `lx-software` #669 `6ce6213ac6a54d5c6c08fbcdee5a9e04a1296bdb`. `evolvesprouts` #2276 `aa0d8d379017b98e4e879ae0ca50111ab1348c75`. `siutindei` #927 `b19167534cf9ba1e23ca805aee483d851bf31961`. The record pull request #28 merged before these SHAs were written. This pull request adds them. |

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
| 2 follow-up | `findingalpha` #79, merge `24e6b0c`, 20:03 HKT. Removes the repository-wide Semgrep urllib exclusion. |
| 3 | `lx-software` #664, merge `ca04022`. `evolvesprouts` #2275, merge `fc2629f`. `siutindei` #926, merge `0f77d451`. |
| Checker | `actions` #26, merge `9235676`. Product pins stay `61b67ed4` until the C04 pull requests below. |

All four product `main` branches run `workflow-conformance` with `mode: enforce`. No caller passes `mode: warn`, `mode: ci`, or `allow-skipped`.

### Inputs that kept an older behaviour

Measured on the four `main` commits above.

On the four `main` commits above, `node-version` is still passed. Jobs a pull request runs pass `"26"`. Workflows a pull request does not run keep the previous string in pair B: `lts/*` in `evolvesprouts`, and `"24"`, `'24'`, or `"lts/*"` in `siutindei`. The C04 pull requests remove that older value. In `evolvesprouts`, `lts/*` already selects Node 26, so the string change does not change the runtime. In `siutindei`, Node 24 to Node 26 is a major-version jump on `deploy-admin-web`, `deploy-public-www`, `promote-public-www`, `smoke-public-www-staging`, `cdk-bootstrap`, `lighthouse-public-www`, and `e2e-admin-web`. Pull-request CI already tests the public site on Node 26. The admin end-to-end workflow runs only when started by hand. `deploy-admin-web` runs on a later push that touches its app paths, so the merge itself does not start the first Node 26 admin deploy. `board-merge-staging` does not set a Node version.

`python-version` is still passed. Every measured value is `"3.12"` or `'3.12'`, the `setup-python` default. No caller passes `3.13`.

`framework` is `cloudformation` in all four. Nobody passes an empty framework.

Semgrep `exclude-rules`: `findingalpha` #79 is merged, and `findingalpha` `main` does not exclude the urllib rule. `siutindei` excludes `yaml.github-actions.security.gha-curl-pipe-shell.gha-curl-pipe-shell` because the rule warns on `${{ }}` in `run:` blocks. `lx-software` and `evolvesprouts` pass no `exclude-rules`.

`flutter-version` stays. C06 makes it required. `evolvesprouts` passes `3.50.1`. `siutindei` passes `3.47.9`.

findingalpha `cdk-diff.yml` calls `aws-oidc`, `cdk-bootstrap-check`, and `cdk-diff`. The other product workflows still contain their own AWS and deploy steps. Stage 6 actions are not called.

### Still open

- C04 is merged. `findingalpha` #80 `e829c7900d496cd7aaaa98619807ed28dd46a3c8`. `lx-software` #669 `6ce6213ac6a54d5c6c08fbcdee5a9e04a1296bdb`. `evolvesprouts` #2276 `aa0d8d379017b98e4e879ae0ca50111ab1348c75`. `siutindei` #927 `b19167534cf9ba1e23ca805aee483d851bf31961`. The pin at that merge was `9235676200771b2f93bc01ac85f3de1392133182`. findingalpha later moved to `12ce754` in #84. `lx-software`, `evolvesprouts`, and `siutindei` are still on that pin. The owner still needs to dispatch `e2e-admin-web.yml` and Deploy Admin Web on `siutindei` `main`. Those are the first Node 26 runs of those paths.
- Flutter pins differ. C06 requires a pin, not one shared version. `evolvesprouts` passes `3.50.1`. `siutindei` passes `3.47.9`.
- Stage 5. G3 is approved. The owner reported O5 complete on 22 Nov 2026. SA-501 is merged, and CDK Diff on findingalpha `main` passed (`45039311163`). SA-502 is merged: `cdk-bootstrap-check` and `cdk-diff`, piloted in findingalpha #84. That pull request's CDK Diff passed (`45040680793`). The other three repositories are not updated. SA-503 is in progress. actions #33 (`b7ae747`) warns on a missing CDK app and streams the diff. actions #34 (`c210c3223782894251ba37b4fc71a0c245619d39`) adds `cfn-stack-outputs`. findingalpha #85 warns in the CDK Diff preparation step. findingalpha #86 is merged and pins `c210c3223782894251ba37b4fc71a0c245619d39`. findingalpha #88 is merged. Manage Public API Keys on that commit succeeded (`45095235815`). No findingalpha workflow reads `vars.AWS_ACCOUNT_ID`, so that variable can be deleted. The owner started lx-software before a findingalpha deploy run. lx-software #674 is merged. That merge push ran Deploy Backend, because `backend/infrastructure/params/README.md` matches its path filter, and the job succeeded (`45094844930`). Deploy Admin Web was dispatched (`45094891068`) and the follow-up run succeeded (`45095083626`). Deploy Public Website has not been re-run since `45038917904`. lx-software #675 moves those workflows to `aws-oidc`, `cdk-bootstrap-check`, `cdk-diff`, and `cfn-stack-outputs`, pinned to `b40bb0725bf84f25a38641f6ca5ec6f4c2f14f98`. CDK Diff stays `workflow_dispatch`. No deploy is dispatched from #675. evolvesprouts #2280 and siutindei #940 are the secret-only switches. After those merge, the `AWS_ACCOUNT_ID` variable is not read there either.
- Stage 6. G4 is approved for SA-601. SA-603 is the design note only; implementation needs a second G5 approval. SA-602 stays out of scope.
- SA-701. The pair B mobile and promote workflows (`deploy-ios.yml`, `deploy-mobile.yml`, `promote-public-www.yml`, `smoke-public-www-staging.yml`) were not compared for a shared block of ten lines.
- SA-702. `mypy` where Python is linted, a type-check for every Node app, a coverage floor at the measured value, and OpenAPI lint where an OpenAPI file exists. Each is its own plan in the repository it changes.
- The pin bump to `9235676` is the same four pull requests. They also drop the quotes around `statuses` in `lx-software` and `siutindei`.
