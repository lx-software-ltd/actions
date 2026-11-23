#!/usr/bin/env python3
"""Read named CloudFormation stack outputs into one JSON step output.

A composite action cannot declare an output name per key. The caller
reads the keys it asked for from the ``json`` output. This does not
change the stack.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from stack_outputs import (  # noqa: E402
    ReadError,
    command,
    prepare,
    redact,
    select,
)

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def write_output(payload: str, present: bool) -> None:
    """Write the JSON object and whether the stack exists.

    The JSON is one line, so the delimiter stays intact.
    """
    path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not path:
        raise ReadError("GITHUB_OUTPUT is unset.")
    flag = "true" if present else "false"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("json<<CFN_OUTPUTS_JSON\n")
        handle.write(payload)
        handle.write("\nCFN_OUTPUTS_JSON\n")
        handle.write(f"present={flag}\n")


def _run_aws(command_args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command_args,
        capture_output=True,
        text=True,
        check=False,
    )


def _missing_stack(detail: str) -> bool:
    return "does not exist" in detail.lower()


def main(run_aws: Runner | None = None) -> int:
    """Read the named outputs. Return 0 when every required key has a value."""
    try:
        stack, region, required, optional, allow_missing = prepare(
            os.environ.get("STACK", ""),
            os.environ.get("AWS_REGION", ""),
            os.environ.get("OUTPUTS", ""),
            os.environ.get("OPTIONAL", ""),
            os.environ.get("ALLOW_MISSING", "false"),
        )
    except ReadError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    completed = (run_aws or _run_aws)(command(stack, region))
    if completed.returncode != 0:
        detail = redact((completed.stderr or "") + (completed.stdout or "")).strip()
        if "AccessDenied" in detail:
            print(
                "::error::GitHubActionsRole needs cloudformation:DescribeStacks "
                f"on stack {stack} in {region}.",
                file=sys.stderr,
            )
            if detail:
                print(detail, file=sys.stderr)
            return 1
        if allow_missing and _missing_stack(detail):
            try:
                write_output("{}", present=False)
            except ReadError as exc:
                print(f"::error::{exc}", file=sys.stderr)
                return 1
            print(f"::notice::Stack {stack} does not exist in {region}.")
            return 0
        print(
            f"::error::Could not read stack {stack} in {region}.",
            file=sys.stderr,
        )
        if detail:
            print(detail, file=sys.stderr)
        return 1
    try:
        chosen = select(completed.stdout or "", required, optional)
        write_output(json.dumps(chosen, separators=(",", ":")), present=True)
    except ReadError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    print(f"Read {len(chosen)} output(s) from stack {stack}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
