#!/usr/bin/env python3
"""Check OpenAPI files against the shared API contract.

The payload uses the standard library. It reads block-style YAML only: the
``servers`` URLs and the keys directly under ``paths``. Flow-style YAML fails
with a message that says this reader cannot follow it.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

CONTRACT_FILES = ("public.yaml", "admin.yaml", "partner.yaml", "webhooks.yaml")
_PREFIX = {
    "public.yaml": ("/v1/public/",),
    "partner.yaml": ("/v1/partner/",),
    "webhooks.yaml": ("/v1/webhooks/",),
}
_VERSION = re.compile(r"^v[0-9]+$")
_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
_PARAM = re.compile(r"\{([^{}]*)\}")


class FlowError(Exception):
    """The line is YAML this reader cannot follow."""

    def __init__(self, line: int) -> None:
        self.line = line
        super().__init__(f"line {line}: this reader cannot follow flow-style YAML")


def _comment_stripped(stripped: str) -> str:
    if " #" in stripped:
        return stripped.split(" #", 1)[0].rstrip()
    return stripped


def _open_block(stripped: str, key: str, line: int) -> bool:
    prefix = f"{key}:"
    if stripped == prefix:
        return True
    if stripped.startswith(prefix):
        raise FlowError(line)
    return False


def _server_url(stripped: str, line: int) -> str | None:
    if "{" in stripped or "[" in stripped:
        raise FlowError(line)
    match = re.match(r"^(?:-\s+)?url:\s*(\S+)\s*$", stripped)
    if match is None:
        return None
    value = match.group(1)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value


def _path_key(stripped: str, line: int) -> str:
    text = _comment_stripped(stripped)
    if text.startswith('"'):
        match = re.match(r'^"(.*)"\s*:\s*$', text)
        if match is None or '"' in match.group(1):
            raise FlowError(line)
        path = match.group(1)
    else:
        if "[" in text or (text.count("{") != text.count("}")):
            raise FlowError(line)
        if not text.startswith("/") or not text.endswith(":"):
            raise FlowError(line)
        path = text[:-1].rstrip()
    if not path.startswith("/") or " " in path:
        raise FlowError(line)
    return path


def read_openapi(text: str) -> tuple[list[str], list[str]]:
    """Return the server URLs and the path keys in ``text``."""
    servers: list[str] = []
    paths: list[str] = []
    mode: str | None = None
    block_indent = -1
    path_indent: int | None = None
    for number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise FlowError(number)
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if mode is not None and indent <= block_indent:
            mode = None
            path_indent = None
        if mode is None:
            if _open_block(stripped, "servers", number):
                mode = "servers"
                block_indent = indent
            elif _open_block(stripped, "paths", number):
                mode = "paths"
                block_indent = indent
                path_indent = None
            continue
        if mode == "servers":
            url = _server_url(stripped, number)
            if url is not None:
                servers.append(url)
            continue
        if path_indent is not None and indent > path_indent:
            continue
        if path_indent is None:
            path_indent = indent
        if indent != path_indent:
            raise FlowError(number)
        paths.append(_path_key(stripped, number))
    return servers, paths


def _segment_findings(path: str) -> list[str]:
    findings: list[str] = []
    versions = 0
    for segment in [part for part in path.split("/") if part]:
        if segment.startswith("{") and segment.endswith("}") and segment.count("{") == 1:
            name = segment[1:-1]
            if _SNAKE.fullmatch(name) is None:
                findings.append(f"{path}: path parameter {segment} is not snake_case")
            continue
        if _PARAM.search(segment):
            findings.append(f"{path}: path parameter is not snake_case")
            continue
        if any(character.isupper() for character in segment):
            findings.append(f"{path}: path segment {segment} has an upper-case letter")
        if "_" in segment:
            findings.append(f"{path}: path segment {segment} has an underscore")
        if "." in segment:
            findings.append(f"{path}: path segment {segment} has a dot")
        if _VERSION.fullmatch(segment):
            versions += 1
            if segment != "v1" or versions > 1:
                findings.append(f"{path}: path segment {segment} is a second version")
    return findings


def _prefix_finding(
    filename: str,
    path: str,
    admin_prefixes: tuple[str, ...],
    legacy: set[str],
) -> str | None:
    if path in legacy:
        return None
    if filename == "admin.yaml":
        if path == "/health" or any(path.startswith(prefix) for prefix in admin_prefixes):
            return None
        return f"admin.yaml: {path} does not start with an admin prefix"
    prefixes = _PREFIX[filename]
    if any(path.startswith(prefix) for prefix in prefixes):
        return None
    return f"{filename}: {path} does not start with {prefixes[0]}"


def _legacy_paths(path: Path | None) -> tuple[set[str], list[str]]:
    if path is None:
        return set(), []
    if not path.is_file():
        return set(), [f"{path}: legacy paths file is missing"]
    found: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        found.add(line)
    return found, []


def check(
    directory: Path,
    *,
    origin: str,
    admin_prefixes: tuple[str, ...],
    legacy_file: Path | None,
) -> list[str]:
    """Return one finding per broken rule. An empty list passes."""
    findings: list[str] = []
    if not origin:
        findings.append("origin is empty")
    if not directory.is_dir():
        findings.append(f"{directory}: directory is missing")
        return findings
    legacy, legacy_findings = _legacy_paths(legacy_file)
    findings.extend(legacy_findings)
    files = sorted(item for item in directory.iterdir() if item.is_file())
    contract = [item for item in files if item.name in CONTRACT_FILES]
    if not contract:
        findings.append(f"{directory}: directory has no OpenAPI contract file")
    for item in files:
        if item.name not in CONTRACT_FILES:
            findings.append(
                f"{item.name}: file is not public.yaml, admin.yaml, "
                "partner.yaml, or webhooks.yaml"
            )
    seen: dict[str, list[str]] = {}
    for item in contract:
        try:
            servers, paths = read_openapi(item.read_text(encoding="utf-8"))
        except FlowError as exc:
            findings.append(f"{item.name}: {exc}")
            continue
        if not servers:
            findings.append(f"{item.name}: has no servers URL")
        for url in servers:
            if url != origin:
                findings.append(f"{item.name}: servers URL {url} is not {origin}")
        for path in paths:
            seen.setdefault(path, []).append(item.name)
            if path in legacy:
                continue
            prefix = _prefix_finding(item.name, path, admin_prefixes, legacy)
            if prefix is not None:
                findings.append(prefix)
            findings.extend(
                f"{item.name}: {item_finding}" for item_finding in _segment_findings(path)
            )
    for path, names in seen.items():
        if len(names) > 1:
            joined = ", ".join(names)
            findings.append(f"{path}: path is listed in more than one file ({joined})")
    return findings


def _workspace_path(value: str, root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def main() -> int:
    root = Path(os.environ.get("API_CONTRACT_ROOT") or os.getcwd())
    origin = os.environ.get("API_CONTRACT_ORIGIN", "").strip()
    directory_value = os.environ.get("API_CONTRACT_DIRECTORY", "").strip() or "docs/api"
    prefix_value = os.environ.get("API_CONTRACT_ADMIN_PREFIXES", "").strip()
    if not prefix_value:
        prefix_value = "/v1/admin/,/v1/user/"
    admin_prefixes = tuple(
        part.strip() for part in prefix_value.split(",") if part.strip()
    )
    legacy_value = os.environ.get("API_CONTRACT_LEGACY_PATHS", "").strip()
    legacy_file = _workspace_path(legacy_value, root) if legacy_value else None
    findings = check(
        _workspace_path(directory_value, root),
        origin=origin,
        admin_prefixes=admin_prefixes,
        legacy_file=legacy_file,
    )
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
