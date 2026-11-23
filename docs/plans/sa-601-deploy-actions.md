# Plan: SA-601 deploy actions

**Status**: In progress
**Zone**: yellow

G4 is approved. This pull request adds the actions. It does not change a product workflow, and no workflow here requests `id-token: write` or calls AWS. Product callers pin the merge commit. They pass `wait: false` on Amplify so a release still returns after `start-job`.

## Goal

`s3-cloudfront-deploy` syncs a build and invalidates CloudFront. `profile` keeps the current upload rules: `public-hashed` for the findingalpha public site, `admin-hashed` for the pair A admin sites, and `public-routes` for the lx-software public site. `amplify-release` starts a RELEASE job. `mode: promote` still requires a green source job and, by default, only staging to main.

## Non-goals

- No product workflow edit. Callers are the next pull requests, one repository at a time, after this commit is on `main`.
- No `cdk-deploy`. That stays a design note until a second G5 approval.
- No account id in this repository. Fixture jobs use a stub `aws`.
- No `v*` tag.

## Files

`s3-cloudfront-deploy/`, `amplify-release/`, their tests, the fixture jobs, and the compile list.

## Invariants this change preserves

- Inputs reach the script through `env`. The `run` block does not interpolate `${{`.
- An empty distribution skips invalidation. `index.html` is still uploaded last on the hashed profiles.
- `wait: false` does not poll. Promote still fails when the source job is not `SUCCEED`.
- AWS errors are printed with a 12-digit account id redacted.

## Done when

`python3 -m unittest discover -s tests -v` passes and `python3 scripts/check_action_layout.py` passes. The fixture jobs do not call AWS.

## Rollback

Revert this pull request. No product workflow pins the actions until the caller pull requests.

## Open questions

None.
