"""Unit tests for the aws-oidc settings check.

The subject strings are the ID form the trust policy matches, and the
name form it does not. No account id is stored here.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "aws-oidc" / "aws_oidc.py"
_SPEC = importlib.util.spec_from_file_location("aws_oidc", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
aws_oidc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(aws_oidc)

ID_FORM_SUBJECT = "repo:lx-software-ltd@321652495/findingalpha@1456774357:*"
ID_FORM_PULL_REQUEST = "repo:lx-software-ltd@321652495/findingalpha@1456774357:pull_request"
NAME_FORM_SUBJECT = "repo:lx-software-ltd/findingalpha:pull_request"
ORG_WILDCARD_SUBJECT = "repo:lx-software-ltd@321652495/*"


class AwsOidcSubjectTest(unittest.TestCase):
    def test_id_form_subjects_match(self) -> None:
        self.assertTrue(aws_oidc.subject_is_id_form(ID_FORM_SUBJECT))
        self.assertTrue(aws_oidc.subject_is_id_form(ID_FORM_PULL_REQUEST))
        self.assertTrue(
            aws_oidc.subject_is_id_form(
                "repo:lx-software-ltd@321652495/findingalpha@1456774357:environment:production"
            )
        )

    def test_name_form_subject_does_not_match(self) -> None:
        self.assertFalse(aws_oidc.subject_is_id_form(NAME_FORM_SUBJECT))
        self.assertFalse(aws_oidc.subject_is_id_form(ORG_WILDCARD_SUBJECT))
        self.assertFalse(
            aws_oidc.subject_is_id_form("repo:lx-software-ltd@321652495/findingalpha:pull_request")
        )


class AwsOidcDecideTest(unittest.TestCase):
    def test_masks_before_ready(self) -> None:
        account = "1" * 12
        result = aws_oidc.decide(account, "ap-southeast-1", True, ID_FORM_SUBJECT)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.ready, "true")
        self.assertTrue(result.stdout.startswith(f"::add-mask::{account}\n"))
        self.assertNotIn(account, result.stdout.split("\n", 1)[1])

    def test_missing_settings_skip_when_optional(self) -> None:
        result = aws_oidc.decide("", "", False, ID_FORM_SUBJECT)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.ready, "false")
        self.assertIn("::warning::", result.stdout)
        self.assertIn("AWS_ACCOUNT_ID", result.summary)
        self.assertIn("AWS_REGION", result.summary)
        self.assertIn("account was not compared", result.summary)
        self.assertNotIn("::add-mask::", result.stdout)

    def test_missing_settings_fail_when_required(self) -> None:
        result = aws_oidc.decide("", "ap-southeast-1", True, "")
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.ready, "")
        self.assertIn("::error::", result.stdout)

    def test_name_form_subject_fails(self) -> None:
        result = aws_oidc.decide("1" * 12, "ap-southeast-1", False, NAME_FORM_SUBJECT)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.ready, "")
        self.assertIn("ID form", result.stdout)
        self.assertNotIn(NAME_FORM_SUBJECT, result.stdout)

    def test_empty_subject_is_not_checked(self) -> None:
        result = aws_oidc.decide("1" * 12, "ap-southeast-1", True, "")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.ready, "true")

    def test_required_must_be_boolean(self) -> None:
        with self.assertRaises(ValueError):
            aws_oidc.parse_required("yes")

    def test_main_writes_ready_and_masks(self) -> None:
        account = "1" * 12
        code, output, stdout, summary = self._run(
            account,
            "ap-southeast-1",
            "true",
            ID_FORM_SUBJECT,
        )
        self.assertEqual(code, 0)
        self.assertEqual(output, "ready=true\n")
        self.assertTrue(stdout.startswith(f"::add-mask::{account}\n"))
        self.assertEqual(summary, "")

    def test_main_skips_without_settings(self) -> None:
        code, output, stdout, summary = self._run("", "", "false", ID_FORM_PULL_REQUEST)
        self.assertEqual(code, 0)
        self.assertEqual(output, "ready=false\n")
        self.assertIn("::warning::", stdout)
        self.assertIn("account was not compared", summary)

    def _run(self, account: str, region: str, required: str, subject: str) -> tuple[str, str, str, str]:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "output"
            summary_path = Path(directory) / "summary"
            previous = {
                key: os.environ.get(key)
                for key in ("ACCOUNT_ID", "AWS_REGION", "REQUIRED", "SUBJECT", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY")
            }
            os.environ["ACCOUNT_ID"] = account
            os.environ["AWS_REGION"] = region
            os.environ["REQUIRED"] = required
            os.environ["SUBJECT"] = subject
            os.environ["GITHUB_OUTPUT"] = str(output_path)
            os.environ["GITHUB_STEP_SUMMARY"] = str(summary_path)
            try:
                from io import StringIO
                import contextlib

                buffer = StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = aws_oidc.main()
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            output = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
            summary = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
            return code, output, buffer.getvalue(), summary
