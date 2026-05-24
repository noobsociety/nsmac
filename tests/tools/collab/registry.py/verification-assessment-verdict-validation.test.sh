#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Verification Verdict Validation" "verification-verdict-validation"
TARGET="$RUN_DATE-verification-verdict-validation"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$TARGET"
REVISION="$(assessment_revision "$TARGET")"

assert_rejected() {
  local expected="$1"
  shift
  local output
  local status
  set +e
  output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$REVISION" --caller-role pa "$@" 2>&1)"
  status=$?
  set -e
  if [[ "$status" -eq 0 || "$output" != *"$expected"* ]]; then
    printf 'FAIL: expected verdict rejection containing %s\n%s\n' "$expected" "$output" >&2
    exit 1
  fi
}

assert_rejected "verdict outcome must be one of: success, incomplete, failed" \
  --outcome retry

assert_rejected "registry: verdict.restoreTarget is required when outcome is not success" \
  --outcome incomplete \
  --restore-reason "Missing evidence."

assert_rejected "registry: verdict.restoreTarget must be absent when outcome is success" \
  --outcome success \
  --restore-target Handoff

assert_rejected "verdict restoreTarget must be one of: Action Plan, Handoff" \
  --outcome failed \
  --restore-target Audit \
  --restore-reason "Audit is not a routed restore phase."

assert_rejected "verdict evidence contains non-anchor fields: ['commandOutput']" \
  --outcome failed \
  --restore-target Handoff \
  --restore-reason "The reviewer found command output masquerading as evidence." \
  --evidence '{"commandOutput":"do not store this"}'

printf 'OK: verification assessment rejects invalid verdict fields\n'
