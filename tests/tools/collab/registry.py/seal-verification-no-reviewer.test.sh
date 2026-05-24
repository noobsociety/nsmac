#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

"$ROOT/tools/collab/registry.py" init --agent-id codex "Seal Verification No Reviewer" >/dev/null
TARGET="$RUN_DATE-seal-verification-no-reviewer"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
revision="$(registry_revision)"

set +e
output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"verification seal requires an active reviewer role"* ]]; then
  printf 'FAIL: seal-render accepted a record with no reviewer\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: seal verification rejects records with no reviewer\n'
