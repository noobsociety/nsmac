#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MODE=""

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --check)
      MODE="--check"
      shift
      ;;
    --root)
      ROOT="$2"
      shift 2
      ;;
    *)
      printf 'usage: %s --check [--root <path>]\n' "$0" >&2
      exit 2
      ;;
  esac
done

if [[ "$MODE" != "--check" ]]; then
  printf 'usage: %s --check [--root <path>]\n' "$0" >&2
  exit 2
fi

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
canonical = root / "platform/standards/context-gate.md"
retired_projection = root / "_mdc/auto/auto-context-gate.mdc"
failures: list[str] = []

if not canonical.exists():
    failures.append("FAIL: missing platform/standards/context-gate.md")
if retired_projection.exists():
    failures.append("FAIL: retired context-gate projection still exists")

if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)

canonical_text = canonical.read_text()

if canonical_text.startswith("---"):
    failures.append("FAIL: platform/standards/context-gate.md must not carry retired projection frontmatter")


def normalize(line: str) -> str:
    line = line.strip().lower()
    line = line.replace("’", "'")
    line = re.sub(r"\bthis gate\b", "this policy", line)
    line = re.sub(r"\bthis rule\b", "this policy", line)
    line = re.sub(r"\brule\b", "policy", line)
    line = re.sub(r"\bruleset\b", "policy set", line)
    line = re.sub(r"\s+", " ", line)
    return line


critical_prefixes = (
    "Never ",
    "Do not ",
    "Stop immediately",
)

missing: list[str] = []
canonical_lines = {normalize(line) for line in canonical_text.splitlines()}
for raw in canonical_text.splitlines():
    stripped = raw.strip()
    if not stripped.startswith(critical_prefixes):
        continue
    normalized = normalize(stripped)
    if normalized not in canonical_lines:
        missing.append(stripped)

if missing:
    failures.append("FAIL: context-gate canonical source missing directive(s):")
    failures.extend(f"  - {item}" for item in missing)

if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)

print("OK: context-gate canonical source is active and retired projection is absent")
PY
