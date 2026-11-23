# Plan: SA-701 pair B shared steps

**Status**: In progress
**Zone**: yellow

Compared `deploy-ios.yml`, `deploy-mobile.yml`, `promote-public-www.yml`, and `smoke-public-www-staging.yml` on `main` after replacing the project name and the Flutter pin.

## What is the same

`deploy-ios.yml` shares the signing setup (32 lines), the export-options script (39), and the TestFlight key plus upload (50). `siutindei` inserts an Amplify config step before the IPA build, so that build stays in the caller.

`deploy-mobile.yml` shares the keystore step (23), the Play prerequisite check, and the Play upload. The package name differs.

`promote-public-www.yml` shares the mode input and the account check. The catalogue and release reads differ, so the rest stays in the caller. `smoke-public-www-staging.yml` shares the checkout and Node setup (32 lines). That is `setup-node` plus checkout, which is already one `uses:` each, so it is not wrapped again.

## This pull request

Extract the whole steps that are scripts:

- `ios-export-options`
- `appstore-api-key`
- `android-signing`
- `play-prerequisites`

The TestFlight upload, the Play upload, `flutter-action`, and `ssh-agent` stay in the caller. Each is one `uses:`. `gem install` stays in the caller so the actions fixture does not install gems.

Product workflows pin the merge commit in a later pull request. This pull request does not edit them.

## Non-goals

- No change to the IPA or AAB build command.
- No deploy run.
- No account id in this repository.

## Done when

`python3 -m unittest tests.test_pair_b_steps tests.test_setup_actions -q` passes and `python3 scripts/check_action_layout.py` passes.

## Rollback

Revert this pull request.

## Open questions

None.
