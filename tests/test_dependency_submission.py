"""Dependency snapshot covers pins, lockfiles, and action uses."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "dependency-graph" / "snapshot.py"
_SPEC = importlib.util.spec_from_file_location("dependency_snapshot", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
snapshot = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(snapshot)

SHA = "a" * 40
REF = "refs/heads/main"


class DependencyGraphTest(unittest.TestCase):
    def test_pass_fixture_lists_each_ecosystem(self) -> None:
        base = ROOT / "fixtures" / "dependency-graph" / "pass"
        files = [
            base / "requirements.txt",
            base / "package-lock.json",
            base / "workflow.yml",
            base / "action.yml",
        ]
        built, errors = snapshot.build_snapshot(files, SHA, REF, "1")
        self.assertEqual(errors, [])
        purls = {
            item["package_url"]
            for manifest in built["manifests"].values()
            for item in manifest["resolved"].values()
        }
        self.assertIn("pkg:pypi/demo@1.2.3", purls)
        self.assertIn("pkg:npm/left@1.0.0", purls)
        self.assertIn("pkg:npm/right@2.0.0", purls)
        self.assertIn(
            "pkg:githubactions/actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            purls,
        )
        self.assertNotIn(
            "pkg:githubactions/actions/setup-python@a26af69be951a213d495a4c5e4e4022e16d87065",
            purls,
        )
        self.assertNotIn(
            "workflow.yml", {Path(name).name for name in built["manifests"]}
        )
        left = next(item for item in purls if item.endswith("left@1.0.0"))
        right = next(
            entry
            for manifest in built["manifests"].values()
            for entry in manifest["resolved"].values()
            if entry["package_url"].endswith("right@2.0.0")
        )
        self.assertEqual(left, "pkg:npm/left@1.0.0")
        self.assertEqual(right["relationship"], "indirect")
        self.assertEqual(right["scope"], "development")
        self.assertEqual(built["version"], 0)
        self.assertEqual(built["job"]["correlator"], "lx-dependency-graph")

    def test_follows_a_requirements_include(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "extra.txt").write_text("extra==2\n", encoding="utf-8")
            start = root / "requirements.txt"
            start.write_text("-r extra.txt\n", encoding="utf-8")
            resolved, errors = snapshot.parse_requirements(start)
            self.assertEqual(errors, [])
            self.assertIn("pkg:pypi/extra@2", resolved)

    def test_ignore_drops_an_unpinned_requirements_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            start = root / "requirements.txt"
            start.write_text("demo==1\n", encoding="utf-8")
            kept, errors = snapshot.select_files(root, [], ["./requirements.txt"])
            self.assertEqual(errors, [])
            self.assertEqual(kept, [])
            kept, errors = snapshot.select_files(root, [], ["missing.txt"])
            self.assertEqual(kept, [start])
            self.assertEqual(errors, ["ignore path matches nothing: missing.txt"])

    def test_unpinned_requirement_is_an_error(self) -> None:
        path = ROOT / "fixtures" / "dependency-graph" / "fail" / "requirements.txt"
        _resolved, errors = snapshot.parse_requirements(path)
        self.assertTrue(any("unpinned" in error for error in errors))

    def test_unpinned_action_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text(
                "jobs:\n  a:\n    steps:\n      - uses: actions/checkout\n",
                encoding="utf-8",
            )
            _resolved, errors = snapshot.parse_actions(path)
            self.assertTrue(any("unpinned" in error for error in errors))

    def test_tag_ref_is_not_a_commit_pin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text(
                "jobs:\n  a:\n    steps:\n      - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            _resolved, errors = snapshot.parse_actions(path)
            self.assertTrue(any("not a commit" in error for error in errors))

    def test_manifest_paths_are_relative_to_the_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "backend" / "requirements.txt"
            requirements.parent.mkdir()
            requirements.write_text("demo==1\n", encoding="utf-8")
            built, errors = snapshot.build_snapshot(
                [requirements.resolve()], SHA, REF, "1", root
            )
            self.assertEqual(errors, [])
            location = "backend/requirements.txt"
            self.assertEqual(list(built["manifests"]), [location])
            self.assertEqual(
                built["manifests"][location]["file"]["source_location"], location
            )

    def test_quoted_sha_and_reusable_workflow_are_accepted(self) -> None:
        path = ROOT / "fixtures" / "dependency-graph" / "pass" / "workflow.yml"
        resolved, errors = snapshot.parse_actions(path)
        self.assertEqual(errors, [])
        self.assertEqual(resolved, {})
        built, build_errors = snapshot.build_snapshot([path], SHA, REF, "1")
        self.assertEqual(build_errors, [])
        self.assertEqual(built["manifests"], {})

    def test_discover_skips_fixtures(self) -> None:
        found = snapshot.discover(ROOT)
        self.assertTrue(found)
        self.assertTrue(all("fixtures" not in path.parts for path in found))

    def test_post_reports_a_rejected_snapshot_without_leaking_the_token(self) -> None:
        def fake_open(request, timeout=30):
            self.assertEqual(timeout, 30)
            self.assertIn("Bearer secret-token", request.get_header("Authorization"))
            body = request.data.decode("utf-8")
            self.assertNotIn("secret-token", body)
            self.assertEqual(json.loads(body)["version"], 0)
            raise snapshot.urllib.error.HTTPError(
                request.full_url,
                422,
                "no",
                hdrs=None,
                fp=io.BytesIO(b'{"message":"disabled"}'),
            )

        original = snapshot.urllib.request.urlopen
        snapshot.urllib.request.urlopen = fake_open
        try:
            with redirect_stderr(io.StringIO()) as caught:
                status = snapshot.post_snapshot(
                    {"version": 0}, "lx-software-ltd/actions", "secret-token"
                )
        finally:
            snapshot.urllib.request.urlopen = original
        self.assertEqual(status, 1)
        self.assertIn("disabled", caught.getvalue())
        self.assertNotIn("secret-token", caught.getvalue())


if __name__ == "__main__":
    unittest.main()
