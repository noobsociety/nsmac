#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


# Retired systems whose artifacts must not return to tracked source. This gate
# keys on artifact identity (path and extension), never on prose. Narrating a
# retired mechanism in the past tense is exempt historical content under the
# closed-collab provenance carve-out (platform/standards/doctrine.md); a
# path-identity gate is therefore the correct instrument -- it catches the
# mechanism itself coming back without ever flagging a doc that merely remembers
# it, so it composes with the carve-out instead of contradicting it.
EXCLUDED_PREFIXES = (".git/", "generated/")


def _is_mdc(rel: str) -> bool:
    return rel.endswith(".mdc")


def _is_gemini(rel: str) -> bool:
    return "gemini" in rel.lower()


def _is_dp_role(rel: str) -> bool:
    return Path(rel).name == "dp.json"


# (label, predicate) rules. A tracked path matching any predicate means a retired
# system's artifact returned to source.
RULES: tuple[tuple[str, "callable[[str], bool]"], ...] = (
    ("retired dormant tooling (.mdc)", _is_mdc),
    ("retired adapter (gemini)", _is_gemini),
    ("retired role key (dp)", _is_dp_role),
)


def tracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return [line for line in result.stdout.splitlines() if line]


def check(root: Path) -> list[str]:
    failures: list[str] = []
    for rel in tracked_paths(root):
        if rel.startswith(EXCLUDED_PREFIXES):
            continue
        for label, predicate in RULES:
            if predicate(rel):
                failures.append(f"{rel}: retired-system artifact returned ({label})")
    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Reject retired-system artifacts (by path/extension) in tracked source."
    )
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    failures = check(root)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: no retired-system artifacts in tracked source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
