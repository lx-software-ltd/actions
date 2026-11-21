# Python requirements pins

Fails when a requirement line does not contain `==`. Lines that start with `-r` or `--requirement` are followed. An include that leaves the directory of the starting file, or a cycle, is a failure.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `files` | yes | | Newline-separated requirements files. |

## Permissions

`contents: read`. No token calls.
