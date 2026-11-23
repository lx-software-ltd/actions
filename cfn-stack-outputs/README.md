# CloudFormation stack outputs

Reads named outputs from one stack into the `json` step output. A composite action cannot declare a separate output for each key, so the caller parses `json`.

The job needs AWS credentials already, from `aws-oidc`. This action does not request a token and does not change the stack. A 12-digit account id in an AWS error is replaced with `***` before it is printed. Output values are written only to the step output.

An empty required value is treated as missing. An `optional` key that is missing or empty becomes `""`. `allow-missing: true` is for a stack that may not exist: the AWS error must say `does not exist`, and the action then sets `present` to `false` and `json` to `{}`. Access denied still fails. Checks that belong to one caller, such as requiring `https://`, stay in that caller.

Read `json` in a later step of the same job. Do not pass it to a job output. GitHub drops a job output that contains a secret, and the next job receives an empty value. The account id is a repository secret. A stack output such as an ARN contains that account id, so the whole job output is dropped. A step output used in the same job is not dropped.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `stack` | yes | | CloudFormation stack name. |
| `outputs` | no | empty | Required keys, separated by spaces or commas. |
| `optional` | no | empty | Keys that become `""` when missing or empty. |
| `allow-missing` | no | `false` | `true` writes `present=false` when the stack does not exist. |
| `region` | yes | | AWS region. The caller passes `vars.AWS_REGION`. |

`present` is `true` when the stack exists and `false` when `allow-missing` accepted a missing stack.

## Example

```yaml
- id: settings
  uses: lx-software-ltd/actions/cfn-stack-outputs@<sha> # main <yyyy-mm-dd>
  with:
    stack: findingalpha
    outputs: UserPoolClientId CognitoDomain AdminApiBaseUrl
    region: ${{ vars.AWS_REGION }}
```

`steps.settings.outputs.json` is an object of those three keys.
