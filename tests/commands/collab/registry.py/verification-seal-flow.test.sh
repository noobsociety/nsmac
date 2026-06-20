#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

read_json_field() {
  python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["'"$1"'"])'
}

seed_paired_verification_round() {
  local slug="$1"
  python3 - "$REGISTRY" "$slug" <<'PY'
import base64
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
slug = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == slug or item['id'] == slug)
entries = []
for role, state in sorted(entry.get('execution', {}).items()):
    row = {
        'role': role,
        'entryId': state.get('entryId') or f"{role}-execution",
        'status': state.get('status'),
        'date': state.get('date'),
        'validationResult': state.get('validationResult'),
        'validationScope': state.get('validationScope'),
        'touchedPaths': list(state.get('touchedPaths', [])),
    }
    if state.get('agentId'):
        row['agentId'] = state.get('agentId')
    if state.get('contentDigest'):
        row['contentDigest'] = state.get('contentDigest')
    if state.get('pathDigests'):
        row['pathDigests'] = state.get('pathDigests')
    entries.append(row)
signature = base64.urlsafe_b64encode(
    json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
).decode().rstrip('=')
entry['verification']['rounds'] = 1
entry['verification']['pairedExecutionSignature'] = signature
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

# Hermetic work repo so the seal git-state gate checks a controlled tree, not the
# ambient framework checkout (which fails whenever platform/tooling/audit.sh is dirty).
WORK_REPO="$TMPDIR/work-repo"
mkdir -p "$WORK_REPO/platform/tooling"
printf '#!/usr/bin/env bash\necho audit\n' >"$WORK_REPO/platform/tooling/audit.sh"
git -C "$WORK_REPO" init -q
git -C "$WORK_REPO" -c user.email=test@example.com -c user.name=test add platform/tooling/audit.sh
git -C "$WORK_REPO" -c user.email=test@example.com -c user.name=test -c commit.gpgsign=false \
  commit -q -m 'fixture: audit.sh'

init_target() {
  local title="$1"
  local slug="$2"
  "$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa --no-participant-verification "$title" >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$RUN_DATE-$slug" pe --agent-id gpt >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$RUN_DATE-$slug" pa --agent-id opus >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$RUN_DATE-$slug" turn-order pe --caller-role mod >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$RUN_DATE-$slug" active-phase Completion --force --caller-role mod >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$RUN_DATE-$slug" work-repo "$WORK_REPO" >/dev/null
}

init_target "Verification Seal Flow" "verification-seal-flow"
TARGET="$RUN_DATE-verification-seal-flow"
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"

"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-15T21:00:00+02:00" \
  --assigned-role pe \
  --auto-close \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path platform/tooling/audit.sh \
  --caller-role pe >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = data['collabs'][0]
entry['verification']['cap'] = 2
path.write_text(json.dumps(data, indent=2) + '\n')
assert entry['status'] == 'open'
assert entry['completion']['subState'] == 'verification'
assert entry['verification']['subState'] == 'seal'
assert entry['verification']['rounds'] == 0
assert 'verificationSeal' not in entry
PY

set +e
close_output="$("$ROOT/commands/collab/engine/registry.py" close "$TARGET" --caller-role mod 2>&1)"
close_status=$?
set -e
if [[ "$close_status" -eq 0 || "$close_output" != *"close blocked: reviewer-backed Completion requires verificationSeal"* ]]; then
  printf 'FAIL: close did not require a verification seal\n%s\n' "$close_output" >&2
  exit 1
fi

state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
rounds="$(read_json_field verificationRounds <<<"$state")"
if [[ "$rounds" != "0" ]]; then
  printf 'FAIL: seal-state spent a verification round\n%s\n' "$state" >&2
  exit 1
fi
second_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
rounds="$(read_json_field verificationRounds <<<"$second_state")"
revision="$(read_json_field registryRevision <<<"$second_state")"
if [[ "$rounds" != "0" ]]; then
  printf 'FAIL: repeated seal-state spent a verification round\n%s\n' "$second_state" >&2
  exit 1
fi
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = json.loads(Path(sys.argv[1]).read_text())['collabs'][0]
assert entry['verification']['rounds'] == 0, entry['verification']
assert 'pairedExecutionSignature' not in entry['verification'], entry['verification']
PY

set +e
wrong_role_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pe --observed-revision "$revision" --caller-role pe 2>&1)"
wrong_role_status=$?
set -e
if [[ "$wrong_role_status" -eq 0 || "$wrong_role_output" != *"seal must be authored by the reviewer role; current role: pe; expected: pa"* ]]; then
  printf 'FAIL: seal-render accepted a non-reviewer\n%s\n' "$wrong_role_output" >&2
  exit 1
fi

set +e
stale_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$((revision - 1))" --caller-role pa 2>&1)"
stale_status=$?
set -e
if [[ "$stale_status" -eq 0 || "$stale_output" != *"stale registry revision: observed"* ]]; then
  printf 'FAIL: seal-render accepted stale observed revision\n%s\n' "$stale_output" >&2
  exit 1
fi
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = json.loads(Path(sys.argv[1]).read_text())['collabs'][0]
assert entry['verification']['rounds'] == 0, entry['verification']
assert 'pairedExecutionSignature' not in entry['verification'], entry['verification']
PY

seed_paired_verification_round "$TARGET"
state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
"$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa >/dev/null
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
entry = json.loads(registry.read_text())['collabs'][0]
transcript = (registry.parent / Path(entry['transcriptPath'])).read_text()
assert entry['status'] == 'open'
assert entry['verificationSeal']['sealedBy'] == 'pa'
assert entry['verificationSeal']['stale'] is False
assert entry['verification']['subState'] == 'assessment'
assert entry['verification']['rounds'] == 1
assert entry['verification']['pairedExecutionSignature'] == entry['verificationSeal']['executionSignature']
assert '**pa:** sealed' in transcript
PY

set +e
assessment_close_output="$("$ROOT/commands/collab/engine/registry.py" close "$TARGET" --caller-role mod 2>&1)"
assessment_close_status=$?
set -e
if [[ "$assessment_close_status" -eq 0 || "$assessment_close_output" != *"close blocked: reviewer-backed Completion requires verdict outcome success"* ]]; then
  printf 'FAIL: close did not require a successful assessment verdict\n%s\n' "$assessment_close_output" >&2
  exit 1
fi

assessment_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
assessment_revision="$(read_json_field registryRevision <<<"$assessment_state")"
"$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$assessment_revision" \
  --outcome success \
  --evidence '{"registryRevision":1,"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"],"committedPaths":["platform/tooling/audit.sh"]}' \
  --caller-role pa >/dev/null
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
entry = json.loads(registry.read_text())['collabs'][0]
transcript = (registry.parent / Path(entry['transcriptPath'])).read_text()
assert entry['status'] == 'closed'
assert entry['verdict']['outcome'] == 'success'
assert '**pa:** assessed' in transcript
PY

init_target "Verification Zero Round" "verification-zero-round"
ZERO_TARGET="$RUN_DATE-verification-zero-round"
"$ROOT/commands/collab/engine/registry.py" execution "$ZERO_TARGET" pe completed "2026-05-15T21:10:00+02:00" \
  --assigned-role pe \
  --auto-close \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path platform/tooling/audit.sh \
  --caller-role pe >/dev/null
python3 - "$REGISTRY" <<'PY'
import base64
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-zero-round')
entries = []
for role, state in sorted(entry.get('execution', {}).items()):
    row = {
        'role': role,
        'entryId': state.get('entryId') or f"{role}-execution",
        'status': state.get('status'),
        'date': state.get('date'),
        'validationResult': state.get('validationResult'),
        'validationScope': state.get('validationScope'),
        'touchedPaths': list(state.get('touchedPaths', [])),
    }
    if state.get('agentId'):
        row['agentId'] = state.get('agentId')
    if state.get('contentDigest'):
        row['contentDigest'] = state.get('contentDigest')
    if state.get('pathDigests'):
        row['pathDigests'] = state.get('pathDigests')
    entries.append(row)
signature = base64.urlsafe_b64encode(
    json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
).decode().rstrip('=')
entry['verification']['rounds'] = 0
entry['verification']['cap'] = 1
entry['verification']['subState'] = 'seal'
entry['verification']['pairedExecutionSignature'] = signature
path.write_text(json.dumps(data, indent=2) + '\n')
PY
zero_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$ZERO_TARGET" pa)"
zero_revision="$(read_json_field registryRevision <<<"$zero_state")"
set +e
zero_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$ZERO_TARGET" pa --observed-revision "$zero_revision" --caller-role pa 2>&1)"
zero_status=$?
set -e
if [[ "$zero_status" -eq 0 || "$zero_output" != *"zero verification rounds; at least one reviewer-executor paired event is required before sealing"* ]]; then
  printf 'FAIL: seal-render accepted zero verification rounds\n%s\n' "$zero_output" >&2
  exit 1
fi

init_target "Verification Cap Exit" "verification-cap-exit"
CAP_TARGET="$RUN_DATE-verification-cap-exit"
"$ROOT/commands/collab/engine/registry.py" execution "$CAP_TARGET" pe completed "2026-05-15T21:15:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path platform/tooling/audit.sh \
  --caller-role pe >/dev/null
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-cap-exit')
entry['verification']['cap'] = 1
path.write_text(json.dumps(data, indent=2) + '\n')
PY
seed_paired_verification_round "$CAP_TARGET"
cap_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$CAP_TARGET" pa)"
cap_revision="$(read_json_field registryRevision <<<"$cap_state")"
cap_rounds="$(read_json_field verificationRounds <<<"$cap_state")"
if [[ "$cap_rounds" != "1" ]]; then
  printf 'FAIL: cap-exit seal-state spent a verification round\n%s\n' "$cap_state" >&2
  exit 1
fi
set +e
cap_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$CAP_TARGET" pa --observed-revision "$cap_revision" --caller-role pa 2>&1)"
cap_status=$?
set -e
if [[ "$cap_status" -eq 0 || "$cap_output" != *"round cap reached; reissue with --cap-exit reopen-action-plan, --cap-exit reopen-handoff, --cap-exit follow-up-collab, or --cap-exit archive"* ]]; then
  printf 'FAIL: seal-render did not enforce the cap exit\n%s\n' "$cap_output" >&2
  exit 1
fi
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(item for item in json.loads(Path(sys.argv[1]).read_text())['collabs'] if item['slug'] == 'verification-cap-exit')
assert entry['verification']['rounds'] == 1, entry['verification']
assert 'pairedExecutionSignature' in entry['verification'], entry['verification']
PY
"$ROOT/commands/collab/engine/registry.py" seal-render "$CAP_TARGET" pa --observed-revision "$cap_revision" --cap-exit reopen-handoff --caller-role pa >/dev/null
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
entry = next(item for item in json.loads(Path(sys.argv[1]).read_text())['collabs'] if item['slug'] == 'verification-cap-exit')
assert entry['status'] == 'open'
assert entry['activePhase'] == 'Handoff'
assert entry['verificationSeal']['capExit'] == 'reopen-handoff'
assert entry['completion']['subState'] == 'execution'
assert entry['verification']['subState'] == 'assessment'
PY

init_target "Verification Render Retry" "verification-render-retry"
RETRY_TARGET="$RUN_DATE-verification-render-retry"
"$ROOT/commands/collab/engine/registry.py" execution "$RETRY_TARGET" pe completed "2026-05-15T21:30:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path platform/tooling/audit.sh \
  --caller-role pe >/dev/null
retry_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$RETRY_TARGET" pa)"
python3 - "$REGISTRY" <<'PY'
import base64
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-render-retry')
entries = []
for role, state in sorted(entry.get('execution', {}).items()):
    row = {
        'role': role,
        'entryId': state.get('entryId') or f"{role}-execution",
        'status': state.get('status'),
        'date': state.get('date'),
        'validationResult': state.get('validationResult'),
        'validationScope': state.get('validationScope'),
        'touchedPaths': list(state.get('touchedPaths', [])),
    }
    if state.get('agentId'):
        row['agentId'] = state.get('agentId')
    if state.get('contentDigest'):
        row['contentDigest'] = state.get('contentDigest')
    if state.get('pathDigests'):
        row['pathDigests'] = state.get('pathDigests')
    entries.append(row)
signature = base64.urlsafe_b64encode(
    json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
).decode().rstrip('=')
entry['verification']['rounds'] = 1
entry['verification']['pairedExecutionSignature'] = signature
path.write_text(json.dumps(data, indent=2) + '\n')
PY
retry_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$RETRY_TARGET" pa)"
retry_revision="$(read_json_field registryRevision <<<"$retry_state")"
"$ROOT/commands/collab/engine/registry.py" seal-render "$RETRY_TARGET" pa --observed-revision "$retry_revision" --caller-role pa >/dev/null
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(item for item in json.loads(Path(sys.argv[1]).read_text())['collabs'] if item['slug'] == 'verification-render-retry')
assert entry['verification']['rounds'] == 1, entry['verification']
assert entry['verification']['pairedExecutionSignature'] == entry['verificationSeal']['executionSignature']
PY

printf 'OK: verification seal flow enforces reviewer gating, seal state, assessment verdicts, cap exits, and close blocking\n'
