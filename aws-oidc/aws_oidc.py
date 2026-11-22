#!/usr/bin/env python3
"""Check the account id, region, and the job's OIDC subject.

The caller passes the account id and region. This script does not read
secrets or variables. When both are set it requests the job's OIDC token
and reads the ``sub`` claim. That claim must be the ID form
``repo:<org>@<org-id>/<repo>@<repo-id>:<claim>``. A name-form subject and
a trust-policy pattern (``*``) both fail. The account id is masked before
any other use and is not printed again. ``ready`` is written only after
the subject check passes, and before the role is assumed.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

# A real token subject. ``*`` is a trust-policy pattern, not a subject.
ID_FORM_SUBJECT = re.compile(
    r"^repo:[A-Za-z0-9_.-]+@[0-9]+/[A-Za-z0-9_.-]+@[0-9]+:[A-Za-z0-9_./:-]+\Z"
)

MISSING_WARNING = (
    "::warning::AWS account id or region is unset, so AWS credentials were not configured."
)
MISSING_SUMMARY = """### AWS credentials were not configured

Set the secret `AWS_ACCOUNT_ID` and the repository variable `AWS_REGION`.
A green result before both are set means the account was not compared.
"""
MISSING_ERROR = "::error::Set the account id and the region before assuming the role."
SUBJECT_ERROR = (
    "::error::OIDC subject is not the ID form "
    "repo:<org>@<org-id>/<repo>@<repo-id>:<claim>."
)


class Decision:
    def __init__(self, exit_code: int, ready: str, stdout: str, summary: str) -> None:
        self.exit_code = exit_code
        self.ready = ready
        self.stdout = stdout
        self.summary = summary


class OidcError(Exception):
    """The job token could not be read."""


def subject_is_id_form(subject: str) -> bool:
    return ID_FORM_SUBJECT.fullmatch(subject) is not None


def parse_required(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError("required must be true or false")


def decide(account_id: str, region: str, required: bool) -> Decision:
    """Return the settings result. Mask first, and do not repeat the account id."""
    lines: list[str] = []
    if account_id:
        lines.append(f"::add-mask::{account_id}")
    if account_id and region:
        return Decision(0, "true", "\n".join(lines) + "\n", "")
    if required:
        lines.append(MISSING_ERROR)
        return Decision(1, "", "\n".join(lines) + "\n", "")
    lines.append(MISSING_WARNING)
    return Decision(0, "false", "\n".join(lines) + "\n", MISSING_SUMMARY)


def fetch_oidc_token() -> str:
    """Request the job token. The calling job must grant ``id-token: write``."""
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
    if not request_token or not url:
        raise OidcError("The job needs id-token: write so the OIDC subject can be read.")
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}audience=sts.amazonaws.com",
        headers={
            "Authorization": f"bearer {request_token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as error:
        raise OidcError("Could not read the OIDC token.") from error
    value = payload.get("value") if isinstance(payload, dict) else None
    if not isinstance(value, str) or value.count(".") < 2:
        raise OidcError("The OIDC response did not include a token.")
    return value


def subject_from_jwt(token: str) -> str:
    """Read ``sub`` from a JWT payload. The token came from GitHub over HTTPS."""
    parts = token.split(".")
    if len(parts) < 2 or not parts[1]:
        raise OidcError("The OIDC token is not a JWT.")
    padding = "=" * (-len(parts[1]) % 4)
    try:
        raw = base64.urlsafe_b64decode(parts[1] + padding)
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        raise OidcError("The OIDC token payload could not be read.") from error
    subject = payload.get("sub") if isinstance(payload, dict) else None
    if not isinstance(subject, str) or not subject:
        raise OidcError("The OIDC token has no sub claim.")
    return subject


def main(fetch_token=None) -> int:
    fetch = fetch_token or fetch_oidc_token
    try:
        required = parse_required(os.environ.get("REQUIRED", "true"))
    except ValueError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    result = decide(
        os.environ.get("ACCOUNT_ID", ""),
        os.environ.get("AWS_REGION", ""),
        required,
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.exit_code != 0:
        return result.exit_code
    if result.ready != "true":
        _append_output("ready", "false")
        if result.summary:
            _append_summary(result.summary)
        return 0
    try:
        subject = subject_from_jwt(fetch())
    except OidcError as error:
        print(f"::error::{error}")
        return 1
    if not subject_is_id_form(subject):
        print(f"{SUBJECT_ERROR} The token sub is: {subject}")
        return 1
    _append_output("ready", "true")
    return 0


def _append_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def _append_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
