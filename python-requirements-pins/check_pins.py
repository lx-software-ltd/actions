#!/usr/bin/env python3
"""Fail when a requirement is not pinned with ==.

Includes written as ``-r`` or ``--requirement`` are followed. An include
must stay inside the directory of the file that started the walk.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _include(line: str) -> str | None:
    if line.startswith("-r ") or line.startswith("--requirement "):
        return line.split(None, 1)[1]
    if line.startswith("-r="):
        return line[3:]
    if line.startswith("--requirement="):
        return line.split("=", 1)[1]
    return None


def check_files(files: list[Path]) -> list[str]:
    errors: list[str] = []
    for start in files:
        root = start.parent.resolve()
        seen: set[Path] = set()

        def check_file(path: Path) -> None:
            resolved = path.resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"include escapes {root}: {path}")
                return
            if resolved in seen:
                errors.append(f"circular include: {path}")
                return
            if not path.exists():
                errors.append(f"missing include: {path}")
                return
            seen.add(resolved)
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                included = _include(stripped)
                if included is not None:
                    check_file(path.parent / included)
                    continue
                if "==" not in stripped:
                    errors.append(f"{path}: {stripped}")

        if not start.exists():
            errors.append(f"missing requirements file: {start}")
            continue
        check_file(start)
    return errors


def main() -> int:
    raw = os.environ.get("REQUIREMENTS_FILES", "")
    files = [Path(line.strip()) for line in raw.splitlines() if line.strip()]
    if not files:
        print("python-requirements-pins: files are required", file=sys.stderr)
        return 1
    errors = check_files(files)
    if errors:
        print("Unpinned requirements found:")
        for entry in errors:
            print(f"- {entry}")
        return 1
    print("All requirements are pinned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
