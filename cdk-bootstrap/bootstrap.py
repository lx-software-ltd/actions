#!/usr/bin/env python3
"""Bootstrap the CDK toolkit stack.

The caller has already assumed a role and set up Node.js. This checks
the account id and region without printing the account id, then runs
the same npm and cdk bootstrap commands the product workflows ran.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

ACCOUNT_RE = re.compile(r"\b\d{12}\b")
ACCOUNT_EXACT = re.compile(r"^\d{12}\Z")
QUALIFIER_RE = re.compile(r"^[A-Za-z0-9]+\Z")
REGION_RE = re.compile(r"^[a-z0-9-]+\Z")

Runner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


class BootstrapError(Exception):
    """The inputs are wrong, or bootstrap failed before CDK ran."""


def decide(
    directory: str, account_id: str, region: str, qualifier: str
) -> tuple[Path, str, str, str]:
    """Validate the inputs. Return the directory, account, region, and qualifier."""
    chosen_dir = directory.strip()
    if not chosen_dir:
        raise BootstrapError("Set working-directory.")
    app = Path(chosen_dir)
    if not (app / "package.json").is_file():
        raise BootstrapError(f"Missing {chosen_dir}/package.json")
    chosen_account = account_id.strip()
    if ACCOUNT_EXACT.fullmatch(chosen_account) is None:
        raise BootstrapError("Account id must be 12 digits.")
    chosen_region = region.strip()
    if not chosen_region:
        raise BootstrapError("Set the region before bootstrapping CDK.")
    if REGION_RE.fullmatch(chosen_region) is None:
        raise BootstrapError(f"Region is not an AWS region name. Got: {chosen_region}")
    chosen_qualifier = qualifier.strip()
    if chosen_qualifier and QUALIFIER_RE.fullmatch(chosen_qualifier) is None:
        raise BootstrapError(
            "Bootstrap qualifier must be letters and digits. "
            f"Got: {chosen_qualifier}"
        )
    return app, chosen_account, chosen_region, chosen_qualifier


def commands(account_id: str, region: str, qualifier: str) -> list[list[str]]:
    """npm ci, an optional build, then cdk bootstrap."""
    bootstrap = ["npx", "cdk", "bootstrap"]
    if qualifier:
        bootstrap.extend(["--qualifier", qualifier])
    bootstrap.append(f"aws://{account_id}/{region}")
    return [
        ["npm", "ci"],
        ["npm", "run", "build", "--if-present"],
        bootstrap,
    ]


def redact(text: str, account_id: str) -> str:
    """Hide the account id. Other text stays."""
    cleaned = text.replace(account_id, "***") if account_id else text
    return ACCOUNT_RE.sub("***", cleaned)


def _run(argv: list[str], directory: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )


def main(run: Runner | None = None) -> int:
    """Bootstrap. Return the CDK exit code."""
    try:
        directory, account_id, region, qualifier = decide(
            os.environ.get("WORKING_DIRECTORY", ""),
            os.environ.get("ACCOUNT_ID", ""),
            os.environ.get("AWS_REGION", ""),
            os.environ.get("QUALIFIER", ""),
        )
    except BootstrapError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    print(f"::add-mask::{account_id}")
    for argv in commands(account_id, region, qualifier):
        completed = (run or _run)(argv, directory)
        output = redact((completed.stdout or "") + (completed.stderr or ""), account_id)
        if output:
            print(output, end="" if output.endswith("\n") else "\n")
        if completed.returncode != 0:
            print("::error::CDK bootstrap failed.", file=sys.stderr)
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
