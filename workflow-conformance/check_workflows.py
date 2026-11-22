#!/usr/bin/env python3
"""Check a repository against the CI contract.

``mode`` is ``warn`` or ``enforce``. Warn prints the findings and exits 0.
Enforce exits 1 when there is a finding.

``profile`` is ``producer`` or ``product``. The producer is this repository.
Product repositories also need the target security jobs and ``semgrep/ci``.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
RUNNERS = {"ubuntu-26.04", "macos-26"}
GATED = {"lint.yml": "lint", "test.yml": "test"}
REQUIRE_JOBS = re.compile(
    r"uses:\s+lx-software-ltd/actions/require-jobs@[0-9a-f]{40}\b"
)
PRODUCT_SECURITY_JOBS = (
    "checkov",
    "codeql",
    "pii-denylist",
    "secrets-scan",
    "dependency-audit",
    "bandit",
    "npm-audit",
    "security-summary",
)


def _uses(line: str) -> str | None:
    # Anchor at the line. "statuses: write" contains the letters uses:.
    match = re.search(r"^\s*(-\s*)?uses:\s+(\S+)", line)
    if not match:
        return None
    return match.group(2)


def _workflows(workflow_dir: Path) -> list[Path]:
    return sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))


def _pull_request_has_path_filter(text: str) -> bool:
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
        if not in_pull:
            continue
        stripped = line.strip()
        if stripped.startswith("paths:") or stripped.startswith("paths-ignore:"):
            return True
    return False


def _jobs(text: str) -> dict[str, str]:
    lines = text.splitlines()
    start = next((index + 1 for index, line in enumerate(lines) if line == "jobs:" or line.startswith("jobs:")), None)
    if start is None:
        return {}
    jobs: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith(" "):
            break
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            if current is not None:
                jobs[current] = "\n".join(body)
            current = match.group(1)
            body = []
            continue
        if current is not None:
            body.append(line)
    if current is not None:
        jobs[current] = "\n".join(body)
    return jobs


def _needs(body: str) -> list[str]:
    inline = re.search(r"(?m)^    needs:\s*\[([^\]]*)\]\s*$", body)
    if inline:
        return [item.strip().strip("'\"") for item in inline.group(1).split(",") if item.strip()]
    names: list[str] = []
    in_needs = False
    for line in body.splitlines():
        if re.match(r"^    needs:\s*$", line):
            in_needs = True
            continue
        if not in_needs:
            continue
        item = re.match(r"^      - (\S+)\s*$", line)
        if item:
            names.append(item.group(1).strip("'\""))
            continue
        break
    return names


def _job_name(job_id: str, body: str) -> str:
    match = re.search(r"(?m)^    name:\s*(\S+)\s*$", body)
    return match.group(1) if match else job_id


def _images(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        image = re.search(r"\bimage:\s*(\S+)", stripped)
        if image:
            found.append((line_number, image.group(1).strip("'\"")))
            continue
        container = re.match(r"container:\s+(\S+)\s*$", stripped)
        if container:
            found.append((line_number, container.group(1).strip("'\"")))
    return found


def _gate_findings(rel: str, job: str, jobs: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if job not in jobs:
        errors.append(f"{rel}: missing the {job} job")
        return errors
    body = jobs[job]
    if not re.search(r"(?m)^    if:\s*(?:always\(\)|\$\{\{\s*always\(\)\s*\}\})\s*$", body):
        errors.append(f"{rel}: {job} is missing if: always()")
    needed = _needs(body)
    missing = [name for name in jobs if name != job and name not in needed]
    extra = [name for name in needed if name not in jobs]
    if missing or extra or len(needed) != len(jobs) - 1:
        errors.append(
            f"{rel}: {job} needs {', '.join(needed) or 'nothing'}; "
            f"the other jobs are {', '.join(name for name in jobs if name != job) or 'none'}"
        )
    if not REQUIRE_JOBS.search(body):
        errors.append(f"{rel}: {job} does not pin lx-software-ltd/actions/require-jobs by commit SHA")
    return errors


def _pre_commit_actions_revs(text: str) -> tuple[bool, list[str]]:
    found = False
    revs: list[str] = []
    for block in re.split(r"(?m)^[ \t]*-[ \t]*repo:\s*", text)[1:]:
        header = block.splitlines()[0] if block.splitlines() else ""
        if "lx-software-ltd/actions" not in header:
            continue
        found = True
        match = re.search(r"(?m)^[ \t]+rev:\s+(\S+)\s*$", block)
        revs.append(match.group(1) if match else "")
    return found, revs


def findings(root: Path, profile: str = "product") -> list[str]:
    if profile not in {"product", "producer"}:
        return [f"workflow-conformance: unknown profile {profile}"]
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    pins: list[str] = []
    if not workflow_dir.is_dir():
        return [".github/workflows is missing"]
    for path in _workflows(workflow_dir):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        if not any(line.startswith("permissions:") for line in text.splitlines()):
            errors.append(f"{rel}: missing a top-level permissions block")
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
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
                if re.search(r"#\s*main\s+\d{4}-\d{2}-\d{2}\b", line) is None:
                    errors.append(
                        f"{rel}:{line_number}: {uses} needs a '# main YYYY-MM-DD' comment"
                    )
        for line_number, image in _images(text):
            if not DIGEST.search(image):
                errors.append(f"{rel}:{line_number}: image {image} is not pinned by digest")
        if path.name in GATED and _pull_request_has_path_filter(text):
            errors.append(f"{rel}: pull_request has a path filter")
    for filename, job in GATED.items():
        path = workflow_dir / filename
        if not path.is_file():
            errors.append(f".github/workflows/{filename}: missing the {job} gate")
            continue
        errors.extend(_gate_findings(f".github/workflows/{filename}", job, _jobs(path.read_text(encoding="utf-8"))))
    security = workflow_dir / "security.yml"
    if profile == "product" and not security.is_file():
        errors.append(".github/workflows/security.yml: missing")
    if security.is_file():
        security_jobs = _jobs(security.read_text(encoding="utf-8"))
        errors.extend(_gate_findings(".github/workflows/security.yml", "security-summary", security_jobs))
        if profile == "product":
            for job in PRODUCT_SECURITY_JOBS:
                if job not in security_jobs:
                    errors.append(f".github/workflows/security.yml: missing job {job}")
    if profile == "product":
        semgrep = workflow_dir / "semgrep.yml"
        if not semgrep.is_file():
            errors.append(".github/workflows/semgrep.yml: missing the semgrep/ci job")
        else:
            semgrep_jobs = _jobs(semgrep.read_text(encoding="utf-8"))
            names = {_job_name(job_id, body) for job_id, body in semgrep_jobs.items()}
            if "semgrep/ci" not in semgrep_jobs and "semgrep/ci" not in names:
                errors.append(".github/workflows/semgrep.yml: missing the semgrep/ci job")
    unique = sorted(set(pins))
    if len(unique) > 1:
        errors.append("more than one lx-software-ltd/actions commit: " + ", ".join(unique))
    pre_commit = root / ".pre-commit-config.yaml"
    if pre_commit.is_file():
        found, revs = _pre_commit_actions_revs(pre_commit.read_text(encoding="utf-8"))
        if found:
            for rev in revs:
                if rev == "":
                    errors.append(".pre-commit-config.yaml names actions but has no rev")
                    continue
                if not SHA.fullmatch(rev):
                    errors.append(f".pre-commit-config.yaml rev {rev} is not a commit SHA")
                elif unique and rev not in unique:
                    errors.append(
                        f".pre-commit-config.yaml rev {rev} is not the actions commit {unique[0]}"
                    )
    return errors


def main() -> int:
    mode = os.environ.get("CONFORMANCE_MODE", "warn")
    profile = os.environ.get("CONFORMANCE_PROFILE", "product")
    if mode not in {"warn", "enforce"}:
        print("workflow-conformance: mode must be warn or enforce", file=sys.stderr)
        return 1
    if profile not in {"product", "producer"}:
        print("workflow-conformance: profile must be product or producer", file=sys.stderr)
        return 1
    root_text = os.environ.get("CONFORMANCE_ROOT", "").strip()
    root = Path(root_text).resolve() if root_text else Path.cwd().resolve()
    found = findings(root, profile)
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
