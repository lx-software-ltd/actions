#!/usr/bin/env python3
"""Check composite-action and workflow rules for this repository."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA_OR_LOCAL = re.compile(
    r"uses:\s+(\./\S+|[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?@[0-9a-f]{40}\b)"
)
STEP_START = re.compile(r"^    - ")


def _steps(text: str) -> list[str]:
    lines = text.splitlines()
    steps: list[list[str]] = []
    current: list[str] | None = None
    in_runs = False
    for line in lines:
        if line.startswith("runs:"):
            in_runs = True
        if not in_runs:
            continue
        if STEP_START.match(line):
            if current is not None:
                steps.append(current)
            current = [line]
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        steps.append(current)
    return ["\n".join(step) for step in steps]


def _action_errors(path: Path, text: str, root: Path) -> list[str]:
    errors: list[str] = []
    relative = path.relative_to(root)
    if "using: composite" not in text:
        errors.append(f"{relative}: runs.using must be composite")
    for step in _steps(text):
        if not re.search(r"^\s*run:", step, re.M):
            continue
        if not re.search(r"^\s*shell:", step, re.M):
            errors.append(f"{relative}: a run step must set shell")
        run_at = None
        for index, line in enumerate(step.splitlines()):
            if re.match(r"^\s*run:", line):
                run_at = index
                break
        if run_at is None:
            continue
        run_body = "\n".join(step.splitlines()[run_at:])
        if "${{" in run_body:
            errors.append(f"{relative}: do not interpolate expressions inside run")
    return errors


def _workflow_errors(path: Path, text: str, root: Path) -> list[str]:
    errors: list[str] = []
    relative = path.relative_to(root)
    if not re.search(r"^permissions:\s*$", text, re.M):
        errors.append(f"{relative}: missing top-level permissions")
    if re.search(r"id-token:\s*write", text):
        errors.append(f"{relative}: must not request id-token: write")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("uses:") and SHA_OR_LOCAL.search(stripped) is None:
            errors.append(f"{relative}: pin uses by full SHA or a local path: {stripped}")
        if stripped.startswith("runs-on:") and "ubuntu-26.04" not in stripped:
            errors.append(f"{relative}: runner must be ubuntu-26.04")
    return errors


def check(root: Path | None = None) -> list[str]:
    base = root or ROOT
    errors: list[str] = []
    for path in sorted(base.glob("*/action.yml")):
        errors.extend(_action_errors(path, path.read_text(encoding="utf-8"), base))
    workflow_dir = base / ".github" / "workflows"
    if workflow_dir.is_dir():
        for path in sorted(workflow_dir.glob("*.yml")):
            errors.extend(_workflow_errors(path, path.read_text(encoding="utf-8"), base))
    return errors


def main() -> int:
    errors = check()
    if errors:
        print("action layout check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("action layout check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
