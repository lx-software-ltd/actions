# CDK bootstrap

Runs `cdk bootstrap` for the account and region the caller passes. The caller has already run `aws-oidc` and `setup-node`. This action does not call another action, and it does not read `secrets` or `vars`.

It checks that the account id is 12 digits and that the region is an AWS region name. The error does not include the account id. `::add-mask::` covers later log lines, and the command output is redacted before it is printed. `npm ci` and `cdk bootstrap` hold their output until that command finishes, so a long run shows no live log. Bootstrap is a manual workflow, so the delay is acceptable.

An empty qualifier omits `--qualifier`. CDK then uses `hnb659fds`. A set qualifier is passed through.

`cdk-bootstrap-check` is the other action. It only reads the SSM version. Deploys keep using that check. This action is the manual bootstrap workflow.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | yes | | Directory that contains `package.json`. |
| `account-id` | yes | | `secrets.AWS_ACCOUNT_ID`. |
| `region` | yes | | `vars.AWS_REGION`. |
| `qualifier` | no | empty | `vars.CDK_BOOTSTRAP_QUALIFIER`. Empty omits the flag. |

## Example

```yaml
- uses: lx-software-ltd/actions/setup-node@<sha> # main <yyyy-mm-dd>
  with:
    cache: npm
    working-directory: backend/infrastructure
    install: "false"

- uses: lx-software-ltd/actions/cdk-bootstrap@<sha> # main <yyyy-mm-dd>
  with:
    working-directory: backend/infrastructure
    account-id: ${{ secrets.AWS_ACCOUNT_ID }}
    region: ${{ vars.AWS_REGION }}
    qualifier: ${{ vars.CDK_BOOTSTRAP_QUALIFIER }}
```
