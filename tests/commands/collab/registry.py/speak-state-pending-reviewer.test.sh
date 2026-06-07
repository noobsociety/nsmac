#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa "Pending Reviewer Gate" >/dev/null

set +e
output="$("$ROOT/commands/collab/engine/registry.py" speak-state "${RUN_DATE}-pending-reviewer-gate" mod 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: speak-state allowed contribution with pending reviewer\n' >&2
  exit 1
fi

if [[ "$output" != *"pending reviewerRole: pa"* ]]; then
  printf 'FAIL: speak-state pending-reviewer message mismatch\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: speak-state rejects pending reviewer gates\n'
