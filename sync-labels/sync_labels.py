#!/usr/bin/env python3
"""Create and update the shared issue labels.

The catalogue is labels.json beside this file. A label that is not in the
catalogue stays on the repository. check fails when a listed repository
differs. apply writes the difference. live JSON skips GitHub and is only
valid with check.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

CATALOGUE = Path(__file__).resolve().parent / "labels.json"
COLOR = re.compile(r"^[0-9a-fA-F]{6}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SIBLINGS = (
    "lx-software-ltd/actions",
    "lx-software-ltd/evolvesprouts",
    "lx-software-ltd/findingalpha",
    "lx-software-ltd/lx-software",
    "lx-software-ltd/siutindei",
)


@dataclass(frozen=True)
class Label:
    name: str
    color: str
    description: str


@dataclass(frozen=True)
class Change:
    action: str
    repo: str
    label: Label
    before: Label | None = None


def parse_mode(text: str) -> str:
    mode = text.strip() or "check"
    if mode not in {"check", "apply"}:
        raise ValueError(f"mode must be check or apply, got {mode!r}")
    return mode


def parse_repositories(text: str, *, default: str) -> list[str]:
    raw = text.strip() or default.strip()
    if not raw:
        raise ValueError("set repositories, or run in GitHub so GITHUB_REPOSITORY is set")
    if raw == "siblings":
        return list(SIBLINGS)
    repos: list[str] = []
    seen: set[str] = set()
    for token in raw.split():
        if REPO.fullmatch(token) is None:
            raise ValueError(f"repository must be owner/name, got {token!r}")
        if token not in seen:
            repos.append(token)
            seen.add(token)
    return repos


def _catalogue_label(item: Any, index: int) -> Label:
    where = f"label {index}"
    if not isinstance(item, dict):
        raise ValueError(f"{where} must be an object")
    name = item.get("name")
    if isinstance(name, str) and name:
        where = f"label {name!r}"
    if not isinstance(name, str) or not name or name.strip() != name:
        raise ValueError(f"label {index} needs a name with no surrounding space")
    if len(name) > 50:
        raise ValueError(f"{where} is longer than 50 characters")
    if any(ord(char) < 32 for char in name):
        raise ValueError(f"{where} contains a control character")
    color = item.get("color")
    if not isinstance(color, str) or COLOR.fullmatch(color) is None:
        raise ValueError(f"{where} color must be 6 hex digits")
    description = item.get("description", "")
    if not isinstance(description, str):
        raise ValueError(f"{where} description must be a string")
    if len(description) > 100:
        raise ValueError(f"{where} description is longer than 100 characters")
    if any(ord(char) < 32 for char in description):
        raise ValueError(f"{where} description contains a control character")
    extra = set(item) - {"name", "color", "description"}
    if extra:
        raise ValueError(f"{where} has unknown keys: {', '.join(sorted(extra))}")
    return Label(name, color.lower(), description)


def parse_catalogue(data: Any) -> list[Label]:
    if not isinstance(data, list) or not data:
        raise ValueError("the catalogue must be a non-empty list")
    labels = [_catalogue_label(item, index) for index, item in enumerate(data, start=1)]
    folded = [label.name.casefold() for label in labels]
    if len(set(folded)) != len(folded):
        raise ValueError("catalogue label names must be unique")
    if folded != sorted(folded):
        raise ValueError("catalogue labels must be in alphabetical order")
    return labels


def load_catalogue_text(text: str) -> list[Label]:
    raw = text.strip()
    if not raw:
        raw = CATALOGUE.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"labels JSON is invalid: {exc}") from exc
    return parse_catalogue(data)


def parse_live(data: Any) -> list[Label]:
    if not isinstance(data, list):
        raise ValueError("live labels must be a list")
    labels: list[Label] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"live label {index} must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"live label {index} needs a name")
        color = item.get("color") or ""
        if not isinstance(color, str):
            raise ValueError(f"live label {name!r} color must be a string")
        description = item.get("description")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise ValueError(f"live label {name!r} description must be a string")
        labels.append(Label(name, color.removeprefix("#").lower(), description))
    return labels


def parse_live_document(text: str, repos: list[str]) -> dict[str, list[Label]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"live JSON is invalid: {exc}") from exc
    if isinstance(data, list):
        labels = parse_live(data)
        return {repo: labels for repo in repos}
    if not isinstance(data, dict):
        raise ValueError("live JSON must be a list or an object keyed by owner/repo")
    found: dict[str, list[Label]] = {}
    for repo in repos:
        if repo not in data:
            raise ValueError(f"live JSON has no entry for {repo}")
        found[repo] = parse_live(data[repo])
    return found


def diff_labels(repo: str, wanted: list[Label], live: list[Label]) -> list[Change]:
    by_name: dict[str, Label] = {}
    for label in live:
        key = label.name.casefold()
        if key in by_name:
            raise ValueError(f"{repo} lists {label.name!r} more than once")
        by_name[key] = label
    changes: list[Change] = []
    for label in wanted:
        current = by_name.get(label.name.casefold())
        if current is None:
            changes.append(Change("create", repo, label))
            continue
        if (
            current.name != label.name
            or current.color != label.color
            or current.description != label.description
        ):
            changes.append(Change("update", repo, label, current))
    return changes


def format_change(change: Change) -> str:
    label = change.label
    if change.action == "create":
        return f"create {change.repo} {label.name} #{label.color} {label.description}"
    before = change.before
    if before is None:
        raise ValueError(f"update of {label.name} on {change.repo} has no current label")
    parts = [f"update {change.repo} {before.name}"]
    if before.name != label.name:
        parts.append(f"name -> {label.name}")
    if before.color != label.color:
        parts.append(f"color {before.color} -> {label.color}")
    if before.description != label.description:
        parts.append(f"description {before.description!r} -> {label.description!r}")
    return " ".join(parts)


def _gh_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("GH_TOKEN", "").strip():
        env.pop("GH_TOKEN", None)
    if not env.get("GITHUB_TOKEN", "").strip():
        env.pop("GITHUB_TOKEN", None)
    return env


def _run_gh(args: list[str], payload: dict[str, Any] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["gh", *args],
            input=None if payload is None else json.dumps(payload),
            check=False,
            capture_output=True,
            text=True,
            env=_gh_env(),
        )
    except FileNotFoundError as exc:
        raise RuntimeError("gh is not on PATH") from exc


def _parse_json_stream(text: str) -> Any:
    raw = text.strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        items: list[Any] = []
        index = 0
        length = len(raw)
        while index < length:
            while index < length and raw[index].isspace():
                index += 1
            if index >= length:
                break
            value, end = decoder.raw_decode(raw, index)
            if isinstance(value, list):
                items.extend(value)
            else:
                items.append(value)
            index = end
        return items


def fetch_labels(repo: str) -> list[Label]:
    result = _run_gh(["api", "--paginate", f"repos/{repo}/labels"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"could not list labels on {repo}: {detail}")
    data = _parse_json_stream(result.stdout)
    if isinstance(data, dict):
        message = data.get("message", data)
        raise RuntimeError(f"could not list labels on {repo}: {message}")
    return parse_live(data)


def apply_change(change: Change) -> None:
    label = change.label
    if change.action == "create":
        method = "POST"
        path = f"repos/{change.repo}/labels"
        payload: dict[str, str] = {
            "name": label.name,
            "color": label.color,
            "description": label.description,
        }
    else:
        if change.before is None:
            raise RuntimeError(f"update of {label.name} on {change.repo} has no current label")
        method = "PATCH"
        path = f"repos/{change.repo}/labels/{quote(change.before.name, safe='')}"
        payload = {
            "new_name": label.name,
            "color": label.color,
            "description": label.description,
        }
    result = _run_gh(["api", "--method", method, "--input", "-", path], payload)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"gh api {method} {path} failed: {detail}")


def main() -> int:
    try:
        mode = parse_mode(os.environ.get("SYNC_LABELS_MODE", ""))
        wanted = load_catalogue_text(os.environ.get("SYNC_LABELS_JSON", ""))
        repos = parse_repositories(
            os.environ.get("SYNC_LABELS_REPOSITORIES", ""),
            default=os.environ.get("GITHUB_REPOSITORY", ""),
        )
    except ValueError as exc:
        print(f"sync-labels: {exc}", file=sys.stderr)
        return 1
    live_text = os.environ.get("SYNC_LABELS_LIVE_JSON", "").strip()
    if mode == "apply" and live_text:
        print("sync-labels: live JSON is only for check.", file=sys.stderr)
        return 1
    try:
        if live_text:
            live_by_repo = parse_live_document(live_text, repos)
        else:
            live_by_repo = {repo: fetch_labels(repo) for repo in repos}
        changes = [
            change
            for repo in repos
            for change in diff_labels(repo, wanted, live_by_repo[repo])
        ]
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"sync-labels: {exc}", file=sys.stderr)
        return 1
    for change in changes:
        print(format_change(change))
    if not changes:
        print("sync-labels: no changes")
        return 0
    if mode == "check":
        print(f"sync-labels: {len(changes)} change(s). check does not write.", file=sys.stderr)
        return 1
    try:
        for change in changes:
            apply_change(change)
    except RuntimeError as exc:
        print(f"sync-labels: {exc}", file=sys.stderr)
        return 1
    print(f"sync-labels: applied {len(changes)} change(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
