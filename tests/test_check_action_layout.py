"""The layout checker accepts this repository and rejects a broken action."""

from __future__ import annotations

import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_action_layout.py"
_SPEC = importlib.util.spec_from_file_location("check_action_layout", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
check_action_layout = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_action_layout)


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


class CheckActionLayoutTest(unittest.TestCase):
    def test_repository_passes(self) -> None:
        self.assertEqual(check_action_layout.check(), [])

    def test_run_without_shell_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "broken/action.yml",
                """\
                name: Broken
                runs:
                  using: composite
                  steps:
                    - name: Run
                      run: echo hi
                """,
            )
            errors = check_action_layout.check(root)
        self.assertTrue(any("must set shell" in error for error in errors))

    def test_expression_inside_run_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "broken/action.yml",
                """\
                name: Broken
                runs:
                  using: composite
                  steps:
                    - shell: bash
                      run: echo ${{ inputs.value }}
                """,
            )
            _write(root, "broken/README.md", "Broken\n")
            errors = check_action_layout.check(root)
        self.assertTrue(any("inside run" in error for error in errors))

    def test_two_space_steps_are_still_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "broken/action.yml",
                """\
                name: Broken
                runs:
                  using: composite
                  steps:
                  - shell: bash
                    run: echo ${{ inputs.value }}
                """,
            )
            _write(root, "broken/README.md", "Broken\n")
            errors = check_action_layout.check(root)
        self.assertTrue(any("inside run" in error for error in errors))

    def test_env_after_run_is_not_part_of_the_run_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "ok/action.yml",
                """\
                name: Ok
                runs:
                  using: composite
                  steps:
                    - shell: bash
                      env:
                        VALUE: ${{ inputs.value }}
                      run: echo ok
                    - shell: bash
                      run: echo ok
                      env:
                        VALUE: ${{ inputs.value }}
                """,
            )
            _write(root, "ok/README.md", "Ok\n")
            errors = check_action_layout.check(root)
        self.assertFalse(any("inside run" in error for error in errors))
        self.assertEqual(errors, [])

    def test_block_run_stops_before_a_later_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "ok/action.yml",
                """\
                name: Ok
                runs:
                  using: composite
                  steps:
                    - shell: bash
                      run: |
                        echo ok
                      env:
                        VALUE: ${{ inputs.value }}
                """,
            )
            _write(root, "ok/README.md", "Ok\n")
            errors = check_action_layout.check(root)
        self.assertEqual(errors, [])

    def test_action_calling_another_action_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "broken/action.yml",
                """\
                name: Broken
                runs:
                  using: composite
                  steps:
                    - shell: bash
                      run: echo hi
                    - uses: ./other
                """,
            )
            _write(root, "broken/README.md", "Broken\n")
            errors = check_action_layout.check(root)
        self.assertTrue(any("must not call another action" in error for error in errors))

    def test_missing_readme_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "broken/action.yml",
                """\
                name: Broken
                runs:
                  using: composite
                  steps:
                    - shell: bash
                      run: echo hi
                """,
            )
            errors = check_action_layout.check(root)
        self.assertTrue(any("README.md" in error for error in errors))

    def test_sha_pin_without_version_comment_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                ".github/workflows/lint.yml",
                """\
                name: Lint
                on: pull_request
                permissions:
                  contents: read
                jobs:
                  lint:
                    runs-on: ubuntu-26.04
                    steps:
                      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
                """,
            )
            errors = check_action_layout.check(root)
        self.assertTrue(any("version comment" in error for error in errors))

    def test_gate_job_must_not_use_a_local_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                ".github/workflows/lint.yml",
                """\
                name: Lint
                on: pull_request
                permissions:
                  contents: read
                jobs:
                  unit:
                    runs-on: ubuntu-26.04
                    steps:
                      - uses: ./require-jobs
                  lint:
                    runs-on: ubuntu-26.04
                    steps:
                      - uses: ./require-jobs
                """,
            )
            errors = check_action_layout.check(root)
        gate_errors = [error for error in errors if "gate job" in error]
        self.assertEqual(len(gate_errors), 1)
        self.assertIn("lint", gate_errors[0])


if __name__ == "__main__":
    unittest.main()
