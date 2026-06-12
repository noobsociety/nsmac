#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-participant-verify-pending-execution-gate"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa "Participant Verify Pending Execution Gate" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" tw --agent-id claude-sonnet-4-6 >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order "pe tw" --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null

REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['handoff'] = {
    'roles': {
        'pe': {'writeScope': ['platform/tooling/audit.sh'], 'validationCommands': [['./platform/tooling/audit.sh']]},
        'tw': {'writeScope': ['REPOSITORY.md'], 'validationCommands': [['./platform/tooling/audit.sh']]},
    }
}
transcript = registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md")
text = transcript.read_text()
marker = '## Action Plan\n<!-- collab:content-only; do-not-execute -->\n'
replacement = marker + '\n- [x] **pe:** [execute] Complete platform migration.\n- [ ] **tw:** [execute] Rewrite repository contract.\n'
transcript.write_text(text.replace(marker, replacement, 1))
registry.write_text(json.dumps(data, indent=2) + '\n')
PY

"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-06-06T12:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path platform/tooling/audit.sh \
  --caller-role pe >/dev/null

set +e
pv_output="$("$ROOT/commands/collab/engine/registry.py" participant-verify-state "$TARGET" pe 2>&1)"
pv_status=$?
set -e
if [[ "$pv_status" -eq 0 || "$pv_output" != *"participant verification blocked: pending execution role(s): tw; unchecked assigned Action Plan item(s): tw=1; run (collab run plan) for role tw"* ]]; then
  printf 'FAIL: participant verification did not block on pending peer execution\n%s\n' "$pv_output" >&2
  exit 1
fi

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['completion'] = {'subState': 'verification'}
entry['verification'] = {
    'rounds': 1,
    'cap': 3,
    'subState': 'seal',
    'participantVerification': True,
    'participants': {'pe': {'stage': 'completed', 'attempts': 1, 'writeScopeSignature': 'fixture'}},
}
registry.write_text(json.dumps(data, indent=2) + '\n')
PY

seal_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
if [[ "$seal_state" != *'"readyToSeal": false'* || "$seal_state" != *'"executionBlocker": "pending execution role(s): tw; unchecked assigned Action Plan item(s): tw=1; run (collab run plan) for role tw"'* ]]; then
  printf 'FAIL: seal-state did not expose pending execution blocker\n%s\n' "$seal_state" >&2
  exit 1
fi
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$seal_state")"
set +e
seal_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa 2>&1)"
seal_status=$?
set -e
if [[ "$seal_status" -eq 0 || "$seal_output" != *"verification seal blocked: pending execution role(s): tw; unchecked assigned Action Plan item(s): tw=1; run (collab run plan) for role tw"* ]]; then
  printf 'FAIL: seal-render did not reject pending execution blocker\n%s\n' "$seal_output" >&2
  exit 1
fi

printf 'OK: participant verification and seal block while peer execution remains pending\n'
