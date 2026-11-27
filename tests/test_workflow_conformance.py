"""Warn reports a bad pin and still exits 0. Enforce exits 1."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "workflow-conformance" / "check_workflows.py"
_SPEC = importlib.util.spec_from_file_location("check_workflows", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)


def _repo(directory: Path, lint: str) -> None:
    workflows = directory / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "lint.yml").write_text(lint, encoding="utf-8")
    (workflows / "test.yml").write_text(
        textwrap.dedent(
            """\
            name: Test
            on:
              pull_request:
            permissions:
              contents: read
            jobs:
              test:
                runs-on: ubuntu-26.04
                steps:
                  - run: "true"
            """
        ),
        encoding="utf-8",
    )


class WorkflowConformanceTest(unittest.TestCase):
    def test_enforce_fails_on_a_tag_pin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _repo(
                root,
                textwrap.dedent(
                    """\
                    name: Lint
                    on:
                      pull_request:
                    permissions:
                      contents: read
                    jobs:
                      lint:
                        runs-on: ubuntu-26.04
                        steps:
                          - uses: actions/checkout@v7
                    """
                ),
            )
            self.assertTrue(
                any("not pinned" in item for item in checker.findings(root))
            )
            completed = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={"CONFORMANCE_MODE": "warn", "PATH": "/usr/bin:/bin"},
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            completed = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={"CONFORMANCE_MODE": "enforce", "PATH": "/usr/bin:/bin"},
                check=False,
            )
            self.assertEqual(completed.returncode, 1)

    def test_this_repository_passes_the_producer_profile(self) -> None:
        self.assertEqual(checker.findings(ROOT, "producer"), [])

    def test_paths_ignore_is_a_path_filter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _repo(
                root,
                textwrap.dedent(
                    """\
                    name: Lint
                    on:
                      pull_request:
                        paths-ignore:
                          - docs/**
                    permissions:
                      contents: read
                    jobs:
                      lint:
                        runs-on: ubuntu-26.04
                        steps:
                          - run: "true"
                    """
                ),
            )
            self.assertTrue(
                any(
                    "path filter" in item for item in checker.findings(root, "producer")
                )
            )

    def test_an_unpinned_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _repo(
                root,
                textwrap.dedent(
                    """\
                    name: Lint
                    on:
                      pull_request:
                    permissions:
                      contents: read
                    jobs:
                      lint:
                        runs-on: ubuntu-26.04
                        container:
                          image: semgrep/semgrep
                        steps:
                          - run: "true"
                    """
                ),
            )
            self.assertTrue(
                any(
                    "not pinned by digest" in item
                    for item in checker.findings(root, "producer")
                )
            )

    def test_a_gate_must_wait_for_every_job_and_pin_require_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            lint = (root / ".github" / "workflows" / "lint.yml").read_text(
                encoding="utf-8"
            )
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace("    if: always()\n", ""),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("if: always()" in item for item in found), found)
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace("      - lint-python\n", ""),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("needs" in item for item in found), found)
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace(
                    f"lx-software-ltd/actions/require-jobs@{REQUIRE}", "./require-jobs"
                ),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("require-jobs" in item for item in found), found)

    def test_a_gate_reads_needs_around_a_value_block_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            found = checker.findings(root, "producer")
            self.assertFalse(any("needs" in item for item in found), found)
            lint = (root / ".github" / "workflows" / "lint.yml").read_text(
                encoding="utf-8"
            )
            self.assertIn("# template:set", lint)
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace("      - lint-python\n", "          example-field: example-value\n"),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("needs nothing" in item for item in found), found)

    def test_an_empty_with_block_is_null(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            lint = (root / ".github" / "workflows" / "lint.yml").read_text(
                encoding="utf-8"
            )
            lint = lint.replace(
                '      - run: "true"\n',
                "      - uses: lx-software-ltd/actions/setup-python@"
                + REQUIRE
                + " # main 2026-11-20\n"
                + "        with:\n"
                + "          # template:set\n"
                + "          # template:end\n",
            )
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint, encoding="utf-8"
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("with: has no value" in item for item in found), found)

    def test_pre_commit_rev_stays_inside_the_actions_block(self) -> None:
        text = textwrap.dedent(
            """\
            repos:
              - repo: https://github.com/lx-software-ltd/actions
                hooks:
                  - id: check-pii
              - repo: https://github.com/pre-commit/pre-commit-hooks
                rev: v5.0.0
            """
        )
        found, revs = checker._pre_commit_actions_revs(text)
        self.assertTrue(found)
        self.assertEqual(revs, [""])

    def test_an_actions_pin_needs_a_main_date_comment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            lint = (root / ".github" / "workflows" / "lint.yml").read_text(
                encoding="utf-8"
            )
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace(" # main 2026-11-20", " # sa-501 2026-11-22"),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("# main YYYY-MM-DD" in item for item in found), found)

    def test_statuses_permission_is_not_an_action_use(self) -> None:
        self.assertIsNone(checker._uses("  statuses: write"))
        self.assertIsNone(checker._uses('  "statuses": write'))
        self.assertIsNone(
            checker._uses("permissions: {contents: read, statuses: write}")
        )
        self.assertEqual(
            checker._uses("        uses: actions/checkout@v4"), "actions/checkout@v4"
        )
        self.assertEqual(
            checker._uses("      - uses: actions/checkout@v4"), "actions/checkout@v4"
        )

    def test_top_level_write_permission_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            lint = (root / ".github" / "workflows" / "lint.yml").read_text(
                encoding="utf-8"
            )
            (root / ".github" / "workflows" / "lint.yml").write_text(
                lint.replace("  contents: read\n", "  contents: write\n"),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(any("contents: read" in item for item in found), found)

    def test_security_path_filter_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            security = (root / ".github" / "workflows" / "security.yml").read_text(
                encoding="utf-8"
            )
            (root / ".github" / "workflows" / "security.yml").write_text(
                security.replace(
                    "pull_request:\n", "pull_request:\n    paths:\n      - src/**\n"
                ),
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(
                any(
                    "security.yml: pull_request has a path filter" in item
                    for item in found
                ),
                found,
            )

    def test_product_profile_requires_the_target_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            found = checker.findings(root, "product")
            self.assertTrue(any("missing job checkov" in item for item in found), found)
            self.assertTrue(any("missing job semgrep" in item for item in found), found)
            self.assertTrue(
                any("missing job node-lockfiles" in item for item in found), found
            )
            self.assertTrue(
                any("missing job python-requirements" in item for item in found), found
            )

    def test_a_separate_semgrep_workflow_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            (root / ".github" / "workflows" / "semgrep.yml").write_text(
                "name: Semgrep\non:\n  pull_request:\npermissions:\n  contents: read\njobs:\n"
                "  semgrep:\n    runs-on: ubuntu-26.04\n    steps:\n      - run: 'true'\n",
                encoding="utf-8",
            )
            found = checker.findings(root, "producer")
            self.assertTrue(
                any("semgrep.yml" in item and "gate" in item for item in found),
                found,
            )

    def test_semgrep_must_keep_the_display_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            workflows = root / ".github" / "workflows"
            _write_product_security(
                workflows / "security.yml",
                [
                    "checkov",
                    "codeql",
                    "pii-denylist",
                    "secrets-scan",
                    "dependency-audit",
                    "bandit",
                    "npm-audit",
                    "semgrep",
                ],
            )
            text = (workflows / "security.yml").read_text(encoding="utf-8")
            (workflows / "security.yml").write_text(
                text.replace("name: semgrep/ci\n", "name: other\n"),
                encoding="utf-8",
            )
            _add_lockfile_jobs(workflows / "lint.yml")
            found = checker.findings(root, "product")
            self.assertTrue(
                any("must be named semgrep/ci" in item for item in found), found
            )

    def test_templates_fold_lockfiles_and_semgrep_under_the_gates(self) -> None:
        workflows = ROOT / "templates" / "workflows"
        self.assertFalse((workflows / "semgrep.yml").is_file())
        self.assertFalse((workflows / "check-lockfiles.yml").is_file())
        security = (workflows / "security.yml").read_text(encoding="utf-8")
        self.assertNotIn("dependabot[bot]", security)
        jobs = checker._jobs(security)
        self.assertEqual(checker._job_name("semgrep", jobs["semgrep"]), "semgrep/ci")
        self.assertIn("semgrep", checker._needs(jobs["security-summary"]))
        lint_jobs = checker._jobs((workflows / "lint.yml").read_text(encoding="utf-8"))
        for job in (
            "node-lockfiles",
            "python-requirements",
            "flutter-lockfiles",
            "ios-lockfiles",
        ):
            self.assertIn(job, lint_jobs)

    def test_alignment_checks_warn_and_do_not_fail_enforce(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            pin = REQUIRE
            workflows = root / ".github" / "workflows"
            jobs = [
                "checkov",
                "codeql",
                "pii-denylist",
                "secrets-scan",
                "dependency-audit",
                "bandit",
                "npm-audit",
                "semgrep",
            ]
            _write_product_security(workflows / "security.yml", jobs)
            _add_lockfile_jobs(workflows / "lint.yml")
            (workflows / "deploy-backend.yml").write_text(
                "name: Deploy\non:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs:\n"
                "  deploy:\n    runs-on: ubuntu-26.04\n    steps:\n"
                f"      - uses: actions/setup-node@{pin} # v4\n"
                f"      - uses: lx-software-ltd/actions/cdk-deploy@{pin} # main 2026-11-24\n"
                "        with:\n          plan-file: backend/infrastructure/cdk-plan.json\n"
                "      - run: aws cloudformation describe-stacks\n",
                encoding="utf-8",
            )
            (workflows / "cdk-diff.yml").write_text(
                "name: Diff\non:\n  pull_request:\npermissions:\n  contents: read\njobs:\n"
                "  diff:\n    runs-on: ubuntu-26.04\n    steps:\n"
                f"      - uses: lx-software-ltd/actions/cdk-diff@{pin} # main 2026-11-24\n",
                encoding="utf-8",
            )
            (workflows / "import-legacy-crm.yml").write_text(
                "name: Import\non:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs:\n"
                "  import:\n    runs-on: ubuntu-26.04\n    steps:\n"
                "      - run: aws cloudformation describe-stacks\n",
                encoding="utf-8",
            )
            advised = checker.advisory_findings(root)
            self.assertTrue(any("setup-node" in item for item in advised), advised)
            self.assertTrue(any("describe-stacks" in item for item in advised), advised)
            self.assertTrue(
                any(
                    "import-legacy-crm" in item and "describe-stacks" in item
                    for item in advised
                ),
                advised,
            )
            self.assertTrue(any("same plan file" in item for item in advised), advised)
            completed = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={
                    "CONFORMANCE_MODE": "enforce",
                    "CONFORMANCE_PROFILE": "product",
                    "CONFORMANCE_ALIGNMENT": "warn",
                    "CONFORMANCE_TEMPLATES": "off",
                    "PATH": "/usr/bin:/bin",
                },
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("::warning::", completed.stderr)
            defaulted = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={
                    "CONFORMANCE_MODE": "enforce",
                    "CONFORMANCE_PROFILE": "product",
                    "CONFORMANCE_TEMPLATES": "off",
                    "PATH": "/usr/bin:/bin",
                },
                check=False,
            )
            self.assertEqual(defaulted.returncode, 1, defaulted.stderr)
            self.assertIn("setup-node", defaulted.stderr)
            enforced = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={
                    "CONFORMANCE_MODE": "enforce",
                    "CONFORMANCE_PROFILE": "product",
                    "CONFORMANCE_ALIGNMENT": "enforce",
                    "CONFORMANCE_TEMPLATES": "off",
                    "PATH": "/usr/bin:/bin",
                },
                check=False,
            )
            self.assertEqual(enforced.returncode, 1, enforced.stderr)
            self.assertIn("same plan file", enforced.stderr)

    def test_plan_values_keep_expressions_and_inline_json(self) -> None:
        pin = "a" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "deploy.yml").write_text(
                "jobs:\n  deploy:\n    steps:\n"
                f'      - uses: "actions/setup-node@{pin}"\n'
                f"      - uses: lx-software-ltd/actions/cdk-deploy@{pin}\n"
                "        with:\n"
                "          plan-file: ${{ runner.temp }}/cdk-plan.json\n",
                encoding="utf-8",
            )
            (workflows / "diff.yml").write_text(
                "jobs:\n  diff:\n    steps:\n"
                f"      - uses: lx-software-ltd/actions/cdk-diff@{pin}\n"
                "        with:\n"
                "          plan-file: ${{ runner.temp }}/other.json # kept\n",
                encoding="utf-8",
            )
            advised = checker.advisory_findings(root)
            self.assertTrue(any("setup-node" in item for item in advised), advised)
            plan = [item for item in advised if "same plan file" in item]
            self.assertEqual(len(plan), 1, advised)
            self.assertIn("${{ runner.temp }}/cdk-plan.json", plan[0])
            self.assertIn("${{ runner.temp }}/other.json", plan[0])
            (workflows / "diff.yml").write_text(
                "jobs:\n  diff:\n    steps:\n"
                f"      - uses: lx-software-ltd/actions/cdk-diff@{pin}\n"
                "        with:\n"
                "          plan-file: ${{ runner.temp }}/cdk-plan.json\n",
                encoding="utf-8",
            )
            matched = checker.advisory_findings(root)
            self.assertFalse(any("same plan file" in item for item in matched), matched)
            (workflows / "deploy.yml").write_text(
                "jobs:\n  deploy:\n    steps:\n"
                f"      - uses: lx-software-ltd/actions/cdk-deploy@{pin}\n"
                "        with:\n"
                "          plan: |\n"
                '            {"id":"one"}\n',
                encoding="utf-8",
            )
            (workflows / "diff.yml").write_text(
                "jobs:\n  diff:\n    steps:\n"
                f"      - uses: lx-software-ltd/actions/cdk-diff@{pin}\n"
                "        with:\n"
                "          plan: |\n"
                '            {"id":"two"}\n',
                encoding="utf-8",
            )
            blocked = checker.advisory_findings(root)
            body = [item for item in blocked if "same plan file" in item]
            self.assertEqual(len(body), 1, blocked)
            self.assertIn('{"id":"one"}', body[0])
            self.assertIn('{"id":"two"}', body[0])
            (workflows / "diff.yml").write_text(
                "jobs:\n  diff:\n    steps:\n"
                f"      - uses: lx-software-ltd/actions/cdk-diff@{pin}\n"
                "        with:\n"
                '          plan: \'{"id":"one"}\'\n',
                encoding="utf-8",
            )
            same = checker.advisory_findings(root)
            self.assertFalse(any("same plan file" in item for item in same), same)

    def test_a_name_before_uses_still_reads_the_plan(self) -> None:
        pin = "b" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)

            def write(name: str, body: str) -> None:
                (workflows / name).write_text(body, encoding="utf-8")

            write(
                "uses-first.yml",
                "jobs:\n  job:\n    steps:\n"
                f"      - uses: lx-software-ltd/actions/cdk-deploy@{pin}\n"
                "        with:\n"
                "          plan-file: two.json\n"
                f"      - uses: lx-software-ltd/actions/cdk-diff@{pin}\n"
                "        with:\n"
                "          plan-file: two.json\n",
            )
            advised = checker.advisory_findings(root)
            self.assertFalse(any("same plan file" in item for item in advised), advised)
            write(
                "name-first.yml",
                "jobs:\n  job:\n    steps:\n"
                "      - name: Deploy\n"
                f"        uses: lx-software-ltd/actions/cdk-deploy@{pin}\n"
                "        with:\n"
                "          plan-file: two.json\n"
                "      - name: Diff\n"
                f"        uses: lx-software-ltd/actions/cdk-diff@{pin}\n"
                "        with:\n"
                "          plan-file: other.json\n",
            )
            named = checker.advisory_findings(root)
            mismatch = [item for item in named if "same plan file" in item]
            self.assertEqual(len(mismatch), 1, named)
            self.assertIn("file:two.json", mismatch[0])
            self.assertIn("file:other.json", mismatch[0])
            write(
                "name-first.yml",
                "jobs:\n  job:\n    steps:\n"
                "      - name: Deploy\n"
                f"        uses: lx-software-ltd/actions/cdk-deploy@{pin}\n"
                "        with:\n"
                "          plan-file: two.json\n"
                "      - name: Diff\n"
                f"        uses: lx-software-ltd/actions/cdk-diff@{pin}\n"
                "        with:\n"
                "          plan-file: two.json\n",
            )
            matched = checker.advisory_findings(root)
            self.assertFalse(any("same plan file" in item for item in matched), matched)


class TemplateComparisonTest(unittest.TestCase):
    def test_marked_lines_and_an_omitted_block_pass(self) -> None:
        template = textwrap.dedent(
            """\
            name: Check
            on:
              pull_request:
            jobs:
            # template:optional flutter-lockfiles
              flutter-lockfiles:
                with:
            # template:set
                  working-directory: apps/example
            # template:end
            # template:end
              node-lockfiles:
                uses: lx-software-ltd/actions/node-lockfiles@ACTIONS_PIN # main DATE
                with:
            # template:set
                  directories: |
                    apps/admin_web
            # template:end
            """
        )
        web = textwrap.dedent(
            """\
            name: Check
            on:
              pull_request:
            jobs:
              node-lockfiles:
                uses: lx-software-ltd/actions/node-lockfiles@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa # main 2026-11-24
                with:
            # template:set
                  directories: |
                    apps/public_www
            # template:end
            """
        )
        self.assertEqual(
            checker.compare_template("check-lockfiles.yml", template, web), []
        )
        mobile = web.replace(
            "jobs:\n",
            "jobs:\n"
            "# template:optional flutter-lockfiles\n"
            "  flutter-lockfiles:\n"
            "    with:\n"
            "# template:set\n"
            "      working-directory: apps/mobile\n"
            "# template:end\n"
            "# template:end\n",
        )
        self.assertEqual(
            checker.compare_template("check-lockfiles.yml", template, mobile), []
        )

    def test_a_change_outside_marked_lines_fails(self) -> None:
        template = "name: Check\njobs:\n  node:\n    runs-on: ubuntu-26.04\n"
        product = "name: Check\njobs:\n  node:\n    runs-on: ubuntu-24.04\n"
        found = checker.compare_template("check-lockfiles.yml", template, product)
        self.assertTrue(any("ubuntu-24.04" in item for item in found), found)

    def test_an_optional_block_cannot_change_its_unmarked_lines(self) -> None:
        template = textwrap.dedent(
            """\
            jobs:
            # template:optional flutter-lockfiles
              flutter-lockfiles:
                runs-on: ubuntu-26.04
            # template:end
              node:
                runs-on: ubuntu-26.04
            """
        )
        product = template.replace(
            "flutter-lockfiles:\n    runs-on: ubuntu-26.04",
            "flutter-lockfiles:\n    runs-on: macos-26",
        )
        found = checker.compare_template("check-lockfiles.yml", template, product)
        self.assertTrue(
            any("optional flutter-lockfiles" in item for item in found), found
        )

    def test_warn_passes_and_enforce_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            workflows = root / ".github" / "workflows"
            jobs = [
                "checkov",
                "codeql",
                "pii-denylist",
                "secrets-scan",
                "dependency-audit",
                "bandit",
                "npm-audit",
                "semgrep",
            ]
            _write_product_security(workflows / "security.yml", jobs)
            _add_lockfile_jobs(workflows / "lint.yml")
            templates = root / "templates"
            templates.mkdir()
            (templates / "extra.yml").write_text("name: Extra\n", encoding="utf-8")
            warned = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={
                    "CONFORMANCE_MODE": "enforce",
                    "CONFORMANCE_PROFILE": "product",
                    "CONFORMANCE_ALIGNMENT": "warn",
                    "CONFORMANCE_TEMPLATES": "warn",
                    "CONFORMANCE_TEMPLATE_DIR": str(templates),
                    "PATH": "/usr/bin:/bin",
                },
                check=False,
            )
            self.assertEqual(warned.returncode, 0, warned.stderr)
            self.assertIn("extra.yml", warned.stderr)
            self.assertIn("::warning::", warned.stderr)
            enforced = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={
                    "CONFORMANCE_MODE": "enforce",
                    "CONFORMANCE_PROFILE": "product",
                    "CONFORMANCE_ALIGNMENT": "warn",
                    "CONFORMANCE_TEMPLATES": "enforce",
                    "CONFORMANCE_TEMPLATE_DIR": str(templates),
                    "PATH": "/usr/bin:/bin",
                },
                check=False,
            )
            self.assertEqual(enforced.returncode, 1, enforced.stderr)
            self.assertIn("extra.yml", enforced.stderr)
            defaulted = subprocess.run(
                ["python3", str(_PATH)],
                cwd=root,
                capture_output=True,
                text=True,
                env={
                    "CONFORMANCE_MODE": "enforce",
                    "CONFORMANCE_PROFILE": "product",
                    "CONFORMANCE_ALIGNMENT": "warn",
                    "CONFORMANCE_TEMPLATE_DIR": str(templates),
                    "PATH": "/usr/bin:/bin",
                },
                check=False,
            )
            self.assertEqual(defaulted.returncode, 1, defaulted.stderr)
            self.assertIn("extra.yml", defaulted.stderr)

    def test_if_present_allows_a_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _repo(
                root,
                textwrap.dedent(
                    """\
                    name: Lint
                    on:
                      pull_request:
                    permissions:
                      contents: read
                    jobs:
                      lint:
                        runs-on: ubuntu-26.04
                        steps:
                          - run: "true"
                    """
                ),
            )
            templates = root / "templates"
            templates.mkdir()
            (templates / "deploy-ios.yml").write_text(
                "# template:if-present\nname: Deploy iOS\n",
                encoding="utf-8",
            )
            self.assertEqual(
                checker.template_findings(root, templates),
                [],
            )
            present = root / ".github" / "workflows" / "deploy-ios.yml"
            present.write_text("name: Something else\n", encoding="utf-8")
            found = checker.template_findings(root, templates)
            self.assertTrue(any("deploy-ios.yml" in item for item in found))
            (templates / "required.yml").write_text(
                "name: Required\n", encoding="utf-8"
            )
            found = checker.template_findings(root, templates)
            self.assertTrue(
                any(
                    "required.yml: missing the shared workflow" in item
                    for item in found
                )
            )

    def test_sync_labels_template_is_required(self) -> None:
        template = (ROOT / "templates" / "workflows" / "sync-labels.yml").read_text(
            encoding="utf-8"
        )
        self.assertFalse(template.startswith("# template:if-present"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            templates = root / "templates" / "workflows"
            templates.mkdir(parents=True)
            (templates / "sync-labels.yml").write_text(template, encoding="utf-8")
            missing = checker.template_findings(root, templates)
            self.assertEqual(
                missing,
                [".github/workflows/sync-labels.yml: missing the shared workflow"],
            )
            pinned = template.replace("ACTIONS_PIN", "a" * 40).replace(
                "DATE", "2026-11-27"
            )
            (workflows / "sync-labels.yml").write_text(pinned, encoding="utf-8")
            found = checker.template_findings(root, templates)
            self.assertEqual(found, [], found)

    def test_an_indented_marker_is_a_marker(self) -> None:
        template = (
            "jobs:\n  step:\n    with:\n"
            "      # template:set\n      value: one\n      # template:end\n"
        )
        product = (
            "jobs:\n  step:\n    with:\n"
            "# template:set\n      value: two\n# template:end\n"
        )
        self.assertEqual(checker.compare_template("extra.yml", template, product), [])
        moved = product.replace("    with:\n", "    env:\n")
        found = checker.compare_template("extra.yml", template, moved)
        self.assertTrue(any("outside marked lines" in item for item in found), found)

    def test_a_nested_optional_block_can_be_omitted(self) -> None:
        template = (
            "# template:optional outer\n"
            "outer\n"
            "# template:optional inner\n"
            "inner\n"
            "# template:end\n"
            "# template:end\n"
        )
        product = "# template:optional outer\nouter\n# template:end\n"
        self.assertEqual(checker.compare_template("test.yml", template, product), [])

    def test_a_marked_block_cannot_hold_a_step_or_a_skip(self) -> None:
        template = "name: shared\n# template:set\nvalue: one\n# template:end\n"
        product = (
            "name: shared\n# template:set\n"
            "- name: Skip\ncontinue-on-error: true\ntype: choice\noptions:\nneeds:\nif: always()\n"
            "# template:end\n"
        )
        found = checker.compare_template("lint.yml", template, product)
        for snippet in ("- name:", "continue-on-error:", "type:", "options:", "needs:", "if:"):
            self.assertTrue(any(snippet in item for item in found), found)

    def test_a_value_block_cannot_copy_the_template_sample(self) -> None:
        template = "name: shared\n# template:set\nstack: stack-name\n# template:end\n"
        copied = "name: shared\n# template:set\nstack: stack-name\n# template:end\n"
        found = checker.compare_template("deploy-backend.yml", template, copied)
        self.assertTrue(any("copies the template sample" in item for item in found), found)
        own = "name: shared\n# template:set\nstack: evolvesprouts-public-www\n# template:end\n"
        self.assertEqual(checker.compare_template("deploy-backend.yml", template, own), [])
        empty = "name: shared\n# template:set\n# template:end\n"
        blank = "name: shared\n# template:set\n\n# template:end\n"
        self.assertEqual(checker.compare_template("deploy-backend.yml", empty, blank), [])

    def test_a_joined_product_name_is_unmarked_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            templates = root / "templates" / "workflows"
            templates.mkdir(parents=True)
            body = "name: Check\njobs:\n  one:\n    steps:\n      - run: echo evolvesprouts-public-www\n"
            (templates / "lint.yml").write_text(body, encoding="utf-8")
            found = checker.template_findings(root, templates)
            self.assertTrue(any("evolvesprouts-public-www" in item for item in found), found)

    def test_unclosed_marker_is_a_finding(self) -> None:
        found = checker.compare_template(
            "check-lockfiles.yml",
            "# template:set\nvalue: one\n",
            "# template:set\nvalue: two\n",
        )
        self.assertTrue(any("unclosed" in item for item in found), found)


class TemplateContractTest(unittest.TestCase):
    def test_an_optional_id_must_be_a_capability_and_follow_the_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            templates = root / "templates" / "workflows"
            templates.mkdir(parents=True)
            (root / "templates" / "capabilities.json").write_text(
                '{"mobile": "apps/*/pubspec.yaml", "search-fixture": "scripts/codegen/sync-activity-search-staging-fixture.sh"}\n',
                encoding="utf-8",
            )
            (templates / "lint.yml").write_text(
                textwrap.dedent(
                    """\
                    name: Lint
                    jobs:
                    # template:optional not-a-capability
                      extra: true
                    # template:end
                    # template:optional search-fixture
                      first: true
                    # template:end
                    # template:optional search-fixture
                      second: true
                    # template:end
                    """
                ),
                encoding="utf-8",
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "lint.yml").write_text(
                "name: Lint\njobs:\n  kept: true\n",
                encoding="utf-8",
            )
            found = checker.template_findings(root, templates)
            self.assertTrue(
                any("not-a-capability is not a capability" in item for item in found),
                found,
            )
            probe = root / "scripts" / "codegen"
            probe.mkdir(parents=True)
            (probe / "sync-activity-search-staging-fixture.sh").write_text(
                "#!/bin/sh\n", encoding="utf-8"
            )
            found = checker.template_findings(root, templates)
            self.assertTrue(
                any("search-fixture" in item and "block count is 0" in item for item in found),
                found,
            )
            (workflows / "lint.yml").write_text(
                textwrap.dedent(
                    """\
                    name: Lint
                    jobs:
                    # template:optional search-fixture
                      first: true
                    # template:end
                    # template:optional search-fixture
                      second: true
                    # template:end
                    """
                ),
                encoding="utf-8",
            )
            found = checker.template_findings(root, templates)
            self.assertFalse(
                any("search-fixture" in item and "block count" in item for item in found),
                found,
            )
            (probe / "sync-activity-search-staging-fixture.sh").unlink()
            found = checker.template_findings(root, templates)
            self.assertTrue(
                any("probe" in item and "absent" in item for item in found),
                found,
            )
        repeated = checker.compare_template(
            "lint.yml",
            "# template:optional search-fixture\none\n# template:end\n"
            "# template:optional search-fixture\ntwo\n# template:end\n",
            "# template:optional search-fixture\none\n# template:end\n"
            "# template:optional search-fixture\ntwo\n# template:end\n",
        )
        self.assertEqual(repeated, [])

    def test_file_presence_follows_the_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            templates = root / "templates" / "workflows"
            templates.mkdir(parents=True)
            (root / "templates" / "capabilities.json").write_text(
                '{"mobile": "apps/*/pubspec.yaml", "staged-release": "scripts/deploy/deploy-public-www.sh"}\n',
                encoding="utf-8",
            )
            (templates / "deploy-ios.yml").write_text(
                "# template:if-present mobile\nname: Deploy iOS\n",
                encoding="utf-8",
            )
            (templates / "deploy-public-www.yml").write_text(
                "# template:if-present !staged-release\nname: Deploy public\n",
                encoding="utf-8",
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "deploy-ios.yml").write_text(
                "name: Deploy iOS\n", encoding="utf-8"
            )
            found = checker.template_findings(root, templates)
            self.assertTrue(
                any("deploy-ios.yml" in item and "excludes" in item for item in found),
                found,
            )
            (workflows / "deploy-ios.yml").unlink()
            app = root / "apps" / "demo"
            app.mkdir(parents=True)
            (app / "pubspec.yaml").write_text("name: demo\n", encoding="utf-8")
            found = checker.template_findings(root, templates)
            self.assertTrue(
                any("deploy-ios.yml" in item and "requires" in item for item in found),
                found,
            )
            deploy = root / "scripts" / "deploy"
            deploy.mkdir(parents=True)
            (deploy / "deploy-public-www.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (workflows / "deploy-public-www.yml").write_text(
                "name: Deploy public\n", encoding="utf-8"
            )
            found = checker.template_findings(root, templates)
            self.assertTrue(
                any(
                    "deploy-public-www.yml" in item and "excludes" in item
                    for item in found
                ),
                found,
            )

    def test_a_value_block_rejects_run_id_comments_and_single_quotes(self) -> None:
        template = "name: shared\n# template:set\nvalue: one\n# template:end\n"
        product = (
            "name: shared\n# template:set\n"
            "run: echo hi\n"
            "id: aws\n"
            "# note\n"
            "description: 'quoted'\n"
            "# template:end\n"
        )
        found = checker.compare_template("lint.yml", template, product)
        for snippet in ("run: echo hi", "id: aws", "# note", "description: 'quoted'"):
            self.assertTrue(any(snippet in item for item in found), found)

    def test_product_names_stay_out_of_unmarked_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            templates = root / "templates" / "workflows"
            templates.mkdir(parents=True)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            body = (
                "name: Check\n"
                "jobs:\n"
                "  one:\n"
                "    steps:\n"
                "      - run: echo evolvesprouts\n"
                "      - uses: lx-software-ltd/actions/setup-node@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa # main 2026-11-24\n"
                "# template:set\n"
                "      stack: evolvesprouts\n"
                "# template:end\n"
            )
            (templates / "lint.yml").write_text(body, encoding="utf-8")
            (workflows / "lint.yml").write_text(body, encoding="utf-8")
            found = checker.template_findings(root, templates)
            unmarked = [item for item in found if "product name" in item]
            self.assertEqual(len(unmarked), 1, unmarked)
            self.assertIn("echo evolvesprouts", unmarked[0])
            clean = body.replace("echo evolvesprouts", "echo shared")
            (templates / "lint.yml").write_text(clean, encoding="utf-8")
            (workflows / "lint.yml").write_text(clean, encoding="utf-8")
            found = checker.template_findings(root, templates)
            self.assertFalse(any("product name" in item for item in found), found)

    def test_an_untemplated_workflow_must_be_listed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            templates = root / "templates" / "workflows"
            templates.mkdir(parents=True)
            (templates / "lint.yml").write_text("name: Lint\n", encoding="utf-8")
            (root / "templates" / "untemplated-workflows.txt").write_text(
                "evolvesprouts deploy-training.yml\n",
                encoding="utf-8",
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "lint.yml").write_text("name: Lint\n", encoding="utf-8")
            (workflows / "deploy-training.yml").write_text(
                "name: Training\n", encoding="utf-8"
            )
            previous = os.environ.get("CONFORMANCE_REPOSITORY")
            os.environ["CONFORMANCE_REPOSITORY"] = "findingalpha"
            try:
                found = checker.template_findings(root, templates)
            finally:
                if previous is None:
                    os.environ.pop("CONFORMANCE_REPOSITORY", None)
                else:
                    os.environ["CONFORMANCE_REPOSITORY"] = previous
            self.assertTrue(
                any("deploy-training.yml" in item and "untemplated" in item for item in found),
                found,
            )
            os.environ["CONFORMANCE_REPOSITORY"] = "evolvesprouts"
            try:
                found = checker.template_findings(root, templates)
            finally:
                os.environ.pop("CONFORMANCE_REPOSITORY", None)
            self.assertFalse(
                any("deploy-training.yml" in item for item in found),
                found,
            )

    def test_a_path_filter_prefix_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _valid(root)
            (root / "backend").mkdir()
            (root / "backend" / "keep.json").write_text("{}\n", encoding="utf-8")
            (root / ".github" / "workflows" / "cdk-diff.yml").write_text(
                textwrap.dedent(
                    """\
                    name: Diff
                    on:
                      pull_request:
                        paths:
                          - packages/*
                          - "backend/**"
                          - "!backend/keep.json"
                          - "!backend/roadmap.json"
                    permissions:
                      contents: read
                    jobs:
                      diff:
                        runs-on: ubuntu-26.04
                        steps:
                          - run: "true"
                    """
                ),
                encoding="utf-8",
            )
            found = checker.findings(root)
            self.assertTrue(any("packages/*" in item for item in found), found)
            self.assertFalse(any("backend/**" in item for item in found), found)
            self.assertFalse(any("keep.json" in item for item in found), found)
            self.assertTrue(any("!backend/roadmap.json" in item for item in found), found)

    def test_a_listed_directory_without_package_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "apps" / "missing").mkdir(parents=True)
            node = subprocess.run(
                ["bash", str(ROOT / "node-lockfiles" / "check.sh")],
                cwd=root,
                capture_output=True,
                text=True,
                env={**os.environ, "LOCKFILE_DIRECTORIES": "apps/missing"},
                check=False,
            )
            self.assertNotEqual(node.returncode, 0, node.stderr)
            self.assertIn("no package.json", node.stderr)
            audit = subprocess.run(
                ["bash", str(ROOT / "npm-audit" / "run.sh")],
                cwd=root,
                capture_output=True,
                text=True,
                env={**os.environ, "NPM_AUDIT_DIRECTORIES": "apps/missing"},
                check=False,
            )
            self.assertNotEqual(audit.returncode, 0, audit.stderr)
            self.assertIn("no package.json", audit.stderr)


REQUIRE = "1a3cca7c38163f8164c262323601c34a4df5b7a4"


def _valid(directory: Path) -> None:
    workflows = directory / ".github" / "workflows"
    workflows.mkdir(parents=True)
    workflows.joinpath("lint.yml").write_text(
        _gated("Lint", "lint", "lint-python"), encoding="utf-8"
    )
    workflows.joinpath("test.yml").write_text(
        _gated("Test", "test", "unit"), encoding="utf-8"
    )
    workflows.joinpath("security.yml").write_text(
        _gated("Security", "security-summary", "secrets-scan"),
        encoding="utf-8",
    )


def _security_job(job: str) -> str:
    name = "\n    name: semgrep/ci" if job == "semgrep" else ""
    return f"  {job}:{name}\n    runs-on: ubuntu-26.04\n    steps:\n      - run: 'true'"


def _write_product_security(path: Path, jobs: list[str]) -> None:
    needs = "\n".join(f"      - {job}" for job in jobs)
    bodies = "\n".join(_security_job(job) for job in jobs)
    path.write_text(
        "name: Security\non:\n  pull_request:\npermissions:\n  contents: read\njobs:\n"
        + bodies
        + "\n  security-summary:\n    runs-on: ubuntu-26.04\n    needs:\n"
        + needs
        + "\n    if: always()\n    steps:\n"
        + f"      - uses: lx-software-ltd/actions/require-jobs@{REQUIRE} # main 2026-11-20\n",
        encoding="utf-8",
    )


def _add_lockfile_jobs(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "  lint-python:\n",
            "  node-lockfiles:\n"
            "    runs-on: ubuntu-26.04\n"
            "    steps:\n"
            '      - run: "true"\n'
            "  python-requirements:\n"
            "    runs-on: ubuntu-26.04\n"
            "    steps:\n"
            '      - run: "true"\n'
            "  lint-python:\n",
        ).replace(
            "      - lint-python\n",
            "      - lint-python\n"
            "      - node-lockfiles\n"
            "      - python-requirements\n",
        ),
        encoding="utf-8",
    )


def _gated(name: str, gate: str, other: str) -> str:
    return textwrap.dedent(
        f"""\
        name: {name}
        on:
          pull_request:
        permissions:
          contents: read
        jobs:
          {other}:
            runs-on: ubuntu-26.04
            steps:
              - run: "true"
          {gate}:
            runs-on: ubuntu-26.04
            needs:
              # template:set
              - {other}
            # template:end
            if: always()
            steps:
              - uses: lx-software-ltd/actions/require-jobs@{REQUIRE} # main 2026-11-20
        """
    )


if __name__ == "__main__":
    unittest.main()
