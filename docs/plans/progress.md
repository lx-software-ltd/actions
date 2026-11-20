# Shared actions plan — progress

**Status**: In progress
**Zone**: yellow

The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. The approved plan is in that file in full. Recorded decisions at the top of that file win where they conflict with the approved text. Decision, owner-task, row, and step numbers keep the approved meanings. This file does not renumber them. An earlier progress table called the Node and macOS choices "O6". That was wrong. O6 is `AWS_ACCOUNT_ID`, and the decision is now that it stays a variable.

Named approvals, 20 Nov 2026:

- Gate G1 is approved for SA-304. The expected approving-review count is 0.
- Gate G2 is approved for SA-302 and for SA-307. The earlier approval for `findingalpha` `scripts/pii-denylist.sha256`, and for that file in this repository, still stands.
- The O3 tag split is approved and not applied. This file's "O3, what the owner applies" is the procedure. The agent does not edit organisation rulesets and does not run `gh release create`.
- O5 is approved and not started. It is before Stage 5. Narrow the role trust to the four product repositories and remove the account id from the public `lx-software` trust-policy document. Do not copy the account id into this file.
- O6 is changed. `AWS_ACCOUNT_ID` stays a variable. Do not add it as a secret. That change is before Stage 5 and is not started.

Gates G3, G4, and G5 stay closed.

## Owner tasks

Numbers are the approved plan's numbers.

| Id | Task | State on 20 Nov 2026, 21:30 Hong Kong |
| --- | --- | --- |
| O1 | Public `actions` repository, agent can push | Confirmed |
| O2 | Actions policy allows `lx-software-ltd/*` | Not read. The policy API returns 403. Observed: this repository's own gates resolved `lx-software-ltd/actions/require-jobs@1a3cca7` and the runs were green. |
| O3 | How `v*` tags get created | Approved, not applied. Only the owner creates one. Nobody can move or delete one. The split below is still not on the organisation. Do not tag until it is. |
| O4 | Is zero approving reviews intended? | Decided. Yes. SA-304 checks for exactly 0. |
| O5 | Narrow `GitHubActionsRole` trust to the four product repositories | Approved, before Stage 5. Not started. Also remove the account id from the public trust-policy document. |
| O6 | `AWS_ACCOUNT_ID` | Changed. It stays a variable. Do not add the secret. Before Stage 5. Not started. |
| O7 | Hand-run each deploy workflow after its pull request merges | Open. Cannot start early. |
| O8 | Attach `main-protection` and `release-tags` to `actions` | Done. Both rulesets are returned for this repository. `main-protection` was updated `2026-11-20T13:17:29Z`. |

Node 26 and `macos-26` are the answers to the open questions, not owner tasks. They are C04 and C03.

## Rulesets, measured 20 Nov 2026, 21:30 Hong Kong

`GET /repos/lx-software-ltd/actions/rulesets` returns `main-protection` (id `27712218`, branch) and `release-tags` (id `27712299`, tag). Both `enforcement: active`. `bypass_actors` is null. `current_user_can_bypass` is `never`.

`main-protection` on `actions` `main`:

- Deletion and force-push blocked.
- Pull request required. `required_approving_review_count` is 0. That is intended (O4).
- Required checks are exactly `lint` and `test`, strict.

`release-tags`: creation, update, and deletion of `refs/tags/v*` are all blocked, with no bypass. A tag cannot be created, and a tag cannot be moved. The O3 split is still to do. Until the owner applies it, this repository stays untagged and callers use `# main <yyyy-mm-dd>`.

The same two rulesets are on the four product repositories.

### O3, what the owner applies

In the organisation ruleset settings:

1. Edit `release-tags`. Keep "Restrict updates" and "Restrict deletions". Remove "Restrict creations". Leave the bypass list empty.
2. Add a tag ruleset, for example `release-tags-create`, with the same repository targeting and pattern `refs/tags/v*`, and only "Restrict creations". Put Organization admin on its bypass list.
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

That commit is still an ancestor of `main`. Force-push is blocked. The gates in this repository pin it. Fixture jobs still use `uses: ./require-jobs`.

One repository uses one actions SHA. `c55e210150528a8e334d95e3ca6ef950f2e83068` is the first commit that contains `require-jobs`, `setup-node`, and `setup-python`. The SA-301 rollout moves each product repository's `require-jobs` pin from `1a3cca7` to that same commit, in the same pull request as the setup actions. Pre-commit `rev` will use that commit too.

`c55e210` treats a `cache` value other than `npm` as no cache. The next change on this repository fails that call. If that change is on `main` before the pilot merges, the pilot pins the newer commit. Still one SHA.

## Dependabot

Unchanged from the earlier note. `cooldown.exclude` for `lx-software-ltd/actions/*` is an inference from the options reference, not a measured run. Do not mark C28 done. `container.image` digest bumps are not documented. Row C14 stays manual until a run shows otherwise.

## SA-103 — next `verify-rulesets` run

Not edited. Pair A warns when the approving-review count is below one and does not fail on that warning. The next weekly run passes, with that warning.

Pair B treats a count below one as an error. The live ruleset asks for zero, and zero is intended (O4). Gate G1 is approved. SA-304 replaces the script and checks for exactly 0. Until that pull request is on `main`, Monday 23 Nov 2026 at 09:00 UTC still fails with `main ruleset does not require at least 1 approving review.` Pair A still only warns.

## Measured commits, 20 Nov 2026, 23:20 Hong Kong

| Repository | Commit | Note |
| --- | --- | --- |
| `findingalpha` | `d924cc4b1bdee7477b49b3352eccd7a4762639ea` | SA-203 merge, #72. |
| `lx-software` | `326acc85fd7f80079b3fefb4551260590c6ef6aa` | SA-205 merge, #657. |
| `evolvesprouts` | `bdf7b0f22518361c0f79d27d35c53e29758b6cab` | SA-205 merge, #2270. |
| `siutindei` | `fe2c76663d4d26a5fb4409ca73ad4bf3ba543e58` | SA-205 merge, #920. |
| `actions` | `c55e210150528a8e334d95e3ca6ef950f2e83068` | SA-301 merge, #9. |

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
| SA-301 | Merged. `actions` #9 at `c55e210`. No product caller yet. |
| SA-204 | Waiting. The tag split is approved and not applied, so Dependabot has no `v*` release to move. |
| SA-301 rollout | Not started. `findingalpha` first. One actions SHA per repository, the commit named in the gate-pin section. Callers pass the versions they use today. |
| SA-304 | Not started. Gate G1 is approved. Needed before Monday 23 Nov 2026, 09:00 UTC, or pair B's weekly run fails on the review count. |
| Later | SA-302 and SA-307 are allowed under the G2 approval above. SA-303, SA-305, SA-306, SA-308, and SA-309 are not started. G3, G4, and G5 stay closed. |
