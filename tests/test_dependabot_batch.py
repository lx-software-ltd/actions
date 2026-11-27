"""dependabot-batch classes Dependabot pull requests and opens one batch."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
import urllib.parse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PATH = ROOT / "dependabot-batch" / "batch.py"
_SPEC = importlib.util.spec_from_file_location("dependabot_batch", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
batch = importlib.util.module_from_spec(_SPEC)
sys.modules["dependabot_batch"] = batch
_SPEC.loader.exec_module(batch)

REPO = "lx-software-ltd/findingalpha"
PATCH = "version-update:semver-patch"
MINOR = "version-update:semver-minor"
MAJOR = "version-update:semver-major"
_ENV = (
    "DEPENDABOT_BATCH_MODE",
    "DEPENDABOT_BATCH_REPOSITORIES",
    "DEPENDABOT_BATCH_UPDATE_TYPES",
    "DEPENDABOT_BATCH_EXCLUDE_DEPENDENCIES",
    "DEPENDABOT_BATCH_EXCLUDE_PATHS",
    "DEPENDABOT_BATCH_REQUIRED_CHECKS",
    "DEPENDABOT_BATCH_START_GATES",
    "DEPENDABOT_BATCH_GATE_WORKFLOWS",
    "DEPENDABOT_BATCH_TIMEOUT_MINUTES",
    "DEPENDABOT_BATCH_LIVE_JSON",
    "DEPENDABOT_BATCH_GITHUB_TOKEN",
    "GITHUB_REPOSITORY",
    "GITHUB_OUTPUT",
    "GITHUB_STEP_SUMMARY",
    "GH_TOKEN",
    "GITHUB_TOKEN",
)


def _sha(char: str) -> str:
    return char * 40


def _block(*entries: tuple[str, str, str]) -> str:
    lines = ["chore(deps): bump packages", "", "---", "updated-dependencies:"]
    for name, version, update_type in entries:
        shown = f'"{name}"' if name.startswith("@") else name
        lines.extend(
            [
                f"- dependency-name: {shown}",
                f"  dependency-version: {version}",
                "  dependency-type: direct:production",
                f"  update-type: {update_type}",
            ]
        )
    lines.extend(["...", "", "Signed-off-by: dependabot[bot] <support@github.com>"])
    return "\n".join(lines) + "\n"


def _config(**overrides: object) -> batch.Config:
    values: dict[str, object] = {
        "update_types": ("patch", "minor"),
        "exclude_dependencies": ("lx-software-ltd/actions/*",),
        "exclude_paths": (".github/workflows/*",),
        "required_checks": ("lint", "test", "security-summary"),
        "start_gates": "none",
        "gate_workflows": ("lint.yml", "test.yml", "security.yml"),
        "timeout_minutes": 60,
    }
    values.update(overrides)
    return batch.Config(**values)


def _commit(message: str | None = None, **overrides: object) -> batch.Commit:
    values: dict[str, object] = {
        "message": message if message is not None else _block(("left-pad", "1.2.3", PATCH)),
        "author_login": batch.DEPENDABOT_LOGIN,
        "committer_login": batch.WEB_FLOW,
        "verified": True,
        "parents": 1,
    }
    values.update(overrides)
    return batch.Commit(**values)


def _checks(**overrides: batch.Check) -> dict[str, batch.Check]:
    found = {name: batch.Check("completed", "success") for name in ("lint", "test", "security-summary")}
    found.update(overrides)
    return found


def _pull(**overrides: object) -> batch.Pull:
    values: dict[str, object] = {
        "number": 2,
        "title": "chore(deps): bump left-pad from 1.2.2 to 1.2.3",
        "body": "",
        "draft": False,
        "state": "open",
        "author_login": batch.DEPENDABOT_LOGIN,
        "author_id": batch.DEPENDABOT_ID,
        "author_type": batch.DEPENDABOT_TYPE,
        "head_ref": "dependabot/npm_and_yarn/left-pad-1.2.3",
        "head_sha": _sha("b"),
        "head_repo": REPO,
        "base_ref": "main",
        "base_repo": REPO,
        "commits": (_commit(),),
        "files": ("package.json", "package-lock.json"),
        "checks": _checks(),
    }
    values.update(overrides)
    return batch.Pull(**values)


def _api_commit(
    message: str,
    *,
    author: str | None = batch.DEPENDABOT_LOGIN,
    committer: str | None = batch.WEB_FLOW,
    verified: bool = True,
    parents: int = 1,
) -> dict[str, object]:
    return {
        "sha": _sha("9"),
        "commit": {"message": message, "verification": {"verified": verified}},
        "author": None if author is None else {"login": author, "id": batch.DEPENDABOT_ID, "type": "Bot"},
        "committer": None if committer is None else {"login": committer, "id": 19864447, "type": "Bot"},
        "parents": [{"sha": f"parent-{index}"} for index in range(parents)],
    }


def _api_pull(
    *,
    number: int,
    title: str,
    head_ref: str,
    head_sha: str,
    body: str = "",
    draft: bool = False,
    state: str = "open",
    login: str = batch.DEPENDABOT_LOGIN,
    author_id: int = batch.DEPENDABOT_ID,
    author_type: str = batch.DEPENDABOT_TYPE,
) -> dict[str, object]:
    return {
        "number": number,
        "title": title,
        "body": body,
        "draft": draft,
        "state": state,
        "user": {"login": login, "id": author_id, "type": author_type},
        "head": {"ref": head_ref, "sha": head_sha, "repo": {"full_name": REPO}},
        "base": {"ref": "main", "repo": {"full_name": REPO}},
    }


def _runs(status_by_name: dict[str, str], *, start: int = 1) -> list[dict[str, object]]:
    runs = []
    for offset, (name, conclusion) in enumerate(status_by_name.items()):
        if conclusion in {"queued", "in_progress"}:
            runs.append({"id": start + offset, "name": name, "status": conclusion, "conclusion": None})
        else:
            runs.append(
                {"id": start + offset, "name": name, "status": "completed", "conclusion": conclusion}
            )
    return runs


GREEN = {"lint": "success", "test": "success", "security-summary": "success"}


class World:
    """A stand-in for ``gh api`` covering the endpoints the payload calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object] | None]] = []
        self.repos: dict[str, dict[str, object]] = {}

    def add_repo(self, name: str = REPO, sha: str | None = None) -> dict[str, object]:
        state: dict[str, object] = {
            "sha": sha or _sha("a"),
            "branch": "main",
            "pulls": [],
            "commits": {},
            "files": {},
            "checks": {},
            "refs": {},
            "merge_status": {},
            "behind": set(),
            "next_number": 80,
        }
        self.repos[name] = state
        return state

    def add_candidate(
        self,
        *,
        number: int,
        sha: str,
        title: str = "chore(deps): bump left-pad",
        message: str | None = None,
        files: list[str] | None = None,
        checks: dict[str, str] | None = None,
        draft: bool = False,
        repo: str = REPO,
    ) -> None:
        state = self.repos[repo]
        pulls = state["pulls"]
        assert isinstance(pulls, list)
        pulls.append(
            _api_pull(
                number=number,
                title=title,
                head_ref=f"dependabot/npm_and_yarn/pkg-{number}",
                head_sha=sha,
                draft=draft,
            )
        )
        commits = state["commits"]
        files_by_number = state["files"]
        checks_by_sha = state["checks"]
        assert isinstance(commits, dict) and isinstance(files_by_number, dict) and isinstance(checks_by_sha, dict)
        commits[number] = [_api_commit(message or _block(("left-pad", "1.2.3", PATCH)))]
        files_by_number[number] = files or ["package.json", "package-lock.json"]
        checks_by_sha[sha] = _runs(checks or GREEN)

    def add_batch(
        self,
        *,
        number: int,
        sha: str,
        body: str,
        checks: dict[str, str] | None = None,
        ref: str = "dependabot-batch/20261126-010101",
        state_name: str = "open",
        repo: str = REPO,
    ) -> None:
        state = self.repos[repo]
        pulls = state["pulls"]
        refs = state["refs"]
        checks_by_sha = state["checks"]
        assert isinstance(pulls, list) and isinstance(refs, dict) and isinstance(checks_by_sha, dict)
        pulls.append(
            _api_pull(
                number=number,
                title="chore(deps): batch Dependabot updates",
                head_ref=ref,
                head_sha=sha,
                body=body,
                state=state_name,
                login="github-actions[bot]",
                author_id=41898282,
                author_type="Bot",
            )
        )
        refs[ref] = sha
        checks_by_sha[sha] = _runs(checks or GREEN)

    def run(self, args: list[str], payload: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
        method = "GET"
        if "--method" in args:
            method = args[args.index("--method") + 1]
        path = args[-1]
        self.calls.append((method, path, payload))
        status, page = self._route(method, path, payload)
        if "--include" in args:
            raw = "" if page is None else json.dumps(page)
            stdout = f"HTTP/2.0 {status} OK\n\n{raw}"
        else:
            stdout = json.dumps([page])
        return subprocess.CompletedProcess(args, 0 if status < 400 else 1, stdout, "")

    def _route(
        self, method: str, path: str, payload: dict[str, object] | None
    ) -> tuple[int, object]:
        bare, _, query = path.partition("?")
        params = {key: values[0] for key, values in urllib.parse.parse_qs(query).items()}
        parts = bare.split("/")
        repo = f"{parts[1]}/{parts[2]}"
        rest = "/".join(parts[3:])
        if repo not in self.repos:
            return 500, {"message": f"missing {repo}"}
        state = self.repos[repo]
        pulls = state["pulls"]
        assert isinstance(pulls, list)
        if method == "GET" and rest == "":
            return 200, {"default_branch": state["branch"], "full_name": repo}
        if method == "GET" and rest.startswith("git/ref/heads/"):
            return 200, {"object": {"sha": state["sha"]}}
        if method == "GET" and rest == "pulls" and params.get("state") == "open":
            return 200, [pull for pull in pulls if pull["state"] == "open"]
        if method == "GET" and rest == "pulls" and params.get("state") == "all":
            head = params.get("head", "")
            branch = head.split(":", 1)[1] if ":" in head else head
            return 200, [pull for pull in pulls if pull["head"]["ref"] == branch]
        if method == "GET" and rest.startswith("pulls/") and rest.endswith("/commits"):
            number = int(rest.split("/")[1])
            commits = state["commits"]
            assert isinstance(commits, dict)
            return 200, commits.get(number, [])
        if method == "GET" and rest.startswith("pulls/") and rest.endswith("/files"):
            number = int(rest.split("/")[1])
            files = state["files"]
            assert isinstance(files, dict)
            return 200, [{"filename": name} for name in files.get(number, [])]
        if method == "GET" and rest.startswith("pulls/") and rest.count("/") == 1:
            number = int(rest.split("/")[1])
            for pull in pulls:
                if pull["number"] == number:
                    return 200, pull
            return 404, {"message": "Not Found"}
        if method == "GET" and rest.startswith("commits/") and rest.endswith("/check-runs"):
            sha = rest[len("commits/") : -len("/check-runs")]
            checks = state["checks"]
            assert isinstance(checks, dict)
            runs = checks.get(sha, [])
            return 200, {"total_count": len(runs), "check_runs": runs}
        if method == "GET" and rest.startswith("git/matching-refs/heads/dependabot-batch"):
            refs = state["refs"]
            assert isinstance(refs, dict)
            return 200, [
                {"ref": f"refs/heads/{name}", "object": {"sha": ref_sha}}
                for name, ref_sha in refs.items()
                if name.startswith("dependabot-batch/")
            ]
        if method == "GET" and rest.startswith("compare/"):
            sha = rest[len("compare/") :].split("...", 1)[1]
            behind = state["behind"]
            assert isinstance(behind, set)
            is_behind = sha in behind
            return 200, {"status": "behind" if is_behind else "identical", "behind_by": 1 if is_behind else 0}
        if method == "DELETE" and rest.startswith("git/refs/heads/"):
            branch = rest[len("git/refs/heads/") :]
            refs = state["refs"]
            assert isinstance(refs, dict)
            refs.pop(branch, None)
            return 204, None
        if method == "POST" and rest == "git/refs" and payload is not None:
            ref = str(payload["ref"]).removeprefix("refs/heads/")
            refs = state["refs"]
            assert isinstance(refs, dict)
            refs[ref] = payload["sha"]
            return 201, {"ref": payload["ref"], "object": {"sha": payload["sha"]}}
        if method == "POST" and rest == "merges" and payload is not None:
            merge_status = state["merge_status"]
            assert isinstance(merge_status, dict)
            status = int(merge_status.get(payload["head"], 201))
            if status >= 400:
                return status, {"message": "not merged"}
            return status, {"sha": _sha("f")}
        if method == "POST" and rest == "pulls" and payload is not None:
            number = int(state["next_number"])
            state["next_number"] = number + 1
            refs = state["refs"]
            assert isinstance(refs, dict)
            branch = str(payload["head"])
            pulls.append(
                _api_pull(
                    number=number,
                    title=str(payload["title"]),
                    head_ref=branch,
                    head_sha=str(refs.get(branch, state["sha"])),
                    body=str(payload["body"]),
                    login="github-actions[bot]",
                    author_id=41898282,
                    author_type="Bot",
                )
            )
            return 201, {"number": number}
        if method == "POST" and rest.startswith("issues/") and rest.endswith("/labels"):
            return 200, [{"name": "dependencies"}]
        if method == "POST" and rest.startswith("issues/") and rest.endswith("/comments"):
            return 201, {"id": 1}
        if method == "PATCH" and rest.startswith("pulls/") and payload is not None:
            number = int(rest.split("/")[1])
            for pull in pulls:
                if pull["number"] == number:
                    pull["state"] = payload.get("state", pull["state"])
                    return 200, pull
            return 404, {"message": "Not Found"}
        if method == "POST" and rest.endswith("/dispatches"):
            return 204, None
        if method == "PUT" and rest.endswith("/update-branch"):
            number = int(rest.split("/")[1])
            for pull in pulls:
                if pull["number"] == number:
                    old = pull["head"]["sha"]
                    behind = state["behind"]
                    assert isinstance(behind, set)
                    behind.discard(old)
                    new = _sha("b") if old != _sha("b") else _sha("c")
                    pull["head"]["sha"] = new
                    checks = state["checks"]
                    assert isinstance(checks, dict)
                    checks[new] = _runs(GREEN, start=20)
                    return 202, {"message": "Updating pull request branch."}
            return 404, {"message": "Not Found"}
        if method == "PUT" and rest.endswith("/merge"):
            return 200, {"sha": None if payload is None else payload.get("sha"), "merged": True}
        return 500, {"message": f"unhandled {method} {rest}"}


class DependabotBatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        self._hooks = (batch._now, batch._sleep, batch._clock, batch._run_gh)
        self.now = 0.0
        self.world = World()
        batch._now = lambda: self.now

        def sleep(seconds: float) -> None:
            self.now += seconds

        batch._sleep = sleep
        batch._clock = lambda: datetime(2026, 11, 27, 3, 4, 5, tzinfo=timezone.utc)
        batch._run_gh = self.world.run
        os.environ["GITHUB_REPOSITORY"] = REPO

    def tearDown(self) -> None:
        batch._now, batch._sleep, batch._clock, batch._run_gh = self._hooks
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _run(self) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = batch.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def _calls(self, method: str, suffix: str) -> list[tuple[str, dict[str, object] | None]]:
        found = []
        for called, path, payload in self.world.calls:
            bare = path.split("?", 1)[0]
            if called == method and bare.endswith(suffix):
                found.append((path, payload))
        return found

    def test_block_parser(self) -> None:
        one = batch.parse_updated_dependencies(_block(("left-pad", "1.2.3", PATCH)))
        self.assertEqual(
            one,
            [
                {
                    "dependency-name": "left-pad",
                    "dependency-version": "1.2.3",
                    "dependency-type": "direct:production",
                    "update-type": PATCH,
                }
            ],
        )
        group = batch.parse_updated_dependencies(
            _block(("left-pad", "1.2.3", PATCH), ("right-pad", "2.0.0", MINOR))
        )
        assert group is not None
        self.assertEqual([entry["dependency-name"] for entry in group], ["left-pad", "right-pad"])
        quoted = batch.parse_updated_dependencies(
            _block(("@tanstack/react-query", "5.108.1", MINOR))
        )
        assert quoted is not None
        self.assertEqual(quoted[0]["dependency-name"], "@tanstack/react-query")
        self.assertIsNone(batch.parse_updated_dependencies("chore: nothing to parse"))
        missing = batch.parse_updated_dependencies(
            "updated-dependencies:\n- dependency-name: foo\n  dependency-version: 1.0.0\n...\n"
        )
        assert missing is not None
        self.assertEqual(missing[0]["dependency-name"], "foo")
        self.assertNotIn("update-type", missing[0])

    def test_class_foreign(self) -> None:
        wrong_id = batch.classify(_pull(author_id=1), _config())
        self.assertEqual(wrong_id.kind, "foreign")
        self.assertIn("dependabot[bot]", wrong_id.reason)
        other_repo = batch.classify(_pull(head_repo="other/fork"), _config())
        self.assertEqual(other_repo.kind, "foreign")

    def test_class_draft(self) -> None:
        self.assertEqual(batch.classify(_pull(draft=True), _config()).kind, "draft")

    def test_class_edited(self) -> None:
        edited = _pull(commits=(_commit(author_login="octocat"),))
        self.assertEqual(batch.classify(edited, _config()).kind, "edited")
        unverified = _pull(commits=(_commit(verified=False),))
        self.assertEqual(batch.classify(unverified, _config()).kind, "edited")
        missing_author = _pull(commits=(_commit(author_login=None),))
        self.assertEqual(batch.classify(missing_author, _config()).kind, "edited")

    def test_update_branch_commit_stays_batch(self) -> None:
        commits = (
            _commit(),
            _commit(
                message="Merge branch 'main' into dependabot/npm_and_yarn/left-pad-1.2.3",
                author_login="lcacchiani",
                committer_login="web-flow",
                verified=True,
                parents=2,
            ),
        )
        self.assertEqual(batch.classify(_pull(commits=commits), _config()).kind, "batch")

    def test_class_unclassified(self) -> None:
        no_block = _pull(commits=(_commit(message="chore(deps): bump left-pad\n"),))
        self.assertEqual(batch.classify(no_block, _config()).kind, "unclassified")
        missing_type = _pull(
            commits=(
                _commit(
                    message="updated-dependencies:\n- dependency-name: foo\n  dependency-version: 1\n...\n"
                ),
            )
        )
        self.assertEqual(batch.classify(missing_type, _config()).kind, "unclassified")

    def test_class_excluded(self) -> None:
        message = _block(("lx-software-ltd/actions/sync-labels", "1.2.3", PATCH))
        kind = batch.classify(_pull(commits=(_commit(message=message),)), _config()).kind
        self.assertEqual(kind, "excluded")

    def test_class_level(self) -> None:
        message = _block(("left-pad", "1.2.3", PATCH), ("right-pad", "2.0.0", MAJOR))
        kind = batch.classify(_pull(commits=(_commit(message=message),)), _config()).kind
        self.assertEqual(kind, "level")

    def test_class_path(self) -> None:
        workflow = _pull(files=(".github/workflows/lint.yml",))
        self.assertEqual(batch.classify(workflow, _config()).kind, "path")
        allowed = _config(exclude_paths=())
        self.assertEqual(batch.classify(workflow, allowed).kind, "batch")

    def test_class_running(self) -> None:
        checks = _checks(test=batch.Check("in_progress", None))
        self.assertEqual(batch.classify(_pull(checks=checks), _config()).kind, "running")

    def test_class_unchecked(self) -> None:
        checks = _checks()
        del checks["test"]
        self.assertEqual(batch.classify(_pull(checks=checks), _config()).kind, "unchecked")

    def test_class_failing(self) -> None:
        checks = _checks(test=batch.Check("completed", "failure"))
        self.assertEqual(batch.classify(_pull(checks=checks), _config()).kind, "failing")

    def test_class_batch(self) -> None:
        self.assertEqual(batch.classify(_pull(), _config()).kind, "batch")

    def test_marker_round_trip_and_a_malformed_marker_is_ignored(self) -> None:
        text = batch.format_marker({2: _sha("b")}, {4: _sha("d")}, {})
        marker = batch.parse_marker("Members\n\n" + text + "\n")
        assert marker is not None
        self.assertEqual(marker.members, {2: _sha("b")})
        self.assertEqual(marker.conflict, {4: _sha("d")})
        self.assertEqual(marker.refused, {})
        self.assertIsNone(batch.parse_marker("<!-- dependabot-batch nope -->"))
        self.assertIsNone(batch.parse_marker(text + "\nthanks"))
        self.assertIsNone(batch.parse_marker("<!-- dependabot-batch {} -->"))

    def test_open_does_nothing_when_no_candidate_is_batch(self) -> None:
        self.world.add_repo()
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertIn("nothing to do", stdout)
        self.assertEqual(self._calls("POST", "/pulls"), [])

    def test_open_waits_while_a_candidate_is_running(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("b"), checks={**GREEN, "test": "in_progress"})
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertIn("waiting", stdout)
        self.assertEqual(self._calls("POST", "/merges"), [])
        self.assertEqual(self._calls("POST", "/pulls"), [])

    def test_build_merges_in_ascending_order_and_records_409_and_422(self) -> None:
        self.world.add_repo()
        shas = {2: _sha("b"), 4: _sha("c"), 5: _sha("d"), 9: _sha("e")}
        for number, sha in shas.items():
            self.world.add_candidate(number=number, sha=sha, title=f"chore(deps): bump pkg-{number}")
        merge_status = self.world.repos[REPO]["merge_status"]
        assert isinstance(merge_status, dict)
        merge_status[_sha("c")] = 409
        merge_status[_sha("d")] = 422
        merge_status[_sha("e")] = 204
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        os.environ["DEPENDABOT_BATCH_START_GATES"] = "dispatch"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        merges = [payload["head"] for _path, payload in self._calls("POST", "/merges") if payload]
        self.assertEqual(merges, [_sha("b"), _sha("c"), _sha("d"), _sha("e")])
        created = self._calls("POST", "/pulls")
        self.assertEqual(len(created), 1)
        body = str(created[0][1]["body"])
        self.assertEqual(created[0][1]["title"], "chore(deps): batch 2 Dependabot updates")
        self.assertIn("Merge this pull request with a merge commit.", body)
        self.assertIn("passed the required checks on its own head", body)
        marker = batch.parse_marker(body)
        assert marker is not None
        self.assertEqual(set(marker.members), {2, 9})
        self.assertEqual(marker.conflict, {4: _sha("c")})
        self.assertEqual(marker.refused, {5: _sha("d")})
        ref = self._calls("POST", "/git/refs")
        self.assertEqual(ref[0][1]["ref"], "refs/heads/dependabot-batch/20261127-030405")
        self.assertEqual(len(self._calls("POST", "/labels")), 1)
        workflows = [path.rsplit("/", 2)[-2] for path, _payload in self._calls("POST", "/dispatches")]
        self.assertEqual(workflows, ["lint.yml", "test.yml", "security.yml"])
        self.assertIn("built #80", stdout)

    def test_build_deletes_the_branch_when_no_member_merges(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("b"))
        self.world.add_candidate(number=3, sha=_sha("c"))
        merge_status = self.world.repos[REPO]["merge_status"]
        assert isinstance(merge_status, dict)
        merge_status[_sha("b")] = 409
        merge_status[_sha("c")] = 422
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self._calls("POST", "/pulls"), [])
        deleted = [path for path, _payload in self._calls("DELETE", "dependabot-batch/20261127-030405")]
        self.assertEqual(deleted, [f"repos/{REPO}/git/refs/heads/dependabot-batch/20261127-030405"])

    def test_cleanup_deletes_a_merged_batch_branch_and_never_a_dependabot_branch(self) -> None:
        state = self.world.add_repo()
        body = "done\n" + batch.format_marker({2: _sha("b")}, {}, {}) + "\n"
        self.world.add_batch(
            number=40,
            sha=_sha("d"),
            body=body,
            state_name="closed",
            ref="dependabot-batch/20261126-010101",
        )
        refs = state["refs"]
        assert isinstance(refs, dict)
        refs["dependabot/npm_and_yarn/left-pad-1.2.3"] = _sha("b")
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        deleted = [path for path, _payload in self._calls("DELETE", "")]
        self.assertEqual(
            deleted,
            [f"repos/{REPO}/git/refs/heads/dependabot-batch/20261126-010101"],
        )
        self.assertTrue(all("/git/refs/heads/dependabot/" not in path for path in deleted))
        with self.assertRaises(RuntimeError):
            batch._delete_branch(REPO, "dependabot/npm_and_yarn/left-pad-1.2.3")

    def test_keep_when_the_marker_still_matches(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("b"))
        body = "kept\n" + batch.format_marker({2: _sha("b")}, {}, {}) + "\n"
        self.world.add_batch(number=40, sha=_sha("d"), body=body)
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertIn("kept #40", stdout)
        self.assertEqual(self._calls("POST", "/merges"), [])
        self.assertEqual(self._calls("POST", "/pulls"), [])
        self.assertEqual(self._calls("PATCH", ""), [])

    def test_keep_when_a_conflict_candidate_is_still_green(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("b"))
        self.world.add_candidate(number=3, sha=_sha("c"))
        body = "kept\n" + batch.format_marker({2: _sha("b")}, {3: _sha("c")}, {}) + "\n"
        self.world.add_batch(number=40, sha=_sha("d"), body=body)
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertIn("kept #40", stdout)
        self.assertIn("| #3 |", stdout)
        self.assertIn("| conflict |", stdout)
        self.assertEqual(self._calls("POST", "/merges"), [])
        check_paths = [path for _method, path, _payload in self.world.calls if "/check-runs" in path]
        self.assertTrue(any(_sha("d") in path for path in check_paths))
        self.assertFalse(any(_sha("b") in path or _sha("c") in path for path in check_paths))

    def test_supersede_when_a_member_became_a_draft(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("b"), draft=True)
        self.world.add_candidate(number=3, sha=_sha("c"))
        body = "old\n" + batch.format_marker({2: _sha("b"), 3: _sha("c")}, {}, {}) + "\n"
        self.world.add_batch(number=40, sha=_sha("d"), body=body, ref="dependabot-batch/20261126-010101")
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertTrue(self._calls("PATCH", "/pulls/40"))
        self.assertIn("Superseded", str(self._calls("POST", "/comments")[0][1]["body"]))
        merges = [payload["head"] for _path, payload in self._calls("POST", "/merges") if payload]
        self.assertEqual(merges, [_sha("c")])
        self.assertIn("built #80", stdout)

    def test_supersede_when_a_member_head_sha_changed(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("b"))
        body = "old\n" + batch.format_marker({2: _sha("9")}, {}, {}) + "\n"
        self.world.add_batch(number=40, sha=_sha("d"), body=body)
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertTrue(self._calls("PATCH", "/pulls/40"))
        merges = [payload["head"] for _path, payload in self._calls("POST", "/merges") if payload]
        self.assertEqual(merges, [_sha("b")])

    def test_keep_with_a_failed_check_exits_1(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("b"))
        body = "kept\n" + batch.format_marker({2: _sha("b")}, {}, {}) + "\n"
        self.world.add_batch(
            number=40,
            sha=_sha("d"),
            body=body,
            checks={**GREEN, "test": "failure"},
        )
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("kept #40", stdout)
        self.assertIn("Checks: failed (test)", stdout)
        self.assertIn("required check test failed", stderr)
        self.assertEqual(self._calls("POST", "/merges"), [])
        self.assertEqual(self._calls("POST", "/pulls"), [])

    def test_a_malformed_marker_is_not_closed(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("b"))
        self.world.add_batch(number=7, sha=_sha("d"), body="<!-- dependabot-batch nope -->\n")
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self._calls("PATCH", "/pulls/7"), [])
        self.assertEqual(len(self._calls("POST", "/pulls")), 1)

    def test_open_and_land_refuse_live_json(self) -> None:
        def forbid(args: list[str], payload: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
            del args, payload
            raise AssertionError("live JSON called GitHub")

        batch._run_gh = forbid
        os.environ["DEPENDABOT_BATCH_LIVE_JSON"] = "{}"
        for mode in ("open", "land"):
            with self.subTest(mode=mode):
                os.environ["DEPENDABOT_BATCH_MODE"] = mode
                code, _stdout, stderr = self._run()
                self.assertEqual(code, 1)
                self.assertIn("live JSON is only for report", stderr)

    def test_land_refuses_github_token(self) -> None:
        os.environ["DEPENDABOT_BATCH_MODE"] = "land"
        os.environ["GH_TOKEN"] = "ghs_same"
        os.environ["DEPENDABOT_BATCH_GITHUB_TOKEN"] = "ghs_same"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("nothing would deploy", stderr)
        self.assertEqual(self.world.calls, [])

    def test_land_updates_when_behind_and_merges_that_sha(self) -> None:
        state = self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("e"))
        body = "kept\n" + batch.format_marker({2: _sha("e")}, {}, {}) + "\n"
        self.world.add_batch(number=40, sha=_sha("d"), body=body)
        behind = state["behind"]
        assert isinstance(behind, set)
        behind.add(_sha("d"))
        os.environ["DEPENDABOT_BATCH_MODE"] = "land"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        update = self._calls("PUT", "/update-branch")
        self.assertEqual(update[0][1]["expected_head_sha"], _sha("d"))
        merge = self._calls("PUT", "/merge")
        self.assertEqual(merge[0][1]["merge_method"], "merge")
        self.assertEqual(merge[0][1]["sha"], _sha("b"))
        self.assertIn("merged #40", stdout)
        deleted = [path for path, _payload in self._calls("DELETE", "dependabot-batch/20261126-010101")]
        self.assertEqual(deleted, [f"repos/{REPO}/git/refs/heads/dependabot-batch/20261126-010101"])

    def test_land_merge_carries_the_sha_it_checked(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("e"))
        body = "kept\n" + batch.format_marker({2: _sha("e")}, {}, {}) + "\n"
        self.world.add_batch(number=40, sha=_sha("d"), body=body)
        os.environ["DEPENDABOT_BATCH_MODE"] = "land"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self._calls("PUT", "/update-branch"), [])
        merge = self._calls("PUT", "/merge")
        self.assertEqual(merge[0][1], {"merge_method": "merge", "sha": _sha("d")})

    def test_land_times_out(self) -> None:
        self.world.add_repo()
        self.world.add_candidate(number=2, sha=_sha("e"))
        body = "kept\n" + batch.format_marker({2: _sha("e")}, {}, {}) + "\n"
        self.world.add_batch(
            number=40,
            sha=_sha("d"),
            body=body,
            checks={**GREEN, "test": "in_progress"},
        )
        os.environ["DEPENDABOT_BATCH_MODE"] = "land"
        os.environ["DEPENDABOT_BATCH_TIMEOUT_MINUTES"] = "0"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("did not finish", stderr)
        self.assertEqual(self._calls("PUT", "/merge"), [])

    def test_report_lists_every_candidate_escapes_a_pipe_and_fails_a_red_batch(self) -> None:
        pipe = _pull(number=2, title="chore(deps): bump foo | bar")
        level = _pull(
            number=3,
            title="chore(deps): bump right-pad",
            head_sha=_sha("c"),
            commits=(_commit(message=_block(("right-pad", "2.0.0", MAJOR))),),
        )
        failing = _pull(
            number=4,
            title="chore(deps): bump ms",
            head_sha=_sha("d"),
            checks=_checks(test=batch.Check("completed", "failure")),
        )
        marker = batch.format_marker({2: pipe.head_sha}, {}, {})
        batch_pull = _pull(
            number=50,
            title="chore(deps): batch 1 Dependabot updates",
            head_ref="dependabot-batch/20261127-030000",
            head_sha=_sha("e"),
            author_login="github-actions[bot]",
            author_id=41898282,
            author_type="Bot",
            body=f"members\n\n{marker}\n",
            commits=(),
            files=(),
            checks=_checks(test=batch.Check("completed", "failure")),
        )
        document = {
            REPO: {
                "default_branch": "main",
                "sha": _sha("a"),
                "pull_requests": [
                    _live(pipe),
                    _live(level),
                    _live(failing),
                    _live(batch_pull),
                ],
            }
        }
        output = Path(os.environ.get("TMPDIR", "/tmp")) / "dependabot-batch-summary.md"
        out_file = Path(os.environ.get("TMPDIR", "/tmp")) / "dependabot-batch-output.txt"
        os.environ["GITHUB_STEP_SUMMARY"] = str(output)
        os.environ["GITHUB_OUTPUT"] = str(out_file)
        os.environ["DEPENDABOT_BATCH_MODE"] = "report"
        os.environ["DEPENDABOT_BATCH_REPOSITORIES"] = REPO
        os.environ["DEPENDABOT_BATCH_LIVE_JSON"] = json.dumps(document)
        code, stdout, stderr = self._run()
        self.assertEqual(code, 1, stderr)
        for number in (2, 3, 4):
            self.assertIn(f"#{number}", stdout)
        self.assertIn(r"foo \| bar", stdout)
        self.assertNotIn("| bump foo | bar |", stdout)
        self.assertIn("Checks: failed (test)", stdout)
        self.assertIn("Checks: failed (test)", output.read_text(encoding="utf-8"))
        self.assertIn("batched=1", out_file.read_text(encoding="utf-8"))
        self.assertIn("pull-request=50", out_file.read_text(encoding="utf-8"))
        self.assertEqual(self.world.calls, [])

    def test_pass_fixture_reports_two_batch_candidates(self) -> None:
        out_file = Path(os.environ.get("TMPDIR", "/tmp")) / "dependabot-batch-pass-output.txt"
        os.environ["GITHUB_OUTPUT"] = str(out_file)
        os.environ["DEPENDABOT_BATCH_MODE"] = "report"
        os.environ["DEPENDABOT_BATCH_REPOSITORIES"] = REPO
        os.environ["DEPENDABOT_BATCH_LIVE_JSON"] = (
            ROOT / "fixtures" / "dependabot-batch" / "pass" / "live.json"
        ).read_text(encoding="utf-8")
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0, stderr)
        for number in range(11, 19):
            self.assertIn(f"#{number}", stdout)
        written = out_file.read_text(encoding="utf-8")
        self.assertIn("batched=2\n", written)
        self.assertIn("pull-request=\n", written)
        self.assertEqual(self.world.calls, [])

    def test_fail_fixture_exits_1(self) -> None:
        os.environ["DEPENDABOT_BATCH_MODE"] = "report"
        os.environ["DEPENDABOT_BATCH_REPOSITORIES"] = REPO
        os.environ["DEPENDABOT_BATCH_LIVE_JSON"] = (
            ROOT / "fixtures" / "dependabot-batch" / "fail" / "live.json"
        ).read_text(encoding="utf-8")
        code, stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("#50", stdout)
        self.assertIn("Checks: failed (test)", stdout)
        self.assertIn("required check test failed", stderr)

    def test_a_failed_repository_does_not_stop_the_next(self) -> None:
        self.world.add_repo()
        os.environ["DEPENDABOT_BATCH_MODE"] = "open"
        os.environ["DEPENDABOT_BATCH_REPOSITORIES"] = f"lx-software-ltd/missing {REPO}"
        code, stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("missing", stderr)
        self.assertIn(f"## {REPO}", stdout)
        self.assertIn("nothing to do", stdout)

    def test_unknown_mode_and_repository_exit_1(self) -> None:
        os.environ["DEPENDABOT_BATCH_MODE"] = "explode"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("mode must be report, open, or land", stderr)
        os.environ["DEPENDABOT_BATCH_MODE"] = "report"
        os.environ["DEPENDABOT_BATCH_REPOSITORIES"] = "not a repo"
        code, _stdout, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("repository must be owner/name", stderr)
        self.assertEqual(
            batch.parse_repositories("siblings", default=""),
            list(batch.SIBLINGS),
        )


def _live(pull: batch.Pull) -> dict[str, object]:
    return {
        "number": pull.number,
        "title": pull.title,
        "body": pull.body,
        "draft": pull.draft,
        "state": pull.state,
        "author": {"login": pull.author_login, "id": pull.author_id, "type": pull.author_type},
        "head": {"ref": pull.head_ref, "sha": pull.head_sha, "repo": pull.head_repo},
        "base": {"ref": pull.base_ref, "repo": pull.base_repo},
        "commits": [
            {
                "message": commit.message,
                "author": commit.author_login,
                "committer": commit.committer_login,
                "verified": commit.verified,
                "parents": commit.parents,
            }
            for commit in pull.commits
        ],
        "files": list(pull.files),
        "checks": {
            name: check.conclusion if check.status == "completed" and check.conclusion else check.status
            for name, check in pull.checks.items()
        },
    }


if __name__ == "__main__":
    unittest.main()
