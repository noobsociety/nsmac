#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export CURSOR_COLLAB_STATE_HOME="$TMPDIR/state-home"

"$ROOT/tools/collab/registry.py" init --agent-id codex --reviewer pa "Verification Participant Seal Gate" >/dev/null
TARGET="$RUN_DATE-verification-participant-seal-gate"
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pe --agent-id gpt >/dev/null
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
seed_handoff_scope "verification-participant-seal-gate"
complete_execution "$TARGET"

REGISTRY="$(registry_path)"
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-participant-seal-gate')
entry['completion'] = {'subState': 'verification'}
entry['verification'] = {
    'rounds': 1,
    'cap': 1,
    'subState': 'seal',
    'participantVerification': True,
    'participants': {
        'pe': {
            'stage': 'audit',
            'attempts': 0,
            'writeScopeSignature': entry['verification']['participants']['pe']['writeScopeSignature'],
        }
    },
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY

participant_speak_state="$("$ROOT/tools/collab/registry.py" speak-state "$TARGET" pe)"
if [[ "$participant_speak_state" != *'"verificationReviewSubState": "participant"'* || "$participant_speak_state" != *'"expectedRole": "pe"'* || "$participant_speak_state" != *'"readyToWrite": true'* ]]; then
  printf 'FAIL: speak-state did not route drifted incomplete participant verification to the participant\n%s\n' "$participant_speak_state" >&2
  exit 1
fi

state="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa)"
if [[ "$state" != *'"verificationReviewSubState": "participant"'* ]]; then
  printf 'FAIL: seal-state did not repair drifted participant sub-state\n%s\n' "$state" >&2
  exit 1
fi
revision="$(read_json_field registryRevision <<<"$state")"

set +e
output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa 2>&1)"
status=$?
set -e
if [[ "$status" -eq 0 || "$output" != *"participant verification is active; next role: pe"* ]]; then
  printf 'FAIL: seal-render accepted drifted incomplete participant verification\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: participant verification blocks seal even when verification.subState drifted to seal\n'
