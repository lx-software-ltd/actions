"""The Lighthouse config writer turns page paths into collect URLs."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "lighthouse-ci" / "prepare.py"
_SPEC = importlib.util.spec_from_file_location("lighthouse_prepare", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
prepare = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(prepare)


class LighthousePrepareTest(unittest.TestCase):
    def test_paths_become_local_urls_and_absolute_urls_stay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".lighthouserc.json").write_text("{}\n", encoding="utf-8")
            destination = prepare.write_config(root, ".lighthouserc.json", ["/", "https://example.com/about"], "9000")
            config = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(
            config["ci"]["collect"]["url"],
            ["http://localhost:9000/", "https://example.com/about"],
        )

    def test_a_missing_config_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(prepare.PrepareError):
                prepare.write_config(Path(directory), ".lighthouserc.json", ["/"], "9000")


if __name__ == "__main__":
    unittest.main()
