# CDK bootstrap check

Reads `/cdk-bootstrap/<qualifier>/version` from SSM. A missing parameter or a denied read fails the step and prints where to look. The account id is not an input and is not printed.

This check does not run `cdk bootstrap`. Creating the bootstrap stack stays in the manual `cdk-bootstrap` workflow.

The job needs AWS credentials already, from `aws-oidc`. This action does not request a token.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `qualifier` | no | `hnb659fds` | Bootstrap qualifier. The caller passes `vars.CDK_BOOTSTRAP_QUALIFIER`. |
| `region` | yes | | AWS region. The caller passes `vars.AWS_REGION`. |

## Example

```yaml
- uses: lx-software-ltd/actions/cdk-bootstrap-check@<sha> # main <yyyy-mm-dd>
  with:
    qualifier: ${{ vars.CDK_BOOTSTRAP_QUALIFIER }}
    region: ${{ vars.AWS_REGION }}
```
