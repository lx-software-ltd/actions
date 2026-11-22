#!/usr/bin/env python3
"""Read the CDK bootstrap version from SSM.

A missing parameter fails the step. This does not run ``cdk bootstrap``.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Callable

QUALIFIER_RE = re.compile(r"^[A-Za-z0-9]+\Z")
REGION_RE = re.compile(r"^[a-z0-9-]+\Z")
DEFAULT_QUALIFIER = "hnb659fds"

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class BootstrapError(Exception):
    """The check cannot run, or the bootstrap parameter is missing."""


def parameter_name(qualifier: str) -> tuple[str, str]:
    """Return the SSM name and the qualifier it uses."""
    chosen = qualifier.strip() or DEFAULT_QUALIFIER
    if QUALIFIER_RE.fullmatch(chosen) is None:
        raise BootstrapError(
            "Bootstrap qualifier must be letters and digits. "
            f"Got: {chosen}"
        )
    return f"/cdk-bootstrap/{chosen}/version", chosen


def decide(qualifier: str, region: str) -> tuple[str, str, str]:
    """Validate the inputs. Return the parameter, qualifier, and region."""
    chosen_region = region.strip()
    if not chosen_region:
        raise BootstrapError("Set the region before checking CDK bootstrap.")
    if REGION_RE.fullmatch(chosen_region) is None:
        raise BootstrapError(
            f"Region is not an AWS region name. Got: {chosen_region}"
        )
    parameter, chosen = parameter_name(qualifier)
    return parameter, chosen, chosen_region


def hint(parameter: str, qualifier: str) -> str:
    """Failure text. It names the parameter and the role, not an account."""
    return (
        "::error::CDK Bootstrap not found or not accessible.\n"
        f"::error::The SSM parameter '{parameter}' could not be read.\n"
        "\n"
        "Possible causes:\n"
        "  1. CDK Bootstrap missing in this account and region "
        f"for qualifier {qualifier}\n"
        "  2. Permission denied: GitHubActionsRole needs "
        "ssm:GetParameter on /cdk-bootstrap/*\n"
        "  3. Wrong region: Verify AWS_REGION matches the "
        "bootstrapped region\n"
        "\n"
        "If bootstrap was run from another repo, ensure "
        "GitHubActionsRole has:\n"
        f"  - sts:AssumeRole on cdk-{qualifier}-*-role-* resources\n"
        "  - ssm:GetParameter on /cdk-bootstrap/* parameters\n"
    )


def _run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def main(run_aws: Runner | None = None) -> int:
    """Check the bootstrap parameter. Return 0 when it is readable."""
    try:
        parameter, qualifier, region = decide(
            os.environ.get("QUALIFIER", ""),
            os.environ.get("AWS_REGION", ""),
        )
    except BootstrapError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    print(
        "Checking for CDK Bootstrap in the configured account, "
        f"region {region}..."
    )
    command = [
        "aws",
        "ssm",
        "get-parameter",
        "--name",
        parameter,
        "--query",
        "Parameter.Value",
        "--output",
        "text",
        "--region",
        region,
    ]
    completed = (run_aws or _run_aws)(command)
    value = (completed.stdout or "").strip()
    if completed.returncode != 0 or not value or value == "None":
        sys.stdout.write(hint(parameter, qualifier))
        return 1
    print(f"CDK Bootstrap version {value}.")
    print("CDK Bootstrap found. Proceeding with diff...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
