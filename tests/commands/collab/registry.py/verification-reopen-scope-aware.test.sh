#!/usr/bin/env bash
set -euo pipefail

# Scope-aware reopen: a non-success verdict that reopens to revise only one
# role's write scope must re-verify only that role. The unchanged role keeps its
# completed participant verification, and the fresh round is earned by the
# re-scoped role's re-run alone (a verification round is earned only by a real
# participant completion, so the unchanged role's preserved completion plus the
# re-run together close the round). A reopen that revises nothing falls back to a
# full reset so the round stays earnable rather than stranding at rounds=0.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

TW_PATH="platform/tooling/audit.sh"
PE_PATH="platform/tooling/audit-role-prose.sh"

AUDIT_FILE="$TMPDIR/audit.txt"; printf 'audit clean\n' >"$AUDIT_FILE"
REMEDIATION_FILE="$TMPDIR/remediation.txt"; printf 'no remediation\n' >"$REMEDIATION_FILE"
FINAL_AUDIT_FILE="$TMPDIR/final.txt"; printf 'final clean\n' >"$FINAL_AUDIT_FILE"

reg() { "$ROOT/commands/collab/engine/registry.py" "$@"; }

run_pv() {
  local role="$1" tpath="$2" state revision
  state="$(reg participant-verify-state "$TARGET" "$role")"
  revision="$(read_json_field registryRevision <<<"$state")"
  reg participant-verify-render "$TARGET" "$role" \
    --observed-revision "$revision" \
    --audit-file "$AUDIT_FILE" --remediation-file "$REMEDIATION_FILE" --final-audit-file "$FINAL_AUDIT_FILE" \
    --status completed --touched-path "$tpath" --caller-role "$role" >/dev/null
}

stage_of() {
  python3 - "$SLUG" "$REGISTRY" "$1" <<'PY'
import json
import sys
from pathlib import Path
slug, registry, role = sys.argv[1:4]
entry = next(i for i in json.loads(Path(registry).read_text())['collabs'] if i['slug'] == slug)
print(entry.get('verification', {}).get('participants', {}).get(role, {}).get('stage', 'none'))
PY
}

assert_sealable() {
  local label="$1" state
  state="$(reg seal-state "$TARGET" pa)"
  if [[ "$(read_json_field verificationRounds <<<"$state")" != "1" || "$(read_json_field readyToSeal <<<"$state")" != "True" ]]; then
    printf 'FAIL: %s — expected rounds=1 readyToSeal=True\n%s\n' "$label" "$state" >&2
    exit 1
  fi
}

seal_to_assessment() {
  local state
  state="$(reg seal-state "$TARGET" pa)"
  reg seal-render "$TARGET" pa --observed-revision "$(read_json_field registryRevision <<<"$state")" --caller-role pa >/dev/null
}

verdict_reopen_handoff() {
  local state
  state="$(reg seal-state "$TARGET" pa)"
  reg seal-render "$TARGET" pa \
    --observed-revision "$(read_json_field registryRevision <<<"$state")" \
    --outcome failed --restore-target Handoff \
    --restore-reason "reopen to revise one role's scope" --failure-category out-of-scope \
    --evidence "{\"committedPaths\":[\"$PE_PATH\"],\"executionEntryIds\":[\"pe-2026-05-17t12-05-00-02-00\"]}" \
    --caller-role pa >/dev/null
}

setup_through_first_round() {
  SLUG="$1"
  reg init --agent-id codex --reviewer pa "$2" >/dev/null
  TARGET="$RUN_DATE-$SLUG"
  reg join-participants "$TARGET" tw --agent-id claude-sonnet-4-6 >/dev/null
  reg join-participants "$TARGET" pe --agent-id codex >/dev/null
  reg join-participants "$TARGET" pa --agent-id opus >/dev/null
  reg set "$TARGET" turn-order "tw pe" --caller-role mod >/dev/null
  reg set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
  bind_lib_work_repo "$TARGET"
  REGISTRY="$(registry_path)"
  python3 - "$SLUG" "$REGISTRY" "$TW_PATH" "$PE_PATH" <<'PY'
import json
import sys
from pathlib import Path
slug, registry, tw_path, pe_path = sys.argv[1:5]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(i for i in data['collabs'] if i['slug'] == slug)
entry['handoff'] = {'roles': {
    'tw': {'writeScope': [tw_path], 'validationCommands': [['./platform/tooling/audit.sh']]},
    'pe': {'writeScope': [pe_path], 'validationCommands': [['./platform/tooling/audit.sh']]},
}}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
  reg execution "$TARGET" tw completed "2026-05-17T12:00:00+02:00" \
    --assigned-role tw --assigned-role pe --validation-result passed --validation-scope scoped \
    --touched-path "$TW_PATH" --caller-role tw >/dev/null
  reg execution "$TARGET" pe completed "2026-05-17T12:05:00+02:00" \
    --assigned-role tw --assigned-role pe --validation-result passed --validation-scope scoped \
    --touched-path "$PE_PATH" --caller-role pe >/dev/null
  run_pv tw "$TW_PATH"
  run_pv pe "$PE_PATH"
  assert_sealable "first round"
}

# --- Scenario 1: reopen revises only pe's scope -> only pe re-verifies. --------
setup_through_first_round "verification-reopen-scope-aware" "Verification Reopen Scope Aware"
seal_to_assessment
verdict_reopen_handoff
reg reopen "$TARGET" handoff --caller-role mod >/dev/null

# Revise ONLY pe's write scope; tw's is untouched.
python3 - "$SLUG" "$REGISTRY" "$TW_PATH" "$PE_PATH" <<'PY'
import json
import sys
from pathlib import Path
slug, registry, tw_path, pe_path = sys.argv[1:5]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(i for i in data['collabs'] if i['slug'] == slug)
entry['handoff']['roles']['pe']['writeScope'] = [pe_path, tw_path]
path.write_text(json.dumps(data, indent=2) + '\n')
PY

reg advance "$TARGET" next --caller-role mod >/dev/null

if [[ "$(stage_of tw)" != "completed" ]]; then
  printf 'FAIL: tw verification not preserved across reopen; stage=%s\n' "$(stage_of tw)" >&2
  exit 1
fi
if [[ "$(stage_of pe)" == "completed" ]]; then
  printf 'FAIL: pe verification not reset after its scope was revised\n' >&2
  exit 1
fi

# pe alone re-verifies; the round is re-earned without tw re-running.
run_pv pe "$PE_PATH"
assert_sealable "round re-earned by pe alone"
if [[ "$(stage_of tw)" != "completed" ]]; then
  printf 'FAIL: tw was forced to re-run on a single-role reopen\n' >&2
  exit 1
fi

# --- Scenario 2: reopen revises nothing -> full reset keeps the round earnable. -
setup_through_first_round "verification-reopen-no-rescope" "Verification Reopen No Rescope"
seal_to_assessment
verdict_reopen_handoff
reg reopen "$TARGET" handoff --caller-role mod >/dev/null
reg advance "$TARGET" next --caller-role mod >/dev/null

# Nothing was re-scoped: the all-preserved guard falls back to a full reset so a
# re-run can earn the round (rounds=0 + all-completed is intentionally unsealable).
if [[ "$(stage_of tw)" == "completed" || "$(stage_of pe)" == "completed" ]]; then
  printf 'FAIL: no-rescope reopen left a stage completed (deadlock risk): tw=%s pe=%s\n' "$(stage_of tw)" "$(stage_of pe)" >&2
  exit 1
fi
run_pv tw "$TW_PATH"
run_pv pe "$PE_PATH"
assert_sealable "round re-earned after full reset"

printf 'OK: reopen preserves unchanged-scope verification, re-verifies only re-scoped roles, and full-resets when nothing is re-scoped\n'
