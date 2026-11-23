# CDK plan file

Zone: yellow. The note stays in this pull request.

`cdk-deploy` accepts `plan` or `plan-file`, the same JSON. `{NAME}` in `extra-args` is replaced from the environment. An empty value stays in the argument, so `Name={VAR}` becomes `Name=` and CloudFormation clears the parameter. A name that is not in the environment fails the deploy. The argument is not dropped.

`cdk-diff` reads that plan through `lib/cdk_plan.py`. It does not import `cdk-deploy`. Deploy-only extras stay off unless `include-extras` is true.

No product workflow calls this until the commit is on `main` and `bump_pins.py` moves the pin.
