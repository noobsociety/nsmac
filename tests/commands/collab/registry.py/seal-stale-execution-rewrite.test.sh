#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Seal Stale Execution Rewrite" "seal-stale-execution-rewrite"
TARGET="$RUN_DATE-seal-stale-execution-rewrite"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET" --cap-exit reopen-handoff

"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-15T22:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path tests/commands/collab/registry.py/seal-stale-execution-rewrite.test.sh \
  --caller-role pe >/dev/null

assert_seal_stale "seal-stale-execution-rewrite" "execution changed for pe"

printf 'OK: execution rewrite invalidates an existing verification seal\n'
