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
    "platform/standards/",
    "tests/specs/",
    "platform/templates/",
    "generated/",
)
ROOT_FILES = frozenset({"AGENTS.md", "CLAUDE.md", "README.md", "REPOSITORY.md"})
ROOT_CONTRACT_DOCS = (*sorted(ROOT_FILES), "commands/commands.md")
CODE_SPAN_RE = re.compile(r"`([^`]+)`")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
RUNTIME_ONLY_PREFIXES = (
    ".claude/",
    ".collabs/",
    "projects/",
    "extensions/",
    "ide_state.json",
    "plugins/",
    "skills/",
    "plans/",
    "subagents/",
)


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


def _find_contract_sources(directory: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.sh", "*.py"],
            capture_output=True, text=True, cwd=directory, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [f for f in result.stdout.splitlines() if (directory / f).exists()]
    except FileNotFoundError:
        pass
    return sorted(
        str(p.relative_to(directory))
        for pattern in ("*.sh", "*.py")
        for p in directory.rglob(pattern)
        if p.is_file()
    )


def is_root(rel: str) -> bool:
    if rel in ROOT_FILES:
        return True
    return any(rel.startswith(pfx) for pfx in ROOT_PREFIXES)


def strip_fenced_blocks(text: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    fence = ""
    for line in text.splitlines():
        marker = FENCE_RE.match(line)
        if marker and not in_fence:
            in_fence = True
            fence = marker.group(1)[0]
            continue
        if in_fence:
            if line.lstrip().startswith(fence * 3):
                in_fence = False
                fence = ""
            continue
        lines.append(line)
    return lines


def brace_expand(value: str) -> list[str]:
    match = re.search(r"\{([^{}]+)\}", value)
    if not match:
        return [value]
    choices = [item.strip() for item in match.group(1).split(",") if item.strip()]
    if not choices:
        return [value]
    expanded: list[str] = []
    for choice in choices:
        replaced = value[: match.start()] + choice + value[match.end() :]
        expanded.extend(brace_expand(replaced))
    return expanded


def normalize_contract_reference(raw: str) -> str | None:
    value = raw.strip().strip("`'\"")
    value = value.rstrip(".,;:")
    if not value or " " in value or "\t" in value:
        return None
    if value.startswith(("http://", "https://", "mailto:", "#", "$")):
        return None
    if value == "~/nsmac":
        return None
    if value.startswith("/") and not value.startswith("/Users/"):
        return None
    if "<" in value or ">" in value or "..." in value:
        return None
    if value.startswith("~/nsmac/"):
        value = value.removeprefix("~/nsmac/")
    if value.startswith("COMMAND_CONFIG_ROOT/"):
        value = value.removeprefix("COMMAND_CONFIG_ROOT/")
    while value.startswith("./"):
        value = value[2:]
    if value.startswith("../"):
        return None
    if value.startswith(RUNTIME_ONLY_PREFIXES):
        return None
    has_path_shape = "/" in value
    if not has_path_shape:
        return None
    return value


def reference_exists(pattern: str) -> bool:
    for expanded in brace_expand(pattern):
        if expanded.startswith("/"):
            candidate = Path(expanded)
        else:
            candidate = root / expanded
        try:
            candidate.resolve().relative_to(root)
        except ValueError:
            return False
        if any(char in expanded for char in "*?["):
            if not list(root.glob(expanded)):
                return False
        elif not candidate.exists():
            return False
    return True


def outbound_contract_failures() -> list[str]:
    failures: list[str] = []
    for rel in ROOT_CONTRACT_DOCS:
        path = root / rel
        if not path.exists():
            continue
        for number, line in enumerate(strip_fenced_blocks(path.read_text()), start=1):
            for match in CODE_SPAN_RE.finditer(line):
                normalized = normalize_contract_reference(match.group(1))
                if normalized is None:
                    continue
                if not reference_exists(normalized):
                    failures.append(f"{rel}:{number}: {match.group(1)}")
    return failures


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

for rel in _find_contract_sources(root):
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

outbound_failures = outbound_contract_failures()
if outbound_failures:
    for failure in outbound_failures:
        print(f"FAIL: unresolved outbound contract reference: {failure}", file=sys.stderr)
    sys.exit(1)

print(f"OK: markdown reference graph has no dead documents ({len(targets)} non-root docs checked)")
print(f"OK: root contract outbound references resolve ({len(ROOT_CONTRACT_DOCS)} docs checked)")
PY
