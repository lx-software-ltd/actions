"""CDK diff: command shape, masking, and the step summary."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cdk-diff"))

import cdk_diff  # noqa: E402


class CdkDiffTest(unittest.TestCase):
    def test_empty_stacks_pass_no_stack_names(self) -> None:
        self.assertEqual(
            cdk_diff.command([], []),
            ["npx", "--no-install", "cdk", "diff", "--no-color"],
        )

    def test_stacks_and_args_keep_their_order(self) -> None:
        command = cdk_diff.command(["app", "web"], ["--parameters", "app:Name=value"])
        self.assertEqual(
            command,
            [
                "npx",
                "--no-install",
                "cdk",
                "diff",
                "--no-color",
                "--parameters",
                "app:Name=value",
                "app",
                "web",
            ],
        )

    def test_stack_list_splits_on_commas_and_space(self) -> None:
        self.assertEqual(cdk_diff.split_list(" app, web\tadmin "), ["app", "web", "admin"])

    def test_args_file_keeps_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "args"
            path.write_bytes(b"--parameters\0app:Name=a value\0")
            self.assertEqual(
                cdk_diff.read_args_file(str(path)),
                ["--parameters", "app:Name=a value"],
            )

    def test_mask_replaces_the_account_and_an_empty_id_changes_nothing(self) -> None:
        raw = "Stack app (aws://000000000000/ap-southeast-1)"
        self.assertEqual(
            cdk_diff.mask(raw, "000000000000"),
            "Stack app (aws://***/ap-southeast-1)",
        )
        self.assertEqual(cdk_diff.mask(raw, ""), raw)

    def test_missing_package_does_not_run_cdk(self) -> None:
        calls: list[list[str]] = []

        def run_cdk(command: list[str], directory: str) -> tuple[int, str]:
            calls.append(command)
            return 0, ""

        with tempfile.TemporaryDirectory() as directory:
            env = {
                "WORKING_DIRECTORY": directory,
                "STACKS": "app",
                "ARGS": "",
                "ARGS_FILE": "",
                "ACCOUNT_ID": "000000000000",
                "SUMMARY": "true",
                "GITHUB_STEP_SUMMARY": "",
            }
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch("sys.stdout") as stdout:
                    code = cdk_diff.main(run_cdk)
            printed = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertIn(f"::warning::Missing {directory}/package.json", printed)

    def test_summary_is_masked_and_the_exit_code_is_kept(self) -> None:
        def run_cdk(command: list[str], directory: str) -> tuple[int, str]:
            return 0, "Stack app (aws://000000000000/ap-southeast-1)\nThere were no differences\n"

        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "package.json"
            app.write_text("{}\n", encoding="utf-8")
            summary = Path(directory) / "summary.md"
            env = {
                "WORKING_DIRECTORY": directory,
                "STACKS": "app",
                "ARGS": "",
                "ARGS_FILE": "",
                "ACCOUNT_ID": "000000000000",
                "SUMMARY": "true",
                "GITHUB_STEP_SUMMARY": str(summary),
                "RUNNER_TEMP": directory,
            }
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch("sys.stdout") as stdout:
                    code = cdk_diff.main(run_cdk)
            text = summary.read_text(encoding="utf-8")
            copy = (Path(directory) / "cdk-diff-summary.md").read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertEqual(text, copy)
        self.assertIn("### CDK diff", text)
        self.assertIn("aws://***/ap-southeast-1", text)
        self.assertNotIn("000000000000", text)
        printed = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertNotIn("000000000000", printed)

    def test_summary_false_writes_nothing(self) -> None:
        def run_cdk(command: list[str], directory: str) -> tuple[int, str]:
            return 2, "diff failed\n"

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "package.json").write_text("{}\n", encoding="utf-8")
            summary = Path(directory) / "summary.md"
            env = {
                "WORKING_DIRECTORY": directory,
                "STACKS": "",
                "ARGS": "",
                "ARGS_FILE": "",
                "ACCOUNT_ID": "",
                "SUMMARY": "false",
                "GITHUB_STEP_SUMMARY": str(summary),
                "RUNNER_TEMP": directory,
            }
            with mock.patch.dict("os.environ", env, clear=False):
                code = cdk_diff.main(run_cdk)
        self.assertEqual(code, 2)
        self.assertFalse(summary.exists())
        self.assertFalse((Path(directory) / "cdk-diff-summary.md").exists())

    def test_args_file_is_used_instead_of_args(self) -> None:
        seen: list[list[str]] = []

        def run_cdk(command: list[str], directory: str) -> tuple[int, str]:
            seen.append(command)
            return 0, "ok\n"

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "package.json").write_text("{}\n", encoding="utf-8")
            args_file = Path(directory) / "args"
            args_file.write_bytes(b"--parameters\0app:Name=a value\0")
            env = {
                "WORKING_DIRECTORY": directory,
                "STACKS": "app",
                "ARGS": "--app ignored",
                "ARGS_FILE": str(args_file),
                "ACCOUNT_ID": "",
                "SUMMARY": "false",
            }
            with mock.patch.dict("os.environ", env, clear=False):
                cdk_diff.main(run_cdk)
        self.assertIn("app:Name=a value", seen[0])
        self.assertNotIn("ignored", seen[0])

    def test_plan_file_supplies_the_parameter_arguments(self) -> None:
        seen: list[list[str]] = []

        def run_cdk(command: list[str], directory: str) -> tuple[int, str]:
            seen.append(command)
            return 0, "ok\n"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            params = root / "params.json"
            params.write_text(json.dumps({"api:Name": "one"}), encoding="utf-8")
            plan = root / "plan.json"
            plan.write_text(
                json.dumps({"groups": [{"stacks": ["api"], "prefixes": ["api:"]}]}),
                encoding="utf-8",
            )
            env = {
                "WORKING_DIRECTORY": directory,
                "STACKS": "api",
                "ARGS": "",
                "ARGS_FILE": "",
                "PLAN": "",
                "PLAN_FILE": str(plan),
                "PARAM_FILE": str(params),
                "FORMAT": "prefixed-json",
                "PASS_EMPTY": "",
                "ESCAPE_NEWLINES": "false",
                "INCLUDE_EXTRAS": "false",
                "ACCOUNT_ID": "",
                "SUMMARY": "false",
            }
            with mock.patch.dict("os.environ", env, clear=False):
                code = cdk_diff.main(run_cdk)
        self.assertEqual(code, 0)
        self.assertIn("--parameters", seen[0])
        self.assertIn("api:Name=one", seen[0])

    def test_lines_are_masked_as_they_arrive(self) -> None:
        written: list[str] = []
        stream = cdk_diff.LineStream("000000000000", written.append)
        stream.feed("aws://000000000000")
        self.assertEqual(written, [])
        stream.feed("/ap\nnext")
        stream.finish()
        self.assertEqual(written, ["aws://***/ap\n", "next"])
        self.assertNotIn("000000000000", "".join(written))

    def test_a_pty_command_streams_masked_output(self) -> None:
        buffer = io.StringIO()
        with mock.patch("sys.stdout", buffer):
            code, raw = cdk_diff._run_cdk(
                [
                    "sh",
                    "-c",
                    "printf 'aws://000000000000/ap\\nsecond\\n'; exit 3",
                ],
                ".",
                "000000000000",
            )
        text = buffer.getvalue()
        self.assertEqual(code, 3)
        self.assertIn("000000000000", raw)
        self.assertIn("aws://***/ap", text)
        self.assertIn("second", text)
        self.assertNotIn("000000000000", text)


if __name__ == "__main__":
    unittest.main()
