"""The CodeQL suite selector keeps security-extended and adds alert suppression."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "codeql" / "select_queries.sh"


def _select(language: str, queries: str = "security-extended", config: str = "") -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env.update(
            {
                "CODEQL_LANGUAGE": language,
                "CODEQL_QUERIES": queries,
                "CODEQL_CONFIG_FILE": config,
                "GITHUB_WORKSPACE": tmp,
                "GITHUB_OUTPUT": "",
            }
        )
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=tmp,
        )
        selected = result.stdout.strip()
        suite = ""
        path = Path(tmp) / selected
        if path.is_file():
            suite = path.read_text(encoding="utf-8")
        return selected, suite


class SelectQueriesTest(unittest.TestCase):
    def test_python_suite_adds_alert_suppression(self) -> None:
        selected, text = _select("python")
        self.assertEqual(selected, "./.codeql-suites/codeql-python-security-extended.qls")
        self.assertIn("from: codeql/python-queries", text)
        self.assertIn("security-extended-selectors.yml", text)
        self.assertIn("kind: alert-suppression", text)

    def test_javascript_typescript_uses_the_javascript_pack(self) -> None:
        _selected, text = _select("javascript-typescript")
        self.assertIn("from: codeql/javascript-queries", text)
        self.assertIn("kind: alert-suppression", text)

    def test_other_languages_keep_the_suite_name(self) -> None:
        selected, suite = _select("actions")
        self.assertEqual(selected, "security-extended")
        self.assertEqual(suite, "")

    def test_an_explicit_suite_passes_through(self) -> None:
        selected, _suite = _select("python", queries="security-and-quality")
        self.assertEqual(selected, "security-and-quality")

    def test_a_config_file_keeps_the_caller_suite(self) -> None:
        selected, _suite = _select("python", config=".github/codeql/codeql-config.yml")
        self.assertEqual(selected, "security-extended")


if __name__ == "__main__":
    unittest.main()
