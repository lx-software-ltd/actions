"""Sync a built site to S3 and invalidate CloudFront.

Profiles keep the upload rules of the repository that already deploys
that way. The caller passes the bucket, or a stack whose outputs name
the bucket and the distribution. This does not print an account id.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from stack_outputs import ReadError, command as stack_command, decide, redact, select  # noqa: E402

IMMUTABLE = "public,max-age=31536000,immutable"
ROOT_CACHE = "no-cache,must-revalidate"
ASSET_CACHE = "public, max-age=31536000, immutable"
DOCUMENT_CACHE = "public, max-age=300, must-revalidate"
NO_STORE = "no-store, max-age=0"
RELEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
# The document sync already excludes these. Deleting them removes the release
# copy or the hashed assets the asset sync just wrote.
KEPT_DELETE_PREFIXES = frozenset({"releases", "_next"})
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
    return _content_type_hashed(path)


def _cache_routes(key: str) -> str:
    lower = key.lower()
    # Root .js and .css names are not content hashes. An immutable year
    # would keep a previous response after the bytes change.
    if (
        lower.endswith((".html", ".txt", ".xml", ".js", ".css"))
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


def _exclude_args(extra: list[str]) -> list[str]:
    arguments: list[str] = ["--exclude", "_next/static/*", "--exclude", "releases/*"]
    for item in extra:
        arguments.extend(["--exclude", item])
    return arguments


def _sync_uri(run_aws: Runner, source: str, dest: str, extra: list[str]) -> None:
    result = run_aws(["aws", "s3", "sync", source, dest, *extra])
    if result.returncode != 0:
        raise SyncError(_redact(result.stderr or result.stdout or "s3 sync failed"))


def _prefix_exists(run_aws: Runner, bucket: str, prefix: str) -> bool:
    listed = run_aws(
        [
            "aws",
            "s3api",
            "list-objects-v2",
            "--bucket",
            bucket,
            "--prefix",
            prefix,
            "--max-keys",
            "1",
            "--query",
            "KeyCount",
            "--output",
            "text",
        ]
    )
    if listed.returncode != 0:
        raise SyncError(_redact(listed.stderr or listed.stdout or "release listing failed"))
    count = (listed.stdout or "").strip()
    return count not in {"", "0", "None"}


def _parse_s3_uri(value: str) -> tuple[str, str]:
    text = value.strip().rstrip("/")
    if not text.startswith("s3://"):
        raise SyncError(f"promote-from must be an s3 URI. Got: {value}")
    rest = text[len("s3://") :]
    bucket, separator, prefix = rest.partition("/")
    if separator == "" or not bucket or not prefix:
        raise SyncError("promote-from must be s3://bucket/releases/<id>")
    return bucket, prefix


def _remove_prefix(run_aws: Runner, dest: str, name: str) -> None:
    """Delete one directory on the destination before the document sync.

    The trailing slash keeps the match on ``name/`` so a key such as
    ``name-old`` or ``name.json`` stays.
    """
    result = run_aws(["aws", "s3", "rm", f"{dest.rstrip('/')}/{name}/", "--recursive"])
    if result.returncode != 0:
        raise SyncError(_redact(result.stderr or result.stdout or "s3 rm failed"))


def _guard_delete_prefix(name: str, maintenance_assets: str) -> str:
    """Return the directory to delete. Empty means skip the delete."""
    chosen = _path_segment(name, "delete-prefix")
    if not chosen:
        return ""
    if chosen in KEPT_DELETE_PREFIXES:
        raise SyncError("delete-prefix cannot remove releases or _next")
    asset_name = _path_segment(maintenance_assets)
    if asset_name and chosen == asset_name:
        raise SyncError("delete-prefix cannot remove the maintenance-assets directory")
    return chosen


def _with_delete_exclude(excludes: list[str], name: str) -> list[str]:
    """Keep the deleted directory out of the document sync that follows."""
    if not name:
        return excludes
    pattern = f"{name}/*"
    if pattern in excludes:
        return excludes
    return [*excludes, pattern]


def _sync_next_site(
    run_aws: Runner,
    *,
    source: Path | None,
    source_uri: str,
    dest: str,
    extra_excludes: list[str],
    asset_cache: str,
    document_cache: str,
    delete_prefix: str,
) -> None:
    """Match the public-www scripts: immutable hashed assets, then documents."""
    excludes = _exclude_args(extra_excludes)
    if source is not None:
        static = source / "_next" / "static"
        if static.is_dir():
            _sync(
                run_aws,
                static,
                f"{dest}/_next/static",
                ["--cache-control", asset_cache],
            )
    else:
        bucket, prefix = _parse_s3_uri(source_uri)
        if _prefix_exists(run_aws, bucket, f"{prefix}/_next/static/"):
            _sync_uri(
                run_aws,
                f"{source_uri}/_next/static",
                f"{dest}/_next/static",
                ["--cache-control", asset_cache],
            )
    if delete_prefix:
        _remove_prefix(run_aws, dest, delete_prefix)
    document = [*excludes, "--cache-control", document_cache, "--delete"]
    if source is not None:
        _sync(run_aws, source, dest, document)
        return
    _sync_uri(run_aws, source_uri, dest, document)


def _write_release_marker(
    run_aws: Runner,
    bucket: str,
    release_id: str,
    cache: str,
    content_type: str,
) -> None:
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
    handle.write(f"{release_id}\n")
    handle.close()
    path = Path(handle.name)
    try:
        command = [
            "aws",
            "s3",
            "cp",
            str(path),
            f"s3://{bucket}/releases/latest-release-id.txt",
        ]
        if cache:
            command.extend(["--cache-control", cache])
        if content_type:
            command.extend(["--content-type", content_type])
        result = run_aws(command)
        if result.returncode != 0:
            raise SyncError(_redact(result.stderr or result.stdout or "release marker failed"))
    finally:
        path.unlink(missing_ok=True)


def _staging_robots(run_aws: Runner, bucket: str) -> None:
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
    handle.write("User-agent: *\nDisallow: /\n")
    handle.close()
    path = Path(handle.name)
    try:
        _cp(
            run_aws,
            path,
            bucket,
            "robots.txt",
            NO_STORE,
            "text/plain; charset=utf-8",
        )
    finally:
        path.unlink(missing_ok=True)


def _path_segment(value: str, label: str = "maintenance-assets") -> str:
    chosen = value.strip().strip("/")
    if not chosen:
        return ""
    if "/" in chosen or "\\" in chosen or chosen in {".", ".."}:
        raise SyncError(f"{label} must be one directory name")
    return chosen


def _check_release_id(release_id: str) -> str:
    chosen = release_id.strip()
    if chosen and RELEASE_ID.fullmatch(chosen) is None:
        raise SyncError(
            "Release id must be letters, digits, dot, dash, or underscore, "
            f"at most 128 characters. Got: {chosen}"
        )
    return chosen


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
    release_id: str = "",
    release_marker: bool = False,
    staging_robots: bool = False,
    promote_from: str = "",
    sync_exclude: list[str] | None = None,
    asset_cache: str = ASSET_CACHE,
    document_cache: str = DOCUMENT_CACHE,
    marker_cache: str = "",
    marker_content_type: str = "",
    maintenance_assets: str = "",
    maintenance_asset_cache: str = "public, max-age=3600, must-revalidate",
    delete_prefix: str = "",
) -> None:
    bucket = _require_bucket(bucket)
    distribution = _distribution(distribution)
    chosen_release = _check_release_id(release_id)
    promote = promote_from.strip()
    excludes = [item.strip() for item in (sync_exclude or []) if item.strip()]
    prefix_name = _guard_delete_prefix(delete_prefix, maintenance_assets)
    excludes = _with_delete_exclude(excludes, prefix_name)
    if release_marker and not chosen_release:
        raise SyncError("release-marker requires release-id")
    if chosen_release and profile == "maintenance":
        raise SyncError("release-id cannot be used with the maintenance profile")
    if promote and profile != "next-site":
        raise SyncError("promote-from requires profile next-site")
    if promote and chosen_release:
        raise SyncError("promote-from and release-id are mutually exclusive")
    if prefix_name and profile != "next-site":
        raise SyncError("delete-prefix requires profile next-site")
    if dry_run:
        print("Dry run: every s3 command uses --dryrun and CloudFront is not invalidated.")
        run_aws = _dry_run_runner(run_aws)
    if profile == "maintenance":
        if not source.is_dir():
            raise SyncError(f"Build output not found at {source}")
        print(f"Syncing the maintenance site to s3://{bucket}")
        asset_name = _path_segment(maintenance_assets)
        maintenance_extra = ["--exclude", "releases/*"]
        if asset_name:
            asset_dir = source / asset_name
            if asset_dir.is_dir():
                _sync(
                    run_aws,
                    asset_dir,
                    f"s3://{bucket}/{asset_name}",
                    ["--cache-control", maintenance_asset_cache, "--delete"],
                )
            maintenance_extra.extend(["--exclude", f"{asset_name}/*"])
        _sync(
            run_aws,
            source,
            f"s3://{bucket}",
            [*maintenance_extra, "--cache-control", NO_STORE, "--delete"],
        )
        if staging_robots:
            _staging_robots(run_aws, bucket)
        _invalidate(run_aws, distribution, dry_run)
        return
    if profile == "next-site":
        if promote:
            source_bucket, prefix = _parse_s3_uri(promote)
            if not _prefix_exists(run_aws, source_bucket, f"{prefix}/"):
                raise SyncError(f"Release prefix not found: {promote}")
            print(f"Promoting {promote} to s3://{bucket}")
            _sync_next_site(
                run_aws,
                source=None,
                source_uri=promote.rstrip("/"),
                dest=f"s3://{bucket}",
                extra_excludes=excludes,
                asset_cache=asset_cache,
                document_cache=document_cache,
                delete_prefix=prefix_name,
            )
        else:
            if not source.is_dir():
                raise SyncError(f"Build output not found at {source}")
            print(f"Syncing the Next.js site to s3://{bucket}")
            _sync_next_site(
                run_aws,
                source=source,
                source_uri="",
                dest=f"s3://{bucket}",
                extra_excludes=excludes,
                asset_cache=asset_cache,
                document_cache=document_cache,
                delete_prefix=prefix_name,
            )
            if chosen_release:
                print(f"Saving immutable release at releases/{chosen_release}/")
                _sync_next_site(
                    run_aws,
                    source=source,
                    source_uri="",
                    dest=f"s3://{bucket}/releases/{chosen_release}",
                    extra_excludes=excludes,
                    asset_cache=asset_cache,
                    document_cache=document_cache,
                    delete_prefix=prefix_name,
                )
                if release_marker:
                    _write_release_marker(
                        run_aws,
                        bucket,
                        chosen_release,
                        marker_cache,
                        marker_content_type,
                    )
        if staging_robots:
            _staging_robots(run_aws, bucket)
        _invalidate(run_aws, distribution, dry_run)
        return
    if chosen_release or staging_robots or release_marker:
        raise SyncError("release-id and staging-robots require profile next-site or maintenance")
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


def resolve_destination(
    *,
    bucket: str,
    distribution: str,
    stack: str,
    region: str,
    bucket_output: str,
    distribution_output: str,
    run_aws: Runner,
) -> tuple[str, str]:
    """Return the bucket and distribution. A stack replaces both."""
    if not stack.strip():
        return bucket, distribution
    keys = bucket_output.strip()
    if distribution_output.strip():
        keys = f"{keys},{distribution_output.strip()}"
    try:
        chosen_stack, chosen_region, names = decide(stack, region, keys)
    except ReadError as exc:
        raise SyncError(str(exc)) from exc
    completed = run_aws(stack_command(chosen_stack, chosen_region))
    if completed.returncode != 0:
        detail = redact((completed.stderr or "") + (completed.stdout or "")).strip()
        message = f"Could not read stack {chosen_stack} in {chosen_region}."
        if detail:
            message = f"{message} {detail}"
        raise SyncError(message)
    try:
        found = select(completed.stdout or "", [names[0]])
    except ReadError as exc:
        raise SyncError(str(exc)) from exc
    resolved_bucket = found[names[0]]
    resolved_distribution = distribution
    if len(names) > 1:
        try:
            resolved_distribution = select(completed.stdout or "", [names[1]])[names[1]]
        except ReadError as exc:
            print(f"::warning::{exc} CloudFront invalidation will be skipped.")
            resolved_distribution = ""
    return resolved_bucket, resolved_distribution


def main(run_aws: Runner = _run_aws) -> int:
    source_text = os.environ.get("SOURCE", "").strip()
    promote = os.environ.get("PROMOTE_FROM", "").strip()
    if not source_text and not promote:
        print("source is required unless promote-from is set", file=sys.stderr)
        return 1
    source = Path(source_text) if source_text else Path(".")
    bucket = os.environ.get("BUCKET", "")
    distribution = os.environ.get("DISTRIBUTION_ID", "")
    try:
        bucket, distribution = resolve_destination(
            bucket=bucket,
            distribution=distribution,
            stack=os.environ.get("STACK", ""),
            region=os.environ.get("AWS_REGION", ""),
            bucket_output=os.environ.get("BUCKET_OUTPUT", "") or "PublicWebsiteBucketName",
            distribution_output=os.environ.get("DISTRIBUTION_OUTPUT", ""),
            run_aws=run_aws,
        )
    except SyncError as error:
        print(str(error), file=sys.stderr)
        return 1
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
            release_id=os.environ.get("RELEASE_ID", ""),
            release_marker=os.environ.get("RELEASE_MARKER", "false").lower() == "true",
            staging_robots=os.environ.get("STAGING_ROBOTS", "false").lower() == "true",
            promote_from=os.environ.get("PROMOTE_FROM", ""),
            sync_exclude=[
                item.strip()
                for item in os.environ.get("SYNC_EXCLUDE", "").split(",")
                if item.strip()
            ],
            asset_cache=os.environ.get("ASSET_CACHE", "") or ASSET_CACHE,
            document_cache=os.environ.get("DOCUMENT_CACHE", "") or DOCUMENT_CACHE,
            marker_cache=os.environ.get("MARKER_CACHE", ""),
            marker_content_type=os.environ.get("MARKER_CONTENT_TYPE", ""),
            maintenance_assets=os.environ.get("MAINTENANCE_ASSETS", ""),
            maintenance_asset_cache=os.environ.get("MAINTENANCE_ASSET_CACHE", "")
            or "public, max-age=3600, must-revalidate",
            delete_prefix=os.environ.get("DELETE_PREFIX", ""),
        )
    except SyncError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
