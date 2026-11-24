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
    try:
        lines = checker._unmarked_lines(text)
    except checker._TemplateSyntax:
        return 0
    count = 0
    for line in lines:
        count += len(
            checker._PRODUCT_NAME.findall(line.replace("lx-software-ltd", "ORG"))
        )
    return count


def measure(checkouts: list[Path]) -> dict[str, int]:
    capabilities = checker._load_capabilities(
        ROOT / "templates" / "capabilities.json"
    )
    by_file: dict[str, dict[str, str]] = defaultdict(dict)
    unbound = 0
    commands = 0
    names = 0
    for checkout in checkouts:
        for filename, text in _workflows(checkout).items():
            by_file[filename][checkout.name] = text
            unbound += _unbound_optional(text, capabilities)
            commands += _command_blocks(text)
            names += _product_name_count(text)
    identical = 0
    for texts in by_file.values():
        if len(texts) < 2:
            continue
        bodies = {repo: _set_bodies(text) for repo, text in texts.items()}
        width = max(len(items) for items in bodies.values())
        for index in range(width):
            present = [
                items[index] for items in bodies.values() if index < len(items)
            ]
            if len(present) != len(bodies):
                continue
            if len(set(present)) == 1:
                identical += 1
    return {
        "optional blocks not bound to a capability": unbound,
        "value blocks containing run, id, or comment lines": commands,
        "value blocks identical in every repo that has the file": identical,
        "product names in unmarked template text": names,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        print(
            "check_template_drift: pass the product checkouts",
            file=sys.stderr,
        )
        return 1
    counts = measure([Path(argument).resolve() for argument in arguments])
    for label, count in counts.items():
        print(f"{label}: {count}")
    if any(count != 0 for count in counts.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
