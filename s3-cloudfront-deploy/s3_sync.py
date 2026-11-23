"""Sync a built site to S3 and invalidate CloudFront.

Profiles keep the upload rules of the repository that already deploys
that way. The caller passes the bucket and distribution. This does not
read a stack and does not print an account id.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

IMMUTABLE = "public,max-age=31536000,immutable"
ROOT_CACHE = "no-cache,must-revalidate"
ACCOUNT_ID = re.compile(r"\b\d{12}\b")

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class SyncError(Exception):
    """The sync cannot run."""


def _run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _with_dryrun(command: list[str], dry_run: bool) -> list[str]:
    if dry_run and command[:2] == ["aws", "s3"]:
        return [command[0], command[1], command[2], "--dryrun", *command[3:]]
    return command


def _dry_run_runner(run_aws: Runner) -> Runner:
    def wrapped(command: list[str]) -> subprocess.CompletedProcess[str]:
        command = _with_dryrun(command, True)
        result = run_aws(command)
        if result.returncode == 0 and result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        return result

    return wrapped


def _redact(text: str) -> str:
    return ACCOUNT_ID.sub("************", text)


def _content_type_hashed(path: str) -> str:
    name = path.lower()
    if name.endswith(".html"):
        return "text/html; charset=utf-8"
    if name.endswith(".json"):
        return "application/json; charset=utf-8"
    if name.endswith(".txt"):
        return "text/plain; charset=utf-8"
    if name.endswith(".xml"):
        return "application/xml; charset=utf-8"
    if name.endswith(".svg"):
        return "image/svg+xml"
    if name.endswith(".png"):
        return "image/png"
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith(".ico"):
        return "image/x-icon"
    if name.endswith(".js"):
        return "text/javascript; charset=utf-8"
    if name.endswith(".css"):
        return "text/css; charset=utf-8"
    return "application/octet-stream"


def _content_type_routes(path: str) -> str:
    name = path.lower()
    if name.endswith(".webmanifest"):
        return "application/manifest+json"
    if name.endswith(".js") or name.endswith(".css"):
        return "application/octet-stream"
    return _content_type_hashed(path)


def _cache_routes(key: str) -> str:
    lower = key.lower()
    if (
        lower.endswith((".html", ".txt", ".xml"))
        or lower.endswith("site.webmanifest")
        or "/" in key
    ):
        return "no-cache"
    if "." in Path(key).name:
        return IMMUTABLE
    return "no-cache"


def _require_bucket(bucket: str) -> str:
    if not bucket or bucket == "None":
        raise SyncError("bucket is required")
    return bucket


def _distribution(value: str) -> str:
    if not value or value == "None":
        return ""
    return value


def _cp(
    run_aws: Runner,
    source: Path,
    bucket: str,
    key: str,
    cache: str,
    content_type: str | None,
) -> None:
    command = [
        "aws",
        "s3",
        "cp",
        str(source),
        f"s3://{bucket}/{key}",
        "--cache-control",
        cache,
    ]
    if content_type is not None:
        command.extend(["--content-type", content_type])
    result = run_aws(command)
    if result.returncode != 0:
        raise SyncError(_redact(result.stderr or result.stdout or "s3 cp failed"))


def _sync(run_aws: Runner, source: Path, dest: str, extra: list[str]) -> None:
    result = run_aws(["aws", "s3", "sync", str(source), dest, *extra])
    if result.returncode != 0:
        raise SyncError(_redact(result.stderr or result.stdout or "s3 sync failed"))


def _invalidate(run_aws: Runner, distribution: str, dry_run: bool) -> None:
    if not distribution:
        return
    if dry_run:
        print(f"Dry run: skipping CloudFront invalidation for {distribution}")
        return
    result = run_aws(
        [
            "aws",
            "cloudfront",
            "create-invalidation",
            "--distribution-id",
            distribution,
            "--paths",
            "/*",
        ]
    )
    if result.returncode != 0:
        raise SyncError(_redact(result.stderr or result.stdout or "invalidation failed"))
    print(f"Invalidating CloudFront distribution {distribution}")


def _prune_root(run_aws: Runner, bucket: str, desired: set[str]) -> None:
    listed = run_aws(
        [
            "aws",
            "s3api",
            "list-objects-v2",
            "--bucket",
            bucket,
            "--delimiter",
            "/",
            "--query",
            "Contents[].Key",
            "--output",
            "text",
        ]
    )
    if listed.returncode != 0:
        raise SyncError(_redact(listed.stderr or listed.stdout or "bucket listing failed"))
    keys = [key for key in listed.stdout.replace("\t", "\n").splitlines() if key and "/" not in key]
    for key in keys:
        if key in desired:
            continue
        print(f"Deleting s3://{bucket}/{key}")
        removed = run_aws(["aws", "s3", "rm", f"s3://{bucket}/{key}"])
        if removed.returncode != 0:
            raise SyncError(_redact(removed.stderr or "s3 rm failed"))


def _upload_hashed_root(run_aws: Runner, source: Path, bucket: str) -> set[str]:
    desired: set[str] = set()
    files = sorted(path for path in source.iterdir() if path.is_file())
    for path in files:
        desired.add(path.name)
        if path.name == "index.html":
            continue
        cache = IMMUTABLE if path.name.startswith("assets/") else ROOT_CACHE
        _cp(run_aws, path, bucket, path.name, cache, _content_type_hashed(path.name))
    print("Uploading index.html last with no-cache…")
    _cp(
        run_aws,
        source / "index.html",
        bucket,
        "index.html",
        ROOT_CACHE,
        "text/html; charset=utf-8",
    )
    return desired


def _deploy_public_hashed(
    run_aws: Runner, source: Path, bucket: str, distribution: str, dry_run: bool
) -> None:
    assets = source / "assets"
    if assets.is_dir():
        print("Uploading hashed assets under dist/assets with long cache…")
        _sync(
            run_aws,
            assets,
            f"s3://{bucket}/assets",
            ["--delete", "--cache-control", IMMUTABLE],
        )
    print("Uploading site root files…")
    desired = _upload_hashed_root(run_aws, source, bucket)
    print("Pruning retired root objects…")
    _prune_root(run_aws, bucket, desired)
    _invalidate(run_aws, distribution, dry_run)


def _deploy_admin_hashed(
    run_aws: Runner, source: Path, bucket: str, distribution: str, dry_run: bool
) -> None:
    assets = source / "assets"
    print("Uploading hashed assets under dist/assets with long cache…")
    if assets.is_dir():
        _sync(
            run_aws,
            assets,
            f"s3://{bucket}/assets",
            ["--delete", "--cache-control", IMMUTABLE],
        )
    print("Uploading other root build artifacts (except index.html)…")
    for path in sorted(item for item in source.iterdir() if item.is_file()):
        if path.name in {"assets", "index.html"} or path.name.startswith("."):
            continue
        _cp(run_aws, path, bucket, path.name, IMMUTABLE, None)
    print("Uploading index.html last with no-cache…")
    _cp(
        run_aws,
        source / "index.html",
        bucket,
        "index.html",
        ROOT_CACHE,
        "text/html; charset=utf-8",
    )
    _invalidate(run_aws, distribution, dry_run)


def _deploy_next_export(
    run_aws: Runner, source: Path, bucket: str, distribution: str, dry_run: bool
) -> None:
    print(f"Syncing the Next.js export to s3://{bucket}")
    _sync(run_aws, source, f"s3://{bucket}", ["--delete"])
    _invalidate(run_aws, distribution, dry_run)


def _deploy_public_routes(
    run_aws: Runner,
    source: Path,
    bucket: str,
    distribution: str,
    indexnow: bool,
    dry_run: bool,
) -> None:
    assets = source / "assets"
    if not assets.is_dir():
        raise SyncError(f"Hashed assets not found at {assets}")
    print(f"Uploading hashed assets to s3://{bucket}/assets")
    _sync(run_aws, assets, f"s3://{bucket}/assets", ["--cache-control", IMMUTABLE])
    media = source / "media"
    if media.is_dir():
        print("Syncing media by size")
        _sync(
            run_aws,
            media,
            f"s3://{bucket}/media",
            ["--size-only", "--delete", "--cache-control", IMMUTABLE],
        )
    print("Uploading site root")
    for path in sorted(item for item in source.iterdir() if item.is_file()):
        _cp(
            run_aws,
            path,
            bucket,
            path.name,
            _cache_routes(path.name),
            _content_type_routes(path.name),
        )
    print("Uploading pre-rendered routes")
    for path in sorted(source.glob("*.html")):
        if path.name == "index.html":
            continue
        key = path.name[: -len(".html")]
        _cp(run_aws, path, bucket, key, _cache_routes(key), _content_type_routes(path.name))
    print("Uploading unhashed public directories")
    for directory in sorted(item for item in source.iterdir() if item.is_dir()):
        if directory.name in {"assets", "media"}:
            continue
        files = sorted(path for path in directory.rglob("*") if path.is_file())
        for path in files:
            key = path.relative_to(source).as_posix()
            _cp(run_aws, path, bucket, key, _cache_routes(key), _content_type_routes(path.name))
    print("Pruning retired hashed assets")
    _sync(
        run_aws,
        assets,
        f"s3://{bucket}/assets",
        ["--delete", "--cache-control", IMMUTABLE],
    )
    _invalidate(run_aws, distribution, dry_run)
    if indexnow and dry_run:
        print("Dry run: skipping IndexNow")
        return
    if indexnow:
        _indexnow(source)


def _indexnow(source: Path) -> None:
    if os.environ.get("INDEXNOW_DISABLED", "0") == "1":
        print("IndexNow ping skipped (INDEXNOW_DISABLED=1)")
        return
    if shutil.which("curl") is None:
        print("IndexNow ping skipped (curl not found)")
        return
    key_file = source / "indexnow.txt"
    sitemap = source / "sitemap.xml"
    if not key_file.is_file() or not sitemap.is_file():
        print("IndexNow ping skipped (indexnow.txt or sitemap.xml missing)")
        return
    key = "".join(key_file.read_text(encoding="utf-8").split())
    urls = [
        line.split("<loc>", 1)[1].split("</loc>", 1)[0].strip()
        for line in sitemap.read_text(encoding="utf-8").splitlines()
        if "<loc>" in line and "</loc>" in line
    ]
    if not key or not urls:
        print("IndexNow ping skipped (empty key or sitemap)")
        return
    origin = urls[0].split("/", 3)
    origin_s = "/".join(origin[:3]) if len(origin) >= 3 else ""
    host = origin_s.split("://", 1)[-1]
    import json

    body = json.dumps(
        {
            "host": host,
            "key": key,
            "keyLocation": f"{origin_s}/indexnow.txt",
            "urlList": urls,
        }
    )
    print(f"IndexNow: submitting {len(urls)} URLs for {host}")
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "-X",
            "POST",
            "https://api.indexnow.org/indexnow",
            "-H",
            "Content-Type: application/json; charset=utf-8",
            "--data",
            body,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    status = (result.stdout or "").strip()
    if status in {"200", "202"}:
        print(f"IndexNow: accepted ({status})")
    else:
        print(f"IndexNow: not accepted (HTTP {status or 'none'}); continuing")


def deploy(
    *,
    source: Path,
    bucket: str,
    distribution: str,
    profile: str,
    indexnow: bool,
    dry_run: bool = False,
    run_aws: Runner,
) -> None:
    bucket = _require_bucket(bucket)
    distribution = _distribution(distribution)
    if dry_run:
        print("Dry run: every s3 command uses --dryrun and CloudFront is not invalidated.")
        run_aws = _dry_run_runner(run_aws)
    if profile == "public-hashed":
        if not source.is_dir():
            raise SyncError(f"Build output not found at {source}")
        _deploy_public_hashed(run_aws, source, bucket, distribution, dry_run)
        return
    if profile == "admin-hashed":
        if not source.is_dir():
            raise SyncError(f"Build output not found at {source}")
        _deploy_admin_hashed(run_aws, source, bucket, distribution, dry_run)
        return
    if profile == "public-routes":
        _deploy_public_routes(run_aws, source, bucket, distribution, indexnow, dry_run)
        return
    if profile == "next-export":
        if not source.is_dir():
            raise SyncError(f"Build output not found at {source}")
        _deploy_next_export(run_aws, source, bucket, distribution, dry_run)
        return
    raise SyncError(f"Unsupported profile: {profile}")


def main(run_aws: Runner = _run_aws) -> int:
    source = Path(os.environ.get("SOURCE", ""))
    bucket = os.environ.get("BUCKET", "")
    distribution = os.environ.get("DISTRIBUTION_ID", "")
    profile = os.environ.get("PROFILE", "public-hashed") or "public-hashed"
    indexnow = os.environ.get("INDEXNOW", "false").lower() == "true"
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    try:
        deploy(
            source=source,
            bucket=bucket,
            distribution=distribution,
            profile=profile,
            indexnow=indexnow,
            dry_run=dry_run,
            run_aws=run_aws,
        )
    except SyncError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
