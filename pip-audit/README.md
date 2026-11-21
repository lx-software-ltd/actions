# pip-audit

Installs `pip-audit` and audits each requirements file. Advisory ids in `ignore-vulns` are passed to `--ignore-vuln`.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `requirements` | yes | | Newline-separated requirements files. |
| `ignore-vulns` | no | empty | Advisory ids to ignore. |

## Permissions

`contents: read`. The audit reaches PyPI.
