#!/usr/bin/env python3
"""Check a repository against the CI contract.

``mode`` is ``warn`` or ``enforce``. Warn prints the findings and exits 0.
Enforce exits 1 when there is a finding.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
RUNNERS = {"ubuntu-26.04", "macos-26"}
GATED = {"lint.yml": "lint", "test.yml": "test"}


def _uses(line: str) -> str | None:
    match = re.search(r"uses:\s+(\S+)", line)
    if not match:
        return None
    return match.group(1)


def _pull_request_has_paths(text: str) -> bool:
    in_on = False
    in_pull = False
    for line in text.splitlines():
        if line.startswith("on:"):
            in_on = True
            in_pull = False
            continue
        if in_on and line and not line.startswith(" "):
            in_on = False
            in_pull = False
        if not in_on:
            continue
        if line.startswith("  ") and not line.startswith("    "):
            in_pull = line.strip() == "pull_request:"
            continue
        if in_pull and line.strip().startswith("paths:"):
            return True
    return False


def findings(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    pins: list[str] = []
    if not workflow_dir.is_dir():
        return [".github/workflows is missing"]
    for path in sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml")):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        if not any(line.startswith("permissions:") for line in text.splitlines()):
            errors.append(f"{rel}: missing a top-level permissions block")
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("runs-on:"):
                label = stripped.split(":", 1)[1].strip().strip("'\"")
                if label not in RUNNERS:
                    errors.append(f"{rel}:{line_number}: runner {label} is not ubuntu-26.04 or macos-26")
            uses = _uses(line)
            if uses is None or uses.startswith("./"):
                continue
            ref = uses.rsplit("@", 1)[-1] if "@" in uses else ""
            if not SHA.fullmatch(ref):
                errors.append(f"{rel}:{line_number}: {uses} is not pinned by commit SHA")
                continue
            if uses.startswith("lx-software-ltd/actions/"):
                pins.append(ref)
        if path.name in GATED and _pull_request_has_paths(text):
            errors.append(f"{rel}: pull_request has a path filter")
    for filename, job in GATED.items():
        path = workflow_dir / filename
        if not path.is_file():
            errors.append(f".github/workflows/{filename}: missing the {job} gate")
            continue
        if not re.search(rf"(?m)^  {job}:\s*$", path.read_text(encoding="utf-8")):
            errors.append(f".github/workflows/{filename}: missing the {job} job")
    unique = sorted(set(pins))
    if len(unique) > 1:
        errors.append("more than one lx-software-ltd/actions commit: " + ", ".join(unique))
    pre_commit = root / ".pre-commit-config.yaml"
    if pre_commit.is_file():
        revs = re.findall(
            r"repo:\s+\S*lx-software-ltd/actions\S*\n(?:.*\n)*?\s*rev:\s*(\S+)",
            pre_commit.read_text(encoding="utf-8"),
        )
        for rev in revs:
            if unique and rev not in unique:
                errors.append(f".pre-commit-config.yaml rev {rev} is not the actions commit {unique[0]}")
            if not SHA.fullmatch(rev):
                errors.append(f".pre-commit-config.yaml rev {rev} is not a commit SHA")
        if unique and not revs and "lx-software-ltd/actions" in pre_commit.read_text(encoding="utf-8"):
            errors.append(".pre-commit-config.yaml names actions but has no rev")
    return errors


def main() -> int:
    mode = os.environ.get("CONFORMANCE_MODE", "warn")
    if mode not in {"warn", "enforce"}:
        print("workflow-conformance: mode must be warn or enforce", file=sys.stderr)
        return 1
    root_text = os.environ.get("CONFORMANCE_ROOT", "").strip()
    root = Path(root_text).resolve() if root_text else Path.cwd().resolve()
    found = findings(root)
    if not found:
        print("Workflow conformance passed.")
        return 0
    print(f"Workflow conformance found {len(found)} issue(s):", file=sys.stderr)
    for item in found:
        print(f"- {item}", file=sys.stderr)
    if mode == "warn":
        print("Workflow conformance is in warn mode.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
