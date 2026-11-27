# Public-routes content types

Zone: yellow. The note stays until the bucket comparison is recorded here, or the owner waives that gate on the pull request. Deleting this note before that finishes the plan early.

Issue 106. `_content_type_routes` now falls through to `_content_type_hashed` for `.js` and `.css`: `text/javascript; charset=utf-8` and `text/css; charset=utf-8`. `.webmanifest` stays `application/manifest+json`. `.mjs` does not match the `.js` suffix, so it stays `application/octet-stream`.

`_cache_routes` returns `no-cache` for `.js` and `.css`, including a file at the site root. Those names are not content hashes. An immutable year would keep a previous response after the bytes change. `favicon.ico` and the other dotted root files stay immutable. `assets/` and `media/` syncs still omit `--content-type`.

## Bucket comparison

Changing the content type needs a dry-run against the live buckets and `head-object` for every `.js` and `.css` key. This repository cannot assume the deploy role. That check is not recorded. The latest deploy log prints the upload phases and does not print a per-object content type.

Public responses on 27 Nov 2026, key suffixes only. These are not `head-object` results.

| Suffix | Content-Type | Cache-Control |
| --- | --- | --- |
| `assets/index-iin_XO8a.js`, `assets/react-D5iAZSgv.js` | `text/javascript` | `public,max-age=31536000,immutable` |
| `assets/index-c5XU8JuR.css` | `text/css` | `public,max-age=31536000,immutable` |
| `assets/ibm-plex-mono-latin-400-normal-DMJ8VG8y.woff2` | `font/woff2` | `public,max-age=31536000,immutable` |
| `site.webmanifest` | `application/manifest+json` | `no-cache` |
| `favicon.svg` | `image/svg+xml` | `public,max-age=31536000,immutable` |
| `index.html` | `text/html; charset=utf-8` | `no-cache` |

`/app.js`, `/app.css`, and an unknown path returned the same HTML document as `/` (45781 bytes). Those paths are the document fallback. The asset rows are the sync path. This change does not set their content type.

Someone who can assume the deploy role runs the `aws s3` commands with `--dryrun` and reads `ContentType` with `head-object`. The record is content types and key suffixes. It does not include a bucket name, an account id, or a distribution id.

## Follow-up

`_content_type_hashed` still returns `application/octet-stream` for `.mjs`, `.woff2`, `.map`, `.gif`, `.avif`, `.webm`, and `.mp4`. `.mjs` does not match the `.js` suffix. With `nosniff`, a module script served as `application/octet-stream` does not run. This change does not add those types. Worth a follow-up issue. This session cannot open one.
