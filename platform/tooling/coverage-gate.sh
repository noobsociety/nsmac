#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

python3 - "$@" <<'PY'
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

COLLAB_COMMAND_ROOT = Path("commands/collab")
BEHAVIOR_SMOKE_TEST = "real-record-behavior-smoke"


@dataclass(frozen=True)
class AbortClause:
    path: str
    line_number: int
    text: str
    anchor: str | None
    honor_system: bool

    @property
    def location(self) -> str:
        return f"{self.path}:{self.line_number}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check public collab ABORT coverage.")
    parser.add_argument("--routes-dir", default=".", help="Root directory containing route files.")
    parser.add_argument("--tests-dir", default="tests/commands/collab/registry.py", help="Directory containing P9 abort tests.")
    parser.add_argument("--route-file", action="append", default=[], help="Route file to scan, relative to routes-dir. Repeatable.")
    return parser.parse_args()


def is_public_route_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    dispatch_label = re.search(r"^\*\*Dispatch:\*\*\s*(.+)$", text, flags=re.MULTILINE)
    if not dispatch_label:
        return False
    return "reference only" not in dispatch_label.group(1)


def discover_route_files(root: Path) -> list[str]:
    collab_root = root / COLLAB_COMMAND_ROOT
    candidates = [collab_root / "index.md"]
    if collab_root.exists():
        candidates.extend(sorted(collab_root.glob("*/index.md")))
    discovered: list[str] = []
    for path in candidates:
        if path.exists() and is_public_route_file(path):
            discovered.append(path.relative_to(root).as_posix())
    return discovered


def route_files(args: argparse.Namespace, root: Path) -> list[str]:
    return args.route_file or discover_route_files(root)


def route_subcommand(path: str) -> str:
    if path.endswith("/index.md"):
        return Path(path).parent.name
    return Path(path).stem


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


def central_checker_test_stems(root: Path, inventory_path: Path) -> set[str]:
    if not inventory_path.exists():
        return set()
    stems: set[str] = set()
    row_re = re.compile(r"^\| `(?P<stem>[^`]+)` \| `(?P<checker>[^`]+)` \|$")
    for raw in inventory_path.read_text().splitlines():
        match = row_re.match(raw)
        if not match:
            continue
        checker = root / match.group("checker")
        if checker.exists():
            stems.add(match.group("stem"))
    return stems


def main() -> int:
    args = parse_args()
    root = Path(args.routes_dir)
    tests_dir = Path(args.tests_dir)
    files = route_files(args, root)
    strict_fixture_scan = bool(args.route_file)
    enforce_behavior_smoke = (
        not strict_fixture_scan
        and (root / "tests/commands/collab/registry.py" / f"{BEHAVIOR_SMOKE_TEST}.test.sh").exists()
    )
    if not files:
        print("coverage-gate: no public collab route files discovered", file=sys.stderr)
        return 1
    clauses = scan_abort_clauses(root, files)

    if not clauses:
        print(
            "coverage-gate: found 0 ABORT clauses; this is unexpected and likely means parsing is broken.",
            file=sys.stderr,
        )
        return 1

    direct_tests = existing_test_stems(tests_dir)
    central_tests = central_checker_test_stems(root, root / "tests/specs/tests.md")
    discovered = direct_tests | central_tests
    opt_in_anchors: list[str] = []
    required: list[str] = []
    stale_honor_system: list[str] = []
    errors: list[str] = []

    if enforce_behavior_smoke and BEHAVIOR_SMOKE_TEST not in discovered:
        errors.append(
            "missing mandatory behavior-smoke floor: "
            f"{tests_dir}/{BEHAVIOR_SMOKE_TEST}.test.sh"
        )

    for clause in clauses:
        if clause.anchor is None:
            if strict_fixture_scan:
                errors.append(
                    f"unanchored ABORT: {clause.location}; "
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
            if clause.anchor in discovered:
                stale_honor_system.append(clause.anchor)
            continue
        opt_in_anchors.append(clause.anchor)
        if clause.anchor in direct_tests:
            required.append(clause.anchor)

    if stale_honor_system:
        errors.append("stale agent-honor-system marker(s):")
        for stem in sorted(set(stale_honor_system)):
            errors.append(f"  {stem}: matching test exists; remove `(agent-honor-system)` from the route ABORT")

    missing = sorted(set(opt_in_anchors) - discovered)
    if missing:
        errors.append("missing opt-in ABORT tests:")
        for stem in missing:
            errors.append(f"  expected {tests_dir}/{stem}.test.sh")

    if errors:
        print("coverage-gate: abort coverage check failed", file=sys.stderr)
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
        "coverage-gate: abort coverage check passed; "
        f"{len(set(required))} required pair(s), {len(direct_tests)} discovered test(s)."
    )
    if enforce_behavior_smoke:
        print("coverage-gate: behavior-smoke floor present.")
    print("coverage-gate: extra tests beyond the opt-in set are ignored.")
    return 0


raise SystemExit(main())
PY
