"""S3 sync profiles keep the current upload rules and hide account ids."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "s3-cloudfront-deploy"))

import s3_sync  # noqa: E402


def _ok(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["aws"], returncode=0, stdout=stdout, stderr="")


class SyncProfileTest(unittest.TestCase):
    def _tree(self, root: Path) -> None:
        (root / "assets").mkdir()
        (root / "assets" / "app.js").write_text("js", encoding="utf-8")
        (root / "index.html").write_text("<html>", encoding="utf-8")
        (root / "favicon.ico").write_text("ico", encoding="utf-8")

    def test_public_hashed_uploads_index_last_and_prunes(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[1:3] == ["s3api", "list-objects-v2"]:
                return _ok("index.html\tfavicon.ico\told.txt\n")
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="E123",
                profile="public-hashed",
                indexnow=False,
                run_aws=run_aws,
            )
        kinds = [(call[1], call[2]) for call in calls]
        self.assertEqual(kinds[0], ("s3", "sync"))
        self.assertIn("--delete", calls[0])
        self.assertIn("public,max-age=31536000,immutable", calls[0])
        copied = [call for call in calls if call[1:3] == ["s3", "cp"]]
        self.assertEqual(copied[-1][4], "s3://site-bucket/index.html")
        self.assertIn("--content-type", copied[-1])
        self.assertIn("text/html; charset=utf-8", copied[-1])
        self.assertIn(["aws", "s3", "rm", "s3://site-bucket/old.txt"], calls)
        self.assertEqual(calls[-1][1:3], ["cloudfront", "create-invalidation"])
        self.assertIn("E123", calls[-1])

    def test_a_failed_root_listing_fails_the_deploy(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            if command[1:3] == ["s3api", "list-objects-v2"]:
                return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="AccessDenied")
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            with self.assertRaises(s3_sync.SyncError) as caught:
                s3_sync.deploy(
                    source=source,
                    bucket="site-bucket",
                    distribution="E123",
                    profile="public-hashed",
                    indexnow=False,
                    run_aws=run_aws,
                )
        self.assertIn("AccessDenied", str(caught.exception))

    def test_admin_hashed_skips_content_type_on_other_files_and_does_not_prune(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            s3_sync.deploy(
                source=source,
                bucket="admin-bucket",
                distribution="",
                profile="admin-hashed",
                indexnow=False,
                run_aws=run_aws,
            )
        self.assertFalse(any(call[1] == "s3api" for call in calls))
        self.assertFalse(any(call[1:3] == ["cloudfront", "create-invalidation"] for call in calls))
        favicon = next(call for call in calls if call[4].endswith("/favicon.ico"))
        self.assertNotIn("--content-type", favicon)
        self.assertIn("public,max-age=31536000,immutable", favicon)
        index = next(call for call in calls if call[4].endswith("/index.html"))
        self.assertIn("no-cache,must-revalidate", index)

    def test_admin_hashed_skips_dotfiles(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            (source / ".gitkeep").write_text("", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="admin-bucket",
                distribution="",
                profile="admin-hashed",
                indexnow=False,
                run_aws=run_aws,
            )
        dests = [call[4] for call in calls if call[1:3] == ["s3", "cp"]]
        self.assertFalse(any(dest.endswith("/.gitkeep") for dest in dests))
        self.assertTrue(any(dest.endswith("/favicon.ico") for dest in dests))

    def test_next_export_syncs_the_tree_and_deletes(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "index.html").write_text("<html>", encoding="utf-8")
            (source / "_next").mkdir()
            (source / "_next" / "chunk.js").write_text("js", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="admin-bucket",
                distribution="E123",
                profile="next-export",
                indexnow=False,
                run_aws=run_aws,
            )
        self.assertEqual(calls[0][1:3], ["s3", "sync"])
        self.assertEqual(calls[0][3], str(source))
        self.assertEqual(calls[0][4], "s3://admin-bucket")
        self.assertEqual(calls[0][5:], ["--delete"])
        self.assertEqual(calls[1][1:3], ["cloudfront", "create-invalidation"])
        self.assertIn("/*", calls[1])

    def test_public_routes_writes_extensionless_keys_and_media(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            (source / "about.html").write_text("about", encoding="utf-8")
            (source / "app.js").write_text("js", encoding="utf-8")
            (source / "app.css").write_text("css", encoding="utf-8")
            (source / "site.webmanifest").write_text("{}", encoding="utf-8")
            (source / "media").mkdir()
            (source / "media" / "clip.mp4").write_text("m", encoding="utf-8")
            (source / "images").mkdir()
            (source / "images" / "logo.png").write_text("p", encoding="utf-8")
            (source / "images" / "widget.js").write_text("js", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="None",
                profile="public-routes",
                indexnow=False,
                run_aws=run_aws,
            )
        dests = [call[4] for call in calls if call[1:3] == ["s3", "cp"]]
        self.assertIn("s3://site-bucket/about", dests)
        self.assertIn("s3://site-bucket/images/logo.png", dests)
        media = next(call for call in calls if call[3].endswith("/media"))
        self.assertIn("--size-only", media)
        self.assertIn("--delete", media)
        asset_syncs = [call for call in calls if call[3].endswith("/assets")]
        self.assertEqual(len(asset_syncs), 2)
        self.assertNotIn("--delete", asset_syncs[0])
        self.assertIn("--delete", asset_syncs[1])
        self.assertTrue(all("--content-type" not in call for call in asset_syncs))

        def header(dest: str, name: str) -> str:
            matches = [call for call in calls if call[1:3] == ["s3", "cp"] and call[4] == dest]
            self.assertEqual(len(matches), 1, dest)
            call = matches[0]
            self.assertIn(name, call, dest)
            return call[call.index(name) + 1]

        self.assertEqual(
            header("s3://site-bucket/app.js", "--content-type"),
            "text/javascript; charset=utf-8",
        )
        self.assertEqual(header("s3://site-bucket/app.js", "--cache-control"), "no-cache")
        self.assertEqual(
            header("s3://site-bucket/app.css", "--content-type"),
            "text/css; charset=utf-8",
        )
        self.assertEqual(header("s3://site-bucket/app.css", "--cache-control"), "no-cache")
        self.assertEqual(
            header("s3://site-bucket/images/widget.js", "--content-type"),
            "text/javascript; charset=utf-8",
        )
        self.assertEqual(
            header("s3://site-bucket/images/widget.js", "--cache-control"),
            "no-cache",
        )
        self.assertEqual(
            header("s3://site-bucket/site.webmanifest", "--content-type"),
            "application/manifest+json",
        )
        self.assertEqual(
            header("s3://site-bucket/favicon.ico", "--cache-control"),
            s3_sync.IMMUTABLE,
        )
        self.assertFalse(any(call[1] == "cloudfront" for call in calls))

    def test_a_missing_build_does_not_call_aws(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with self.assertRaises(s3_sync.SyncError):
            s3_sync.deploy(
                source=Path("/tmp/does-not-exist-s3-sync"),
                bucket="site-bucket",
                distribution="E123",
                profile="public-hashed",
                indexnow=False,
                run_aws=run_aws,
            )
        self.assertEqual(calls, [])

    def test_aws_errors_hide_an_account_id(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=254,
                stdout="",
                stderr="account 123456789012 denied",
            )

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            env = {
                "SOURCE": str(source),
                "BUCKET": "site-bucket",
                "DISTRIBUTION_ID": "E123",
                "PROFILE": "public-hashed",
                "INDEXNOW": "false",
            }
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch("sys.stderr") as stderr:
                    code = s3_sync.main(run_aws)
        self.assertEqual(code, 1)
        text = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertNotIn("123456789012", text)
        self.assertIn("************", text)

    def test_dry_run_plans_s3_changes_and_skips_invalidation(self) -> None:
        calls: list[list[str]] = []
        printed: list[str] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[1:3] == ["s3api", "list-objects-v2"]:
                return _ok("index.html\told.txt\n")
            if command[1:3] == ["s3", "rm"]:
                return _ok("(dryrun) delete: s3://site-bucket/old.txt\n")
            return _ok("(dryrun) upload: dist/index.html to s3://site-bucket/index.html\n")

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            with mock.patch("builtins.print", side_effect=lambda *args, **kwargs: printed.append(" ".join(map(str, args)))):
                s3_sync.deploy(
                    source=source,
                    bucket="site-bucket",
                    distribution="E123",
                    profile="public-hashed",
                    indexnow=False,
                    dry_run=True,
                    run_aws=run_aws,
                )
        s3_calls = [call for call in calls if call[1] == "s3"]
        self.assertTrue(s3_calls)
        self.assertTrue(all(call[3] == "--dryrun" for call in s3_calls))
        self.assertTrue(any(call[1:3] == ["s3api", "list-objects-v2"] for call in calls))
        self.assertFalse(any(call[1] == "cloudfront" for call in calls))
        self.assertIn("(dryrun) delete: s3://site-bucket/old.txt", "\n".join(printed))
        self.assertTrue(any("skipping CloudFront invalidation" in line for line in printed))

    def test_main_reads_the_profile_from_the_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            env = {
                "SOURCE": str(source),
                "BUCKET": "",
                "DISTRIBUTION_ID": "",
                "PROFILE": "admin-hashed",
                "INDEXNOW": "false",
            }
            with mock.patch.dict("os.environ", env, clear=False):
                code = s3_sync.main(lambda command: _ok())
        self.assertEqual(code, 1)

    def test_stack_outputs_replace_the_bucket_and_distribution(self) -> None:
        document = json.dumps(
            {
                "Stacks": [
                    {
                        "Outputs": [
                            {"OutputKey": "PublicWebsiteBucketName", "OutputValue": "from-stack"},
                            {"OutputKey": "PublicWebsiteDistributionId", "OutputValue": "E999"},
                        ]
                    }
                ]
            }
        )
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[1] == "cloudformation":
                return _ok(document)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            bucket, distribution = s3_sync.resolve_destination(
                bucket="",
                distribution="",
                stack="findingalpha-public-www",
                region="ap-east-1",
                bucket_output="PublicWebsiteBucketName",
                distribution_output="PublicWebsiteDistributionId",
                run_aws=run_aws,
            )
            self.assertEqual(bucket, "from-stack")
            self.assertEqual(distribution, "E999")
            self.assertEqual(calls[0][1], "cloudformation")
            bucket_only = {
                "Stacks": [
                    {
                        "Outputs": [
                            {"OutputKey": "PublicWebsiteBucketName", "OutputValue": "from-stack"}
                        ]
                    }
                ]
            }
            with mock.patch("sys.stdout", new_callable=io.StringIO) as printed:
                bucket, distribution = s3_sync.resolve_destination(
                    bucket="",
                    distribution="",
                    stack="findingalpha-public-www",
                    region="ap-east-1",
                    bucket_output="PublicWebsiteBucketName",
                    distribution_output="PublicWebsiteDistributionId",
                    run_aws=lambda command: _ok(json.dumps(bucket_only)),
                )
            self.assertEqual(bucket, "from-stack")
            self.assertEqual(distribution, "")
            self.assertIn("::warning::", printed.getvalue())
            self.assertIn("CloudFront invalidation will be skipped", printed.getvalue())

    def test_next_site_copies_a_release_and_writes_robots(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            static = source / "_next" / "static"
            static.mkdir(parents=True)
            (static / "app.js").write_text("js", encoding="utf-8")
            (source / "index.html").write_text("<html>", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="E123",
                profile="next-site",
                indexnow=False,
                run_aws=run_aws,
                release_id="2026.11.24",
                release_marker=True,
                staging_robots=True,
                sync_exclude=["landing-pages-manifest.json"],
            )
        syncs = [call for call in calls if call[1:3] == ["s3", "sync"]]
        self.assertEqual(syncs[0][3], str(static))
        self.assertIn("public, max-age=31536000, immutable", syncs[0])
        self.assertIn("--exclude", syncs[1])
        self.assertIn("landing-pages-manifest.json", syncs[1])
        self.assertIn("public, max-age=300, must-revalidate", syncs[1])
        self.assertIn("--delete", syncs[1])
        self.assertTrue(any(call[4].endswith("/releases/2026.11.24") for call in syncs if len(call) > 4))
        marker = [call for call in calls if call[-1].endswith("latest-release-id.txt")]
        self.assertEqual(len(marker), 1)
        self.assertNotIn("--cache-control", marker[0])
        robots = [call for call in calls if call[4] == "s3://site-bucket/robots.txt"]
        self.assertIn("text/plain; charset=utf-8", robots[0])
        self.assertIn("no-store, max-age=0", robots[0])
        self.assertEqual(calls[-1][1:3], ["cloudfront", "create-invalidation"])

    def test_promote_requires_the_release_prefix(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            if command[1:3] == ["s3api", "list-objects-v2"]:
                return _ok("0\n")
            return _ok()

        with self.assertRaises(s3_sync.SyncError) as caught:
            s3_sync.deploy(
                source=Path("."),
                bucket="site-bucket",
                distribution="",
                profile="next-site",
                indexnow=False,
                run_aws=run_aws,
                promote_from="s3://staging-bucket/releases/2026.11.24",
            )
        self.assertIn("not found", str(caught.exception))

    def test_maintenance_excludes_releases(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "index.html").write_text("down", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="",
                profile="maintenance",
                indexnow=False,
                run_aws=run_aws,
            )
        self.assertIn("--exclude", calls[0])
        self.assertIn("releases/*", calls[0])
        self.assertIn("no-store, max-age=0", calls[0])
        self.assertIn("--delete", calls[0])

    def test_maintenance_assets_sync_before_the_page(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            images = source / "images"
            images.mkdir()
            (images / "logo.svg").write_text("<svg>", encoding="utf-8")
            (source / "index.html").write_text("down", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="",
                profile="maintenance",
                indexnow=False,
                run_aws=run_aws,
                maintenance_assets="images",
            )
        self.assertEqual(calls[0][4], "s3://site-bucket/images")
        self.assertIn("public, max-age=3600, must-revalidate", calls[0])
        self.assertIn("images/*", calls[1])
        self.assertIn("no-store, max-age=0", calls[1])

    def test_document_cache_and_marker_headers(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        document = "public, max-age=300, must-revalidate, stale-while-revalidate=60"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "index.html").write_text("<html>", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="",
                profile="next-site",
                indexnow=False,
                run_aws=run_aws,
                release_id="2026.11.24",
                release_marker=True,
                document_cache=document,
                marker_cache=s3_sync.NO_STORE,
                marker_content_type="text/plain; charset=utf-8",
            )
        documents = [call for call in calls if document in call]
        self.assertGreaterEqual(len(documents), 1)
        marker = [
            call
            for call in calls
            if any(item.endswith("latest-release-id.txt") for item in call)
        ]
        self.assertIn(s3_sync.NO_STORE, marker[0])
        self.assertIn("text/plain; charset=utf-8", marker[0])

    def test_promote_allows_an_empty_source(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            if command[1:3] == ["s3api", "list-objects-v2"]:
                return _ok("1\n")
            return _ok()

        env = {
            "SOURCE": "",
            "BUCKET": "site-bucket",
            "DISTRIBUTION_ID": "",
            "STACK": "",
            "PROFILE": "next-site",
            "PROMOTE_FROM": "s3://staging-bucket/releases/2026.11.24",
            "DRY_RUN": "false",
            "INDEXNOW": "false",
            "RELEASE_ID": "",
            "RELEASE_MARKER": "false",
            "STAGING_ROBOTS": "false",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            self.assertEqual(s3_sync.main(run_aws), 0)
        env["PROMOTE_FROM"] = ""
        with mock.patch.dict(os.environ, env, clear=False):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as printed:
                status = s3_sync.main(run_aws)
            self.assertEqual(status, 1)
            self.assertIn("source is required", printed.getvalue())

    def test_a_release_id_with_maintenance_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(s3_sync.SyncError):
                s3_sync.deploy(
                    source=Path(tmp),
                    bucket="site-bucket",
                    distribution="",
                    profile="maintenance",
                    indexnow=False,
                    run_aws=lambda command: _ok(),
                    release_id="bad id",
                )

    def test_delete_prefix_runs_between_the_asset_sync_and_the_document_sync(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            static = source / "_next" / "static"
            static.mkdir(parents=True)
            (static / "app.js").write_text("js", encoding="utf-8")
            (source / "index.html").write_text("<html>", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="",
                profile="next-site",
                indexnow=False,
                run_aws=run_aws,
                release_id="2026.11.24",
                sync_exclude=["fixtures/*"],
                delete_prefix="fixtures",
            )
        removals = [call for call in calls if call[1:3] == ["s3", "rm"]]
        self.assertEqual(
            removals,
            [
                ["aws", "s3", "rm", "s3://site-bucket/fixtures", "--recursive"],
                ["aws", "s3", "rm", "s3://site-bucket/releases/2026.11.24/fixtures", "--recursive"],
            ],
        )
        for call in calls:
            if call[1:3] != ["s3", "rm"]:
                continue
            index = calls.index(call)
            self.assertTrue(calls[index - 1][4].endswith("/_next/static"))
            document = calls[index + 1]
            self.assertEqual(document[1:3], ["s3", "sync"])
            self.assertIn("fixtures/*", document)
            self.assertIn("--delete", document)

    def test_promote_deletes_the_prefix_on_the_destination(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[1:3] == ["s3api", "list-objects-v2"]:
                return _ok("1\n")
            return _ok()

        s3_sync.deploy(
            source=Path("."),
            bucket="site-bucket",
            distribution="",
            profile="next-site",
            indexnow=False,
            run_aws=run_aws,
            promote_from="s3://staging-bucket/releases/2026.11.24",
            sync_exclude=["fixtures/*"],
            delete_prefix="fixtures",
        )
        self.assertEqual(
            [(call[1], call[2]) for call in calls],
            [
                ("s3api", "list-objects-v2"),
                ("s3api", "list-objects-v2"),
                ("s3", "sync"),
                ("s3", "rm"),
                ("s3", "sync"),
            ],
        )
        self.assertEqual(calls[3], ["aws", "s3", "rm", "s3://site-bucket/fixtures", "--recursive"])
        self.assertTrue(calls[2][3].endswith("/_next/static"))
        self.assertIn("fixtures/*", calls[4])
        self.assertIn("--delete", calls[4])

    def test_delete_prefix_runs_without_hashed_assets(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "index.html").write_text("<html>", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="",
                profile="next-site",
                indexnow=False,
                run_aws=run_aws,
                delete_prefix="fixtures",
            )
        self.assertEqual(calls[0], ["aws", "s3", "rm", "s3://site-bucket/fixtures", "--recursive"])
        self.assertEqual(calls[1][1:3], ["s3", "sync"])

    def test_an_empty_delete_prefix_issues_no_remove(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            static = source / "_next" / "static"
            static.mkdir(parents=True)
            (static / "app.js").write_text("js", encoding="utf-8")
            (source / "index.html").write_text("<html>", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="",
                profile="next-site",
                indexnow=False,
                run_aws=run_aws,
            )
        self.assertFalse(any(call[1:3] == ["s3", "rm"] for call in calls))

    def test_delete_prefix_requires_next_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self._tree(source)
            with self.assertRaises(s3_sync.SyncError) as caught:
                s3_sync.deploy(
                    source=source,
                    bucket="site-bucket",
                    distribution="",
                    profile="public-hashed",
                    indexnow=False,
                    run_aws=lambda command: _ok(),
                    delete_prefix="fixtures",
                )
        self.assertIn("delete-prefix requires profile next-site", str(caught.exception))

    def test_delete_prefix_is_one_directory_name(self) -> None:
        with self.assertRaises(s3_sync.SyncError) as caught:
            s3_sync.deploy(
                source=Path("."),
                bucket="site-bucket",
                distribution="",
                profile="next-site",
                indexnow=False,
                run_aws=lambda command: _ok(),
                delete_prefix="fixtures/other",
            )
        self.assertIn("delete-prefix must be one directory name", str(caught.exception))

    def test_dry_run_plans_the_prefix_delete(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok("(dryrun) delete: s3://site-bucket/fixtures/index.html\n")

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "index.html").write_text("<html>", encoding="utf-8")
            s3_sync.deploy(
                source=source,
                bucket="site-bucket",
                distribution="",
                profile="next-site",
                indexnow=False,
                dry_run=True,
                run_aws=run_aws,
                delete_prefix="fixtures",
            )
        removal = [call for call in calls if call[2] == "rm"]
        self.assertEqual(
            removal,
            [["aws", "s3", "rm", "--dryrun", "s3://site-bucket/fixtures", "--recursive"]],
        )

    def test_a_failed_prefix_delete_fails_the_deploy(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            if command[1:3] == ["s3", "rm"]:
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=1,
                    stdout="",
                    stderr="AccessDenied for 123456789012",
                )
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "index.html").write_text("<html>", encoding="utf-8")
            with self.assertRaises(s3_sync.SyncError) as caught:
                s3_sync.deploy(
                    source=source,
                    bucket="site-bucket",
                    distribution="",
                    profile="next-site",
                    indexnow=False,
                    run_aws=run_aws,
                    delete_prefix="fixtures",
                )
        self.assertNotIn("123456789012", str(caught.exception))
        self.assertIn("************", str(caught.exception))

    def test_main_reads_delete_prefix(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _ok()

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "index.html").write_text("<html>", encoding="utf-8")
            env = {
                "SOURCE": str(source),
                "BUCKET": "site-bucket",
                "DISTRIBUTION_ID": "",
                "STACK": "",
                "PROFILE": "next-site",
                "DELETE_PREFIX": "fixtures",
                "SYNC_EXCLUDE": "fixtures/*",
                "DRY_RUN": "false",
                "INDEXNOW": "false",
                "PROMOTE_FROM": "",
                "RELEASE_ID": "",
                "RELEASE_MARKER": "false",
                "STAGING_ROBOTS": "false",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                self.assertEqual(s3_sync.main(run_aws), 0)
        self.assertEqual(calls[0], ["aws", "s3", "rm", "s3://site-bucket/fixtures", "--recursive"])
        self.assertIn("fixtures/*", calls[1])
