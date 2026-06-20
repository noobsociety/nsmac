#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

python3 - "$ROOT" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1])))
from commands.collab.engine import registry_state

assert registry_state.STATE_ROOT_PROOF_COMMAND == './tests/commands/collab/registry.py/state-root-resolution.test.sh'
assert callable(registry_state.resolve_default_registry_path)
assert callable(registry_state.assert_registry_project_binding)
PY

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Home State Init" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
LIST_OUTPUT="$("$ROOT/commands/collab/engine/registry.py" list)"
LOCK_PATH="${REGISTRY}.lock"

python3 - "$REGISTRY" "$COLLAB_STATE_HOME" "$RUN_DATE-home-state-init" "$LIST_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
state_home = Path(sys.argv[2]).resolve()
target = sys.argv[3]
list_output = sys.argv[4]
identity = json.loads(Path('.collab.json').read_text())
assert 'schema' + 'Version' not in identity
assert identity['projectId']
assert identity['label'] == Path.cwd().name
assert registry == state_home / identity['projectId'] / 'registry.json'
assert registry.exists()
assert not Path('.collabs').exists()
data = json.loads(registry.read_text())
assert data['project'] == {'projectId': identity['projectId'], 'label': identity['label']}
assert f"Project: {identity['label']} · {identity['projectId']}" in list_output
entry = data['collabs'][0]
assert entry['id'] == target
assert entry['transcriptPath'] == f'records/{target}.md'
projection = registry.parent / entry['transcriptPath']
store = registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-contributions.json")
assert projection.exists()
assert store.exists()
PY

python3 - <<'PY'
import json
from pathlib import Path

path = Path('.collab.json')
identity = json.loads(path.read_text())
identity['label'] = 'renamed-system'
path.write_text(json.dumps(identity, indent=2) + '\n')
PY
UPDATED_LIST_OUTPUT="$("$ROOT/commands/collab/engine/registry.py" list)"
python3 - "$REGISTRY" "$UPDATED_LIST_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
list_output = sys.argv[2]
identity = json.loads(Path('.collab.json').read_text())
assert (registry.parent / 'label').read_text() == identity['label'] + '\n'
assert f"Project: {identity['label']} · {identity['projectId']}" in list_output
PY

if [[ ! -e "$LOCK_PATH" ]]; then
  printf 'FAIL: expected persistent registry lock file: %s\n' "$LOCK_PATH" >&2
  exit 1
fi

touch -t 200001010000 "$LOCK_PATH"
"$ROOT/commands/collab/engine/registry.py" validate >/dev/null
python3 - "$LOCK_PATH" <<'PY'
import sys
from pathlib import Path

lock_path = Path(sys.argv[1])
assert lock_path.exists()
assert lock_path.stat().st_mtime > 946684800
PY

READY="$TMPDIR/lock-ready"
python3 - "$LOCK_PATH" "$READY" <<'PY' &
import fcntl
import os
import sys
import time
from pathlib import Path

lock_path = Path(sys.argv[1])
ready = Path(sys.argv[2])
with lock_path.open('a+') as lock_file:
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    os.utime(lock_path, (946684800, 946684800))
    ready.write_text('ready')
    time.sleep(10)
PY
LOCKER_PID=$!
for _ in {1..100}; do
  [[ -e "$READY" ]] && break
  sleep 0.05
done
if [[ ! -e "$READY" ]]; then
  kill "$LOCKER_PID" 2>/dev/null || true
  wait "$LOCKER_PID" 2>/dev/null || true
  printf 'FAIL: timed out waiting for test lock holder\n' >&2
  exit 1
fi

set +e
LOCK_OUTPUT="$("$ROOT/commands/collab/engine/registry.py" validate 2>&1)"
LOCK_STATUS=$?
set -e
kill "$LOCKER_PID" 2>/dev/null || true
wait "$LOCKER_PID" 2>/dev/null || true

if [[ "$LOCK_STATUS" -eq 0 ]]; then
  printf 'FAIL: validate accepted an aged held registry lock\n' >&2
  exit 1
fi

if [[ "$LOCK_OUTPUT" != *"stale registry lock:"* ]]; then
  printf 'FAIL: stale registry lock message mismatch\n%s\n' "$LOCK_OUTPUT" >&2
  exit 1
fi

printf 'OK: collab registry resolves through .collab.json, user-scope state root, and persistent lock validation\n'
