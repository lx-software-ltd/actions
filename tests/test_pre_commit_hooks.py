"""The hook scripts find the repository that is being checked."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreCommitHooksTest(unittest.TestCase):
    def test_file_length_hook_uses_the_callers_repository(self) -> None:
        fixture = ROOT / "fixtures" / "agent-harness" / "pass"
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            shutil.copytree(fixture, repo)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            completed = subprocess.run(
                ["bash", str(ROOT / "hooks" / "check-file-length")],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("passed", completed.stdout + completed.stderr)

    def test_hook_manifest_names_the_four_checks(self) -> None:
        text = (ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
        for hook_id in ("check-pii", "validate-agent-rules", "check-file-length", "check-test-focus"):
            self.assertIn(f"id: {hook_id}", text)
            self.assertIn("language: script", text)


if __name__ == "__main__":
    unittest.main()
