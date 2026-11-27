"""Fail-fixture Dependabot entries ignore updates outside a security group."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".github" / "dependabot.yml"
WORKFLOW = ROOT / ".github" / "workflows" / "test.yml"

FAIL_DIRECTORIES = {
    "pip": {
        "/fixtures/python-requirements/fail",
        "/fixtures/dependency-submission/fail",
    },
    "npm": {
        "/fixtures/node-lockfiles/fail",
    },
}

# These pins stay vulnerable for the fail jobs. They are written under
# RUNNER_TEMP so the default branch has no manifest for them.
UNTRACKED_PINS = (
    "fixtures/pip-audit/fail/requirements.txt",
    "fixtures/npm-audit/fail/package.json",
    "fixtures/npm-audit/fail/package-lock.json",
)


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

    def test_audit_fail_pins_are_not_manifests_on_main(self) -> None:
        config = CONFIG.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("/fixtures/pip-audit/fail", config)
        self.assertNotIn("/fixtures/npm-audit/fail", config)
        self.assertNotIn("fixtures/pip-audit/fail", workflow)
        self.assertNotIn("fixtures/npm-audit/fail", workflow)
        self.assertIn("requests==2.19.1", workflow)
        self.assertIn('"$RUNNER_TEMP/pip-audit-fail-requirements.txt"', workflow)
        self.assertIn("${{ runner.temp }}/pip-audit-fail-requirements.txt", workflow)
        self.assertIn('"$RUNNER_TEMP/npm-audit-fail"', workflow)
        self.assertIn("${{ runner.temp }}/npm-audit-fail", workflow)
        self.assertIn('"ip": "2.0.1"', workflow)
        for relative in UNTRACKED_PINS:
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_github_actions_has_no_cooldown_and_splits_the_pin(self) -> None:
        blocks = _update_blocks(CONFIG.read_text(encoding="utf-8"))
        actions = next(
            block
            for block in blocks
            if block.splitlines()[0].strip() == "github-actions"
        )
        self.assertNotIn("cooldown:", actions)
        self.assertIn("actions-pin:", actions)
        self.assertEqual(actions.count('"lx-software-ltd/actions/*"'), 2)
        for block in blocks:
            if block.splitlines()[0].strip() == "github-actions":
                continue
            self.assertNotIn("lx-software-ltd/actions", block)
