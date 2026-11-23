#!/usr/bin/env python3
"""Rewrite lx-software-ltd/actions pins in a product checkout.

Every workflow pin, the ``# main YYYY-MM-DD`` comment on that line, and
the pre-commit ``rev`` move together. Conformance fails when they differ.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
PIN = re.compile(
    r"^(?P<prefix>.*uses:\s+lx-software-ltd/actions/[A-Za-z0-9_.-]+@)(?P<sha>[0-9a-f]{40})(?P<suffix>.*)$"
)
REV = re.compile(
    r"^(?P<indent>[ \t]*rev:[ \t]+)(?P<sha>\S+)(?P<trail>[ \t]*)$"
)
REPO = re.compile(r"^[ \t]*-[ \t]*repo:[ \t]*\S*lx-software-ltd/actions\S*")


def _date(value: str | None) -> str:
    if value:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    return datetime.now(timezone.utc).date().isoformat()


def _comment(suffix: str, day: str) -> str:
    comment = f"# main {day}"
    if "#" in suffix:
        return re.sub(r"#.*$", comment, suffix)
    spacer = "" if suffix.endswith(" ") or suffix == "" else " "
    return f"{suffix}{spacer}{comment}"


def rewrite_workflow(text: str, sha: str, day: str) -> tuple[str, int]:
    count = 0
    lines: list[str] = []
    for line in text.splitlines():
        match = PIN.match(line)
        if match is None:
            lines.append(line)
            continue
        count += 1
        lines.append(f"{match.group('prefix')}{sha}{_comment(match.group('suffix'), day)}")
    ending = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + ending, count


def rewrite_pre_commit(text: str, sha: str) -> tuple[str, int]:
    count = 0
    in_actions = False
    lines: list[str] = []
    for line in text.splitlines():
        if REPO.match(line):
            in_actions = True
            lines.append(line)
            continue
        if in_actions and re.match(r"^[ \t]*-[ \t]*repo:", line):
            in_actions = False
        match = REV.match(line) if in_actions else None
        if match is None:
            lines.append(line)
            continue
        count += 1
        in_actions = False
        lines.append(f"{match.group('indent')}{sha}{match.group('trail')}")
    ending = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + ending, count


def _read_compare(sha: str) -> str:
    """Return the compare status of this SHA against actions main."""
    url = f"https://api.github.com/repos/lx-software-ltd/actions/compare/{sha}...main"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "bump-pins"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ValueError(f"{sha} is not a commit on main") from None
        raise ValueError(f"could not check {sha} against main ({error.code})") from None
    return str(payload.get("status", ""))


def require_sha_on_main(sha: str, read=None) -> None:
    """Reject a SHA that is not contained in actions main.

    ``ahead`` and ``identical`` mean main contains the SHA. ``behind`` is a
    commit that main does not contain yet. A missing commit is a 404.
    """
    if not SHA.fullmatch(sha):
        raise ValueError(f"sha must be 40 hex characters, got {sha!r}")
    status = (_read_compare if read is None else read)(sha)
    if status not in {"ahead", "identical"}:
        raise ValueError(f"{sha} is not on main")


def bump(root: Path, sha: str, day: str) -> int:
    if not SHA.fullmatch(sha):
        raise ValueError(f"sha must be 40 hex characters, got {sha!r}")
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        raise ValueError(f"no workflows at {workflow_dir}")
    changed = 0
    for path in sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        updated, count = rewrite_workflow(text, sha, day)
        if count:
            path.write_text(updated, encoding="utf-8")
            changed += count
    pre_commit = root / ".pre-commit-config.yaml"
    rev_count = 0
    if pre_commit.is_file():
        text = pre_commit.read_text(encoding="utf-8")
        updated, rev_count = rewrite_pre_commit(text, sha)
        if rev_count:
            pre_commit.write_text(updated, encoding="utf-8")
    if changed == 0:
        raise ValueError("no lx-software-ltd/actions pins found")
    if pre_commit.is_file() and rev_count == 0 and "lx-software-ltd/actions" in pre_commit.read_text(encoding="utf-8"):
        raise ValueError("pre-commit names actions but no rev was rewritten")
    return changed + rev_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Move every actions pin in a checkout to one SHA.")
    parser.add_argument("checkout", type=Path)
    parser.add_argument("sha")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD. Defaults to today, UTC.")
    args = parser.parse_args(argv)
    try:
        day = _date(args.date)
        require_sha_on_main(args.sha)
        count = bump(args.checkout, args.sha, day)
    except (ValueError, OSError) as exc:
        print(f"bump_pins: {exc}", file=sys.stderr)
        return 1
    print(f"Rewrote {count} pin(s) to {args.sha} # main {day}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
