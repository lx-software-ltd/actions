"""The API contract check reads block-style OpenAPI and fails closed."""

from __future__ import annotations

import importlib.util
import re
import subprocess
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
    "proxy-middle": "{proxy+} is not the last segment",
    "proxy-public": "{proxy+} is not allowed without an authorizer",
}

_ACTION_PIN = re.compile(
    r"uses:\s*lx-software-ltd/actions/([A-Za-z0-9_.-]+)@([0-9a-f]{40})"
)


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

    def test_a_real_spec_with_refs_parses(self) -> None:
        directory = FIXTURES / "siutindei-public"
        text = (directory / "public.yaml").read_text(encoding="utf-8")
        servers, paths = check_module.read_openapi(text)
        self.assertIn("https://api.siutindei.com", servers)
        self.assertGreater(len(paths), 0)
        findings = check_module.check(
            directory,
            origin="https://api.siutindei.com",
            admin_prefixes=PREFIXES,
            legacy_file=None,
        )
        self.assertEqual(findings, [])

    def test_lint_template_omits_the_action_until_it_is_on_main(self) -> None:
        text = (ROOT / "templates" / "workflows" / "lint.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("npx --yes @redocly/cli@1.34.11 lint docs/api/*.yaml", text)
        self.assertNotIn("lx-software-ltd/actions/api-contract@", text)

    def test_template_pins_point_at_an_action_file(self) -> None:
        missing: list[str] = []
        for path in sorted((ROOT / "templates").rglob("*.yml")):
            text = path.read_text(encoding="utf-8")
            for match in _ACTION_PIN.finditer(text):
                directory, sha = match.group(1), match.group(2)
                spec = f"{sha}:{directory}/action.yml"
                result = subprocess.run(
                    ["git", "cat-file", "-e", spec],
                    cwd=ROOT,
                    capture_output=True,
                    check=False,
                )
                if result.returncode != 0:
                    relative = path.relative_to(ROOT)
                    missing.append(f"{relative}: {directory}@{sha}")
        self.assertEqual(missing, [])
