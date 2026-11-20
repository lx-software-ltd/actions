# Shared actions plan — progress

**Status**: In progress
**Zone**: yellow

The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`. The approved plan is in that file in full. Recorded decisions at the top of that file win where they conflict with the approved text. Decision, owner-task, row, and step numbers keep the approved meanings. This file does not renumber them. An earlier progress table called the Node and macOS choices "O6". That was wrong. O6 is still the `AWS_ACCOUNT_ID` secret.

Gates G1 to G5 stay closed, except one named approval: gate G2, for `findingalpha` `scripts/pii-denylist.sha256` only. The red write of `scripts/pii-denylist.sha256` in this repository is also approved, and this branch writes that file.

## Owner tasks

Numbers are the approved plan's numbers.

| Id | Task | State on 20 Nov 2026, 21:30 Hong Kong |
| --- | --- | --- |
| O1 | Public `actions` repository, agent can push | Confirmed |
| O2 | Actions policy allows `lx-software-ltd/*` | Not read. The policy API returns 403. Observed: this repository's own gates resolved `lx-software-ltd/actions/require-jobs@1a3cca7` and the runs were green. |
| O3 | How `v*` tags get created | Decided. Only the owner creates one. Nobody can move or delete one. The ruleset split that makes this true is not applied yet. Do not tag until it is. |
| O4 | Is zero approving reviews intended? | Decided. Yes. SA-304 checks for exactly 0. |
| O5 | Narrow `GitHubActionsRole` trust to the four product repositories | Open |
| O6 | Add `AWS_ACCOUNT_ID` as a secret where it is only a variable | Open. The variable keeps working. |
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

That commit is still an ancestor of `main`. Force-push is now blocked, so callers may pin it. The `lint`, `test`, and `security-summary` gates in this repository already do. Fixture jobs still use `uses: ./require-jobs`.

## Dependabot

Unchanged from the earlier note. `cooldown.exclude` for `lx-software-ltd/actions/*` is an inference from the options reference, not a measured run. Do not mark C28 done. `container.image` digest bumps are not documented. Row C14 stays manual until a run shows otherwise.

## SA-103 — next `verify-rulesets` run

Not edited. Pair A warns when the approving-review count is below one and does not fail on that warning. The next weekly run passes, with that warning.

Pair B treats a count below one as an error. The live ruleset asks for zero, and zero is intended (O4). The next weekly run, Monday 23 Nov 2026, still fails with `main ruleset does not require at least 1 approving review.` SA-304 replaces the script, behind gate G1, and the shared action takes an expected count of 0.

## Measured commits, 20 Nov 2026, 21:30 Hong Kong

| Repository | Commit | Note |
| --- | --- | --- |
| `findingalpha` | `8c3d3aaf2260966242e600b262d5ce876785272f` | Includes the SA-102 merge, #69. |
| `lx-software` | `6a986bfcbd28c4c604c821501e385a87c2e8f99c` | Includes the SA-102 merge, #656. |
| `evolvesprouts` | `aff0c818a3552308b041a89cf5d0fb7b3c9ad335` | Includes SA-101 #2267 and SA-102 #2268. |
| `siutindei` | `754ee28cd91ffbce371f001139be5d317cddbebd` | Includes SA-101 #917 and SA-102 #918. |
| `actions` | `b1d436a1e365a0a67cbc8ba10ad4701ebf188754` | #1, #2, and #4 merged. Both organisation rulesets attached. |

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
| Denylist copy | This pull request writes the 31 digests here. `findingalpha` is a separate pull request. |
| SA-203 | Not started. O8 no longer blocks it. A tag is not required for the pin. |
| SA-203 onward | Red gates G1 to G5 stay closed, apart from the one G2 file named above. |
