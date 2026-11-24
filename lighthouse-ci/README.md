# Lighthouse CI

Writes the runtime config under `RUNNER_TEMP`, outside the workspace, then installs `@lhci/cli` there and runs `lhci autorun`. The caller builds the site first. This action does not read `vars`. When `bypass-secret` is set, the runtime config sets `ci.upload.target` to `filesystem`, so autorun does not send the report to temporary-public-storage while the request header is in the result. After the run it deletes that config and removes `x-staging-bypass` from `.lighthouseci`.

The install replaces `chrome-launcher` 0.13.4 with 0.15.2, `tmp` 0.1.0 with 0.2.4, and `uuid` 8.3.2 with 11.1.1. Those are the ranges that pull `inflight` 1, `glob` 7, `rimraf` 2 and 3, and `uuid` 8. Lighthouse keeps its own `chrome-launcher` 1.x. `lhci autorun` still calls `require('chrome-launcher').Launcher`, `uuid.v4()`, and `tmp.fileSync`.

A path becomes `http://localhost:<port><path>`. A value that already starts with `http://` or `https://` is kept. `dry-run: true` writes the config and does not start Lighthouse.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | yes | | Config and build directory. |
| `config` | no | `.lighthouserc.json` | Base config. |
| `page-paths` | no | empty | Paths or URLs. Empty uses `default-paths`. |
| `default-paths` | no | `/` | Fallback page list. |
| `port` | no | `9000` | Port for a relative path. |
| `lhci-version` | no | `0.15.1` | `@lhci/cli` version. |
| `github-token` | no | empty | Passed as `LHCI_GITHUB_TOKEN`. |
| `dry-run` | no | `false` | Write the config only. |

## Example

```yaml
- uses: lx-software-ltd/actions/lighthouse-ci@<sha> # main <yyyy-mm-dd>
  with:
    working-directory: apps/public_www
    page-paths: ${{ inputs.page_paths }}
    default-paths: /,/about,/privacy
    github-token: ${{ secrets.GITHUB_TOKEN }}
```
