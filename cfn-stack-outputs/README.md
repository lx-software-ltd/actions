# CloudFormation stack outputs

Reads named outputs from one stack into the `json` step output. A composite action cannot declare a separate output for each key, so the caller parses `json`.

The job needs AWS credentials already, from `aws-oidc`. This action does not request a token and does not change the stack. A 12-digit account id in an AWS error is replaced with `***` before it is printed. Output values are written only to the step output.

An empty value is treated as missing. Checks that belong to one caller, such as requiring `https://`, stay in that caller.

## Inputs

| Input | Required | Meaning |
| --- | --- | --- |
| `stack` | yes | CloudFormation stack name. |
| `outputs` | yes | Keys, separated by spaces or commas. |
| `region` | yes | AWS region. The caller passes `vars.AWS_REGION`. |

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
