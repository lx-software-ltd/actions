const cdk = require("aws-cdk-lib");

const app = new cdk.App();
const stack = new cdk.Stack(app, "ParamStack", {
  env: { account: "123456789012", region: "us-east-1" },
  synthesizer: new cdk.LegacyStackSynthesizer(),
});
new cdk.CfnParameter(stack, "Name", {
  type: "String",
  default: "from-default",
});
app.synth();
