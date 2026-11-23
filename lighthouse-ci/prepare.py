#!/usr/bin/env python3
"""Write a Lighthouse CI config whose collect URLs come from the input."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

URL = re.compile(r"^https?://", re.IGNORECASE)


class PrepareError(Exception):
    """The config cannot be written."""


def targets(raw: str, defaults: str) -> list[str]:
    source = raw.strip() or defaults.strip()
    found = [part.strip() for part in re.split(r"[\n,]+", source) if part.strip()]
    if not found:
        raise PrepareError("Set page-paths or default-paths.")
    return found


def urls(pages: list[str], port: str) -> list[str]:
    if not port.isdigit():
        raise PrepareError(f"port must be a number. Got: {port}")
    collected: list[str] = []
    for target in pages:
        if URL.match(target):
            collected.append(target)
            continue
        path = target if target.startswith("/") else f"/{target}"
        collected.append(f"http://localhost:{port}{path}")
    return collected


def write_config(directory: Path, config_name: str, pages: list[str], port: str) -> Path:
    source = directory / config_name
    if not source.is_file():
        raise PrepareError(f"Missing {config_name}")
    try:
        config = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PrepareError(f"{config_name} is not JSON") from exc
    if not isinstance(config, dict):
        raise PrepareError(f"{config_name} must be a JSON object")
    ci = config.get("ci")
    if not isinstance(ci, dict):
        ci = {}
        config["ci"] = ci
    collect = ci.get("collect")
    if not isinstance(collect, dict):
        collect = {}
        ci["collect"] = collect
    chosen = urls(pages, port)
    collect["url"] = chosen
    destination = directory / ".lighthouserc.runtime.json"
    destination.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print("Lighthouse targets:")
    for url in chosen:
        print(f"- {url}")
    return destination


def main() -> int:
    directory = Path(os.environ.get("WORKING_DIRECTORY", "") or ".")
    try:
        pages = targets(
            os.environ.get("LIGHTHOUSE_PAGE_PATHS", ""),
            os.environ.get("DEFAULT_PATHS", ""),
        )
        write_config(
            directory,
            os.environ.get("CONFIG", "") or ".lighthouserc.json",
            pages,
            os.environ.get("PORT", "") or "9000",
        )
    except PrepareError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    if os.environ.get("DRY_RUN", "").lower() == "true":
        print("Dry run: Lighthouse CI was not started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
