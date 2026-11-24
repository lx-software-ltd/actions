#!/usr/bin/env python3
"""The drift counter reports real differences and fails closed."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_template_drift.py"


def _run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


class TemplateDriftTest(unittest.TestCase):
    def test_help_exits_without_a_zero_report(self) -> None:
        result = _run(["--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stderr)
        self.assertNotIn(": 0", result.stdout)

    def test_a_missing_checkout_exits_1(self) -> None:
        missing = Path(tempfile.gettempdir()) / "no-such-checkout-for-drift"
        result = _run([str(missing)])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("not a directory", result.stderr)
        self.assertNotIn(": 0", result.stdout)

    def test_an_optional_block_does_not_shift_later_blocks(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_template_drift as drift

        shared = (
            "name: shared\n"
            "# template:set\n"
            "stack: one\n"
            "# template:end\n"
            "# template:optional catalogue\n"
            "# template:set\n"
            "stack: catalogue\n"
            "# template:end\n"
            "# template:end\n"
            "# template:set\n"
            "format: plain\n"
            "# template:end\n"
        )
        shorter = (
            "name: shared\n"
            "# template:set\n"
            "stack: two\n"
            "# template:end\n"
            "# template:set\n"
            "format: plain\n"
            "# template:end\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in (("alpha", shared), ("beta", shorter)):
                workflow = root / name / ".github" / "workflows"
                workflow.mkdir(parents=True)
                (workflow / "deploy-backend.yml").write_text(text, encoding="utf-8")
            counts = drift.measure([root / "alpha", root / "beta"])
        self.assertEqual(
            counts["value blocks identical in every repo that has the file"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
