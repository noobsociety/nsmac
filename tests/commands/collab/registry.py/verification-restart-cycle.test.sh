#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

SLUG="verification-restart-cycle"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa "Verification Restart Cycle" >/dev/null
TARGET="$RUN_DATE-$SLUG"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" tw --agent-id claude-sonnet-4-6 >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order "tw pe" --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
bind_lib_work_repo "$TARGET"
REGISTRY="$(registry_path)"

# Seed handoff write scopes for both assigned roles.
python3 - "$SLUG" "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

slug, registry = sys.argv[1:3]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == slug)
entry['handoff'] = {
    'roles': {
        'tw': {'writeScope': ['platform/tooling/audit.sh'], 'validationCommands': [['./platform/tooling/audit.sh']]},
        'pe': {'writeScope': ['platform/tooling/audit-role-prose.sh'], 'validationCommands': [['./platform/tooling/audit.sh']]},
    }
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY

# Complete execution for both roles.
"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" tw completed "2026-05-17T12:00:00+02:00" \
  --assigned-role tw --assigned-role pe \
  --validation-result passed --validation-scope scoped \
  --touched-path platform/tooling/audit.sh --caller-role tw >/dev/null
"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-17T12:05:00+02:00" \
  --assigned-role tw --assigned-role pe \
  --validation-result passed --validation-scope scoped \
  --touched-path platform/tooling/audit-role-prose.sh --caller-role pe >/dev/null

AUDIT_FILE="$TMPDIR/audit.txt"; printf 'audit clean\n' > "$AUDIT_FILE"
REMEDIATION_FILE="$TMPDIR/remediation.txt"; printf 'no remediation\n' > "$REMEDIATION_FILE"
FINAL_AUDIT_FILE="$TMPDIR/final.txt"; printf 'final clean\n' > "$FINAL_AUDIT_FILE"

run_pv() {
  local role="$1" tpath="$2" state revision
  state="$("$ROOT/commands/collab/engine/registry.py" participant-verify-state "$TARGET" "$role")"
  revision="$(read_json_field registryRevision <<<"$state")"
  "$ROOT/commands/collab/engine/registry.py" participant-verify-render "$TARGET" "$role" \
    --observed-revision "$revision" \
    --audit-file "$AUDIT_FILE" --remediation-file "$REMEDIATION_FILE" --final-audit-file "$FINAL_AUDIT_FILE" \
    --status completed --touched-path "$tpath" --caller-role "$role" >/dev/null
}

assert_rounds_ready() {
  local want_rounds="$1" want_ready="$2" state rounds ready
  state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
  rounds="$(read_json_field verificationRounds <<<"$state")"
  ready="$(read_json_field readyToSeal <<<"$state")"
  if [[ "$rounds" != "$want_rounds" || "$ready" != "$want_ready" ]]; then
    printf 'FAIL: expected rounds=%s ready=%s; got rounds=%s ready=%s\n%s\n' \
      "$want_rounds" "$want_ready" "$rounds" "$ready" "$state" >&2
    exit 1
  fi
}

# First verification cycle: both roles complete -> one paired round, sealable.
run_pv tw platform/tooling/audit.sh
run_pv pe platform/tooling/audit-role-prose.sh
assert_rounds_ready 1 True

# Restart the verification cycle (reviewer recovery primitive).
"$ROOT/commands/collab/engine/registry.py" restart-verification "$TARGET" --caller-role pa >/dev/null

python3 - "$SLUG" "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

slug, registry = sys.argv[1:3]
entry = next(item for item in json.loads(Path(registry).read_text())['collabs'] if item['slug'] == slug)
v = entry['verification']
assert v['rounds'] == 0, v
assert v['subState'] == 'participant', v
assert 'pairedExecutionSignature' not in v, v
for role in ('tw', 'pe'):
    st = v.get('participants', {}).get(role, {})
    assert st.get('stage') != 'completed', (role, st)
    assert st.get('attempts') == 0, (role, st)
PY

# After restart, not sealable until a fresh round is recorded.
assert_rounds_ready 0 False

# Re-verify both roles -> fresh paired round, sealable again.
run_pv tw platform/tooling/audit.sh
run_pv pe platform/tooling/audit-role-prose.sh
assert_rounds_ready 1 True

# Reviewer-only gate: a non-reviewer caller is rejected.
if "$ROOT/commands/collab/engine/registry.py" restart-verification "$TARGET" --caller-role pe 2>/dev/null; then
  printf 'FAIL: restart-verification accepted a non-reviewer caller\n' >&2
  exit 1
fi

# Defense-in-depth (readyToSeal gates on rounds): force a drifted
# rounds=0 + subState=seal + stages-completed state and confirm it is not sealable.
python3 - "$SLUG" "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

slug, registry = sys.argv[1:3]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == slug)
v = entry['verification']
v['rounds'] = 0
v['subState'] = 'seal'
for role in ('tw', 'pe'):
    v.setdefault('participants', {}).setdefault(role, {})['stage'] = 'completed'
path.write_text(json.dumps(data, indent=2) + '\n')
PY

state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
ready="$(read_json_field readyToSeal <<<"$state")"
if [[ "$ready" != "False" ]]; then
  printf 'FAIL: readyToSeal true over zero rounds with subState=seal\n%s\n' "$state" >&2
  exit 1
fi
seal_revision="$(read_json_field registryRevision <<<"$state")"
if "$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$seal_revision" --caller-role pa 2>/dev/null; then
  printf 'FAIL: seal-render accepted a zero-round seal\n' >&2
  exit 1
fi

printf 'OK: restart-verification resets the cycle and zero-round seals stay blocked\n'
