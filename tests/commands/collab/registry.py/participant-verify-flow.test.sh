#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-participant-verify-flow"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa "Participant Verify Flow" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null

REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'participant-verify-flow')
entry['handoff'] = {
    'roles': {
        'pe': {
            'writeScope': ['platform/tooling/audit.sh'],
            'validationCommands': [['./platform/tooling/audit.sh']],
        }
    },
}
registry.write_text(json.dumps(data, indent=2) + '\n')
PY

"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-17T12:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path platform/tooling/audit.sh \
  --caller-role pe >/dev/null

state="$("$ROOT/commands/collab/engine/registry.py" participant-verify-state "$TARGET" pe)"
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"

if [[ "$state" != *'"verificationReviewSubState": "participant"'* || "$state" != *'"readyToVerify": true'* ]]; then
  printf 'FAIL: participant-verify-state did not expose participant readiness\n%s\n' "$state" >&2
  exit 1
fi
if [[ "$state" != *'"stage": "audit"'* ]]; then
  printf 'FAIL: participant-verify-state did not persist the active audit lock\n%s\n' "$state" >&2
  exit 1
fi

speak_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe)"
if [[ "$speak_state" != *'"completionSubState": "verification"'* || "$speak_state" != *'"verificationReviewSubState": "participant"'* || "$speak_state" != *'"expectedRole": "pe"'* || "$speak_state" != *'"readyToWrite": true'* ]]; then
  printf 'FAIL: speak-state did not route Completion.verification.participant to the pending participant\n%s\n' "$speak_state" >&2
  exit 1
fi

seal_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
if [[ "$seal_state" != *'"verificationReviewSubState": "participant"'* ]]; then
  printf 'FAIL: seal-state did not preserve participant sub-state before participant verification\n%s\n' "$seal_state" >&2
  exit 1
fi

set +e
blocked_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$seal_state")" --caller-role pa 2>&1)"
blocked_status=$?
set -e
if [[ "$blocked_status" -eq 0 || "$blocked_output" != *"participant verification is active; next role: pe"* ]]; then
  printf 'FAIL: seal-render did not block before participant verification completed\n%s\n' "$blocked_output" >&2
  exit 1
fi

state="$("$ROOT/commands/collab/engine/registry.py" participant-verify-state "$TARGET" pe)"
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"

AUDIT_FILE="$TMPDIR/audit.txt"
REMEDIATION_FILE="$TMPDIR/remediation.txt"
FINAL_AUDIT_FILE="$TMPDIR/final-audit.txt"
printf 'audit ok\n' > "$AUDIT_FILE"
printf 'remediated scoped issue\n' > "$REMEDIATION_FILE"
printf 'final audit ok\n' > "$FINAL_AUDIT_FILE"

"$ROOT/commands/collab/engine/registry.py" participant-verify-render "$TARGET" pe \
  --observed-revision "$revision" \
  --audit-file "$AUDIT_FILE" \
  --remediation-file "$REMEDIATION_FILE" \
  --final-audit-file "$FINAL_AUDIT_FILE" \
  --status completed \
  --touched-path platform/tooling/audit.sh \
  --audit-agent-id worker-a \
  --remediation-agent-id codex \
  --caller-role pe >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'participant-verify-flow')
transcript = (registry.parent / entry['transcriptPath']).read_text()
state = entry['verification']['participants']['pe']
assert state['stage'] == 'completed', state
assert state['attempts'] == 1, state
assert entry['verification']['subState'] == 'seal', entry['verification']
assert transcript.count('<summary>pe · audit</summary>') == 1
assert transcript.count('<summary>pe · remediation</summary>') == 1
assert transcript.count('<summary>pe · final-audit</summary>') == 1
assert 'AgentId: execution=worker-a; remediation=codex' in transcript
PY

reviewer_speak_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pa)"
if [[ "$reviewer_speak_state" != *'"verificationReviewSubState": "seal"'* || "$reviewer_speak_state" != *'"expectedRole": "pa"'* || "$reviewer_speak_state" != *'"readyToWrite": true'* ]]; then
  printf 'FAIL: speak-state did not route Completion.verification.seal to the reviewer\n%s\n' "$reviewer_speak_state" >&2
  exit 1
fi

seal_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
seal_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$seal_state")"
"$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$seal_revision" \
  --caller-role pa >/dev/null

assessment_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
assessment_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$assessment_state")"
"$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$assessment_revision" \
  --outcome success \
  --evidence '{"registryRevision":2,"committedPaths":["platform/tooling/audit.sh"],"executionEntryIds":["pe-2026-05-17t12-00-00-02-00"]}' \
  --caller-role pa >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'participant-verify-flow')
transcript = (registry.parent / entry['transcriptPath']).read_text()
assert entry['status'] == 'closed', entry
assert entry['verdict']['outcome'] == 'success', entry.get('verdict')
assert transcript.count('### Summary — ') == 1, transcript
assert transcript.index('<summary>pe · final-audit</summary>') < transcript.index('### Summary — ')
PY

printf 'OK: participant verification writes an atomic three-turn sequence, seals, and closes with summary\n'
