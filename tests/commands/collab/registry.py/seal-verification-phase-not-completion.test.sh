#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Seal Verification Phase Guard" "seal-verification-phase-guard"
TARGET="$RUN_DATE-seal-verification-phase-guard"

set +e
output="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"(collab seal verification) is valid only in the Completion phase"* ]]; then
  printf 'FAIL: seal-state accepted a non-Completion phase\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: seal verification rejects non-Completion phases\n'
