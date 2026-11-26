"""Code scanning uploads must close a suppressed result and the old Semgrep category."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CodeScanningUploadTest(unittest.TestCase):
    def test_codeql_filters_before_upload(self) -> None:
        text = (ROOT / "codeql" / "action.yml").read_text(encoding="utf-8")
        self.assertIn("upload: never", text)
        self.assertIn("filter_results.sh", text)
        self.assertIn("upload-sarif@", text)
        self.assertNotIn("upload: always", text)

    def test_semgrep_keeps_the_previous_category(self) -> None:
        text = (ROOT / "semgrep" / "action.yml").read_text(encoding="utf-8")
        self.assertIn('category: ".github/workflows/security.yml:semgrep"', text)
        self.assertEqual(text.count("upload-sarif@"), 2)
