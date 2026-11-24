#!/usr/bin/env python3
"""Count remaining template drift across product checkouts.

Prints four counts and exits 1 when any of them is not zero:

- optional blocks whose id is not a capability
- value blocks that contain ``run:``, ``id:``, or a comment
- value blocks whose text is the same in every checkout that has the file
- product names in unmarked template text
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workflow-conformance"))

import check_workflows as checker  # noqa: E402


def _workflows(root: Path) -> dict[str, str]:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return {}
    found: dict[str, str] = {}
    for path in sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml")):
        found[path.name] = path.read_text(encoding="utf-8")
    return found


def _set_bodies(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").splitlines()
    bodies: list[str] = []
    index = 0
    while index < len(lines):
        if not checker._is_set(lines[index]):
            index += 1
            continue
        block, index = checker._consume_balanced(lines, index)
        bodies.append("\n".join(block[1:-1]))
    return bodies


def _command_blocks(text: str) -> int:
    count = 0
    for body in _set_bodies(text):
        if any(checker._value_block_command(line.strip()) for line in body.splitlines()):
            count += 1
    return count


def _unbound_optional(text: str, capabilities: dict[str, str]) -> int:
    return sum(
        1
        for line in text.splitlines()
        if (name := checker._optional_name(line)) is not None and name not in capabilities
    )


def _product_name_count(text: str) -> int:
    lines = checker._unmarked_lines(text)
    count = 0
    for line in lines:
        count += len(
            checker._PRODUCT_NAME.findall(line.replace("lx-software-ltd", "ORG"))
        )
    return count


def _identical_blocks(texts: dict[str, str]) -> int:
    """Count non-empty blocks that match at the same anchor in every checkout."""
    anchored = {
        repo: checker._anchored_value_bodies(text) for repo, text in texts.items()
    }
    keys: set[tuple[tuple[str, ...], int]] = set()
    for items in anchored.values():
        for stack, local, _body in items:
            keys.add((stack, local))
    count = 0
    for key in keys:
        present: list[str] = []
        for items in anchored.values():
            matches = [body for stack, local, body in items if (stack, local) == key]
            if matches:
                present.append(matches[0])
        if len(present) != len(anchored) or not present[0]:
            continue
        if len(set(present)) == 1:
            count += 1
    return count


def measure(checkouts: list[Path]) -> dict[str, int]:
    capabilities = checker._load_capabilities(
        ROOT / "templates" / "capabilities.json"
    )
    by_file: dict[str, dict[str, str]] = defaultdict(dict)
    unbound = 0
    commands = 0
    names = 0
    for path in sorted((ROOT / "templates" / "workflows").glob("*.yml")):
        names += _product_name_count(path.read_text(encoding="utf-8"))
    for checkout in checkouts:
        templates = {
            path.name for path in (ROOT / "templates" / "workflows").glob("*.yml")
        }
        for filename, text in _workflows(checkout).items():
            if filename not in templates:
                continue
            by_file[filename][checkout.name] = text
            unbound += _unbound_optional(text, capabilities)
            commands += _command_blocks(text)
    identical = 0
    for texts in by_file.values():
        if len(texts) < 2:
            continue
        identical += _identical_blocks(texts)
    return {
        "optional blocks not bound to a capability": unbound,
        "value blocks containing run, id, or comment lines": commands,
        "value blocks identical in every repo that has the file": identical,
        "product names in unmarked template text": names,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(argument in ("-h", "--help") for argument in arguments):
        print(
            "usage: check_template_drift.py CHECKOUT [CHECKOUT...]",
            file=sys.stderr,
        )
        return 0
    if not arguments:
        print(
            "check_template_drift: pass the product checkouts",
            file=sys.stderr,
        )
        return 1
    paths = [Path(argument).resolve() for argument in arguments]
    missing = [path for path in paths if not path.is_dir()]
    if missing:
        for path in missing:
            print(f"check_template_drift: not a directory: {path}", file=sys.stderr)
        return 1
    counts = measure(paths)
    for label, count in counts.items():
        print(f"{label}: {count}")
    if any(count != 0 for count in counts.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
