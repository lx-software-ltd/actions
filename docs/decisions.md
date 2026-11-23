# Decisions

What still binds. The route that got here is in git history.

## Pins

Callers pin one full commit SHA of this repository. A product repository uses one SHA. The pre-commit `rev` for this repository equals that SHA. The same workflow line carries `# main YYYY-MM-DD`, and that commit is on `main`.

`scripts/bump_pins.py` rewrites the workflow pins, that date comment, and the pre-commit `rev` in a product checkout. It refuses a SHA that is not contained in `main`. Conformance fails when the pins differ, so a bump is one command and one pull request per product repository.

The `lint`, `test`, and `security-summary` gates in this repository pin `lx-software-ltd/actions/require-jobs` at `1a3cca7c38163f8164c262323601c34a4df5b7a4` (`# main 2026-11-20`). They must not use `uses: ./require-jobs`. A local action is loaded from the pull request. Fixture jobs may use `uses: ./require-jobs`.

No `v*` tag. `release-tags` blocks update and deletion. `release-tags-create` blocks creation. Organization admin is on the bypass list of `release-tags-create` and is the actor who can create a tag. Tags are worth adding only if Dependabot should open the bump pull requests. The bump script comes first. Dependabot has not moved an actions pin, and a cooldown exclusion for this repository is not a measured result.

## Rulesets

Three organisation rulesets apply here and in the four product repositories.

| Ruleset | What it requires |
| --- | --- |
| `main-protection` | Pull request, exactly 0 approving reviews, deletion and force-push blocked, required checks exactly `lint`, `test`, and `security-summary`. |
| `release-tags` | Update and deletion blocked on `refs/tags/v*`. |
| `release-tags-create` | Creation blocked on `refs/tags/v*`. Organization admin can bypass. |

## Gates

Gate jobs stay in the caller. The job ids are `lint`, `test`, and `security-summary`. A gate has `if: always()`, lists every other job in that file under `needs`, and fails unless those jobs succeeded. A skipped job is a failure. `require-jobs` has no skip allowance.

`workflow-conformance` defaults to `enforce`. All four product repositories run `enforce`.

## Versions and credentials

Node is major version 26. Python is 3.12. Linux jobs use `ubuntu-26.04`. macOS jobs use `macos-26`.

`AWS_ACCOUNT_ID` is a repository secret. Callers pass `secrets.AWS_ACCOUNT_ID` only. An action cannot read `secrets` or `vars`. The account id is not written in this repository.

## Deploy

`evolvesprouts` and `siutindei` must not run `cdk bootstrap` on every backend deploy. Bootstrap rewrites the CDK output, including zip timestamps, before the asset hash, so the next deploy updates every Lambda. Bootstrap stays in the manual `cdk-bootstrap.yml`. A deploy uses `cdk-bootstrap-check`, which reads the SSM version and does not bootstrap. A CDK upgrade that needs a newer bootstrap stack fails the deploy until someone runs that manual workflow. That failure is the intended trade-off.

A pull request diff does not assume `GitHubActionsRole`. It assumes the role named by the repository variable `AWS_DIFF_ROLE_NAME`, and only when that variable is set. Until the variable is set, the pull request warns and does not call AWS. A manual run still assumes `GitHubActionsRole`. `siutindei` manual diffs use the `production` environment, because that environment holds the parameter-file variable and the branch policy allows `main` only. A `siutindei` pull request does not diff.

The workflow step that refuses `GitHubActionsRole` is not a security boundary. A pull request can edit the workflow. The boundary is IAM. `GitHubActionsRole` must not trust `pull_request`. The role named by `AWS_DIFF_ROLE_NAME` is read-only and trusts only `pull_request`. This repository cannot create those roles.

`cdk diff` masks the account id and any email address in the log and the step summary. A parameter value that is not an email is still printed. A public repository must not put personal data in such a value.

`cdk-deploy` takes a plan JSON and a parameters file. The file is either prefixed JSON or plain JSON. The design is `docs/architecture/cdk-deploy.md`.

`lighthouse-ci` writes its runtime config under `RUNNER_TEMP` and deletes it after the run. When `bypass-secret` is set, `ci.upload.target` is `filesystem`, so autorun does not upload the report to temporary-public-storage. The action also removes `x-staging-bypass` from `.lighthouseci`, because a Lighthouse result can copy request headers into the report that a public artifact uploads.

## Denylist

`scripts/pii-denylist.sha256` holds the 31 organisation digests approved on 20 Nov 2026. No plaintext. `lx-software` holds 30 of them. That omission was deliberate: the copy decision does not add the missing digest there. Holding the organisation list only in this repository would apply that digest to `lx-software`, so the five copies stay until a new approval.

## Not finished

- A Dependabot path that bumps this pin, and a measured cooldown exclusion.
- The public-site release action. The design is written. The scripts stay until a dry-run matches them.
- The read-only diff role named by `AWS_DIFF_ROLE_NAME`. The workflows do not create it.
- The siutindei Play upload still checks `PLAY_STORE_UPLOAD_ENABLED` and the package name inline. `play-prerequisites` now has `upload-enabled` and `require-package-name` for that caller. It moves with the pin bump. The other three mobile actions, and evolvesprouts Play, match the current pin. Those signing workflows run on a release, so they have not run yet.
- S3 `public-routes` uploads `.js` and `.css` as `application/octet-stream`. Changing that, or renaming the profiles, needs a dry-run comparison against the live buckets.
- One harness mode of each kind. Three file-length modes, two test-focus modes, and two rule modes still exist.
- Templates for the workflow files that are the same across product repositories. Conformance compares a checkout to a template before any return to reusable workflows.
- Lockfile and Semgrep jobs folded under the required gates.
- The same 31 digests held once, which waits on the denylist decision above.
