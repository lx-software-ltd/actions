"""verify-rulesets expects exactly 0 reviews and exactly lint and test."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "verify-rulesets" / "verify_rulesets.py"
_SPEC = importlib.util.spec_from_file_location("verify_rulesets", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
rulesets = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rulesets)


def _main(*, enforcement: str = "active", contexts: list[str] | None = None, reviews: int = 0) -> dict:
    checks = [{"context": context} for context in (contexts if contexts is not None else ["lint", "test"])]
    return {
        "name": "main-protection",
        "target": "branch",
        "enforcement": enforcement,
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": {"required_approving_review_count": reviews}},
            {"type": "required_status_checks", "parameters": {"required_status_checks": checks}},
        ],
    }


def _tags() -> dict:
    return {
        "name": "release-tags",
        "target": "tag",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/tags/v*"]}},
        "rules": [{"type": "deletion"}, {"type": "update"}, {"type": "creation"}],
    }


def _evaluate(items: list[dict], job_names: set[str] | None = None, reviews: int = 0) -> list[str]:
    return rulesets.evaluate(
        rulesets=items,
        legacy_tags=None,
        job_names=job_names if job_names is not None else {"lint", "test"},
        expected_reviews=reviews,
        required_checks={"lint", "test"},
    )


class VerifyRulesetsTest(unittest.TestCase):
    def test_zero_reviews_and_exact_checks_pass(self) -> None:
        self.assertEqual(_evaluate([_main(), _tags()]), [])

    def test_one_review_fails(self) -> None:
        errors = _evaluate([_main(reviews=1), _tags()])
        self.assertTrue(any("expected exactly 0" in error for error in errors))

    def test_missing_review_rule_fails(self) -> None:
        ruleset = _main()
        ruleset["rules"] = [rule for rule in ruleset["rules"] if rule["type"] != "pull_request"]
        errors = _evaluate([ruleset, _tags()])
        self.assertTrue(any("does not set an approving-review count" in error for error in errors))

    def test_checks_must_match_exactly(self) -> None:
        only_test = _evaluate([_main(contexts=["test"]), _tags()])
        extra = _evaluate([_main(contexts=["lint", "test", "build"]), _tags()], job_names={"lint", "test", "build"})
        self.assertTrue(any("expected exactly" in error for error in only_test))
        self.assertTrue(any("expected exactly" in error for error in extra))

    def test_expected_check_must_be_a_job_name(self) -> None:
        errors = _evaluate([_main(), _tags()], job_names={"test"})
        self.assertTrue(any("does not match a job name" in error for error in errors))

    def test_disabled_main_ruleset_fails(self) -> None:
        errors = _evaluate([_main(enforcement="disabled"), _tags()])
        self.assertTrue(any("not active" in error for error in errors))

    def test_missing_main_ruleset_fails(self) -> None:
        self.assertEqual(_evaluate([_tags()]), ["No active ruleset targets main."])

    def test_missing_force_push_block_fails(self) -> None:
        ruleset = _main()
        ruleset["rules"] = [rule for rule in ruleset["rules"] if rule["type"] != "non_fast_forward"]
        errors = _evaluate([ruleset, _tags()])
        self.assertTrue(any("force pushes" in error for error in errors))

    def test_split_tag_rules_pass(self) -> None:
        update_and_delete = _tags()
        update_and_delete["rules"] = [{"type": "deletion"}, {"type": "update"}]
        create = _tags()
        create["name"] = "release-tags-create"
        create["rules"] = [{"type": "creation"}]
        self.assertEqual(_evaluate([_main(), update_and_delete, create]), [])

    def test_missing_tag_creation_fails(self) -> None:
        tags = _tags()
        tags["rules"] = [{"type": "deletion"}, {"type": "update"}]
        errors = _evaluate([_main(), tags])
        self.assertTrue(any("do not block creation" in error for error in errors))

    def test_missing_tag_protection_fails(self) -> None:
        errors = _evaluate([_main()])
        self.assertTrue(any("v* tags" in error for error in errors))

    def test_doubled_tag_pattern_does_not_count(self) -> None:
        tags = _tags()
        tags["conditions"] = {"ref_name": {"include": ["refs/tags/refs/tags/v*"]}}
        errors = _evaluate([_main(), tags])
        self.assertTrue(any("v* tags" in error for error in errors))

    def test_job_names_ignore_step_names(self) -> None:
        text = """
name: Test
on: pull_request
jobs:
  test:
    name: test
    steps:
      - name: Require every test job
        run: echo ok
"""
        self.assertEqual(rulesets.job_names_in_workflow(text), {"test"})

    def test_fixtures_match_the_contract(self) -> None:
        passing = json.loads((ROOT / "fixtures/verify-rulesets/pass.json").read_text(encoding="utf-8"))
        failing = json.loads((ROOT / "fixtures/verify-rulesets/fail.json").read_text(encoding="utf-8"))
        self.assertEqual(_evaluate(passing), [])
        self.assertTrue(_evaluate(failing))

    def test_legacy_403_is_treated_as_absent(self) -> None:
        self.assertTrue(rulesets.legacy_read_is_absent("gh api failed: HTTP 403"))


if __name__ == "__main__":
    unittest.main()
