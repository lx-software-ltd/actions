#!/usr/bin/env python3
"""Fail when tracked source contains a denylisted personal-data value.

The denylist stores SHA-256 hex digests only. A hit is reported as a path
and line number, without the matched text.

Normalization, applied to each line and to each pair of consecutive lines:

- lowercase
- drop ASCII apostrophes and right single quotation marks
- hash emails matched in that text
- hash the digits of a phone-like run when the digit length is 8 to 20
- replace every other character outside ``[a-z0-9.+@]`` with a space
- hash each token (a leading ``@`` is stripped, and leading or trailing
  ``.`` is stripped so sentence punctuation does not hide a match) and each
  2- to 6-token window

``PII_ROOT`` is the directory to scan. Empty uses ``GITHUB_WORKSPACE``, then
the working directory. ``PII_DENYLIST`` is the hash list. A relative path is
resolved from ``PII_ROOT``. Empty uses ``scripts/pii-denylist.sha256``.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

SCAN_SUFFIXES = {
    ".css",
    ".dart",
    ".html",
    ".js",
    ".md",
    ".mdc",
    ".mjs",
    ".py",
    ".sh",
    ".sql",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
EMAIL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}")
PHONE_RE = re.compile(r"\d[\d\s().+\-]{6,}\d")
TOKEN_RE = re.compile(r"[^a-z0-9.+@]+")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _root() -> Path:
    raw = os.environ.get("PII_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    workspace = os.environ.get("GITHUB_WORKSPACE", "").strip()
    if workspace:
        return Path(workspace).resolve()
    return Path.cwd().resolve()


def _denylist_path(root: Path) -> Path:
    raw = os.environ.get("PII_DENYLIST", "").strip()
    if not raw:
        return root / "scripts" / "pii-denylist.sha256"
    path = Path(raw)
    if path.is_absolute():
        return path
    return root / path


def _load_denylist(path: Path) -> set[str]:
    hashes: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        hashes.add(stripped)
    return hashes


def _candidates(text: str) -> set[str]:
    lowered = text.lower().replace("’", "").replace("'", "")
    found: set[str] = set()
    found.update(EMAIL_RE.findall(lowered))
    for match in PHONE_RE.findall(lowered):
        digits = re.sub(r"\D", "", match)
        if 8 <= len(digits) <= 20:
            found.add(digits)
    tokens: list[str] = []
    for token in TOKEN_RE.sub(" ", lowered).split():
        if token.startswith("@"):
            token = token[1:]
        token = token.strip(".")
        if token:
            tokens.append(token)
    for size in range(1, 7):
        for index in range(0, len(tokens) - size + 1):
            found.add(" ".join(tokens[index : index + size]))
    return found


def _git_toplevel(root: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def _tracked_files(root: Path) -> list[Path]:
    top = _git_toplevel(root)
    if top is None:
        return [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SCAN_SUFFIXES
        ]
    result = subprocess.run(
        ["git", "-C", str(top), "ls-files", "-z", "--", str(root)],
        check=True,
        capture_output=True,
    )
    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = top / raw.decode("utf-8")
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.suffix.lower() in SCAN_SUFFIXES:
            paths.append(path)
    return paths


def _matching_lines(path: Path, denied: set[str]) -> list[int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    hits: list[int] = []
    for index, line in enumerate(lines, start=1):
        windows = [line]
        if index < len(lines):
            windows.append(f"{line} {lines[index]}")
        for window in windows:
            if any(_digest(candidate) in denied for candidate in _candidates(window)):
                hits.append(index)
                break
    return hits


def main() -> int:
    root = _root()
    denylist_path = _denylist_path(root)
    if not denylist_path.is_file():
        print(f"missing denylist: {denylist_path}", file=sys.stderr)
        return 1
    denied = _load_denylist(denylist_path)
    if not denied:
        print(
            f"pii check passed: {denylist_path} has no digests, "
            "so this run checks nothing"
        )
        return 0
    failures = 0
    for path in _tracked_files(root):
        try:
            hits = _matching_lines(path, denied)
        except OSError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            return 1
        for line_number in hits:
            relative = path.relative_to(root)
            print(f"{relative}:{line_number}: denylisted personal data")
            failures += 1
    if failures:
        print(
            f"pii check failed: {failures} line(s) match the hashed denylist",
            file=sys.stderr,
        )
        return 1
    print("pii check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
