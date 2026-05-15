#!/usr/bin/env bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
RUN_DATE="$(date +%Y-%m-%d)"

read_json_field() {
  python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["'"$1"'"])'
}

registry_revision() {
  python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('.collabs/registry.json').read_text()).get('revision', 0))
PY
}

init_reviewer_target() {
  local title="$1"
  local slug="$2"
  "$ROOT/tools/collab/registry.py" init --agent-id codex --reviewer pa "$title" >/dev/null
  "$ROOT/tools/collab/registry.py" join-participants "$RUN_DATE-$slug" pe --agent-id gpt >/dev/null
  "$ROOT/tools/collab/registry.py" join-participants "$RUN_DATE-$slug" pa --agent-id opus >/dev/null
  "$ROOT/tools/collab/registry.py" set "$RUN_DATE-$slug" turn-order pe --caller-role mod >/dev/null
}

complete_execution() {
  local target="$1"
  "$ROOT/tools/collab/registry.py" execution "$target" pe completed "2026-05-15T21:00:00+02:00" \
    --assigned-role pe \
    --validation-result passed \
    --validation-scope scoped \
    --touched-path tools/collab/registry.py \
    --caller-role pe >/dev/null
}

seal_target() {
  local target="$1"
  shift || true
  local state
  local revision
  state="$("$ROOT/tools/collab/registry.py" seal-state "$target" pa)"
  revision="$(read_json_field registryRevision <<<"$state")"
  "$ROOT/tools/collab/registry.py" seal-render "$target" pa --observed-revision "$revision" --caller-role pa "$@" >/dev/null
}

seed_handoff_scope() {
  local slug="$1"
  python3 - "$slug" <<'PY'
import json
import sys
from pathlib import Path

slug = sys.argv[1]
path = Path('.collabs/registry.json')
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == slug)
entry['handoff'] = {
    'schemaVersion': 1,
    'roles': {
        'pe': {
            'schemaVersion': 1,
            'writeScope': ['tools/collab/registry.py'],
            'validationCommands': [['./tools/cursor/audit.sh']],
        }
    }
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

assert_seal_stale() {
  local slug="$1"
  local reason="$2"
  python3 - "$slug" "$reason" <<'PY'
import json
import sys
from pathlib import Path

slug, reason = sys.argv[1:3]
entry = next(item for item in json.loads(Path('.collabs/registry.json').read_text())['collabs'] if item['slug'] == slug)
seal = entry['verificationSeal']
assert seal['stale'] is True, seal
assert seal['staleReason'] == reason, seal
PY
}
