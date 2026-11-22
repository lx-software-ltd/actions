#!/usr/bin/env python3
"""Check the account id and region, and mask the account id.

The caller passes the account id and region. This script does not read
secrets or variables. When a subject is passed it must be the ID form
``repo:<org>@<org-id>/<repo>@<repo-id>:...``. The name form is rejected.
The account id is masked before any other use and is not printed again.
"""

from __future__ import annotations

import os
import re
import sys

# org and repo names, then a numeric id on each, then the claim suffix.
ID_FORM_SUBJECT = re.compile(r"^repo:[A-Za-z0-9_.-]+@[0-9]+/[A-Za-z0-9_.-]+@[0-9]+:.+\Z")

MISSING_WARNING = (
    "::warning::AWS account id or region is unset, so AWS credentials were not configured."
)
MISSING_SUMMARY = """### AWS credentials were not configured

Set the repository variables `AWS_ACCOUNT_ID` and `AWS_REGION`.
A green result before both are set means the account was not compared.
"""
MISSING_ERROR = "::error::Set the account id and the region before assuming the role."
SUBJECT_ERROR = (
    "::error::OIDC subject must be the ID form "
    "repo:<org>@<org-id>/<repo>@<repo-id>:..."
)


class Decision:
    def __init__(self, exit_code: int, ready: str, stdout: str, summary: str) -> None:
        self.exit_code = exit_code
        self.ready = ready
        self.stdout = stdout
        self.summary = summary


def subject_is_id_form(subject: str) -> bool:
    return ID_FORM_SUBJECT.fullmatch(subject) is not None


def parse_required(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError("required must be true or false")


def decide(account_id: str, region: str, required: bool, subject: str) -> Decision:
    """Return the step result. Mask first, and do not repeat the account id."""
    lines: list[str] = []
    if account_id:
        lines.append(f"::add-mask::{account_id}")
    if subject and not subject_is_id_form(subject):
        lines.append(SUBJECT_ERROR)
        return Decision(1, "", "\n".join(lines) + "\n", "")
    if account_id and region:
        return Decision(0, "true", "\n".join(lines) + ("\n" if lines else ""), "")
    if required:
        lines.append(MISSING_ERROR)
        return Decision(1, "", "\n".join(lines) + "\n", "")
    lines.append(MISSING_WARNING)
    return Decision(0, "false", "\n".join(lines) + "\n", MISSING_SUMMARY)


def main() -> int:
    try:
        required = parse_required(os.environ.get("REQUIRED", "true"))
    except ValueError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    result = decide(
        os.environ.get("ACCOUNT_ID", ""),
        os.environ.get("AWS_REGION", ""),
        required,
        os.environ.get("SUBJECT", ""),
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.ready:
        _append_output("ready", result.ready)
    if result.summary:
        _append_summary(result.summary)
    return result.exit_code


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
