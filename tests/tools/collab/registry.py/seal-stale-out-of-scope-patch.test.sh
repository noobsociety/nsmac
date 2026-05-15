#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"

init_reviewer_target "Seal Stale Out Of Scope Patch" "seal-stale-out-of-scope-patch"
TARGET="$RUN_DATE-seal-stale-out-of-scope-patch"
seed_handoff_scope "seal-stale-out-of-scope-patch"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET" --cap-exit reopen-handoff

"$ROOT/tools/collab/registry.py" out-of-scope-patch "$TARGET" pe \
  --path tests/tools/collab/registry.py/seal-stale-out-of-scope-patch.test.sh \
  --caller-role pe >/dev/null

assert_seal_stale \
  "seal-stale-out-of-scope-patch" \
  "out-of-scope patch outside declared writeScope: tests/tools/collab/registry.py/seal-stale-out-of-scope-patch.test.sh"

printf 'OK: out-of-scope patch hook invalidates an existing verification seal\n'
