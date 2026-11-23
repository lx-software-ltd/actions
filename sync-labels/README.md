# Sync labels

Creates and updates the shared issue labels. A label that is not in the catalogue stays on the repository.

The catalogue is `labels.json` in this action. It is the GitHub defaults plus `dependencies`, `ci`, `infrastructure`, and `mobile`. Colour and description follow the value already shared by the product repositories. `mobile` is `0e8a16`, "Flutter app". `dependencies` and `ci` are the labels Dependabot is configured to apply.

`siblings` means `lx-software-ltd/actions`, `evolvesprouts`, `findingalpha`, `lx-software`, and `siutindei`.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `token` | no | empty | Token that can write issues on each target. `github.token` writes the calling repository. Ignored when `live-json` is set. |
| `mode` | no | `check` | `check` fails on drift and does not write. `apply` writes. |
| `repositories` | no | the calling repository | Space-separated `owner/repo`, or `siblings`. |
| `labels-json` | no | the bundled catalogue | Catalogue array for a fixture. |
| `live-json` | no | empty | Current labels for a fixture. `check` only. The action does not call GitHub. |

## Permissions

The calling job needs `contents: read`. `apply` also needs `issues: write` on each target repository. `github.token` can write labels on the repository that is running the workflow. Writing the other four repositories needs a token that can write issues on each of them. The runner needs `python3` and, unless `live-json` is set, `gh` on `PATH`. The current Ubuntu runners provide both. Do not add `setup-python`.

## Example

```yaml
      - uses: lx-software-ltd/actions/sync-labels@<40-hex> # main <yyyy-mm-dd>
        with:
          token: ${{ github.token }}
          mode: apply
```

From a checkout of this repository, with `gh` authenticated for every target:

```sh
SYNC_LABELS_MODE=apply SYNC_LABELS_REPOSITORIES=siblings python3 sync-labels/sync_labels.py
```

`SYNC_LABELS_MODE=check` prints the drift and exits 1.
