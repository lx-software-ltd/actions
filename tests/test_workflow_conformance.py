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

    def test_this_repository_passes_the_producer_profile(self) -> None:
        self.assertEqual(checker.findings(ROOT, "producer"), [])

    def test_paths_ignore_is_a_path_filter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _repo(
                root,
                textwrap.dedent(
                    """\
                    name: Lint
                    on:
                      pull_request:
                        paths-ignore:
                          - docs/**
                    permissions:
                      contents: read
                    jobs:
                      lint:
                        runs-on: ubuntu-26.04
                        steps:
                          - run: "true"
                    """
                ),
            )
            self.assertTrue(any("path filter" in item for item in checker.findings(root, "producer")))

    def test_an_unpinned_image_fails(self) -> None:
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
                        container:
                          image: semgrep/semgrep
                        steps:
                          - run: "true"
                    """
                ),
            )
            self.assertTrue(any("not pinned by digest" in item for item in checker.findings(root, "producer")))

    def test_a_gate_must_wait_for_every_job_and_pin_require_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            lint = (root / ".github" / "workflows" / "lint.yml").read_text(encoding="utf-8")
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace("    if: always()\n", ""),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("if: always()" in item for item in found), found)
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace("      - lint-python\n", ""),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("needs" in item for item in found), found)
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace(f"lx-software-ltd/actions/require-jobs@{REQUIRE}", "./require-jobs"),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("require-jobs" in item for item in found), found)

    def test_pre_commit_rev_stays_inside_the_actions_block(self) -> None:
        text = textwrap.dedent(
            """\
            repos:
              - repo: https://github.com/lx-software-ltd/actions
                hooks:
                  - id: check-pii
              - repo: https://github.com/pre-commit/pre-commit-hooks
                rev: v5.0.0
            """
        )
        found, revs = checker._pre_commit_actions_revs(text)
        self.assertTrue(found)
        self.assertEqual(revs, [""])

    def test_an_actions_pin_needs_a_main_date_comment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            lint = (root / ".github" / "workflows" / "lint.yml").read_text(encoding="utf-8")
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace(" # main 2026-11-20", " # sa-501 2026-11-22"),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("# main YYYY-MM-DD" in item for item in found), found)

    def test_statuses_permission_is_not_an_action_use(self) -> None:
        self.assertIsNone(checker._uses("  statuses: write"))
        self.assertIsNone(checker._uses('  "statuses": write'))
        self.assertIsNone(checker._uses("permissions: {contents: read, statuses: write}"))
        self.assertEqual(checker._uses("        uses: actions/checkout@v4"), "actions/checkout@v4")
        self.assertEqual(checker._uses("      - uses: actions/checkout@v4"), "actions/checkout@v4")

    def test_product_profile_requires_the_target_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            found = checker.findings(root, "product")
            self.assertTrue(any("missing job checkov" in item for item in found), found)
            self.assertTrue(any("semgrep/ci" in item for item in found), found)


REQUIRE = "1a3cca7c38163f8164c262323601c34a4df5b7a4"


def _valid(directory: Path) -> None:
    workflows = directory / ".github" / "workflows"
    workflows.mkdir(parents=True)
    workflows.joinpath("lint.yml").write_text(_gated("Lint", "lint", "lint-python"), encoding="utf-8")
    workflows.joinpath("test.yml").write_text(_gated("Test", "test", "unit"), encoding="utf-8")
    workflows.joinpath("security.yml").write_text(
        _gated("Security", "security-summary", "secrets-scan"),
        encoding="utf-8",
    )


def _gated(name: str, gate: str, other: str) -> str:
    return textwrap.dedent(
        f"""\
        name: {name}
        on:
          pull_request:
        permissions:
          contents: read
        jobs:
          {other}:
            runs-on: ubuntu-26.04
            steps:
              - run: "true"
          {gate}:
            runs-on: ubuntu-26.04
            needs:
              - {other}
            if: always()
            steps:
              - uses: lx-software-ltd/actions/require-jobs@{REQUIRE} # main 2026-11-20
        """
    )


if __name__ == "__main__":
    unittest.main()
