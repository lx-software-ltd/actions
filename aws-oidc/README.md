# AWS OIDC

Checks the account id and region, reads the job's OIDC token, and assumes an IAM role with `aws-actions/configure-aws-credentials`. The session name is `GitHubActions-<run id>`.

The action cannot read `secrets` or `vars`. The caller passes them as inputs.

Pass the account id from a secret: `secrets.AWS_ACCOUNT_ID`. GitHub masks a secret in the step header. `::add-mask::` then covers later log lines. Do not pass it from a variable, and do not write `secrets.AWS_ACCOUNT_ID || vars.AWS_ACCOUNT_ID`. A variable is printed in the step header before the mask command runs. AWS does not treat an account id as a credential, but this repository's workflows stay public, so the value belongs in a secret.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `account-id` | yes | | Account id. Pass `secrets.AWS_ACCOUNT_ID`. |
| `region` | yes | | Region. Pass `vars.AWS_REGION`. |
| `role-name` | no | `GitHubActionsRole` | Role in that account. |
| `required` | no | `true` | `false` sets `ready` to false and warns when the account id or region is empty. `true` fails the step. |

There is no subject input. When the account and region are set, the action requests the job token and reads its `sub` claim. The claim must be the ID form `repo:<org>@<org-id>/<repo>@<repo-id>:<claim>`. The name form fails, and so does a trust-policy pattern such as `*`. The error prints the token's `sub`.

## Outputs

| Output | Meaning |
| --- | --- |
| `ready` | `true` when the account, region, and token subject were accepted. The assume step runs after that. A failed assumption fails the job. `false` when `required` is false and a setting is missing. |

## Permissions

The calling job needs `id-token: write` and `contents: read` when the account and region are set. A job that only takes the skip path does not request a token. This repository's own workflows do not call the assume step.

## Example

Pin a commit that is on `main`. The comment is `# main <yyyy-mm-dd>`.

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
          account-id: ${{ secrets.AWS_ACCOUNT_ID }}
          region: ${{ vars.AWS_REGION }}
          required: "false"
```

Later steps that need credentials use `if: steps.aws.outputs.ready == 'true'`.
