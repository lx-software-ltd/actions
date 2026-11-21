#!/usr/bin/env python3
"""Drop SARIF results suppressed in source.

A result is removed when any suppression has kind ``inSource``. The matched
text is not printed. The removed count is the finding-count delta.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def empty_sarif() -> dict:
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [],
    }


def drop_in_source(payload: dict) -> tuple[dict, int]:
    removed = 0
    for run in payload.get("runs") or []:
        if not isinstance(run, dict):
            continue
        kept = []
        for result in run.get("results") or []:
            suppressions = result.get("suppressions") if isinstance(result, dict) else None
            if any(
                isinstance(item, dict) and item.get("kind") == "inSource"
                for item in (suppressions or [])
            ):
                removed += 1
                continue
            kept.append(result)
        run["results"] = kept
    return payload, removed


def filter_file(source: Path, destination: Path) -> int:
    if source.is_dir():
        candidates = sorted(source.glob("*.sarif"))
        source = candidates[0] if candidates else source
    if not source.is_file():
        destination.write_text(json.dumps(empty_sarif()), encoding="utf-8")
        print(f"{source} not found; emitting empty SARIF.")
        return 0
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload, removed = drop_in_source(payload)
    destination.write_text(json.dumps(payload), encoding="utf-8")
    print(f"Removed {removed} in-source suppressed findings from SARIF.")
    return removed


def main() -> int:
    source = Path(os.environ.get("SARIF_INPUT", "")).expanduser()
    destination = Path(os.environ.get("SARIF_OUTPUT", "")).expanduser()
    if not str(source) or not str(destination) or str(source) == "." or str(destination) == ".":
        print("filter_sarif: SARIF_INPUT and SARIF_OUTPUT are required", file=sys.stderr)
        return 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    filter_file(source, destination)
    output = os.environ.get("GITHUB_OUTPUT", "")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"filtered_sarif={destination}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
