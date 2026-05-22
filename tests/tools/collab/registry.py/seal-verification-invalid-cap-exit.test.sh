#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

set +e
output="$("$ROOT/tools/collab/registry.py" --registry registry.json seal-render missing pa --observed-revision 0 --cap-exit retry 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"invalid cap-exit value retry; must be one of: reopen-action-plan, reopen-handoff, follow-up-collab, archive"* ]]; then
  printf 'FAIL: seal-render accepted an invalid cap exit\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: seal verification rejects invalid cap exits\n'
