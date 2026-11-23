"""bump_pins moves workflow pins and the pre-commit rev together."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "scripts" / "bump_pins.py"
_SPEC = importlib.util.spec_from_file_location("bump_pins", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
bump_pins = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bump_pins)

OLD = "a" * 40
NEW = "b" * 40


class BumpPinsTest(unittest.TestCase):
    def test_rewrites_the_pin_the_date_and_the_rev(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "lint.yml").write_text(
                f"uses: lx-software-ltd/actions/require-jobs@{OLD} # main 2026-11-20\n"
                f"uses: actions/checkout@{OLD} # v1\n",
                encoding="utf-8",
            )
            (root / ".pre-commit-config.yaml").write_text(
                "repos:\n"
                "  - repo: https://github.com/lx-software-ltd/actions\n"
                f"    rev: {OLD}\n"
                "    hooks:\n"
                "      - id: check-pii\n"
                "  - repo: https://github.com/pre-commit/pre-commit-hooks\n"
                "    rev: v5.0.0\n",
                encoding="utf-8",
            )
            self.assertEqual(bump_pins.bump(root, NEW, "2026-11-23"), 2)
            lint = (workflows / "lint.yml").read_text(encoding="utf-8")
            self.assertIn(f"require-jobs@{NEW} # main 2026-11-23", lint)
            self.assertIn(f"actions/checkout@{OLD}", lint)
            config = (root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
            self.assertIn(f"rev: {NEW}", config)
            self.assertIn("rev: v5.0.0", config)

    def test_rejects_a_short_sha(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github" / "workflows").mkdir(parents=True)
            with self.assertRaises(ValueError):
                bump_pins.bump(root, "abc", "2026-11-23")

    def test_rejects_a_sha_that_is_not_on_main(self) -> None:
        sha = "c" * 40
        with self.assertRaises(ValueError):
            bump_pins.require_sha_on_main(sha, lambda _sha: "behind")
        with self.assertRaises(ValueError):
            bump_pins.require_sha_on_main(sha, lambda _sha: "diverged")

    def test_accepts_a_sha_that_main_contains(self) -> None:
        sha = "d" * 40
        bump_pins.require_sha_on_main(sha, lambda _sha: "ahead")
        bump_pins.require_sha_on_main(sha, lambda _sha: "identical")


if __name__ == "__main__":
    unittest.main()
