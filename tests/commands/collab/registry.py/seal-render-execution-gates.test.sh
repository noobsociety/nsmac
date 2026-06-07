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

seed_round() {
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
        'commits': list(state.get('commits', [])),
    }
    if state.get('contentDigest'):
        row['contentDigest'] = state.get('contentDigest')
    if isinstance(state.get('pathDigests'), dict):
        row['pathDigests'] = state.get('pathDigests')
    if state.get('agentId'):
        row['agentId'] = state.get('agentId')
    entries.append(row)
signature = base64.urlsafe_b64encode(
    json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
).decode().rstrip('=')
entry.setdefault('verification', {})['rounds'] = 1
entry['verification']['subState'] = 'seal'
entry['verification']['pairedExecutionSignature'] = signature
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

init_target() {
  local title="$1"
  local slug="$2"
  "$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa --no-participant-verification "$title" >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$RUN_DATE-$slug" pa --agent-id opus >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$RUN_DATE-$slug" active-phase Completion --force --caller-role mod >/dev/null
}

FIXTURE_PATHS=(
  "tests/platform/tooling/audit-reachability.test.sh"
  "platform/tooling/audit-reachability.sh"
  "platform/tooling/audit.sh"
)

fixture_commit() {
  local index="$TMPDIR/fixture.index"
  local mode blob tree path
  rm -f "$index"
  GIT_INDEX_FILE="$index" git -C "$ROOT" read-tree --empty
  for path in "${FIXTURE_PATHS[@]}"; do
    mode="$(git -C "$ROOT" ls-files -s -- "$path" | awk '{print $1}')"
    blob="$(git -C "$ROOT" hash-object -w -- "$ROOT/$path")"
    GIT_INDEX_FILE="$index" git -C "$ROOT" update-index --add --cacheinfo "$mode" "$blob" "$path"
  done
  tree="$(GIT_INDEX_FILE="$index" git -C "$ROOT" write-tree)"
  GIT_AUTHOR_NAME="test" \
    GIT_AUTHOR_EMAIL="test@example.invalid" \
    GIT_AUTHOR_DATE="2026-05-23T18:00:00+02:00" \
    GIT_COMMITTER_NAME="test" \
    GIT_COMMITTER_EMAIL="test@example.invalid" \
    GIT_COMMITTER_DATE="2026-05-23T18:00:00+02:00" \
    git -C "$ROOT" commit-tree "$tree" -m "seal-render fixture"
}

HEAD_COMMIT="$(fixture_commit)"

init_target "Seal Render Touched Path Drift" "seal-render-touched-path-drift"
DRIFT_TARGET="$RUN_DATE-seal-render-touched-path-drift"
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
"$ROOT/commands/collab/engine/registry.py" join-participants "$DRIFT_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$DRIFT_TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" execution "$DRIFT_TARGET" pe completed "2026-05-23T17:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --caller-role pe >/dev/null
python3 - "$REGISTRY" "$DRIFT_TARGET" "$HEAD_COMMIT" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
target = sys.argv[2]
head = sys.argv[3]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
execution = entry['execution']['pe']
if execution.get('entryId') == head:
    raise SystemExit('execution entryId must keep production role-timestamp shape')
execution['commits'] = [head]
entry.setdefault('handoff', {}).setdefault('roles', {})['pe'] = {
    'writeScope': ['commands/collab/engine/registry.py'],
    'validationCommands': [['./platform/tooling/audit.sh']],
    'body': ''
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
seed_round "$DRIFT_TARGET"
drift_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$DRIFT_TARGET" pa)"
drift_revision="$(read_json_field registryRevision <<<"$drift_state")"
set +e
drift_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$DRIFT_TARGET" pa --observed-revision "$drift_revision" --caller-role pa 2>&1)"
drift_status=$?
set -e
if [[ "$drift_status" -ne 0 || "$drift_output" != *"ADVISORY-SCOPE: undeclared"* ]]; then
  printf 'FAIL: seal-render did not downgrade touchedPath drift to advisory output\n%s\n' "$drift_output" >&2
  exit 1
fi

python3 - "$REGISTRY" "$DRIFT_TARGET" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry.pop('verificationSeal', None)
entry['execution']['pe']['commits'] = ['0' * 40]
entry.setdefault('verification', {})['subState'] = 'seal'
path.write_text(json.dumps(data, indent=2) + '\n')
PY
seed_round "$DRIFT_TARGET"
bogus_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$DRIFT_TARGET" pa)"
bogus_revision="$(read_json_field registryRevision <<<"$bogus_state")"
set +e
bogus_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$DRIFT_TARGET" pa --observed-revision "$bogus_revision" --caller-role pa 2>&1)"
bogus_status=$?
set -e
if [[ "$bogus_status" -ne 0 ]]; then
  printf 'FAIL: seal-render treated commits as a validation gate\n%s\n' "$bogus_output" >&2
  exit 1
fi

init_target "Seal Render Agent Conflation" "seal-render-agent-conflation"
CONFLATION_TARGET="$RUN_DATE-seal-render-agent-conflation"
"$ROOT/commands/collab/engine/registry.py" join-participants "$CONFLATION_TARGET" tw --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$CONFLATION_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$CONFLATION_TARGET" turn-order "tw pe" --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" execution "$CONFLATION_TARGET" tw completed "2026-05-23T17:10:00+02:00" \
  --assigned-role tw \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id codex \
  --caller-role tw >/dev/null
"$ROOT/commands/collab/engine/registry.py" execution "$CONFLATION_TARGET" pe completed "2026-05-23T17:11:00+02:00" \
  --assigned-role tw \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id codex \
  --caller-role pe >/dev/null
python3 - "$REGISTRY" "$CONFLATION_TARGET" "$HEAD_COMMIT" "$ROOT" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

path = Path(sys.argv[1])
target = sys.argv[2]
head = sys.argv[3]
root = sys.argv[4]
head_paths = [
    line.strip()
    for line in subprocess.check_output(
        ['git', '-C', root, 'show', '--name-only', '--format=', head],
        text=True,
    ).splitlines()
    if line.strip()
]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
for role in ('tw', 'pe'):
    entry['execution'][role]['commits'] = [head]
    entry['execution'][role]['touchedPaths'] = head_paths
path.write_text(json.dumps(data, indent=2) + '\n')
PY
seed_round "$CONFLATION_TARGET"
conflation_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$CONFLATION_TARGET" pa)"
conflation_revision="$(read_json_field registryRevision <<<"$conflation_state")"
set +e
conflation_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$CONFLATION_TARGET" pa --observed-revision "$conflation_revision" --caller-role pa 2>&1)"
conflation_status=$?
set -e
if [[ "$conflation_status" -eq 0 || "$conflation_output" != *"PARTICIPANT-VERIFY-AGENT-CONFLATION:"* ]]; then
  printf 'FAIL: seal-render accepted shared execution agentId\n%s\n' "$conflation_output" >&2
  exit 1
fi

init_target "Seal Render Combined Commit" "seal-render-combined-commit"
COMBINED_TARGET="$RUN_DATE-seal-render-combined-commit"
"$ROOT/commands/collab/engine/registry.py" join-participants "$COMBINED_TARGET" tw --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$COMBINED_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$COMBINED_TARGET" turn-order "tw pe" --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" execution "$COMBINED_TARGET" tw completed "2026-05-23T18:00:00+02:00" \
  --assigned-role tw \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id codex \
  --caller-role tw >/dev/null
"$ROOT/commands/collab/engine/registry.py" execution "$COMBINED_TARGET" pe completed "2026-05-23T18:01:00+02:00" \
  --assigned-role tw \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id gpt \
  --caller-role pe >/dev/null
python3 - "$REGISTRY" "$COMBINED_TARGET" "$HEAD_COMMIT" "$ROOT" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

path = Path(sys.argv[1])
target = sys.argv[2]
head = sys.argv[3]
root = sys.argv[4]
head_paths = [
    line.strip()
    for line in subprocess.check_output(
        ['git', '-C', root, 'show', '--name-only', '--format=', head],
        text=True,
    ).splitlines()
    if line.strip()
]
# Split the single commit's files into disjoint per-role subsets whose UNION is
# the full commit: the legitimate combined-commit shape the gate must accept.
split = len(head_paths) // 2
role_paths = {'tw': head_paths[:split], 'pe': head_paths[split:]}
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
handoff_roles = entry.setdefault('handoff', {}).setdefault('roles', {})
for role in ('tw', 'pe'):
    entry['execution'][role]['commits'] = [head]
    entry['execution'][role]['touchedPaths'] = role_paths[role]
    handoff_roles[role] = {
        'writeScope': head_paths,
        'validationCommands': [['./platform/tooling/audit.sh']],
        'body': '',
    }
path.write_text(json.dumps(data, indent=2) + '\n')
PY
seed_round "$COMBINED_TARGET"
combined_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$COMBINED_TARGET" pa)"
combined_revision="$(read_json_field registryRevision <<<"$combined_state")"
set +e
combined_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$COMBINED_TARGET" pa --observed-revision "$combined_revision" --caller-role pa 2>&1)"
combined_status=$?
set -e
if [[ "$combined_status" -ne 0 ]]; then
  printf 'FAIL: seal-render rejected a legitimate combined commit (union of role scopes == commit)\n%s\n' "$combined_output" >&2
  exit 1
fi

printf 'OK: seal-render ungates commits, keeps scope advisory non-blocking, rejects agent conflation\n'
