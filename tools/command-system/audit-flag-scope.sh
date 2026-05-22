#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_CONFIG_ROOT="${COMMAND_CONFIG_ROOT:-$ROOT}"

python3 - "$COMMAND_CONFIG_ROOT" <<'PY'
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

root = Path(sys.argv[1]).resolve()
commands_dir = root / "commands"


@dataclass(frozen=True)
class FlagBlock:
    flag: str
    scope: str
    path: Path
    line: int
    override: str | None

    @property
    def field(self) -> str:
        return f"{self.path.relative_to(root)}:{self.line}"


def infer_scope(path: Path) -> str | None:
    rel = path.relative_to(commands_dir)
    parts = rel.parts
    if parts == ("index.md",):
        return "system"
    if len(parts) == 2 and parts[1] == "index.md":
        return "namespace"
    if len(parts) == 3 and parts[2] == "index.md":
        return "command"
    return None


def parse_route_flags(path: Path) -> list[FlagBlock]:
    scope = infer_scope(path)
    if scope is None:
        return []
    lines = path.read_text().splitlines()
    blocks: list[FlagBlock] = []
    in_block = False
    start_line = 0
    fields: dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        if not in_block and line.strip() == "```route-flag":
            in_block = True
            start_line = number
            fields = {}
            continue
        if in_block and line.strip() == "```":
            flag = fields.get("flag", "").strip()
            if flag:
                name = flag if flag.startswith("--") else f"--{flag}"
                blocks.append(
                    FlagBlock(
                        flag=name,
                        scope=scope,
                        path=path,
                        line=start_line,
                        override=fields.get("override"),
                    )
                )
            in_block = False
            continue
        if in_block and ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return blocks


def valid_override(text: str | None, parent: str) -> bool:
    if text is None:
        return False
    pattern = rf"^{re.escape(parent)} — \S.*$"
    return re.match(pattern, text) is not None


paths = sorted(commands_dir.glob("index.md"))
paths.extend(sorted(commands_dir.glob("*/index.md")))
paths.extend(sorted(commands_dir.glob("*/*/index.md")))

blocks_by_scope: dict[str, list[FlagBlock]] = {"system": [], "namespace": [], "command": []}
for path in paths:
    if path.exists():
        for block in parse_route_flags(path):
            blocks_by_scope[block.scope].append(block)

if not any(blocks_by_scope.values()):
    print("audit-flag-scope: OK (no restructured route-flag blocks)")
    sys.exit(0)

failures = 0
system_flags = {block.flag: block for block in blocks_by_scope["system"]}
namespace_flags: dict[str, dict[str, FlagBlock]] = {}
command_flags: dict[tuple[str, str], dict[str, FlagBlock]] = {}

for block in blocks_by_scope["namespace"]:
    ns = block.path.relative_to(commands_dir).parts[0]
    namespace_flags.setdefault(ns, {})[block.flag] = block

for block in blocks_by_scope["command"]:
    ns, cmd, _ = block.path.relative_to(commands_dir).parts
    command_flags.setdefault((ns, cmd), {})[block.flag] = block


def report_missing(narrow: FlagBlock, broad_scope: str) -> None:
    global failures
    print(
        f"ERROR: flag '{narrow.flag}' at {narrow.scope} scope shadows {broad_scope} scope without override declaration",
        file=sys.stderr,
    )
    print(f"  field: {narrow.field}", file=sys.stderr)
    print(f"  conflicting scopes: {narrow.scope}, {broad_scope}", file=sys.stderr)
    print(f"  required form: override: {broad_scope} — <reason>", file=sys.stderr)
    failures += 1


def report_malformed(narrow: FlagBlock, broad_scope: str) -> None:
    global failures
    print(
        f"ERROR: malformed override declaration for flag '{narrow.flag}' at {narrow.scope} scope",
        file=sys.stderr,
    )
    print(f"  field: {narrow.field}", file=sys.stderr)
    print(f"  found: override: {narrow.override or ''}", file=sys.stderr)
    print(f"  required form: override: {broad_scope} — <reason>", file=sys.stderr)
    failures += 1


def check_override(narrow: FlagBlock, broad_scope: str) -> None:
    if narrow.override is None:
        report_missing(narrow, broad_scope)
    elif not valid_override(narrow.override, broad_scope):
        report_malformed(narrow, broad_scope)


for ns, flags in sorted(namespace_flags.items()):
    for flag, block in sorted(flags.items()):
        if flag in system_flags:
            check_override(block, "system")

for (ns, cmd), flags in sorted(command_flags.items()):
    ns_flags = namespace_flags.get(ns, {})
    for flag, block in sorted(flags.items()):
        if flag in ns_flags:
            check_override(block, "namespace")
        elif flag in system_flags:
            check_override(block, "system")

if failures:
    sys.exit(1)

print("audit-flag-scope: OK")
PY
