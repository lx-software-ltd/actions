"""Contracts the layout check does not cover.

The layout check already requires the SHA comment, the shell, and the
README. These tests cover the inputs that keep an extraction
behaviour-preserving, and that each action has a fail fixture.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _inputs(text: str) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    in_inputs = False
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("inputs:"):
            in_inputs = True
            continue
        if in_inputs and line.startswith("runs:"):
            break
        if not in_inputs:
            continue
        name = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if name:
            current = name.group(1)
            found[current] = {}
            continue
        field = re.match(r"^    (required|default): (.*)$", line)
        if field and current is not None:
            found[current][field.group(1)] = field.group(2).strip()
    return found


def _steps(text: str) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    in_steps = False
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if re.match(r"^  steps:\s*$", line):
            in_steps = True
            continue
        if not in_steps:
            continue
        if line.startswith("    - "):
            current = {"raw": line}
            steps.append(current)
            rest = line[6:]
            if ":" in rest:
                key, value = rest.split(":", 1)
                current[key.strip()] = value.strip()
            continue
        if current is None:
            continue
        current["raw"] += "\n" + line
        field = re.match(r"^      ([A-Za-z0-9_-]+): (.*)$", line)
        if field:
            current[field.group(1)] = field.group(2).strip()
    return steps


class SetupNodeContractTest(unittest.TestCase):
    def test_cache_and_working_directory_are_optional(self) -> None:
        inputs = _inputs(_text("setup-node/action.yml"))
        self.assertEqual(inputs["node-version"]["default"], '"26"')
        self.assertEqual(inputs["working-directory"]["required"], "false")
        self.assertEqual(inputs["working-directory"]["default"], '""')
        self.assertEqual(inputs["cache"]["required"], "false")
        self.assertEqual(inputs["cache"]["default"], '""')
        self.assertEqual(inputs["install"]["default"], '"true"')

    def test_cache_and_install_are_conditional(self) -> None:
        steps = _steps(_text("setup-node/action.yml"))
        cached = next(
            step for step in steps if step.get("if") == "inputs.cache == 'npm'"
        )
        plain = next(step for step in steps if step.get("if") == "inputs.cache == ''")
        rejected = next(
            step for step in steps if "unknown cache" in step.get("name", "")
        )
        install = next(step for step in steps if "npm ci" in step.get("run", ""))
        self.assertIn("cache: npm", cached["raw"])
        self.assertIn("cache-dependency-path", cached["raw"])
        self.assertNotIn("cache-dependency-path", plain["raw"])
        self.assertEqual(rejected["if"], "inputs.cache != '' && inputs.cache != 'npm'")
        self.assertIn("exit 1", rejected["raw"])
        self.assertEqual(
            install["if"],
            "inputs.install == 'true' && inputs.working-directory != ''",
        )
        self.assertIn("npm ci --no-audit --no-fund", install["run"])

    def test_fail_fixture_has_no_lockfile(self) -> None:
        directory = ROOT / "fixtures/setup-node-no-lock"
        self.assertTrue((directory / "package.json").is_file())
        self.assertFalse((directory / "package-lock.json").exists())


class FlutterLockfilesContractTest(unittest.TestCase):
    def test_flutter_version_defaults_to_the_shared_sdk(self) -> None:
        inputs = _inputs(_text("flutter-lockfiles/action.yml"))
        self.assertEqual(inputs["flutter-version"]["required"], "false")
        self.assertEqual(inputs["flutter-version"]["default"], '"3.50.1"')
        steps = _steps(_text("flutter-lockfiles/action.yml"))
        rejected = next(
            step for step in steps if "flutter-version ==" in step.get("if", "")
        )
        self.assertIn("exit 1", rejected["raw"])


class SetupPythonContractTest(unittest.TestCase):
    def test_producer_workflows_pin_python_3_12(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        for path in sorted(workflows.glob("*.yml")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                if "uses: actions/setup-python@" not in line:
                    continue
                window = "\n".join(lines[index : index + 4])
                self.assertIn(
                    'python-version: "3.12"',
                    window,
                    f"{path.name} calls actions/setup-python without Python 3.12",
                )

    def test_requirements_gate_the_cache(self) -> None:
        inputs = _inputs(_text("setup-python/action.yml"))
        self.assertEqual(inputs["python-version"]["default"], '"3.12"')
        self.assertEqual(inputs["requirements"]["required"], "false")
        self.assertEqual(inputs["requirements"]["default"], '""')
        steps = _steps(_text("setup-python/action.yml"))
        cached = next(step for step in steps if "requirements !=" in step.get("if", ""))
        plain = next(step for step in steps if "requirements ==" in step.get("if", ""))
        self.assertIn("cache-dependency-path", cached["raw"])
        self.assertNotIn("cache-dependency-path", plain["raw"])


class FixtureWorkflowTest(unittest.TestCase):
    def test_each_action_has_a_passing_and_a_failing_job(self) -> None:
        text = _text(".github/workflows/test.yml")
        for job in (
            "setup-node-fixture:",
            "setup-node-fail:",
            "setup-node-unknown-cache:",
            "setup-python-fixture:",
            "setup-python-fail:",
            "sync-labels-pass:",
            "sync-labels-fail:",
            "pii-denylist-pass:",
            "pii-denylist-fail:",
            "gitleaks-pass:",
            "gitleaks-fail:",
            "semgrep-lib-path:",
            "semgrep-fail:",
            "node-lockfiles-pass:",
            "node-lockfiles-fail:",
            "python-requirements-pass:",
            "python-requirements-fail:",
            "flutter-lockfiles-pass:",
            "flutter-lockfiles-fail:",
            "pod-lockfiles-pass:",
            "pod-lockfiles-fail:",
            "agent-harness-pass:",
            "agent-harness-fail:",
            "flutter-version-fail:",
            "pip-audit-fail:",
            "bandit-fail:",
            "npm-audit-fail:",
            "playwright-fail:",
            "aws-oidc-skip:",
            "aws-oidc-fail:",
            "cdk-bootstrap-pass:",
            "cdk-bootstrap-fail:",
            "cdk-bootstrap-action-pass:",
            "cdk-bootstrap-action-fail:",
            "cdk-diff-pass:",
            "cdk-diff-fail:",
            "cdk-omitted-parameter:",
            "cfn-stack-outputs-pass:",
            "cfn-stack-outputs-fail:",
            "cfn-stack-outputs-missing:",
            "s3-cloudfront-pass:",
            "s3-cloudfront-fail:",
            "ios-export-pass:",
            "ios-export-fail:",
            "appstore-key-pass:",
            "appstore-key-fail:",
            "android-signing-pass:",
            "android-signing-fail:",
            "play-prerequisites-pass:",
            "play-prerequisites-skip:",
            "cdk-deploy-pass:",
            "cdk-deploy-fail:",
            "setup-flutter-pass:",
            "setup-flutter-fail:",
            "lighthouse-pass:",
            "lighthouse-fail:",
            "dependency-submission-pass:",
            "dependency-submission-fail:",
            "api-contract-pass:",
            "api-contract-fail:",
        ):
            self.assertIn(job, text)
        self.assertEqual(text.count("continue-on-error: true"), 35)
        self.assertEqual(text.count('test "$OUTCOME" = "failure"'), 34)


if __name__ == "__main__":
    unittest.main()
