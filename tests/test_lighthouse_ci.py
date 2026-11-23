"""The Lighthouse config writer turns page paths into collect URLs."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import unittest.mock
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

    def test_root_alias_and_staging_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".lighthouserc.json").write_text("{}\n", encoding="utf-8")
            destination = prepare.write_config(
                root,
                ".lighthouserc.json",
                ["/", "https://staging.example/en/"],
                "9000",
                root_alias="/en/",
                staging_origin="https://staging.example",
                bypass_secret="secret",
            )
            config = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(config["ci"]["collect"]["url"][0], "http://localhost:9000/en/")
        self.assertIn("x-staging-bypass", config["ci"]["collect"]["settings"]["extraHeaders"])
        self.assertNotIn("secret", (root / ".lighthouseci").as_posix())

    def test_the_runtime_config_stays_outside_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            site.mkdir()
            (site / ".lighthouserc.json").write_text("{}\n", encoding="utf-8")
            temp = root / "runner"
            temp.mkdir()
            output = root / "output"
            env = {
                "WORKING_DIRECTORY": str(site),
                "LIGHTHOUSE_PAGE_PATHS": "/",
                "DEFAULT_PATHS": "",
                "PORT": "9000",
                "RUNNER_TEMP": str(temp),
                "GITHUB_OUTPUT": str(output),
                "DRY_RUN": "true",
                "BYPASS_SECRET": "secret",
                "STAGING_ORIGIN": "",
            }
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                code = prepare.main()
            recorded = output.read_text(encoding="utf-8")
            self.assertEqual(code, 0)
            self.assertIn(str(temp / "lighthouserc.runtime.json"), recorded)
            self.assertFalse((site / ".lighthouserc.runtime.json").exists())

    def test_scrub_removes_the_bypass_secret_from_a_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / ".lighthouseci" / "lhr.json"
            report.parent.mkdir()
            report.write_text(
                '{"extraHeaders": "{\\"x-staging-bypass\\": \\"secret\\"}"}',
                encoding="utf-8",
            )
            prepare.scrub(root, "secret")
            text = report.read_text(encoding="utf-8")
        self.assertNotIn("secret", text)
        self.assertIn("***", text)

    def test_a_missing_config_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(prepare.PrepareError):
                prepare.write_config(Path(directory), ".lighthouserc.json", ["/"], "9000")


if __name__ == "__main__":
    unittest.main()
