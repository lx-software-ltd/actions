# Lighthouse CI

Zone: yellow. The note stays in this pull request.

The action writes the runtime config under `RUNNER_TEMP`, not beside the site. `@lhci/cli` autorun uses that path. After the run the config is deleted, and any `x-staging-bypass` value is removed from `.lighthouseci` before an artifact upload. The Lighthouse result can copy `extraHeaders` into the report, so the scrub runs even when the header was only meant for the request.

No product workflow calls this until the commit is on `main`.
