# Dependabot batch

Reads the open Dependabot pull requests and classes each one. `open` merges the head commits of the safe ones onto one branch cut from the default branch and opens one pull request. The owner merges that pull request with a merge commit. GitHub then marks each member merged.

`report` writes nothing. `land` does what `open` does, then waits for the required checks and merges. `land` refuses `github.token`: a merge by that token starts no push workflow, so nothing would deploy.

To take an update out of a batch, mark its pull request as draft. The next run builds the batch without it.

## Classes

The first rule that matches wins.

| Class | Rule |
| --- | --- |
| `foreign` | The author is not `dependabot[bot]` (id `49699333`, type `Bot`), or the head repository is not the base repository. |
| `draft` | The pull request is a draft. |
| `edited` | A commit is not Dependabot's, or is not verified. A verified two-parent commit whose committer is `web-flow` is the Update branch merge and is allowed. |
| `unclassified` | No Dependabot commit carries an `updated-dependencies` block, or an entry has no `update-type`. |
| `excluded` | A dependency name matches `exclude-dependencies`. |
| `level` | An entry's semver level is not in `update-types`. One major entry in a group makes the pull request `level`. |
| `path` | A changed file matches `exclude-paths`. |
| `running` | A required check on the head is still running. |
| `unchecked` | A required check has no run on the head. |
| `failing` | A required check finished with anything other than success. |
| `batch` | None of the above. |
| `conflict` | The merge into the batch branch returned 409. |
| `refused` | The merge into the batch branch returned 422. |

A candidate named in the open batch's marker, with the same head SHA, keeps the recorded `batch`, `conflict`, or `refused` class. Its checks are not read again.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `token` | no | `github.token` | Token for `gh`. Ignored when `live-json` is set. |
| `mode` | no | `report` | `report` reads. `open` builds the batch pull request. `land` also waits for the gates and merges. |
| `repositories` | no | the calling repository | Space-separated `owner/repo`, or `siblings`. |
| `update-types` | no | `patch minor` | Semver levels that may be batched. |
| `exclude-dependencies` | no | `lx-software-ltd/actions/*` | Space-separated name globs. A match keeps the pull request out. |
| `exclude-paths` | no | `.github/workflows/*` | Space-separated path globs. A changed file that matches keeps the pull request out. Empty batches every path. |
| `required-checks` | no | `lint test security-summary` | Check names that must have succeeded on a member's head. |
| `start-gates` | no | `none` | `dispatch` sends `workflow_dispatch` for `gate-workflows` on the batch branch. `none` leaves the gates to the `pull_request` event. |
| `gate-workflows` | no | `lint.yml test.yml security.yml` | Workflow files for `start-gates: dispatch`. |
| `timeout-minutes` | no | `60` | `land` only. How long to wait for the gates. |
| `live-json` | no | empty | A snapshot for a fixture. `report` only. The action does not call GitHub. |

With one repository, `pull-request` is the batch pull request number, or empty, and `batched` is the member count. In `report`, `batched` is the number of candidates whose class is `batch`. With more than one repository both outputs are empty and the step summary carries the result.

## Permissions

`report` needs `contents: read`, `checks: read`, and `pull-requests: read`. `open` also needs `contents: write` and `pull-requests: write`. `start-gates: dispatch` needs `actions: write`. The runner needs `python3` and, unless `live-json` is set, `gh` on `PATH`. The current Ubuntu runners provide both. Do not add `setup-python`.

`siblings` means `lx-software-ltd/actions`, `evolvesprouts`, `findingalpha`, `lx-software`, and `siutindei`. The product workflow opens a batch for the calling repository. This repository's workflow reports all five. `report` works with any token that can read public repositories.

## Three ways to run it

A product workflow, on a schedule, with `github.token`. The owner merges the one pull request:

```yaml
      - uses: lx-software-ltd/actions/dependabot-batch@<40-hex> # main <yyyy-mm-dd>
        with:
          mode: open
          start-gates: dispatch
```

This repository, on a schedule. The job only reads:

```yaml
      - uses: lx-software-ltd/actions/dependabot-batch@<40-hex> # main <yyyy-mm-dd>
        with:
          mode: report
          repositories: siblings
```

A checkout, with `gh` signed in as the owner. The pull request is then the owner's, so the `pull_request` event starts the gates:

```sh
DEPENDABOT_BATCH_MODE=land DEPENDABOT_BATCH_REPOSITORIES=siblings python3 dependabot-batch/batch.py
```

`land` refuses when the token is `github.token`. A member that changes a workflow needs the `workflow` scope on that login and `exclude-paths` set to empty.

`open` does not update a batch branch. When the default branch moves, the owner clicks Update branch on the batch pull request. That click starts the gates as the owner.
