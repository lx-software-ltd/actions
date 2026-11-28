# Production public-site promotion

Zone: yellow. The note stays until a dry-run against both production buckets is recorded here, or the owner waives that gate. Deleting this note before that finishes the plan early.

Issue 103. `delete-prefix` on `s3-cloudfront-deploy` profile `next-site` runs `aws s3 rm s3://<dest>/<name> --recursive` after the `_next/static` sync and before the document sync. The same delete runs for `promote-from` and for a `release-id` copy. It runs when `_next/static` is absent. Empty skips it. A name with a slash fails. Any other profile fails. `dry-run` adds `--dryrun`.

siutindei production passes `delete-prefix: fixtures` and `sync-exclude: fixtures/*`. evolvesprouts passes `sync-exclude: landing-pages-manifest.json` and leaves `delete-prefix` empty. `templates/workflows/promote-public-www.yml` still runs `scripts/deploy/deploy-public-www.sh`.

## Dry-run

This repository cannot assume the deploy role. That check is not recorded. Production workflows keep calling the scripts until it is.

Someone who can assume the role runs the action with `dry-run: true` and the script's `aws s3` lines for one local-build promotion and one `promote-from` copy, for each product. The record is cache headers, key prefixes, and invalidation paths. It does not include a bucket name, an account id, or a distribution id.

siutindei production, local build: `profile: next-site`, `bucket-output: PublicWwwBucketName`, document cache `public, max-age=300, must-revalidate, stale-while-revalidate=60`, `sync-exclude: fixtures/*`, `delete-prefix: fixtures`. evolvesprouts production, local build: the same profile and bucket output, `sync-exclude: landing-pages-manifest.json`, no `delete-prefix`. evolvesprouts `distribution-output` stays empty so the `/www/*` switch runs before the invalidation. siutindei promotion invalidates `/*`.

## After the record

Point the promote template at the action for the upload. The script keeps maintenance assembly, image optimisation, the `/www/*` switch, and catalogue comparison. Both product scripts reject `PUBLIC_WWW_UPLOAD=external` unless the environment is staging. Accepting an external production upload is a product change. `evolvesprouts` `deploy-training.sh` stays `next-export`. No second action. No pin bump in this repository.
