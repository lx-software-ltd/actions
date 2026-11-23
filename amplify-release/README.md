# Amplify release

Starts an Amplify `RELEASE` job. `mode: promote` first requires the latest job on `source-branch` to be `SUCCEED`, and by default only `staging` may promote to `main`.

The job needs AWS credentials already, from `aws-oidc`. This action does not request a token.

`wait` defaults to true, so a failed Amplify job fails the step. The current deploy and promote workflows do not wait. They pass `wait: false` and keep that behaviour.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `app-id` | yes | | Amplify app id. |
| `branch` | yes | | Branch that receives the RELEASE job. |
| `mode` | no | `release` | `release` or `promote`. |
| `source-branch` | no | empty | Required when `mode` is `promote`. |
| `wait` | no | `true` | Poll until the job finishes. |
| `allowed-source` | no | `staging` | Promote source name. Empty skips the check. |
| `allowed-target` | no | `main` | Promote target name. Empty skips the check. |

## Example

```yaml
- uses: lx-software-ltd/actions/amplify-release@<sha> # main <yyyy-mm-dd>
  with:
    app-id: ${{ vars.AMPLIFY_APP_ID }}
    branch: ${{ vars.AMPLIFY_BRANCH }}
    mode: release
    wait: "false"
```
