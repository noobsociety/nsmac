#!/usr/bin/env bash
set -euo pipefail

CASE_NAME="${1:?case name required}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
RUN_DATE="$(date +%Y-%m-%d)"
REGISTRY="$TMPDIR/registry.json"
REGISTRY_PY="$ROOT/commands/collab/engine/registry.py"

assert_fails_containing() {
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
    printf 'FAIL: %s\nexpected: %s\nactual:\n%s\n' "$label" "$needle" "$output" >&2
    exit 1
  fi
}

init_target() {
  local title="$1"
  local slug="$2"
  "$REGISTRY_PY" --registry "$REGISTRY" init --agent-id codex "$title" >/dev/null
  printf '%s-%s\n' "$RUN_DATE" "$slug"
}

init_target_with_reviewer() {
  local title="$1"
  local slug="$2"
  local reviewer="$3"
  "$REGISTRY_PY" --registry "$REGISTRY" init --agent-id codex --reviewer "$reviewer" "$title" >/dev/null
  printf '%s-%s\n' "$RUN_DATE" "$slug"
}

transcript_path_for_target() {
  local target="$1"
  python3 - "$REGISTRY" "$target" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['id'] == target)
print(registry.parent / entry['transcriptPath'])
PY
}

remove_transcript() {
  local target="$1"
  local transcript
  transcript="$(transcript_path_for_target "$target")"
  rm "$transcript"
}

set_active_phase() {
  local target="$1"
  local phase="$2"
  python3 - "$REGISTRY" "$target" "$phase" <<'PY'
import json
import sys
from pathlib import Path

registry, target, phase = sys.argv[1:4]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['activePhase'] = phase
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

role_fixture_dir() {
  local roles_dir="$TMPDIR/roles"
  cp -R "$ROOT/commands/collab/reference/roles" "$roles_dir"
  printf '%s\n' "$roles_dir"
}

write_invalid_role_fixture() {
  local roles_dir="$1"
  local role="$2"
  printf '{invalid json\n' >"$roles_dir/$role.json"
}

join_role() {
  local target="$1"
  local role="$2"
  "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" "$role" --agent-id codex >/dev/null
}

summary_file() {
  local path="$TMPDIR/summary.md"
  printf 'Replacement summary.\n' >"$path"
  printf '%s\n' "$path"
}

content_file() {
  local body="${1:-Contribution body.}"
  local path="$TMPDIR/content.md"
  printf '%s\n' "$body" >"$path"
  printf '%s\n' "$path"
}

empty_content_file() {
  local path="$TMPDIR/empty-content.md"
  : >"$path"
  printf '%s\n' "$path"
}

registry_revision_for_target() {
  local target="$1"
  "$REGISTRY_PY" --registry "$REGISTRY" speak-state "$target" mod 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])'
}

# Append one moderator contribution in the active phase, then pin the registry so
# the moderator role is both the expected speaker and an existing contributor in a
# one-speak phase (the state the duplicate-phase guard rejects).
record_moderator_speak_then_pin() {
  local target="$1"
  local phase="$2"
  local revision
  revision="$(registry_revision_for_target "$target")"
  "$REGISTRY_PY" --registry "$REGISTRY" speak-render "$target" mod \
    --content-file "$(content_file "First contribution.")" \
    --observed-revision "$revision" --caller-role mod >/dev/null
  python3 - "$REGISTRY" "$target" "$phase" <<'PY'
import json
import sys
from pathlib import Path

registry, target, phase = sys.argv[1:4]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['activePhase'] = phase
entry['turnOrder'] = ['mod']
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

# Tier-4 execution fixture: a Completion-phase record with joined non-moderator
# roles and a turn order. `--reviewer` is omitted so the close path is reachable
# without a verification seal. Prints the resolved target id.
init_execution_target() {
  local title="$1"
  local slug="$2"
  local target="$RUN_DATE-$slug"
  "$REGISTRY_PY" --registry "$REGISTRY" init --agent-id codex "$title" >/dev/null
  "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" tw --agent-id claude-sonnet >/dev/null
  "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" pe --agent-id codex >/dev/null
  "$REGISTRY_PY" --registry "$REGISTRY" set "$target" turn-order "tw pe" --caller-role mod >/dev/null
  "$REGISTRY_PY" --registry "$REGISTRY" set "$target" active-phase Completion --force --caller-role mod >/dev/null
  printf '%s\n' "$target"
}

# Append one unchecked `**<role>:**` Action Plan item so the execution recorder's
# unchecked-assigned-item backstop (the requires-chain "perform or halt" contract)
# fires when recording `completed`.
seed_unchecked_action_plan_item() {
  local target="$1"
  local role="$2"
  python3 - "$REGISTRY" "$target" "$role" <<'PY'
import json
import sys
from pathlib import Path

registry, target, role = sys.argv[1:4]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
transcript = path.parent / entry['transcriptPath']
lines = transcript.read_text().splitlines()
out = []
for line in lines:
    out.append(line)
    if line.strip() == '## Action Plan':
        out.append('')
        out.append(f'- [ ] **{role}:** implement the assigned work item')
transcript.write_text('\n'.join(out) + '\n')
PY
}

# Reviewer-backed Completion fixture with execution recorded complete for each
# listed executor role, which advances the verification sub-state to
# `participant`. The reviewer is `pa`. Pass executor roles after the slug.
# Prints the resolved target id.
init_participant_verify_target() {
  local title="$1"
  local slug="$2"
  shift 2
  local target="$RUN_DATE-$slug"
  "$REGISTRY_PY" --registry "$REGISTRY" init --agent-id codex --reviewer pa "$title" >/dev/null
  "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" pa --agent-id codex >/dev/null
  local role
  for role in "$@"; do
    "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" "$role" --agent-id codex >/dev/null
  done
  "$REGISTRY_PY" --registry "$REGISTRY" set "$target" turn-order "$*" --caller-role mod >/dev/null
  "$REGISTRY_PY" --registry "$REGISTRY" set "$target" active-phase Completion --force --caller-role mod >/dev/null
  for role in "$@"; do
    "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" "$role" completed "2026-06-24T12:00:00+02:00" --caller-role "$role" >/dev/null
  done
  printf '%s\n' "$target"
}

# Inject a schema-valid non-success verdict so reopen/show-verdict reach their
# verdict-dependent guards. restoreTarget defaults to `Action Plan`.
seed_failed_verdict() {
  local target="$1"
  local restore_target="${2:-Action Plan}"
  python3 - "$REGISTRY" "$target" "$restore_target" <<'PY'
import json
import sys
from pathlib import Path

registry, target, restore_target = sys.argv[1:4]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['verdict'] = {
    'outcome': 'failed',
    'restoreTarget': restore_target,
    'restoreReason': 'seeded failed verdict for reopen guard fixture',
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

case "$CASE_NAME" in
  join-role-required)
    init_target "Join Role Required" "join-role-required" >/dev/null
    assert_fails_containing "$CASE_NAME" "the following arguments are required: role" \
      "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$RUN_DATE-join-role-required" --agent-id codex
    ;;
  join-role-file-unreadable)
    target="$(init_target "Join Role File Unreadable" "join-role-file-unreadable")"
    roles_dir="$(role_fixture_dir)"
    rm "$roles_dir/pe.json"
    assert_fails_containing "$CASE_NAME" "role missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" pe --roles-dir "$roles_dir" --agent-id codex
    ;;
  join-invalid-role-json)
    target="$(init_target "Join Invalid Role Json" "join-invalid-role-json")"
    roles_dir="$(role_fixture_dir)"
    write_invalid_role_fixture "$roles_dir" pe
    assert_fails_containing "$CASE_NAME" "role invalid JSON:" \
      "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" pe --roles-dir "$roles_dir" --agent-id codex
    ;;
  join-record-unreadable)
    target="$(init_target "Join Record Unreadable" "join-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" pe --agent-id codex
    ;;
  join-record-is-closed)
    target="$(init_target "Join Record Is Closed" "join-record-is-closed")"
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" pe --agent-id codex
    ;;
  join-registry-target-unavailable)
    init_target "Join Target Unavailable" "join-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" join-participants missing pe --agent-id codex
    ;;
  remove-participant-role-required)
    init_target "Remove Participant Role Required" "remove-participant-role-required" >/dev/null
    assert_fails_containing "$CASE_NAME" "the following arguments are required: role" \
      "$REGISTRY_PY" --registry "$REGISTRY" remove-participant "$RUN_DATE-remove-participant-role-required" --caller-role mod
    ;;
  remove-participant-record-unreadable)
    target="$(init_target "Remove Participant Record Unreadable" "remove-participant-record-unreadable")"
    join_role "$target" pe
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" remove-participant "$target" pe --caller-role mod
    ;;
  remove-participant-moderator-removal-block)
    target="$(init_target "Remove Participant Moderator Removal Block" "remove-participant-moderator-removal-block")"
    assert_fails_containing "$CASE_NAME" "moderator cannot be removed" \
      "$REGISTRY_PY" --registry "$REGISTRY" remove-participant "$target" mod --caller-role mod
    ;;
  remove-participant-reviewer-removal-block)
    target="$(init_target_with_reviewer "Remove Participant Reviewer Removal Block" "remove-participant-reviewer-removal-block" pa)"
    join_role "$target" pa
    assert_fails_containing "$CASE_NAME" "reviewer cannot be removed while assigned" \
      "$REGISTRY_PY" --registry "$REGISTRY" remove-participant "$target" pa --caller-role mod
    ;;
  remove-participant-registry-target-unavailable)
    init_target "Remove Participant Target Unavailable" "remove-participant-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" remove-participant missing pe --caller-role mod
    ;;
  retract-speak-role-not-registered)
    target="$(init_target "Retract Speak Role Not Registered" "retract-speak-role-not-registered")"
    assert_fails_containing "$CASE_NAME" "role must already be a participant: pe" \
      "$REGISTRY_PY" --registry "$REGISTRY" retract-speak "$target" pe --caller-role pe
    ;;
  retract-speak-record-is-closed)
    target="$(init_target "Retract Speak Record Is Closed" "retract-speak-record-is-closed")"
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" retract-speak "$target" mod --caller-role mod
    ;;
  retract-speak-registry-target-unavailable)
    init_target "Retract Speak Target Unavailable" "retract-speak-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" retract-speak missing mod --caller-role mod
    ;;
  set-field-required)
    init_target "Set Field Required" "set-field-required" >/dev/null
    assert_fails_containing "$CASE_NAME" "the following arguments are required: field" \
      "$REGISTRY_PY" --registry "$REGISTRY" set "$RUN_DATE-set-field-required" --caller-role mod
    ;;
  set-value-required)
    target="$(init_target "Set Value Required" "set-value-required")"
    assert_fails_containing "$CASE_NAME" "title requires a value" \
      "$REGISTRY_PY" --registry "$REGISTRY" set "$target" title --caller-role mod
    ;;
  set-record-unreadable)
    target="$(init_target "Set Record Unreadable" "set-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" set "$target" title "New Title" --caller-role mod
    ;;
  set-field-not-settable)
    target="$(init_target "Set Field Not Settable" "set-field-not-settable")"
    assert_fails_containing "$CASE_NAME" "field not settable: status" \
      "$REGISTRY_PY" --registry "$REGISTRY" set "$target" status closed --caller-role mod
    ;;
  set-registry-target-unavailable)
    init_target "Set Target Unavailable" "set-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" set missing title "New Title" --caller-role mod
    ;;
  unset-field-required)
    init_target "Unset Field Required" "unset-field-required" >/dev/null
    assert_fails_containing "$CASE_NAME" "the following arguments are required: field" \
      "$REGISTRY_PY" --registry "$REGISTRY" unset "$RUN_DATE-unset-field-required" --caller-role mod
    ;;
  unset-record-unreadable)
    target="$(init_target "Unset Record Unreadable" "unset-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" unset "$target" reviewer --caller-role mod
    ;;
  unset-field-not-unsettable)
    target="$(init_target "Unset Field Not Unsettable" "unset-field-not-unsettable")"
    assert_fails_containing "$CASE_NAME" "field not unsettable: title" \
      "$REGISTRY_PY" --registry "$REGISTRY" unset "$target" title --caller-role mod
    ;;
  unset-registry-target-unavailable)
    init_target "Unset Target Unavailable" "unset-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" unset missing reviewer --caller-role mod
    ;;
  summarize-record-unreadable)
    target="$(init_target "Summarize Record Unreadable" "summarize-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" summarize "$target"
    ;;
  summarize-registry-target-unavailable)
    init_target "Summarize Target Unavailable" "summarize-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" summarize missing
    ;;
  advance-record-unreadable)
    target="$(init_target "Advance Record Unreadable" "advance-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance "$target" next --caller-role mod
    ;;
  advance-record-is-closed)
    target="$(init_target "Advance Record Is Closed" "advance-record-is-closed")"
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance "$target" next --caller-role mod
    ;;
  advance-active-phase-missing)
    target="$(init_target "Advance Active Phase Missing" "advance-active-phase-missing")"
    set_active_phase "$target" "Unknown"
    assert_fails_containing "$CASE_NAME" "collab activePhase must be one of" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance "$target" next --caller-role mod
    ;;
  advance-no-next-phase)
    target="$(init_target "Advance No Next Phase" "advance-no-next-phase")"
    set_active_phase "$target" "Completion"
    assert_fails_containing "$CASE_NAME" "no next phase" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance "$target" next --caller-role mod
    ;;
  advance-registry-target-unavailable)
    init_target "Advance Target Unavailable" "advance-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance missing next --caller-role mod
    ;;
  activate-record-required)
    assert_fails_containing "$CASE_NAME" "the following arguments are required: target" \
      "$REGISTRY_PY" --registry "$REGISTRY" activate
    ;;
  activate-registry-unreadable)
    assert_fails_containing "$CASE_NAME" "registry missing:" \
      "$REGISTRY_PY" --registry "$TMPDIR/missing-registry.json" activate missing
    ;;
  activate-registry-target-unavailable)
    init_target "Activate Target Unavailable" "activate-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" activate missing
    ;;
  activate-registry-target-archived)
    target="$(init_target "Activate Target Archived" "activate-target-archived")"
    "$REGISTRY_PY" --registry "$REGISTRY" archive "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target archived: $target" \
      "$REGISTRY_PY" --registry "$REGISTRY" activate "$target"
    ;;
  archive-record-unreadable)
    target="$(init_target "Archive Record Unreadable" "archive-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" archive "$target" --caller-role mod
    ;;
  archive-registry-target-unavailable)
    init_target "Archive Target Unavailable" "archive-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" archive missing --caller-role mod
    ;;
  close-record-unreadable)
    target="$(init_target "Close Record Unreadable" "close-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod
    ;;
  close-registry-target-unavailable)
    init_target "Close Target Unavailable" "close-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" close missing --caller-role mod
    ;;
  delete-record-unreadable)
    target="$(init_target "Delete Record Unreadable" "delete-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" delete "$target" --yes --caller-role mod
    ;;
  delete-registry-target-unavailable)
    init_target "Delete Target Unavailable" "delete-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" delete missing --yes --caller-role mod
    ;;
  open-record-unreadable)
    target="$(init_target "Open Record Unreadable" "open-record-unreadable")"
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" open "$target" --caller-role mod
    ;;
  open-registry-target-unavailable)
    init_target "Open Target Unavailable" "open-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" open missing --caller-role mod
    ;;
  open-record-archived)
    target="$(init_target "Open Record Archived" "open-record-archived")"
    "$REGISTRY_PY" --registry "$REGISTRY" archive "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "archived records must be restored before reopening" \
      "$REGISTRY_PY" --registry "$REGISTRY" open "$target" --caller-role mod
    ;;
  restore-record-unreadable)
    target="$(init_target "Restore Record Unreadable" "restore-record-unreadable")"
    set_active_phase "$target" "Discussion"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance "$target" prev --caller-role mod
    ;;
  restore-record-is-closed)
    target="$(init_target "Restore Record Is Closed" "restore-record-is-closed")"
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance "$target" prev --caller-role mod
    ;;
  restore-active-phase-missing)
    target="$(init_target "Restore Active Phase Missing" "restore-active-phase-missing")"
    set_active_phase "$target" "Unknown"
    assert_fails_containing "$CASE_NAME" "collab activePhase must be one of" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance "$target" prev --caller-role mod
    ;;
  restore-no-previous-phase)
    target="$(init_target "Restore No Previous Phase" "restore-no-previous-phase")"
    assert_fails_containing "$CASE_NAME" "no previous phase" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance "$target" prev --caller-role mod
    ;;
  restore-registry-target-unavailable)
    init_target "Restore Target Unavailable" "restore-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" advance missing prev --caller-role mod
    ;;
  speak-record-unreadable)
    target="$(init_target "Speak Record Unreadable" "speak-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-state "$target" mod
    ;;
  speak-record-is-closed)
    target="$(init_target "Speak Record Is Closed" "speak-record-is-closed")"
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-state "$target" mod
    ;;
  speak-active-phase-missing)
    target="$(init_target "Speak Active Phase Missing" "speak-active-phase-missing")"
    set_active_phase "$target" "Unknown"
    assert_fails_containing "$CASE_NAME" "collab activePhase must be one of" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-state "$target" mod
    ;;
  speak-completion-block)
    target="$(init_target "Speak Completion Block" "speak-completion-block")"
    set_active_phase "$target" "Completion"
    assert_fails_containing "$CASE_NAME" "speak-render is not permitted in Completion" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-render "$target" mod \
        --content-file "$(content_file)" --observed-revision 1 --caller-role mod
    ;;
  speak-invalid-turn-order)
    target="$(init_target "Speak Invalid Turn Order" "speak-invalid-turn-order")"
    assert_fails_containing "$CASE_NAME" "turn-order roles must already be participants" \
      "$REGISTRY_PY" --registry "$REGISTRY" set "$target" turn-order "mod missing" --caller-role mod
    ;;
  speak-participant-not-joined)
    target="$(init_target "Speak Participant Not Joined" "speak-participant-not-joined")"
    assert_fails_containing "$CASE_NAME" "role must already be a participant: pe" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-state "$target" pe
    ;;
  speak-expected-role)
    target="$(init_target "Speak Expected Role" "speak-expected-role")"
    join_role "$target" pe
    assert_fails_containing "$CASE_NAME" "expected role:" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-state "$target" pe
    ;;
  speak-moderator-text-required)
    target="$(init_target "Speak Moderator Text Required" "speak-moderator-text-required")"
    assert_fails_containing "$CASE_NAME" "content must be non-empty" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-render "$target" mod \
        --content-file "$(empty_content_file)" --observed-revision 1 --caller-role mod
    ;;
  speak-duplicate-phase-contribution)
    target="$(init_target "Speak Duplicate Phase Contribution" "speak-duplicate-phase-contribution")"
    record_moderator_speak_then_pin "$target" "Audit"
    assert_fails_containing "$CASE_NAME" "duplicate phase contribution: mod in Audit" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-render "$target" mod \
        --content-file "$(content_file "Second contribution.")" \
        --observed-revision "$(registry_revision_for_target "$target")" --caller-role mod
    ;;
  speak-registry-target-unavailable)
    init_target "Speak Target Unavailable" "speak-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" speak-state missing mod
    ;;
  rewrite-speak-record-unreadable)
    target="$(init_target "Rewrite Speak Record Unreadable" "rewrite-speak-record-unreadable")"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" rewrite-speak-render "$target" mod \
        --content-file "$(content_file)" --caller-role mod
    ;;
  rewrite-speak-record-is-closed)
    target="$(init_target "Rewrite Speak Record Is Closed" "rewrite-speak-record-is-closed")"
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" rewrite-speak-render "$target" mod \
        --content-file "$(content_file)" --caller-role mod
    ;;
  rewrite-speak-active-phase-missing)
    target="$(init_target "Rewrite Speak Active Phase Missing" "rewrite-speak-active-phase-missing")"
    set_active_phase "$target" "Unknown"
    assert_fails_containing "$CASE_NAME" "collab activePhase must be one of" \
      "$REGISTRY_PY" --registry "$REGISTRY" rewrite-speak-render "$target" mod \
        --content-file "$(content_file)" --caller-role mod
    ;;
  rewrite-speak-completion-block)
    target="$(init_target "Rewrite Speak Completion Block" "rewrite-speak-completion-block")"
    set_active_phase "$target" "Completion"
    assert_fails_containing "$CASE_NAME" "rewrite-speak-render is not permitted in Completion" \
      "$REGISTRY_PY" --registry "$REGISTRY" rewrite-speak-render "$target" mod \
        --content-file "$(content_file)" --caller-role mod
    ;;
  rewrite-speak-participant-not-joined)
    target="$(init_target "Rewrite Speak Participant Not Joined" "rewrite-speak-participant-not-joined")"
    assert_fails_containing "$CASE_NAME" "role must already be a participant: pe" \
      "$REGISTRY_PY" --registry "$REGISTRY" rewrite-speak-render "$target" pe \
        --content-file "$(content_file)" --caller-role pe
    ;;
  rewrite-speak-no-prior-contribution)
    target="$(init_target "Rewrite Speak No Prior Contribution" "rewrite-speak-no-prior-contribution")"
    assert_fails_containing "$CASE_NAME" "no prior contribution to rewrite" \
      "$REGISTRY_PY" --registry "$REGISTRY" rewrite-speak-render "$target" mod \
        --content-file "$(content_file)" --caller-role mod
    ;;
  rewrite-speak-moderator-text-required)
    target="$(init_target "Rewrite Speak Moderator Text Required" "rewrite-speak-moderator-text-required")"
    assert_fails_containing "$CASE_NAME" "content must be non-empty" \
      "$REGISTRY_PY" --registry "$REGISTRY" rewrite-speak-render "$target" mod \
        --content-file "$(empty_content_file)" --caller-role mod
    ;;
  rewrite-speak-registry-target-unavailable)
    init_target "Rewrite Speak Target Unavailable" "rewrite-speak-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" rewrite-speak-render missing mod \
        --content-file "$(content_file)" --caller-role mod
    ;;
  run-plan-record-is-closed)
    target="$(init_target "Run Plan Record Is Closed" "run-plan-record-is-closed")"
    join_role "$target" pe
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" pe completed "2026-06-24T12:00:00+02:00" --caller-role pe
    ;;
  run-plan-active-phase-missing)
    target="$(init_target "Run Plan Active Phase Missing" "run-plan-active-phase-missing")"
    join_role "$target" pe
    set_active_phase "$target" "Unknown"
    assert_fails_containing "$CASE_NAME" "collab activePhase must be one of" \
      "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" pe completed "2026-06-24T12:00:00+02:00" --caller-role pe
    ;;
  run-plan-phase-not-completion)
    target="$(init_target "Run Plan Phase Not Completion" "run-plan-phase-not-completion")"
    join_role "$target" pe
    set_active_phase "$target" "Audit"
    assert_fails_containing "$CASE_NAME" "execute-spawn is valid only in Completion" \
      "$REGISTRY_PY" --registry "$REGISTRY" execute-spawn "$target" pe --scope commands/
    ;;
  run-plan-role-not-registered)
    target="$(init_target "Run Plan Role Not Registered" "run-plan-role-not-registered")"
    assert_fails_containing "$CASE_NAME" "caller role must already be a participant: pe" \
      "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" pe completed "2026-06-24T12:00:00+02:00" --caller-role pe
    ;;
  run-plan-requires-chain)
    target="$(init_execution_target "Run Plan Requires Chain" "run-plan-requires-chain")"
    seed_unchecked_action_plan_item "$target" tw
    assert_fails_containing "$CASE_NAME" "execution completed blocked for role tw: 1 unchecked assigned Action Plan item(s) remain" \
      "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" tw completed "2026-06-24T12:00:00+02:00" --assigned-role tw --caller-role tw
    ;;
  run-plan-registry-target)
    init_target "Run Plan Target Unavailable" "run-plan-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" execution missing pe completed "2026-06-24T12:00:00+02:00" --caller-role pe
    ;;
  rewrite-execution-record-is-closed)
    target="$(init_target "Rewrite Execution Record Is Closed" "rewrite-execution-record-is-closed")"
    join_role "$target" pe
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" pe in_progress "2026-06-24T12:00:00+02:00" --caller-role pe
    ;;
  rewrite-execution-active-phase-missing)
    target="$(init_target "Rewrite Execution Active Phase Missing" "rewrite-execution-active-phase-missing")"
    join_role "$target" pe
    set_active_phase "$target" "Unknown"
    assert_fails_containing "$CASE_NAME" "collab activePhase must be one of" \
      "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" pe in_progress "2026-06-24T12:00:00+02:00" --caller-role pe
    ;;
  rewrite-execution-phase-not-completion)
    target="$(init_target "Rewrite Execution Phase Not Completion" "rewrite-execution-phase-not-completion")"
    join_role "$target" pe
    set_active_phase "$target" "Audit"
    assert_fails_containing "$CASE_NAME" "execute-spawn is valid only in Completion" \
      "$REGISTRY_PY" --registry "$REGISTRY" execute-spawn "$target" pe --scope commands/
    ;;
  rewrite-execution-role-not-registered)
    target="$(init_target "Rewrite Execution Role Not Registered" "rewrite-execution-role-not-registered")"
    assert_fails_containing "$CASE_NAME" "caller role must already be a participant: pe" \
      "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" pe in_progress "2026-06-24T12:00:00+02:00" --caller-role pe
    ;;
  log-registry-target)
    init_target "Log Target Unavailable" "log-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" log missing
    ;;
  participant-verify-record-unreadable)
    target="$(init_target "Participant Verify Record Unreadable" "participant-verify-record-unreadable")"
    join_role "$target" pe
    "$REGISTRY_PY" --registry "$REGISTRY" set "$target" active-phase Completion --force --caller-role mod >/dev/null
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" participant-verify-state "$target" pe
    ;;
  participant-verify-record-closed)
    target="$(init_target "Participant Verify Record Closed" "participant-verify-record-closed")"
    "$REGISTRY_PY" --registry "$REGISTRY" close "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is closed" \
      "$REGISTRY_PY" --registry "$REGISTRY" participant-verify-state "$target" pe
    ;;
  participant-verify-phase-not-completion)
    target="$(init_target "Participant Verify Phase Not Completion" "participant-verify-phase-not-completion")"
    assert_fails_containing "$CASE_NAME" "(collab participant verify) requires activePhase = Completion" \
      "$REGISTRY_PY" --registry "$REGISTRY" participant-verify-state "$target" pe
    ;;
  participant-verify-substate-not-participant)
    target="$RUN_DATE-participant-verify-substate-not-participant"
    "$REGISTRY_PY" --registry "$REGISTRY" init --agent-id codex --reviewer pa "Participant Verify Substate Not Participant" >/dev/null
    "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" pa --agent-id codex >/dev/null
    "$REGISTRY_PY" --registry "$REGISTRY" join-participants "$target" pe --agent-id codex >/dev/null
    "$REGISTRY_PY" --registry "$REGISTRY" set "$target" turn-order "pe" --caller-role mod >/dev/null
    "$REGISTRY_PY" --registry "$REGISTRY" set "$target" active-phase Completion --force --caller-role mod >/dev/null
    "$REGISTRY_PY" --registry "$REGISTRY" execution "$target" pe completed "2026-06-24T12:00:00+02:00" --caller-role pe >/dev/null
    python3 - "$REGISTRY" "$target" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['verification']['subState'] = 'seal'
path.write_text(json.dumps(data, indent=2) + '\n')
PY
    assert_fails_containing "$CASE_NAME" "participant verification already complete" \
      "$REGISTRY_PY" --registry "$REGISTRY" participant-verify-state "$target" pe
    ;;
  participant-verify-role-not-registered)
    target="$(init_target "Participant Verify Role Not Registered" "participant-verify-role-not-registered")"
    "$REGISTRY_PY" --registry "$REGISTRY" set "$target" active-phase Completion --force --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "role must already be a participant: pe" \
      "$REGISTRY_PY" --registry "$REGISTRY" participant-verify-state "$target" pe
    ;;
  participant-verify-not-assigned)
    target="$(init_participant_verify_target "Participant Verify Not Assigned" "participant-verify-not-assigned" pe)"
    assert_fails_containing "$CASE_NAME" "role is not assigned to participant verification: pa" \
      "$REGISTRY_PY" --registry "$REGISTRY" participant-verify-state "$target" pa
    ;;
  participant-verify-turn-lock)
    target="$(init_participant_verify_target "Participant Verify Turn Lock" "participant-verify-turn-lock" pe tw)"
    assert_fails_containing "$CASE_NAME" "participant verification turn lock is held by role pe" \
      "$REGISTRY_PY" --registry "$REGISTRY" participant-verify-state "$target" tw
    ;;
  participant-verify-registry-target)
    init_target "Participant Verify Target Unavailable" "participant-verify-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" participant-verify-state missing pe
    ;;
  reopen-record-unreadable)
    target="$(init_target "Reopen Record Unreadable" "reopen-record-unreadable")"
    "$REGISTRY_PY" --registry "$REGISTRY" set "$target" active-phase Completion --force --caller-role mod >/dev/null
    seed_failed_verdict "$target" "Action Plan"
    remove_transcript "$target"
    assert_fails_containing "$CASE_NAME" "transcript missing:" \
      "$REGISTRY_PY" --registry "$REGISTRY" reopen "$target" action-plan --caller-role mod
    ;;
  reopen-phase-invalid)
    target="$(init_target "Reopen Phase Invalid" "reopen-phase-invalid")"
    assert_fails_containing "$CASE_NAME" "invalid choice: 'badphase'" \
      "$REGISTRY_PY" --registry "$REGISTRY" reopen "$target" badphase --caller-role mod
    ;;
  reopen-archived)
    target="$(init_target "Reopen Archived" "reopen-archived")"
    "$REGISTRY_PY" --registry "$REGISTRY" archive "$target" --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "record is archived" \
      "$REGISTRY_PY" --registry "$REGISTRY" reopen "$target" action-plan --caller-role mod
    ;;
  reopen-not-completion)
    target="$(init_target "Reopen Not Completion" "reopen-not-completion")"
    assert_fails_containing "$CASE_NAME" "(collab reopen) is valid only after a non-success Completion verdict" \
      "$REGISTRY_PY" --registry "$REGISTRY" reopen "$target" action-plan --caller-role mod
    ;;
  reopen-no-verdict)
    target="$(init_target "Reopen No Verdict" "reopen-no-verdict")"
    "$REGISTRY_PY" --registry "$REGISTRY" set "$target" active-phase Completion --force --caller-role mod >/dev/null
    assert_fails_containing "$CASE_NAME" "(collab reopen) requires a non-success Completion verdict" \
      "$REGISTRY_PY" --registry "$REGISTRY" reopen "$target" action-plan --caller-role mod
    ;;
  reopen-phase-mismatch)
    target="$(init_target "Reopen Phase Mismatch" "reopen-phase-mismatch")"
    "$REGISTRY_PY" --registry "$REGISTRY" set "$target" active-phase Completion --force --caller-role mod >/dev/null
    seed_failed_verdict "$target" "Action Plan"
    assert_fails_containing "$CASE_NAME" "(collab reopen) phase mismatch: verdict restoreTarget is Action Plan; expected action-plan" \
      "$REGISTRY_PY" --registry "$REGISTRY" reopen "$target" handoff --caller-role mod
    ;;
  reopen-registry-target)
    init_target "Reopen Target Unavailable" "reopen-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" reopen missing action-plan --caller-role mod
    ;;
  show-verdict-registry-target)
    init_target "Show Verdict Target Unavailable" "show-verdict-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" show-verdict missing
    ;;
  status-registry-target)
    init_target "Status Target Unavailable" "status-target-unavailable" >/dev/null
    assert_fails_containing "$CASE_NAME" "registry target not found: missing" \
      "$REGISTRY_PY" --registry "$REGISTRY" status-view missing
    ;;
  *)
    printf 'FAIL: unknown admin guard case: %s\n' "$CASE_NAME" >&2
    exit 1
    ;;
esac

printf 'OK: %s abort path covered\n' "$CASE_NAME"
