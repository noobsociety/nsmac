#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

FAIL=0

# Verify commands catalog is in sync with current route files
if ! ./platform/tooling/sync-commands-catalog.sh --check; then
  printf 'FAIL: commands catalog is stale — run platform/tooling/sync-commands-catalog.sh to update\n' >&2
  FAIL=1
fi

# Verify no synthesis dispatch remains in commands/commands.md
if grep -Eq '\(collab synthesize\)|synthesize/index\.md' commands/commands.md 2>/dev/null; then
  printf 'FAIL: synthesis dispatch found in commands/commands.md\n' >&2
  FAIL=1
fi

# Verify no synthesis entry in generated/command-reference.md
if grep -Eq '\(collab synthesize\)|synthesize/index\.md' generated/command-reference.md 2>/dev/null; then
  printf 'FAIL: synthesis dispatch found in generated/command-reference.md\n' >&2
  FAIL=1
fi

[ "$FAIL" -eq 0 ] && printf 'OK: commands catalog is synced and clean of synthesis entries\n'
exit "$FAIL"
