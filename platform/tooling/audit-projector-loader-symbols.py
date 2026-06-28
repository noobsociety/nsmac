#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FORBIDDEN_SYMBOLS = (
    "load_projector",
    "projectors_dir_for_roles",
    "DEFAULT_PROJECTORS_DIR",
)
SCAN_PATHS = (
    "commands/collab/engine",
    "platform/tooling/roles.py",
)


def iter_scan_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in SCAN_PATHS:
        path = root / rel
        if path.is_dir():
            files.extend(sorted(path.glob("*.py")))
        elif path.exists():
            files.append(path)
    return files


def check(root: Path) -> list[str]:
    failures: list[str] = []
    pattern = re.compile(r"\b(" + "|".join(re.escape(symbol) for symbol in FORBIDDEN_SYMBOLS) + r")\b")
    for path in iter_scan_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            match = pattern.search(line)
            if match:
                failures.append(f"{path.relative_to(root)}:{number}: projector loader symbol `{match.group(1)}`")
    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Reject retired projector loader machinery.")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    failures = check(root)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: projector loader machinery is absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
