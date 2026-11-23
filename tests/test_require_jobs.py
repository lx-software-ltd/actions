"""Unit tests for the require-jobs action."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "require-jobs" / "require_jobs.py"
_SPEC = importlib.util.spec_from_file_location("require_jobs", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
require_jobs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(require_jobs)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "require-jobs"


class RequireJobsTest(unittest.TestCase):
    def test_flat_success(self) -> None:
        results = require_jobs.parse_results({"lint": "success", "test": "success"})
        self.assertEqual(require_jobs.failing_jobs(results), [])

    def test_github_needs_shape(self) -> None:
        payload = {"lint": {"result": "success", "outputs": {}}}
        results = require_jobs.parse_results(payload)
        self.assertEqual(results, {"lint": "success"})

    def test_failure_is_reported(self) -> None:
        results = require_jobs.parse_results(json.loads((FIXTURES / "fail" / "needs.json").read_text()))
        self.assertEqual(
            require_jobs.failing_jobs(results),
            ["validate-agent-harness=failure"],
        )

    def test_pass_fixture(self) -> None:
        results = require_jobs.parse_results(json.loads((FIXTURES / "pass" / "needs.json").read_text()))
        self.assertEqual(require_jobs.failing_jobs(results), [])

    def test_skipped_fails(self) -> None:
        results = {"lint": "skipped"}
        self.assertEqual(require_jobs.failing_jobs(results), ["lint=skipped"])

    def test_empty_object_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            require_jobs.parse_results({})

    def test_missing_result_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            require_jobs.parse_results({"lint": {"outputs": {}}})

    def test_summary_escapes_pipes(self) -> None:
        table = require_jobs.summary_table({"a|b": "success"})
        self.assertIn(r"a\|b", table)
        self.assertIn("| Result |", table)

    def test_main_success_and_summary(self) -> None:
        summary = self._summary_path()
        code = self._run('{"lint":"success"}', summary)
        self.assertEqual(code, 0)
        self.assertIn("| lint | success |", summary.read_text(encoding="utf-8"))

    def test_main_failure(self) -> None:
        code = self._run((FIXTURES / "fail" / "needs.json").read_text(encoding="utf-8"), None)
        self.assertEqual(code, 1)

    def test_main_rejects_invalid_json(self) -> None:
        self.assertEqual(self._run("{", None), 1)

    def _summary_path(self) -> Path:
        path = Path(self.id().replace(".", "_") + "-summary.md")
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def _run(self, raw: str, summary: Path | None) -> int:
        import os

        previous = {
            "NEEDS_JSON": os.environ.get("NEEDS_JSON"),
            "GITHUB_STEP_SUMMARY": os.environ.get("GITHUB_STEP_SUMMARY"),
        }
        os.environ["NEEDS_JSON"] = raw
        if summary is None:
            os.environ.pop("GITHUB_STEP_SUMMARY", None)
        else:
            os.environ["GITHUB_STEP_SUMMARY"] = str(summary)
        try:
            return require_jobs.main()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
