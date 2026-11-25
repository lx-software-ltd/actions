# Setup Node

Sets up Node.js. `npm ci --no-audit --no-fund` runs only when `working-directory` is set and `install` is true. Audit stays in the caller's `security.yml`. The npm cache is off unless `cache` is `npm`.

The default `node-version` is `26`. Omit the input when that is the version the job should run.

A call site that today only runs `actions/setup-node` passes `node-version` and leaves `working-directory` and `cache` empty. A call site that caches and installs passes `cache: npm` and `working-directory`. `actions/setup-node` fails when `cache` is `npm` and the lockfile is not there. That failure is the fail fixture.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `node-version` | no | `26` | Passed to `actions/setup-node`. |
| `working-directory` | no | empty | Directory with `package.json` and `package-lock.json`. Empty skips `npm ci`. |
| `cache` | no | empty | `npm` caches that directory's `package-lock.json`. Empty does not cache. Any other value fails the action. |
| `install` | no | `true` | When `true` and `working-directory` is set, run `npm ci --no-audit --no-fund`. |

## Permissions

The calling job needs `contents: read`. The action does not call the GitHub API.

## Examples

Node only:

```yaml
      - uses: lx-software-ltd/actions/setup-node@<40-hex> # main <yyyy-mm-dd>
```

Cache and install:

```yaml
      - uses: lx-software-ltd/actions/setup-node@<40-hex> # main <yyyy-mm-dd>
        with:
          working-directory: apps/public_www
          cache: npm
```
