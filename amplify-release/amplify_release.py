"""Start an Amplify RELEASE job, or promote after the source job is green.

The caller has already assumed a role. This action does not request a
token and does not print an account id. ``wait`` false keeps the current
fire-and-forget release. Promote still refuses a source job that is not
SUCCEED, and by default only staging may promote to main.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable

ACCOUNT_ID = re.compile(r"\b\d{12}\b")
TERMINAL_OK = {"SUCCEED"}
TERMINAL_BAD = {"FAILED", "CANCELLED"}

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class AmplifyError(Exception):
    """The release cannot run."""


def _run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _redact(text: str) -> str:
    return ACCOUNT_ID.sub("************", text)


def _aws_json(run_aws: Runner, command: list[str]) -> dict[str, object]:
    result = run_aws(command)
    if result.returncode != 0:
        detail = _redact(result.stderr or result.stdout or "aws failed")
        raise AmplifyError(detail)
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as error:
        raise AmplifyError("Amplify did not return JSON") from error
    if not isinstance(payload, dict):
        raise AmplifyError("Amplify did not return JSON")
    return payload


def _truthy(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.lower() == "true"


def _start_job(run_aws: Runner, app_id: str, branch: str) -> str:
    payload = _aws_json(
        run_aws,
        [
            "aws",
            "amplify",
            "start-job",
            "--app-id",
            app_id,
            "--branch-name",
            branch,
            "--job-type",
            "RELEASE",
            "--output",
            "json",
        ],
    )
    summary = payload.get("jobSummary")
    job_id = ""
    if isinstance(summary, dict):
        job_id = str(summary.get("jobId") or "")
    if not job_id:
        raise AmplifyError("Amplify did not return a job id")
    print(f"Started Amplify RELEASE {job_id} on {branch}")
    return job_id


def _job_status(run_aws: Runner, app_id: str, branch: str, job_id: str) -> str:
    payload = _aws_json(
        run_aws,
        [
            "aws",
            "amplify",
            "get-job",
            "--app-id",
            app_id,
            "--branch-name",
            branch,
            "--job-id",
            job_id,
            "--output",
            "json",
        ],
    )
    job = payload.get("job")
    if isinstance(job, dict):
        summary = job.get("summary")
        if isinstance(summary, dict):
            return str(summary.get("status") or "")
    return ""


def _wait(run_aws: Runner, app_id: str, branch: str, job_id: str, polls: int, interval: float) -> None:
    for _ in range(polls):
        status = _job_status(run_aws, app_id, branch, job_id)
        print(f"Amplify job {job_id} status: {status}")
        if status in TERMINAL_OK:
            return
        if status in TERMINAL_BAD:
            raise AmplifyError(f"Amplify job {job_id} {status}")
        if interval:
            time.sleep(interval)
    raise AmplifyError(f"Amplify job {job_id} did not finish")


def _source_is_green(run_aws: Runner, app_id: str, source: str) -> None:
    payload = _aws_json(
        run_aws,
        [
            "aws",
            "amplify",
            "list-jobs",
            "--app-id",
            app_id,
            "--branch-name",
            source,
            "--max-items",
            "1",
            "--output",
            "json",
        ],
    )
    summaries = payload.get("jobSummaries")
    status = ""
    if isinstance(summaries, list) and summaries and isinstance(summaries[0], dict):
        status = str(summaries[0].get("status") or "")
    print(f"Latest job status on {source}: {status or 'None'}")
    if status != "SUCCEED":
        raise AmplifyError("Source branch build is not green")


def release(
    *,
    app_id: str,
    branch: str,
    mode: str,
    source_branch: str,
    wait: bool,
    allowed_source: str,
    allowed_target: str,
    polls: int,
    interval: float,
    run_aws: Runner,
) -> None:
    if not app_id:
        raise AmplifyError("app-id is required")
    if not branch:
        raise AmplifyError("branch is required")
    if mode == "promote":
        if not source_branch:
            raise AmplifyError("source-branch is required when mode is promote")
        if allowed_source and source_branch != allowed_source:
            raise AmplifyError("Only staging -> main promotions are allowed")
        if allowed_target and branch != allowed_target:
            raise AmplifyError("Only staging -> main promotions are allowed")
        _source_is_green(run_aws, app_id, source_branch)
    elif mode != "release":
        raise AmplifyError(f"Unsupported mode: {mode}")
    job_id = _start_job(run_aws, app_id, branch)
    if wait:
        _wait(run_aws, app_id, branch, job_id, polls, interval)


def main(run_aws: Runner = _run_aws) -> int:
    try:
        release(
            app_id=os.environ.get("APP_ID", ""),
            branch=os.environ.get("BRANCH", ""),
            mode=os.environ.get("MODE", "release") or "release",
            source_branch=os.environ.get("SOURCE_BRANCH", ""),
            wait=_truthy(os.environ.get("WAIT", ""), True),
            allowed_source=os.environ.get("ALLOWED_SOURCE", "staging"),
            allowed_target=os.environ.get("ALLOWED_TARGET", "main"),
            polls=int(os.environ.get("MAX_POLLS", "60") or "60"),
            interval=float(os.environ.get("POLL_INTERVAL", "10") or "10"),
            run_aws=run_aws,
        )
    except AmplifyError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
