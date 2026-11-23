"""The harness matches the messages of the scripts it replaces."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "agent-harness" / "check_harness.py"
_SPEC = importlib.util.spec_from_file_location("check_harness", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
harness = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(harness)

LENGTH = {
    "allowlist": "scripts/file-length-allowlist.txt",
    "python-limit": 500,
    "typescript-limit": 800,
    "python-prefix": "backend/lambda/",
    "typescript-app-prefix": "apps/",
    "typescript-lib-prefix": "backend/infrastructure/lib/",
    "generated-suffix": "src/lib/contracts/generated.ts",
    "scan-roots": ["backend/lambda"],
}


class AgentHarnessTest(unittest.TestCase):
    def test_pass_fixture_is_clean(self) -> None:
        root = ROOT / "fixtures" / "agent-harness" / "pass"
        errors = harness.run(root, root / ".github" / "harness.json")
        self.assertEqual(errors, [])

    def test_missing_why_uses_the_file_line(self) -> None:
        root = ROOT / "fixtures" / "agent-harness" / "fail"
        errors = harness.run(root, root / ".github" / "harness.json")
        self.assertIn("00-repository-core.mdc:6 rule bullet is missing [why:]", errors)

    def test_file_length_reports_growth(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "backend" / "lambda"
            target.mkdir(parents=True)
            source = target / "app.py"
            source.write_text("\n".join(["x"] * 501) + "\n", encoding="utf-8")
            errors = harness.check_file_length(root, LENGTH)
            self.assertEqual(
                errors,
                ["backend/lambda/app.py is 501 lines (limit 500); split it or, if it already exists, allowlist 501"],
            )

    def test_typed_skips_alembic_and_does_not_need_a_typescript_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            versions = root / "backend" / "src" / "alembic" / "versions"
            versions.mkdir(parents=True)
            (versions / "rev.py").write_text("\n".join(["x"] * 600) + "\n", encoding="utf-8")
            app = root / "backend" / "src" / "app.py"
            app.write_text("\n".join(["x"] * 501) + "\n", encoding="utf-8")
            page = root / "apps" / "web" / "src" / "page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text("\n".join(["x"] * 900) + "\n", encoding="utf-8")
            errors = harness.check_file_length(
                root,
                {
                    "mode": "typed",
                    "python-limit": 500,
                    "python-prefix": "backend/",
                    "allowlist": "missing.txt",
                    "scan-roots": ["backend/src", "apps"],
                },
            )
            self.assertEqual(
                errors,
                ["backend/src/app.py is 501 lines (limit 500); split it or, if it already exists, allowlist 501"],
            )

    def test_other_file_length_modes_are_rejected(self) -> None:
        errors = harness.check_file_length(Path("."), {"mode": "python-counted"})
        self.assertEqual(errors, ["file-length mode must be typed, got python-counted"])

    def test_a_placeholder_prefix_is_rejected(self) -> None:
        errors = harness.check_file_length(
            Path("."),
            {"mode": "typed", "typescript-app-prefix": "apps/__not_scanned__/", "allowlist": "missing.txt"},
        )
        self.assertEqual(errors, ["file-length typescript-app-prefix is a placeholder. Omit the key."])

    def test_help_exits_without_scanning(self) -> None:
        with mock.patch("sys.stdout"):
            with self.assertRaises(SystemExit) as raised:
                harness.main(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_an_unknown_argument_is_an_error(self) -> None:
        with mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit) as raised:
                harness.main(["--not-a-flag"])
        self.assertEqual(raised.exception.code, 2)

    def test_python_fit_and_a_conditional_skip_are_not_focused_tests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "apps"
            source.mkdir()
            (source / "image.py").write_text("ImageOps.fit(image, (1, 1))\n", encoding="utf-8")
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_app.py").write_text(
                "ImageOps.fit(image, (1, 1))\n"
                "def test_one():\n"
                "    test.skip(missing, 'reason')\n"
                "    test.skip('reason')\n",
                encoding="utf-8",
            )
            errors = harness.check_test_focus(
                root,
                {
                    "mode": "test-names",
                    "roots": ["apps", "tests"],
                    "suffixes": [".py"],
                    "skip-parts": ["node_modules"],
                },
            )
        self.assertEqual(errors, ["tests/test_app.py:4: test.skip('reason')"])


if __name__ == "__main__":
    unittest.main()
