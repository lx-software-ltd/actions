# PII denylist

Fails when tracked source matches the organisation SHA-256 denylist, plus any extra digests the caller supplies. A hit is printed as a path and line number. The matched text is not printed.

The calling job needs `python3` on `PATH` and a checkout. The action does not install Python. `ubuntu-26.04` provides it.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `denylist-path` | no | `scripts/pii-denylist.sha256` | Extra digests, added to the organisation list. Relative paths are resolved from `root`. The default path is optional. Any other path must exist. |
| `root` | no | the workspace | Directory whose tracked files are scanned. |

The organisation list is `scripts/pii-denylist.sha256` in this action's checkout. A missing organisation file fails. An empty organisation file passes and checks nothing. A missing default product file adds nothing.

## Permissions

The calling job needs `contents: read` for the checkout. The action does not call the GitHub API.

## Example

```yaml
  pii-denylist:
    name: PII denylist
    runs-on: ubuntu-26.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: lx-software-ltd/actions/pii-denylist@<40-hex> # main YYYY-MM-DD
```

Pin the same commit as the repository's other `lx-software-ltd/actions` references.
