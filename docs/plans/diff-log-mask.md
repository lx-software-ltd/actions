# Mask addresses in a CDK diff

Zone: yellow. The note stays in the pull request so the change can be reviewed.

`cdk diff` prints parameter values. A public repository's log is public. Mask an email address in the log and the step summary, the same way the account id is masked. Other parameter values stay visible, because the diff is how a reviewer sees a change.

The workflow step that refuses `GitHubActionsRole` on a pull request is not the control. A pull request can edit that step. The control is the role's trust policy, and this repository cannot change it.
