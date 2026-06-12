#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

run_case() {
  local title="$1"
  local slug="$2"
  local participant_verification="$3"
  local target="$RUN_DATE-$slug"
  local init_args=(--agent-id codex --reviewer pa)

  if [[ "$participant_verification" == "false" ]]; then
    init_args+=(--no-participant-verification)
  fi
  init_args+=("$title")

  "$ROOT/commands/collab/engine/registry.py" init "${init_args[@]}" >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$target" tw --agent-id claude-sonnet-4-6 >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$target" pe --agent-id codex >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$target" pa --agent-id opus >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$target" turn-order "tw pe" --caller-role mod >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$target" active-phase Completion --force --caller-role mod >/dev/null
  python3 - "$target" "$("$ROOT/commands/collab/engine/registry.py" registry-path)" <<'PY'
import json
import sys
from pathlib import Path

target = sys.argv[1]
registry = Path(sys.argv[2])
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['completion'] = {'subState': 'execution'}
entry.setdefault('verification', {})['subState'] = 'participant'
registry.write_text(json.dumps(data, indent=2) + '\n')
PY

  if [[ "$participant_verification" == "true" ]]; then
    state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$target" pe --resume)"
    STATE="$state" python3 - <<'PY'
import json
import os

state = json.loads(os.environ['STATE'])
assert state['completionSubState'] == 'execution', state
assert state['expectedRole'] == 'tw', state
assert state['allowedRoles'] == ['tw', 'pe'], state
assert state['readyToWrite'] is True, state
assert state['policyBlockers'] == [], state
PY
  fi

  output="$("$ROOT/commands/collab/engine/registry.py" execution "$target" tw completed "2026-05-17T12:00:00+02:00" \
    --assigned-role tw \
    --assigned-role pe \
    --validation-result passed \
    --validation-scope scoped \
    --touched-path commands/collab/engine/registry.py \
    --caller-role tw 2>&1)"

  if [[ "$output" != *"NEXT: Run (collab run plan) for role pe."* ]]; then
    printf 'FAIL: execution NEXT did not name the pending peer role for %s\n%s\n' "$slug" "$output" >&2
    exit 1
  fi
  if [[ "$output" == *"NEXT: Run (collab run plan) for role tw."* ]]; then
    printf 'FAIL: execution NEXT named the role that just completed for %s\n%s\n' "$slug" "$output" >&2
    exit 1
  fi
  if [[ "$output" == *"NEXT: Run (collab seal verification)"* ]]; then
    printf 'FAIL: execution NEXT skipped pending execution and named seal verification for %s\n%s\n' "$slug" "$output" >&2
    exit 1
  fi
  if [[ "$output" == *"NEXT: Run (collab participant verify)"* ]]; then
    printf 'FAIL: execution NEXT skipped pending execution and named participant verification for %s\n%s\n' "$slug" "$output" >&2
    exit 1
  fi

  if [[ "$participant_verification" == "true" ]]; then
    state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$target" pe --resume)"
    STATE="$state" python3 - <<'PY'
import json
import os

state = json.loads(os.environ['STATE'])
assert state['completionSubState'] == 'execution', state
assert state['expectedRole'] == 'pe', state
assert state['allowedRoles'] == ['tw', 'pe'], state
assert state['readyToWrite'] is True, state
assert state['policyBlockers'] == [], state
PY
  fi
}

run_case "Execution Next Mixed Completion" "execution-next-mixed-completion" false
run_case "Execution Next Mixed Completion Participant Verify" "execution-next-mixed-completion-participant-verify" true

printf 'OK: execution NEXT names pending peer execution before reviewer verification advisories\n'
