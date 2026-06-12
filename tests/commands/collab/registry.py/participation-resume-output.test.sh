#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-participation-resume-output"

"$ROOT/commands/collab/engine/registry.py" init --agent-id mod-agent "Participation Resume Output" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"

join_output="$("$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id gpt)"
if [[ "$join_output" != *"RESUME: commands/collab/engine/registry.py speak-state --resume $TARGET pe"* ]]; then
  printf 'FAIL: join advisory did not include exact resume command\n%s\n' "$join_output" >&2
  exit 1
fi
if [[ "$join_output" != *"TRANSCRIPT: commands/collab/engine/registry.py transcript-view $TARGET Audit --raw"* ]]; then
  printf 'FAIL: join advisory did not include active-phase transcript pointer\n%s\n' "$join_output" >&2
  exit 1
fi

"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" tw --agent-id sonnet >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order "pe tw" --caller-role mod >/dev/null

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe --resume)"
STATE="$state" python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
state = json.loads(os.environ['STATE'])
assert state['nextCommand'] == f'(collab speak {target})', state
assert state['nextTranscriptCommand'] == f'commands/collab/engine/registry.py transcript-view {target} Audit --raw', state
assert state['policyBlockers'] == [], state
assert state['phaseSummary']['activePhase'] == 'Audit', state
assert state['phaseSummary']['status'] == 'open', state
assert state['phaseSummary']['expectedRole'] == 'pe', state
assert 'excerptAnchors' not in state, state
PY

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" mod --resume)"
STATE="$state" python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
state = json.loads(os.environ['STATE'])
assert state['nextTranscriptCommand'] == f'commands/collab/engine/registry.py transcript-view {target} Audit', state
assert not state['nextTranscriptCommand'].endswith('--raw'), state
PY

"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Discussion --force --caller-role mod >/dev/null
state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe)"
revision="$(STATE="$state" python3 - <<'PY'
import json
import os

print(json.loads(os.environ['STATE'])['registryRevision'])
PY
)"
printf 'discussion anchor source\n' >discussion.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" pe \
  --content-file discussion.md \
  --observed-revision "$revision" \
  --caller-role pe >/dev/null
state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" tw --resume)"
STATE="$state" python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
state = json.loads(os.environ['STATE'])
assert state['nextCommand'], state
assert state['nextCommand'].startswith('(collab speak '), state
assert target in state['nextCommand'], state
assert state['phaseSummary']['activePhase'] == 'Discussion', state
assert 'discussion-pe-1' in state['excerptAnchors'], state
PY

"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Conclusion --force --caller-role mod >/dev/null
state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe --resume)"
STATE="$state" python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
state = json.loads(os.environ['STATE'])
assert state['nextCommand'], state
assert state['nextCommand'].startswith('(collab speak '), state
assert target in state['nextCommand'], state
assert state['phaseSummary']['activePhase'] == 'Conclusion', state
PY

"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Handoff --force --caller-role mod >/dev/null
state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe --resume)"
STATE="$state" python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
state = json.loads(os.environ['STATE'])
assert state['nextCommand'], state
assert state['nextCommand'].startswith('(collab speak '), state
assert target in state['nextCommand'], state
assert state['phaseSummary']['activePhase'] == 'Handoff', state
PY

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['activePhase'] = 'Action Plan'
registry.write_text(json.dumps(data, indent=2) + '\n')
PY

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe --resume)"
STATE="$state" python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
state = json.loads(os.environ['STATE'])
assert state['nextCommand'] == f'(collab speak {target})', state
assert state['nextTranscriptCommand'] == f"commands/collab/engine/registry.py transcript-view {target} 'Action Plan' --raw", state
assert state['policyBlockers'] == [], state
assert state['phaseSummary']['activePhase'] == 'Action Plan', state
assert 'excerptAnchors' not in state, state
PY

"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order "tw pe" --caller-role mod >/dev/null
state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe --resume)"
STATE="$state" python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
state = json.loads(os.environ['STATE'])
assert state['readyToWrite'] is False, state
assert state['expectedRole'] == 'tw', state
assert state['nextCommand'] == f'(collab speak {target})', state
assert state['policyBlockers'] == [{'code': 'expected-role', 'expectedRole': 'tw'}], state
PY

"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Discussion --force --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order "mod pe" --caller-role mod >/dev/null
state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe --resume)"
STATE="$state" python3 - <<'PY'
import json
import os

state = json.loads(os.environ['STATE'])
assert state['expectedRole'] == 'mod', state
assert 'nextCommand' not in state, state
assert state['policyBlockers'] == [{'code': 'expected-role', 'expectedRole': 'mod'}], state
assert state['phaseSummary']['activePhase'] == 'Discussion', state
PY

python3 - "$REGISTRY" "$TARGET" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['reviewerRole'] = 'pa'
entry['reviewerMode'] = 'last-in-convergent-phases'
entry['reviewerOptionalPhases'] = ['Discussion']
entry['activePhase'] = 'Completion'
entry['turnOrder'] = ['pe', 'tw']
entry['completion'] = {'subState': 'verification'}
entry['execution'] = {
    'pe': {'status': 'completed', 'date': '2026-06-04 12:00 +00:00'},
    'tw': {'status': 'completed', 'date': '2026-06-04 12:01 +00:00'},
}
scope_signature = hashlib.sha256(b'[]').hexdigest()
entry['verification'] = {
    'rounds': 1,
    'cap': 3,
    'subState': 'seal',
    'participantVerification': True,
    'participants': {
        'pe': {'stage': 'completed', 'attempts': 1, 'writeScopeSignature': scope_signature},
        'tw': {'stage': 'completed', 'attempts': 1, 'writeScopeSignature': scope_signature},
    },
}
registry.write_text(json.dumps(data, indent=2) + '\n')
PY

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pa --resume)"
STATE="$state" python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
state = json.loads(os.environ['STATE'])
assert state['nextCommand'], state
assert state['nextCommand'].startswith('(collab seal verification '), state
assert target in state['nextCommand'], state
assert state['nextTranscriptCommand'] == f'commands/collab/engine/registry.py transcript-view {target} Completion --raw', state
assert state['phaseSummary']['activePhase'] == 'Completion', state
assert state['verificationReviewSubState'] == 'seal', state
PY

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['verification']['subState'] = 'assessment'
registry.write_text(json.dumps(data, indent=2) + '\n')
PY

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pa --resume)"
STATE="$state" python3 - <<'PY'
import json
import os

state = json.loads(os.environ['STATE'])
assert state['nextTranscriptCommand'].endswith(' Completion --raw'), state
assert state['verificationReviewSubState'] == 'assessment', state
assert state['phaseSummary']['activePhase'] == 'Completion', state
assert 'nextCommand' not in state, state
PY

printf 'OK: participation resume output exposes copyable commands and blockers\n'
