# Lighthouse CI

Writes the runtime config under `RUNNER_TEMP`, outside the workspace, then runs `npx --yes @lhci/cli@<version> autorun`. The caller builds the site first. This action does not read `vars`. When `bypass-secret` is set, the runtime config sets `ci.upload.target` to `filesystem`, so autorun does not send the report to temporary-public-storage while the request header is in the result. After the run it deletes that config and removes `x-staging-bypass` from `.lighthouseci`.

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
