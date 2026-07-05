#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_PREFIXES = (
    ".github/",
    "commands/",
    "generated/",
    "platform/",
    "tests/",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "REPOSITORY.md",
)
EXAMPLE_MARKERS = (
    "{",
    "}",
    "<",
    ">",
    "...",
    "*",
    "YYYY",
    "yyyy",
)
EXTERNAL_PREFIXES = (
    "~/",
    "$HOME/",
    "/",
    "http://",
    "https://",
    "mailto:",
)
# Permanent intentional entries only. A path belongs here ONLY when a tracked
# doc deliberately names a file that must NOT exist (a documented prohibition or
# reserved-but-forbidden name); transient "not yet created / since removed"
# citations must be corrected in the doc, not parked here.
ALLOWLISTED_MISSING_PATHS: set[tuple[str, str]] = set()


def tracked_markdown(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "*.md"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0 and result.stdout.strip():
        return [root / line for line in result.stdout.splitlines() if line.strip()]
    return sorted(path for path in root.rglob("*.md") if ".git" not in path.parts)


def code_spans(line: str) -> list[str]:
    return re.findall(r"`([^`]+)`", line)


def normalize_token(raw: str) -> str:
    return raw.strip().strip(".,;:)]}")


def literal_path_token(token: str) -> str | None:
    if re.search(r"\s", token):
        return None
    token = token.split("#", 1)[0]
    match = re.match(r"^(.+\.[A-Za-z0-9]+):\d+(?::\d+)?$", token)
    if match:
        return match.group(1)
    return token


def is_external_or_example(token: str) -> bool:
    if token.startswith(EXTERNAL_PREFIXES):
        return True
    if token.startswith("weekly/") and re.fullmatch(r"weekly/\d{4}-W\d{2}", token):
        return True
    return any(marker in token for marker in EXAMPLE_MARKERS)


def is_repo_path_candidate(token: str) -> bool:
    if is_external_or_example(token):
        return False
    return token.startswith(REPO_PREFIXES)


def check(root: Path) -> list[str]:
    failures: list[str] = []
    for path in tracked_markdown(root):
        if not path.exists():
            continue
        rel = path.relative_to(root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            for raw in code_spans(line):
                token = normalize_token(raw)
                if not is_repo_path_candidate(token):
                    continue
                target = literal_path_token(token)
                if target is None:
                    continue
                if (str(rel), target) in ALLOWLISTED_MISSING_PATHS:
                    continue
                if target and not (root / target).exists():
                    failures.append(f"{rel}:{number}: backticked repo path missing: `{token}`")
    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit backticked repo-relative Markdown path references.")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    failures = check(root)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: backticked repo-relative doc paths resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
