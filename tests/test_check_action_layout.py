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


class CheckActionLayoutTest(unittest.TestCase):
    def test_repository_passes(self) -> None:
        self.assertEqual(check_action_layout.check(), [])

    def test_run_without_shell_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            action = root / "broken"
            action.mkdir()
            (action / "action.yml").write_text(
                textwrap.dedent(
                    """\
                    name: Broken
                    runs:
                      using: composite
                      steps:
                        - name: Run
                          run: echo hi
                    """
                ),
                encoding="utf-8",
            )
            errors = check_action_layout.check(root)
        self.assertTrue(any("must set shell" in error for error in errors))

    def test_expression_inside_run_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            action = root / "broken"
            action.mkdir()
            (action / "action.yml").write_text(
                "name: Broken\n"
                "runs:\n"
                "  using: composite\n"
                "  steps:\n"
                "    - shell: bash\n"
                "      run: echo ${{ inputs.value }}\n",
                encoding="utf-8",
            )
            errors = check_action_layout.check(root)
        self.assertTrue(any("inside run" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
