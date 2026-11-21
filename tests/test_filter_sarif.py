"""The SARIF filter drops in-source suppressions and keeps the rest."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "lib" / "filter_sarif.py"
_SPEC = importlib.util.spec_from_file_location("filter_sarif", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sarif = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sarif)


class FilterSarifTest(unittest.TestCase):
    def test_drops_in_source_and_counts_them(self) -> None:
        payload = {
            "version": "2.1.0",
            "runs": [
                {
                    "results": [
                        {"ruleId": "keep"},
                        {"ruleId": "drop", "suppressions": [{"kind": "inSource"}]},
                        {"ruleId": "other", "suppressions": [{"kind": "external"}]},
                    ]
                }
            ],
        }
        filtered, removed = sarif.drop_in_source(payload)
        self.assertEqual(removed, 1)
        self.assertEqual(
            [item["ruleId"] for item in filtered["runs"][0]["results"]],
            ["keep", "other"],
        )

    def test_missing_file_writes_an_empty_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "out.sarif"
            removed = sarif.filter_file(Path(directory) / "missing.sarif", destination)
            self.assertEqual(removed, 0)
            payload = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(payload["runs"], [])

    def test_semgrep_uses_the_shared_library_path(self) -> None:
        text = (ROOT / "semgrep" / "scan.sh").read_text(encoding="utf-8")
        self.assertIn('"$GITHUB_ACTION_PATH/../lib/filter_sarif.py"', text)
        self.assertIn("does not resolve", text)


if __name__ == "__main__":
    unittest.main()
