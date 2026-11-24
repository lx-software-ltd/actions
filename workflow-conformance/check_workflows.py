#!/usr/bin/env python3
"""Check a repository against the CI contract.

``mode`` is ``enforce`` or ``warn``. Enforce exits 1 when there is a finding.
Warn prints the findings and exits 0. The default is enforce.

``profile`` is ``producer`` or ``product``. The producer is this repository.
Product repositories also need the target security jobs and ``semgrep/ci``.

``alignment`` defaults to ``enforce``. ``templates`` defaults to ``enforce`` and
compares product workflows with ``templates/workflows``. The producer skips both.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
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
_IF_PRESENT = re.compile(r"^# template:if-present(?:\s+(!)?([a-z0-9-]+))?$")
_PRODUCT_NAME = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:evolvesprouts|findingalpha|lxsoftware|lx-software|siutindei)"
    r"(?![A-Za-z0-9])"
)
_VALUE_RUN = re.compile(r"^run:")
_VALUE_ID = re.compile(r"^id:")
_SINGLE_QUOTED = re.compile(r"^(?:-\s+|[^:#\n]+:\s+)'")


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


def _extract_optional(
    lines: list[str],
) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Replace each optional block with its opening marker.

    The same id may occur more than once in a file. Each occurrence is its
    own block.
    """
    skeleton: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
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
        blocks.append((name, inner))
    return skeleton, blocks


def _prepare(text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    normalized = _normalize_pins(text.replace("\r\n", "\n"))
    return _flatten_optional(normalized.splitlines())


def _flatten_optional(
    lines: list[str],
) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Optional blocks may nest. A nested block can be omitted on its own."""
    skeleton, blocks = _extract_optional(lines)
    flat: list[tuple[str, list[str]]] = []
    for name, body in blocks:
        body_skeleton, nested = _flatten_optional(body)
        flat.extend(nested)
        flat.append((name, _strip_sets(body_skeleton)))
    return _strip_sets(skeleton), flat


_SET_STEP = re.compile(r"^-\s+(?:name|uses|run|id):")
_SET_KEY = re.compile(r"^(?:continue-on-error|type|options|needs):")


def _set_block_violations(text: str) -> list[str]:
    """A marked block holds values, not a new step or a way to skip one."""
    lines = text.replace("\r\n", "\n").splitlines()
    notes: list[str] = []
    index = 0
    while index < len(lines):
        if not _is_set(lines[index]):
            index += 1
            continue
        block, index = _consume_balanced(lines, index)
        for line in block[1:-1]:
            if _is_set(line) or _is_end(line) or _optional_name(line):
                continue
            stripped = line.strip()
            if _value_line_forbidden(stripped):
                notes.append(stripped)
    return notes


def _value_line_forbidden(stripped: str) -> bool:
    """A value block holds values, not commands, ids, comments, or single quotes."""
    if not stripped:
        return False
    if _SET_STEP.match(stripped) or _SET_KEY.match(stripped):
        return True
    if _VALUE_RUN.match(stripped) or _VALUE_ID.match(stripped):
        return True
    if stripped.startswith("#"):
        return True
    return _SINGLE_QUOTED.match(stripped) is not None


def _value_block_command(stripped: str) -> bool:
    """A drift count: run, id, or a comment. Single quotes are a separate rule."""
    if not stripped or stripped.startswith("# template:"):
        return False
    if _SET_STEP.match(stripped) and (
        stripped.startswith("- run:") or stripped.startswith("- id:")
    ):
        return True
    if _VALUE_RUN.match(stripped) or _VALUE_ID.match(stripped):
        return True
    return stripped.startswith("#")


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


def _aligned_value_bodies(template: str, product: str) -> list[tuple[str, str]]:
    """Pair value-block interiors, skipping optionals the product omits."""
    template_lines = template.replace("\r\n", "\n").splitlines()
    product_lines = product.replace("\r\n", "\n").splitlines()
    pairs: list[tuple[str, str]] = []
    template_index = 0
    product_index = 0
    while template_index < len(template_lines) and product_index < len(product_lines):
        if _optional_name(template_lines[template_index]):
            if (
                template_lines[template_index].strip()
                == product_lines[product_index].strip()
            ):
                template_index += 1
                product_index += 1
                continue
            _block, template_index = _consume_balanced(template_lines, template_index)
            continue
        if _is_set(template_lines[template_index]) and _is_set(
            product_lines[product_index]
        ):
            template_block, template_index = _consume_balanced(
                template_lines, template_index
            )
            product_block, product_index = _consume_balanced(
                product_lines, product_index
            )
            pairs.append(
                (
                    "\n".join(template_block[1:-1]).strip(),
                    "\n".join(product_block[1:-1]).strip(),
                )
            )
            continue
        template_index += 1
        product_index += 1
    return pairs


def _anchored_value_bodies(text: str) -> list[tuple[tuple[str, ...], int, str]]:
    """Value blocks keyed by the optional blocks around them, not by position."""
    lines = text.replace("\r\n", "\n").splitlines()
    found: list[tuple[tuple[str, ...], int, str]] = []

    def walk(start: int, end: int, stack: tuple[str, ...]) -> None:
        index = start
        local = 0
        while index < end:
            if _optional_name(lines[index]):
                block, index = _consume_balanced(lines, index)
                name = _optional_name(block[0]) or ""
                inner_end = index - 1
                inner_start = inner_end - (len(block) - 2)
                walk(inner_start, inner_end, stack + (name,))
                continue
            if _is_set(lines[index]):
                block, index = _consume_balanced(lines, index)
                found.append((stack, local, "\n".join(block[1:-1]).strip()))
                local += 1
                continue
            index += 1

    walk(0, len(lines), ())
    return found


def compare_template(filename: str, template: str, product: str) -> list[str]:
    """Findings when product differs from template outside marked lines."""
    try:
        expected, expected_blocks = _prepare(template)
        actual, actual_blocks = _prepare(product)
    except _TemplateSyntax as exc:
        return [f".github/workflows/{filename}: {exc}"]
    notes: list[str] = []
    for line in _set_block_violations(template) + _set_block_violations(product):
        notes.append(
            f".github/workflows/{filename}: # template:set cannot contain {line!r}"
        )
    diff = _skeleton_diff(expected, actual)
    if diff:
        notes.append(f".github/workflows/{filename}: {diff}")
    notes.extend(_optional_body_diffs(filename, expected_blocks, actual_blocks))
    for template_body, product_body in _aligned_value_bodies(template, product):
        if template_body and template_body == product_body:
            sample = template_body.splitlines()[0].strip()
            notes.append(
                f".github/workflows/{filename}: value block copies the template sample {sample!r}"
            )
    return notes


def _optional_body_diffs(
    filename: str,
    expected: list[tuple[str, list[str]]],
    actual: list[tuple[str, list[str]]],
) -> list[str]:
    """Compare optional bodies in order. The same id may occur more than once."""
    expected_groups: dict[str, list[list[str]]] = {}
    actual_groups: dict[str, list[list[str]]] = {}
    for name, body in expected:
        expected_groups.setdefault(name, []).append(body)
    for name, body in actual:
        actual_groups.setdefault(name, []).append(body)
    notes: list[str] = []
    for name in sorted(set(actual_groups) - set(expected_groups)):
        notes.append(
            f".github/workflows/{filename}: unknown # template:optional {name}"
        )
    for name in sorted(expected_groups):
        got = actual_groups.get(name, [])
        wanted = expected_groups[name]
        extra = len(got) - len(wanted)
        if extra > 0:
            notes.append(
                f".github/workflows/{filename}: unknown # template:optional {name}"
            )
        for index, actual_body in enumerate(got[: len(wanted)]):
            block_diff = _skeleton_diff(wanted[index], actual_body)
            if not block_diff:
                continue
            label = name if len(wanted) == 1 else f"{name} #{index + 1}"
            notes.append(f".github/workflows/{filename} optional {label}: {block_diff}")
    return notes


def _if_present(template_text: str) -> tuple[bool, str | None, bool]:
    """A template may start with an if-present marker.

    The return is (marked, capability, negated). A bare marker has no
    capability and only allows the file to be absent.
    """
    lines = template_text.splitlines()
    if not lines:
        return False, None, False
    match = _IF_PRESENT.match(lines[0].strip())
    if match is None:
        return False, None, False
    return True, match.group(2), match.group(1) == "!"


def _marked_if_present(template_text: str) -> bool:
    """A template may start with the if-present marker."""
    marked, _, _ = _if_present(template_text)
    return marked


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


def _repository_name(root: Path) -> str:
    override = os.environ.get("CONFORMANCE_REPOSITORY", "").strip()
    if override:
        return override.split("/")[-1]
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return root.name
    if result.returncode != 0:
        return root.name
    name = result.stdout.strip().rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    return name or root.name


def _capabilities_path(template_dir: Path) -> Path | None:
    override = os.environ.get("CONFORMANCE_CAPABILITIES", "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    candidate = template_dir.parent / "capabilities.json"
    if template_dir.name == "workflows" and candidate.is_file():
        return candidate
    return None


def _load_capabilities(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def _probe_matches(root: Path, pattern: str) -> bool:
    if any(char in pattern for char in "*?["):
        return any(root.glob(pattern))
    return (root / pattern).exists()


def _optional_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in text.splitlines():
        name = _optional_name(line)
        if name is None:
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts


def _unmarked_lines(text: str) -> list[str]:
    """Lines outside value blocks. Marker lines themselves are not text."""
    lines = text.replace("\r\n", "\n").splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        if _is_set(lines[index]):
            _, index = _consume_balanced(lines, index)
            continue
        stripped = lines[index].strip()
        if _optional_name(lines[index]) or _is_end(lines[index]) or _IF_PRESENT.match(stripped):
            index += 1
            continue
        kept.append(lines[index])
        index += 1
    return kept


def _product_name_findings(template_dir: Path) -> list[str]:
    notes: list[str] = []
    for template in sorted(template_dir.glob("*.yml")):
        try:
            lines = _unmarked_lines(template.read_text(encoding="utf-8"))
        except _TemplateSyntax as exc:
            notes.append(f"templates/workflows/{template.name}: {exc}")
            continue
        for line in lines:
            # lx-software-ltd is the actions org, not a product name.
            if _PRODUCT_NAME.search(line.replace("lx-software-ltd", "ORG")) is None:
                continue
            notes.append(
                f"templates/workflows/{template.name}: product name in unmarked text: {line.strip()}"
            )
    return notes


def _capability_block_findings(
    root: Path,
    template_dir: Path,
    capabilities: dict[str, str],
) -> list[str]:
    if not capabilities:
        return []
    notes: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    for template in sorted(template_dir.glob("*.yml")):
        template_text = template.read_text(encoding="utf-8")
        expected = _optional_counts(template_text)
        for name in sorted(expected):
            if name not in capabilities:
                notes.append(
                    f"templates/workflows/{template.name}: "
                    f"# template:optional {name} is not a capability"
                )
        product = workflow_dir / template.name
        if not product.is_file():
            continue
        actual = _optional_counts(product.read_text(encoding="utf-8"))
        for name in sorted(set(actual) - set(expected)):
            if name not in capabilities:
                notes.append(
                    f".github/workflows/{template.name}: "
                    f"# template:optional {name} is not a capability"
                )
        names = set(expected) | set(actual)
        for name in sorted(names):
            if name not in capabilities:
                continue
            present = _probe_matches(root, capabilities[name])
            have = actual.get(name, 0)
            want = expected.get(name, 0)
            if present and have != want:
                notes.append(
                    f".github/workflows/{template.name}: capability {name} "
                    f"probe {capabilities[name]} is present and the block count is {have}"
                )
            if not present and have != 0:
                notes.append(
                    f".github/workflows/{template.name}: capability {name} "
                    f"block is present and probe {capabilities[name]} is absent"
                )
    return notes


def _file_presence_finding(
    root: Path,
    filename: str,
    capability: str,
    negated: bool,
    present: bool,
    capabilities: dict[str, str],
) -> str | None:
    if capability not in capabilities:
        return (
            f"templates/workflows/{filename}: "
            f"# template:if-present names unknown capability {capability}"
        )
    matched = _probe_matches(root, capabilities[capability])
    should_exist = (not matched) if negated else matched
    if should_exist and not present:
        return (
            f".github/workflows/{filename}: capability {capability} "
            "requires this workflow"
        )
    if not should_exist and present:
        return (
            f".github/workflows/{filename}: capability {capability} "
            "excludes this workflow"
        )
    return None


def _untemplated_path(template_dir: Path) -> Path | None:
    override = os.environ.get("CONFORMANCE_UNTEMPLATED", "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    candidate = template_dir.parent / "untemplated-workflows.txt"
    if template_dir.name == "workflows" and candidate.is_file():
        return candidate
    return None


def _untemplated_allow(path: Path) -> dict[str, set[str]]:
    allowed: dict[str, set[str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        repo, _, filename = line.partition(" ")
        if not filename:
            continue
        allowed.setdefault(repo, set()).add(filename.strip())
    return allowed


def _untemplated_findings(root: Path, template_dir: Path, allow_path: Path | None) -> list[str]:
    if allow_path is None:
        return []
    allowed = _untemplated_allow(allow_path)
    repo = _repository_name(root)
    known = {path.name for path in template_dir.glob("*.yml")}
    notes: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return notes
    listed = allowed.get(repo, set())
    for path in sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml")):
        if path.name in known:
            continue
        if path.name in listed:
            continue
        notes.append(
            f".github/workflows/{path.name}: no template and not in "
            "templates/untemplated-workflows.txt"
        )
    return notes


def _literal_prefix(entry: str) -> str:
    cut = len(entry)
    for index, char in enumerate(entry):
        if char in "*?[":
            cut = index
            break
    return entry[:cut].rstrip("/")


def _on_path_entries(text: str) -> list[str]:
    """Literal items under on.*.paths. paths-ignore is a separate key."""
    entries: list[str] = []
    in_on = False
    in_paths = False
    paths_indent = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if line.startswith("on:"):
            in_on = True
            in_paths = False
            continue
        if in_on and line and not line[0].isspace():
            in_on = False
            in_paths = False
        if not in_on:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if in_paths:
            if stripped.startswith("- ") and indent > paths_indent:
                value = stripped[2:].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]
                entries.append(value)
                continue
            in_paths = False
        if stripped == "paths:":
            in_paths = True
            paths_indent = indent
    return entries


def _path_filter_findings(root: Path, rel: str, text: str) -> list[str]:
    notes: list[str] = []
    for entry in _on_path_entries(text):
        prefix = _literal_prefix(entry)
        if not prefix:
            continue
        if (root / prefix).exists():
            continue
        notes.append(f"{rel}: path filter {entry} does not exist ({prefix})")
    return notes


def template_findings(root: Path, template_dir: Path | None = None) -> list[str]:
    """Compare product workflows with the templates that exist for them."""
    directory = template_directory() if template_dir is None else template_dir
    if not directory.is_dir():
        return [f"workflow templates are missing at {directory}"]
    workflow_dir = root / ".github" / "workflows"
    notes: list[str] = []
    capabilities = _load_capabilities(_capabilities_path(directory))
    notes.extend(_product_name_findings(directory))
    for template in sorted(directory.glob("*.yml")):
        template_text = template.read_text(encoding="utf-8")
        marked, capability, negated = _if_present(template_text)
        product = workflow_dir / template.name
        if marked and capability and capabilities:
            finding = _file_presence_finding(
                root,
                template.name,
                capability,
                negated,
                product.is_file(),
                capabilities,
            )
            if finding:
                notes.append(finding)
        if not product.is_file():
            if marked and not (capability and capabilities):
                continue
            if marked and capability and capabilities:
                continue
            notes.append(
                f".github/workflows/{template.name}: missing the shared workflow"
            )
            continue
        if (
            marked
            and capability
            and capabilities
            and capability in capabilities
        ):
            matched = _probe_matches(root, capabilities[capability])
            should_exist = (not matched) if negated else matched
            if not should_exist:
                continue
        compared = _without_if_present(template_text) if marked else template_text
        notes.extend(
            compare_template(
                template.name,
                compared,
                product.read_text(encoding="utf-8"),
            )
        )
    notes.extend(_capability_block_findings(root, directory, capabilities))
    notes.extend(
        _untemplated_findings(root, directory, _untemplated_path(directory))
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
        errors.extend(_path_filter_findings(root, rel, text))
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
    templates_mode = os.environ.get("CONFORMANCE_TEMPLATES", "enforce").strip().lower()
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
