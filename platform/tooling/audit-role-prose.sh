#!/usr/bin/env bash
set -euo pipefail

ROOT="."
PATHS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      if [[ $# -lt 2 ]]; then
        printf 'audit-role-prose: --root requires a value\n' >&2
        exit 2
      fi
      ROOT="$2"
      shift 2
      ;;
    --path)
      if [[ $# -lt 2 ]]; then
        printf 'audit-role-prose: --path requires a value\n' >&2
        exit 2
      fi
      PATHS+=("$2")
      shift 2
      ;;
    --help|-h)
      printf 'usage: %s [--root DIR] [--path PATH ...]\n' "$(basename "$0")"
      exit 0
      ;;
    *)
      printf 'audit-role-prose: unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

PY_ARGS=("$ROOT")
if [[ ${#PATHS[@]} -gt 0 ]]; then
  PY_ARGS+=("${PATHS[@]}")
fi

python3 - "${PY_ARGS[@]}" <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
requested = [Path(value) for value in sys.argv[2:]]

ROLE_KEY_RE = re.compile(r"(?<![A-Za-z0-9_])(mod|pa|pe|tw)(?![A-Za-z0-9_])")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
INLINE_CODE_RE = re.compile(r"`([^`]*)`")


def is_source_candidate(path: Path) -> bool:
    rel = path.as_posix()
    return (
        rel in {".gitignore", ".collab.json", "CLAUDE.md", "AGENTS.md", "GEMINI.md", "README.md", "REPOSITORY.md"}
        or rel.startswith((".github/", "platform/standards/", "generated/", "platform/templates/", "tests/specs/", "commands/", "tests/"))
    )


def repo_paths() -> list[Path]:
    paths: list[str] = []
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "-z", "*.md", "*.mdc"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout.decode().split("\0")
        paths.extend(item for item in tracked if item)
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z", "*.md", "*.mdc"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout.decode().split("\0")
        paths.extend(item for item in untracked if item)
        return sorted({Path(item) for item in paths if is_source_candidate(Path(item))})
    except (subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        return sorted(
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() and path.suffix in {".md", ".mdc"}
        )


def expand_requested(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for raw in paths:
        path = raw if raw.is_absolute() else root / raw
        if path.is_dir():
            expanded.extend(
                item.relative_to(root)
                for item in path.rglob("*")
                if item.is_file() and item.suffix in {".md", ".mdc"}
            )
        elif path.is_file() and path.suffix in {".md", ".mdc"}:
            expanded.append(path.relative_to(root))
    return sorted(set(expanded))


def skip_path(rel: Path) -> bool:
    text = rel.as_posix()
    return (
        text.startswith("generated/")
        or text.startswith("tests/fixtures/")
        or text.startswith("tests/platform/")
    )


def starts_front_matter(lines: list[str]) -> bool:
    return bool(lines and lines[0].strip() == "---")


def strip_allowed_inline_code(line: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(1)
        if "/" in value or "--" in value or "<" in value or ">" in value:
            return ""
        if value.endswith((".md", ".mdc", ".json", ".sh", ".py")):
            return ""
        if value.startswith("commands/collab/reference/roles/"):
            return ""
        return value

    return INLINE_CODE_RE.sub(replace, line)


def is_metadata_or_carveout(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith(("<!--", "-->")):
        return True
    if stripped.startswith("|"):
        return True
    if stripped.startswith(("dispatch:", "param:", "description:")):
        return True
    if stripped.startswith("**Prose dispatch:**"):
        return True
    if "**Examples:**" in stripped or stripped.startswith("Example:") or stripped.startswith("**Example:**"):
        return True
    if "ABORT" in stripped:
        return True
    if stripped.startswith("**Declared bias.**"):
        return True
    return False


def scan_file(rel: Path) -> list[str]:
    path = root / rel
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []

    findings: list[str] = []
    in_fence = False
    fence = ""
    in_front_matter = starts_front_matter(lines)
    ingenerated = False
    in_examples_section_level: int | None = None
    in_declared_bias_section_level: int | None = None

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()

        if in_front_matter:
            if index > 1 and stripped == "---":
                in_front_matter = False
            continue

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

        if "BEGIN GENERATED:" in line:
            ingenerated = True
            continue
        if "END GENERATED:" in line:
            ingenerated = False
            continue
        if ingenerated:
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip().lower()
            if in_examples_section_level is not None and level <= in_examples_section_level:
                in_examples_section_level = None
            if in_declared_bias_section_level is not None and level <= in_declared_bias_section_level:
                in_declared_bias_section_level = None
            if "example" in title:
                in_examples_section_level = level
            if title == "declared bias":
                in_declared_bias_section_level = level
            continue

        if in_examples_section_level is not None or in_declared_bias_section_level is not None:
            continue
        if is_metadata_or_carveout(line):
            continue

        scan_line = strip_allowed_inline_code(line)
        if ROLE_KEY_RE.search(scan_line):
            findings.append(f"{rel.as_posix()}:{index}")

    return findings


def main() -> int:
    paths = expand_requested(requested) if requested else repo_paths()
    findings: list[str] = []
    for rel in paths:
        if skip_path(rel):
            continue
        findings.extend(scan_file(rel))

    if findings:
        print("\n".join(findings))
        return 1
    return 0


raise SystemExit(main())
PY
