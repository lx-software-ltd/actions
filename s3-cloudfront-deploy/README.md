# S3 CloudFront deploy

Syncs a built site to a bucket and invalidates CloudFront. The job needs AWS credentials already, from `aws-oidc`. This action does not request a token. Set `bucket`, or set `stack` and `region` and the action reads `bucket-output` and `distribution-output`.

`profile` keeps the upload rules that site already uses:

| Profile | Rules |
| --- | --- |
| `public-hashed` | Hashed `assets/` with `--delete`, root files with a content type, `index.html` last and `no-cache`, then delete retired root keys. |
| `admin-hashed` | Hashed `assets/` with `--delete`. Other root files are immutable and have no content type. `index.html` is last and `no-cache`. Root keys are not pruned. |
| `public-routes` | Assets, size-only `media/`, extensionless HTML routes, unhashed directories, then a second assets sync with `--delete`. `indexnow: true` pings IndexNow and does not fail the deploy. |
| `next-export` | `aws s3 sync --delete` of a Next.js `out/` directory, then an invalidation. |
| `next-site` | `_next/static` with `public, max-age=31536000, immutable`, then the other files with `public, max-age=300, must-revalidate` and `--delete`. The document sync excludes `_next/static/*` and `releases/*`. |
| `maintenance` | One sync with `no-store, max-age=0`, `--delete`, and `--exclude releases/*`. `maintenance-assets` syncs that directory first with its own cache, then excludes it. |

An empty `distribution-id` skips the invalidation. A missing distribution output prints a warning and then skips it. A missing bucket output fails the deploy.

`dry-run: true` adds `--dryrun` to every `aws s3` command and does not create an invalidation. The planned uploads and deletes are printed. IndexNow is not called.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `source` | except promote | empty | Build directory. Empty when `promote-from` is set. |
| `bucket` | no | empty | Destination bucket. Empty when `stack` is set. |
| `stack` | no | empty | Stack whose outputs name the bucket and distribution. |
| `region` | no | empty | Region for that stack read. |
| `bucket-output` | no | `PublicWebsiteBucketName` | Output key for the bucket. |
| `distribution-output` | no | `PublicWebsiteDistributionId` | Output key for the distribution. |
| `distribution-id` | no | empty | CloudFront distribution. Empty skips invalidation. |
| `profile` | no | `public-hashed` | Upload rules. |
| `indexnow` | no | `false` | Ping IndexNow after `public-routes`. |
| `dry-run` | no | `false` | Plan the S3 changes and skip CloudFront. |
| `release-id` | no | empty | Copy a `next-site` upload to `releases/<id>/`. |
| `release-marker` | no | `false` | Write `releases/latest-release-id.txt` with no cache header. |
| `staging-robots` | no | `false` | Upload a deny-all `robots.txt` with `no-store`. |
| `promote-from` | no | empty | Copy `s3://bucket/releases/<id>` with the `next-site` rules. |
| `sync-exclude` | no | empty | Extra `--exclude` patterns for `next-site`, comma-separated. |
| `asset-cache` | no | `public, max-age=31536000, immutable` | Cache-Control for `_next/static`. |
| `document-cache` | no | `public, max-age=300, must-revalidate` | Cache-Control for the other `next-site` files. |
| `marker-cache` | no | empty | Cache-Control for the release marker. Empty omits it. |
| `marker-content-type` | no | empty | Content-Type for the release marker. Empty omits it. |
| `maintenance-assets` | no | empty | Directory synced before the no-store maintenance upload. |
| `maintenance-asset-cache` | no | `public, max-age=3600, must-revalidate` | Cache-Control for that directory. |

`release-id` and `promote-from` together fail. `release-id` with `maintenance` fails. A release id is letters, digits, dot, dash, or underscore, at most 128 characters. The caller still builds the maintenance page, optimises images, and switches the `/www/*` function.

The action invalidates `/*` at the end of the sync. evolvesprouts switches the `/www/*` function and then invalidates. Leave `distribution-id` empty and invalidate after that switch. An invalidation inside the action runs before the switch, so the previous function can stay cached for a short time.

evolvesprouts passes `sync-exclude: landing-pages-manifest.json` on the site sync and the release copy. The action does not exclude that file.

siutindei passes `document-cache` `public, max-age=300, must-revalidate, stale-while-revalidate=60`, a no-store marker with `text/plain; charset=utf-8`, and `maintenance-assets: images`. Production also passes `sync-exclude: fixtures/*` and deletes `fixtures/` before the action runs. The script deletes fixtures between the asset sync and the document sync. One action call cannot do that in the middle.

## Example

```yaml
- uses: lx-software-ltd/actions/s3-cloudfront-deploy@<sha> # main <yyyy-mm-dd>
  with:
    source: apps/public_www/dist
    bucket: ${{ steps.outputs.outputs.bucket }}
    distribution-id: ${{ steps.outputs.outputs.distribution }}
    profile: public-hashed
```
