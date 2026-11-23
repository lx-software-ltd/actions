# Lighthouse CI

Zone: yellow. The note stays in this pull request.

The action writes the runtime config under `RUNNER_TEMP`, not beside the site. `@lhci/cli` autorun uses that path. When `bypass-secret` is set, `ci.upload.target` is `filesystem`, so autorun does not upload the report to temporary-public-storage before the scrub. After the run the config is deleted, and any `x-staging-bypass` value is removed from `.lighthouseci` before a GitHub artifact upload. The Lighthouse result can copy `extraHeaders` into the report, so the scrub still runs.

No product workflow calls this until the commit is on `main`.
