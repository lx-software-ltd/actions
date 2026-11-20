"""The setup actions keep the organisation defaults and the pin rules."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class SetupActionsTest(unittest.TestCase):
    def test_setup_node_defaults_and_pin(self) -> None:
        text = _text("setup-node/action.yml")
        self.assertIn('default: "26"', text)
        self.assertIn("working-directory:", text)
        self.assertIn('default: "true"', text)
        self.assertIn(
            "uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0",
            text,
        )
        self.assertIn("npm ci", text)
        self.assertNotIn("uses: ./", text)

    def test_setup_python_defaults_and_pin(self) -> None:
        text = _text("setup-python/action.yml")
        self.assertIn('default: "3.12"', text)
        self.assertIn("requirements:", text)
        self.assertIn(
            "uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0",
            text,
        )
        self.assertNotIn("uses: ./", text)
        run_blocks = [line for line in text.splitlines() if line.strip().startswith("run:")]
        self.assertFalse(any("${{" in line for line in run_blocks))

    def test_node_fixture_has_a_lockfile(self) -> None:
        self.assertTrue((ROOT / "fixtures/setup-node/package.json").is_file())
        self.assertTrue((ROOT / "fixtures/setup-node/package-lock.json").is_file())
        self.assertTrue((ROOT / "fixtures/setup-python/requirements.txt").is_file())


if __name__ == "__main__":
    unittest.main()
