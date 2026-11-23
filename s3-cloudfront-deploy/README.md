# S3 CloudFront deploy

Syncs a built site to a bucket and invalidates CloudFront. The job needs AWS credentials already, from `aws-oidc`. This action does not request a token and does not read a stack.

`profile` keeps the upload rules that site already uses:

| Profile | Rules |
| --- | --- | --- |
| `public-hashed` | Hashed `assets/` with `--delete`, root files with a content type, `index.html` last and `no-cache`, then delete retired root keys. |
| `admin-hashed` | Hashed `assets/` with `--delete`. Other root files are immutable and have no content type. `index.html` is last and `no-cache`. Root keys are not pruned. |
| `public-routes` | Assets, size-only `media/`, extensionless HTML routes, unhashed directories, then a second assets sync with `--delete`. `indexnow: true` pings IndexNow and does not fail the deploy. `.js` and `.css` are uploaded as `application/octet-stream`. |
| `next-export` | `aws s3 sync --delete` of a Next.js `out/` directory, then an invalidation. |

An empty `distribution-id` skips the invalidation, which is what a missing distribution output does today.

`dry-run: true` adds `--dryrun` to every `aws s3` command and does not create an invalidation. The planned uploads and deletes are printed. IndexNow is not called.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `source` | yes | | Build directory. |
| `bucket` | yes | | Destination bucket. |
| `distribution-id` | no | empty | CloudFront distribution. Empty skips invalidation. |
| `profile` | no | `public-hashed` | Upload rules. |
| `indexnow` | no | `false` | Ping IndexNow after `public-routes`. |
| `dry-run` | no | `false` | Plan the S3 changes and skip CloudFront. |

## Example

```yaml
- uses: lx-software-ltd/actions/s3-cloudfront-deploy@<sha> # main <yyyy-mm-dd>
  with:
    source: apps/public_www/dist
    bucket: ${{ steps.outputs.outputs.bucket }}
    distribution-id: ${{ steps.outputs.outputs.distribution }}
    profile: public-hashed
```
