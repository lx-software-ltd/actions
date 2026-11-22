"""CDK bootstrap check: SSM read, hint, and no account id."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cdk-bootstrap-check"))

import check_bootstrap  # noqa: E402


def _completed(code: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["aws"],
        returncode=code,
        stdout=stdout,
        stderr=stderr,
    )


class BootstrapCheckTest(unittest.TestCase):
    def test_empty_qualifier_uses_the_default(self) -> None:
        parameter, qualifier = check_bootstrap.parameter_name("")
        self.assertEqual(qualifier, "hnb659fds")
        self.assertEqual(parameter, "/cdk-bootstrap/hnb659fds/version")

    def test_qualifier_rejects_a_path(self) -> None:
        with self.assertRaises(check_bootstrap.BootstrapError):
            check_bootstrap.parameter_name("../secrets")

    def test_missing_region_does_not_call_aws(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _completed(0, "21")

        with mock.patch.dict("os.environ", {"QUALIFIER": "", "AWS_REGION": ""}, clear=False):
            code = check_bootstrap.main(run_aws)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])

    def test_a_readable_parameter_passes(self) -> None:
        seen: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            seen.append(command)
            return _completed(0, "21\n")

        env = {"QUALIFIER": "hnb659fds", "AWS_REGION": "ap-southeast-1"}
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch("sys.stdout") as stdout:
                code = check_bootstrap.main(run_aws)
        self.assertEqual(code, 0)
        self.assertEqual(seen[0][0:3], ["aws", "ssm", "get-parameter"])
        self.assertIn("/cdk-bootstrap/hnb659fds/version", seen[0])
        text = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("CDK Bootstrap version 21.", text)
        self.assertNotRegex(text, r"\d{12}")

    def test_a_missing_parameter_prints_the_hint_without_an_account(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            return _completed(254, stderr="account 123456789012")

        env = {"QUALIFIER": "hnb659fds", "AWS_REGION": "us-east-1"}
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch("sys.stdout") as stdout:
                code = check_bootstrap.main(run_aws)
        self.assertEqual(code, 1)
        text = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("/cdk-bootstrap/hnb659fds/version", text)
        self.assertIn("ssm:GetParameter", text)
        self.assertIn("in this account and region", text)
        self.assertNotIn("123456789012", text)


if __name__ == "__main__":
    unittest.main()
