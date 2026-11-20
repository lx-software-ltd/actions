# Setup Python

Sets up Python. When `requirements` is set, pip is cached against that file.

The default `python-version` is `3.12`. A caller passes the version that repository uses today. `siutindei`'s 3.13 jobs move on their C05 pull request, not by omitting this input before that pull request.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `python-version` | no | `3.12` | Passed to `actions/setup-python`. |
| `requirements` | no | empty | Requirements file for the pip cache. Empty skips the cache. |

## Permissions

The calling job needs `contents: read`. The action does not call the GitHub API. It does not need `python3` to be installed already. `actions/setup-python` provides it.

## Example

```yaml
      - uses: lx-software-ltd/actions/setup-python@<40-hex> # main <yyyy-mm-dd>
        with:
          python-version: "3.12"
          requirements: backend/lambda/requirements.txt
```
