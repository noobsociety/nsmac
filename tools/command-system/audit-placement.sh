#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_CONFIG_ROOT="${COMMAND_CONFIG_ROOT:-$ROOT}"

python3 - "$COMMAND_CONFIG_ROOT" <<'PY'
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

root = Path(sys.argv[1]).resolve()
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

for source in sorted(commands_dir.glob("*/*/index.md")):
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
        if len(parts) >= 3 and parts[0].startswith("/"):
            target = normalize_target(source, parts[2])
            if target:
                references[target].add(rel_source)

failures = 0
for target, sources in sorted(references.items()):
    if len(sources) < 2:
        continue
    namespace_sources: dict[str, list[str]] = defaultdict(list)
    for source in sorted(sources):
        parts = Path(source).parts
        if len(parts) >= 4 and parts[0] == "commands":
            namespace_sources[parts[1]].append(source)

    if len(namespace_sources) > 1:
        if not target.startswith("core/"):
            print(f"ERROR: cross-namespace shared file must move to core/: {target}", file=sys.stderr)
            print(f"  referenced by: {', '.join(sorted(sources))}", file=sys.stderr)
            failures += 1
        continue

    for ns, ns_sources in sorted(namespace_sources.items()):
        if len(ns_sources) >= 2 and not target.startswith(f"core/{ns}/"):
            print(f"ERROR: shared file must move to core/{ns}/: {target}", file=sys.stderr)
            print(f"  referenced by: {', '.join(ns_sources)}", file=sys.stderr)
            failures += 1

if failures:
    sys.exit(1)

print("audit-placement: OK")
PY
