#!/usr/bin/env python3
"""Run ``cdk diff``, mask the account id, and write the step summary."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

SPLIT = re.compile(r"[,\s]+")

Runner = Callable[[list[str], str], tuple[int, str]]


def split_list(value: str) -> list[str]:
    """Split a stack list or a simple argument string on commas and space."""
    return [part for part in SPLIT.split(value.strip()) if part]


def read_args_file(path: str) -> list[str]:
    """Read a null-delimited argument list. Empty pieces are dropped."""
    raw = Path(path).read_bytes()
    return [part.decode("utf-8") for part in raw.split(b"\0") if part]


def command(stacks: list[str], args: list[str]) -> list[str]:
    """The diff command. ``--no-install`` uses the CDK from ``npm ci``."""
    return ["npx", "--no-install", "cdk", "diff", "--no-color", *args, *stacks]


def mask(text: str, account_id: str) -> str:
    """Replace the account id. An empty id leaves the text unchanged."""
    if not account_id:
        return text
    return text.replace(account_id, "***")


def summary_block(text: str) -> str:
    """The markdown block written for one diff."""
    return "### CDK diff\n\n```\n" + text.rstrip("\n") + "\n```\n"


def write_summary(text: str, summary_path: str) -> None:
    """Append the diff to a summary file."""
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(summary_block(text))


def _run_cdk(command_args: list[str], directory: str) -> tuple[int, str]:
    completed = subprocess.run(
        command_args,
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output


def main(run_cdk: Runner | None = None) -> int:
    """Run the diff. Return the CDK exit code."""
    directory = os.environ.get("WORKING_DIRECTORY", "").strip()
    if not directory:
        print("::error::Set working-directory.", file=sys.stderr)
        return 1
    package = Path(directory) / "package.json"
    if not package.is_file():
        print(f"Missing {directory}/package.json")
        return 0

    args_file = os.environ.get("ARGS_FILE", "").strip()
    if args_file:
        extra = read_args_file(args_file)
    else:
        extra = split_list(os.environ.get("ARGS", ""))
    stacks = split_list(os.environ.get("STACKS", ""))
    account_id = os.environ.get("ACCOUNT_ID", "")
    write = os.environ.get("SUMMARY", "true").strip() == "true"

    code, output = (run_cdk or _run_cdk)(command(stacks, extra), directory)
    masked = mask(output, account_id)
    sys.stdout.write(masked)
    if write:
        # Each step has its own GITHUB_STEP_SUMMARY, so a later step cannot
        # read this one. The copy under RUNNER_TEMP is the same text.
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
        if summary_path:
            write_summary(masked, summary_path)
        temp = os.environ.get("RUNNER_TEMP", "").strip()
        if temp:
            Path(temp, "cdk-diff-summary.md").write_text(
                summary_block(masked),
                encoding="utf-8",
            )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
