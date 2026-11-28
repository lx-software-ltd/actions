# Public-site release

`evolvesprouts` `scripts/deploy/deploy-public-www.sh` and `siutindei` `scripts/deploy/deploy-public-www.sh` are the release. Staging uploads with `s3-cloudfront-deploy` profile `next-site` and an empty distribution, then the script finishes the release. `promote-public-www.yml` still runs the script for the upload. The direct pair deploys from `deploy-public-www.yml` without that script. This note is the design. Production promotion stays on the script until the dry-run in `docs/plans/103-production-public-site-promotion.md` is recorded.

## What the scripts do

Both scripts publish one Next.js `out/` directory to the public-site bucket and invalidate CloudFront. They are not the hashed `s3-cloudfront-deploy` profiles.

Shared steps:

1. Read the bucket, the distribution, and the release prefix from CloudFormation outputs (`require_stack_output` / `get_environment_outputs`).
2. Reject a release id that is not a safe path segment (`validate_release_id`).
3. Sync the current build (`sync_site_artifacts`) and, when a release id is set, a copy under that id (`sync_release_artifacts`).
4. Invalidate the distribution (`invalidate_distribution`), with a cap on wildcard invalidations (`assert_wildcard_invalidation_limit`).
5. Build a maintenance page from a partial and contact settings (`prepare_maintenance_build_dir` and the inject helpers) and sync it when maintenance mode is on (`sync_maintenance_artifacts`).
6. Force a staging `robots.txt` (`enforce_staging_robots_txt`).

`siutindei` deletes `fixtures/` on production after the `_next/static` sync and before the document sync, and excludes `fixtures/*` from that sync. `sync_site_artifacts` repeats that delete on the release copy when a release id is set. `s3-cloudfront-deploy` `delete-prefix` is that delete. It refuses `releases`, `_next`, and the `maintenance-assets` directory, adds `<name>/*` to the document exclude, and removes `s3://<bucket>/<name>/` so the prefix match stops at that directory. The promote workflow does not pass it yet. `evolvesprouts` excludes `landing-pages-manifest.json`. Cache-Control is three policies: immutable assets, a short document cache, and `no-store`.

`siutindei` adds the catalogue snapshot the promote workflow fetches, and the same maintenance and release layout. The two scripts are the same shape with different stack names and a few extra files.

## What stays in the caller

- The workflow still assumes the role, selects the environment, and builds the site.
- Release id, promote id, maintenance flag, and contact values stay inputs. An action cannot read `vars` or `secrets`.
- Stack names stay inputs. `evolvesprouts` defaults to `evolvesprouts-public-www`. `siutindei` names its own stack.
- `s3-cloudfront-deploy` profile `next-site` is the staged upload: immutable `_next/static`, the document cache, a release copy, and `delete-prefix` between those syncs. Production promotion still calls the script.
- `s3-cloudfront-deploy` profile `next-export` is a plain `aws s3 sync --delete`. It does not do release copies, maintenance pages, or the three cache policies. It is not this release.
