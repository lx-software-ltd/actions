# AWS OIDC

Masks the account id, checks that the account id and region are set, and assumes an IAM role with `aws-actions/configure-aws-credentials`. The session name is `GitHubActions-<run id>`.

The action cannot read `secrets` or `vars`. The caller passes them as inputs.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `account-id` | yes | | Account id. Pass `secrets.AWS_ACCOUNT_ID \|\| vars.AWS_ACCOUNT_ID`. Masked before the role is assumed. |
| `region` | yes | | Region. Pass `vars.AWS_REGION`. |
| `role-name` | no | `GitHubActionsRole` | Role in that account. |
| `required` | no | `true` | `false` sets `ready` to false and warns when the account id or region is empty. `true` fails the step. |
| `subject` | no | empty | When set, must be the ID form `repo:<org>@<org-id>/<repo>@<repo-id>:...`. The name form `repo:<org>/<repo>:...` fails the step. Empty skips the check. |

## Outputs

| Output | Meaning |
| --- | --- |
| `ready` | `true` when the assume step ran. `false` when `required` is false and a setting is missing. |

## Permissions

The calling job needs `id-token: write` and `contents: read` when `ready` will be true. A job that only takes the skip path does not request a token. This repository's own workflows do not call the assume step.

## Example

Pin a commit that is on `main`.

```yaml
permissions:
  contents: read
  id-token: write

jobs:
  diff:
    runs-on: ubuntu-26.04
    steps:
      - uses: lx-software-ltd/actions/aws-oidc@<40-hex> # main <yyyy-mm-dd>
        id: aws
        with:
          account-id: ${{ secrets.AWS_ACCOUNT_ID || vars.AWS_ACCOUNT_ID }}
          region: ${{ vars.AWS_REGION }}
          required: "false"
          subject: repo:<org>@<org-id>/<repo>@<repo-id>:*
```

Later steps that need credentials use `if: steps.aws.outputs.ready == 'true'`.
