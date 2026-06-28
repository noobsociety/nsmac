#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SCAN_PREFIXES = ("commands/", "platform/", "tests/")
ROOT_MARKDOWN = {".md"}
SELF_REFERENCE_PATHS = {"platform/tooling/audit-present-state.py"}

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("dated baseline", re.compile(r"\b(?:BASELINE:|SUITE_BASELINE_|baseline\b.*\b20\d{2}-\d{2}-\d{2}\b|\b20\d{2}-\d{2}-\d{2}\b.*\bbaseline\b)", re.IGNORECASE)),
    ("next weekly target", re.compile(r"\bnext weekly target\b", re.IGNORECASE)),
    ("reduction target", re.compile(r"\breduction target\b", re.IGNORECASE)),
    ("target cycle", re.compile(r"\btarget cycle\b", re.IGNORECASE)),
    ("week-scoped deadline", re.compile(r"(?:\bby\s+W\d{2}\b|-\s*by\s*-\s*W\d{2}\b|-\s*by\s*W\d{2}\b|<=\s*\d+\s*-\s*by\s*-\s*W\d{2}\b|<=\s*\d+\s*-\s*by\s*W\d{2}\b)", re.IGNORECASE)),
    ("week-scoped disposition", re.compile(r"\b(?:closed|retired)\s+for\s+W\d{2}\b", re.IGNORECASE)),
    ("deprecation window", re.compile(r"\bdeprecation windows?\b", re.IGNORECASE)),
    ("backwards compatibility", re.compile(r"\bbackwards-compat(?:ibility)?\b", re.IGNORECASE)),
    ("dated certification", re.compile(r"certif(?:y|ied|ication)\b[^\n]*\(\s*20\d{2}-\d{2}-\d{2}", re.IGNORECASE)),
    ("issue-roadmap promise", re.compile(r"\bProposed\s+#\d+|#\d+\s+should\b", re.IGNORECASE)),
    ("line-count baseline", re.compile(r"\bbaseline\b[^\n]*\b\d{3,5}\s+lines\b|\b\d{3,5}\s+lines\b[^\n]*\bbaseline\b", re.IGNORECASE)),
    (
        "line-count target",
        re.compile(
            r"(?:"
            r"\b(?:success\s+requires|reduce)\b[^\n]*"
            r"(?:`[^`\n]+\.[A-Za-z0-9]+`|\b[A-Za-z0-9_/-]+\.py\b)[^\n]*"
            r"\b(?:at|to)\s+\d{3,5}\s+lines?(?:\s+or\s+fewer)?\b"
            r"|(?:`[^`\n]+\.[A-Za-z0-9]+`|\b[A-Za-z0-9_/-]+\.py\b)[^\n]*"
            r"\bat\s+\d{3,5}\s+lines?\s+or\s+fewer\b"
            r"|\b\d{3,5}\s+lines?\s+or\s+fewer\s+after\b[^\n]*"
            r"(?:`[^`\n]+\.[A-Za-z0-9]+`|\b[A-Za-z0-9_/-]+\.py\b)"
            r")",
            re.IGNORECASE,
        ),
    ),
)

DOCTRINE_SELF_REFERENCE = "Do not retain legacy aliases, deprecation windows, or backwards-compatibility shims."


@dataclass(frozen=True)
class Failure:
    path: str
    line: int
    label: str
    text: str

    def render(self) -> str:
        return f"FAIL: {self.path}:{self.line}: present-state residue ({self.label}): {self.text.strip()}"


def tracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        return [line for line in result.stdout.splitlines() if line]
    return [
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    ]


def in_scope(rel: str) -> bool:
    if rel.startswith(SCAN_PREFIXES):
        return True
    path = Path(rel)
    return len(path.parts) == 1 and path.suffix in ROOT_MARKDOWN


def allowed_self_reference(rel: str, line: str, label: str) -> bool:
    if rel != "platform/data/doctrines.md":
        return False
    if label not in {"deprecation window", "backwards compatibility"}:
        return False
    return DOCTRINE_SELF_REFERENCE in line


def check(root: Path) -> list[Failure]:
    failures: list[Failure] = []
    for rel in tracked_paths(root):
        if rel in SELF_REFERENCE_PATHS:
            continue
        if not in_scope(rel):
            continue
        path = root / rel
        if not path.exists() or path.is_dir():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            for label, pattern in PATTERNS:
                if not pattern.search(line):
                    continue
                if allowed_self_reference(rel, line, label):
                    continue
                failures.append(Failure(rel, number, label, line))
    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit tracked source for past/future outcome residue.")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    failures = check(root)
    if failures:
        for failure in failures:
            print(failure.render(), file=sys.stderr)
        return 1
    print("OK: tracked source carries present-state doctrine only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
