"""CDK bootstrap: the command shape, and no account id in the log."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cdk-bootstrap"))

import bootstrap  # noqa: E402


def _ok(text: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=text, stderr="")


class BootstrapTest(unittest.TestCase):
    def test_qualifier_is_passed_and_the_account_is_masked(self) -> None:
        seen: list[list[str]] = []

        def run(argv: list[str], directory: Path) -> subprocess.CompletedProcess[str]:
            seen.append(argv)
            return _ok(f"bootstrapped aws://123456789012/{directory.name}\n")

        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / "package.json").write_text("{}\n", encoding="utf-8")
            env = {
                "WORKING_DIRECTORY": directory,
                "ACCOUNT_ID": "123456789012",
                "AWS_REGION": "ap-southeast-1",
                "QUALIFIER": "hnb659fds",
            }
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch("sys.stdout") as stdout:
                    code = bootstrap.main(run)
            printed = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertEqual(code, 0)
        self.assertEqual(seen[0], ["npm", "ci"])
        self.assertEqual(seen[1], ["npm", "run", "build", "--if-present"])
        self.assertEqual(
            seen[2],
            [
                "npx",
                "cdk",
                "bootstrap",
                "--qualifier",
                "hnb659fds",
                "aws://123456789012/ap-southeast-1",
            ],
        )
        self.assertIn("::add-mask::123456789012", printed)
        self.assertIn("aws://***/", printed)
        self.assertEqual(printed.count("123456789012"), 1)

    def test_an_empty_qualifier_omits_the_flag(self) -> None:
        self.assertEqual(
            bootstrap.commands("123456789012", "us-east-1", ""),
            [
                ["npm", "ci"],
                ["npm", "run", "build", "--if-present"],
                ["npx", "cdk", "bootstrap", "aws://123456789012/us-east-1"],
            ],
        )

    def test_a_bad_account_does_not_run_or_echo_the_value(self) -> None:
        calls: list[list[str]] = []

        def run(argv: list[str], directory: Path) -> subprocess.CompletedProcess[str]:
            calls.append(argv)
            return _ok()

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "package.json").write_text("{}\n", encoding="utf-8")
            env = {
                "WORKING_DIRECTORY": directory,
                "ACCOUNT_ID": "1234",
                "AWS_REGION": "ap-southeast-1",
                "QUALIFIER": "",
            }
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch("sys.stderr") as stderr:
                    code = bootstrap.main(run)
            printed = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])
        self.assertIn("12 digits", printed)
        self.assertNotIn("1234", printed)

    def test_an_empty_region_fails_before_npm(self) -> None:
        calls: list[list[str]] = []

        def run(argv: list[str], directory: Path) -> subprocess.CompletedProcess[str]:
            calls.append(argv)
            return _ok()

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "package.json").write_text("{}\n", encoding="utf-8")
            env = {
                "WORKING_DIRECTORY": directory,
                "ACCOUNT_ID": "123456789012",
                "AWS_REGION": "",
                "QUALIFIER": "",
            }
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch("sys.stderr") as stderr:
                    code = bootstrap.main(run)
            printed = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])
        self.assertIn("Set the region", printed)
        self.assertNotIn("123456789012", printed)


if __name__ == "__main__":
    unittest.main()
