#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Seal Stale Transcript Repair" "seal-stale-transcript-repair"
TARGET="$RUN_DATE-seal-stale-transcript-repair"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET" --cap-exit reopen-handoff

"$ROOT/tools/collab/registry.py" transcript-repair "$TARGET" --touch-execution-evidence --caller-role mod >/dev/null

assert_seal_stale "seal-stale-transcript-repair" "transcript repair touched execution evidence"

printf 'OK: transcript repair touching execution evidence invalidates an existing verification seal\n'
