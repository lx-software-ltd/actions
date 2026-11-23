# CDK deploy

How `cdk-deploy` turns a parameters file and a plan into `cdk deploy` commands. The action does not assume a role, and it does not print an account id, a parameter value, or a secret.

## Goal

One action deploys the selected stacks from a parameters file, retries a failed deploy, and recovers `UPDATE_ROLLBACK_FAILED`. Each repository passes an input where its current deploy differs. A missing input must not change that repository's accept or reject rules.

The action does not assume a role. The caller has already run `aws-oidc`. It does not print an account id, a parameter value, or a secret. Fixture jobs in `actions` stub `aws` and `npx` and do not deploy.

## Parameters file

Two file shapes exist. The action accepts both. `format` selects the shape. The default is `prefixed-json`, which is what `findingalpha` and `lx-software` use.

`prefixed-json` is a JSON object. Each key is `stack:ParameterName`, or a key with no colon when the plan sets `unprefixed-prefix`. lx-software sets `unprefixed-prefix` to `lxsoftware-public-www:`, which is what `scripts/deploy/cdk-params.sh` does with `PublicWebsiteDomainName` and `PublicWebsiteCertificateArn`. Any other prefix is rejected. A `<FROM_GITHUB_SECRET: NAME>` or `<FROM_GITHUB_VAR: NAME>` value reads that environment variable. Values are strings or numbers. Null and empty strings are omitted. Newlines in a value become the two characters `\n`. The caller passes `CDK_PARAM_FILE`. A set variable that does not point at a file fails the deploy. An empty variable skips the file, which is what both pair A workflows do today.

`plain-json` is the pair B file (`vars.CDK_PARAM_FILE`, usually `backend/infrastructure/params/production.json`). Keys are parameter names with no stack prefix. A value may be a plain string or a placeholder:

- `<FROM_GITHUB_SECRET: ENV_NAME>` reads that environment variable.
- `<FROM_GITHUB_VAR: ENV_NAME>` reads that environment variable.

The workflow still maps the GitHub secret or variable into the environment. The file names the variable. It does not contain the secret. An unknown placeholder is passed through unchanged. `escape-newlines: false` leaves a resolved value unchanged, including its newlines. That is the evolvesprouts script. `siutindei` passes true, and newlines become the two characters `\n`.

## Routing a parameter to a stack

`{NAME}` in `extra-args` is replaced from the environment. An empty value stays, so `Name={VAR}` becomes `Name=` and CloudFormation clears the parameter. A variable that is not set fails the deploy, so a typo or a missing `env` line does not clear the parameter. Dropping the argument would keep the previously deployed value. An explicit empty value is what the findingalpha builder did when it always passed `Name=`.

`findingalpha` splits the prefixed file into three argv lists by key prefix: `findingalpha:`, `findingalpha-admin-web:`, and `findingalpha-public-www:`. It then deploys `findingalpha` and `findingalpha-admin-web` together, and deploys `findingalpha-public-www` only when both the domain and the certificate variable are set. Extra `--parameters` flags in the workflow override or add the domain, Google, mail, API, Cognito, and WAF values. Those flags stay caller inputs (`extra-args`), because they are not in the file.

`lx-software` uses the same prefixed file. It deploys `lxsoftware-public-www` first, with only that stack's parameters. It then checks the email allow-list and, only when `SIUTINDEI_BOARD_META_VERIFY_TOKEN` is non-empty, appends `lxsoftware:SiutindeiBoardMetaVerifyToken`. An empty secret must not be sent, so CloudFormation keeps the previous token. The admin stacks (`lxsoftware`, `lxsoftware-admin-web`) deploy second, without `--exclusively`. The allow-list check and the public-first order stay caller inputs: `order` and `allowlist`.

Pair B routes by parameter name, not by key prefix. A name in the admin set goes to the admin stack, a name in the public set goes to the public stack, and a name in both goes to both. Anything else goes to the API stack. `PublicWwwOriginVerifySecret` also goes to the API stack. `evolvesprouts` adds the training set and copies the four domain names onto the API stack for CORS. `siutindei` does not have a training stack.

Empty values are omitted, except the names in `pass-empty`. Sending an empty string is what clears a previous stack value. Omitting it leaves the previous value.

| Repository | `pass-empty` |
| --- | --- |
| `findingalpha`, `lx-software` | none. Empty strings are omitted. |
| `evolvesprouts` | `WafWebAclArn` and the four edge-verify secrets. An empty edge-verify secret must be able to turn the origin lock off. |
| `siutindei` | `WafWebAclArn`, `CognitoCustomDomainName`, `CognitoCustomDomainCertificateArn`, `ApiCustomDomainName`, `ApiCustomDomainCertificateArn`, `SearchAreaScope`. |

`run_seed_data: true` on a workflow dispatch replaces `RunSeedData` on the API stack only. The default is false. `siutindei` can also destroy the selected stacks before deploy when `destroy_before_deploy` is true. The other three do not. The action input `destroy` defaults false, and only `siutindei` passes true.

## Retry and recovery

Pair A deploys once. There is no retry and no rollback recovery. The action input `attempts` defaults to 1 so pair A stays a single `cdk deploy`.

Pair B uses three attempts. A log line matching `HandlerErrorCode: InvalidRequest`, `HandlerErrorCode: AlreadyExists`, `must be in ARN format or "*"`, or `already exists.` fails immediately. Otherwise it waits `45 * attempt` seconds and tries again.

Before a retry, a stack in `UPDATE_ROLLBACK_FAILED` gets `continue-update-rollback`, then `aws cloudformation wait stack-rollback-complete`.

`evolvesprouts` looks for `is in UPDATE_ROLLBACK_FAILED state and can not be updated`. A failed continue or a failed wait is logged and the loop continues. It does not skip a resource. After a green deploy of `evolvesprouts-public-www` it still runs `report_public_www_edge_verify.sh`. That report stays in the caller.

`siutindei` looks for `UPDATE_ROLLBACK_FAILED` anywhere in the attempt log. A failed continue fails the job. It also retries `continue-update-rollback` once with `--resources-to-skip RunMigrations` when that resource is in `UPDATE_FAILED` or `UPDATE_ROLLBACK_FAILED`, or the recent events mention `Can't locate revision` or `did not finish`. The other repositories do not skip a resource. The action input `skip-resource` is empty except for `siutindei`, which passes `RunMigrations`.

`cdk deploy` is `npx cdk deploy --require-approval never`. Pair B also passes `--no-notices`. Pair A does not. The input `no-notices` defaults false, and pair B passes true. Neither pair passes `--qualifier` on deploy. The qualifier stays in the environment for the CDK app.

## What each repository passes

| Input | findingalpha | lx-software | evolvesprouts | siutindei |
| --- | --- | --- | --- | --- |
| `format` | `prefixed-json` | `prefixed-json` | `plain-json` | `plain-json` |
| `attempts` | 1 | 1 | 3 | 3 |
| `no-notices` | false | false | true | true |
| `pass-empty` | empty | empty | the edge-verify set | the domain and search set |
| `skip-resource` | empty | empty | empty | `RunMigrations` |
| `destroy` | false | false | false | the workflow input |

Stack names, the parameter-to-stack sets, and the extra `--parameters` flags stay caller inputs. The action does not hard-code a repository name.
