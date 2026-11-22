#!/usr/bin/env python3
"""Read named CloudFormation stack outputs into one JSON step output.

A composite action cannot declare an output name per key. The caller
reads the keys it asked for from the ``json`` output. This does not
change the stack.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Callable

ACCOUNT_RE = re.compile(r"\b\d{12}\b")
STACK_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*\Z")
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*\Z")
REGION_RE = re.compile(r"^[a-z0-9-]+\Z")

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class ReadError(Exception):
    """The inputs are wrong, or the requested outputs are not there."""


def split_keys(text: str) -> list[str]:
    """Split a comma or whitespace list. Keep the first copy of each key."""
    keys: list[str] = []
    for part in re.split(r"[\s,]+", text.strip()):
        if part and part not in keys:
            keys.append(part)
    return keys


def redact(text: str) -> str:
    """Hide a 12-digit account id. Other text stays."""
    return ACCOUNT_RE.sub("***", text)


def decide(stack: str, region: str, outputs: str) -> tuple[str, str, list[str]]:
    """Validate the inputs. Return the stack, region, and keys."""
    chosen_stack = stack.strip()
    chosen_region = region.strip()
    keys = split_keys(outputs)
    if not chosen_stack:
        raise ReadError("Set the stack name.")
    if STACK_RE.fullmatch(chosen_stack) is None:
        raise ReadError(f"Stack name is not a CloudFormation name. Got: {chosen_stack}")
    if not chosen_region:
        raise ReadError("Set the region before reading stack outputs.")
    if REGION_RE.fullmatch(chosen_region) is None:
        raise ReadError(f"Region is not an AWS region name. Got: {chosen_region}")
    if not keys:
        raise ReadError("Set outputs to the CloudFormation output keys to read.")
    rejected = [key for key in keys if KEY_RE.fullmatch(key) is None]
    if rejected:
        raise ReadError(
            "Output keys must be letters and digits. Got: " + ", ".join(rejected)
        )
    return chosen_stack, chosen_region, keys


def command(stack: str, region: str) -> list[str]:
    return [
        "aws",
        "cloudformation",
        "describe-stacks",
        "--stack-name",
        stack,
        "--region",
        region,
        "--output",
        "json",
    ]


def select(document: str, keys: list[str]) -> dict[str, str]:
    """Return the requested keys. An empty or missing value is an error."""
    try:
        payload = json.loads(document)
    except json.JSONDecodeError as exc:
        raise ReadError("describe-stacks did not return JSON.") from exc
    stacks = payload.get("Stacks") if isinstance(payload, dict) else None
    if not isinstance(stacks, list) or not stacks or not isinstance(stacks[0], dict):
        raise ReadError("describe-stacks returned no stack.")
    raw = stacks[0].get("Outputs") or []
    if not isinstance(raw, list):
        raise ReadError("describe-stacks returned no outputs.")
    found: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = item.get("OutputKey")
        value = item.get("OutputValue")
        if isinstance(key, str) and isinstance(value, str) and value:
            found[key] = value
    missing = [key for key in keys if key not in found]
    if missing:
        raise ReadError("Stack is missing " + ", ".join(missing) + ".")
    return {key: found[key] for key in keys}


def write_output(payload: str) -> None:
    """Write one JSON object. It is one line, so the delimiter stays intact."""
    path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not path:
        raise ReadError("GITHUB_OUTPUT is unset.")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("json<<CFN_OUTPUTS_JSON\n")
        handle.write(payload)
        handle.write("\nCFN_OUTPUTS_JSON\n")


def _run_aws(command_args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command_args,
        capture_output=True,
        text=True,
        check=False,
    )


def main(run_aws: Runner | None = None) -> int:
    """Read the named outputs. Return 0 when every key has a value."""
    try:
        stack, region, keys = decide(
            os.environ.get("STACK", ""),
            os.environ.get("AWS_REGION", ""),
            os.environ.get("OUTPUTS", ""),
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
        else:
            print(
                f"::error::Could not read stack {stack} in {region}.",
                file=sys.stderr,
            )
        if detail:
            print(detail, file=sys.stderr)
        return 1
    try:
        chosen = select(completed.stdout or "", keys)
        write_output(json.dumps(chosen, separators=(",", ":")))
    except ReadError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    print(f"Read {len(chosen)} output(s) from stack {stack}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
