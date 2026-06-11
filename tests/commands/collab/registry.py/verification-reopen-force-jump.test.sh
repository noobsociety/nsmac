#!/usr/bin/env bash
set -euo pipefail

# A forced jump to Completion (`set active-phase Completion --force`) after a
# reopen must not strand the verification cycle. Before the fix, force bypassed
# the scope-aware reset that only ran in advance_phase, leaving every stage
# preserved at rounds=0: not sealable (zero rounds) and not re-verifiable
# (participant-verify aborted "already complete"). This drives that exact path
# end to end and asserts the cycle stays recoverable: re-verify, then re-seal.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

SLUG="verification-reopen-force-jump"
PE_PATH="platform/tooling/audit.sh"
EID="pe-2026-05-17t12-00-00-02-00"
AUDIT_FILE="$TMPDIR/a"; printf 'audit\n' >"$AUDIT_FILE"
REM_FILE="$TMPDIR/r"; printf 'remediation\n' >"$REM_FILE"
FIN_FILE="$TMPDIR/f"; printf 'final\n' >"$FIN_FILE"

reg() { "$ROOT/commands/collab/engine/registry.py" "$@"; }

reg init --agent-id codex --reviewer pa "Verification Reopen Force Jump" >/dev/null
TARGET="$RUN_DATE-$SLUG"
reg join-participants "$TARGET" pe --agent-id gpt >/dev/null
reg join-participants "$TARGET" pa --agent-id opus >/dev/null
reg set "$TARGET" turn-order pe --caller-role mod >/dev/null
reg set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
bind_lib_work_repo "$TARGET"
REGISTRY="$(registry_path)"

python3 - "$SLUG" "$REGISTRY" "$PE_PATH" <<'PY'
import json
import sys
from pathlib import Path
slug, registry, path = sys.argv[1:4]
data = json.loads(Path(registry).read_text())
entry = next(i for i in data['collabs'] if i['slug'] == slug)
entry['handoff'] = {'roles': {'pe': {'writeScope': [path], 'validationCommands': [['./platform/tooling/audit.sh']]}}}
Path(registry).write_text(json.dumps(data, indent=2) + '\n')
PY

reg execution "$TARGET" pe completed "2026-05-17T12:00:00+02:00" \
  --assigned-role pe --validation-result passed --validation-scope scoped \
  --touched-path "$PE_PATH" --caller-role pe >/dev/null

run_pv() {
  local state revision
  state="$(reg participant-verify-state "$TARGET" pe)"
  revision="$(read_json_field registryRevision <<<"$state")"
  reg participant-verify-render "$TARGET" pe --observed-revision "$revision" \
    --audit-file "$AUDIT_FILE" --remediation-file "$REM_FILE" --final-audit-file "$FIN_FILE" \
    --status completed --touched-path "$PE_PATH" --caller-role pe >/dev/null
}

# First cycle -> seal -> assessment -> non-success verdict -> reopen Handoff.
run_pv
state="$(reg seal-state "$TARGET" pa)"
reg seal-render "$TARGET" pa --observed-revision "$(read_json_field registryRevision <<<"$state")" --caller-role pa >/dev/null
state="$(reg seal-state "$TARGET" pa)"
reg seal-render "$TARGET" pa --observed-revision "$(read_json_field registryRevision <<<"$state")" \
  --outcome failed --restore-target Handoff --restore-reason "force-jump recovery probe" \
  --failure-category out-of-scope \
  --evidence "{\"committedPaths\":[\"$PE_PATH\"],\"executionEntryIds\":[\"$EID\"]}" \
  --caller-role pa >/dev/null
reg reopen "$TARGET" handoff --caller-role mod >/dev/null

# BYPASS the sanctioned advance: force straight to Completion.
reg set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null

# Must not be deadlocked: a pending participant exists, and a zero-round seal is
# not ready. The exact abort pe hit ("already complete") must not occur.
state="$(reg seal-state "$TARGET" pa)"
if [[ "$(read_json_field nextParticipantVerificationRole <<<"$state")" != "pe" ]]; then
  printf 'FAIL: force-jump left no pending participant (deadlock)\n%s\n' "$state" >&2
  exit 1
fi
if [[ "$(read_json_field readyToSeal <<<"$state")" != "False" ]]; then
  printf 'FAIL: force-jump left a zero-round seal ready\n%s\n' "$state" >&2
  exit 1
fi
pvs="$(reg participant-verify-state "$TARGET" pe 2>&1)" || { printf 'FAIL: participant-verify aborted after force-jump\n%s\n' "$pvs" >&2; exit 1; }
if [[ "$pvs" != *'"readyToVerify": true'* ]]; then
  printf 'FAIL: pe is not ready to verify after force-jump\n%s\n' "$pvs" >&2
  exit 1
fi

# Recover fully: re-verify -> seal -> success -> closed.
run_pv
state="$(reg seal-state "$TARGET" pa)"
if [[ "$(read_json_field readyToSeal <<<"$state")" != "True" ]]; then
  printf 'FAIL: not sealable after re-verify\n%s\n' "$state" >&2
  exit 1
fi
reg seal-render "$TARGET" pa --observed-revision "$(read_json_field registryRevision <<<"$state")" --caller-role pa >/dev/null
state="$(reg seal-state "$TARGET" pa)"
reg seal-render "$TARGET" pa --observed-revision "$(read_json_field registryRevision <<<"$state")" \
  --outcome success --evidence "{\"committedPaths\":[\"$PE_PATH\"],\"executionEntryIds\":[\"$EID\"]}" \
  --caller-role pa >/dev/null

python3 - "$SLUG" "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
slug, registry = sys.argv[1:3]
entry = next(i for i in json.loads(Path(registry).read_text())['collabs'] if i['slug'] == slug)
assert entry['status'] == 'closed', entry['status']
assert entry['verdict']['outcome'] == 'success', entry.get('verdict')
PY

printf 'OK: forced jump to Completion after reopen stays recoverable — re-verifies and re-seals, no deadlock\n'
