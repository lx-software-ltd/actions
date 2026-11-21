"""Pinned requirements stay, unpinned ones and escaping includes fail."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "python-requirements-pins" / "check_pins.py"
_SPEC = importlib.util.spec_from_file_location("check_pins", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
pins = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pins)


class RequirementPinsTest(unittest.TestCase):
    def test_follows_an_include(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "extra.txt").write_text("extra==2\n", encoding="utf-8")
            start = root / "requirements.txt"
            start.write_text("demo==1\n-r extra.txt\n", encoding="utf-8")
            self.assertEqual(pins.check_files([start]), [])

    def test_reports_an_unpinned_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            start = Path(directory) / "requirements.txt"
            start.write_text("demo>=1\n", encoding="utf-8")
            errors = pins.check_files([start])
            self.assertEqual(len(errors), 1)
            self.assertIn("demo>=1", errors[0])

    def test_rejects_an_include_that_leaves_the_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outside.txt").write_text("demo==1\n", encoding="utf-8")
            nested = root / "app"
            nested.mkdir()
            start = nested / "requirements.txt"
            start.write_text("-r ../outside.txt\n", encoding="utf-8")
            errors = pins.check_files([start])
            self.assertTrue(any("escapes" in entry for entry in errors))


if __name__ == "__main__":
    unittest.main()
