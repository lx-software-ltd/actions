# PII denylist

Fails when tracked source matches a SHA-256 denylist of personal data. A hit is printed as a path and line number. The matched text is not printed.

The calling job needs `python3` on `PATH` and a checkout. The action does not install Python. `ubuntu-26.04` provides it.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `denylist-path` | no | `scripts/pii-denylist.sha256` | Hash list. Relative paths are resolved from `root`. |
| `root` | no | the workspace | Directory whose tracked files are scanned. |

An empty hash list passes and checks nothing. A missing file fails.

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
