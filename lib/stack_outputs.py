"""Read CloudFormation stack outputs.

cfn-stack-outputs and s3-cloudfront-deploy both import this module.
Neither action loads the other's file.
"""

from __future__ import annotations

import json
import re

ACCOUNT_RE = re.compile(r"\b\d{12}\b")
STACK_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*\Z")
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*\Z")
REGION_RE = re.compile(r"^[a-z0-9-]+\Z")


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


def _checked_keys(keys: list[str]) -> None:
    rejected = [key for key in keys if KEY_RE.fullmatch(key) is None]
    if rejected:
        raise ReadError(
            "Output keys must be letters and digits. Got: " + ", ".join(rejected)
        )


def prepare(
    stack: str,
    region: str,
    outputs: str,
    optional: str = "",
    allow_missing: str = "false",
) -> tuple[str, str, list[str], list[str], bool]:
    """Validate a read. Return stack, region, required keys, optional keys, and allow-missing."""
    chosen_stack = stack.strip()
    chosen_region = region.strip()
    required = split_keys(outputs)
    chosen_optional = split_keys(optional)
    missing_ok = allow_missing.strip().lower() == "true"
    if not chosen_stack:
        raise ReadError("Set the stack name.")
    if STACK_RE.fullmatch(chosen_stack) is None:
        raise ReadError(f"Stack name is not a CloudFormation name. Got: {chosen_stack}")
    if not chosen_region:
        raise ReadError("Set the region before reading stack outputs.")
    if REGION_RE.fullmatch(chosen_region) is None:
        raise ReadError(f"Region is not an AWS region name. Got: {chosen_region}")
    overlap = [key for key in chosen_optional if key in required]
    if overlap:
        raise ReadError(
            "A key is in both outputs and optional: " + ", ".join(overlap)
        )
    _checked_keys([*required, *chosen_optional])
    if not required and not chosen_optional and not missing_ok:
        raise ReadError("Set outputs to the CloudFormation output keys to read.")
    return chosen_stack, chosen_region, required, chosen_optional, missing_ok


def decide(stack: str, region: str, outputs: str) -> tuple[str, str, list[str]]:
    """Validate a required read. Return the stack, region, and keys."""
    chosen_stack, chosen_region, required, _optional, _missing_ok = prepare(
        stack, region, outputs
    )
    return chosen_stack, chosen_region, required


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


def select(
    document: str, keys: list[str], optional: list[str] | None = None
) -> dict[str, str]:
    """Return the requested keys. An empty or missing required value is an error.

    An optional key that is missing or empty becomes an empty string.
    """
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
    chosen = {key: found[key] for key in keys}
    for key in optional or []:
        chosen[key] = found.get(key, "")
    return chosen

