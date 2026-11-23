# dependency-graph

Build a dependency snapshot from pinned Python requirements and `package-lock.json`, then post it to the dependency submission API.

A `uses` line in a workflow or `action.yml` must name a 40-character commit. A tag such as `@v4` fails the run. Quotes around the value are ignored, and a reusable workflow path is accepted when its ref is a commit. Workflow uses are not submitted: GitHub already records the actions a workflow calls. Uses inside `action.yml` are submitted.

`submit` posts only when it is `true`. A pull request job stays at `contents: read` and does not post, so a branch snapshot does not replace the default-branch graph. `contents: write` belongs only on the job that runs for a push to `main`. In this repository that job runs the action from the checkout, so a pull request must not receive a write token. The caller passes `github.token` as `token` on the submit job.

An unpinned requirement or a use that is not a commit fails the run and nothing is posted. Each `ignore` path must match a manifest the scan would read. A path that matches nothing fails the run. `fixtures/` is not scanned. GitHub's automatic `update-pip-graph` job uses a different correlator and stays in place.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `root` | no | workspace | Directory scanned when `manifests` is empty. |
| `manifests` | no | empty | Newline-separated paths relative to `root`. |
| `ignore` | no | empty | Paths relative to `root` left out of the snapshot. A path that matches nothing fails the run. |
| `submit` | no | `false` | `true` posts the snapshot. |
| `token` | when submitting | empty | Token with contents write. |
| `snapshot-path` | no | empty | File that receives the snapshot JSON. |

## Permissions

`contents: read` on the pull request job. `contents: write` only on the push-to-`main` job that submits.
