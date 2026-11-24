#!/usr/bin/env python3
"""Install @lhci/cli without the deprecated packages its old ranges pull in."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# @lhci/cli 0.15.1 resolves these exact versions. 0.13.4 pulls rimraf 3, glob 7,
# and inflight. tmp 0.1.0 pulls rimraf 2. uuid 8.3.2 is the direct dependency.
# The keys are version-specific so Lighthouse keeps chrome-launcher 1.x and a
# newer CLI keeps uuid 14.
OVERRIDES = {
    "chrome-launcher@0.13.4": "0.15.2",
    "tmp@0.1.0": "0.2.4",
    "uuid@8.3.2": "11.1.1",
}
INSTALL_DIRECTORY = "lhci"
_VERSION = re.compile(r"^[A-Za-z0-9^~][A-Za-z0-9._^+~-]*$")


class InstallError(Exception):
    """The CLI cannot be installed."""


def manifest(version: str) -> dict[str, object]:
    chosen = version.strip()
    if _VERSION.fullmatch(chosen) is None:
        raise InstallError(f"lhci-version is not an npm version. Got: {version!r}")
    return {
        "private": True,
        "dependencies": {"@lhci/cli": chosen},
        "overrides": dict(OVERRIDES),
    }


def install_root(temp: Path) -> Path:
    return temp / INSTALL_DIRECTORY


def install(temp: Path, version: str) -> Path:
    """Write the manifest under the runner temp dir and install the CLI."""
    root = install_root(temp)
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        json.dumps(manifest(version), indent=2) + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund"],
        cwd=root,
        check=False,
    )
    if completed.returncode != 0:
        raise InstallError("npm install of @lhci/cli failed.")
    binary = root / "node_modules" / ".bin" / "lhci"
    if not binary.is_file():
        raise InstallError("lhci was not installed.")
    return binary


def main() -> int:
    temp = os.environ.get("RUNNER_TEMP", "").strip()
    if not temp:
        print("::error::RUNNER_TEMP is required", file=sys.stderr)
        return 1
    try:
        install(Path(temp), os.environ.get("LHCI_VERSION", ""))
    except InstallError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
