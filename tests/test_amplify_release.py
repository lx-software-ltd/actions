"""Amplify release starts a job, and promote still requires a green source."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "amplify-release"))

import amplify_release  # noqa: E402


def _json(payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["aws"],
        returncode=0,
        stdout=json.dumps(payload),
        stderr="",
    )


class AmplifyReleaseTest(unittest.TestCase):
    def test_release_without_wait_starts_one_job(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _json({"jobSummary": {"jobId": "4", "status": "PENDING"}})

        amplify_release.release(
            app_id="d123",
            branch="main",
            mode="release",
            source_branch="",
            wait=False,
            allowed_source="staging",
            allowed_target="main",
            polls=2,
            interval=0,
            run_aws=run_aws,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1:3], ["amplify", "start-job"])
        self.assertIn("RELEASE", calls[0])
        self.assertIn("main", calls[0])

    def test_release_waits_until_succeed(self) -> None:
        calls: list[str] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command[2])
            if command[2] == "start-job":
                return _json({"jobSummary": {"jobId": "9"}})
            return _json({"job": {"summary": {"status": "SUCCEED"}}})

        amplify_release.release(
            app_id="d123",
            branch="main",
            mode="release",
            source_branch="",
            wait=True,
            allowed_source="staging",
            allowed_target="main",
            polls=3,
            interval=0,
            run_aws=run_aws,
        )
        self.assertEqual(calls, ["start-job", "get-job"])

    def test_promote_refuses_a_source_that_is_not_green(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            return _json({"jobSummaries": [{"status": "FAILED"}]})

        with self.assertRaises(amplify_release.AmplifyError) as caught:
            amplify_release.release(
                app_id="d123",
                branch="main",
                mode="promote",
                source_branch="staging",
                wait=False,
                allowed_source="staging",
                allowed_target="main",
                polls=1,
                interval=0,
                run_aws=run_aws,
            )
        self.assertIn("not green", str(caught.exception))

    def test_promote_rejects_a_branch_other_than_staging_to_main(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _json({})

        with self.assertRaises(amplify_release.AmplifyError):
            amplify_release.release(
                app_id="d123",
                branch="production",
                mode="promote",
                source_branch="staging",
                wait=False,
                allowed_source="staging",
                allowed_target="main",
                polls=1,
                interval=0,
                run_aws=run_aws,
            )
        self.assertEqual(calls, [])

    def test_a_failed_aws_call_hides_an_account_id(self) -> None:
        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=254,
                stdout="",
                stderr="account 123456789012",
            )

        env = {
            "APP_ID": "d123",
            "BRANCH": "main",
            "MODE": "release",
            "WAIT": "false",
            "ALLOWED_SOURCE": "staging",
            "ALLOWED_TARGET": "main",
            "MAX_POLLS": "1",
            "POLL_INTERVAL": "0",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch("sys.stderr") as stderr:
                code = amplify_release.main(run_aws)
        self.assertEqual(code, 1)
        text = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertNotIn("123456789012", text)

    def test_a_missing_app_id_does_not_call_aws(self) -> None:
        calls: list[list[str]] = []

        def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return _json({})

        env = {"APP_ID": "", "BRANCH": "main", "MODE": "release", "WAIT": "false"}
        with mock.patch.dict("os.environ", env, clear=False):
            code = amplify_release.main(run_aws)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])
