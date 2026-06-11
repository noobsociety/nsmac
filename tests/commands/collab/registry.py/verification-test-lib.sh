#!/usr/bin/env bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
RUN_DATE="$(date +%Y-%m-%d)"

read_json_field() {
  python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["'"$1"'"])'
}

registry_revision() {
  local registry
  registry="$(registry_path)"
  python3 - "$registry" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text()).get('revision', 0))
PY
}

registry_path() {
  "$ROOT/commands/collab/engine/registry.py" registry-path
}

init_reviewer_target() {
  local title="$1"
  local slug="$2"
  "$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa --no-participant-verification "$title" >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$RUN_DATE-$slug" pe --agent-id gpt >/dev/null
  "$ROOT/commands/collab/engine/registry.py" join-participants "$RUN_DATE-$slug" pa --agent-id opus >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$RUN_DATE-$slug" turn-order pe --caller-role mod >/dev/null
}

# Hermetic work repo for the git-state/seal gates. Without a declared workRepo,
# work_repo_root() falls back to the framework checkout (ROOT), so the
# seal-git-state gate reads the ambient worktree and fails whenever a fixture
# touched-path is uncommitted there. A clean HEAD clone of the framework repo is
# behaviorally identical to ROOT for provenance/history but has a clean worktree,
# so every committed path a consumer records (audit.sh or its own file) is clean.
LIB_WORK_REPO=""
ensure_lib_work_repo() {
  if [[ -n "$LIB_WORK_REPO" ]]; then return 0; fi
  : "${TMPDIR:?TMPDIR must be set before complete_execution}"
  LIB_WORK_REPO="$TMPDIR/verification-lib-work-repo"
  git clone --quiet --local "$ROOT" "$LIB_WORK_REPO"
}

# Bind a collab to the hermetic clone work repo so its seal git-state gate checks
# the clean HEAD checkout, not the ambient (possibly dirty) framework tree. Call
# after creating a collab whose execution touched-paths are real repo paths
# recorded directly (i.e. not through complete_execution, which binds on its own).
bind_lib_work_repo() {
  ensure_lib_work_repo
  "$ROOT/commands/collab/engine/registry.py" set "$1" work-repo "$LIB_WORK_REPO" >/dev/null
}

complete_execution() {
  local target="$1"
  ensure_lib_work_repo
  "$ROOT/commands/collab/engine/registry.py" set "$target" work-repo "$LIB_WORK_REPO" >/dev/null
  "$ROOT/commands/collab/engine/registry.py" execution "$target" pe completed "2026-05-15T21:00:00+02:00" \
    --assigned-role pe \
    --validation-result passed \
    --validation-scope scoped \
    --touched-path platform/tooling/audit.sh \
    --caller-role pe >/dev/null
}

seed_paired_verification_round() {
  local slug="$1"
  local rounds="${2:-1}"
  local registry
  registry="$(registry_path)"
  python3 - "$slug" "$rounds" "$registry" <<'PY'
import json
import sys
from pathlib import Path

slug, rounds, registry = sys.argv[1:4]
path = Path(registry)
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
    entries.append(row)
import base64
signature = base64.urlsafe_b64encode(
    json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
).decode().rstrip('=')
entry.setdefault('verification', {})['rounds'] = int(rounds)
entry['verification']['pairedExecutionSignature'] = signature
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

seal_target() {
  local target="$1"
  shift || true
  local state
  local revision
  python3 - "$target" "$(registry_path)" <<'PY'
import json
import sys
from pathlib import Path

target, registry = sys.argv[1:3]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry.setdefault('verification', {})['cap'] = 2
path.write_text(json.dumps(data, indent=2) + '\n')
PY
  seed_paired_verification_round "$target"
  state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$target" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  "$ROOT/commands/collab/engine/registry.py" seal-render "$target" pa --observed-revision "$revision" --caller-role pa "$@" >/dev/null
}

start_assessment() {
  local target="$1"
  complete_execution "$target"
  seal_target "$target"
}

assessment_revision() {
  local target="$1"
  local state
  state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$target" pa)"
  read_json_field registryRevision <<<"$state"
}

seed_handoff_scope() {
  local slug="$1"
  local registry
  registry="$(registry_path)"
  python3 - "$slug" "$registry" <<'PY'
import json
import sys
from pathlib import Path

slug = sys.argv[1]
path = Path(sys.argv[2])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == slug)
entry['handoff'] = {
    'roles': {
        'pe': {
            'writeScope': ['platform/tooling/audit.sh'],
            'validationCommands': [['./platform/tooling/audit.sh']],
        }
    }
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

assert_seal_stale() {
  local slug="$1"
  local reason="$2"
  local registry
  registry="$(registry_path)"
  python3 - "$slug" "$reason" "$registry" <<'PY'
import json
import sys
from pathlib import Path

slug, reason, registry = sys.argv[1:4]
entry = next(item for item in json.loads(Path(registry).read_text())['collabs'] if item['slug'] == slug)
seal = entry['verificationSeal']
assert seal['stale'] is True, seal
assert seal['staleReason'] == reason, seal
PY
}
