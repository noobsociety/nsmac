#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"

RUN_DATE="$(date +%Y-%m-%d)"

read_json_field() {
  python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["'"$1"'"])'
}

init_target() {
  local title="$1"
  local slug="$2"
  "$ROOT/tools/collab/registry.py" init --agent-id codex --reviewer pa "$title" >/dev/null
  "$ROOT/tools/collab/registry.py" join-participants "$RUN_DATE-$slug" pe --agent-id gpt >/dev/null
  "$ROOT/tools/collab/registry.py" join-participants "$RUN_DATE-$slug" pa --agent-id opus >/dev/null
  "$ROOT/tools/collab/registry.py" set "$RUN_DATE-$slug" turn-order pe --caller-role mod >/dev/null
  "$ROOT/tools/collab/registry.py" set "$RUN_DATE-$slug" active-phase Completion --force --caller-role mod >/dev/null
}

init_target "Verification Seal Flow" "verification-seal-flow"
TARGET="$RUN_DATE-verification-seal-flow"

"$ROOT/tools/collab/registry.py" execution "$TARGET" pe completed "2026-05-15T21:00:00+02:00" \
  --assigned-role pe \
  --auto-close \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path tools/collab/registry.py \
  --caller-role pe >/dev/null

python3 - <<'PY'
import json
from pathlib import Path
entry = json.loads(Path('.collabs/registry.json').read_text())['collabs'][0]
assert entry['status'] == 'open'
assert entry['completion']['subState'] == 'verification'
assert entry['verification']['rounds'] == 0
assert 'verificationSeal' not in entry
PY

set +e
close_output="$("$ROOT/tools/collab/registry.py" close "$TARGET" --caller-role mod 2>&1)"
close_status=$?
set -e
if [[ "$close_status" -eq 0 || "$close_output" != *"close blocked: reviewer-backed Completion requires verificationSeal"* ]]; then
  printf 'FAIL: close did not require a verification seal\n%s\n' "$close_output" >&2
  exit 1
fi

state="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa)"
rounds="$(read_json_field verificationRounds <<<"$state")"
revision="$(read_json_field registryRevision <<<"$state")"
if [[ "$rounds" != "1" ]]; then
  printf 'FAIL: seal-state did not record the paired verification round\n%s\n' "$state" >&2
  exit 1
fi

set +e
wrong_role_output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pe --observed-revision "$revision" --caller-role pe 2>&1)"
wrong_role_status=$?
set -e
if [[ "$wrong_role_status" -eq 0 || "$wrong_role_output" != *"seal must be authored by the reviewer role; current role: pe; expected: pa"* ]]; then
  printf 'FAIL: seal-render accepted a non-reviewer\n%s\n' "$wrong_role_output" >&2
  exit 1
fi

set +e
stale_output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$((revision - 1))" --caller-role pa 2>&1)"
stale_status=$?
set -e
if [[ "$stale_status" -eq 0 || "$stale_output" != *"stale registry revision: observed"* ]]; then
  printf 'FAIL: seal-render accepted stale observed revision\n%s\n' "$stale_output" >&2
  exit 1
fi

"$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
entry = json.loads(Path('.collabs/registry.json').read_text())['collabs'][0]
transcript = Path(entry['transcriptPath']).read_text()
assert entry['status'] == 'closed'
assert entry['verificationSeal']['sealedBy'] == 'pa'
assert entry['verificationSeal']['stale'] is False
assert '**pa:** sealed' in transcript
PY

init_target "Verification Zero Round" "verification-zero-round"
ZERO_TARGET="$RUN_DATE-verification-zero-round"
python3 - <<'PY'
import json
from pathlib import Path
path = Path('.collabs/registry.json')
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-zero-round')
entry['completion'] = {'subState': 'verification'}
entry['verification'] = {'rounds': 0, 'cap': 3}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
zero_revision="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('.collabs/registry.json').read_text()).get('revision', 0))
PY
)"
set +e
zero_output="$("$ROOT/tools/collab/registry.py" seal-render "$ZERO_TARGET" pa --observed-revision "$zero_revision" --caller-role pa 2>&1)"
zero_status=$?
set -e
if [[ "$zero_status" -eq 0 || "$zero_output" != *"zero verification rounds; at least one reviewer-executor paired event is required before sealing"* ]]; then
  printf 'FAIL: seal-render accepted zero verification rounds\n%s\n' "$zero_output" >&2
  exit 1
fi

init_target "Verification Cap Exit" "verification-cap-exit"
CAP_TARGET="$RUN_DATE-verification-cap-exit"
"$ROOT/tools/collab/registry.py" execution "$CAP_TARGET" pe completed "2026-05-15T21:15:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path tools/collab/registry.py \
  --caller-role pe >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
path = Path('.collabs/registry.json')
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-cap-exit')
entry['verification']['cap'] = 1
path.write_text(json.dumps(data, indent=2) + '\n')
PY
cap_state="$("$ROOT/tools/collab/registry.py" seal-state "$CAP_TARGET" pa)"
cap_revision="$(read_json_field registryRevision <<<"$cap_state")"
set +e
cap_output="$("$ROOT/tools/collab/registry.py" seal-render "$CAP_TARGET" pa --observed-revision "$cap_revision" --caller-role pa 2>&1)"
cap_status=$?
set -e
if [[ "$cap_status" -eq 0 || "$cap_output" != *"round cap reached; reissue with --cap-exit reopen-action-plan, --cap-exit reopen-handoff, or --cap-exit archive"* ]]; then
  printf 'FAIL: seal-render did not enforce the cap exit\n%s\n' "$cap_output" >&2
  exit 1
fi
"$ROOT/tools/collab/registry.py" seal-render "$CAP_TARGET" pa --observed-revision "$cap_revision" --cap-exit reopen-handoff --caller-role pa >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
entry = next(item for item in json.loads(Path('.collabs/registry.json').read_text())['collabs'] if item['slug'] == 'verification-cap-exit')
assert entry['status'] == 'open'
assert entry['activePhase'] == 'Handoff'
assert entry['verificationSeal']['capExit'] == 'reopen-handoff'
assert entry['completion']['subState'] == 'execution'
PY

printf 'OK: verification seal flow enforces reviewer gating, seal state, cap exits, and close blocking\n'
