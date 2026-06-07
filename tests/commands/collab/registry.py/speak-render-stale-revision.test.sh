#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Stale Speak Render" >/dev/null
printf 'Moderator note.\n' >content.md

set +e
output="$("$ROOT/commands/collab/engine/registry.py" speak-render "${RUN_DATE}-stale-speak-render" mod --content-file content.md --observed-revision 0 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: speak-render accepted stale observed revision\n' >&2
  exit 1
fi

if [[ "$output" != *"stale registry revision: observed 0, live 1"* ]]; then
  printf 'FAIL: speak-render stale-revision message mismatch\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: speak-render rejects stale observed revisions\n'
