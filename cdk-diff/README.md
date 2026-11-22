# CDK diff

Runs `npx --no-install cdk diff --no-color` in `working-directory`, then removes the account id from the log and the step summary. The step exits with the diff's own status. Diff lines are written as CDK prints them. A missing `package.json` prints a warning and does not run CDK. The step still succeeds, so a caller can skip a repository that has no CDK app.

`npm ci` has already installed `aws-cdk`. `--no-install` does not download a package. Building the app, acknowledging notices, and loading parameter files stay in the caller. Those steps differ by repository. Pass the resulting arguments in `args` or, when a value contains spaces, in a null-delimited `args-file`.

An empty `stacks` list passes no stack names, so CDK diffs every stack. A caller that always names stacks passes that list itself, including its default.

The account id comes from `secrets.AWS_ACCOUNT_ID`. A variable is printed in the step header before this action can mask it. An empty account id is left as-is and is not printed by this action.

Set `summary` to `false` to keep a caller that does not write a step summary. The log is still masked.

The same markdown is written to `$RUNNER_TEMP/cdk-diff-summary.md`. A later step can read that file. `GITHUB_STEP_SUMMARY` belongs to the step that writes it.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | yes | | CDK app directory. |
| `stacks` | no | empty | Stack names. Empty diffs every stack. |
| `args` | no | empty | Extra arguments, split on whitespace. |
| `args-file` | no | empty | Null-delimited arguments. Wins over `args`. |
| `account-id` | yes | | `secrets.AWS_ACCOUNT_ID`. Stripped from the output. |
| `summary` | no | `true` | Write the masked diff to the step summary. |

## Example

```yaml
- uses: lx-software-ltd/actions/cdk-diff@<sha> # main <yyyy-mm-dd>
  with:
    working-directory: backend/infrastructure
    stacks: ${{ steps.prep.outputs.stacks }}
    args-file: ${{ runner.temp }}/cdk-diff-args
    account-id: ${{ secrets.AWS_ACCOUNT_ID }}
```
