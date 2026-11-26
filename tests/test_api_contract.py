"""The API contract check reads block-style OpenAPI and fails closed."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import tempfile
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
    "proxy-webhooks": "{proxy+} is not allowed without an authorizer",
    "servers-under-path": "servers key under a path is not the document servers",
    "quoted-paths": "quoted paths key is not opened",
    "quoted-paths-single": "quoted paths key is not opened",
    "no-paths": "file has no paths block",
    "query-segment": "path segment a?x=1 does not match ^[a-z0-9]+(-[a-z0-9]+)*$",
    "empty-segment": "empty path segment",
    "trailing-slash": "empty path segment",
    "colon-segment": "path segment items:search does not match ^[a-z0-9]+(-[a-z0-9]+)*$",
    "hash-segment": "path segment a#b does not match ^[a-z0-9]+(-[a-z0-9]+)*$",
    "parameter-underscores": "path parameter {a__b_} is not snake_case",
    "single-quoted-path": "single-quoted path key is not a path",
    "extension-key": "x- key under paths is not a path",
    "paths-comment": "comment after paths: is not read",
    "url-comment": "comment after a servers URL is not read",
    "duplicate-one": "path is duplicated in public.yaml",
    "non-path-key": "summary under paths is not a path",
    "paths-anchor": "anchor is not accepted",
    "subdirectory": "subdirectory is not a contract file",
    "servers-under-operation": "servers key under a path is not the document servers",
}

_ACTION_PIN = re.compile(
    r"uses:\s*lx-software-ltd/actions/([A-Za-z0-9_.-]+)@([0-9a-f]{40})"
)


def _git_ok(args: list[str]) -> bool:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, check=False)
    return result.returncode == 0


def _commit_has_action(sha: str, directory: str, fetched: set[str]) -> bool:
    """True when ``directory/action.yml`` exists at ``sha``.

    A pull-request checkout is shallow, so a pin on main is fetched once
    before the missing path is treated as a failure.
    """
    spec = f"{sha}:{directory}/action.yml"
    if _git_ok(["git", "cat-file", "-e", spec]):
        return True
    if sha not in fetched:
        fetched.add(sha)
        _git_ok(["git", "fetch", "--depth=1", "origin", sha])
    return _git_ok(["git", "cat-file", "-e", spec])


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

    def test_the_legacy_file_may_sit_in_the_contract_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for item in (FIXTURES / "pass").iterdir():
                if item.is_file():
                    shutil.copy(item, root / item.name)
            legacy = root / "legacy-paths.txt"
            shutil.copy(FIXTURES / "legacy-paths.txt", legacy)
            self.assertEqual(_check(root, legacy), [])
            (root / "notes.txt").write_text("extra\n", encoding="utf-8")
            findings = _check(root, legacy)
            self.assertEqual(
                findings,
                [
                    "notes.txt: file is not public.yaml, admin.yaml, "
                    "partner.yaml, or webhooks.yaml"
                ],
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

    def test_a_ref_and_a_schema_property_named_paths_or_servers_parse(self) -> None:
        directory = FIXTURES / "refs"
        text = (directory / "public.yaml").read_text(encoding="utf-8")
        servers, paths, reader_findings = check_module.read_openapi(text)
        self.assertEqual(reader_findings, [])
        self.assertEqual(servers, [ORIGIN])
        self.assertEqual(paths, ["/v1/public/items/{item_id}"])
        self.assertEqual(_check(directory), [])

    def test_reader_misses_are_not_called_flow_style(self) -> None:
        expectations = {
            "non-path-key": [
                "public.yaml: line 8: summary under paths is not a path",
                "public.yaml: line 9: widgets under paths is not a path",
                "public.yaml: line 10: note under paths is not a path",
            ],
            "paths-anchor": ["public.yaml: line 7: anchor is not accepted"],
            "subdirectory": ["nested: subdirectory is not a contract file"],
            "servers-under-operation": [
                "public.yaml: line 10: servers key under a path is not the document servers"
            ],
        }
        for name, expected in expectations.items():
            with self.subTest(name=name):
                findings = _check(FIXTURES / "fail" / name)
                self.assertEqual(findings, expected)
                self.assertFalse(any("flow-style" in finding for finding in findings))

    def test_a_legacy_path_skips_prefix_segment_and_parameter_rules(self) -> None:
        directory = FIXTURES / "fail" / "proxy-legacy"
        legacy = directory / "legacy-paths.txt"
        listed = _check(directory, legacy)
        self.assertEqual(
            listed,
            [
                "public.yaml: /v1/public/{proxy+}: {proxy+} is not allowed "
                "without an authorizer"
            ],
        )
        unlisted = _check(directory)
        self.assertTrue(
            any(
                "/v1/Kept/items/{grantId} does not start with /v1/public/" in finding
                for finding in unlisted
            ),
            unlisted,
        )
        self.assertTrue(
            any(
                "path segment Kept has an upper-case letter" in finding
                for finding in unlisted
            ),
            unlisted,
        )
        self.assertTrue(
            any(
                "path parameter {grantId} is not snake_case" in finding
                for finding in unlisted
            ),
            unlisted,
        )

    def test_a_legacy_proxy_outside_partner_and_admin_still_fails(self) -> None:
        cases = (
            ("proxy-public", "/v1/public/{proxy+}"),
            ("proxy-webhooks", "/v1/webhooks/{proxy+}"),
        )
        for name, path in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    source = FIXTURES / "fail" / name
                    for item in source.iterdir():
                        if item.is_file():
                            shutil.copy(item, root / item.name)
                    legacy = root / "legacy-paths.txt"
                    legacy.write_text(f"{path}\n", encoding="utf-8")
                    findings = _check(root, legacy)
                    filename = next(
                        item.name for item in source.iterdir() if item.suffix == ".yaml"
                    )
                    self.assertIn(
                        f"{filename}: {path}: {{proxy+}} is not allowed without an authorizer",
                        findings,
                    )
                    self.assertFalse(
                        any("flow-style" in finding for finding in findings),
                        findings,
                    )

    def test_a_path_duplicated_in_one_file_names_that_file(self) -> None:
        findings = _check(FIXTURES / "fail" / "duplicate-one")
        self.assertIn(
            "/v1/public/items: path is duplicated in public.yaml",
            findings,
        )
        self.assertFalse(any("more than one file" in finding for finding in findings))

    def test_a_stale_legacy_path_is_reported(self) -> None:
        findings = _check(FIXTURES / "pass", FIXTURES / "fail" / "stale-legacy.txt")
        self.assertEqual(
            findings,
            ["/v1/public/missing: legacy path is not in a contract file"],
        )

    def test_an_admin_prefix_without_a_trailing_slash_fails(self) -> None:
        findings = check_module.check(
            FIXTURES / "pass",
            origin=ORIGIN,
            admin_prefixes=("/v1/admin", "/v1/user/"),
            legacy_file=FIXTURES / "legacy-paths.txt",
        )
        self.assertTrue(
            any(
                "admin prefix /v1/admin does not match ^/v1/[a-z0-9-]+/$" in finding
                for finding in findings
            ),
            findings,
        )

    def test_an_origin_outside_the_pattern_fails(self) -> None:
        findings = check_module.check(
            FIXTURES / "pass",
            origin="https://api.example.com/v1",
            admin_prefixes=PREFIXES,
            legacy_file=FIXTURES / "legacy-paths.txt",
        )
        self.assertTrue(
            any(
                "origin https://api.example.com/v1 does not match ^https://[a-z0-9.-]+$"
                in finding
                for finding in findings
            ),
            findings,
        )

    def test_lint_template_omits_the_action_until_it_is_on_main(self) -> None:
        text = (ROOT / "templates" / "workflows" / "lint.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("npx --yes @redocly/cli@1.34.11 lint docs/api/*.yaml", text)
        self.assertNotIn("lx-software-ltd/actions/api-contract@", text)

    def test_template_pins_point_at_an_action_file(self) -> None:
        missing: list[str] = []
        fetched: set[str] = set()
        for path in sorted((ROOT / "templates").rglob("*.yml")):
            text = path.read_text(encoding="utf-8")
            for match in _ACTION_PIN.finditer(text):
                directory, sha = match.group(1), match.group(2)
                if _commit_has_action(sha, directory, fetched):
                    continue
                relative = path.relative_to(ROOT)
                missing.append(f"{relative}: {directory}@{sha}")
        self.assertEqual(missing, [])
