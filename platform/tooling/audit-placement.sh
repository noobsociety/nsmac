#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_CONFIG_ROOT="${COMMAND_CONFIG_ROOT:-$ROOT}"

python3 - "$COMMAND_CONFIG_ROOT" <<'PY'
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from urllib.parse import unquote

root = Path(sys.argv[1]).resolve()
commands_dir = root / "commands"
legacy_dirs = [
    root / "core",
    root / "tools",
    root / "templates",
    root / "data",
]
markdown_link = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
failures: list[str] = []

for path in legacy_dirs:
    if path.exists():
        failures.append(f"legacy root path remains after vertical-slice move: {path.relative_to(root).as_posix()}")


def namespace_for(path: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(root)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "commands":
        if len(parts) == 2 and parts[1] == "commands.md":
            return None
        return parts[1]
    return None


def rel(path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def normalized_link_target(source: Path, raw: str) -> Path | None:
    target = raw.split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    target = unquote(target)
    if target.startswith("/"):
        candidate = (root / target.lstrip("/")).resolve()
    else:
        candidate = (source.parent / target).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def imported_command_namespace(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == "commands":
        if len(parts) == 2 and parts[1] == "commands.md":
            return None
        return parts[1]
    return None

for source in sorted(commands_dir.rglob("*.py")) if commands_dir.exists() else []:
    source_ns = namespace_for(source)
    if not source_ns:
        continue
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except SyntaxError as exc:
        failures.append(f"{rel(source)}: cannot parse Python for slice audit: {exc}")
        continue
    for node in ast.walk(tree):
        module = ""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                target_ns = imported_command_namespace(module)
                if target_ns and target_ns != source_ns:
                    failures.append(f"{rel(source)}: cross-slice import `{module}` targets commands/{target_ns}/")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            module = node.module
            target_ns = imported_command_namespace(module)
            if target_ns and target_ns != source_ns:
                failures.append(f"{rel(source)}: cross-slice import `from {module} ...` targets commands/{target_ns}/")

for source in sorted(commands_dir.rglob("*.md")) if commands_dir.exists() else []:
    source_ns = namespace_for(source)
    if not source_ns:
        continue
    text = source.read_text(encoding="utf-8")
    for match in markdown_link.finditer(text):
        target = normalized_link_target(source, match.group(1))
        if not target:
            continue
        target_ns = namespace_for(target)
        if target_ns and target_ns != source_ns:
            failures.append(f"{rel(source)}: cross-slice markdown link `{match.group(1)}` targets commands/{target_ns}/")

if failures:
    for item in failures:
        print(f"ERROR: {item}", file=sys.stderr)
    sys.exit(1)

print("audit-placement: OK")
PY
