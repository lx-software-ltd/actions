"""Shared CDK plan loading.

cdk-deploy and cdk-diff both import this module. Neither action imports
the other. An empty ``{NAME}`` stays in the argument so CloudFormation
clears the previous value.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ACCOUNT_ID = re.compile(r"\b\d{12}\b")
FATAL = re.compile(
    r'HandlerErrorCode: (?:InvalidRequest|AlreadyExists)|must be in ARN format or "\*"|already exists\.',
    re.IGNORECASE,
)
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SECRET = re.compile(r"^<FROM_GITHUB_SECRET:\s*([^>]+?)\s*>$")
VARIABLE = re.compile(r"^<FROM_GITHUB_VAR:\s*([^>]+?)\s*>$")
ENV_TOKEN = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


class DeployError(Exception):
    """The deploy cannot run."""


def _redact(text: str) -> str:
    return ACCOUNT_ID.sub("************", text)


def _print_log(text: str) -> None:
    cleaned = _redact(text)
    if cleaned:
        print(cleaned, end="" if cleaned.endswith("\n") else "\n")


def _resolve_file(path: str) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_file():
        return candidate
    workspace = os.environ.get("GITHUB_WORKSPACE", "")
    if workspace and (Path(workspace) / path).is_file():
        return Path(workspace) / path
    raise DeployError(f"CDK_PARAM_FILE '{path}' not found")


def _as_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _normalize(value: object, escape_newlines: bool) -> str:
    text = _as_text(value).replace("\r\n", "\n").replace("\r", "\n")
    if escape_newlines:
        text = text.replace("\n", "\\n")
    return text.strip(" ")


def _placeholder(text: str) -> str:
    secret = SECRET.fullmatch(text)
    if secret:
        return os.environ.get(secret.group(1), "")
    variable = VARIABLE.fullmatch(text)
    if variable:
        return os.environ.get(variable.group(1), "")
    return text


def _load_object(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DeployError("parameters file must be a JSON object")
    return data


def _group_list(plan: dict[str, object]) -> list[dict[str, object]]:
    groups = plan.get("groups")
    if not isinstance(groups, list) or not all(isinstance(group, dict) for group in groups):
        raise DeployError("plan.groups must list the deploys")
    if not groups:
        raise DeployError("plan.groups must list at least one deploy")
    return groups


def _selected(plan: dict[str, object], stacks: list[str]) -> set[str]:
    if stacks:
        return set(stacks)
    names: set[str] = set()
    for group in _group_list(plan):
        names.update(str(name) for name in group.get("stacks") or [])
    return names


def _prefixes(groups: list[dict[str, object]]) -> list[str]:
    return [str(prefix) for group in groups for prefix in group.get("prefixes") or []]


def _matching_prefix(key: str, prefixes: list[str]) -> str:
    matches = [prefix for prefix in prefixes if key.startswith(prefix)]
    if not matches:
        return ""
    return max(matches, key=len)


def _prefixed_key(key: str, unprefixed_prefix: str) -> str:
    if ":" in key:
        return key
    if not unprefixed_prefix:
        raise DeployError("unknown parameter key prefix")
    return f"{unprefixed_prefix}{key}"


def _prefixed_value(raw: object) -> str:
    if isinstance(raw, str):
        return _normalize(_placeholder(raw.strip()), True)
    return _normalize(raw, True)


def _prefixed_args(
    data: dict[str, object],
    groups: list[dict[str, object]],
    selected: set[str],
    pass_empty: set[str],
    unprefixed_prefix: str,
) -> dict[int, list[str]]:
    prefixes = _prefixes(groups)
    if not prefixes:
        raise DeployError("prefixed-json groups need prefixes")
    by_group = {index: [] for index in range(len(groups))}
    for key, raw in data.items():
        if raw is None:
            continue
        text = _prefixed_key(str(key), unprefixed_prefix)
        prefix = _matching_prefix(text, prefixes)
        if not prefix:
            raise DeployError("unknown parameter key prefix")
        value = _prefixed_value(raw)
        name = text[len(prefix) :]
        if name not in pass_empty and value == "":
            continue
        for index, group in enumerate(groups):
            group_prefixes = [str(item) for item in group.get("prefixes") or []]
            stacks = [str(item) for item in group.get("stacks") or []]
            if prefix in group_prefixes and any(stack in selected for stack in stacks):
                by_group[index].extend(["--parameters", f"{text}={value}"])
    return by_group


def _route_stacks(plan: dict[str, object], key: str, value: str) -> list[str]:
    api = str(plan.get("api-stack") or "")
    also_api = {str(name) for name in plan.get("also-api") or []}
    targets: list[str] = []
    for route in plan.get("routes") or []:
        if not isinstance(route, dict):
            continue
        names = {str(item) for item in route.get("parameters") or []}
        if key not in names:
            continue
        skip_empty = {str(item) for item in route.get("skip-empty") or []}
        if key in skip_empty and value == "":
            continue
        targets.append(str(route.get("stack") or ""))
    if key in also_api and api and api not in targets:
        targets.append(api)
    if not targets and api:
        targets.append(api)
    return [target for target in targets if target]


def _plain_args(
    data: dict[str, object],
    plan: dict[str, object],
    selected: set[str],
    pass_empty: set[str],
    escape_newlines: bool,
) -> dict[int, list[str]]:
    groups = _group_list(plan)
    by_group: dict[int, list[str]] = {index: [] for index in range(len(groups))}
    for key, raw in data.items():
        value = "" if raw is None else _plain_value(raw, escape_newlines)
        if str(key) not in pass_empty and value == "":
            continue
        for stack in _route_stacks(plan, str(key), value):
            if stack not in selected:
                continue
            for index, group in enumerate(groups):
                if stack in [str(item) for item in group.get("stacks") or []]:
                    by_group[index].extend(["--parameters", f"{stack}:{key}={value}"])
    return by_group


def _plain_value(raw: object, escape_newlines: bool) -> str:
    text = _placeholder(raw.strip()) if isinstance(raw, str) else _as_text(raw)
    if not escape_newlines:
        return text
    return _normalize(text, True)


def _check_allowlist(value: str) -> None:
    if value.strip() == "":
        raise DeployError("ADMIN_FEDERATED_EMAIL_ALLOWLIST is empty.")
    trimmed = value.strip()
    if trimmed.endswith(","):
        raise DeployError(
            "ADMIN_FEDERATED_EMAIL_ALLOWLIST entry "
            f"{trimmed.count(',') + 1} is not an email address."
        )
    for index, entry in enumerate(trimmed.split(","), start=1):
        if EMAIL.fullmatch(entry.strip()) is None:
            raise DeployError(
                f"ADMIN_FEDERATED_EMAIL_ALLOWLIST entry {index} is not an email address."
            )


def _append_if_set(group: dict[str, object]) -> list[str]:
    args: list[str] = []
    for entry in group.get("append-if-set") or []:
        if not isinstance(entry, dict):
            continue
        parameter = str(entry.get("parameter") or "")
        env_name = str(entry.get("env") or "")
        if os.environ.get(env_name, ""):
            print(f"Passing {parameter} from the environment")
            args.extend(["--parameters", f"{parameter}={os.environ[env_name]}"])
        else:
            print(f"{env_name} is unset; CloudFormation keeps the previous value")
    return args


def _apply_seed(args: list[str], api_stack: str) -> list[str]:
    prefix = f"{api_stack}:RunSeedData="
    kept: list[str] = []
    index = 0
    while index < len(args):
        if (
            args[index] == "--parameters"
            and index + 1 < len(args)
            and str(args[index + 1]).startswith(prefix)
        ):
            index += 2
            continue
        kept.append(args[index])
        index += 1
    print(f"RunSeedData override enabled for {api_stack}.")
    kept.extend(["--parameters", f"{api_stack}:RunSeedData=true"])
    return kept


def _deploy_command(stacks: list[str], args: list[str], extra: list[str], no_notices: bool) -> list[str]:
    command = ["npx", "cdk", "deploy", "--require-approval", "never"]
    if no_notices:
        command.append("--no-notices")
    return [*command, *args, *extra, *stacks]


def _destroy_command(stacks: list[str], no_notices: bool) -> list[str]:
    command = ["npx", "cdk", "destroy"]
    if no_notices:
        command.append("--no-notices")
    command.append("--force")
    return [*command, *stacks]


def build_commands(
    *,
    plan: dict[str, object],
    parameters: dict[str, object] | None,
    fmt: str,
    selected_stacks: list[str],
    pass_empty: set[str],
    escape_newlines: bool,
    no_notices: bool,
    destroy: bool,
    run_seed: bool,
) -> list[tuple[list[str], list[str]]]:
    """Return ``(argv, stack names)`` for destroy and each deploy group."""
    groups = _group_list(plan)
    selected = _selected(plan, selected_stacks)
    if parameters is None:
        grouped: dict[int, list[str]] = {}
    elif fmt == "prefixed-json":
        grouped = _prefixed_args(
            parameters,
            groups,
            selected,
            pass_empty,
            str(plan.get("unprefixed-prefix") or ""),
        )
    elif fmt == "plain-json":
        grouped = _plain_args(parameters, plan, selected, pass_empty, escape_newlines)
    else:
        raise DeployError(f"Unsupported format: {fmt}")
    api = str(plan.get("api-stack") or "")
    commands: list[tuple[list[str], list[str]]] = []
    if destroy and selected:
        names: list[str] = []
        for group in groups:
            for name in group.get("stacks") or []:
                text = str(name)
                if text in selected and text not in names:
                    names.append(text)
        commands.append((_destroy_command(names, no_notices), names))
    seed_skipped = False
    for index, group in enumerate(groups):
        stacks = [str(item) for item in group.get("stacks") or [] if str(item) in selected]
        if not stacks:
            continue
        required = [str(item) for item in group.get("when-all-env") or []]
        if any(not os.environ.get(name) for name in required):
            print(f"::notice::Skipping {' '.join(stacks)} because a required environment value is unset.")
            continue
        allowlist_env = str(group.get("allowlist-env") or "")
        if allowlist_env:
            commands.append((["cdk-deploy", "allowlist", allowlist_env], []))
        args = list(grouped.get(index, []))
        args.extend(_append_if_set(group))
        if run_seed and api in stacks:
            args = _apply_seed(args, api)
        elif run_seed and api and api not in selected and not seed_skipped:
            print("run_seed_data=true requested, but the API stack is not selected; skipping seed override.")
            seed_skipped = True
        extra = [str(item) for item in group.get("extra-args") or []]
        commands.append((_deploy_command(stacks, args, extra, no_notices), stacks))
    return commands


def _expand_token(text: str) -> str:
    """Replace ``{NAME}`` from the environment. An unset name is empty."""
    return ENV_TOKEN.sub(lambda match: os.environ.get(match.group(1), ""), text)


def _expand_extra(extra: list[object]) -> list[object]:
    """Expand tokens and keep an empty value. The argument is not dropped."""
    expanded: list[object] = []
    for item in extra:
        if not isinstance(item, str):
            expanded.append(item)
            continue
        expanded.append(_expand_token(item))
    return expanded


def load_plan_text(plan: str, plan_file: str) -> dict[str, object]:
    """Read the plan JSON from the string or the file, not from both."""
    if plan.strip() and plan_file.strip():
        raise DeployError("Set plan or plan-file, not both")
    raw = plan
    if plan_file.strip():
        path = _resolve_file(plan_file.strip())
        if path is None:
            raise DeployError("Set plan or plan-file")
        raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise DeployError("Set plan or plan-file")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DeployError("plan must be JSON") from exc
    if not isinstance(data, dict):
        raise DeployError("plan must be a JSON object")
    groups = data.get("groups")
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            extra = group.get("extra-args")
            if isinstance(extra, list):
                group["extra-args"] = _expand_extra(extra)
    return data


def _routing_plan(plan: dict[str, object]) -> dict[str, object]:
    """The same groups without deploy-only extras, for a diff."""
    groups = plan.get("groups")
    if not isinstance(groups, list):
        return plan
    copied_groups: list[object] = []
    for group in groups:
        if not isinstance(group, dict):
            copied_groups.append(group)
            continue
        copied = dict(group)
        for key in ("extra-args", "append-if-set", "allowlist-env", "when-all-env"):
            copied.pop(key, None)
        copied_groups.append(copied)
    routed = dict(plan)
    routed["groups"] = copied_groups
    return routed


def parameter_arguments(
    *,
    plan: dict[str, object],
    parameters: dict[str, object] | None,
    fmt: str,
    selected_stacks: list[str],
    pass_empty: set[str],
    escape_newlines: bool,
    include_extras: bool,
) -> list[str]:
    """The ``--parameters`` arguments the deploy would pass."""
    source = plan if include_extras else _routing_plan(plan)
    commands = build_commands(
        plan=source,
        parameters=parameters,
        fmt=fmt,
        selected_stacks=selected_stacks,
        pass_empty=pass_empty,
        escape_newlines=escape_newlines,
        no_notices=False,
        destroy=False,
        run_seed=False,
    )
    collected: list[str] = []
    for argv, _stacks in commands:
        index = 0
        while index < len(argv):
            if argv[index] == "--parameters" and index + 1 < len(argv):
                collected.extend(argv[index : index + 2])
                index += 2
                continue
            index += 1
    return collected
