#!/usr/bin/env python3
"""Check composite-action and workflow rules for this repository.

Rules this script enforces:

- A composite action uses ``runs.using: composite``.
- Every ``run`` step sets ``shell``.
- ``${{`` is not interpolated inside a ``run`` body. A later ``env:`` is not
  part of that body.
- An action does not call another action (``uses: ./...``).
- Each action directory has a ``README.md``.
- A third-party ``uses:`` pin is a 40-character SHA with a version comment
  on the same line.
- Workflows set top-level ``permissions``, do not request ``id-token: write``,
  and run on ``ubuntu-26.04``.
- The gate jobs ``lint``, ``test``, and ``security-summary`` do not use a
  local action. A pull request's checkout must not be the code that turns
  the required check green.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA_PIN = re.compile(r"@[0-9a-f]{40}\b")
LOCAL_OR_SHA = re.compile(
    r"uses:\s+(\./\S+|[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?@[0-9a-f]{40}\b)"
)
VERSION_COMMENT = re.compile(r"#\s*\S")
GATE_NAMES = {"lint", "test", "security-summary"}
JOB_KEY = re.compile(r"^  ([A-Za-z0-9_-]+):\s*(?:#.*)?$")
GATE_NAME_FIELD = re.compile(r"(?m)^[ \t]+name:\s*(lint|test|security-summary)\s*$")


def _steps(text: str) -> list[str]:
    """Return composite steps at whatever indent the file uses."""
    lines = text.splitlines()
    steps_index = None
    steps_indent = 0
    in_runs = False
    for index, line in enumerate(lines):
        if line.startswith("runs:"):
            in_runs = True
        if not in_runs:
            continue
        match = re.match(r"^(\s*)steps:\s*$", line)
        if match:
            steps_index = index
            steps_indent = len(match.group(1))
            break
    if steps_index is None:
        return []

    steps: list[list[str]] = []
    current: list[str] | None = None
    item_indent: int | None = None
    for line in lines[steps_index + 1 :]:
        if line.strip() == "":
            if current is not None:
                current.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        is_item = line.lstrip(" ").startswith("- ")
        if is_item and indent >= steps_indent and (item_indent is None or indent == item_indent):
            if current is not None:
                steps.append(current)
            item_indent = indent
            current = [line]
            continue
        if indent <= steps_indent:
            break
        if current is not None:
            current.append(line)
    if current is not None:
        steps.append(current)
    return ["\n".join(step) for step in steps]


def _is_comment(line: str) -> bool:
    return line.strip().startswith("#")


def _has_key(step: str, key: str) -> bool:
    """True when ``key:`` is a step key, including ``- key:`` on the list line."""
    return re.search(rf"(?m)^\s*(?:-\s+)?{key}:", step) is not None


def _run_body(step: str) -> str | None:
    """Return the ``run`` scalar only, not sibling keys such as ``env:``."""
    lines = step.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)(?:-\s+)?run:(.*)$", line)
        if not match:
            continue
        # Indent of the `run` key, so a sibling `env:` is not part of the body
        # when the key sits on the list dash (`- run:`).
        indent = len(match.group(1))
        if line[indent:].startswith("-"):
            indent += 2
        rest = match.group(2).strip()
        if rest in {"|", ">", "|-", ">-", "|+", ">+"}:
            body: list[str] = []
            for follow in lines[index + 1 :]:
                if follow.strip() == "":
                    body.append(follow)
                    continue
                follow_indent = len(follow) - len(follow.lstrip(" "))
                if follow_indent <= indent:
                    break
                body.append(follow)
            return "\n".join(body)
        body = [rest]
        for follow in lines[index + 1 :]:
            if follow.strip() == "":
                break
            follow_indent = len(follow) - len(follow.lstrip(" "))
            if follow_indent <= indent:
                break
            body.append(follow)
        return "\n".join(body)
    return None


def _uses_lines(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if _is_comment(stripped) or "uses:" not in stripped:
            continue
        found.append(stripped)
    return found


def _pin_errors(relative: Path, text: str) -> list[str]:
    errors: list[str] = []
    for stripped in _uses_lines(text):
        if SHA_PIN.search(stripped) and VERSION_COMMENT.search(stripped) is None:
            errors.append(f"{relative}: SHA pin needs a version comment: {stripped}")
    return errors


def _uses_local_action(text: str) -> bool:
    return any(re.search(r"uses:\s+\./", stripped) for stripped in _uses_lines(text))


def _action_errors(path: Path, text: str, root: Path) -> list[str]:
    errors: list[str] = []
    relative = path.relative_to(root)
    if "using: composite" not in text:
        errors.append(f"{relative}: runs.using must be composite")
    if not (path.parent / "README.md").is_file():
        errors.append(f"{relative}: action directory needs a README.md")
    if _uses_local_action(text):
        errors.append(
            f"{relative}: an action must not call another action with uses: ./..."
        )
    errors.extend(_pin_errors(relative, text))
    for step in _steps(text):
        if not _has_key(step, "run"):
            continue
        if not _has_key(step, "shell"):
            errors.append(f"{relative}: a run step must set shell")
        run_body = _run_body(step)
        if run_body is not None and "${{" in run_body:
            errors.append(f"{relative}: do not interpolate expressions inside run")
    return errors


def _job_blocks(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line == "jobs:" or line.startswith("jobs:"):
            start = index + 1
            break
    if start is None:
        return []
    blocks: list[tuple[str, str]] = []
    current_id: str | None = None
    current: list[str] = []
    for line in lines[start:]:
        match = JOB_KEY.match(line)
        if match:
            if current_id is not None:
                blocks.append((current_id, "\n".join(current)))
            current_id = match.group(1)
            current = [line]
            continue
        if current_id is None:
            continue
        if line and not line.startswith(" ") and not line.startswith("#"):
            break
        current.append(line)
    if current_id is not None:
        blocks.append((current_id, "\n".join(current)))
    return blocks


def _workflow_errors(path: Path, text: str, root: Path) -> list[str]:
    errors: list[str] = []
    relative = path.relative_to(root)
    if not re.search(r"^permissions:\s*$", text, re.M):
        errors.append(f"{relative}: missing top-level permissions")
    if re.search(r"id-token:\s*write", text):
        errors.append(f"{relative}: must not request id-token: write")
    for stripped in _uses_lines(text):
        if LOCAL_OR_SHA.search(stripped) is None:
            errors.append(f"{relative}: pin uses by full SHA or a local path: {stripped}")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("runs-on:") and "ubuntu-26.04" not in stripped:
            errors.append(f"{relative}: runner must be ubuntu-26.04")
    errors.extend(_pin_errors(relative, text))
    for job_id, block in _job_blocks(text):
        if job_id not in GATE_NAMES and GATE_NAME_FIELD.search(block) is None:
            continue
        if _uses_local_action(block):
            errors.append(
                f"{relative}: gate job {job_id} must not use a local action; "
                "pin require-jobs at a commit on main"
            )
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
