# Public-site release

`evolvesprouts` `scripts/deploy/deploy-public-www.sh` (725 lines) and `siutindei` `scripts/deploy/deploy-public-www.sh` (620 lines) are the release. `deploy-public-www.yml` and `promote-public-www.yml` run them. This note is the design. It does not move the scripts.

## What the scripts do

Both scripts publish one Next.js `out/` directory to the public-site bucket and invalidate CloudFront. They are not the hashed `s3-cloudfront-deploy` profiles.

Shared steps:

1. Read the bucket, the distribution, and the release prefix from CloudFormation outputs (`require_stack_output` / `get_environment_outputs`).
2. Reject a release id that is not a safe path segment (`validate_release_id`).
3. Sync the current build (`sync_site_artifacts`) and, when a release id is set, a copy under that id (`sync_release_artifacts`).
4. Invalidate the distribution (`invalidate_distribution`), with a cap on wildcard invalidations (`assert_wildcard_invalidation_limit`).
5. Build a maintenance page from a partial and contact settings (`prepare_maintenance_build_dir` and the inject helpers) and sync it when maintenance mode is on (`sync_maintenance_artifacts`).
6. Force a staging `robots.txt` (`enforce_staging_robots_txt`).

`evolvesprouts` also removes production fixtures before a production sync. Cache-Control is three policies: immutable assets, a short document cache, and `no-store`.

`siutindei` adds the catalogue snapshot the promote workflow fetches, and the same maintenance and release layout. The two scripts are the same shape with different stack names and a few extra files.

## What stays in the caller

- The workflow still assumes the role, selects the environment, and builds the site.
- Release id, promote id, maintenance flag, and contact values stay inputs. An action cannot read `vars` or `secrets`.
- Stack names stay inputs. `evolvesprouts` defaults to `evolvesprouts-public-www`. `siutindei` names its own stack.
- `s3-cloudfront-deploy` profile `next-export` is a plain `aws s3 sync --delete`. It does not do release copies, maintenance pages, or the three cache policies. It is not this release.

## A later action

One `public-site-release` action can own the six steps above once a dry-run against both buckets matches the scripts byte for byte on cache headers, key prefixes, and invalidation paths. Until that comparison exists, the workflows keep calling the scripts. `evolvesprouts` `deploy-training.sh` is a separate `next-export` upload and is not part of this release.
