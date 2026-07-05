#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


EXCLUDED_PREFIXES = (
    ".git/",
    "generated/",
)

REINTRODUCTION_ALLOWLIST = {
    "commands/collab/diff/index.md",
}


def git_lines(root: Path, args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def all_deleted_paths(root: Path) -> set[str]:
    paths = set(git_lines(root, ["log", "--name-only", "--diff-filter=D", "--format="]))
    return {path for path in paths if path}


def absent_deleted_paths(root: Path) -> list[str]:
    return sorted(path for path in all_deleted_paths(root) if not (root / path).exists())


def reintroduced_deleted_paths(root: Path) -> list[str]:
    tracked = set(git_lines(root, ["ls-files"]))
    return sorted(
        path
        for path in all_deleted_paths(root) & tracked
        if path not in REINTRODUCTION_ALLOWLIST
    )


def tracked_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in git_lines(root, ["ls-files"]):
        if rel.startswith(EXCLUDED_PREFIXES):
            continue
        path = root / rel
        if path.exists() and path.is_file():
            files.append(path)
    return files


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    deleted = absent_deleted_paths(root)
    failures: list[str] = []

    for path in reintroduced_deleted_paths(root):
        failures.append(f"deleted path exists at HEAD without allowlist: {path}")

    for path in tracked_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(root).as_posix()
        for deleted_path in deleted:
            if deleted_path in text:
                failures.append(f"{rel}: references deleted path {deleted_path}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: current source has no deleted-path references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
