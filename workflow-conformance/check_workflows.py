#!/usr/bin/env python3
"""Check a repository against the CI contract.

``mode`` is ``enforce`` or ``warn``. Enforce exits 1 when there is a finding.
Warn prints the findings and exits 0. The default is enforce.

``profile`` is ``producer`` or ``product``. The producer is this repository.
Product repositories also need the target security jobs and ``semgrep/ci``.

``alignment`` defaults to ``enforce``. ``templates`` defaults to ``warn`` and
compares product workflows with ``templates/workflows``. The producer skips both.
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
SETUP_ACTION = re.compile(r"""uses:\s+['"]?actions/setup-(?:node|python)@""")
CDK_ACTION = re.compile(r"""uses:\s+['"]?lx-software-ltd/actions/cdk-(deploy|diff)@""")
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
_OPTIONAL = re.compile(r"^# template:optional ([a-z0-9-]+)$")
_SET = re.compile(r"^# template:set$")
_END = re.compile(r"^# template:end$")


def _is_set(line: str) -> bool:
    return _SET.match(line.strip()) is not None


def _is_end(line: str) -> bool:
    return _END.match(line.strip()) is not None


def _optional_name(line: str) -> str | None:
    match = _OPTIONAL.match(line.strip())
    return match.group(1) if match else None


def _marker(line: str) -> str:
    """A marker matches at any indent. The comparison stores it without indent."""
    stripped = line.strip()
    if _is_set(stripped) or _is_end(stripped) or _optional_name(stripped):
        return stripped
    return line


_ACTION_PIN = re.compile(
    r"lx-software-ltd/actions/(?P<name>[A-Za-z0-9_.-]+)@"
    r"(?:[0-9a-f]{40}|ACTIONS_PIN)"
    r"(?:[ \t]+# main (?:[0-9]{4}-[0-9]{2}-[0-9]{2}|DATE))?"
)


class _TemplateSyntax(Exception):
    """A template marker is opened and not closed, or closed without an open."""


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
    start = next(
        (
            index + 1
            for index, line in enumerate(lines)
            if line == "jobs:" or line.startswith("jobs:")
        ),
        None,
    )
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
        return [
            item.strip().strip("'\"")
            for item in inline.group(1).split(",")
            if item.strip()
        ]
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
    if not re.search(
        r"(?m)^    if:\s*(?:always\(\)|\$\{\{\s*always\(\)\s*\}\})\s*$", body
    ):
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
        errors.append(
            f"{rel}: {job} does not pin lx-software-ltd/actions/require-jobs by commit SHA"
        )
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
        if (
            line.startswith(" ")
            or line.startswith("#")
            or not line.startswith("permissions:")
        ):
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


def _step_bound(lines: list[str], uses_index: int) -> int:
    """Indent of the step list marker. Keys beside uses stay inside the step."""
    current = lines[uses_index]
    if current.lstrip().startswith("-"):
        return _indent(current)
    uses_indent = _indent(current)
    index = uses_index - 1
    while index >= 0:
        earlier = lines[index]
        if earlier.strip() and not earlier.strip().startswith("#"):
            indent = _indent(earlier)
            if indent < uses_indent:
                return indent
        index -= 1
    return uses_indent


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
            if "describe-stacks" in line:
                notes.append(
                    f"{rel}:{line_number}: describe-stacks stays out of workflows"
                )
            action = CDK_ACTION.search(line)
            if action is None:
                continue
            plans = _with_plans(
                lines, line_number, _step_bound(lines, line_number - 1)
            ) or {""}
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


def _normalize_pins(text: str) -> str:
    """Ignore the shared actions SHA and its date comment."""
    return _ACTION_PIN.sub(
        lambda match: (
            f"lx-software-ltd/actions/{match.group('name')}@ACTIONS_PIN # main DATE"
        ),
        text,
    )


def _consume_balanced(lines: list[str], index: int) -> tuple[list[str], int]:
    """Copy a marker block starting at index, including the matching end."""
    copied: list[str] = []
    depth = 0
    while index < len(lines):
        copied.append(lines[index])
        if _is_set(lines[index]) or _optional_name(lines[index]):
            depth += 1
        elif _is_end(lines[index]):
            depth -= 1
            if depth == 0:
                return copied, index + 1
        index += 1
    raise _TemplateSyntax("unclosed # template:set")


def _strip_sets(lines: list[str]) -> list[str]:
    """Drop the lines a repository may set. The marker lines stay."""
    out: list[str] = []
    index = 0
    while index < len(lines):
        if _is_set(lines[index]):
            block, index = _consume_balanced(lines, index)
            out.append(_marker(block[0]))
            out.append(_marker(block[-1]))
            continue
        if _is_end(lines[index]):
            raise _TemplateSyntax("# template:end without a start")
        out.append(_marker(lines[index]))
        index += 1
    return out


def _extract_optional(lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Replace each optional block with its opening marker."""
    skeleton: list[str] = []
    blocks: dict[str, list[str]] = {}
    index = 0
    while index < len(lines):
        if _is_set(lines[index]):
            block, index = _consume_balanced(lines, index)
            skeleton.extend(_marker(line) for line in block)
            continue
        name = _optional_name(lines[index])
        if name is None:
            if _is_end(lines[index]):
                raise _TemplateSyntax("# template:end without a start")
            skeleton.append(_marker(lines[index]))
            index += 1
            continue
        if name in blocks:
            raise _TemplateSyntax(f"repeated # template:optional {name}")
        skeleton.append(_marker(lines[index]))
        index += 1
        depth = 1
        inner: list[str] = []
        while index < len(lines) and depth:
            if _optional_name(lines[index]) or _is_set(lines[index]):
                depth += 1
                inner.append(lines[index])
            elif _is_end(lines[index]):
                depth -= 1
                if depth == 0:
                    index += 1
                    break
                inner.append(lines[index])
            else:
                inner.append(lines[index])
            index += 1
        else:
            raise _TemplateSyntax(f"unclosed # template:optional {name}")
        blocks[name] = inner
    return skeleton, blocks


def _prepare(text: str) -> tuple[list[str], dict[str, list[str]]]:
    normalized = _normalize_pins(text.replace("\r\n", "\n"))
    skeleton, blocks = _extract_optional(normalized.splitlines())
    return _strip_sets(skeleton), {
        name: _strip_sets(body) for name, body in blocks.items()
    }


def _skeleton_diff(template: list[str], product: list[str]) -> str | None:
    """Return the first unmarked line that differs. An optional block may be absent."""
    template_index = 0
    product_index = 0
    while template_index < len(template) or product_index < len(product):
        if template_index < len(template) and _optional_name(template[template_index]):
            if (
                product_index < len(product)
                and product[product_index] == template[template_index]
            ):
                template_index += 1
                product_index += 1
                continue
            template_index += 1
            continue
        template_line = (
            template[template_index] if template_index < len(template) else "<end>"
        )
        product_line = (
            product[product_index] if product_index < len(product) else "<end>"
        )
        if template_line != product_line:
            return (
                f"outside marked lines, template {template_line!r} "
                f"product {product_line!r}"
            )
        template_index += 1
        product_index += 1
    return None


def compare_template(filename: str, template: str, product: str) -> list[str]:
    """Findings when product differs from template outside marked lines."""
    try:
        expected, expected_blocks = _prepare(template)
        actual, actual_blocks = _prepare(product)
    except _TemplateSyntax as exc:
        return [f".github/workflows/{filename}: {exc}"]
    notes: list[str] = []
    diff = _skeleton_diff(expected, actual)
    if diff:
        notes.append(f".github/workflows/{filename}: {diff}")
    for name in sorted(set(actual_blocks) - set(expected_blocks)):
        notes.append(
            f".github/workflows/{filename}: unknown # template:optional {name}"
        )
    for name, body in expected_blocks.items():
        if name not in actual_blocks:
            continue
        block_diff = _skeleton_diff(body, actual_blocks[name])
        if block_diff:
            notes.append(f".github/workflows/{filename} optional {name}: {block_diff}")
    return notes


def _marked_if_present(template_text: str) -> bool:
    """A template may start with the if-present marker."""
    lines = template_text.splitlines()
    return bool(lines) and lines[0].strip() == "# template:if-present"


def _without_if_present(template_text: str) -> str:
    """Drop the leading if-present marker before comparing a present file."""
    lines = template_text.splitlines()
    body = "\n".join(lines[1:])
    if template_text.endswith("\n"):
        body += "\n"
    return body


def template_directory() -> Path:
    override = os.environ.get("CONFORMANCE_TEMPLATE_DIR", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "templates" / "workflows"


def template_findings(root: Path, template_dir: Path | None = None) -> list[str]:
    """Compare product workflows with the templates that exist for them."""
    directory = template_directory() if template_dir is None else template_dir
    if not directory.is_dir():
        return [f"workflow templates are missing at {directory}"]
    workflow_dir = root / ".github" / "workflows"
    notes: list[str] = []
    for template in sorted(directory.glob("*.yml")):
        template_text = template.read_text(encoding="utf-8")
        product = workflow_dir / template.name
        if not product.is_file():
            if _marked_if_present(template_text):
                continue
            notes.append(
                f".github/workflows/{template.name}: missing the shared workflow"
            )
            continue
        if _marked_if_present(template_text):
            template_text = _without_if_present(template_text)
        notes.extend(
            compare_template(
                template.name,
                template_text,
                product.read_text(encoding="utf-8"),
            )
        )
    return notes


def advisory_findings(root: Path, profile: str = "product") -> list[str]:
    """Alignment findings. The producer profile does not run them."""
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
                    errors.append(
                        f"{rel}:{line_number}: runner {label} is not ubuntu-26.04 or macos-26"
                    )
            uses = _uses(line)
            if uses is None or uses.startswith("./"):
                continue
            ref = uses.rsplit("@", 1)[-1] if "@" in uses else ""
            if not SHA.fullmatch(ref):
                errors.append(
                    f"{rel}:{line_number}: {uses} is not pinned by commit SHA"
                )
                continue
            if uses.startswith("lx-software-ltd/actions/"):
                pins.append(ref)
                if re.search(r"#\s*main\s+\d{4}-\d{2}-\d{2}\b", line) is None:
                    errors.append(
                        f"{rel}:{line_number}: {uses} needs a '# main YYYY-MM-DD' comment"
                    )
        for line_number, image in _images(text):
            if not DIGEST.search(image):
                errors.append(
                    f"{rel}:{line_number}: image {image} is not pinned by digest"
                )
        if path.name in PATH_FILTERED and _pull_request_has_path_filter(text):
            errors.append(f"{rel}: pull_request has a path filter")
    for filename, job in GATED.items():
        path = workflow_dir / filename
        if not path.is_file():
            errors.append(f".github/workflows/{filename}: missing the {job} gate")
            continue
        errors.extend(
            _gate_findings(
                f".github/workflows/{filename}",
                job,
                _jobs(path.read_text(encoding="utf-8")),
            )
        )
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
                errors.append(
                    ".github/workflows/semgrep.yml: missing the semgrep/ci job"
                )
    unique = sorted(set(pins))
    if len(unique) > 1:
        errors.append(
            "more than one lx-software-ltd/actions commit: " + ", ".join(unique)
        )
    pre_commit = root / ".pre-commit-config.yaml"
    if pre_commit.is_file():
        found, revs = _pre_commit_actions_revs(pre_commit.read_text(encoding="utf-8"))
        if found:
            for rev in revs:
                if rev == "":
                    errors.append(
                        ".pre-commit-config.yaml names actions but has no rev"
                    )
                    continue
                if not SHA.fullmatch(rev):
                    errors.append(
                        f".pre-commit-config.yaml rev {rev} is not a commit SHA"
                    )
                elif unique and rev not in unique:
                    errors.append(
                        f".pre-commit-config.yaml rev {rev} is not the actions commit {unique[0]}"
                    )
    return errors


def main() -> int:
    mode = os.environ.get("CONFORMANCE_MODE", "enforce")
    profile = os.environ.get("CONFORMANCE_PROFILE", "product")
    alignment = os.environ.get("CONFORMANCE_ALIGNMENT", "enforce").strip().lower()
    templates_mode = os.environ.get("CONFORMANCE_TEMPLATES", "warn").strip().lower()
    if mode not in {"warn", "enforce"}:
        print("workflow-conformance: mode must be warn or enforce", file=sys.stderr)
        return 1
    if profile not in {"product", "producer"}:
        print(
            "workflow-conformance: profile must be product or producer", file=sys.stderr
        )
        return 1
    if alignment not in {"warn", "enforce"}:
        print(
            "workflow-conformance: alignment must be warn or enforce", file=sys.stderr
        )
        return 1
    if templates_mode not in {"off", "warn", "enforce"}:
        print(
            "workflow-conformance: templates must be off, warn, or enforce",
            file=sys.stderr,
        )
        return 1
    root_text = os.environ.get("CONFORMANCE_ROOT", "").strip()
    root = Path(root_text).resolve() if root_text else Path.cwd().resolve()
    found = findings(root, profile)
    aligned = advisory_findings(root, profile)
    advised = aligned if alignment == "warn" else []
    if alignment == "enforce":
        found.extend(aligned)
    templated: list[str] = []
    if profile == "product" and templates_mode != "off":
        templated = template_findings(root)
    if templates_mode == "enforce":
        found.extend(templated)
        templated = []
    for item in advised:
        print(f"::warning::{item}", file=sys.stderr)
    for item in templated:
        print(f"::warning::{item}", file=sys.stderr)
    if not found and not advised and not templated:
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
    if templated:
        print(
            f"Workflow conformance found {len(templated)} template advisory issue(s).",
            file=sys.stderr,
        )
    if mode == "warn" or not found:
        if mode == "warn" and found:
            print("Workflow conformance is in warn mode.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
