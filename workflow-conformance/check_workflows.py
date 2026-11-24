#!/usr/bin/env python3
"""Check a repository against the CI contract.

``mode`` is ``enforce`` or ``warn``. Enforce exits 1 when there is a finding.
Warn prints the findings and exits 0. The default is enforce.

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
GATED = {"lint.yml": "lint", "test.yml": "test", "security.yml": "security-summary"}
PATH_FILTERED = {"lint.yml", "test.yml", "security.yml"}
REQUIRE_JOBS = re.compile(
    r"uses:\s+lx-software-ltd/actions/require-jobs@[0-9a-f]{40}\b"
)
DESCRIBE_STACKS_ALLOW = {
    ".github/workflows/import-legacy-crm.yml",
}
SETUP_ACTION = re.compile(r"""uses:\s+['"]?actions/setup-(?:node|python)@""")
CDK_ACTION = re.compile(
    r"""uses:\s+['"]?lx-software-ltd/actions/cdk-(deploy|diff)@"""
)
_BLOCK = {"|", ">", "|-", ">-", "|+", ">+"}
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


def _permission_findings(rel: str, text: str) -> list[str]:
    """Top-level permissions are contents: read. A job sets anything more."""
    for index, line in enumerate(text.splitlines()):
        if line.startswith(" ") or line.startswith("#") or not line.startswith("permissions:"):
            continue
        rest = line.split(":", 1)[1].strip()
        if rest:
            compact = rest.replace(" ", "").replace("{", "").replace("}", "")
            if compact in {"contents:read", "'contents':read", '"contents":read'}:
                return []
            return [f"{rel}: top-level permissions must be contents: read"]
        keys: list[str] = []
        for follow in text.splitlines()[index + 1 :]:
            if not follow.strip() or follow.strip().startswith("#"):
                continue
            if not follow.startswith(" "):
                break
            if follow.startswith("  ") and not follow.startswith("    "):
                keys.append(follow.strip())
        if keys == ["contents: read"]:
            return []
        return [f"{rel}: top-level permissions must be contents: read"]
    return [f"{rel}: missing a top-level permissions block"]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _without_comment(text: str) -> str:
    """Drop a trailing comment. A hash inside quotes stays."""
    quote = ""
    for index, char in enumerate(text):
        if char in {"'", '"'}:
            quote = "" if quote == char else (quote or char)
            continue
        if char == "#" and not quote:
            return text[:index].rstrip()
    return text.rstrip()


def _scalar(raw: str) -> tuple[str, bool]:
    text = _without_comment(raw.strip())
    if text in _BLOCK:
        return "", True
    if len(text) >= 2 and text[0] in {"'", '"'} and text.endswith(text[0]):
        return text[1:-1], False
    return text, False


def _plan_token(name: str, value: str) -> str:
    kind = "file" if name == "plan-file" else "inline"
    return f"{kind}:{value}"


def _with_plans(lines: list[str], start: int, step_indent: int) -> set[str]:
    """plan and plan-file on the cdk step's with block, including a block body."""
    found: set[str] = set()
    in_with = False
    with_indent = 0
    pending: tuple[str, int] | None = None
    block: list[str] = []
    index = start
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.strip().startswith("#"):
            if pending is not None:
                block.append("")
            index += 1
            continue
        indent = _indent(line)
        if indent <= step_indent:
            break
        if pending is not None:
            if indent > pending[1]:
                block.append(line.strip())
                index += 1
                continue
            while block and block[-1] == "":
                block.pop()
            found.add(_plan_token(pending[0], "\n".join(block)))
            pending = None
            block = []
        stripped = line.strip()
        if re.fullmatch(r"with:\s*", _without_comment(stripped)):
            in_with = True
            with_indent = indent
            index += 1
            continue
        if in_with and indent <= with_indent:
            in_with = False
        if not in_with:
            index += 1
            continue
        key = re.fullmatch(r"(plan-file|plan):(.*)", stripped)
        if key:
            value, is_block = _scalar(key.group(2))
            if is_block:
                pending = (key.group(1), indent)
                block = []
            else:
                found.add(_plan_token(key.group(1), value))
        index += 1
    if pending is not None:
        while block and block[-1] == "":
            block.pop()
        found.add(_plan_token(pending[0], "\n".join(block)))
    return found


def _alignment_findings(root: Path) -> list[str]:
    """Shared setup, one plan, and no inline describe-stacks."""
    notes: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return []
    deploy_plans: set[str] = set()
    diff_plans: set[str] = set()
    saw_deploy = False
    saw_diff = False
    for path in _workflows(workflow_dir):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for line_number, line in enumerate(lines, start=1):
            if line.strip().startswith("#"):
                continue
            if SETUP_ACTION.search(line):
                notes.append(
                    f"{rel}:{line_number}: use lx-software-ltd/actions/setup-node "
                    "or setup-python"
                )
            if "describe-stacks" in line and rel not in DESCRIBE_STACKS_ALLOW:
                notes.append(f"{rel}:{line_number}: describe-stacks stays out of workflows")
            action = CDK_ACTION.search(line)
            if action is None:
                continue
            plans = _with_plans(lines, line_number, _indent(line)) or {""}
            if action.group(1) == "deploy":
                saw_deploy = True
                deploy_plans |= plans
            else:
                saw_diff = True
                diff_plans |= plans
    same = deploy_plans == diff_plans and len(deploy_plans) == 1
    if saw_deploy and saw_diff and not same:
        notes.append(
            "cdk-diff and cdk-deploy do not name the same plan file: "
            f"diff={sorted(diff_plans)} deploy={sorted(deploy_plans)}"
        )
    return notes


def advisory_findings(root: Path, profile: str = "product") -> list[str]:
    """Alignment findings. Callers warn by default and enforce per repository."""
    if profile != "product":
        return []
    return _alignment_findings(root)


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
        errors.extend(_permission_findings(rel, text))
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
        if path.name in PATH_FILTERED and _pull_request_has_path_filter(text):
            errors.append(f"{rel}: pull_request has a path filter")
    for filename, job in GATED.items():
        path = workflow_dir / filename
        if not path.is_file():
            errors.append(f".github/workflows/{filename}: missing the {job} gate")
            continue
        errors.extend(_gate_findings(f".github/workflows/{filename}", job, _jobs(path.read_text(encoding="utf-8"))))
    security = workflow_dir / "security.yml"
    if security.is_file():
        security_jobs = _jobs(security.read_text(encoding="utf-8"))
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
    mode = os.environ.get("CONFORMANCE_MODE", "enforce")
    profile = os.environ.get("CONFORMANCE_PROFILE", "product")
    alignment = os.environ.get("CONFORMANCE_ALIGNMENT", "warn").strip().lower()
    if mode not in {"warn", "enforce"}:
        print("workflow-conformance: mode must be warn or enforce", file=sys.stderr)
        return 1
    if profile not in {"product", "producer"}:
        print("workflow-conformance: profile must be product or producer", file=sys.stderr)
        return 1
    if alignment not in {"warn", "enforce"}:
        print("workflow-conformance: alignment must be warn or enforce", file=sys.stderr)
        return 1
    root_text = os.environ.get("CONFORMANCE_ROOT", "").strip()
    root = Path(root_text).resolve() if root_text else Path.cwd().resolve()
    found = findings(root, profile)
    aligned = advisory_findings(root, profile)
    advised = aligned if alignment == "warn" else []
    if alignment == "enforce":
        found.extend(aligned)
    for item in advised:
        print(f"::warning::{item}", file=sys.stderr)
    if not found and not advised:
        print("Workflow conformance passed.")
        return 0
    if found:
        print(f"Workflow conformance found {len(found)} issue(s):", file=sys.stderr)
        for item in found:
            print(f"- {item}", file=sys.stderr)
    if advised:
        print(
            f"Workflow conformance found {len(advised)} advisory issue(s).",
            file=sys.stderr,
        )
    if mode == "warn" or not found:
        if mode == "warn" and found:
            print("Workflow conformance is in warn mode.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
