"""The API contract check reads block-style OpenAPI and fails closed."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = ROOT / "api-contract" / "check.py"
_SPEC = importlib.util.spec_from_file_location("api_contract_check", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
check_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_module)

FIXTURES = ROOT / "fixtures" / "api-contract"
ORIGIN = "https://api.example.com"
PREFIXES = ("/v1/admin/", "/v1/user/")

EXPECTATIONS = {
    "unknown-file": "notes.txt: file is not public.yaml, admin.yaml, partner.yaml, or webhooks.yaml",
    "server-origin": "servers URL https://api.other.example is not https://api.example.com",
    "public-prefix": "public.yaml: /v1/items does not start with /v1/public/",
    "partner-prefix": "partner.yaml: /v1/public/items does not start with /v1/partner/",
    "webhooks-prefix": "webhooks.yaml: /v1/hooks/mailchimp does not start with /v1/webhooks/",
    "admin-prefix": "admin.yaml: /v1/partner/contacts does not start with an admin prefix",
    "upper-case": "path segment Items has an upper-case letter",
    "underscore": "path segment item_id has an underscore",
    "dot": "path segment items.json has a dot",
    "second-version": "path segment v2 is a second version",
    "parameter": "path parameter {itemId} is not snake_case",
    "flow-style": "this reader cannot follow flow-style YAML",
}


def _check(directory: Path, legacy: Path | None = None) -> list[str]:
    return check_module.check(
        directory,
        origin=ORIGIN,
        admin_prefixes=PREFIXES,
        legacy_file=legacy,
    )


class ApiContractTest(unittest.TestCase):
    def test_pass_fixture_matches_the_contract(self) -> None:
        findings = _check(FIXTURES / "pass", FIXTURES / "legacy-paths.txt")
        self.assertEqual(findings, [])

    def test_each_failing_tree_names_its_rule(self) -> None:
        for name, expected in EXPECTATIONS.items():
            with self.subTest(name=name):
                findings = _check(FIXTURES / "fail" / name)
                self.assertTrue(
                    any(expected in finding for finding in findings),
                    findings,
                )

    def test_a_legacy_path_in_two_files_still_fails(self) -> None:
        findings = _check(
            FIXTURES / "fail" / "duplicate",
            FIXTURES / "fail" / "duplicate-legacy.txt",
        )
        self.assertEqual(
            findings,
            [
                "/v1/kept/items: path is listed in more than one file "
                "(admin.yaml, public.yaml)"
            ],
        )

    def test_a_missing_directory_fails(self) -> None:
        findings = _check(FIXTURES / "missing")
        self.assertIn(f"{FIXTURES / 'missing'}: directory is missing", findings)

    def test_lint_template_runs_the_check_after_redocly(self) -> None:
        text = (ROOT / "templates" / "workflows" / "lint.yml").read_text(
            encoding="utf-8"
        )
        redocly = text.index("npx --yes @redocly/cli@1.34.11 lint docs/api/*.yaml")
        step = text.index("lx-software-ltd/actions/api-contract@", redocly)
        self.assertIn(
            "8b75c2c3e18a96ffae1ac4f99e3dceb4821a1faf # main 2026-11-24",
            text[step : step + 120],
        )
        window = text[step : text.index("# template:end", step)]
        self.assertIn("# template:set", window)
        self.assertIn("origin: https://api.example.com", window)
        self.assertIn("admin-prefixes: /v1/admin/,/v1/user/", window)
        self.assertNotIn("- uses:", window.split("# template:set", 1)[1])
