"""Fail-fixture Dependabot entries ignore updates outside a security group."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".github" / "dependabot.yml"

FAIL_DIRECTORIES = {
    "pip": {
        "/fixtures/pip-audit/fail",
        "/fixtures/python-requirements/fail",
        "/fixtures/dependency-graph/fail",
    },
    "npm": {
        "/fixtures/npm-audit/fail",
        "/fixtures/node-lockfiles/fail",
    },
}


def _update_blocks(text: str) -> list[str]:
    body = text.split("updates:\n", 1)[1]
    return [
        block
        for block in body.split("\n  - package-ecosystem: ")
        if block.strip()
    ]


class DependabotFailFixturesTest(unittest.TestCase):
    def test_fail_fixtures_are_ignored_outside_a_security_group(self) -> None:
        blocks = _update_blocks(CONFIG.read_text(encoding="utf-8"))
        seen: set[str] = set()
        for block in blocks:
            ecosystem = block.splitlines()[0].strip()
            if ecosystem not in FAIL_DIRECTORIES:
                continue
            seen.add(ecosystem)
            for directory in FAIL_DIRECTORIES[ecosystem]:
                self.assertIn(f'- "{directory}"', block)
            self.assertIn('dependency-name: "*"', block)
            group = block.split("groups:", 1)[1]
            self.assertIn("applies-to: security-updates", group)
            self.assertIn("exclude-patterns:", group)
            self.assertEqual(group.count('- "*"'), 2)
        self.assertEqual(seen, set(FAIL_DIRECTORIES))
