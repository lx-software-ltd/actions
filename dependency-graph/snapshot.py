#!/usr/bin/env python3
"""Build a dependency snapshot and, when asked, submit it.

Reads pinned Python requirements, npm lockfiles, and pinned GitHub
Actions uses. An unpinned requirement or action fails the run before
any submit. Submit posts one snapshot for this correlator.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CORRELATOR = "lx-dependency-graph"
DETECTOR = "lx-software-dependency-graph"
SKIP_DIRS = {"fixtures", "node_modules", ".git", ".venv", "venv", "Pods"}
PIN = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*==\s*([^;\s]+)")
USES = re.compile(
    r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/([A-Za-z0-9_.-]+))?@([^\s#]+)$"
)


def _purl_version(version: str) -> str:
    return urllib.parse.quote(version, safe="")


def pypi_purl(name: str, version: str) -> str:
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    return (
        f"pkg:pypi/{urllib.parse.quote(normalized, safe='')}@{_purl_version(version)}"
    )


def npm_purl(name: str, version: str) -> str:
    if name.startswith("@") and "/" in name:
        scope, rest = name[1:].split("/", 1)
        encoded = f"%40{urllib.parse.quote(scope, safe='')}/{urllib.parse.quote(rest, safe='')}"
    else:
        encoded = urllib.parse.quote(name, safe="")
    return f"pkg:npm/{encoded}@{_purl_version(version)}"


def actions_purl(owner: str, repo: str, subpath: str | None, ref: str) -> str:
    parts = [urllib.parse.quote(owner, safe=""), urllib.parse.quote(repo, safe="")]
    if subpath:
        parts.append(urllib.parse.quote(subpath, safe=""))
    return f"pkg:githubactions/{'/'.join(parts)}@{_purl_version(ref)}"


def _include(line: str) -> str | None:
    if line.startswith("-r ") or line.startswith("--requirement "):
        return line.split(None, 1)[1]
    if line.startswith("-r="):
        return line[3:]
    if line.startswith("--requirement="):
        return line.split("=", 1)[1]
    return None


def parse_requirements(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Return resolved purl entries and errors for one requirements file."""
    resolved: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    root = path.parent.resolve()
    seen: set[Path] = set()

    def walk(current: Path) -> None:
        resolved_path = current.resolve()
        try:
            resolved_path.relative_to(root)
        except ValueError:
            errors.append(f"include escapes {root}: {current}")
            return
        if resolved_path in seen:
            errors.append(f"circular include: {current}")
            return
        if not current.is_file():
            errors.append(f"missing include: {current}")
            return
        seen.add(resolved_path)
        for raw in current.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            included = _include(line)
            if included is not None:
                walk(current.parent / included)
                continue
            if line.startswith("-"):
                continue
            match = PIN.match(line)
            if match is None:
                errors.append(f"{current}: unpinned requirement {line}")
                continue
            purl = pypi_purl(match.group(1), match.group(2))
            resolved[purl] = {
                "package_url": purl,
                "relationship": "direct",
                "scope": "runtime",
            }

    if not path.is_file():
        return {}, [f"missing requirements file: {path}"]
    walk(path)
    return resolved, errors


def _npm_name(key: str, meta: dict[str, Any]) -> str | None:
    name = meta.get("name")
    if isinstance(name, str) and name:
        return name
    marker = "node_modules/"
    if marker not in key:
        return None
    return key.rsplit(marker, 1)[-1]


def parse_package_lock(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not path.is_file():
        return {}, [f"missing lockfile: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"{path}: {exc.msg}"]
    if not isinstance(payload, dict):
        return {}, [f"{path}: lockfile must be an object"]
    packages = payload.get("packages")
    if not isinstance(packages, dict):
        return {}, [f"{path}: lockfile has no packages map"]
    root = packages.get("") if isinstance(packages.get(""), dict) else {}
    direct: set[str] = set()
    for field in ("dependencies", "devDependencies", "optionalDependencies"):
        names = root.get(field)
        if isinstance(names, dict):
            direct.update(str(name) for name in names)
    resolved: dict[str, dict[str, Any]] = {}
    for key, meta in packages.items():
        if key == "" or not isinstance(meta, dict):
            continue
        version = meta.get("version")
        name = _npm_name(str(key), meta)
        if not isinstance(version, str) or not version or name is None:
            continue
        purl = npm_purl(name, version)
        dev_names = root.get("devDependencies") or {}
        runtime_names = root.get("dependencies") or {}
        if meta.get("dev") is True or (name in dev_names and name not in runtime_names):
            scope = "development"
        else:
            scope = "runtime"
        resolved[purl] = {
            "package_url": purl,
            "relationship": "direct" if name in direct else "indirect",
            "scope": scope,
        }
    return resolved, []


def parse_actions(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not path.is_file():
        return {}, [f"missing workflow: {path}"]
    resolved: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        found = re.search(r"(?:^|\s)uses:\s*(.+)$", stripped)
        if not stripped or stripped.startswith("#") or found is None:
            continue
        value = found.group(1).split("#", 1)[0].strip()
        if value.startswith("./") or value.startswith("docker://"):
            continue
        match = USES.match(value)
        if match is None:
            errors.append(f"{path}: unpinned action {value}")
            continue
        purl = actions_purl(
            match.group(1), match.group(2), match.group(3), match.group(4)
        )
        resolved[purl] = {
            "package_url": purl,
            "relationship": "direct",
            "scope": "runtime",
        }
    return resolved, errors


def _kind(path: Path) -> str | None:
    name = path.name
    if name.startswith("requirements") and name.endswith(".txt"):
        return "pip"
    if name == "package-lock.json":
        return "npm"
    if name in {"action.yml", "action.yaml"} or path.suffix in {".yml", ".yaml"}:
        return "actions"
    return None


def discover(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if _kind(path) is not None and (
            path.name.startswith("requirements")
            or path.name == "package-lock.json"
            or path.name in {"action.yml", "action.yaml"}
            or ".github/workflows" in path.as_posix()
        ):
            found.append(path)
    return sorted(found)


def build_snapshot(
    files: list[Path], sha: str, ref: str, job_id: str
) -> tuple[dict[str, Any], list[str]]:
    manifests: dict[str, Any] = {}
    errors: list[str] = []
    for path in files:
        kind = _kind(path)
        if kind == "pip":
            resolved, found = parse_requirements(path)
        elif kind == "npm":
            resolved, found = parse_package_lock(path)
        elif kind == "actions":
            resolved, found = parse_actions(path)
        else:
            errors.append(f"unsupported manifest: {path}")
            continue
        errors.extend(found)
        if not resolved:
            continue
        location = path.as_posix()
        manifests[location] = {
            "name": path.name,
            "file": {"source_location": location},
            "resolved": resolved,
        }
    snapshot = {
        "version": 0,
        "sha": sha,
        "ref": ref,
        "job": {"correlator": CORRELATOR, "id": job_id},
        "detector": {
            "name": DETECTOR,
            "version": "1",
            "url": "https://github.com/lx-software-ltd/actions",
        },
        "scanned": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifests": manifests,
    }
    return snapshot, errors


def post_snapshot(snapshot: dict[str, Any], repository: str, token: str) -> int:
    url = f"https://api.github.com/repos/{repository}/dependency-graph/snapshots"
    body = json.dumps(snapshot).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": DETECTOR,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        print(f"dependency graph submit failed: {exc.code} {detail}", file=sys.stderr)
        return 1
    print(f"submitted dependency snapshot ({status})")
    return 0 if status in {200, 201} else 1


def _lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _ignored(path: Path, root: Path, ignored: set[str]) -> bool:
    if not ignored:
        return False
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = path.as_posix()
    return relative in ignored


def main() -> int:
    root = Path(
        os.environ.get("DEPENDENCY_GRAPH_ROOT")
        or os.environ.get("GITHUB_WORKSPACE")
        or "."
    )
    listed = _lines(os.environ.get("DEPENDENCY_GRAPH_MANIFESTS", ""))
    ignored = set(_lines(os.environ.get("DEPENDENCY_GRAPH_IGNORE", "")))
    files = [root / line for line in listed] if listed else discover(root)
    files = [path for path in files if not _ignored(path, root, ignored)]
    sha = os.environ.get("GITHUB_SHA", "")
    ref = os.environ.get("GITHUB_REF", "")
    if not sha or not ref:
        print(
            "dependency graph: GITHUB_SHA and GITHUB_REF are required", file=sys.stderr
        )
        return 1
    job_id = os.environ.get("GITHUB_RUN_ID", "local")
    snapshot, errors = build_snapshot(files, sha, ref, job_id)
    if errors:
        print("dependency graph: manifest errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    destination = os.environ.get("DEPENDENCY_GRAPH_SNAPSHOT", "")
    if destination:
        Path(destination).write_text(
            json.dumps(snapshot, indent=2) + "\n", encoding="utf-8"
        )
    count = sum(len(item["resolved"]) for item in snapshot["manifests"].values())
    print(
        f"dependency snapshot: {count} package(s) in {len(snapshot['manifests'])} manifest(s)"
    )
    submit = os.environ.get("DEPENDENCY_GRAPH_SUBMIT", "false").lower() == "true"
    if not submit:
        return 0
    token = os.environ.get("DEPENDENCY_GRAPH_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repository:
        print(
            "dependency graph: token and GITHUB_REPOSITORY are required to submit",
            file=sys.stderr,
        )
        return 1
    return post_snapshot(snapshot, repository, token)


if __name__ == "__main__":
    raise SystemExit(main())
