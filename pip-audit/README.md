# pip-audit

Installs `pip-audit` and audits each requirements file. Advisory ids in `ignore-vulns` are passed to `--ignore-vuln`.

The caller runs `setup-python` first. This action installs with `python3 -m pip install` onto the Python that is on `PATH`.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `requirements` | yes | | Newline-separated requirements files. |
| `ignore-vulns` | no | empty | Advisory ids to ignore. |
| `report-path` | no | empty | Also write the audit output to this file. |

## Permissions

`contents: read`. The audit reaches PyPI.
