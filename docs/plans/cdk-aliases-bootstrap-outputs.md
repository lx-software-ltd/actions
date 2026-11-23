# CDK aliases, bootstrap, and optional stack outputs

Yellow. `lib/cdk_plan.py`, `cdk-deploy`, `cdk-diff`, a new `cdk-bootstrap` action, `cfn-stack-outputs`, and `lib/stack_outputs.py`.

## Aliases

A plan may set `aliases`, an object whose values are lists of stack names. The whole `stacks` string is one alias when it matches, so a label with spaces is not split first. Otherwise each comma-separated token is an alias or a list of stack names. Empty `stacks` still means every stack in `groups`. Both actions resolve the same way. `cdk-diff` without a plan keeps the comma and whitespace split.

## Bootstrap

`cdk-bootstrap` takes a working directory, account id, region, and qualifier. It runs `npm ci`, `npm run build --if-present`, and `npx cdk bootstrap` with the optional qualifier. It checks the account id and region without printing the account id. The caller has already run `aws-oidc` and `setup-node`.

## Stack outputs

`optional` keys are empty when missing. `allow-missing: true` writes `present=false` and `{}` when the stack does not exist. Access denied still fails. Existing callers keep the required-key failure.

## Omitted parameters

A fixture runs `aws-cdk` 2.1148.1 against a local CloudFormation stand-in. The default diff builds a change set and does not send `UsePreviousValue` for an omitted parameter. A template default is then what CloudFormation applies, and a parameter with no default fails the diff. Deploy still keeps the previous value. Callers pass the same explicit parameters to both.
