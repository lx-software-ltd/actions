# Verify rulesets — target repository input

**Status**: This pull request
**Zone**: yellow

## Intent

Rename the unused `repository` input to `target-repository`. The action no longer assigns `GITHUB_REPOSITORY`, which GitHub sets itself. An empty input still reads that variable.

## What it does not change

The tag rules, the review count, or any caller. No caller passes the old input.

## Rollback

Revert this pull request.
