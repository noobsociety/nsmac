#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_CONFIG_ROOT="${COMMAND_CONFIG_ROOT:-$ROOT}"

python3 - "$COMMAND_CONFIG_ROOT" <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()

ROOT_PREFIXES = (
    "commands/",
    "core/framework/",
    "tests/specs/",
    "templates/",
    "generated/",
)
ROOT_FILES = frozenset({"AGENTS.md", "CLAUDE.md", "README.md", "REPOSITORY.md"})


def _find_md(directory: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.md"],
            capture_output=True, text=True, cwd=directory, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [f for f in result.stdout.splitlines() if (directory / f).exists()]
    except FileNotFoundError:
        pass
    return sorted(str(p.relative_to(directory)) for p in directory.rglob("*.md") if p.is_file())


def _find_sh(directory: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.sh"],
            capture_output=True, text=True, cwd=directory, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [f for f in result.stdout.splitlines() if (directory / f).exists()]
    except FileNotFoundError:
        pass
    return sorted(str(p.relative_to(directory)) for p in directory.rglob("*.sh") if p.is_file())


def is_root(rel: str) -> bool:
    if rel in ROOT_FILES:
        return True
    return any(rel.startswith(pfx) for pfx in ROOT_PREFIXES)


all_md = _find_md(root)
targets = {rel for rel in all_md if not is_root(rel)}

link_re = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)\)")
contract_re = re.compile(r"^\s*#\s+Contract:\s+(.+\.md)\s*$")

reachable: set[str] = set()

for rel in all_md:
    p = root / rel
    text = p.read_text()
    for m in link_re.finditer(text):
        href = m.group(1).split("#")[0].strip()
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        resolved = (p.parent / href).resolve()
        try:
            reachable.add(str(resolved.relative_to(root)))
        except ValueError:
            pass

for rel in _find_sh(root):
    p = root / rel
    for line in p.read_text().splitlines():
        m = contract_re.match(line)
        if not m:
            continue
        contract_path = m.group(1).strip()
        candidate = root / contract_path
        if candidate.exists():
            reachable.add(str(candidate.relative_to(root)))

orphans = sorted(t for t in targets if t not in reachable)

if orphans:
    for orphan in orphans:
        print(
            f"FAIL: unreachable tracked doc (no inbound Markdown link or Contract reference): {orphan}",
            file=sys.stderr,
        )
    sys.exit(1)

print(f"OK: markdown reference graph has no dead documents ({len(targets)} non-root docs checked)")
PY
