# CDK deploy

Deploys the stacks named in `plan`. The job needs AWS credentials already, from `aws-oidc`. This action does not request a token, does not bootstrap, and does not read an account id.

`format` is `prefixed-json` or `plain-json`. An empty `param-file` skips the file. A set path that is not a file fails. `prefixed-json` rejects a key whose prefix is not declared on a group. Empty values are omitted unless the name is in `pass-empty`.

`plan` and `plan-file` are the same JSON. Set one. `{NAME}` in `extra-args` is replaced from the environment. An empty value stays in the argument, including `Name=`, so CloudFormation clears the previous parameter. The argument is not dropped.

`plan.groups` is the deploy order. Each group is one `cdk deploy`. `prefixes` choose prefixed keys. `routes` and `api-stack` choose plain-json stacks, and a name in `also-api` is also sent to `api-stack`. `extra-args` are the caller's extra `--parameters` flags. `when-all-env` skips the group unless every named variable is set. `allowlist-env` checks a comma-separated email list and reports the entry position, not the address. `append-if-set` adds one parameter only when that variable is non-empty.

`attempts` defaults to 1. A log line matching `HandlerErrorCode: InvalidRequest`, `HandlerErrorCode: AlreadyExists`, `must be in ARN format or "*"`, or `already exists.` fails immediately. Otherwise the action waits `45 * attempt` seconds. `rollback-match` triggers `continue-update-rollback` before the next try. `skip-resource` is empty except where a failed migration resource must be skipped; a failed rollback then fails the job.

`destroy: true` runs `cdk destroy --force` on the selected stacks first. `run-seed: true` sets `RunSeedData=true` on `api-stack` only. `--qualifier` is not passed. `--no-notices` is off unless `no-notices` is true.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | yes | | CDK app directory. |
| `plan` | no | empty | JSON deploy order and routing. Set this or `plan-file`. |
| `plan-file` | no | empty | Path to that JSON. |
| `param-file` | no | empty | Parameters file. Empty skips it. |
| `format` | no | `prefixed-json` | File shape. |
| `stacks` | no | empty | Subset of the plan. Empty deploys every named stack. |
| `attempts` | no | `1` | Tries per group. |
| `no-notices` | no | `false` | Pass `--no-notices`. |
| `pass-empty` | no | empty | Names sent when the value is empty. |
| `escape-newlines` | no | `false` | Escape newlines in plain-json values. |
| `rollback-match` | no | `is in UPDATE_ROLLBACK_FAILED state and can not be updated` | Log text that starts rollback recovery. |
| `skip-resource` | no | empty | Resource skipped once during rollback. |
| `destroy` | no | `false` | Destroy the selected stacks first. |
| `run-seed` | no | `false` | Force `RunSeedData=true` on `api-stack`. |
| `region` | no | empty | Region for rollback calls. |

## Example

```yaml
- uses: lx-software-ltd/actions/cdk-deploy@<sha> # main <yyyy-mm-dd>
  with:
    working-directory: backend/infrastructure
    format: prefixed-json
    param-file: ${{ vars.CDK_PARAM_FILE }}
    plan: |
      {"groups":[{"stacks":["example","example-admin-web"],"prefixes":["example:","example-admin-web:"]}]}
```
