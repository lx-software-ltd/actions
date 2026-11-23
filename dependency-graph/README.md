# dependency-graph

Build a dependency snapshot from pinned Python requirements, `package-lock.json`, and pinned `uses:` lines, then post it to the dependency submission API.

`submit` posts only when it is `true`. A pull request leaves it false so a branch snapshot does not replace the default-branch graph. The job that submits needs `contents: write`. The caller passes `github.token` as `token`.

An unpinned requirement or action fails the run and nothing is posted. `fixtures/` is not scanned. GitHub's automatic `update-pip-graph` job uses a different correlator and stays in place.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `root` | no | workspace | Directory scanned when `manifests` is empty. |
| `manifests` | no | empty | Newline-separated paths relative to `root`. |
| `submit` | no | `false` | `true` posts the snapshot. |
| `token` | when submitting | empty | Token with contents write. |
| `snapshot-path` | no | empty | File that receives the snapshot JSON. |

## Permissions

`contents: read` to build the snapshot. `contents: write` on the job that submits.
