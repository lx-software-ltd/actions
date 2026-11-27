# One batch pull request for Dependabot updates

Zone: yellow. The note stays until the pull request that finishes this change deletes it.

Checked 27 Nov 2026. This note is the brief for the agent that implements the change. It covers this repository and the four product repositories.

## What is true

### The toil

Every merged Dependabot pull request in the five repositories was merged by the owner, by hand. `evolvesprouts` opens 5 to 25 a week, `siutindei` 8 to 21, `lx-software` 4 to 7. `findingalpha` and this repository open a few.

`main-protection` sets `strict_required_status_checks_policy: true`. A pull request has to contain the head of `main` before it can merge. Each merge puts every other open pull request behind. The owner clicks Update branch, waits for the three gates, merges, and repeats.

- 16 Nov 2026, `evolvesprouts`: 17 Dependabot pull requests opened at 03:36 UTC and all were merged by 04:03 UTC.
- 23 Nov 2026, `evolvesprouts`, after the organisation ruleset: 9 opened at 05:12 UTC and the last merged at 08:09 UTC.
- 27 Nov 2026: 32 opened across the four products after an edit to `.github/dependabot.yml`. An hour later 26 were still open.

The gates take 11 to 16 minutes in `evolvesprouts` and `siutindei`, and 1 to 3 minutes in the other three.

An edit to `.github/dependabot.yml` starts a full Dependabot run in that repository. The weekly schedule is Monday. The time is not set, and each repository has its own.

### What a Dependabot pull request looks like

- The author is `dependabot[bot]`, user id `49699333`, type `Bot`. The head is a branch of the same repository and starts with `dependabot/`.
- There is one commit. Its author is `dependabot[bot]`, its committer is `web-flow`, and it is verified.
- The commit message ends with a block that names every update:

```text
---
updated-dependencies:
- dependency-name: "@tanstack/react-query"
  dependency-version: 5.108.1
  dependency-type: direct:production
  update-type: version-update:semver-minor
  dependency-group: minor-and-patch
...
```

- Update branch adds a merge commit by the person who clicked. It has two parents, the committer is `web-flow`, and it is verified.
- `chore(deps)` is the prefix for npm, pip, and pub. `ci` is the prefix for `github-actions`. A `github-actions` group can hold a major bump. `siutindei` 997 moves `actions/download-artifact` from 7 to 8.
- The `actions-pin` group needs `scripts/bump_pins.py` on the branch before it can merge. That stays as it is.

### What a merge to `main` starts

A push to `main` starts the production deploys. The path filters include the manifests Dependabot edits: `apps/admin_web/**`, `apps/public_www/**`, `backend/**`, and the Flutter app directory. It also starts `submit` in `dependency-submission.yml`, and `lint.yml` and `test.yml` on `main`.

### What `github.token` can and cannot do

- An event caused by `github.token` does not start a workflow run. The exceptions are `workflow_dispatch` and `repository_dispatch`, and a pull request that a workflow opens or updates: its `pull_request` runs are created waiting for a person to approve them. Source: <https://docs.github.com/en/actions/concepts/security/github_token>.
- So a merge made with `github.token` does not start the deploys or the dependency submission.
- `github.token` cannot add a pull request to a merge queue. Source: <https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions>.
- `github.token` cannot hold the `workflows` permission. A push or a server-side merge that creates or changes a file under `.github/workflows/` is refused. The API answers 422.
- A workflow run that Dependabot starts reads Dependabot secrets, not Actions secrets.
- All five repositories let GitHub Actions create pull requests (`can_approve_pull_request_reviews` is true).

### Other facts

- `@dependabot merge`, `@dependabot squash and merge`, `@dependabot close`, and `@dependabot reopen` stopped working on 27 Jan 2026. `evolvesprouts` and `siutindei` still list `@dependabot merge` in `docs/architecture/decisions.md`.
- Dependabot rebases its pull request when a push to the target branch puts it in conflict.
- GitHub marks a pull request merged when its head commit becomes reachable from the base branch.
- `lint.yml`, `test.yml`, and `security.yml` in the four products read no secret and have no job that depends on the event. All three have `workflow_dispatch`.
- `require_extra_approval_for_unattributed_changes` has no effect while the approval count is 0.
- `allow_auto_merge` and `delete_branch_on_merge` are off in all five repositories.

## Decision

A new composite action, `dependabot-batch`, lands the routine updates as one pull request per repository.

It reads the open Dependabot pull requests, picks the ones that are safe to land together, and merges their head commits onto one new branch cut from `main`. It opens one pull request for that branch. The gates run once, on the combination. The owner merges that one pull request with a merge commit. GitHub then marks each member pull request merged.

Each Dependabot pull request keeps its own gate result. A failing update is left out and does not block the others.

The owner still makes the merge. That is what starts the deploys, and `github.token` cannot do it.

The action runs three ways from one payload, the way `sync-labels` does:

| Where | Mode | Token | What the owner does |
| --- | --- | --- | --- |
| Each product, on a schedule | `open` | `github.token` | Merges one pull request |
| This repository, on a schedule | `report` for `siblings` | `github.token` | Reads one summary for all five |
| A checkout, with `gh` signed in | `land` for `siblings` | The owner's | Runs one command |

### What stays by hand

The report lists these and the action never batches them:

- A major update, unless the caller adds `major` to `update-types`.
- A pull request that changes a file under `.github/workflows/`. A third-party action runs inside the deploy workflows, and `github.token` cannot merge that change anyway.
- The `actions-pin` group.
- A pull request with a commit from someone other than Dependabot, other than an Update branch merge.
- A pull request whose gates failed, or that conflicts with the batch.

### Not chosen

- **Loosen the ruleset.** Turning off `strict_required_status_checks_policy` brings back the 16 Nov behaviour: one click per pull request and no wait. The combination is then first tested on `main`, after the deploys have started. That is the owner's call and needs no code. The batch works with either setting.
- **A merge queue.** It fixes the wait for every pull request, not only Dependabot's. It needs a ruleset in each repository, `merge_group` on the three gate workflows in all five, and a token other than `github.token` to queue without a click. It is a larger change and can come later. A batch pull request goes through a queue like any other.
- **One Dependabot group per repository.** `multi-ecosystem-groups` gives one pull request with no code. One update that fails then blocks all of them, and how the key combines with `groups` and `ignore` is not measured here.
- **A workflow that enables auto-merge on each Dependabot pull request.** Under the strict rule each one stalls as soon as another merges, and a merge by `github.token` starts no deploy.

## The owner decides

The defaults below are what the implementing agent builds unless the owner says otherwise.

| Question | Default |
| --- | --- |
| Which update levels are batched | `patch` and `minor` |
| Are workflow changes batched | No |
| Who merges the batch pull request | The owner. No stored credential |
| Does this repository open batches of its own | No. Its Dependabot updates are all `github-actions`. It runs the report |
| Hosted `land`, with no click | Not built. It needs a GitHub App, see [Later](#later-and-only-with-approval) |

## This change

### The action

`dependabot-batch/action.yml`, `dependabot-batch/batch.py`, and `dependabot-batch/README.md`. Standard library only, Python 3.12. The payload calls GitHub through `gh api`, with the request body as JSON on stdin, the way `sync-labels/sync_labels.py` does. Inputs reach the payload as `DEPENDABOT_BATCH_*` environment variables. No `${{ }}` inside a `run` body. A pull request title never reaches a shell.

| Input | Default | Meaning |
| --- | --- | --- |
| `token` | `github.token` | Token for `gh`. Ignored when `live-json` is set. |
| `mode` | `report` | `report` reads. `open` builds the batch pull request. `land` also waits for the gates and merges. |
| `repositories` | the calling repository | Space-separated `owner/repo`, or `siblings`. |
| `update-types` | `patch minor` | Semver levels that may be batched. |
| `exclude-dependencies` | `lx-software-ltd/actions/*` | Space-separated name globs. A match keeps the pull request out. |
| `exclude-paths` | `.github/workflows/*` | Space-separated path globs. A changed file that matches keeps the pull request out. |
| `required-checks` | `lint test security-summary` | Check names that must have succeeded on a member's head. |
| `start-gates` | `none` | `dispatch` sends `workflow_dispatch` for `gate-workflows` on the batch branch. `none` leaves the gates to the `pull_request` event. |
| `gate-workflows` | `lint.yml test.yml security.yml` | Workflow files for `start-gates: dispatch`. |
| `timeout-minutes` | `60` | `land` only. How long to wait for the gates. |
| `live-json` | empty | A snapshot for a fixture. `report` only. The action does not call GitHub. |

Outputs: `pull-request` (the batch pull request number, or empty) and `batched` (the member count, or in `report` the number of candidates whose class is `batch`). With more than one repository the outputs are empty and the summary carries the result.

#### Candidates and classes

A candidate is an open pull request whose base is the default branch and whose head ref starts with `dependabot/`. Each candidate gets one class. The first rule that matches wins.

| Class | Rule |
| --- | --- |
| `foreign` | The author is not `dependabot[bot]` with id `49699333` and type `Bot`, or the head repository is not the base repository. |
| `draft` | The pull request is a draft. |
| `edited` | A commit is not authored by `dependabot[bot]`, or is not verified. One exception: a verified two-parent commit whose committer is `web-flow`, which is what Update branch writes. A commit with no linked author is not Dependabot's. |
| `unclassified` | No Dependabot commit carries an `updated-dependencies` block, or an entry has no `update-type`. |
| `excluded` | A dependency name matches `exclude-dependencies`. |
| `level` | An entry's level is not in `update-types`. A group with one major entry is `level`. |
| `path` | A changed file matches `exclude-paths`. |
| `running` | A required check on the head is queued or in progress. |
| `unchecked` | A required check has no run on the head. |
| `failing` | A required check finished with anything other than success. |
| `batch` | None of the above. |

Two more classes are set while building: `conflict` when the merge returns 409, and `refused` when it returns 422.

The `updated-dependencies` block is read with a line parser. It starts at the line `updated-dependencies:` and ends at the line `...`. An entry starts at `- dependency-name:`. A value may be double-quoted.

A candidate named in the marker of the open batch pull request, with the same head SHA, is still put through the rules down to `path`. If it passes them, its checks are not read again and it keeps what the marker recorded: `batch` for a member, `conflict` or `refused` for one that was tried and left out.

To take an update out of a batch, mark its pull request as draft. The next run builds the batch without it.

#### Open

Per repository:

1. Delete each `dependabot-batch/*` branch whose pull request carries a valid marker and is no longer open. `delete_branch_on_merge` is off, so a merged batch leaves its branch behind.
2. If any candidate is `running`, build nothing and report `waiting`. This stops a run that starts in the middle of Dependabot's own gates from building half a batch.
3. Find the open batch pull request: head ref starts with `dependabot-batch/`, head repository is the base repository, and the body ends with a valid marker. A pull request without a valid marker is not touched.
4. Compare the marker with the candidates now. The marker names the members and the candidates it tried and left out, each with its head SHA.
   - The candidates that are `batch`, `conflict`, or `refused` now are exactly the ones the marker names, with the same head SHAs: keep it. Do not update the branch and do not start the gates again. If a required check on its head has failed, the run exits 1 so the owner is told.
   - Anything else: comment on the old pull request that it is superseded, close it, delete its branch, and build a new one.
   - No batch pull request and no `batch` candidate: nothing to do.
5. Build. Create `refs/heads/dependabot-batch/<yyyymmdd>-<hhmmss>` (UTC) at the head SHA of the default branch. For each `batch` candidate in ascending pull request number, `POST /repos/{repo}/merges` with `base` the batch branch and `head` the candidate's head SHA. 201 and 204 make it a member. 409 is `conflict`. 422 is `refused`. If no member merged, delete the branch and stop.
6. Open the pull request. Title: `chore(deps): batch <n> Dependabot updates`. Label: `dependencies`. The body lists each member as `#<number>` with its title, lists every candidate that was left out with its class, says that each member passed the required checks on its own head, says to merge with a merge commit, and ends with the marker:

```text
<!-- dependabot-batch {"members":{"<number>":"<head sha>"},"conflict":{"<number>":"<head sha>"},"refused":{"<number>":"<head sha>"}} -->
```

7. When `start-gates` is `dispatch`, send `workflow_dispatch` on the batch branch for each file in `gate-workflows`.

The `conflict` and `refused` records are what stop a rebuild every run. A candidate that conflicts with the batch is still green on its own. Without the record it would look like a new member each time. Once the batch merges, that candidate conflicts with `main`, Dependabot rebases it, and the next batch picks it up.

The action never updates a batch branch in `open`. When `main` moves, the owner clicks Update branch on the batch pull request. That click starts the gates as the owner, with no approval step.

#### Land

`land` does everything `open` does, then:

1. Waits until every required check on the batch head has finished, polling every 30 seconds, up to `timeout-minutes`.
2. If the pull request is behind the default branch, calls `PUT /pulls/{n}/update-branch` with `expected_head_sha` and waits again. Three attempts.
3. If a required check failed, stops and exits 1. The pull request stays open.
4. Merges with `PUT /pulls/{n}/merge`, `merge_method: merge`, and `sha` set to the head it checked.
5. Deletes the batch branch.

`land` refuses to run when `token` equals `github.token`. The action passes `github.token` to the payload in a second variable so it can compare. The message says that a merge by `github.token` starts no push workflow, so nothing would deploy.

`land` is for a checkout with `gh` signed in as the owner:

```sh
DEPENDABOT_BATCH_MODE=land DEPENDABOT_BATCH_REPOSITORIES=siblings python3 dependabot-batch/batch.py
```

The pull request is then the owner's, so the `pull_request` event starts the gates and `start-gates` stays `none`. A member that changes a workflow needs the `workflow` scope on that login and `exclude-paths` set to empty.

#### Report

`report` writes nothing to GitHub. It prints, and appends to `GITHUB_STEP_SUMMARY` when that is set, one table per repository: pull request number, title, class, and the reason. It also shows the batch pull request, its members, and whether its required checks passed, failed, or are running. A `|` in a title is escaped.

`report` exits 1 when a batch pull request has a failed required check, the same as `open`. The scheduled report in this repository then goes red and the owner is told.

`report` with `repositories: siblings` works with any token that can read public repositories, including a read-only one.

#### Exit codes

| Case | Exit |
| --- | --- |
| `report`, no batch has a failed required check | 0 |
| `report` or `open`, a batch pull request has a failed required check | 1 |
| `open`, built, kept, waiting, or nothing to do | 0 |
| `open` or `land` with `live-json` | 1, and nothing is written |
| `land` with `github.token` | 1 |
| `land`, gates failed or timed out | 1 |
| An unknown `mode`, `start-gates`, or repository name | 1 |
| A GitHub call failed | 1, after the other repositories have run |

#### What the action must never do

- Push to, update, or delete a `dependabot/*` branch. Dependabot stops rebasing a branch someone else has pushed to.
- Merge into the default branch with `github.token`.
- Force-push.
- Close or change a pull request it did not open. It closes only a batch pull request that carries its marker.
- Delete a branch other than a `dependabot-batch/*` branch whose pull request carries its marker.
- Batch a candidate whose class is not `batch`.

### Fixtures and tests

`live-json` is one object keyed by `owner/repo`. Each value holds the default branch, its head SHA, and the open pull requests. Each pull request holds what the classes read: number, title, body, draft, author, head, base, commits, changed files, and the latest result of each required check.

- `fixtures/dependabot-batch/pass/live.json`: one repository with a `batch` pair, one `level`, one `path`, one `excluded`, one `edited`, one `failing`, and one `foreign`. `report` exits 0 and `batched` is 2.
- `fixtures/dependabot-batch/fail/live.json`: one repository with an open batch pull request whose `test` check failed. `report` exits 1.

Add `dependabot-batch-pass` and `dependabot-batch-fail` to `.github/workflows/test.yml` and to the `test` gate `needs`. The fail job uses `continue-on-error` and then `test "$OUTCOME" = "failure"`, like the other fail jobs.

`tests/test_dependabot_batch.py` loads the payload with `importlib`, like `tests/test_sync_labels.py`. `gh` is replaced by a function the test passes in. It covers:

- The block parser: one entry, a group, a quoted name, no block, an entry with no `update-type`.
- Every class in the table, one test each, including the Update branch exception and an author with the right login and the wrong id.
- The plan: nothing to do, `waiting`, build in ascending order, keep, keep when a `conflict` candidate is still green, supersede when a member became a draft, supersede when a member's head SHA changed, and keep with a failed check exiting 1.
- The marker: written, read back, and a malformed one ignored.
- The build calls in order, with a 409 and a 422 in the middle, and the branch deleted when no member merged.
- The clean-up: a merged batch branch is deleted, and a `dependabot/*` branch never is.
- `land`: refused with `github.token`, an update when behind, the merge carrying `sha`, and a timeout.
- `open` and `land` refused with `live-json`.
- The report: every candidate appears, a `|` in a title is escaped, and a batch with a failed check exits 1.

A test that counts the jobs in `test.yml` or the files in `templates/workflows/` moves with the change.

### Workflows

This repository, `.github/workflows/dependabot-batch.yml`. Top-level `permissions: contents: read`. One job, `report`, with `contents: read`, `checks: read`, and `pull-requests: read`. It checks out, then `uses: ./dependabot-batch` with `mode: report` and `repositories: siblings`. Triggers: `workflow_dispatch` and `15 */2 * * 1-5`. It is not a required check and not a gate.

`templates/workflows/dependabot-batch.yml`, for the products. The first line is a bare `# template:if-present`, so a product that has not added the file yet still passes conformance.

```yaml
# template:if-present
name: Dependabot Batch

on:
  workflow_dispatch:
  schedule:
    - cron: "15 */2 * * 1-5"

permissions:
  contents: read

concurrency:
  group: dependabot-batch
  cancel-in-progress: false

jobs:
  batch:
    name: Batch Dependabot updates
    runs-on: ubuntu-26.04
    permissions:
      actions: write
      checks: read
      contents: write
      pull-requests: write
    steps:
      - name: Open the batch pull request
        uses: lx-software-ltd/actions/dependabot-batch@ACTIONS_PIN # main DATE
        with:
          mode: open
          start-gates: dispatch
```

The job needs no checkout. `actions: write` is for the dispatch. `contents: write` is for the branch and the merges. A run every two hours on weekdays costs a few seconds when there is nothing to do. The `waiting` rule and the marker comparison stop it from rebuilding.

### Docs

- `README.md`: a catalogue row for `dependabot-batch`, and a tick per repository as each one adds the workflow.
- `docs/ci-contract.md`: a row in the In place table (`dependabot-batch.yml`, job `batch`, the two triggers, not a required check), a row in the This repository table (job `report`), and one sentence that the `batch` job sets `actions: write`, `contents: write`, and `pull-requests: write` at job level.
- `docs/decisions.md`: a Dependabot section. Routine updates land as one batch pull request per product. The owner merges it. Nothing merges with `github.token`. Workflow changes, majors, and `actions-pin` stay single pull requests. Add each measured result from [Measure](#measure).
- `dependabot-batch/README.md`: inputs, permissions, the classes, the three ways to run it, and how to take an update out of a batch.

### Order of work

1. **This repository, one pull request.** The action, the fixtures, the tests, both workflows, and the docs. Yellow. This note is the plan. The three checks under [How to check](#how-to-check) pass. Evidence in the pull request includes the output of the five-repository report run from the branch:

```sh
DEPENDABOT_BATCH_MODE=report DEPENDABOT_BATCH_REPOSITORIES=siblings python3 dependabot-batch/batch.py
```

2. **The owner tags the merged commit.** A `v*` tag is the owner's. Dependabot then opens the `actions-pin` pull request in each product, and `scripts/bump_pins.py` runs on it as it does today. `.pre-commit-config.yaml` is red in `findingalpha`, `lx-software`, and `siutindei`, so the agent does not move that pin on its own.
3. **`findingalpha`, one pull request, after its pin contains the action.** Add `.github/workflows/dependabot-batch.yml` from the template. Write the short plan that repository's `AGENTS.md` asks for. Treat the workflow as yellow: it holds write permissions and is not a deploy workflow. Then run [Measure](#measure).
4. **`lx-software`, `evolvesprouts`, `siutindei`, one pull request each.** The same file. In `evolvesprouts` and `siutindei` the same pull request removes the `@dependabot merge` line from `docs/architecture/decisions.md` and says how updates land now.
5. **This repository, a last pull request.** Record the measurements in `docs/decisions.md`, tick the catalogue, remove the bare `# template:if-present` line so the workflow is required in every product, and delete this note.

Do not edit `.github/dependabot.yml` in any repository for this change. An edit starts a full Dependabot run.

### Measure

`findingalpha` is first because its gates take about two minutes. Run the workflow by hand once at least two candidates are `batch`. Record each answer in `docs/decisions.md`.

| Question | If the answer is no |
| --- | --- |
| Do the gates started by `workflow_dispatch` satisfy `lint`, `test`, and `security-summary` on the batch pull request, so it shows as mergeable? | Set `start-gates: none` in the template. The owner clicks Approve workflows to run on the batch pull request. |
| Do the `pull_request` runs that wait for approval leave the pull request mergeable? | The same. |
| Does `POST /merges` with `github.token` succeed for a member that changes no workflow, when `main` has changed a workflow since that member's branch was cut? | The member is `refused` and stays a single pull request until Dependabot rebases it. Record how often. |
| After the owner merges with a merge commit, does GitHub show every member as merged? | The README tells the owner to close the members. Dependabot closes them on its next run in any case. |
| Does the five-repository report run from this repository's workflow with `github.token`? | The workflow reports this repository only. The five-repository report stays a local command. |

After three weekly runs, count the `conflict` members in the reports. That count decides whether the product Dependabot groups in one directory should be merged into one. That would be a separate change.

## Later, and only with approval

A hosted `land`, with no click, needs a token whose merge starts push workflows. That is a GitHub App with `contents: write` and `pull-requests: write` on the four products, and its private key as a secret. A new credential is red: plan in chat and wait.

What that plan has to cover:

- The key sits in an environment whose branch rule allows `main` only. A pull request workflow can then not read it. The ruleset asks for zero approvals, so this token could merge any green pull request.
- The workflow mints an installation token in the job and passes it as `token` with `mode: land`. `start-gates` goes back to `none`, because a pull request opened by an App starts its gates without approval.
- Nothing private goes in this repository. The App id and the key are inputs the product passes.

## Not in this change

- Any ruleset, and `strict_required_status_checks_policy`.
- Any `.github/dependabot.yml`.
- A merge queue.
- Re-running a gate that failed on a runner fault.
- Deleting old `dependabot/*` branches. The owner can turn on automatic deletion of head branches.
- The `actions-pin` flow and `scripts/bump_pins.py`.

## After this change

Each product opens at most one batch pull request at a time. The owner merges it, with Update branch first when `main` has moved. The report in this repository shows, for all five, what is in a batch and what is waiting for a person.

The owner can turn on Allow auto-merge in each product. Update branch and Enable auto-merge on the batch pull request are then two clicks with no wait. Whether that merge starts the deploys is not measured. Check it on the first one.

## How to check

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```
