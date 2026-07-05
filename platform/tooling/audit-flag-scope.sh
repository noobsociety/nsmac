#!/usr/bin/env bash
# Contract: platform/tooling/flag-scope-validator-contract.md
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
source_root = Path(__file__).resolve().parents[2]
commands_dir = root / "commands"
validate_schema_for_root = root == source_root


@dataclass(frozen=True)
class FlagBlock:
    flag: str
    scope: str
    path: Path
    line: int
    fields: dict[str, str]
    eligibility: str | None
    guard_class: str | None
    ineligibility_reason: str | None
    override: str | None
    validate_schema: bool

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
    validate_schema = validate_schema_for_root and any(line.startswith("**Dispatch:**") for line in lines)
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
                        fields=dict(fields),
                        eligibility=fields.get("eligibility"),
                        guard_class=fields.get("guard-class"),
                        ineligibility_reason=fields.get("ineligibility-reason"),
                        override=fields.get("override"),
                        validate_schema=validate_schema,
                    )
                )
            in_block = False
            continue
        if in_block and ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return blocks


ELIGIBLE_GUARD_CLASSES = {"hard-abort", "gated-overwrite", "recovery-only"}
INELIGIBLE_GUARD_CLASSES = {
    "registry-integrity",
    "lifecycle-gate",
    "role-gate",
    "schema-validation",
    "unreadable-context",
    "destructive-delete",
}
ALLOWED_FIELDS = {
    "flag",
    "eligibility",
    "guard-class",
    "ineligibility-reason",
    "override",
}


def valid_override(text: str | None, parent: str) -> bool:
    if text is None:
        return False
    pattern = rf"^{re.escape(parent)} — \S.*$"
    return re.match(pattern, text) is not None


def override_parent(text: str | None) -> str | None:
    if text is None:
        return None
    parent = text.split(maxsplit=1)[0]
    if parent in {"system", "namespace"}:
        return parent
    return None


paths = sorted(commands_dir.glob("index.md"))
paths.extend(sorted(commands_dir.glob("*/index.md")))
paths.extend(sorted(commands_dir.glob("*/*/index.md")))

blocks_by_scope: dict[str, list[FlagBlock]] = {"system": [], "namespace": [], "command": []}
for path in paths:
    if path.exists():
        for block in parse_route_flags(path):
            blocks_by_scope[block.scope].append(block)

if not any(blocks_by_scope.values()):
    print("audit-flag-scope: OK (route-flag blocks are optional; none found)")
    sys.exit(0)

failures = 0
system_flags = {block.flag: block for block in blocks_by_scope["system"]}
namespace_flags: dict[str, dict[str, FlagBlock]] = {}
command_flags: dict[tuple[str, str], dict[str, FlagBlock]] = {}


def report_schema(block: FlagBlock, message: str) -> None:
    global failures
    print("ERROR: malformed route-flag block", file=sys.stderr)
    print(f"  field: {block.field}", file=sys.stderr)
    print(f"  reason: {message}", file=sys.stderr)
    failures += 1


def validate_block_schema(block: FlagBlock) -> None:
    unknown = sorted(set(block.fields) - ALLOWED_FIELDS)
    if unknown:
        report_schema(block, f"unknown field(s): {', '.join(unknown)}")
    if block.eligibility not in {"eligible", "ineligible"}:
        report_schema(block, "eligibility must be eligible or ineligible")
        return
    if not block.guard_class:
        report_schema(block, "guard-class is required")
        return
    if block.eligibility == "eligible":
        if block.guard_class not in ELIGIBLE_GUARD_CLASSES:
            report_schema(block, f"eligible guard-class is not allowed: {block.guard_class}")
        if block.ineligibility_reason:
            report_schema(block, "eligible blocks must not declare ineligibility-reason")
    if block.eligibility == "ineligible":
        if block.guard_class not in INELIGIBLE_GUARD_CLASSES:
            report_schema(block, f"ineligible guard-class is not allowed: {block.guard_class}")
        if not block.ineligibility_reason or not block.ineligibility_reason.strip():
            report_schema(block, "ineligibility-reason is required when eligibility is ineligible")


for scope_blocks in blocks_by_scope.values():
    for block in scope_blocks:
        if block.validate_schema:
            validate_block_schema(block)

for block in blocks_by_scope["namespace"]:
    ns = block.path.relative_to(commands_dir).parts[0]
    route_flags = namespace_flags.setdefault(ns, {})
    if block.flag in route_flags:
        report_schema(block, f"duplicate route-flag for {block.flag} in route")
    route_flags[block.flag] = block

for block in blocks_by_scope["command"]:
    ns, cmd, _ = block.path.relative_to(commands_dir).parts
    route_flags = command_flags.setdefault((ns, cmd), {})
    if block.flag in route_flags:
        report_schema(block, f"duplicate route-flag for {block.flag} in route")
    route_flags[block.flag] = block


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
    if narrow.override and "–" in narrow.override:
        print("  delimiter: found U+2013 en-dash; expected U+2014 em-dash", file=sys.stderr)
    elif narrow.override and " - " in narrow.override:
        print("  delimiter: found U+002D hyphen-minus; expected U+2014 em-dash", file=sys.stderr)
    print(f"  required form: override: {broad_scope} — <reason>", file=sys.stderr)
    failures += 1


def report_unresolved_origin(narrow: FlagBlock, parent: str) -> None:
    global failures
    print(
        f"ERROR: unresolved inherited flag origin for flag '{narrow.flag}' at {narrow.scope} scope",
        file=sys.stderr,
    )
    print(f"  field: {narrow.field}", file=sys.stderr)
    print(f"  found: override: {narrow.override or ''}", file=sys.stderr)
    print(f"  missing origin: {parent}", file=sys.stderr)
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
        elif override_parent(block.override) == "system":
            if valid_override(block.override, "system"):
                report_unresolved_origin(block, "system")
            else:
                report_malformed(block, "system")

for (ns, cmd), flags in sorted(command_flags.items()):
    ns_flags = namespace_flags.get(ns, {})
    for flag, block in sorted(flags.items()):
        if flag in ns_flags:
            check_override(block, "namespace")
        elif flag in system_flags:
            check_override(block, "system")
        else:
            parent = override_parent(block.override)
            if parent == "namespace":
                if valid_override(block.override, "namespace"):
                    report_unresolved_origin(block, "namespace")
                else:
                    report_malformed(block, "namespace")
            elif parent == "system":
                if valid_override(block.override, "system"):
                    report_unresolved_origin(block, "system")
                else:
                    report_malformed(block, "system")

if failures:
    sys.exit(1)

print("audit-flag-scope: OK")
PY
