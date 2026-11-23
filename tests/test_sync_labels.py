"""sync-labels creates and updates the shared catalogue and leaves other labels."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "sync-labels" / "sync_labels.py"
_SPEC = importlib.util.spec_from_file_location("sync_labels", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sync_labels = importlib.util.module_from_spec(_SPEC)
sys.modules["sync_labels"] = sync_labels
_SPEC.loader.exec_module(sync_labels)

CATALOGUE = (
    ("accessibility", "f143ab", "Barrier affecting people with disabilities"),
    ("bug", "d73a4a", "Something isn't working"),
    ("ci", "d4c5f9", "GitHub Actions / CI"),
    ("dependencies", "0366d6", "Dependency updates (Dependabot)"),
    ("documentation", "0075ca", "Improvements or additions to documentation"),
    ("duplicate", "cfd3d7", "This issue or pull request already exists"),
    ("enhancement", "a2eeef", "New feature or request"),
    ("good first issue", "7057ff", "Good for newcomers"),
    ("help wanted", "008672", "Extra attention is needed"),
    ("infrastructure", "5319e7", "CDK / infrastructure"),
    ("invalid", "e4e669", "This doesn't seem right"),
    ("mobile", "0e8a16", "Flutter app"),
    ("question", "d876e3", "Further information is requested"),
    ("wontfix", "ffffff", "This will not be worked on"),
)
_LABEL_ENV = (
    "SYNC_LABELS_MODE",
    "SYNC_LABELS_REPOSITORIES",
    "SYNC_LABELS_JSON",
    "SYNC_LABELS_LIVE_JSON",
    "GITHUB_REPOSITORY",
    "GH_TOKEN",
    "GITHUB_TOKEN",
)


def _bug(**overrides: str) -> dict[str, str]:
    label = {"name": "bug", "color": "d73a4a", "description": "Something isn't working"}
    label.update(overrides)
    return label


class SyncLabelsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in _LABEL_ENV}
        for key in _LABEL_ENV:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _run(self) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = sync_labels.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_catalogue_is_the_shared_set(self) -> None:
        labels = sync_labels.load_catalogue_text("")
        self.assertEqual(
            [(label.name, label.color, label.description) for label in labels],
            list(CATALOGUE),
        )

    def test_catalogue_rejects_unsorted_and_bad_color(self) -> None:
        with self.assertRaises(ValueError):
            sync_labels.parse_catalogue([_bug(), {"name": "accessibility", "color": "f143ab", "description": ""}])
        with self.assertRaises(ValueError):
            sync_labels.parse_catalogue([{"name": "bug", "color": "red", "description": ""}])

    def test_siblings_are_the_five_repositories(self) -> None:
        self.assertEqual(
            sync_labels.parse_repositories("siblings", default=""),
            list(sync_labels.SIBLINGS),
        )
        self.assertEqual(
            sync_labels.parse_repositories("", default="lx-software-ltd/actions"),
            ["lx-software-ltd/actions"],
        )
        with self.assertRaises(ValueError):
            sync_labels.parse_repositories("https://github.com/lx-software-ltd/actions", default="")

    def test_diff_creates_updates_and_keeps_extra_labels(self) -> None:
        wanted = sync_labels.parse_catalogue(
            [_bug(), {"name": "dependencies", "color": "0366d6", "description": "Dependency updates (Dependabot)"}]
        )
        live = sync_labels.parse_live(
            [
                {"name": "Bug", "color": "#D73A4A", "description": "Something isn't working"},
                {"name": "lambda", "color": "c2e0c6", "description": None},
            ]
        )
        changes = sync_labels.diff_labels("lx-software-ltd/actions", wanted, live)
        self.assertEqual([change.action for change in changes], ["update", "create"])
        self.assertEqual(changes[0].before and changes[0].before.name, "Bug")
        self.assertIn("name -> bug", sync_labels.format_change(changes[0]))
        self.assertTrue(sync_labels.format_change(changes[1]).startswith("create "))

    def test_check_passes_when_color_case_and_extra_labels_differ(self) -> None:
        os.environ["SYNC_LABELS_JSON"] = (ROOT / "fixtures/sync-labels/pass/labels.json").read_text(encoding="utf-8")
        os.environ["SYNC_LABELS_LIVE_JSON"] = (ROOT / "fixtures/sync-labels/pass/live.json").read_text(encoding="utf-8")
        os.environ["GITHUB_REPOSITORY"] = "lx-software-ltd/actions"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertIn("no changes", stdout)

    def test_check_fails_on_drift(self) -> None:
        os.environ["SYNC_LABELS_MODE"] = "check"
        os.environ["SYNC_LABELS_JSON"] = (ROOT / "fixtures/sync-labels/fail/labels.json").read_text(encoding="utf-8")
        os.environ["SYNC_LABELS_LIVE_JSON"] = (ROOT / "fixtures/sync-labels/fail/live.json").read_text(encoding="utf-8")
        os.environ["SYNC_LABELS_REPOSITORIES"] = "lx-software-ltd/actions lx-software-ltd/findingalpha"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertEqual(stdout.count("color 000000 -> d73a4a"), 2)
        self.assertEqual(stdout.count("create lx-software-ltd/"), 2)
        self.assertIn("check does not write", stderr)

    def test_apply_refuses_live_json(self) -> None:
        os.environ["SYNC_LABELS_MODE"] = "apply"
        os.environ["SYNC_LABELS_LIVE_JSON"] = "[]"
        os.environ["GITHUB_REPOSITORY"] = "lx-software-ltd/actions"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("live JSON is only for check", stderr)

    def test_apply_posts_a_missing_label_and_patches_letter_case(self) -> None:
        calls: list[tuple[list[str], dict[str, str] | None]] = []

        def fake_run(
            args: list[str], payload: dict[str, str] | None = None
        ) -> subprocess.CompletedProcess[str]:
            calls.append((args, payload))
            stdout = "[]" if "--paginate" in args else ""
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

        original = sync_labels._run_gh
        sync_labels._run_gh = fake_run
        try:
            os.environ["SYNC_LABELS_MODE"] = "apply"
            os.environ["SYNC_LABELS_REPOSITORIES"] = "lx-software-ltd/actions"
            os.environ["SYNC_LABELS_JSON"] = json.dumps([_bug()])
            code, stdout, stderr = self._run()
        finally:
            sync_labels._run_gh = original
        self.assertEqual(code, 0, stderr)
        self.assertIn("applied 1 change", stdout)
        self.assertIn("applied create lx-software-ltd/actions bug", stdout)
        self.assertEqual(calls[0][0][:2], ["api", "--paginate"])
        method_args, payload = calls[1]
        self.assertEqual(method_args[:3], ["api", "--method", "POST"])
        self.assertEqual(payload, _bug())

    def test_apply_encodes_the_current_name(self) -> None:
        calls: list[list[str]] = []

        def fake_run(
            args: list[str], payload: dict[str, str] | None = None
        ) -> subprocess.CompletedProcess[str]:
            del payload
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        original = sync_labels._run_gh
        sync_labels._run_gh = fake_run
        try:
            sync_labels.apply_change(
                sync_labels.Change(
                    "update",
                    "lx-software-ltd/actions",
                    sync_labels.Label("good first issue", "7057ff", "Good for newcomers"),
                    sync_labels.Label("Good first issue", "7057ff", "Good for newcomers"),
                )
            )
        finally:
            sync_labels._run_gh = original
        self.assertIn("repos/lx-software-ltd/actions/labels/Good%20first%20issue", calls[0])

    def test_apply_continues_after_a_repository_fails(self) -> None:
        def fake_run(
            args: list[str], payload: dict[str, str] | None = None
        ) -> subprocess.CompletedProcess[str]:
            del payload
            target = args[-1]
            if "findingalpha" in target:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 403")
            if "--paginate" in args:
                return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
            if "evolvesprouts" in target:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 403")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        original = sync_labels._run_gh
        sync_labels._run_gh = fake_run
        try:
            os.environ["SYNC_LABELS_MODE"] = "apply"
            os.environ["SYNC_LABELS_REPOSITORIES"] = (
                "lx-software-ltd/findingalpha "
                "lx-software-ltd/evolvesprouts "
                "lx-software-ltd/actions"
            )
            os.environ["SYNC_LABELS_JSON"] = json.dumps([_bug()])
            code, stdout, stderr = self._run()
        finally:
            sync_labels._run_gh = original
        self.assertEqual(code, 1)
        self.assertIn("applied create lx-software-ltd/actions bug", stdout)
        self.assertNotIn("applied create lx-software-ltd/evolvesprouts", stdout)
        self.assertIn("applied 1 of 2 change(s)", stderr)
        self.assertIn("could not list labels on lx-software-ltd/findingalpha", stderr)
        self.assertIn("repos/lx-software-ltd/evolvesprouts/labels failed", stderr)
