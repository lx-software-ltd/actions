"""The Lighthouse installer replaces the ranges that pull deprecated packages."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "lighthouse-ci" / "install.py"
_SPEC = importlib.util.spec_from_file_location("lighthouse_install", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
install = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(install)


class LighthouseInstallTest(unittest.TestCase):
    def test_the_manifest_replaces_the_deprecated_ranges(self) -> None:
        body = install.manifest("0.15.1")
        self.assertEqual(body["dependencies"], {"@lhci/cli": "0.15.1"})
        overrides = body["overrides"]
        self.assertEqual(overrides["chrome-launcher@0.13.4"], "0.15.2")
        self.assertEqual(overrides["tmp@0.1.0"], "0.2.4")
        self.assertEqual(overrides["uuid@8.3.2"], "11.1.1")
        self.assertNotIn("chrome-launcher", overrides)
        ranged = install.manifest("^0.16.1")
        self.assertEqual(ranged["dependencies"], {"@lhci/cli": "^0.16.1"})

    def test_a_version_with_shell_characters_is_rejected(self) -> None:
        for version in ("", "0.15.1; rm -rf /", "file:../cli", "0.15.1 latest"):
            with self.assertRaises(install.InstallError):
                install.manifest(version)

    def test_the_action_runs_the_installer_instead_of_npx(self) -> None:
        text = (ROOT / "lighthouse-ci" / "action.yml").read_text(encoding="utf-8")
        self.assertIn('python3 "$GITHUB_ACTION_PATH/install.py"', text)
        self.assertIn(
            '"$RUNNER_TEMP/lhci/node_modules/.bin/lhci" autorun --config="$CONFIG_PATH"',
            text,
        )
        self.assertNotIn("npx --yes", text)
