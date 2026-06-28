#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REGISTRY_CALL_RE = re.compile(r"commands/collab/engine/registry\.py\s+([A-Za-z0-9_-]+)")
READ_ONLY_CLAIM_RE = re.compile(
    r"(\*\*Read-only:\*\*|\bis read-only\b|\bdoes not mutate\b|\bmust not mutate\b|"
    r"\bwithout mutating\b|\bnever creates\b|\bnever edits\b|\bnever archives\b|"
    r"\bnever selects\b|\*\*Documentation-only status:\*\*)",
    re.IGNORECASE,
)
READ_ONLY_SUBCOMMANDS = {
    "audit-closed",
    "audit-effort-matrix",
    "banner-timestamp",
    "diff",
    "effort-state",
    "flag-inventory",
    "handoff-state",
    "list",
    "log",
    "participant-verify-state",
    "registry-cli-doc",
    "registry-path",
    "reviewer-state",
    "role-row",
    "roles",
    "seal-state",
    "show-verdict",
    "speak-lifecycle",
    "speak-lifecycle-live",
    "speak-state",
    "status-view",
    "summary-role",
    "timestamp",
    "transcript-view",
    "validate",
    "write-guard",
}


@dataclass(frozen=True)
class RouteCheck:
    route: str
    path: Path
    claims_read_only: bool
    step_calls: list[tuple[int, str]]


def route_name(path: Path) -> str:
    return path.parent.name.replace("-", " ")


def steps_lines(lines: list[str]) -> list[tuple[int, str]]:
    in_steps = False
    collected: list[tuple[int, str]] = []
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            in_steps = line.strip() == "## Steps"
            continue
        if in_steps:
            collected.append((number, line))
    return collected


def route_check(path: Path) -> RouteCheck:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    step_calls: list[tuple[int, str]] = []
    for number, line in steps_lines(lines):
        for match in REGISTRY_CALL_RE.finditer(line):
            step_calls.append((number, match.group(1)))
    return RouteCheck(
        route=route_name(path),
        path=path,
        claims_read_only=any(READ_ONLY_CLAIM_RE.search(line) for line in lines),
        step_calls=step_calls,
    )


def check(root: Path) -> list[str]:
    failures: list[str] = []
    for path in sorted((root / "commands/collab").glob("*/index.md")):
        route = route_check(path)
        if not route.claims_read_only:
            continue
        rel = route.path.relative_to(root)
        if not route.step_calls:
            failures.append(f"{rel}: read-only route has no auditable Step registry.py backend")
            continue
        for line, subcommand in route.step_calls:
            if subcommand not in READ_ONLY_SUBCOMMANDS:
                failures.append(
                    f"{rel}:{line}: read-only route calls mutating or unknown registry subcommand: "
                    f"{subcommand}"
                )
    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit collab read-only route/backend contracts.")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    failures = check(root)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: collab read-only route contracts pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
