# Verify rulesets — v* tag rules

**Status**: This pull request
**Zone**: yellow

## Intent

Require the active `refs/tags/v*` rulesets to block creation, update, and deletion. The three rules may be split across rulesets.

## Measured 20 Nov 2026, 16:11 UTC

`release-tags` includes `refs/tags/v*` and blocks `deletion` and `update`. Its bypass list is empty. `release-tags-create` was updated at `2026-11-20T16:11:54Z`. Its include is `refs/tags/v*`, and its only rule is `creation`. Organization admin is on its bypass list, so that role can create a `v*` tag. Other actors cannot. Update and deletion stay blocked. This check looks at the three rule types, not at bypass actors.

Product callers stay on `61d2a581a1d880533982bada88923ad1b6431700` until a later pin move. This pull request does not change those pins.

## Rollback

Revert this pull request.
