"""Unit tests for the aws-oidc settings and token-subject checks.

The subject strings are ID-form claims a token can carry, and the name
form and trust-policy pattern it must reject. No account id is stored here.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import unittest
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "aws-oidc" / "aws_oidc.py"
_SPEC = importlib.util.spec_from_file_location("aws_oidc", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
aws_oidc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(aws_oidc)

ID_FORM_PULL_REQUEST = "repo:example-org@100000001/example-repo@100000002:pull_request"
ID_FORM_REF = "repo:example-org@100000001/example-repo@100000002:ref:refs/heads/main"
ID_FORM_ENVIRONMENT = "repo:example-org@100000001/example-repo@100000002:environment:production"
NAME_FORM_SUBJECT = "repo:example-org/example-repo:pull_request"
PATTERN_SUBJECT = "repo:example-org@100000001/example-repo@100000002:*"


def _jwt(subject: str) -> str:
    def encode(value: dict) -> str:
        raw = json.dumps(value).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    return f"{encode({'alg': 'none'})}.{encode({'sub': subject})}.sig"


class AwsOidcSubjectTest(unittest.TestCase):
    def test_id_form_subjects_match(self) -> None:
        self.assertTrue(aws_oidc.subject_is_id_form(ID_FORM_PULL_REQUEST))
        self.assertTrue(aws_oidc.subject_is_id_form(ID_FORM_REF))
        self.assertTrue(aws_oidc.subject_is_id_form(ID_FORM_ENVIRONMENT))

    def test_name_form_and_pattern_do_not_match(self) -> None:
        self.assertFalse(aws_oidc.subject_is_id_form(NAME_FORM_SUBJECT))
        self.assertFalse(aws_oidc.subject_is_id_form(PATTERN_SUBJECT))
        self.assertFalse(aws_oidc.subject_is_id_form("repo:example-org@100000001/*"))
        self.assertFalse(
            aws_oidc.subject_is_id_form("repo:example-org@100000001/example-repo:pull_request")
        )

    def test_subject_is_read_from_the_token(self) -> None:
        self.assertEqual(aws_oidc.subject_from_jwt(_jwt(ID_FORM_PULL_REQUEST)), ID_FORM_PULL_REQUEST)


class AwsOidcDecideTest(unittest.TestCase):
    def test_masks_before_any_other_line(self) -> None:
        account = "1" * 12
        result = aws_oidc.decide(account, "ap-southeast-1", True)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.ready, "true")
        self.assertTrue(result.stdout.startswith(f"::add-mask::{account}\n"))
        self.assertNotIn(account, result.stdout.split("\n", 1)[1])

    def test_missing_settings_skip_when_optional(self) -> None:
        result = aws_oidc.decide("", "", False)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.ready, "false")
        self.assertIn("::warning::", result.stdout)
        self.assertIn("secret `AWS_ACCOUNT_ID`", result.summary)
        self.assertIn("AWS_REGION", result.summary)
        self.assertIn("account was not compared", result.summary)
        self.assertNotIn("::add-mask::", result.stdout)

    def test_missing_settings_fail_when_required(self) -> None:
        result = aws_oidc.decide("", "ap-southeast-1", True)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.ready, "")
        self.assertIn("::error::", result.stdout)

    def test_required_must_be_boolean(self) -> None:
        with self.assertRaises(ValueError):
            aws_oidc.parse_required("yes")

    def test_main_accepts_an_id_form_token_subject(self) -> None:
        account = "1" * 12
        code, output, stdout, _summary = self._run(
            account,
            "ap-southeast-1",
            "true",
            lambda: _jwt(ID_FORM_PULL_REQUEST),
        )
        self.assertEqual(code, 0)
        self.assertEqual(output, "ready=true\n")
        self.assertTrue(stdout.startswith(f"::add-mask::{account}\n"))
        self.assertNotIn(_jwt(ID_FORM_PULL_REQUEST), stdout)

    def test_main_rejects_a_name_form_token_subject(self) -> None:
        code, output, stdout, _summary = self._run(
            "1" * 12,
            "ap-southeast-1",
            "true",
            lambda: _jwt(NAME_FORM_SUBJECT),
        )
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("ID form", stdout)
        self.assertIn(NAME_FORM_SUBJECT, stdout)

    def test_main_rejects_a_pattern_instead_of_a_subject(self) -> None:
        code, output, stdout, _summary = self._run(
            "1" * 12,
            "ap-southeast-1",
            "false",
            lambda: _jwt(PATTERN_SUBJECT),
        )
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn(PATTERN_SUBJECT, stdout)

    def test_main_skips_without_reading_a_token(self) -> None:
        def fail_if_called() -> str:
            raise AssertionError("token requested")

        code, output, stdout, summary = self._run("", "", "false", fail_if_called)
        self.assertEqual(code, 0)
        self.assertEqual(output, "ready=false\n")
        self.assertIn("::warning::", stdout)
        self.assertIn("account was not compared", summary)

    def test_main_reports_a_missing_token(self) -> None:
        def fail() -> str:
            raise aws_oidc.OidcError("The job needs id-token: write so the OIDC subject can be read.")

        code, output, stdout, _summary = self._run("1" * 12, "ap-southeast-1", "true", fail)
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("id-token: write", stdout)

    def _run(self, account: str, region: str, required: str, fetch) -> tuple[int, str, str, str]:
        import contextlib
        import os
        import tempfile
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "output"
            summary_path = Path(directory) / "summary"
            previous = {
                key: os.environ.get(key)
                for key in ("ACCOUNT_ID", "AWS_REGION", "REQUIRED", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY")
            }
            os.environ["ACCOUNT_ID"] = account
            os.environ["AWS_REGION"] = region
            os.environ["REQUIRED"] = required
            os.environ["GITHUB_OUTPUT"] = str(output_path)
            os.environ["GITHUB_STEP_SUMMARY"] = str(summary_path)
            buffer = StringIO()
            try:
                with contextlib.redirect_stdout(buffer):
                    code = aws_oidc.main(fetch_token=fetch)
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            output = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
            summary = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
            return code, output, buffer.getvalue(), summary
