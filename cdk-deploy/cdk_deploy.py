"""Deploy CDK stacks from a parameters file.

The caller describes stack order and parameter routing. This does not
assume a role, and it does not print an account id, a parameter value,
or a secret. Fixture jobs stub ``aws`` and ``npx``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from cdk_plan import (  # noqa: E402
    FATAL,
    DeployError,
    _check_allowlist,
    _load_object,
    _print_log,
    _redact,
    _resolve_file,
    build_commands,
    load_plan_text,
    resolve_selection,
)

DEFAULT_ROLLBACK = "is in UPDATE_ROLLBACK_FAILED state and can not be updated"

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]
Sleeper = Callable[[int], None]


def _region(region: str) -> list[str]:
    return ["--region", region] if region else []


def _aws(run: Runner, command: list[str]) -> tuple[int, str]:
    result = run(command)
    text = f"{result.stdout or ''}{result.stderr or ''}"
    return result.returncode, text


def _should_skip(run: Runner, stack: str, resource: str, region: str) -> bool:
    code, resources = _aws(
        run,
        [
            "aws", "cloudformation", "describe-stack-resources",
            "--stack-name", stack, *_region(region),
            "--query",
            "StackResources[?ResourceStatus=='UPDATE_FAILED' || ResourceStatus=='UPDATE_ROLLBACK_FAILED'].LogicalResourceId",
            "--output", "text",
        ],
    )
    events_code, events = _aws(
        run,
        [
            "aws", "cloudformation", "describe-stack-events",
            "--stack-name", stack, *_region(region),
            "--max-items", "50",
            "--query",
            f"StackEvents[?contains(LogicalResourceId, '{resource}')].[ResourceStatus,ResourceStatusReason]",
            "--output", "text",
        ],
    )
    blob = f"{resources if code == 0 else ''}\n{events if events_code == 0 else ''}"
    return resource in blob or "Can't locate revision" in blob or "did not finish" in blob


def _continue_rollback(run: Runner, stack: str, resource: str, region: str, skip: bool) -> bool:
    command = [
        "aws", "cloudformation", "continue-update-rollback",
        "--stack-name", stack, *_region(region),
    ]
    if skip and resource:
        command.extend(["--resources-to-skip", resource])
        print(f"Stack {stack} continue-update-rollback skips {resource}.")
    else:
        print(f"Stack {stack} is in UPDATE_ROLLBACK_FAILED; calling continue-update-rollback.")
    code, output = _aws(run, command)
    _print_log(output)
    if code != 0:
        if resource and not skip and resource in output:
            print(f"Retrying continue-update-rollback for {stack} with {resource} skipped.")
            return _continue_rollback(run, stack, resource, region, True)
        print(f"continue-update-rollback failed for {stack}.")
        return False
    print(f"Waiting for {stack} to reach UPDATE_ROLLBACK_COMPLETE.")
    waited, _wait_output = _aws(
        run,
        ["aws", "cloudformation", "wait", "stack-rollback-complete", "--stack-name", stack, *_region(region)],
    )
    if waited != 0 and resource and not skip:
        print(f"Retrying continue-update-rollback for {stack} with {resource} skipped.")
        return _continue_rollback(run, stack, resource, region, True)
    return waited == 0


def _recover(
    run: Runner,
    stacks: list[str],
    log: str,
    match: str,
    resource: str,
    region: str,
) -> bool:
    if re.search(re.escape(match), log, re.IGNORECASE) is None:
        return True
    print("Detected UPDATE_ROLLBACK_FAILED; attempting continue-update-rollback before retry.")
    for stack in stacks:
        code, status = _aws(
            run,
            [
                "aws", "cloudformation", "describe-stacks",
                "--stack-name", stack, *_region(region),
                "--query", "Stacks[0].StackStatus", "--output", "text",
            ],
        )
        if code != 0 or status.strip() != "UPDATE_ROLLBACK_FAILED":
            continue
        skip = bool(resource) and _should_skip(run, stack, resource, region)
        if _continue_rollback(run, stack, resource, region, skip):
            continue
        if resource:
            return False
        print(f"continue-update-rollback failed for {stack}; the next deploy attempt will report the wedged state.")
    return True


def run_commands(
    commands: list[tuple[list[str], list[str]]],
    *,
    attempts: int,
    rollback_match: str,
    skip_resource: str,
    region: str,
    run: Runner,
    sleep: Sleeper,
) -> int:
    for command, stacks in commands:
        if command[:2] == ["cdk-deploy", "allowlist"]:
            _check_allowlist(os.environ.get(command[2], ""))
            continue
        if command[2] == "destroy":
            code, output = _aws(run, command)
            _print_log(output)
            if code != 0:
                return code
            continue
        exit_code = 1
        for attempt in range(1, attempts + 1):
            print(f"CDK deploy attempt {attempt} of {attempts}")
            exit_code, output = _aws(run, command)
            _print_log(output)
            if exit_code == 0:
                break
            if FATAL.search(output):
                print("Detected non-retryable CloudFormation error; failing fast without additional retries.")
                return exit_code
            if attempt == attempts:
                return exit_code
            if not _recover(run, stacks, output, rollback_match, skip_resource, region):
                print("Could not recover the wedged stack.")
                return exit_code
            delay = 45 * attempt
            print(f"CDK deploy failed (exit {exit_code}); waiting {delay}s before retry...")
            sleep(delay)
        if exit_code != 0:
            return exit_code
    return 0


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def main(run: Runner = _run, sleep: Sleeper = time.sleep) -> int:
    try:
        plan = load_plan_text(os.environ.get("PLAN") or "", os.environ.get("PLAN_FILE") or "")
        path = _resolve_file(os.environ.get("PARAM_FILE", ""))
        parameters = _load_object(path) if path else None
        directory = os.environ.get("WORKING_DIRECTORY", "")
        if directory:
            os.chdir(directory)
        attempts = int(os.environ.get("ATTEMPTS", "1") or "1")
        commands = build_commands(
            plan=plan,
            parameters=parameters,
            fmt=os.environ.get("FORMAT", "prefixed-json") or "prefixed-json",
            selected_stacks=resolve_selection(plan, os.environ.get("STACKS", "")),
            pass_empty={part for part in os.environ.get("PASS_EMPTY", "").split(",") if part},
            escape_newlines=os.environ.get("ESCAPE_NEWLINES", "false").lower() == "true",
            no_notices=os.environ.get("NO_NOTICES", "false").lower() == "true",
            destroy=os.environ.get("DESTROY", "false").lower() == "true",
            run_seed=os.environ.get("RUN_SEED", "false").lower() == "true",
        )
        code = run_commands(
            commands,
            attempts=attempts,
            rollback_match=os.environ.get("ROLLBACK_MATCH", DEFAULT_ROLLBACK) or DEFAULT_ROLLBACK,
            skip_resource=os.environ.get("SKIP_RESOURCE", ""),
            region=os.environ.get("REGION") or os.environ.get("AWS_REGION", ""),
            run=run,
            sleep=sleep,
        )
    except (DeployError, json.JSONDecodeError, OSError, ValueError) as error:
        print(_redact(str(error)), file=sys.stderr)
        return 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
