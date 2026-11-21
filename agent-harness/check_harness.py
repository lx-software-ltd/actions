#!/usr/bin/env python3
"""Run the agent harness from .github/harness.json.

The config carries the lists and limits that differ between repositories.
The messages match the scripts this action replaces.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
WHY_SHA = re.compile(r"\b([0-9a-f]{7,40})\b")
FOCUSED = re.compile(r"\.only\s*\(|\bfit\s*\(|\bfdescribe\s*\(|\bxit\s*\(|\bxdescribe\s*\(")
UNCONDITIONAL_SKIP = re.compile(r"\b(?:test|it|describe|context)\.skip\s*\(\s*(?:\)|['\"`])")
UNITTEST_SKIP = re.compile(r"@unittest\.skip(?!If)\b")
PAIR_B_JS = re.compile(
    r"(\.only\s*\(|\bfit\s*\(|\bfdescribe\s*\(|\bxit\s*\(|\bxdescribe\s*\(|"
    r"\bdescribe\.skip\s*\(|\bit\.skip\s*\(|\btest\.skip\s*\(|\bcontext\.skip\s*\()"
)
PAIR_B_PY = re.compile(r"@pytest\.mark\.skip\b(?!if)")


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _front_matter(text: str) -> dict[str, str]:
    match = FRONT_MATTER.match(text)
    if not match:
        raise ValueError("missing front matter")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith(" "):
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def _body(text: str) -> str:
    match = FRONT_MATTER.match(text)
    if not match:
        return text
    return text[match.end() :]


def _repo_is_shallow(root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "true"


def _why_is_real(tag: str, root: Path) -> bool:
    shas = WHY_SHA.findall(tag)
    if not shas:
        return "convention" in tag
    for sha in shas:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            return False
    return True


def _check_rule(
    name: str,
    path: Path,
    *,
    always: bool,
    limit: int,
    verify_commits: bool,
    root: Path,
) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    count = len(_lines(path))
    if count > limit:
        errors.append(f"{name} is {count} lines; limit is {limit}")
    try:
        fields = _front_matter(text)
    except ValueError as exc:
        return [*errors, f"{name}: {exc}"]
    expected = "true" if always else "false"
    if fields.get("alwaysApply") != expected:
        errors.append(f"{name} alwaysApply must be {expected}")
    if not always and not fields.get("globs"):
        errors.append(f"{name} must set globs")
    if always and fields.get("globs"):
        errors.append(f"{name} is always applied and must not set globs")
    body = _body(text)
    match = FRONT_MATTER.match(text)
    start = text[: match.end()].count("\n") + 1 if match else 1
    shallow = _repo_is_shallow(root) if verify_commits else False
    for offset, line in enumerate(body.splitlines()):
        if not line.startswith("- "):
            continue
        line_number = start + offset
        if "[why:" not in line:
            errors.append(f"{name}:{line_number} rule bullet is missing [why:]")
            continue
        if not verify_commits:
            continue
        tag = line.split("[why:", 1)[1]
        if _why_is_real(tag, root):
            continue
        if shallow and WHY_SHA.findall(tag):
            errors.append(
                f"{name}:{line_number} [why:] commit is not in this shallow clone; fetch full history (fetch-depth: 0)"
            )
            continue
        errors.append(f"{name}:{line_number} [why:] is not a known commit or convention")
    return errors


def _check_rule_presence(name: str, path: Path, *, always: bool, limit: int) -> list[str]:
    """evolvesprouts: [why:] must be present, and the line number is the body line."""
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    count = len(_lines(path))
    if count > limit:
        errors.append(f"{name} is {count} lines; limit is {limit}")
    try:
        fields = _front_matter(text)
    except ValueError as exc:
        errors.append(f"{name}: {exc}")
        return errors
    expected = "true" if always else "false"
    if fields.get("alwaysApply") != expected:
        errors.append(f"{name} alwaysApply must be {expected}")
    if not always and not fields.get("globs"):
        errors.append(f"{name} must set globs")
    if always and fields.get("globs"):
        errors.append(f"{name} is always applied and must not set globs")
    for line_number, line in enumerate(_body(text).splitlines(), start=1):
        if line.startswith("- ") and "[why:" not in line:
            errors.append(f"{name}:{line_number} rule bullet is missing [why:]")
    return errors


def check_rules(root: Path, cfg: dict) -> list[str]:
    errors: list[str] = []
    agents_limit = int(cfg["agents-limit"])
    rule_limit = int(cfg["rule-limit"])
    skill_limit = int(cfg["skill-limit"])
    pointer_limit = int(cfg["pointer-limit"])
    core = cfg["core-rule"]
    required_rules = cfg["required-rules"]
    required_skills = list(cfg["required-skills"])
    agents = root / "AGENTS.md"
    pointer = root / ".cursorrules"
    if not agents.exists():
        errors.append("Missing AGENTS.md")
    else:
        count = len(_lines(agents))
        if count > agents_limit:
            errors.append(f"AGENTS.md is {count} lines; limit is {agents_limit}")
        text = agents.read_text(encoding="utf-8")
        for required in cfg["agents-phrases"]:
            if required not in text:
                errors.append(f"AGENTS.md is missing {required}")
    if not pointer.exists():
        errors.append("Missing .cursorrules pointer")
    else:
        count = len(_lines(pointer))
        text = pointer.read_text(encoding="utf-8")
        if count > pointer_limit:
            errors.append(f".cursorrules is {count} lines; keep it a pointer of at most {pointer_limit}")
        if "AGENTS.md" not in text or ".cursor/rules/" not in text:
            errors.append(".cursorrules must point at AGENTS.md and .cursor/rules/")
    for relative in cfg["required-files"]:
        if not (root / relative).exists():
            errors.append(f"Missing {relative}")

    rules_dir = root / ".cursor" / "rules"
    found = {path.name: path for path in rules_dir.glob("*.mdc")} if rules_dir.exists() else {}
    extra = cfg["extra-rules"]
    verify = bool(cfg.get("verify-why-commits"))
    for name, always in required_rules.items():
        path = found.get(name)
        if path is None:
            errors.append(f"Missing rule {name}")
            continue
        if extra == "full":
            continue
        if verify:
            errors.extend(_check_rule(name, path, always=bool(always), limit=rule_limit, verify_commits=True, root=root))
        else:
            errors.extend(_check_rule_presence(name, path, always=bool(always), limit=rule_limit))
    if extra == "full":
        for name, path in sorted(found.items()):
            errors.extend(
                _check_rule(name, path, always=name == core, limit=rule_limit, verify_commits=verify, root=root)
            )
    else:
        for name, path in sorted(found.items()):
            if name in required_rules:
                continue
            try:
                fields = _front_matter(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
                continue
            if fields.get("alwaysApply") == "true":
                errors.append(f"Only {core} may set alwaysApply: true ({name})")

    skills_dir = root / ".cursor" / "skills"
    found_skills = {path.parent.name for path in skills_dir.glob("*/SKILL.md")} if skills_dir.exists() else set()
    for skill in sorted(set(required_skills) - found_skills):
        errors.append(f"Missing skill {skill}")
    scope = found_skills if cfg.get("skills") == "all" else set(required_skills) & found_skills
    for skill in sorted(scope):
        path = skills_dir / skill / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        count = len(_lines(path))
        if count > skill_limit:
            errors.append(f"{skill}/SKILL.md is {count} lines; limit is {skill_limit}")
        try:
            fields = _front_matter(text)
        except ValueError as exc:
            errors.append(f"{skill}: {exc}")
            continue
        if fields.get("name") != skill:
            errors.append(f"{skill} front matter name must be {skill}")
        if not fields.get("description"):
            errors.append(f"{skill} is missing a description")
    return errors


def limit_for(rel: str, cfg: dict) -> int | None:
    path = Path(rel)
    if "node_modules" in path.parts or "dist" in path.parts:
        return None
    if rel.startswith(cfg["python-prefix"]) and path.suffix == ".py":
        if path.name.startswith("test_"):
            return None
        return int(cfg["python-limit"])
    if rel.endswith(cfg["generated-suffix"]):
        return None
    if path.suffix in {".ts", ".tsx"} and ".test." not in path.name and ".spec." not in path.name:
        if rel.startswith(cfg["typescript-app-prefix"]) and "/src/" in rel:
            return int(cfg["typescript-limit"])
        if rel.startswith(cfg["typescript-lib-prefix"]):
            return int(cfg["typescript-limit"])
    return None


def load_allowlist(root: Path, cfg: dict) -> dict[str, int]:
    allowlist_path = root / cfg["allowlist"]
    if not allowlist_path.exists():
        return {}
    allowed: dict[str, int] = {}
    for line_number, line in enumerate(allowlist_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            rel_path, count_text = stripped.rsplit(None, 1)
            count = int(count_text)
        except ValueError as exc:
            raise SystemExit(f"{allowlist_path}:{line_number}: expected '<path> <lines>'") from exc
        if rel_path in allowed:
            raise SystemExit(f"{allowlist_path}:{line_number}: duplicate entry for {rel_path}")
        ceiling = limit_for(rel_path, cfg)
        if ceiling is None:
            raise SystemExit(f"{allowlist_path}:{line_number}: {rel_path} is not a scanned file")
        if count <= ceiling:
            raise SystemExit(
                f"{allowlist_path}:{line_number}: {rel_path} allowance {count} is not above {ceiling}; remove it"
            )
        allowed[rel_path] = count
    return allowed


def length_problems(counts: dict[str, int], allowed: dict[str, int], cfg: dict) -> list[str]:
    errors: list[str] = []
    for rel, count in sorted(counts.items()):
        ceiling = limit_for(rel, cfg)
        if ceiling is None:
            continue
        allowance = allowed.get(rel)
        if count <= ceiling:
            if allowance is not None:
                errors.append(f"{rel} is {count} lines; remove it from the allowlist")
            continue
        if allowance is None:
            errors.append(f"{rel} is {count} lines (limit {ceiling}); split it or, if it already exists, allowlist {count}")
        elif count > allowance:
            errors.append(f"{rel} grew from {allowance} to {count} lines")
        elif count < allowance:
            errors.append(f"{rel} shrank from {allowance} to {count} lines; lower its allowlist entry")
    for rel in sorted(set(allowed) - set(counts)):
        errors.append(f"{rel} is allowlisted but was not found")
    return errors


def check_python_counted(root: Path, cfg: dict) -> list[str]:
    """evolvesprouts: counted allowlist, Alembic versions and dot paths skipped."""
    limit = int(cfg["limit"])
    allowlist_path = root / cfg["allowlist"]
    allowed: dict[str, int] = {}
    if allowlist_path.exists():
        for line_number, raw in enumerate(allowlist_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rel_path, count_text = line.rsplit(None, 1)
                count = int(count_text)
            except ValueError as exc:
                raise SystemExit(f"{allowlist_path}:{line_number}: expected '<path> <lines>'") from exc
            if count <= limit:
                raise SystemExit(
                    f"{allowlist_path}:{line_number}: {rel_path} allowance {count} is not above {limit}; remove it"
                )
            if rel_path in allowed:
                raise SystemExit(f"{allowlist_path}:{line_number}: duplicate entry for {rel_path}")
            allowed[rel_path] = count
    seen: set[str] = set()
    errors: list[str] = []
    for relative in cfg["scan-roots"]:
        scan = root / relative
        if not scan.exists():
            continue
        for path in scan.rglob("*.py"):
            parts = path.parts
            if "alembic" in parts:
                alembic_at = parts.index("alembic")
                if alembic_at + 1 < len(parts) and parts[alembic_at + 1] == "versions":
                    continue
            if any(part.startswith(".") for part in parts):
                continue
            rel = path.relative_to(root).as_posix()
            seen.add(rel)
            count = len(_lines(path))
            allowance = allowed.get(rel)
            if count <= limit:
                if allowance is not None:
                    errors.append(f"{rel} is {count} lines; remove it from the allowlist")
                continue
            if allowance is None:
                errors.append(f"{rel} is {count} lines (limit {limit}); split it or, if it already exists, allowlist {count}")
            elif count > allowance:
                errors.append(f"{rel} grew from {allowance} to {count} lines")
            elif count < allowance:
                errors.append(f"{rel} shrank from {allowance} to {count} lines; lower its allowlist entry")
    for rel in sorted(set(allowed) - seen):
        errors.append(f"{rel} is allowlisted but was not found")
    return errors


def check_python_names(root: Path, cfg: dict) -> list[str]:
    """siutindei: the allowlist names files and only shrinks."""
    limit = int(cfg["limit"])
    allowlist_path = root / cfg["allowlist"]
    allowed: list[str] = []
    if allowlist_path.exists():
        for line in allowlist_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            allowed.append(stripped)
    allowed_set = set(allowed)
    seen: set[str] = set()
    errors: list[str] = []
    for relative in cfg["scan-roots"]:
        scan = root / relative
        if not scan.exists():
            continue
        for path in scan.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            count = len(_lines(path))
            seen.add(rel)
            if count <= limit:
                continue
            if rel in allowed_set:
                continue
            errors.append(f"{rel} is {count} lines (max {limit})")
    for rel in sorted(allowed_set):
        path = root / rel
        if not path.exists():
            errors.append(f"allowlist entry does not exist: {rel}")
            continue
        if rel not in seen:
            errors.append(f"allowlist entry is outside the scan: {rel}")
            continue
        if len(_lines(path)) <= limit:
            errors.append(f"allowlist entry is now within {limit} lines; remove {rel}")
    return errors


def check_file_length(root: Path, cfg: dict) -> list[str]:
    mode = cfg.get("mode", "typed")
    if mode == "python-counted":
        return check_python_counted(root, cfg)
    if mode == "python-names":
        return check_python_names(root, cfg)
    allowed = load_allowlist(root, cfg)
    counts: dict[str, int] = {}
    for relative in cfg["scan-roots"]:
        scan = root / relative
        if not scan.exists():
            continue
        for path in scan.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {"node_modules", "dist"} for part in path.parts):
                continue
            rel = path.relative_to(root).as_posix()
            if limit_for(rel, cfg) is None:
                continue
            counts[rel] = len(_lines(path))
    return length_problems(counts, allowed, cfg)


def _is_test_file(path: Path, suffixes: set[str]) -> bool:
    if path.suffix not in suffixes:
        return False
    name = path.name
    if name.startswith("test_") or ".test." in name or ".spec." in name:
        return True
    return "e2e" in path.parts


def check_test_focus(root: Path, cfg: dict) -> list[str]:
    errors: list[str] = []
    suffixes = set(cfg["suffixes"])
    skip_parts = set(cfg.get("skip-parts", ["node_modules"]))
    mode = cfg["mode"]
    for relative in cfg["roots"]:
        scan = root / relative
        if not scan.exists():
            continue
        for path in scan.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip_parts for part in path.parts):
                continue
            if mode == "test-names":
                if not _is_test_file(path, suffixes):
                    continue
            elif path.suffix not in suffixes:
                continue
            rel = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if mode == "test-names":
                    problem = None
                    if FOCUSED.search(line) or UNCONDITIONAL_SKIP.search(line):
                        problem = line.strip()
                    elif path.suffix == ".py" and UNITTEST_SKIP.search(line) and not re.search(r"['\"]", line):
                        problem = line.strip()
                    if problem:
                        errors.append(f"{rel}:{line_number}: {problem}")
                else:
                    if PAIR_B_JS.search(line):
                        errors.append(f"{rel}:{line_number}: focused or skipped test: {line.strip()}")
                    if path.suffix == ".py" and PAIR_B_PY.search(line):
                        errors.append(f"{rel}:{line_number}: unconditional pytest skip: {line.strip()}")
    return errors


def run(root: Path, config_path: Path) -> list[str]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    errors = check_rules(root, cfg["rules"])
    if "file-length" in cfg:
        errors.extend(check_file_length(root, cfg["file-length"]))
    if "test-focus" in cfg:
        errors.extend(check_test_focus(root, cfg["test-focus"]))
    return errors


def main() -> int:
    root_text = os.environ.get("HARNESS_ROOT", "").strip()
    root = Path(root_text).resolve() if root_text else Path.cwd().resolve()
    config_text = os.environ.get("HARNESS_CONFIG", ".github/harness.json")
    config_path = Path(config_text)
    if not config_path.is_absolute():
        config_path = root / config_path
    if not config_path.is_file():
        print(f"agent-harness: missing {config_path}", file=sys.stderr)
        return 1
    errors = run(root, config_path)
    if errors:
        print("Agent harness check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Agent harness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
