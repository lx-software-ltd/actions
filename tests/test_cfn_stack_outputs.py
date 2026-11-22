"""CloudFormation stack outputs: named keys, and no account id."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cfn-stack-outputs"))

import read_outputs  # noqa: E402


def _completed(code: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["aws"],
        returncode=code,
        stdout=stdout,
        stderr=stderr,
    )


DOCUMENT = json.dumps(
    {
        "Stacks": [
            {
                "Outputs": [
                    {"OutputKey": "UserPoolClientId", "OutputValue": "client"},
                    {
                        "OutputKey": "CognitoDomain",
                        "OutputValue": "https://example.auth.ap-southeast-1.amazoncognito.com",
                    },
                    {"OutputKey": "Empty", "OutputValue": ""},
                ]
            }
        ]
    }
)


class StackOutputsTest(unittest.TestCase):
    def test_missing_region_does_not_call_aws(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _completed(0, DOCUMENT)

        env = {"STACK": "findingalpha", "AWS_REGION": "", "OUTPUTS": "UserPoolClientId"}
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch("sys.stderr") as stderr:
                code = read_outputs.main(run_aws)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])
        printed = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("Set the region", printed)

    def test_a_bad_stack_name_does_not_call_aws(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _completed(0, DOCUMENT)

        env = {
            "STACK": "../other",
            "AWS_REGION": "ap-southeast-1",
            "OUTPUTS": "UserPoolClientId",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            code = read_outputs.main(run_aws)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])

    def test_access_denied_hides_the_account(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            return _completed(
                254,
                stderr=(
                    "An error occurred (AccessDenied) when calling the "
                    "DescribeStacks operation: User: arn:aws:sts::123456789012:assumed-role/"
                    "GitHubActionsRole/session is not authorized"
                ),
            )

        env = {
            "STACK": "findingalpha",
            "AWS_REGION": "ap-southeast-1",
            "OUTPUTS": "UserPoolClientId",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch("sys.stderr") as stderr:
                code = read_outputs.main(run_aws)
        printed = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertEqual(code, 1)
        self.assertIn("cloudformation:DescribeStacks", printed)
        self.assertIn("***", printed)
        self.assertNotIn("123456789012", printed)

    def test_a_missing_key_fails(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            return _completed(0, DOCUMENT)

        env = {
            "STACK": "findingalpha",
            "AWS_REGION": "ap-southeast-1",
            "OUTPUTS": "UserPoolClientId AdminApiBaseUrl",
            "GITHUB_OUTPUT": "",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch("sys.stderr") as stderr:
                code = read_outputs.main(run_aws)
        printed = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertEqual(code, 1)
        self.assertIn("AdminApiBaseUrl", printed)
        self.assertNotIn("client", printed)

    def test_an_empty_value_is_missing(self) -> None:
        with self.assertRaises(read_outputs.ReadError):
            read_outputs.select(DOCUMENT, ["Empty"])

    def test_the_json_output_keeps_only_the_requested_keys(self) -> None:
        seen: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            seen.append(command)
            return _completed(0, DOCUMENT)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "github-output"
            env = {
                "STACK": "findingalpha",
                "AWS_REGION": "ap-southeast-1",
                "OUTPUTS": "CognitoDomain, UserPoolClientId",
                "GITHUB_OUTPUT": str(output),
            }
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch("sys.stdout") as stdout:
                    code = read_outputs.main(run_aws)
            text = output.read_text(encoding="utf-8")
            printed = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertEqual(code, 0)
        self.assertEqual(
            seen[0],
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                "findingalpha",
                "--region",
                "ap-southeast-1",
                "--output",
                "json",
            ],
        )
        self.assertTrue(text.startswith("json<<CFN_OUTPUTS_JSON\n"))
        body = text.split("\n", 1)[1].rsplit("\nCFN_OUTPUTS_JSON\n", 1)[0]
        self.assertEqual(
            json.loads(body),
            {
                "CognitoDomain": "https://example.auth.ap-southeast-1.amazoncognito.com",
                "UserPoolClientId": "client",
            },
        )
        self.assertNotIn("client", printed)
        self.assertNotIn("https://", printed)
