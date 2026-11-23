"""Plan aliases: a spaced label is one alias, and empty stays every group."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

import cdk_plan  # noqa: E402


PLAN = {
    "aliases": {
        "all stacks": ["api", "admin"],
        "admin web": ["admin"],
        "public www": ["www"],
    },
    "groups": [
        {"stacks": ["api"]},
        {"stacks": ["admin"]},
        {"stacks": ["www"]},
        {"stacks": ["waf"]},
    ],
}


class AliasTest(unittest.TestCase):
    def test_a_spaced_label_is_one_alias(self) -> None:
        self.assertEqual(
            cdk_plan.resolve_selection(PLAN, "all stacks"),
            ["api", "admin"],
        )

    def test_comma_separated_labels_expand_in_order(self) -> None:
        self.assertEqual(
            cdk_plan.resolve_selection(PLAN, "public www, admin web"),
            ["www", "admin"],
        )

    def test_an_unknown_label_stays_a_stack_name(self) -> None:
        self.assertEqual(cdk_plan.resolve_selection(PLAN, "custom"), ["custom"])

    def test_stack_names_still_split_on_whitespace(self) -> None:
        self.assertEqual(
            cdk_plan.resolve_selection(PLAN, "api admin"),
            ["api", "admin"],
        )

    def test_empty_selects_nothing_so_groups_apply(self) -> None:
        self.assertEqual(cdk_plan.resolve_selection(PLAN, "  "), [])
        self.assertEqual(
            cdk_plan._selected(PLAN, []),
            {"api", "admin", "www", "waf"},
        )

    def test_repeated_names_are_kept_once(self) -> None:
        self.assertEqual(
            cdk_plan.resolve_selection(PLAN, "admin web, admin"),
            ["admin"],
        )

    def test_a_label_with_a_comma_is_rejected(self) -> None:
        broken = {"aliases": {"a, b": ["api"]}, "groups": [{"stacks": ["api"]}]}
        with self.assertRaises(cdk_plan.DeployError):
            cdk_plan.resolve_selection(broken, "a, b")

    def test_a_missing_alias_map_keeps_the_old_split(self) -> None:
        plain = {"groups": [{"stacks": ["api"]}]}
        self.assertEqual(cdk_plan.resolve_selection(plain, "api, web"), ["api", "web"])


if __name__ == "__main__":
    unittest.main()
