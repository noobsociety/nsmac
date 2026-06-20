#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

python3 - "$@" <<'PY'
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

COLLAB_COMMAND_ROOT = Path("commands/collab")

# Accepted-debt decision — 2026-06-08 (tooling-contracts collab, tw)
#
# The 8 routes below have anchored ABORT clauses (structural P9 requirement met) but
# no corresponding test files. The gate warns instead of enforcing for these routes.
#
# Why deferred: each route requires non-trivial registry-state fixtures to exercise its
# failure modes meaningfully. Writing those fixtures is a focused test-authoring task
# that exceeds the scope of the tooling-contracts collab, which targeted the paved-path
# and contract-surface gaps.
#
#   diff             — display-only; ABORT paths need registry state stubs
#   export-issues    — issue-terminal export; needs populated registry + transcript fixtures
#   log              — audit log display; needs multi-entry registry state
#   participant-verify — 3-turn lifecycle; significant registry orchestration required
#   reopen           — lifecycle restore; needs seal + verdict state preconditions
#   seal-verification — reviewer seal; needs full participant-verification preconditions
#   show-verdict     — display-only; needs verdict + seal state
#   status           — display-only; needs varied phase/status state
#
# Burn-down trigger: open a dedicated coverage-test-authoring collab when any of the
# following fires — (1) a new collab explicitly scopes P9 test authoring for these
# routes, (2) DISCOVERY_DEBT_ROUTE_FILES grows beyond 10 entries, or (3) a test
# suite regression surfaces in one of these routes during another collab.
DISCOVERY_DEBT_ROUTE_FILES = {
    "commands/collab/diff/index.md",
    "commands/collab/export-issues/index.md",
    "commands/collab/log/index.md",
    "commands/collab/participant-verify/index.md",
    "commands/collab/reopen/index.md",
    "commands/collab/seal-verification/index.md",
    "commands/collab/show-verdict/index.md",
    "commands/collab/status/index.md",
}


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
    def path_fingerprint(self) -> str:
        digest = hashlib.sha1(self.text.strip().encode("utf-8")).hexdigest()[:12]
        return f"{self.path}|{digest}"

    @property
    def location(self) -> str:
        return f"{self.path}:{self.line_number}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check P9-required collab abort coverage.")
    parser.add_argument("--routes-dir", default=".", help="Root directory containing route files.")
    parser.add_argument("--tests-dir", default="tests/commands/collab/registry.py", help="Directory containing P9 abort tests.")
    parser.add_argument("--allowlist", default="platform/tooling/coverage-gate-allowlist.txt", help="Current migration allowlist.")
    parser.add_argument("--route-file", action="append", default=[], help="Route file to scan, relative to routes-dir. Repeatable.")
    parser.add_argument("--print-unanchored-allowlist", action="store_true", help="Print allowlist entries for current unanchored ABORT clauses.")
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


def allowlist_path_fingerprints(entries: set[str]) -> set[str]:
    values: set[str] = set()
    for entry in entries:
        if "|" not in entry:
            continue
        location, digest = entry.rsplit("|", 1)
        rel = location.rsplit(":", 1)[0]
        if rel and digest:
            values.add(f"{rel}|{digest}")
    return values


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


def main() -> int:
    args = parse_args()
    root = Path(args.routes_dir)
    allowlist_path = Path(args.allowlist)
    tests_dir = Path(args.tests_dir)
    files = route_files(args, root)
    if not files:
        print("coverage-gate: no public collab route files discovered", file=sys.stderr)
        return 1
    clauses = scan_abort_clauses(root, files)

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
    allowlist_paths = allowlist_path_fingerprints(allowlist)
    discovered = existing_test_stems(tests_dir)
    required: list[str] = []
    errors: list[str] = []
    allowlisted_unanchored = 0
    discovery_debt_unanchored = 0
    discovery_debt_required: set[str] = set()

    for clause in clauses:
        if clause.anchor is None:
            if clause.path in DISCOVERY_DEBT_ROUTE_FILES:
                discovery_debt_unanchored += 1
                continue
            if clause.fingerprint in allowlist or clause.path_fingerprint in allowlist_paths:
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
        if clause.path in DISCOVERY_DEBT_ROUTE_FILES:
            discovery_debt_required.add(clause.anchor)
        required.append(clause.anchor)

    missing = sorted((set(required) - discovered) - discovery_debt_required)
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
    if discovery_debt_unanchored or discovery_debt_required:
        print(
            "coverage-gate: discovery migration debt remains; "
            f"{discovery_debt_unanchored} unanchored ABORT clause(s) and "
            f"{len(discovery_debt_required)} anchored required pair(s) are discovered but deferred."
        )
    print("coverage-gate: extra tests beyond the required set are ignored.")
    return 0


raise SystemExit(main())
PY
