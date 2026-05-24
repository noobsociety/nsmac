#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

python3 - "$@" <<'PY'
from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROUTE_FILES = [
    "commands/collab/index.md",
    "commands/collab/activate/index.md",
    "commands/collab/advance/index.md",
    "commands/collab/archive/index.md",
    "commands/collab/close/index.md",
    "commands/collab/delete/index.md",
    "commands/collab/init/index.md",
    "commands/collab/join/index.md",
    "commands/collab/list/index.md",
    "commands/collab/open/index.md",
    "commands/collab/remove-participant/index.md",
    "commands/collab/restore/index.md",
    "commands/collab/retract-speak/index.md",
    "commands/collab/rewrite-execution/index.md",
    "commands/collab/rewrite-speak/index.md",
    "commands/collab/rewrite-summary/index.md",
    "commands/collab/run-plan/index.md",
    "commands/collab/set/index.md",
    "commands/collab/speak/index.md",
    "commands/collab/unset/index.md",
    "commands/collab/write-summary/index.md",
]


@dataclass(frozen=True)
class AbortClause:
    path: str
    line_number: int
    text: str
    anchor: str | None
    honor_system: bool

    @property
    def fingerprint(self) -> str:
        digest = hashlib.sha1(self.text.strip().encode("utf-8")).hexdigest()[:12]
        return f"{self.path}:{self.line_number}|{digest}"

    @property
    def location(self) -> str:
        return f"{self.path}:{self.line_number}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check P9-required collab abort coverage.")
    parser.add_argument("--routes-dir", default=".", help="Root directory containing route files.")
    parser.add_argument("--tests-dir", default="tests/tools/collab/registry.py", help="Directory containing P9 abort tests.")
    parser.add_argument("--allowlist", default="tools/command-system/coverage-gate-allowlist.txt", help="Current migration allowlist.")
    parser.add_argument("--route-file", action="append", default=[], help="Route file to scan, relative to routes-dir. Repeatable.")
    parser.add_argument("--print-unanchored-allowlist", action="store_true", help="Print allowlist entries for current unanchored ABORT clauses.")
    return parser.parse_args()


def route_files(args: argparse.Namespace) -> list[str]:
    return args.route_file or DEFAULT_ROUTE_FILES


def route_subcommand(path: str) -> str:
    if path.endswith("/index.md"):
        return Path(path).parent.name
    return Path(path).stem


def load_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    entries: set[str] = set()
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.add(line)
    return entries


def anchor_for_previous_line(lines: list[str], index: int) -> str | None:
    if index == 0:
        return None
    previous = lines[index - 1].strip()
    prefix = "<!-- abort:"
    suffix = "-->"
    if not (previous.startswith(prefix) and previous.endswith(suffix)):
        return None
    value = previous[len(prefix) : -len(suffix)].strip()
    return value or None


def is_abort_line(line: str) -> bool:
    return "**ABORT**" in line or "ABORT:" in line


def is_honor_system_line(line: str) -> bool:
    return "**ABORT** (agent-honor-system):" in line


def scan_abort_clauses(root: Path, files: list[str]) -> list[AbortClause]:
    clauses: list[AbortClause] = []
    for rel in files:
        path = root / rel
        if not path.exists():
            raise SystemExit(f"coverage-gate: missing route file: {rel}")
        lines = path.read_text().splitlines()
        for index, line in enumerate(lines):
            if not is_abort_line(line):
                if "agent-honor-system" in line and "**ABORT** (agent-honor-system):" not in line:
                    raise SystemExit(
                        "coverage-gate: agent-honor-system marker must be line-local to an ABORT clause: "
                        f"{rel}:{index + 1}"
                    )
                continue
            if "agent-honor-system" in line and not is_honor_system_line(line):
                raise SystemExit(
                    "coverage-gate: malformed agent-honor-system marker; expected "
                    f"`**ABORT** (agent-honor-system): ...` at {rel}:{index + 1}"
                )
            clauses.append(
                AbortClause(
                    path=rel,
                    line_number=index + 1,
                    text=line,
                    anchor=anchor_for_previous_line(lines, index),
                    honor_system=is_honor_system_line(line),
                )
            )
    return clauses


def existing_test_stems(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {item.name.removesuffix(".test.sh") for item in path.glob("*.test.sh")}


def main() -> int:
    args = parse_args()
    root = Path(args.routes_dir)
    allowlist_path = Path(args.allowlist)
    tests_dir = Path(args.tests_dir)
    clauses = scan_abort_clauses(root, route_files(args))

    if args.print_unanchored_allowlist:
        for clause in clauses:
            if clause.anchor is None:
                print(clause.fingerprint)
        return 0

    if not clauses:
        print(
            "coverage-gate: found 0 ABORT clauses; this is unexpected and likely means parsing is broken.",
            file=sys.stderr,
        )
        return 1

    allowlist = load_allowlist(allowlist_path)
    discovered = existing_test_stems(tests_dir)
    required: list[str] = []
    errors: list[str] = []
    allowlisted_unanchored = 0

    for clause in clauses:
        if clause.anchor is None:
            if clause.fingerprint in allowlist:
                allowlisted_unanchored += 1
                continue
            errors.append(
                f"unanchored ABORT outside allowlist: {clause.location}; "
                f"add `<!-- abort: <stable-id> -->` immediately above it"
            )
            continue
        expected_prefix = f"{route_subcommand(clause.path)}-"
        if not clause.anchor.startswith(expected_prefix):
            errors.append(
                f"abort anchor must start with `{expected_prefix}` at {clause.location}: "
                f"`{clause.anchor}`"
            )
            continue
        if clause.honor_system:
            continue
        required.append(clause.anchor)

    missing = sorted(set(required) - discovered)
    if missing:
        errors.append("missing P9-required tests:")
        for stem in missing:
            errors.append(f"  expected {tests_dir}/{stem}.test.sh")

    if errors:
        print("coverage-gate: P9-required-only check failed", file=sys.stderr)
        print("required pairs:", file=sys.stderr)
        for stem in sorted(set(required)):
            print(f"  {stem}", file=sys.stderr)
        print("discovered tests:", file=sys.stderr)
        for stem in sorted(discovered):
            print(f"  {stem}", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(
        "coverage-gate: P9-required-only check passed; "
        f"{len(set(required))} required pair(s), {len(discovered)} discovered test(s)."
    )
    if allowlisted_unanchored:
        print(
            "coverage-gate: migration debt remains; "
            f"{allowlisted_unanchored} allowlisted unanchored ABORT clause(s) "
            "are not counted as required pairs yet."
        )
    print("coverage-gate: extra tests beyond the required set are ignored.")
    return 0


raise SystemExit(main())
PY
