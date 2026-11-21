"""Warn reports a bad pin and still exits 0. Enforce exits 1."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "workflow-conformance" / "check_workflows.py"
_SPEC = importlib.util.spec_from_file_location("check_workflows", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)


def _repo(directory: Path, lint: str) -> None:
    workflows = directory / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "lint.yml").write_text(lint, encoding="utf-8")
    (workflows / "test.yml").write_text(
        textwrap.dedent(
            """\
            name: Test
            on:
              pull_request:
            permissions:
              contents: read
            jobs:
              test:
                runs-on: ubuntu-26.04
                steps:
                  - run: "true"
            """
        ),
        encoding="utf-8",
    )


class WorkflowConformanceTest(unittest.TestCase):
    def test_enforce_fails_on_a_tag_pin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _repo(
                root,
                textwrap.dedent(
                    """\
                    name: Lint
                    on:
                      pull_request:
                    permissions:
                      contents: read
                    jobs:
                      lint:
                        runs-on: ubuntu-26.04
                        steps:
                          - uses: actions/checkout@v7
                    """
                ),
            )
            self.assertTrue(any("not pinned" in item for item in checker.findings(root)))
            completed = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={"CONFORMANCE_MODE": "warn", "PATH": "/usr/bin:/bin"},
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            completed = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={"CONFORMANCE_MODE": "enforce", "PATH": "/usr/bin:/bin"},
                check=False,
            )
            self.assertEqual(completed.returncode, 1)

    def test_this_repository_passes_enforce(self) -> None:
        self.assertEqual(checker.findings(ROOT), [])


if __name__ == "__main__":
    unittest.main()
