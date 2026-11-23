#!/usr/bin/env python3
"""Run ``cdk diff``, mask the account id, and write the step summary."""

from __future__ import annotations

import os
import pty
import re
import subprocess
import sys
import termios
from pathlib import Path
from typing import Callable, Iterator

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


class LineStream:
    """Mask complete lines and write them as they arrive."""

    def __init__(self, account_id: str, write: Callable[[str], object]) -> None:
        self._account_id = account_id
        self._write = write
        self._pending = ""
        self.raw_parts: list[str] = []

    def feed(self, chunk: str) -> None:
        self.raw_parts.append(chunk)
        text = self._pending + chunk.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        self._pending = lines.pop()
        for line in lines:
            self._emit(line + "\n")

    def finish(self) -> str:
        if self._pending:
            self._emit(self._pending)
            self._pending = ""
        return "".join(self.raw_parts)

    def _emit(self, piece: str) -> None:
        self._write(mask(piece, self._account_id))
        flush = getattr(self._write, "__self__", None)
        if flush is sys.stdout:
            sys.stdout.flush()


def _pty_chunks(
    command_args: list[str], directory: str
) -> tuple[subprocess.Popen[bytes], Iterator[str]]:
    """Run a command on a pseudo-terminal so Node flushes each line.

    A pipe makes Node block-buffer stdout. A cancelled or timed-out job
    would then show nothing from the diff.
    """
    master, slave = pty.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[3] = attrs[3] & ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    process = subprocess.Popen(
        command_args,
        cwd=directory,
        stdin=subprocess.DEVNULL,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)

    def chunks() -> Iterator[str]:
        try:
            while True:
                try:
                    data = os.read(master, 4096)
                except OSError:
                    return
                if not data:
                    return
                yield data.decode("utf-8", errors="replace")
        finally:
            os.close(master)

    return process, chunks()


def _run_cdk(command_args: list[str], directory: str, account_id: str) -> tuple[int, str]:
    """Stream masked output. Return the exit code and the raw text."""
    process, chunks = _pty_chunks(command_args, directory)
    stream = LineStream(account_id, sys.stdout.write)
    raw = ""
    try:
        for chunk in chunks:
            stream.feed(chunk)
        raw = stream.finish()
    finally:
        code = process.wait()
    sys.stdout.flush()
    return code, raw


def _deploy():
    root = Path(__file__).resolve().parents[1] / "cdk-deploy"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import cdk_deploy

    return cdk_deploy


def _plan_arguments(extra: list[str]) -> list[str]:
    """Parameter arguments from the same plan the deploy uses."""
    plan_text = os.environ.get("PLAN", "")
    plan_file = os.environ.get("PLAN_FILE", "").strip()
    if not plan_text.strip() and not plan_file:
        return extra
    module = _deploy()
    try:
        plan = module.load_plan_text(plan_text, plan_file)
        path = module._resolve_file(os.environ.get("PARAM_FILE", ""))
        parameters = module._load_object(path) if path else None
        selected = split_list(os.environ.get("STACKS", ""))
        pass_empty = {part for part in os.environ.get("PASS_EMPTY", "").split(",") if part}
        arguments = module.parameter_arguments(
            plan=plan,
            parameters=parameters,
            fmt=os.environ.get("FORMAT", "prefixed-json") or "prefixed-json",
            selected_stacks=selected,
            pass_empty=pass_empty,
            escape_newlines=os.environ.get("ESCAPE_NEWLINES", "false").lower() == "true",
            include_extras=os.environ.get("INCLUDE_EXTRAS", "false").lower() == "true",
        )
    except module.DeployError as exc:
        raise SystemExit(str(exc)) from exc
    return [*arguments, *extra]


def main(run_cdk: Runner | None = None) -> int:
    """Run the diff. Return the CDK exit code."""
    directory = os.environ.get("WORKING_DIRECTORY", "").strip()
    if not directory:
        print("::error::Set working-directory.", file=sys.stderr)
        return 1
    package = Path(directory) / "package.json"
    if not package.is_file():
        message = f"Missing {directory}/package.json"
        print(f"::warning::{message}")
        print(message)
        return 0

    args_file = os.environ.get("ARGS_FILE", "").strip()
    if args_file:
        extra = read_args_file(args_file)
    else:
        extra = split_list(os.environ.get("ARGS", ""))
    try:
        extra = _plan_arguments(extra)
    except SystemExit as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    stacks = split_list(os.environ.get("STACKS", ""))
    account_id = os.environ.get("ACCOUNT_ID", "")
    write = os.environ.get("SUMMARY", "true").strip() == "true"

    if run_cdk is None:
        code, output = _run_cdk(command(stacks, extra), directory, account_id)
        masked = mask(output, account_id)
    else:
        code, output = run_cdk(command(stacks, extra), directory)
        masked = mask(output, account_id)
        sys.stdout.write(masked)
        sys.stdout.flush()
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
