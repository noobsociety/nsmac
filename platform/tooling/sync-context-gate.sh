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

import sys
from pathlib import Path

root = Path(sys.argv[1])
canonical = root / "platform/standards/context-gate.md"
failures: list[str] = []

if not canonical.exists():
    failures.append("FAIL: missing platform/standards/context-gate.md")

if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)

canonical_text = canonical.read_text()

if canonical_text.startswith("---"):
    failures.append("FAIL: platform/standards/context-gate.md must not carry frontmatter")


critical_prefixes = (
    "Never ",
    "Do not ",
    "Stop immediately",
)

# Real assertion (not a source-vs-source tautology): the canonical gate must
# retain at least one critical directive. Stripping every `Never`/`Do not`/
# `Stop immediately` line now fails the gate instead of passing vacuously.
directive_lines = [
    line.strip()
    for line in canonical_text.splitlines()
    if line.strip().startswith(critical_prefixes)
]
if not directive_lines:
    failures.append(
        "FAIL: context-gate canonical source carries no critical directive "
        "(expected at least one `Never`/`Do not`/`Stop immediately` line)"
    )

if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)

print("OK: context-gate canonical source present with critical directives")
PY
