"""CDK deploy keeps each repository's parameter and retry rules."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cdk-deploy"))

import cdk_deploy  # noqa: E402


def _ok(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["npx"], returncode=0, stdout=stdout, stderr="")


def _fail(stdout: str = "", code: int = 1) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["npx"], returncode=code, stdout=stdout, stderr="")


class PlanTest(unittest.TestCase):
    def test_prefixed_json_splits_by_prefix_and_rejects_an_unknown_key(self) -> None:
        plan = {
            "groups": [
                {
                    "stacks": ["example", "example-admin"],
                    "prefixes": ["example:", "example-admin:"],
                    "extra-args": ["--parameters", "example:Domain=app.example"],
                },
                {
                    "stacks": ["example-www"],
                    "prefixes": ["example-www:"],
                    "when-all-env": ["WWW_DOMAIN", "WWW_CERT"],
                },
            ]
        }
        parameters = {
            "example:Name": "one",
            "example-admin:Name": 2,
            "example:Blank": "",
            "example:Note": "a\nb",
            "example-www:Name": "www",
        }
        with mock.patch.dict(os.environ, {"WWW_DOMAIN": "", "WWW_CERT": ""}, clear=False):
            commands = cdk_deploy.build_commands(
                plan=plan,
                parameters=parameters,
                fmt="prefixed-json",
                selected_stacks=[],
                pass_empty=set(),
                escape_newlines=False,
                no_notices=False,
                destroy=False,
                run_seed=False,
            )
        argv = commands[0][0]
        self.assertEqual(argv[:5], ["npx", "cdk", "deploy", "--require-approval", "never"])
        self.assertIn("example:Name=one", argv)
        self.assertIn("example-admin:Name=2", argv)
        self.assertIn("example:Note=a\\nb", argv)
        self.assertNotIn("example:Blank=", argv)
        self.assertIn("example:Domain=app.example", argv)
        self.assertEqual(argv[-2:], ["example", "example-admin"])
        self.assertEqual(len(commands), 1)
        plan["unprefixed-prefix"] = "example-www:"
        parameters["Domain"] = "<FROM_GITHUB_SECRET: WWW_CERT>"
        with mock.patch.dict(os.environ, {"WWW_CERT": "cert-value", "WWW_DOMAIN": "www.example"}, clear=False):
            prefixed = cdk_deploy.build_commands(
                plan=plan,
                parameters={"Domain": "<FROM_GITHUB_SECRET: WWW_CERT>"},
                fmt="prefixed-json",
                selected_stacks=["example-www"],
                pass_empty=set(),
                escape_newlines=False,
                no_notices=False,
                destroy=False,
                run_seed=False,
            )
        self.assertIn("example-www:Domain=cert-value", prefixed[0][0])
        parameters["other:Name"] = "no"
        with self.assertRaises(cdk_deploy.DeployError):
            cdk_deploy.build_commands(
                plan=plan,
                parameters=parameters,
                fmt="prefixed-json",
                selected_stacks=[],
                pass_empty=set(),
                escape_newlines=False,
                no_notices=False,
                destroy=False,
                run_seed=False,
            )

    def test_plain_json_routes_placeholders_and_empty_values(self) -> None:
        plan = {
            "api-stack": "api",
            "also-api": ["OriginSecret"],
            "routes": [
                {"stack": "admin", "parameters": ["AdminName", "Waf"], "skip-empty": ["Waf"]},
                {"stack": "www", "parameters": ["WwwName", "Waf", "OriginSecret"]},
                {"stack": "api", "parameters": ["WwwName"]},
            ],
            "groups": [{"stacks": ["api", "admin", "www"]}],
        }
        parameters = {
            "AdminName": "<FROM_GITHUB_SECRET: ADMIN_SECRET>",
            "WwwName": "<FROM_GITHUB_VAR: WWW_VAR>",
            "Waf": "",
            "OriginSecret": "keep",
            "Other": "<NOT_A_PLACEHOLDER>",
            "Missing": "<FROM_GITHUB_SECRET: GONE>",
        }
        env = {
            "ADMIN_SECRET": "secret-value",
            "WWW_VAR": "line1\r\nline2\n",
            "GONE": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            commands = cdk_deploy.build_commands(
                plan=plan,
                parameters=parameters,
                fmt="plain-json",
                selected_stacks=[],
                pass_empty={"Waf"},
                escape_newlines=False,
                no_notices=True,
                destroy=False,
                run_seed=False,
            )
        argv = commands[0][0]
        self.assertIn("--no-notices", argv)
        self.assertIn("admin:AdminName=secret-value", argv)
        self.assertIn("www:WwwName=line1\r\nline2\n", argv)
        self.assertIn("api:WwwName=line1\r\nline2\n", argv)
        self.assertIn("www:Waf=", argv)
        self.assertNotIn("admin:Waf=", argv)
        self.assertIn("www:OriginSecret=keep", argv)
        self.assertIn("api:OriginSecret=keep", argv)
        self.assertIn("api:Other=<NOT_A_PLACEHOLDER>", argv)
        self.assertFalse(any(arg.startswith("api:Missing=") for arg in argv))

    def test_allowlist_stops_the_later_group_without_printing_the_address(self) -> None:
        plan = {
            "groups": [
                {"stacks": ["www"], "prefixes": ["www:"]},
                {
                    "stacks": ["admin"],
                    "prefixes": ["admin:"],
                    "allowlist-env": "ALLOWLIST",
                },
            ]
        }
        with mock.patch.dict(os.environ, {"ALLOWLIST": "not-an-email"}, clear=False):
            commands = cdk_deploy.build_commands(
                plan=plan,
                parameters={"www:Name": "site"},
                fmt="prefixed-json",
                selected_stacks=[],
                pass_empty=set(),
                escape_newlines=False,
                no_notices=False,
                destroy=False,
                run_seed=False,
            )
            calls: list[list[str]] = []

            def run(command: list[str]) -> subprocess.CompletedProcess[str]:
                calls.append(command)
                return _ok()

            with self.assertRaises(cdk_deploy.DeployError) as raised:
                cdk_deploy.run_commands(
                    commands,
                    attempts=1,
                    rollback_match=cdk_deploy.DEFAULT_ROLLBACK,
                    skip_resource="",
                    region="",
                    run=run,
                    sleep=lambda seconds: None,
                )
        self.assertEqual([call[2] for call in calls], ["deploy"])
        self.assertEqual(calls[0][-1], "www")
        self.assertIn("entry 1", str(raised.exception))
        self.assertNotIn("not-an-email", str(raised.exception))

    def test_retry_waits_and_a_fatal_error_does_not(self) -> None:
        calls: list[list[str]] = []
        delays: list[int] = []

        def run(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[2] == "deploy" and len([item for item in calls if item[2:3] == ["deploy"]]) < 3:
                return _fail("account 123456789012 denied")
            return _ok("done")

        code = cdk_deploy.run_commands(
            [(["npx", "cdk", "deploy", "--require-approval", "never", "api"], ["api"])],
            attempts=3,
            rollback_match=cdk_deploy.DEFAULT_ROLLBACK,
            skip_resource="",
            region="",
            run=run,
            sleep=delays.append,
        )
        self.assertEqual(code, 0)
        self.assertEqual(delays, [45, 90])
        fatal = cdk_deploy.run_commands(
            [(["npx", "cdk", "deploy", "--require-approval", "never", "api"], ["api"])],
            attempts=3,
            rollback_match=cdk_deploy.DEFAULT_ROLLBACK,
            skip_resource="",
            region="",
            run=lambda command: _fail('HandlerErrorCode: AlreadyExists'),
            sleep=delays.append,
        )
        self.assertEqual(fatal, 1)
        self.assertEqual(delays, [45, 90])

    def test_rollback_skip_fails_the_job_when_recovery_fails(self) -> None:
        calls: list[list[str]] = []

        def run(command: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[2] == "deploy":
                return _fail("Stack api is in UPDATE_ROLLBACK_FAILED state and can not be updated")
            if command[1:3] == ["cloudformation", "describe-stacks"]:
                return _ok("UPDATE_ROLLBACK_FAILED")
            if command[1:3] == ["cloudformation", "describe-stack-resources"]:
                return _ok("RunMigrations")
            if command[1:3] == ["cloudformation", "describe-stack-events"]:
                return _ok("UPDATE_FAILED\tCan't locate revision")
            if command[1:3] == ["cloudformation", "continue-update-rollback"]:
                return _fail("still wedged")
            return _ok()

        code = cdk_deploy.run_commands(
            [(["npx", "cdk", "deploy", "--require-approval", "never", "api"], ["api"])],
            attempts=3,
            rollback_match=cdk_deploy.DEFAULT_ROLLBACK,
            skip_resource="RunMigrations",
            region="ap-southeast-1",
            run=run,
            sleep=lambda seconds: None,
        )
        self.assertEqual(code, 1)
        rollback = next(call for call in calls if call[1:3] == ["cloudformation", "continue-update-rollback"])
        self.assertIn("--resources-to-skip", rollback)
        self.assertIn("RunMigrations", rollback)
        self.assertIn("ap-southeast-1", rollback)

    def test_destroy_runs_first_and_seed_replaces_the_api_parameter(self) -> None:
        plan = {
            "api-stack": "api",
            "groups": [
                {"stacks": ["www"], "prefixes": ["www:"]},
                {"stacks": ["api"], "prefixes": ["api:"]},
            ],
        }
        commands = cdk_deploy.build_commands(
            plan=plan,
            parameters={"www:Name": "site", "api:RunSeedData": "false", "api:Name": "one"},
            fmt="prefixed-json",
            selected_stacks=[],
            pass_empty=set(),
            escape_newlines=False,
            no_notices=True,
            destroy=True,
            run_seed=True,
        )
        self.assertEqual(commands[0][0][:5], ["npx", "cdk", "destroy", "--no-notices", "--force"])
        self.assertEqual(commands[0][0][-2:], ["www", "api"])
        seeded = commands[2][0]
        self.assertIn("api:RunSeedData=true", seeded)
        self.assertNotIn("api:RunSeedData=false", seeded)
        self.assertIn("api:Name=one", seeded)

    def test_append_if_set_omits_an_empty_value_and_does_not_print_it(self) -> None:
        plan = {
            "groups": [
                {
                    "stacks": ["api"],
                    "prefixes": ["api:"],
                    "append-if-set": [{"parameter": "api:Token", "env": "TOKEN"}],
                }
            ]
        }
        with mock.patch.dict(os.environ, {"TOKEN": ""}, clear=False):
            skipped = cdk_deploy.build_commands(
                plan=plan,
                parameters={},
                fmt="prefixed-json",
                selected_stacks=[],
                pass_empty=set(),
                escape_newlines=False,
                no_notices=False,
                destroy=False,
                run_seed=False,
            )
        self.assertFalse(any("Token" in arg for arg in skipped[0][0]))
        with mock.patch.dict(os.environ, {"TOKEN": "secret-token"}, clear=False):
            with mock.patch("sys.stdout") as stdout:
                sent = cdk_deploy.build_commands(
                    plan=plan,
                    parameters={},
                    fmt="prefixed-json",
                    selected_stacks=[],
                    pass_empty=set(),
                    escape_newlines=False,
                    no_notices=False,
                    destroy=False,
                    run_seed=False,
                )
                printed = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("api:Token=secret-token", sent[0][0])
        self.assertNotIn("secret-token", printed)

    def test_main_redacts_an_account_id_and_deploys_the_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            params = Path(tmp) / "params.json"
            params.write_text(json.dumps({"api:Name": "one"}), encoding="utf-8")
            app = Path(tmp) / "app"
            app.mkdir()
            seen: list[list[str]] = []

            def run(command: list[str]) -> subprocess.CompletedProcess[str]:
                seen.append(command)
                return _ok("created in 123456789012")

            env = {
                "WORKING_DIRECTORY": str(app),
                "PLAN": json.dumps({"groups": [{"stacks": ["api"], "prefixes": ["api:"]}]}),
                "PARAM_FILE": str(params),
                "FORMAT": "prefixed-json",
                "ATTEMPTS": "1",
                "NO_NOTICES": "false",
                "PASS_EMPTY": "",
                "DESTROY": "false",
                "RUN_SEED": "false",
                "STACKS": "",
                "ESCAPE_NEWLINES": "false",
                "SKIP_RESOURCE": "",
                "REGION": "",
            }
            previous = Path.cwd()
            try:
                with mock.patch.dict(os.environ, env, clear=False):
                    with mock.patch("sys.stdout") as stdout:
                        code = cdk_deploy.main(run, lambda seconds: None)
                        printed = "".join(call.args[0] for call in stdout.write.call_args_list)
                self.assertEqual(Path.cwd().name, "app")
            finally:
                os.chdir(previous)
        self.assertEqual(code, 0)
        self.assertEqual(seen[0][0:3], ["npx", "cdk", "deploy"])
        self.assertIn("api:Name=one", seen[0])
        self.assertNotIn("123456789012", printed)
        self.assertIn("************", printed)
