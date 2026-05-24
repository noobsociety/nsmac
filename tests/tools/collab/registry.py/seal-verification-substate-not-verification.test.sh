#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Seal Verification Substate Guard" "seal-verification-substate-guard"
TARGET="$RUN_DATE-seal-verification-substate-guard"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
state="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"

set +e
output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"Completion.verification sub-state is not active; current sub-state: execution"* ]]; then
  printf 'FAIL: seal-render accepted Completion.execution\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: seal verification rejects Completion.execution sub-state\n'
