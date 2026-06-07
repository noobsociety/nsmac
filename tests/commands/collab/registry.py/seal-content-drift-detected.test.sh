#!/usr/bin/env bash
set -euo pipefail

# Post-seal content changes are detected by invalidate_seal_on_content_drift:
# if any declared touchedPath is re-committed with different bytes after sealing,
# the verificationSeal is marked stale with staleReason "content-drift", and a
# subsequent success verdict is rejected with SEAL-CONTENT-DRIFT.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
printf '{"projectId":"test-seal-content-drift-fixture","label":"test"}\n' > .collab.json

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
target = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
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

WORK="$TMPDIR/work"
mkdir -p "$WORK"
git -C "$WORK" init >/dev/null
git -C "$WORK" config user.name test
git -C "$WORK" config user.email test@example.invalid
printf 'original\n' > "$WORK/deliverable.txt"
git -C "$WORK" add deliverable.txt
GIT_AUTHOR_DATE="2026-05-23T17:00:00+02:00" \
GIT_COMMITTER_DATE="2026-05-23T17:00:00+02:00" \
  git -C "$WORK" commit -m "deliverable" >/dev/null

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa \
  --no-participant-verification --work-repo "$WORK" "Seal Content Drift Detected" >/dev/null
TARGET="$RUN_DATE-seal-content-drift-detected"
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-23T18:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id codex \
  --touched-path deliverable.txt \
  --caller-role pe >/dev/null

seed_round "$TARGET"
seal_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
seal_revision="$(read_json_field registryRevision <<<"$seal_state")"
"$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$seal_revision" --caller-role pa >/dev/null

# Tamper: edit + commit the touched path after sealing
printf 'tampered\n' > "$WORK/deliverable.txt"
git -C "$WORK" add deliverable.txt
GIT_AUTHOR_DATE="2026-05-23T19:00:00+02:00" \
GIT_COMMITTER_DATE="2026-05-23T19:00:00+02:00" \
  git -C "$WORK" commit -m "post-seal edit" >/dev/null

# Success verdict must fail with SEAL-CONTENT-DRIFT
verdict_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
verdict_revision="$(read_json_field registryRevision <<<"$verdict_state")"
set +e
verdict_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$verdict_revision" --caller-role pa --outcome success 2>&1)"
verdict_status=$?
set -e

if [[ "$verdict_status" -eq 0 || "$verdict_output" != *"SEAL-CONTENT-DRIFT"* ]]; then
  printf 'FAIL: success verdict after content change did not emit SEAL-CONTENT-DRIFT\n%s\n' \
    "$verdict_output" >&2
  exit 1
fi

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
entry = next(item for item in data['collabs'] if item['id'] == sys.argv[2])
seal = entry.get('verificationSeal', {})
if seal.get('stale') is not True or seal.get('staleReason') != 'content-drift':
    raise SystemExit(f"content drift did not persist stale seal state: {seal!r}")
PY

printf 'OK: post-seal content change causes success verdict to fail with SEAL-CONTENT-DRIFT\n'
