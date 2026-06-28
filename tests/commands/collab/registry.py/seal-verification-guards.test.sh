#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

assert_command_fails_containing() {
  local label="$1"
  local needle="$2"
  shift 2
  local output
  local status

  set +e
  output="$("$@" 2>&1)"
  status=$?
  set -e

  if [[ "$status" -eq 0 || "$output" != *"$needle"* ]]; then
    printf 'FAIL: %s\n%s\n' "$label" "$output" >&2
    exit 1
  fi
}

assert_command_fails_containing \
  "seal-render accepted an invalid cap exit" \
  "invalid cap-exit value retry; must be one of: reopen-action-plan, reopen-handoff, follow-up-collab, archive" \
  "$ROOT/commands/collab/engine/registry.py" --registry registry.json seal-render missing pa --observed-revision 0 --cap-exit retry

assert_command_fails_containing \
  "seal-state did not reject an unreadable registry" \
  "project marker missing: .collab.json; run (collab init) from the project root" \
  "$ROOT/commands/collab/engine/registry.py" seal-state missing pa

init_reviewer_target "Seal Verification Phase Guard" "seal-verification-phase-guard"
TARGET="$RUN_DATE-seal-verification-phase-guard"
assert_command_fails_containing \
  "seal-state accepted a non-Completion phase" \
  "(collab seal verification) is valid only in the Completion phase" \
  "$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Seal Verification No Reviewer" >/dev/null
TARGET="$RUN_DATE-seal-verification-no-reviewer"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
revision="$(registry_revision)"
assert_command_fails_containing \
  "seal-render accepted a record with no reviewer" \
  "verification seal requires an active reviewer role" \
  "$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$revision"

init_reviewer_target "Seal Verification Substate Guard" "seal-verification-substate-guard"
TARGET="$RUN_DATE-seal-verification-substate-guard"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
assert_command_fails_containing \
  "seal-render accepted Completion.execution" \
  "Completion.verification sub-state is not active; current sub-state: execution" \
  "$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa

init_reviewer_target "Seal Verification Closed Record" "seal-verification-closed-record"
TARGET="$RUN_DATE-seal-verification-closed-record"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"
seal_target "$TARGET"
"$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$(assessment_revision "$TARGET")" \
  --outcome success \
  --caller-role pa >/dev/null
assert_command_fails_containing \
  "seal-state accepted a closed record" \
  "record is closed" \
  "$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa

init_reviewer_target "Seal Verification Zero Round No Record" "seal-verification-zero-round-no-record"
TARGET="$RUN_DATE-seal-verification-zero-round-no-record"
REGISTRY="$(registry_path)"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"

state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
rounds="$(read_json_field verificationRounds <<<"$state")"

if [[ "$rounds" != "0" ]]; then
  printf 'FAIL: seal-state should expose zero verification rounds before any seal attempt\n%s\n' "$state" >&2
  exit 1
fi

assert_command_fails_containing \
  "seal-render accepted a zero-round first seal attempt" \
  "zero verification rounds; at least one reviewer-executor paired event is required before sealing" \
  "$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(
    item
    for item in json.loads(registry.read_text())['collabs']
    if item['slug'] == 'seal-verification-zero-round-no-record'
)
transcript = (registry.parent / Path(entry['transcriptPath'])).read_text()

assert entry['status'] == 'open', entry
assert entry['activePhase'] == 'Completion', entry
assert entry['completion']['subState'] == 'verification', entry['completion']
assert entry['verification']['subState'] == 'seal', entry['verification']
assert entry['verification']['rounds'] == 0, entry['verification']
assert 'pairedExecutionSignature' not in entry['verification'], entry['verification']
assert 'verificationSeal' not in entry, entry
assert 'verdict' not in entry, entry
assert entry['terminal'] == 'seal', entry
assert 'terminalMode' not in entry, entry
assert 'workflowModel' not in entry, entry
assert '**pa:** sealed' not in transcript, transcript
PY

printf 'OK: seal verification guard checks remain covered\n'
