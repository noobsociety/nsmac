#!/usr/bin/env bash
# Contract: tools/command-system/placement-audit-contract.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_CONFIG_ROOT="${COMMAND_CONFIG_ROOT:-$ROOT}"
MODE="post-migration"

usage() {
  cat <<'USAGE'
Usage: ./tools/command-system/audit-placement.sh [--migration]

Options:
  --migration  Include flat commands/<ns>.md sources while a namespace move is in progress.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --migration)
      MODE="migration"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "audit-placement: unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

python3 - "$COMMAND_CONFIG_ROOT" "$MODE" <<'PY'
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

root = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
commands_dir = root / "commands"
markdown_link = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def normalize_target(source: Path, raw: str) -> str | None:
    target = raw.split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    target = unquote(target)
    if target.startswith("/"):
        candidate = (root / target.lstrip("/")).resolve()
    else:
        candidate = (source.parent / target).resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError:
        return None


references: dict[str, set[str]] = defaultdict(set)
known_namespaces = {
    path.stem
    for path in commands_dir.glob("*.md")
    if path.name not in {"commands.md", "index.md"}
}
known_namespaces.update(path.parent.name for path in commands_dir.glob("*/index.md"))
known_namespaces.update(path.parent.parent.name for path in commands_dir.glob("*/*/index.md"))


def source_files() -> list[Path]:
    files = list(commands_dir.glob("*/*/index.md"))
    if mode == "migration":
        files.extend(
            path
            for path in commands_dir.glob("*.md")
            if path.name not in {"commands.md", "index.md"}
        )
    return sorted(set(files))


def source_namespace(source: str) -> str | None:
    parts = Path(source).parts
    if len(parts) >= 4 and parts[0] == "commands" and parts[3] == "index.md":
        return parts[1]
    if len(parts) == 2 and parts[0] == "commands" and parts[1].endswith(".md"):
        name = Path(parts[1]).stem
        if name not in {"commands", "index"}:
            return name
    return None


def slash_target(parts: list[str]) -> str | None:
    if len(parts) < 3 or not parts[0].startswith("/"):
        return None
    return parts[-1]


for source in source_files():
    rel_source = source.relative_to(root).as_posix()
    for line in source.read_text().splitlines():
        for match in markdown_link.finditer(line):
            target = normalize_target(source, match.group(1))
            if target:
                references[target].add(rel_source)
        stripped = line.strip()
        if not stripped.startswith("/"):
            continue
        parts = stripped.split()
        raw_target = slash_target(parts)
        if raw_target:
            target = normalize_target(source, raw_target)
            if target:
                references[target].add(rel_source)

failures = 0
for target, sources in sorted(references.items()):
    if len(sources) < 2:
        continue
    if mode == "migration" and target.startswith("core/framework/"):
        continue
    namespace_sources: dict[str, list[str]] = defaultdict(list)
    for source in sorted(sources):
        namespace = source_namespace(source)
        if namespace:
            namespace_sources[namespace].append(source)

    if len(namespace_sources) > 1:
        if target.startswith("core/framework/"):
            continue
        core_parts = Path(target).parts
        is_namespace_core = (
            len(core_parts) >= 2
            and core_parts[0] == "core"
            and core_parts[1] in known_namespaces
        )
        if not target.startswith("core/") or is_namespace_core:
            print(f"ERROR: cross-namespace shared file must move to core/: {target}", file=sys.stderr)
            print(f"  referenced by: {', '.join(sorted(sources))}", file=sys.stderr)
            failures += 1
        continue

    for ns, ns_sources in sorted(namespace_sources.items()):
        if target.startswith("core/framework/"):
            continue
        if len(ns_sources) >= 2 and not target.startswith(f"core/{ns}/"):
            print(f"ERROR: shared file must move to core/{ns}/: {target}", file=sys.stderr)
            print(f"  referenced by: {', '.join(ns_sources)}", file=sys.stderr)
            failures += 1

if failures:
    sys.exit(1)

print("audit-placement: OK")
PY
