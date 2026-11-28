# Production public-site promotion

Zone: yellow. The note stays until a dry-run against both production buckets is recorded here, or the owner waives that gate. Deleting this note before that finishes the plan early.

Issue 103. Checked 28 Nov 2026. `templates/workflows/promote-public-www.yml` still runs `scripts/deploy/deploy-public-www.sh`. `evolvesprouts` `.github/workflows/promote-public-www.yml` does the same. Staging in both products calls `s3-cloudfront-deploy` with `profile: next-site` and `distribution-output: ""`.

## What already matches

`next-site` syncs `_next/static` with `public, max-age=31536000, immutable`, then the other files with the document cache, `--delete`, and excludes `_next/static/*` and `releases/*`. `sync-exclude` adds caller excludes. `promote-from` copies `s3://<bucket>/releases/<id>` with those rules. `release-id` copies to `releases/<id>/`. `staging-robots` writes a deny-all `robots.txt` with `no-store`. `maintenance` syncs `no-store` and excludes `releases/*`. `maintenance-assets` syncs one directory first with its own cache, then excludes it. An empty distribution skips invalidation. A set distribution invalidates `/*`.

evolvesprouts document cache is the action default, `public, max-age=300, must-revalidate`. The script excludes `landing-pages-manifest.json`. Staging passes that as `sync-exclude`. siutindei staging passes `document-cache` `public, max-age=300, must-revalidate, stale-while-revalidate=60` and a no-store marker with `text/plain; charset=utf-8`. evolvesprouts writes the marker with no cache header and no content type. That is the action default.

Production promotion invalidates `/*` after the upload. evolvesprouts switches the `/www/*` viewer-request functions first. Both staging workflows leave the distribution empty, and the script invalidates the site path list. siutindei has no `/www/*` switch. The site path list, the wildcard cap of 15, and the `TooManyInvalidationsInProgress` retry stay in the scripts.

## Gap

siutindei `remove_production_fixtures` runs `aws s3 rm <dest>/fixtures --recursive` after the `_next/static` sync and before the document sync, on production only. The document sync also passes `--exclude fixtures/*`. An exclude on the document sync leaves objects already under `fixtures/` in the bucket. `s3-cloudfront-deploy` has no command between those two syncs. `docs/architecture/public-site-release.md` attributes that delete to evolvesprouts. The evolvesprouts script excludes `landing-pages-manifest.json` and has no `fixtures/` delete.

`maintenance-assets` is implemented and tested. Neither promote workflow passes it. siutindei maintenance syncs `images/` at `public, max-age=3600, must-revalidate`, then the page with `no-store` excluding `images/*`. evolvesprouts maintenance is one no-store sync.

Both scripts reject `PUBLIC_WWW_UPLOAD=external` unless the environment is staging. A promote workflow that uploads with the action and then calls the script for the switch fails on that line.

## This change

Add `delete-prefix` to `s3-cloudfront-deploy`. One directory name, the same segment rule as `maintenance-assets`. Empty skips it. On `next-site` only, including `promote-from` and a `release-id` copy. Inside `_sync_next_site`, after the optional `_next/static` sync and before the document sync: `aws s3 rm s3://<dest>/<name> --recursive`. The rm runs when the static directory is absent, matching the script. The caller still passes `sync-exclude: fixtures/*` so the document sync does not upload the directory. Any other profile with `delete-prefix` set fails. `dry-run` adds `--dryrun` through the existing wrapper.

`tests/test_s3_cloudfront_deploy.py`: with `delete-prefix` `fixtures` and `sync-exclude` `fixtures/*`, the `rm` sits between the static sync and the document sync, on a local source and on `promote-from`. The document sync still contains `--exclude fixtures/*`. An empty `delete-prefix` issues no `rm`. A profile other than `next-site` fails. A source with no `_next/static` still deletes the prefix.

`s3-cloudfront-deploy/README.md` and `action.yml` describe the input. `docs/architecture/public-site-release.md`: the fixtures delete is siutindei production; staging upload is already `next-site`; production promotion still calls the script.

No edit to `templates/workflows/promote-public-www.yml`.

## Gate

This repository cannot assume the deploy role. The production workflows keep calling the scripts until this note records a dry-run against both buckets. A person who can assume the role runs the action with `dry-run: true` and the script's `aws s3` lines for one local-build promotion and one `promote-from` copy, for each product. The record is cache headers, key prefixes, and invalidation paths. It does not include a bucket name, an account id, or a distribution id.

siutindei production, local build: `profile: next-site`, `bucket-output: PublicWwwBucketName`, the staging `document-cache`, `sync-exclude: fixtures/*`, `delete-prefix: fixtures`. evolvesprouts production, local build: the same profile and bucket output, `sync-exclude: landing-pages-manifest.json`, no `delete-prefix`. evolvesprouts `distribution-output` stays empty so the `/www/*` switch runs before the invalidation. siutindei promotion invalidates `/*`, which is the path the action sends when a distribution id is set.

## After the record

Point `templates/workflows/promote-public-www.yml` at the action for the upload. The script keeps maintenance assembly, image optimisation, the `/www/*` switch, and catalogue comparison. `evolvesprouts` `deploy-training.sh` stays `next-export`.

That template change waits on both products accepting `PUBLIC_WWW_UPLOAD=external` for production, so the script can skip the sync and still switch and invalidate. Those edits are in the product repositories. Pins move with `scripts/bump_pins.py` after this action is on `main`. No pin bump in this repository.

There is no second action. An action cannot call another action in this repository, and `next-site` and `maintenance` already own the upload.

## Checks

`python3 -m unittest discover -s tests -v`

`python3 scripts/check_action_layout.py`

`python3 scripts/check_pii.py`

## Left alone

The site path list, the wildcard cap, and the invalidation retry. Maintenance assembly, image optimisation, the `/www/*` switch, and catalogue comparison. `deploy-training.sh`. Profile names. Staging workflows.
