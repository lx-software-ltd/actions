# Setup Node

Sets up Node.js. `npm ci` runs only when `working-directory` is set and `install` is true. The npm cache is off unless `cache` is `npm`.

The default `node-version` is `26`, the organisation major. A caller passes the version that repository uses today. Changing a repository onto 26 is its own C04 pull request, not a silent default.

A call site that today only runs `actions/setup-node` passes `node-version` and leaves `working-directory` and `cache` empty. A call site that caches and installs passes `cache: npm` and `working-directory`. `actions/setup-node` fails when `cache` is `npm` and the lockfile is not there. That failure is the fail fixture.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `node-version` | no | `26` | Passed to `actions/setup-node`. |
| `working-directory` | no | empty | Directory with `package.json` and `package-lock.json`. Empty skips `npm ci`. |
| `cache` | no | empty | `npm` caches that directory's `package-lock.json`. Empty does not cache. |
| `install` | no | `true` | When `true` and `working-directory` is set, run `npm ci`. |

## Permissions

The calling job needs `contents: read`. The action does not call the GitHub API.

## Examples

Node only, which is what `findingalpha` `check-lockfiles.yml` and the `siutindei` harness job do today:

```yaml
      - uses: lx-software-ltd/actions/setup-node@<40-hex> # main <yyyy-mm-dd>
        with:
          node-version: "22"
```

Cache and install:

```yaml
      - uses: lx-software-ltd/actions/setup-node@<40-hex> # main <yyyy-mm-dd>
        with:
          node-version: "lts/*"
          working-directory: apps/public_www
          cache: npm
```
