#!/usr/bin/env python3
"""Fail unless every job result in NEEDS_JSON succeeded.

Accepts either a flat map of job id to result, or the GitHub ``needs``
object (job id to ``{"result": ...}``). Writes a result table to
``GITHUB_STEP_SUMMARY`` when that variable is set.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

PASSING = {"success"}


def parse_results(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict) or not payload:
        raise ValueError("needs-json must be a non-empty object")
    results: dict[str, str] = {}
    for name, value in payload.items():
        job = str(name)
        if isinstance(value, str):
            results[job] = value
            continue
        if isinstance(value, dict) and isinstance(value.get("result"), str):
            results[job] = value["result"]
            continue
        raise ValueError(f"job {job} has no result")
    return results


def failing_jobs(results: dict[str, str]) -> list[str]:
    return [f"{name}={result}" for name, result in results.items() if result not in PASSING]


def summary_table(results: dict[str, str]) -> str:
    lines = ["| Job | Result |", "| --- | --- |"]
    for name, result in results.items():
        safe_name = name.replace("|", "\\|")
        safe_result = result.replace("|", "\\|")
        lines.append(f"| {safe_name} | {safe_result} |")
    return "\n".join(lines) + "\n"


def write_summary(results: dict[str, str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(summary_table(results))


def main() -> int:
    raw = os.environ.get("NEEDS_JSON", "")
    try:
        results = parse_results(json.loads(raw))
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"require-jobs: {exc}", file=sys.stderr)
        return 1
    write_summary(results)
    failed = failing_jobs(results)
    if failed:
        print("Jobs did not all succeed: " + ", ".join(failed), file=sys.stderr)
        return 1
    print("All jobs succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
