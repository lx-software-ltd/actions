#!/usr/bin/env python3
"""Check OpenAPI files against the shared API contract.

The payload uses the standard library. It reads block-style YAML only: the
``servers`` URLs and the keys directly under the top-level ``paths`` key.
A schema property named ``paths`` or ``servers`` is not that key. Flow-style
YAML fails with a message that says this reader cannot follow it. A key
under ``paths`` that does not start with ``/``, and an anchor on ``paths``,
are reported on their own.
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
_PROXY_ALLOWED = {"partner.yaml", "admin.yaml"}
_VERSION = re.compile(r"^v[0-9]+$")
_LITERAL = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PARAM_NAME = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_ADMIN_PREFIX = re.compile(r"^/v1/[a-z0-9-]+/$")
_ORIGIN = re.compile(r"^https://[a-z0-9.-]+$")
_QUOTED_PATHS = re.compile(r"""^(['"])paths\1\s*:\s*$""")
_BLOCK_SCALAR = re.compile(r":\s*[|>](?:[+-]\d*|\d*[+-]?)?\s*$")
_PATHS_ANCHOR = re.compile(r"paths:\s*&")
_PATHS_ANCHOR_BLOCK = re.compile(r"paths:\s*&\S+")
_GREEDY = "{proxy+}"
_METHODS = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)


class FlowError(Exception):
    """The line is YAML this reader cannot follow."""

    def __init__(self, line: int) -> None:
        self.line = line
        super().__init__(f"line {line}: this reader cannot follow flow-style YAML")


class NotAPathKey(Exception):
    """A mapping key directly under paths does not start with /."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(key)


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


def _commented_url(stripped: str) -> bool:
    if " #" not in stripped:
        return False
    return re.match(
        r"^(?:-\s+)?url:\s*\S+\s*$",
        _comment_stripped(stripped),
    ) is not None


def _is_servers_key(stripped: str) -> bool:
    bare = _comment_stripped(stripped)
    if bare == "servers:":
        return True
    if not bare.startswith("servers:"):
        return False
    return bare[len("servers:") :].startswith((" ", "[", "{"))


def _is_method_key(stripped: str) -> bool:
    bare = _comment_stripped(stripped)
    if not bare.endswith(":"):
        return False
    return bare[:-1].strip() in _METHODS


def _path_key(stripped: str, line: int) -> str:
    text = _comment_stripped(stripped)
    if text.startswith('"'):
        match = re.match(r'^"(?P<key>[^"]*)"\s*:(?P<rest>.*)$', text)
        if match is None:
            raise FlowError(line)
        key = match.group("key")
        rest = match.group("rest").strip()
        if not key or " " in key:
            raise FlowError(line)
        if not key.startswith("/"):
            raise NotAPathKey(key)
        if rest:
            raise FlowError(line)
        return key
    if "[" in text or (text.count("{") != text.count("}")):
        raise FlowError(line)
    if not text.endswith(":"):
        if not text.startswith("/") and ":" in text:
            key = text.split(":", 1)[0].rstrip()
            if key and not any(character in key for character in "[]{}"):
                raise NotAPathKey(key)
        raise FlowError(line)
    path = text[:-1].rstrip()
    if " " in path or not path:
        raise FlowError(line)
    if not path.startswith("/"):
        if any(character in path for character in "[]{}"):
            raise FlowError(line)
        raise NotAPathKey(path)
    return path


def read_openapi(text: str) -> tuple[list[str], list[str], list[str]]:
    """Return the server URLs, the path keys, and reader findings."""
    servers: list[str] = []
    paths: list[str] = []
    findings: list[str] = []
    mode: str | None = None
    block_indent = -1
    path_indent: int | None = None
    item_indent: int | None = None
    operation_indent: int | None = None
    inside_operation = False
    scalar_indent: int | None = None
    saw_paths = False
    saw_quoted_paths = False
    saw_paths_comment = False
    for number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise FlowError(number)
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if scalar_indent is not None and indent <= scalar_indent:
            scalar_indent = None
        if mode is not None and indent <= block_indent:
            mode = None
            path_indent = None
            item_indent = None
            operation_indent = None
            inside_operation = False
            scalar_indent = None
        if scalar_indent is not None and indent > scalar_indent:
            continue
        if mode is None:
            if indent != 0:
                continue
            bare = _comment_stripped(stripped)
            if _QUOTED_PATHS.fullmatch(bare):
                saw_quoted_paths = True
                findings.append(f"line {number}: quoted paths key is not opened")
                continue
            if bare == "paths:" and stripped != "paths:":
                saw_paths_comment = True
                findings.append(f"line {number}: comment after paths: is not read")
                continue
            if bare == "servers:" and stripped != "servers:" and " #" in stripped:
                mode = "servers"
                block_indent = indent
                continue
            if _open_block(stripped, "servers", number):
                mode = "servers"
                block_indent = indent
                continue
            if _PATHS_ANCHOR.match(bare):
                findings.append(f"line {number}: anchor is not accepted")
                saw_paths = True
                if _PATHS_ANCHOR_BLOCK.fullmatch(bare):
                    mode = "paths"
                    block_indent = indent
                    path_indent = None
                    item_indent = None
                    operation_indent = None
                    inside_operation = False
                continue
            if _open_block(stripped, "paths", number):
                mode = "paths"
                block_indent = indent
                path_indent = None
                item_indent = None
                operation_indent = None
                inside_operation = False
                saw_paths = True
            continue
        if mode == "servers":
            if _commented_url(stripped):
                findings.append(
                    f"line {number}: comment after a servers URL is not read"
                )
                continue
            url = _server_url(stripped, number)
            if url is not None:
                servers.append(url)
            continue
        if path_indent is not None and indent > path_indent:
            if item_indent is None:
                item_indent = indent
            servers_here = False
            if indent == item_indent:
                inside_operation = False
                operation_indent = None
                servers_here = _is_servers_key(stripped)
                if _is_method_key(stripped):
                    inside_operation = True
            elif inside_operation and indent > item_indent:
                if operation_indent is None:
                    operation_indent = indent
                servers_here = indent == operation_indent and _is_servers_key(stripped)
            if servers_here:
                findings.append(
                    f"line {number}: servers key under a path is not the document servers"
                )
            if _BLOCK_SCALAR.search(stripped):
                scalar_indent = indent
            continue
        if path_indent is None:
            path_indent = indent
        if indent != path_indent:
            raise FlowError(number)
        item_indent = None
        operation_indent = None
        inside_operation = False
        bare = _comment_stripped(stripped)
        if bare.startswith("'"):
            findings.append(f"line {number}: single-quoted path key is not a path")
            continue
        if bare.startswith("x-"):
            findings.append(f"line {number}: x- key under paths is not a path")
            continue
        try:
            paths.append(_path_key(stripped, number))
        except NotAPathKey as exc:
            findings.append(f"line {number}: {exc.key} under paths is not a path")
    if not saw_paths and not saw_quoted_paths and not saw_paths_comment:
        findings.append("file has no paths block")
    return servers, paths, findings


def _matches_prefix(path: str, prefix: str) -> bool:
    """True for the audience root and for every path under that prefix."""
    return path == prefix.rstrip("/") or path.startswith(prefix)


def _segment_findings(path: str) -> list[str]:
    findings: list[str] = []
    if not path.startswith("/"):
        findings.append(f"{path}: path does not start with /")
        return findings
    segments = path.split("/")[1:]
    if not segments:
        findings.append(f"{path}: empty path segment")
        return findings
    versions = 0
    last = len(segments) - 1
    for index, segment in enumerate(segments):
        if segment == "":
            findings.append(f"{path}: empty path segment")
            continue
        if segment == _GREEDY:
            if index != last:
                findings.append(f"{path}: {{proxy+}} is not the last segment")
            continue
        if (
            segment.startswith("{")
            and segment.endswith("}")
            and segment.count("{") == 1
        ):
            name = segment[1:-1]
            if _PARAM_NAME.fullmatch(name) is None:
                findings.append(f"{path}: path parameter {segment} is not snake_case")
            continue
        if "{" in segment or "}" in segment:
            findings.append(f"{path}: path parameter is not snake_case")
            continue
        if _LITERAL.fullmatch(segment) is None:
            specific = False
            if any(character.isupper() for character in segment):
                findings.append(
                    f"{path}: path segment {segment} has an upper-case letter"
                )
                specific = True
            if "_" in segment:
                findings.append(f"{path}: path segment {segment} has an underscore")
                specific = True
            if "." in segment:
                findings.append(f"{path}: path segment {segment} has a dot")
                specific = True
            if not specific:
                findings.append(
                    f"{path}: path segment {segment} does not match "
                    "^[a-z0-9]+(-[a-z0-9]+)*$"
                )
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
        if path == "/health" or any(
            _matches_prefix(path, prefix) for prefix in admin_prefixes
        ):
            return None
        return f"admin.yaml: {path} does not start with an admin prefix"
    prefixes = _PREFIX[filename]
    if any(_matches_prefix(path, prefix) for prefix in prefixes):
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


def _duplicate_findings(seen: dict[str, list[str]]) -> list[str]:
    findings: list[str] = []
    for path, names in seen.items():
        unique = list(dict.fromkeys(names))
        for name in unique:
            if names.count(name) > 1:
                findings.append(f"{path}: path is duplicated in {name}")
        if len(unique) > 1:
            joined = ", ".join(unique)
            findings.append(
                f"{path}: path is listed in more than one file ({joined})"
            )
    return findings


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
    elif _ORIGIN.fullmatch(origin) is None:
        findings.append(f"origin {origin} does not match ^https://[a-z0-9.-]+$")
    for prefix in admin_prefixes:
        if _ADMIN_PREFIX.fullmatch(prefix) is None:
            findings.append(
                f"admin prefix {prefix} does not match ^/v1/[a-z0-9-]+/$"
            )
    usable_prefixes = tuple(
        prefix for prefix in admin_prefixes if _ADMIN_PREFIX.fullmatch(prefix)
    )
    if not directory.is_dir():
        findings.append(f"{directory}: directory is missing")
        return findings
    legacy, legacy_findings = _legacy_paths(legacy_file)
    findings.extend(legacy_findings)
    legacy_resolved = (
        legacy_file.resolve()
        if legacy_file is not None and legacy_file.is_file()
        else None
    )
    entries = sorted(directory.iterdir(), key=lambda item: item.name)
    for item in entries:
        if item.is_dir():
            findings.append(f"{item.name}: subdirectory is not a contract file")
    files = [item for item in entries if item.is_file()]
    contract = [item for item in files if item.name in CONTRACT_FILES]
    if not contract:
        findings.append(f"{directory}: directory has no OpenAPI contract file")
    for item in files:
        if item.name in CONTRACT_FILES:
            continue
        if legacy_resolved is not None and item.resolve() == legacy_resolved:
            continue
        findings.append(
            f"{item.name}: file is not public.yaml, admin.yaml, "
            "partner.yaml, or webhooks.yaml"
        )
    seen: dict[str, list[str]] = {}
    parsed_all = True
    for item in contract:
        try:
            servers, paths, reader_findings = read_openapi(
                item.read_text(encoding="utf-8")
            )
        except FlowError as exc:
            findings.append(f"{item.name}: {exc}")
            parsed_all = False
            continue
        for reader_finding in reader_findings:
            findings.append(f"{item.name}: {reader_finding}")
        if not servers and not any(
            "comment after a servers URL" in item_finding
            for item_finding in reader_findings
        ):
            findings.append(f"{item.name}: has no servers URL")
        for url in servers:
            if url != origin:
                findings.append(f"{item.name}: servers URL {url} is not {origin}")
        for path in paths:
            seen.setdefault(path, []).append(item.name)
            if _GREEDY in path.split("/") and item.name not in _PROXY_ALLOWED:
                findings.append(
                    f"{item.name}: {path}: {{proxy+}} is not allowed without an authorizer"
                )
            if path in legacy:
                continue
            prefix_finding = _prefix_finding(
                item.name, path, usable_prefixes, legacy
            )
            if prefix_finding is not None:
                findings.append(prefix_finding)
            findings.extend(
                f"{item.name}: {item_finding}"
                for item_finding in _segment_findings(path)
            )
    findings.extend(_duplicate_findings(seen))
    if contract and parsed_all:
        present = set(seen)
        for legacy_path in sorted(legacy):
            if legacy_path not in present:
                findings.append(
                    f"{legacy_path}: legacy path is not in a contract file"
                )
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
