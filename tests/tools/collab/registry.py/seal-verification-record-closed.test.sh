#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"

init_reviewer_target "Seal Verification Closed Record" "seal-verification-closed-record"
TARGET="$RUN_DATE-seal-verification-closed-record"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET"

set +e
output="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"record is closed"* ]]; then
  printf 'FAIL: seal-state accepted a closed record\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: seal verification rejects closed records\n'
