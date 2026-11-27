# Public-routes content types

Zone: yellow. The note stays until the pull request that finishes this change deletes it.

Issue 106. Checked 27 Nov 2026. `s3-cloudfront-deploy/s3_sync.py` `_content_type_routes` still returns `application/octet-stream` for `.js` and `.css`. `_content_type_hashed` returns `text/javascript; charset=utf-8` and `text/css; charset=utf-8`.

## What is wrong

`_content_type_routes` is the content type on three `aws s3 cp` passes in `public-routes`: files at the site root, extensionless HTML routes, and files under unhashed directories. `assets/` and `media/` are `aws s3 sync` and do not pass `--content-type`. A hashed bundle is not uploaded by this function.

`.webmanifest` stays `application/manifest+json`.

The only caller is `lx-software` `.github/workflows/deploy-public-www.yml` (`profile: public-routes`, `indexnow: true`, pin `b911ce02864881b95506a008a471108db22ce29e`). `findingalpha`, `evolvesprouts`, and `siutindei` do not set this profile. `apps/public_www/public/` has no `.js` or `.css`. Vite writes hashed scripts under `dist/assets/`, and that site inlines CSS into the HTML. The octet-stream branch still runs for a later `.js` or `.css` at the dist root or under `public/`.

## Gate

Changing the content type, or renaming the profiles, needs a dry-run comparison against the live buckets. This repository does not call AWS and does not hold an account id or a bucket name. Record the comparison in this note before editing `s3_sync.py`.

The deploy job runs only on `main` and sets `dry-run: "false"`. Leave that workflow as it is. A person who can assume the deploy role runs the same `aws s3` commands the action would run, with `--dryrun`, against the bucket named by `PublicWebsiteBucketName`, and reads `ContentType` with `head-object` for every `.js` and `.css` key. The note records content types and key suffixes. It does not record an account id, a bucket name, or a distribution id.

`aws s3 cp` plans every key on each run, so a dry-run does not show a metadata difference. Compare `--content-type` on the `.js` and `.css` `cp` lines with the live `ContentType`. The two `assets/` syncs and the `media/` sync must match before and after the edit, because they do not use `_content_type_routes`.

Profile names stay `public-hashed`, `admin-hashed`, `public-routes`, `next-export`, `next-site`, and `maintenance`.

## This change, after the comparison

Delete the `.js` / `.css` branch in `_content_type_routes` so those names fall through to `_content_type_hashed`.

`tests/test_s3_cloudfront_deploy.py`: a root `app.js` and `app.css`, and one `.js` under an unhashed directory, assert `--content-type` `text/javascript; charset=utf-8` and `text/css; charset=utf-8`. `site.webmanifest` stays `application/manifest+json`. The `assets/` syncs still omit `--content-type`.

`s3-cloudfront-deploy/README.md`: drop the sentence that `.js` and `.css` are uploaded as `application/octet-stream`.

No workflow edit in this repository. No pin bump here. After this merges, `lx-software` bumps the pin with `scripts/bump_pins.py`. That deploy writes the new content type. Until then the live site stays on the current pin.

## Checks

`python3 -m unittest discover -s tests -v`

`python3 scripts/check_action_layout.py`

`python3 scripts/check_pii.py`

## Left alone

`assets/` and `media/` sync flags. `admin-hashed` still omits a content type on files other than `index.html`. IndexNow. Cache-Control. If the comparison finds `assets/*.js` or `assets/*.css` stored as `application/octet-stream`, that is a separate change: those syncs do not set a content type, and this note does not add one.
