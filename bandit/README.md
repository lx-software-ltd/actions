# Bandit

Installs Bandit and runs it on the caller's paths. `skip` is passed to `--skip`. `exclude` is passed to `--exclude`.

The caller runs `setup-python` first. This action installs with `python3 -m pip install` onto the Python that is on `PATH`.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `paths` | yes | | Space-separated paths. |
| `skip` | no | empty | Test ids to skip. |
| `root` | no | the workspace | Working directory. |
| `exclude` | no | empty | Comma-separated glob paths. Tests that sit beside the code go here. |

## Permissions

`contents: read`.
