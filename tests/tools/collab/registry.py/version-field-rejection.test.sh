#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-version-field-rejection"
FIELD="$(python3 - <<'PY'
print('schema' + 'Version')
PY
)"

expect_failure() {
  local label="$1"
  local expected="$2"
  shift 2
  set +e
  local output
  output="$("$@" 2>&1)"
  local status=$?
  set -e
  if [[ "$status" -eq 0 ]]; then
    printf 'FAIL: %s accepted a disallowed version field\n' "$label" >&2
    exit 1
  fi
  if [[ "$output" != *"$expected"* ]]; then
    printf 'FAIL: %s message mismatch\n%s\n' "$label" "$output" >&2
    exit 1
  fi
  if [[ "$output" == *"must be 1"* || "$output" == *"Schema revision"* ]]; then
    printf 'FAIL: %s used schema-contract wording\n%s\n' "$label" "$output" >&2
    exit 1
  fi
}

"$ROOT/tools/collab/registry.py" init --agent-id codex "Version Field Rejection" >/dev/null
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pe --agent-id gpt >/dev/null
REGISTRY="$("$ROOT/tools/collab/registry.py" registry-path)"

python3 - "$REGISTRY" "$FIELD" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]
data = json.loads(path.read_text())
data[field] = 1
path.write_text(json.dumps(data, indent=2) + '\n')
PY
expect_failure "registry root" "root contains disallowed version field" "$ROOT/tools/collab/registry.py" validate
python3 - "$REGISTRY" "$FIELD" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]
data = json.loads(path.read_text())
data.pop(field, None)
path.write_text(json.dumps(data, indent=2) + '\n')
PY

python3 - "$REGISTRY" "$FIELD" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'version-field-rejection')
entry['handoff'] = {field: 1, 'roles': {}}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
expect_failure "handoff root" "handoff contains disallowed version field" "$ROOT/tools/collab/registry.py" validate

python3 - "$REGISTRY" "$FIELD" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'version-field-rejection')
entry['handoff'] = {
    'roles': {
        'pe': {
            field: 1,
            'writeScope': ['tools/collab/registry.py'],
            'validationCommands': [['./tools/command-system/audit.sh']],
        }
    }
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
expect_failure "handoff role" "handoff state contains disallowed version field" "$ROOT/tools/collab/registry.py" validate

python3 - "$REGISTRY" "$FIELD" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'version-field-rejection')
entry.pop('handoff', None)
entry['verificationSeal'] = {
    field: 1,
    'observedRevision': 1,
    'executionEntries': [],
    'validationScopes': [],
    'touchedPaths': [],
    'sealedAt': '2026-05-19T00:00:00+02:00',
    'sealedBy': 'pa',
    'executionSignature': 'empty',
    'fullBodySignature': 'empty',
    'stale': False,
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
expect_failure "verification seal" "verificationSeal contains disallowed version field" "$ROOT/tools/collab/registry.py" validate

python3 - "$FIELD" <<'PY'
import json
import sys
from pathlib import Path

field = sys.argv[1]
path = Path('.collab.json')
identity = json.loads(path.read_text())
identity[field] = 1
path.write_text(json.dumps(identity, indent=2) + '\n')
PY
expect_failure "project identity" "project identity contains disallowed version field" "$ROOT/tools/collab/registry.py" registry-path

printf 'OK: active collab state rejects disallowed version fields\n'
