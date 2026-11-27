#!/usr/bin/env python3
"""Open one pull request that batches routine Dependabot updates.

report reads. open builds the batch pull request. land also waits for the
gates and merges. live JSON skips GitHub and is only valid with report.
A merge by github.token is refused: it would not start a push workflow.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from typing import Any

DEPENDABOT_LOGIN = "dependabot[bot]"
DEPENDABOT_ID = 49699333
DEPENDABOT_TYPE = "Bot"
WEB_FLOW = "web-flow"
MARKER_PREFIX = "<!-- dependabot-batch "
MARKER_SUFFIX = " -->"
POLL_SECONDS = 30
SIBLINGS = (
    "lx-software-ltd/actions",
    "lx-software-ltd/evolvesprouts",
    "lx-software-ltd/findingalpha",
    "lx-software-ltd/lx-software",
    "lx-software-ltd/siutindei",
)
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ENTRY_KEY = re.compile(r"^[A-Za-z0-9-]+$")
RUNNING_STATUS = {"queued", "in_progress", "pending", "waiting", "requested"}
COMPLETED_OK = "success"


@dataclass(frozen=True)
class Commit:
    message: str
    author_login: str | None
    committer_login: str | None
    verified: bool
    parents: int


@dataclass(frozen=True)
class Check:
    status: str
    conclusion: str | None


@dataclass
class Pull:
    number: int
    title: str
    body: str
    draft: bool
    state: str
    author_login: str
    author_id: int | None
    author_type: str
    head_ref: str
    head_sha: str
    head_repo: str
    base_ref: str
    base_repo: str
    commits: tuple[Commit, ...] = ()
    files: tuple[str, ...] = ()
    checks: dict[str, Check] = field(default_factory=dict)


@dataclass(frozen=True)
class Marker:
    members: dict[int, str]
    conflict: dict[int, str]
    refused: dict[int, str]


@dataclass(frozen=True)
class Classified:
    pull: Pull
    kind: str
    reason: str


@dataclass(frozen=True)
class Config:
    update_types: tuple[str, ...]
    exclude_dependencies: tuple[str, ...]
    exclude_paths: tuple[str, ...]
    required_checks: tuple[str, ...]
    start_gates: str
    gate_workflows: tuple[str, ...]
    timeout_minutes: int


@dataclass(frozen=True)
class Snapshot:
    repo: str
    default_branch: str
    sha: str
    pulls: tuple[Pull, ...]


@dataclass
class RepoResult:
    text: str
    pull_request: str
    batched: int
    failure: bool
    action: str


def _setting(name: str, default: str) -> str:
    """Return an env value. Unset uses the default. An empty value stays empty."""
    if name not in os.environ:
        return default
    return os.environ[name].strip()


def parse_mode(text: str) -> str:
    mode = text.strip() or "report"
    if mode not in {"report", "open", "land"}:
        raise ValueError(f"mode must be report, open, or land, got {mode!r}")
    return mode


def parse_repositories(text: str, *, default: str) -> list[str]:
    raw = text.strip() or default.strip()
    if not raw:
        raise ValueError("set repositories, or run in GitHub so GITHUB_REPOSITORY is set")
    if raw == "siblings":
        return list(SIBLINGS)
    repos: list[str] = []
    seen: set[str] = set()
    for token in raw.split():
        if REPO.fullmatch(token) is None:
            raise ValueError(f"repository must be owner/name, got {token!r}")
        if token not in seen:
            repos.append(token)
            seen.add(token)
    return repos


def parse_config() -> Config:
    start_gates = _setting("DEPENDABOT_BATCH_START_GATES", "none") or "none"
    if start_gates not in {"none", "dispatch"}:
        raise ValueError(f"start-gates must be none or dispatch, got {start_gates!r}")
    timeout_text = _setting("DEPENDABOT_BATCH_TIMEOUT_MINUTES", "60") or "60"
    if not timeout_text.isdigit():
        raise ValueError(f"timeout-minutes must be a whole number of minutes, got {timeout_text!r}")
    return Config(
        update_types=tuple(_setting("DEPENDABOT_BATCH_UPDATE_TYPES", "patch minor").split()),
        exclude_dependencies=tuple(_setting("DEPENDABOT_BATCH_EXCLUDE_DEPENDENCIES", "lx-software-ltd/actions/*").split()),
        exclude_paths=tuple(_setting("DEPENDABOT_BATCH_EXCLUDE_PATHS", ".github/workflows/*").split()),
        required_checks=tuple(_setting("DEPENDABOT_BATCH_REQUIRED_CHECKS", "lint test security-summary").split()),
        start_gates=start_gates,
        gate_workflows=tuple(_setting("DEPENDABOT_BATCH_GATE_WORKFLOWS", "lint.yml test.yml security.yml").split()),
        timeout_minutes=int(timeout_text),
    )


def _unquote(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return text


def parse_updated_dependencies(message: str) -> list[dict[str, str]] | None:
    """Return the entries of the first updated-dependencies block.

    None means the message has no block. An entry with no update-type is
    still returned, without that key, so the caller can reject it.
    """
    lines = message.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "updated-dependencies:":
            start = index + 1
            break
    if start is None:
        return None
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in lines[start:]:
        stripped = line.strip()
        if stripped == "...":
            break
        if not stripped:
            continue
        if stripped.startswith("- dependency-name:"):
            if current is not None:
                entries.append(current)
            current = {"dependency-name": _unquote(stripped.split(":", 1)[1])}
            continue
        if current is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if ENTRY_KEY.fullmatch(key) is None:
            continue
        current[key] = _unquote(value)
    if current is not None:
        entries.append(current)
    return entries


def _marker_map(value: Any, label: str) -> dict[int, str]:
    if not isinstance(value, dict):
        raise ValueError(f"marker {label} must be an object")
    found: dict[int, str] = {}
    for number, sha in value.items():
        if not isinstance(number, str) or not number.isdigit():
            raise ValueError(f"marker {label} key {number!r} is not a pull request number")
        if not isinstance(sha, str) or not sha or any(char.isspace() for char in sha):
            raise ValueError(f"marker {label} value for {number} is not a SHA")
        found[int(number)] = sha
    return found


def parse_marker(body: str) -> Marker | None:
    """Return the marker when the body ends with one. A malformed marker is ignored."""
    text = body.strip()
    if not text.endswith(MARKER_SUFFIX):
        return None
    start = text.rfind(MARKER_PREFIX)
    if start < 0:
        return None
    payload = text[start + len(MARKER_PREFIX) : -len(MARKER_SUFFIX)].strip()
    if not payload:
        return None
    try:
        data = json.loads(payload)
        if not isinstance(data, dict) or set(data) != {"members", "conflict", "refused"}:
            return None
        members = _marker_map(data["members"], "members")
        conflict = _marker_map(data["conflict"], "conflict")
        refused = _marker_map(data["refused"], "refused")
    except (json.JSONDecodeError, ValueError):
        return None
    numbers = list(members) + list(conflict) + list(refused)
    if len(numbers) != len(set(numbers)):
        return None
    return Marker(members, conflict, refused)


def format_marker(members: dict[int, str], conflict: dict[int, str], refused: dict[int, str]) -> str:
    payload = {
        "members": {str(number): members[number] for number in sorted(members)},
        "conflict": {str(number): conflict[number] for number in sorted(conflict)},
        "refused": {str(number): refused[number] for number in sorted(refused)},
    }
    return MARKER_PREFIX + json.dumps(payload, separators=(",", ":")) + MARKER_SUFFIX


def _glob_any(value: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        if pattern and fnmatchcase(value, pattern):
            return pattern
    return None


def author_foreign(pull: Pull) -> bool:
    return not (
        pull.author_login == DEPENDABOT_LOGIN
        and pull.author_id == DEPENDABOT_ID
        and pull.author_type == DEPENDABOT_TYPE
    )


def head_foreign(pull: Pull) -> bool:
    return pull.head_repo != pull.base_repo


def is_update_branch(commit: Commit) -> bool:
    """The merge commit Update branch writes: verified, two parents, committer web-flow."""
    return commit.verified and commit.parents == 2 and commit.committer_login == WEB_FLOW


def is_edited(pull: Pull) -> bool:
    for commit in pull.commits:
        if is_update_branch(commit):
            continue
        if commit.author_login != DEPENDABOT_LOGIN or not commit.verified:
            return True
    return False


def collect_entries(pull: Pull) -> list[dict[str, str]] | None:
    """Entries from Dependabot commits. None when no commit carries a block."""
    found = False
    entries: list[dict[str, str]] = []
    for commit in pull.commits:
        if commit.author_login != DEPENDABOT_LOGIN:
            continue
        parsed = parse_updated_dependencies(commit.message)
        if parsed is None:
            continue
        found = True
        entries.extend(parsed)
    if not found:
        return None
    return entries


def update_level(update_type: str) -> str:
    marker = "semver-"
    if marker in update_type:
        return update_type.rsplit(marker, 1)[1].strip()
    return update_type.strip()


def marker_kind(marker: Marker | None, pull: Pull) -> str | None:
    if marker is None:
        return None
    if marker.members.get(pull.number) == pull.head_sha:
        return "batch"
    if marker.conflict.get(pull.number) == pull.head_sha:
        return "conflict"
    if marker.refused.get(pull.number) == pull.head_sha:
        return "refused"
    return None


def classify(pull: Pull, config: Config, marker: Marker | None = None) -> Classified:
    """Assign one class. The first matching rule wins."""
    if author_foreign(pull):
        return Classified(pull, "foreign", "author is not dependabot[bot]")
    if head_foreign(pull):
        return Classified(pull, "foreign", "head repository is not the base repository")
    if pull.draft:
        return Classified(pull, "draft", "pull request is a draft")
    if is_edited(pull):
        return Classified(pull, "edited", "a commit is not from Dependabot, or is not verified")
    entries = collect_entries(pull)
    if entries is None or not entries:
        return Classified(pull, "unclassified", "no updated-dependencies block")
    if any(not entry.get("update-type") for entry in entries):
        return Classified(pull, "unclassified", "an entry has no update-type")
    for entry in entries:
        name = entry.get("dependency-name", "")
        pattern = _glob_any(name, config.exclude_dependencies)
        if pattern is not None:
            return Classified(pull, "excluded", f"{name} matches {pattern}")
    allowed = set(config.update_types)
    for entry in entries:
        level = update_level(entry.get("update-type", ""))
        if level not in allowed:
            name = entry.get("dependency-name", "")
            return Classified(pull, "level", f"{name} is {level}")
    for path in pull.files:
        pattern = _glob_any(path, config.exclude_paths)
        if pattern is not None:
            return Classified(pull, "path", f"{path} matches {pattern}")
    recorded = marker_kind(marker, pull)
    if recorded == "batch":
        return Classified(pull, "batch", "already in the batch")
    if recorded == "conflict":
        return Classified(pull, "conflict", "merge returned 409")
    if recorded == "refused":
        return Classified(pull, "refused", "merge returned 422")
    for name in config.required_checks:
        check = pull.checks.get(name)
        if check is not None and check.status != "completed":
            return Classified(pull, "running", f"{name} is {check.status}")
    for name in config.required_checks:
        if name not in pull.checks:
            return Classified(pull, "unchecked", f"{name} has no run")
    for name in config.required_checks:
        check = pull.checks[name]
        if check.conclusion != COMPLETED_OK:
            conclusion = check.conclusion or check.status
            return Classified(pull, "failing", f"{name} finished {conclusion}")
    return Classified(pull, "batch", "ready")


def _cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def check_report(checks: dict[str, Check], required: tuple[str, ...]) -> tuple[str, str]:
    """Return passed, failed, or running, and the check names that explain it.

    A completed check that is not success is failed, including when another
    required check has not finished. Exit 1 follows from failed.
    """
    failed: list[str] = []
    pending: list[str] = []
    for name in required:
        check = checks.get(name)
        if check is not None and check.status == "completed" and check.conclusion != COMPLETED_OK:
            failed.append(name)
        elif check is None or check.status != "completed":
            pending.append(name)
    if failed:
        return "failed", ", ".join(failed)
    if pending:
        return "running", ", ".join(pending)
    return "passed", ""


def render_report(
    repo: str,
    classified: list[Classified],
    batch: Pull | None,
    *,
    status: str,
    required: tuple[str, ...],
) -> str:
    lines = [
        f"## {repo}",
        "",
        status,
        "",
        "| Pull request | Title | Class | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for item in sorted(classified, key=lambda entry: entry.pull.number):
        lines.append(
            f"| #{item.pull.number} | {_cell(item.pull.title)} | {item.kind} | {_cell(item.reason)} |"
        )
    lines.append("")
    if batch is None:
        lines.append("Batch: none")
    else:
        marker = parse_marker(batch.body)
        if marker is None:
            members = "none"
        else:
            members = ", ".join(f"#{number}" for number in sorted(marker.members)) or "none"
        state, detail = check_report(batch.checks, required)
        lines.append(f"Batch: #{batch.number} `{batch.head_ref}`")
        lines.append(f"Members: {members}")
        lines.append(f"Checks: {state}" + (f" ({detail})" if detail else ""))
    return "\n".join(lines) + "\n"


def _batch_branch(name: str) -> None:
    if not name.startswith("dependabot-batch/") or name.startswith("dependabot/"):
        raise RuntimeError(f"refusing to touch branch {name}")
    if ".." in name:
        raise RuntimeError(f"refusing to touch branch {name}")


def _now() -> float:
    return time.monotonic()


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _gh_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("GH_TOKEN", "").strip():
        env.pop("GH_TOKEN", None)
    if not env.get("GITHUB_TOKEN", "").strip():
        env.pop("GITHUB_TOKEN", None)
    return env


def _run_gh(args: list[str], payload: dict[str, Any] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["gh", *args],
            input=None if payload is None else json.dumps(payload),
            check=False,
            capture_output=True,
            text=True,
            env=_gh_env(),
        )
    except FileNotFoundError as exc:
        raise RuntimeError("gh is not on PATH") from exc


def _parse_include(stdout: str) -> tuple[int, Any]:
    """Split ``gh api --include`` output into a status code and a JSON body.

    Real responses put headers between the status line and a blank line.
    A response with no headers has the blank line immediately after the status.
    """
    text = stdout.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("HTTP/"):
        detail = text.strip()[:300] or "empty response"
        raise RuntimeError(f"gh api returned no status line: {detail}")
    header, separator, raw = text.partition("\n\n")
    first = header.split("\n", 1)[0]
    try:
        status = int(first.split()[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"gh api status line is unreadable: {first}") from exc
    if not separator:
        raw = ""
    raw = raw.strip()
    if not raw:
        return status, None
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def _flatten_pages(data: Any) -> list[Any]:
    if not isinstance(data, list):
        raise RuntimeError("paginated GitHub response was not a list of pages")
    items: list[Any] = []
    for page in data:
        if isinstance(page, list):
            items.extend(page)
        elif isinstance(page, dict) and isinstance(page.get("check_runs"), list):
            items.extend(page["check_runs"])
        else:
            raise RuntimeError("unrecognised GitHub page")
    return items


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    args = ["api", "--include", "--method", method]
    if payload is not None:
        args.extend(["--input", "-"])
    args.append(path)
    result = _run_gh(args, payload)
    if not result.stdout.strip() and result.returncode != 0:
        detail = (result.stderr or "").strip() or f"gh api {method} {path} failed"
        raise RuntimeError(detail)
    return _parse_include(result.stdout)


def _request_pages(path: str) -> list[Any]:
    result = _run_gh(["api", "--paginate", "--slurp", path])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"gh api {path} failed"
        raise RuntimeError(detail)
    try:
        data = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh api {path} returned invalid JSON") from exc
    return _flatten_pages(data)


def _expect(status: int, allowed: set[int], method: str, path: str, body: Any) -> Any:
    if status in allowed:
        return body
    message = body.get("message", body) if isinstance(body, dict) else body
    raise RuntimeError(f"gh api {method} {path} returned {status}: {message}")


def _commit_from_api(item: dict[str, Any]) -> Commit:
    commit = item.get("commit") if isinstance(item.get("commit"), dict) else {}
    author = item.get("author") if isinstance(item.get("author"), dict) else None
    committer = item.get("committer") if isinstance(item.get("committer"), dict) else None
    verification = commit.get("verification") if isinstance(commit.get("verification"), dict) else {}
    parents = item.get("parents") if isinstance(item.get("parents"), list) else []
    message = commit.get("message")
    return Commit(
        message=message if isinstance(message, str) else "",
        author_login=author.get("login") if author and isinstance(author.get("login"), str) else None,
        committer_login=committer.get("login") if committer and isinstance(committer.get("login"), str) else None,
        verified=bool(verification.get("verified")),
        parents=len(parents),
    )


def _pull_from_api(item: dict[str, Any]) -> Pull:
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    head = item.get("head") if isinstance(item.get("head"), dict) else {}
    base = item.get("base") if isinstance(item.get("base"), dict) else {}
    head_repo = head.get("repo") if isinstance(head.get("repo"), dict) else {}
    base_repo = base.get("repo") if isinstance(base.get("repo"), dict) else {}
    author_id = user.get("id")
    return Pull(
        number=int(item["number"]),
        title=item.get("title") if isinstance(item.get("title"), str) else "",
        body=item.get("body") if isinstance(item.get("body"), str) else "",
        draft=bool(item.get("draft")),
        state=item.get("state") if isinstance(item.get("state"), str) else "open",
        author_login=user.get("login") if isinstance(user.get("login"), str) else "",
        author_id=author_id if isinstance(author_id, int) else None,
        author_type=user.get("type") if isinstance(user.get("type"), str) else "",
        head_ref=head.get("ref") if isinstance(head.get("ref"), str) else "",
        head_sha=head.get("sha") if isinstance(head.get("sha"), str) else "",
        head_repo=head_repo.get("full_name") if isinstance(head_repo.get("full_name"), str) else "",
        base_ref=base.get("ref") if isinstance(base.get("ref"), str) else "",
        base_repo=base_repo.get("full_name") if isinstance(base_repo.get("full_name"), str) else "",
    )


def _checks_from_runs(runs: list[Any]) -> dict[str, Check]:
    best: dict[str, tuple[int, Check]] = {}
    for run in runs:
        if not isinstance(run, dict):
            continue
        name = run.get("name")
        if not isinstance(name, str) or not name:
            continue
        run_id = run.get("id") if isinstance(run.get("id"), int) else 0
        status = run.get("status") if isinstance(run.get("status"), str) else ""
        conclusion = run.get("conclusion") if isinstance(run.get("conclusion"), str) else None
        current = best.get(name)
        if current is None or run_id >= current[0]:
            best[name] = (run_id, Check(status, conclusion))
    return {name: check for name, (_run_id, check) in best.items()}


def _check_from_live(value: Any) -> Check:
    if isinstance(value, str):
        if value in RUNNING_STATUS:
            return Check(value, None)
        return Check("completed", value)
    if isinstance(value, dict):
        status = value.get("status")
        conclusion = value.get("conclusion")
        return Check(
            status if isinstance(status, str) else "",
            conclusion if isinstance(conclusion, str) else None,
        )
    raise ValueError("a check result must be a string or an object")


def _commit_from_live(item: Any, index: int) -> Commit:
    if not isinstance(item, dict):
        raise ValueError(f"commit {index} must be an object")
    message = item.get("message", "")
    if not isinstance(message, str):
        raise ValueError(f"commit {index} message must be a string")
    author = item.get("author")
    if author is not None and not isinstance(author, str):
        raise ValueError(f"commit {index} author must be a login or null")
    committer = item.get("committer")
    if committer is not None and not isinstance(committer, str):
        raise ValueError(f"commit {index} committer must be a login or null")
    parents = item.get("parents", 1)
    if not isinstance(parents, int) or isinstance(parents, bool):
        raise ValueError(f"commit {index} parents must be a count")
    return Commit(
        message=message,
        author_login=author,
        committer_login=committer,
        verified=bool(item.get("verified")),
        parents=parents,
    )


def _repo_name(value: Any, label: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("full_name"), str):
        return value["full_name"]
    raise ValueError(f"{label} must be a repository name")


def _pull_from_live(item: Any, index: int, repo: str) -> Pull:
    where = f"{repo} pull request {index}"
    if not isinstance(item, dict):
        raise ValueError(f"{where} must be an object")
    number = item.get("number")
    if not isinstance(number, int) or isinstance(number, bool):
        raise ValueError(f"{where} needs a number")
    where = f"{repo} #{number}"
    title = item.get("title", "")
    body = item.get("body", "")
    if not isinstance(title, str) or not isinstance(body, str):
        raise ValueError(f"{where} title and body must be strings")
    author = item.get("author")
    if not isinstance(author, dict):
        raise ValueError(f"{where} author must be an object")
    login = author.get("login")
    author_id = author.get("id")
    author_type = author.get("type")
    if not isinstance(login, str) or (author_id is not None and not isinstance(author_id, int)):
        raise ValueError(f"{where} author needs a login and an id")
    if author_type is not None and not isinstance(author_type, str):
        raise ValueError(f"{where} author type must be a string")
    head = item.get("head")
    base = item.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise ValueError(f"{where} head and base must be objects")
    head_ref = head.get("ref")
    head_sha = head.get("sha")
    base_ref = base.get("ref")
    if not all(isinstance(value, str) for value in (head_ref, head_sha, base_ref)):
        raise ValueError(f"{where} head ref, head SHA, and base ref must be strings")
    commits = item.get("commits", [])
    files = item.get("files", [])
    checks = item.get("checks", {})
    if not isinstance(commits, list) or not isinstance(files, list) or not isinstance(checks, dict):
        raise ValueError(f"{where} commits, files, and checks have the wrong shape")
    if not all(isinstance(path, str) for path in files):
        raise ValueError(f"{where} files must be path strings")
    state = item.get("state", "open")
    if not isinstance(state, str):
        raise ValueError(f"{where} state must be a string")
    return Pull(
        number=number,
        title=title,
        body=body,
        draft=bool(item.get("draft")),
        state=state,
        author_login=login,
        author_id=author_id if isinstance(author_id, int) else None,
        author_type=author_type or "",
        head_ref=head_ref,
        head_sha=head_sha,
        head_repo=_repo_name(head.get("repo", repo), f"{where} head repo"),
        base_ref=base_ref,
        base_repo=_repo_name(base.get("repo", repo), f"{where} base repo"),
        commits=tuple(_commit_from_live(commit, commit_index) for commit_index, commit in enumerate(commits, start=1)),
        files=tuple(files),
        checks={name: _check_from_live(value) for name, value in checks.items()},
    )


def parse_live_document(text: str, repos: list[str]) -> dict[str, Snapshot]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"live JSON is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("live JSON must be an object keyed by owner/repo")
    found: dict[str, Snapshot] = {}
    for repo in repos:
        if repo not in data:
            raise ValueError(f"live JSON has no entry for {repo}")
        entry = data[repo]
        if not isinstance(entry, dict):
            raise ValueError(f"live JSON entry for {repo} must be an object")
        default_branch = entry.get("default_branch")
        sha = entry.get("sha")
        pulls = entry.get("pull_requests")
        if not isinstance(default_branch, str) or not default_branch:
            raise ValueError(f"{repo} needs a default branch")
        if not isinstance(sha, str) or not sha:
            raise ValueError(f"{repo} needs the default branch SHA")
        if not isinstance(pulls, list):
            raise ValueError(f"{repo} pull_requests must be a list")
        found[repo] = Snapshot(
            repo,
            default_branch,
            sha,
            tuple(_pull_from_live(item, index, repo) for index, item in enumerate(pulls, start=1)),
        )
    return found


def _load_github(repo: str) -> Snapshot:
    status, body = _request("GET", f"repos/{repo}")
    body = _expect(status, {200}, "GET", f"repos/{repo}", body)
    if not isinstance(body, dict) or not isinstance(body.get("default_branch"), str):
        raise RuntimeError(f"could not read the default branch of {repo}")
    default_branch = body["default_branch"]
    ref_path = f"repos/{repo}/git/ref/heads/{default_branch}"
    status, ref = _request("GET", ref_path)
    ref = _expect(status, {200}, "GET", ref_path, ref)
    sha = ref.get("object", {}).get("sha") if isinstance(ref, dict) else None
    if not isinstance(sha, str) or not sha:
        raise RuntimeError(f"could not read {default_branch} on {repo}")
    raw_pulls = _request_pages(f"repos/{repo}/pulls?state=open&per_page=100")
    pulls = tuple(_pull_from_api(item) for item in raw_pulls if isinstance(item, dict))
    return Snapshot(repo, default_branch, sha, pulls)


def _with_commits(repo: str, pull: Pull) -> Pull:
    raw = _request_pages(f"repos/{repo}/pulls/{pull.number}/commits?per_page=100")
    pull.commits = tuple(_commit_from_api(item) for item in raw if isinstance(item, dict))
    return pull


def _with_files(repo: str, pull: Pull) -> Pull:
    raw = _request_pages(f"repos/{repo}/pulls/{pull.number}/files?per_page=100")
    files: list[str] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("filename"), str):
            files.append(item["filename"])
    pull.files = tuple(files)
    return pull


def _with_checks(repo: str, pull: Pull) -> Pull:
    pull.checks = _fetch_checks(repo, pull.head_sha)
    return pull


def _fetch_checks(repo: str, sha: str) -> dict[str, Check]:
    raw = _request_pages(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")
    return _checks_from_runs(raw)


def _prepare(repo: str, pull: Pull, config: Config, marker: Marker | None, *, live: bool) -> Pull:
    """Load the fields the class rules read. A marker hit does not read checks again."""
    if live or author_foreign(pull) or head_foreign(pull) or pull.draft:
        return pull
    pull = _with_commits(repo, pull)
    if is_edited(pull):
        return pull
    entries = collect_entries(pull)
    if entries is None or not entries or any(not entry.get("update-type") for entry in entries):
        return pull
    if any(_glob_any(entry.get("dependency-name", ""), config.exclude_dependencies) for entry in entries):
        return pull
    allowed = set(config.update_types)
    if any(update_level(entry.get("update-type", "")) not in allowed for entry in entries):
        return pull
    pull = _with_files(repo, pull)
    if any(_glob_any(path, config.exclude_paths) for path in pull.files):
        return pull
    if marker_kind(marker, pull) is not None:
        return pull
    return _with_checks(repo, pull)


def _is_candidate(pull: Pull, default_branch: str) -> bool:
    return (
        pull.state == "open"
        and pull.base_ref == default_branch
        and pull.head_ref.startswith("dependabot/")
    )


def _is_batch_pull(pull: Pull) -> bool:
    return (
        pull.state == "open"
        and pull.head_ref.startswith("dependabot-batch/")
        and pull.head_repo == pull.base_repo
        and parse_marker(pull.body) is not None
    )


def _delete_branch(repo: str, branch: str) -> None:
    _batch_branch(branch)
    path = f"repos/{repo}/git/refs/heads/{branch}"
    status, body = _request("DELETE", path)
    _expect(status, {200, 204, 404}, "DELETE", path, body)


def _cleanup(repo: str, open_pulls: tuple[Pull, ...]) -> None:
    """Delete a batch branch whose marked pull request is no longer open."""
    refs = _request_pages(f"repos/{repo}/git/matching-refs/heads/dependabot-batch/")
    open_refs = {pull.head_ref for pull in open_pulls if pull.head_ref.startswith("dependabot-batch/")}
    owner = repo.split("/", 1)[0]
    for item in refs:
        if not isinstance(item, dict) or not isinstance(item.get("ref"), str):
            continue
        branch = item["ref"].removeprefix("refs/heads/")
        if not branch.startswith("dependabot-batch/") or branch in open_refs:
            continue
        query = urllib.parse.urlencode({"head": f"{owner}:{branch}", "state": "all", "per_page": "100"})
        found = _request_pages(f"repos/{repo}/pulls?{query}")
        for raw in found:
            if not isinstance(raw, dict):
                continue
            pull = _pull_from_api(raw)
            if pull.state == "open":
                break
            if parse_marker(pull.body) is not None:
                _delete_branch(repo, branch)
                break


def _supersede(repo: str, pull: Pull) -> None:
    _batch_branch(pull.head_ref)
    comment = f"repos/{repo}/issues/{pull.number}/comments"
    status, body = _request(
        "POST",
        comment,
        {"body": "Superseded. A new batch pull request replaces this one."},
    )
    _expect(status, {200, 201}, "POST", comment, body)
    close = f"repos/{repo}/pulls/{pull.number}"
    status, body = _request("PATCH", close, {"state": "closed"})
    _expect(status, {200}, "PATCH", close, body)
    _delete_branch(repo, pull.head_ref)


def _tracked(classified: list[Classified]) -> dict[int, tuple[str, str]]:
    return {
        item.pull.number: (item.kind, item.pull.head_sha)
        for item in classified
        if item.kind in {"batch", "conflict", "refused"}
    }


def _marker_tracked(marker: Marker) -> dict[int, tuple[str, str]]:
    found: dict[int, tuple[str, str]] = {}
    for number, sha in marker.members.items():
        found[number] = ("batch", sha)
    for number, sha in marker.conflict.items():
        found[number] = ("conflict", sha)
    for number, sha in marker.refused.items():
        found[number] = ("refused", sha)
    return found


def _one_line(title: str) -> str:
    return " ".join(title.split())


def _pull_body(
    members: list[Classified],
    left_out: list[Classified],
    marker_members: dict[int, str],
    conflict: dict[int, str],
    refused: dict[int, str],
) -> str:
    lines = [
        "Each member passed the required checks on its own head. "
        "Merge this pull request with a merge commit. "
        "GitHub then marks each member as merged.",
        "",
        "## Members",
        "",
    ]
    if members:
        for item in members:
            lines.append(f"- #{item.pull.number} {_one_line(item.pull.title)}")
    else:
        lines.append("None.")
    lines.extend(["", "## Left out", ""])
    if left_out:
        for item in left_out:
            lines.append(f"- #{item.pull.number} {item.kind}: {_one_line(item.pull.title)}")
    else:
        lines.append("None.")
    lines.extend(["", format_marker(marker_members, conflict, refused)])
    return "\n".join(lines) + "\n"


def _create_branch(repo: str, branch: str, sha: str) -> None:
    _batch_branch(branch)
    path = f"repos/{repo}/git/refs"
    status, body = _request("POST", path, {"ref": f"refs/heads/{branch}", "sha": sha})
    _expect(status, {201, 200}, "POST", path, body)


def _merge_sha(repo: str, branch: str, sha: str, number: int) -> int:
    _batch_branch(branch)
    path = f"repos/{repo}/merges"
    status, _body = _request(
        "POST",
        path,
        {
            "base": branch,
            "head": sha,
            "commit_message": f"Merge Dependabot update #{number}",
        },
    )
    if status in {201, 204, 409, 422}:
        return status
    raise RuntimeError(f"gh api POST {path} returned {status}")


def _dispatch(repo: str, branch: str, workflows: tuple[str, ...]) -> None:
    for workflow in workflows:
        path = f"repos/{repo}/actions/workflows/{workflow}/dispatches"
        status, body = _request("POST", path, {"ref": branch})
        _expect(status, {204, 200, 201}, "POST", path, body)


def _build(
    snapshot: Snapshot,
    classified: list[Classified],
    config: Config,
) -> tuple[Pull | None, list[Classified], int]:
    """Merge batch candidates. Return the new pull request, the final classes, and the member count.

    None for the pull request means no member merged and the branch was deleted.
    """
    branch = "dependabot-batch/" + _clock().strftime("%Y%m%d-%H%M%S")
    _create_branch(snapshot.repo, branch, snapshot.sha)
    members: dict[int, str] = {}
    conflict: dict[int, str] = {}
    refused: dict[int, str] = {}
    for item in sorted(classified, key=lambda entry: entry.pull.number):
        if item.kind == "conflict":
            conflict[item.pull.number] = item.pull.head_sha
        elif item.kind == "refused":
            refused[item.pull.number] = item.pull.head_sha
    for item in sorted(
        (entry for entry in classified if entry.kind == "batch"),
        key=lambda entry: entry.pull.number,
    ):
        status = _merge_sha(snapshot.repo, branch, item.pull.head_sha, item.pull.number)
        if status in {201, 204}:
            members[item.pull.number] = item.pull.head_sha
        elif status == 409:
            conflict[item.pull.number] = item.pull.head_sha
        else:
            refused[item.pull.number] = item.pull.head_sha
    final: list[Classified] = []
    for item in classified:
        number = item.pull.number
        if number in members:
            final.append(Classified(item.pull, "batch", "merged into the batch"))
        elif number in conflict and item.kind == "batch":
            final.append(Classified(item.pull, "conflict", "merge returned 409"))
        elif number in refused and item.kind == "batch":
            final.append(Classified(item.pull, "refused", "merge returned 422"))
        else:
            final.append(item)
    if not members:
        _delete_branch(snapshot.repo, branch)
        return None, final, 0
    merged = [item for item in final if item.pull.number in members]
    left_out = [item for item in final if item.pull.number not in members]
    title = f"chore(deps): batch {len(members)} Dependabot updates"
    body = _pull_body(merged, left_out, members, conflict, refused)
    path = f"repos/{snapshot.repo}/pulls"
    status, created = _request(
        "POST",
        path,
        {
            "title": title,
            "head": branch,
            "base": snapshot.default_branch,
            "body": body,
        },
    )
    created = _expect(status, {201, 200}, "POST", path, created)
    if not isinstance(created, dict) or not isinstance(created.get("number"), int):
        raise RuntimeError(f"opening the batch pull request on {snapshot.repo} returned no number")
    number = created["number"]
    label_path = f"repos/{snapshot.repo}/issues/{number}/labels"
    status, label_body = _request("POST", label_path, {"labels": ["dependencies"]})
    _expect(status, {200, 201}, "POST", label_path, label_body)
    if config.start_gates == "dispatch":
        _dispatch(snapshot.repo, branch, config.gate_workflows)
    opened = Pull(
        number=number,
        title=title,
        body=body,
        draft=False,
        state="open",
        author_login="",
        author_id=None,
        author_type="",
        head_ref=branch,
        head_sha=snapshot.sha,
        head_repo=snapshot.repo,
        base_ref=snapshot.default_branch,
        base_repo=snapshot.repo,
    )
    return opened, final, len(members)


def _attach_batch_checks(repo: str, pull: Pull, *, live: bool) -> Pull:
    if live or pull.checks:
        return pull
    return _with_checks(repo, pull)


def _status_line(repo: str, action: str, number: str = "", count: int = 0) -> str:
    if action == "waiting":
        return f"dependabot-batch: {repo} waiting"
    if action == "nothing":
        return f"dependabot-batch: {repo} nothing to do"
    if action == "kept":
        return f"dependabot-batch: {repo} kept #{number}"
    if action == "built":
        return f"dependabot-batch: {repo} built #{number} with {count} members"
    return f"dependabot-batch: {repo} {action}"


def _result(
    snapshot: Snapshot,
    classified: list[Classified],
    batch: Pull | None,
    *,
    action: str,
    number: str = "",
    count: int = 0,
    failure: bool = False,
    required: tuple[str, ...] = (),
) -> RepoResult:
    text_status = _status_line(snapshot.repo, action, number, count)
    if batch is not None and required:
        state, detail = check_report(batch.checks, required)
        if state == "failed":
            failure = True
            text_status += f"\ndependabot-batch: #{batch.number} required check {detail} failed"
    rendered = render_report(
        snapshot.repo,
        classified,
        batch,
        status=text_status,
        required=required,
    )
    return RepoResult(rendered, number, count, failure, action)


def _classify_all(
    snapshot: Snapshot,
    config: Config,
    marker: Marker | None,
    *,
    live: bool,
) -> list[Classified]:
    classified: list[Classified] = []
    for pull in snapshot.pulls:
        if not _is_candidate(pull, snapshot.default_branch):
            continue
        prepared = _prepare(snapshot.repo, pull, config, marker, live=live)
        classified.append(classify(prepared, config, marker))
    return classified


def _open_batches(snapshot: Snapshot) -> list[Pull]:
    found = [pull for pull in snapshot.pulls if _is_batch_pull(pull)]
    return sorted(found, key=lambda pull: pull.number)


def _run_open(snapshot: Snapshot, config: Config, *, live: bool) -> RepoResult:
    if not live:
        _cleanup(snapshot.repo, snapshot.pulls)
    batches = _open_batches(snapshot)
    current = batches[-1] if batches else None
    marker = parse_marker(current.body) if current is not None else None
    classified = _classify_all(snapshot, config, marker, live=live)
    if any(item.kind == "running" for item in classified):
        if current is not None:
            current = _attach_batch_checks(snapshot.repo, current, live=live)
        return _result(
            snapshot,
            classified,
            current,
            action="waiting",
            number=str(current.number) if current else "",
            count=len(marker.members) if marker else 0,
            required=config.required_checks,
        )
    if current is not None and marker is not None and _tracked(classified) == _marker_tracked(marker):
        for older in batches[:-1]:
            _supersede(snapshot.repo, older)
        current = _attach_batch_checks(snapshot.repo, current, live=live)
        return _result(
            snapshot,
            classified,
            current,
            action="kept",
            number=str(current.number),
            count=len(marker.members),
            required=config.required_checks,
        )
    for batch in batches:
        _supersede(snapshot.repo, batch)
    if not any(item.kind == "batch" for item in classified):
        return _result(snapshot, classified, None, action="nothing", required=config.required_checks)
    # The candidates that were classed against the old marker keep conflict and
    # refused. Reclassify only for the build's merge results.
    opened, final, count = _build(snapshot, classified, config)
    if opened is None:
        return _result(snapshot, final, None, action="nothing", required=config.required_checks)
    return _result(
        snapshot,
        final,
        opened,
        action="built",
        number=str(opened.number),
        count=count,
        required=config.required_checks,
    )


def _checks_settled(checks: dict[str, Check], required: tuple[str, ...]) -> str | None:
    """passed or failed once every required check has completed. None while any is open."""
    conclusions: list[str | None] = []
    for name in required:
        check = checks.get(name)
        if check is None or check.status != "completed":
            return None
        conclusions.append(check.conclusion)
    if all(conclusion == COMPLETED_OK for conclusion in conclusions):
        return "passed"
    return "failed"


def _wait_for_checks(repo: str, sha: str, required: tuple[str, ...], deadline: float) -> str:
    while True:
        settled = _checks_settled(_fetch_checks(repo, sha), required)
        if settled is not None:
            return settled
        if _now() >= deadline:
            return "timeout"
        _sleep(POLL_SECONDS)


def _behind(repo: str, base: str, sha: str) -> bool:
    path = f"repos/{repo}/compare/{base}...{sha}"
    status, body = _request("GET", path)
    body = _expect(status, {200}, "GET", path, body)
    if not isinstance(body, dict):
        raise RuntimeError(f"compare of {base}...{sha} on {repo} was not an object")
    behind_by = body.get("behind_by") or 0
    if isinstance(behind_by, int) and behind_by > 0:
        return True
    return body.get("status") in {"behind", "diverged"}


def _update_branch(repo: str, number: int, sha: str) -> None:
    path = f"repos/{repo}/pulls/{number}/update-branch"
    status, body = _request("PUT", path, {"expected_head_sha": sha})
    _expect(status, {200, 202}, "PUT", path, body)


def _wait_for_new_sha(repo: str, number: int, previous: str, deadline: float) -> Pull | None:
    while True:
        status, body = _request("GET", f"repos/{repo}/pulls/{number}")
        body = _expect(status, {200}, "GET", f"repos/{repo}/pulls/{number}", body)
        if not isinstance(body, dict):
            raise RuntimeError(f"could not read pull request #{number} on {repo}")
        pull = _pull_from_api(body)
        if pull.head_sha and pull.head_sha != previous:
            return pull
        if _now() >= deadline:
            return None
        _sleep(POLL_SECONDS)


def _land(snapshot: Snapshot, number: int, config: Config) -> None:
    deadline = _now() + config.timeout_minutes * 60
    updates = 0
    while True:
        status, body = _request("GET", f"repos/{snapshot.repo}/pulls/{number}")
        body = _expect(status, {200}, "GET", f"repos/{snapshot.repo}/pulls/{number}", body)
        if not isinstance(body, dict):
            raise RuntimeError(f"could not read pull request #{number} on {snapshot.repo}")
        pull = _pull_from_api(body)
        _batch_branch(pull.head_ref)
        outcome = _wait_for_checks(snapshot.repo, pull.head_sha, config.required_checks, deadline)
        if outcome == "timeout":
            raise RuntimeError(
                f"#{number} gates did not finish within {config.timeout_minutes} minutes"
            )
        if _behind(snapshot.repo, snapshot.default_branch, pull.head_sha):
            updates += 1
            if updates > 3:
                raise RuntimeError(f"#{number} is still behind {snapshot.default_branch} after 3 updates")
            _update_branch(snapshot.repo, number, pull.head_sha)
            moved = _wait_for_new_sha(snapshot.repo, number, pull.head_sha, deadline)
            if moved is None:
                raise RuntimeError(f"#{number} did not move off {pull.head_sha} before the timeout")
            continue
        if outcome == "failed":
            raise RuntimeError(f"#{number} required checks failed")
        path = f"repos/{snapshot.repo}/pulls/{number}/merge"
        status, merge_body = _request(
            "PUT",
            path,
            {"merge_method": "merge", "sha": pull.head_sha},
        )
        _expect(status, {200, 201}, "PUT", path, merge_body)
        _delete_branch(snapshot.repo, pull.head_ref)
        return


def _report(snapshot: Snapshot, config: Config, *, live: bool) -> RepoResult:
    batches = _open_batches(snapshot)
    current = batches[-1] if batches else None
    marker = parse_marker(current.body) if current is not None else None
    classified = _classify_all(snapshot, config, marker, live=live)
    if current is not None:
        current = _attach_batch_checks(snapshot.repo, current, live=live)
    count = sum(1 for item in classified if item.kind == "batch")
    return _result(
        snapshot,
        classified,
        current,
        action="report",
        number=str(current.number) if current is not None else "",
        count=count,
        required=config.required_checks,
    )


def _run_repo(snapshot: Snapshot, mode: str, config: Config, *, live: bool) -> RepoResult:
    if mode == "report":
        return _report(snapshot, config, live=live)
    result = _run_open(snapshot, config, live=live)
    if mode == "land" and result.action in {"kept", "built"} and result.pull_request and not result.failure:
        _land(snapshot, int(result.pull_request), config)
        result.text += f"dependabot-batch: {snapshot.repo} merged #{result.pull_request}\n"
    return result


def token_is_github_token() -> bool:
    """True when the token land would use is the workflow's github.token."""
    if "DEPENDABOT_BATCH_GITHUB_TOKEN" not in os.environ:
        return False
    github = os.environ.get("DEPENDABOT_BATCH_GITHUB_TOKEN", "")
    if "GH_TOKEN" in os.environ:
        token = os.environ["GH_TOKEN"]
    else:
        token = os.environ.get("GITHUB_TOKEN", "")
    return token == github


def _write_outputs(pull_request: str, batched: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"pull-request={pull_request}\n")
        handle.write(f"batched={batched}\n")


def _write_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if not path or not text:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def main() -> int:
    try:
        mode = parse_mode(os.environ.get("DEPENDABOT_BATCH_MODE", ""))
        config = parse_config()
        repos = parse_repositories(
            os.environ.get("DEPENDABOT_BATCH_REPOSITORIES", ""),
            default=os.environ.get("GITHUB_REPOSITORY", ""),
        )
    except ValueError as exc:
        print(f"dependabot-batch: {exc}", file=sys.stderr)
        return 1
    live_text = os.environ.get("DEPENDABOT_BATCH_LIVE_JSON", "").strip()
    if mode in {"open", "land"} and live_text:
        print("dependabot-batch: live JSON is only for report.", file=sys.stderr)
        return 1
    if mode == "land" and token_is_github_token():
        print(
            "dependabot-batch: a merge by github.token starts no push workflow, so nothing would deploy.",
            file=sys.stderr,
        )
        return 1
    live_doc: dict[str, Snapshot] | None = None
    if live_text:
        try:
            live_doc = parse_live_document(live_text, repos)
        except ValueError as exc:
            print(f"dependabot-batch: {exc}", file=sys.stderr)
            return 1
    code = 0
    summaries: list[str] = []
    single: RepoResult | None = None
    saw_repo = False
    for repo in repos:
        saw_repo = True
        try:
            snapshot = live_doc[repo] if live_doc is not None else _load_github(repo)
            result = _run_repo(snapshot, mode, config, live=live_doc is not None)
        except (RuntimeError, ValueError, KeyError) as exc:
            print(f"dependabot-batch: {exc}", file=sys.stderr)
            summaries.append(f"## {repo}\n\ndependabot-batch: {exc}\n")
            code = 1
            single = None
            continue
        print(result.text, end="" if result.text.endswith("\n") else "\n")
        summaries.append(result.text)
        if result.failure:
            code = 1
            for line in result.text.splitlines():
                if line.startswith("dependabot-batch:") and "failed" in line:
                    print(line, file=sys.stderr)
        if len(repos) == 1:
            single = result
    _write_summary("".join(summaries))
    if len(repos) == 1 and single is not None:
        _write_outputs(single.pull_request, str(single.batched))
    elif saw_repo:
        _write_outputs("", "")
    return code


if __name__ == "__main__":
    sys.exit(main())
