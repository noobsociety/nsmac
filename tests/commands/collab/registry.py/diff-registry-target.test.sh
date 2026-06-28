#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Diff Registry Target" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"

set +e
output="$("$ROOT/commands/collab/engine/registry.py" --registry "$REGISTRY" diff missing 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"registry target not found: missing"* ]]; then
  printf 'FAIL: diff missing target did not report registry target failure\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: diff-registry-target abort path covered\n'
