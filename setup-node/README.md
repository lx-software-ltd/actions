# Setup Node

Sets up Node.js with the npm cache, then runs `npm ci` in `working-directory`.

The default `node-version` is `26`, the organisation major. A caller passes the version that repository uses today. Changing a repository onto 26 is its own C04 pull request, not a silent default.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `node-version` | no | `26` | Passed to `actions/setup-node`. |
| `working-directory` | yes | | Directory with `package.json` and `package-lock.json`. |
| `install` | no | `true` | When `true`, run `npm ci` in that directory. |

## Permissions

The calling job needs `contents: read`. The action does not call the GitHub API.

## Example

```yaml
      - uses: lx-software-ltd/actions/setup-node@<40-hex> # main <yyyy-mm-dd>
        with:
          node-version: "lts/*"
          working-directory: apps/public_www
```
