#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-registry-schema-roundtrip"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Registry Schema Roundtrip" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'registry-schema-roundtrip')
data['unknownTopLevel'] = {'preserve': True}
entry['unknownCollabField'] = ['preserve']
entry['verification'] = {
    'rounds': 0,
    'subState': 'seal',
    'participants': {},
    'unknownNestedLifecycle': {'preserve': True},
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY

"$ROOT/commands/collab/engine/registry.py" set "$TARGET" description "Roundtrip mutation" --caller-role mod >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'registry-schema-roundtrip')
assert data['unknownTopLevel'] == {'preserve': True}, data
assert entry['unknownCollabField'] == ['preserve'], entry
assert entry['verification']['unknownNestedLifecycle'] == {'preserve': True}, entry['verification']
PY

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data['revision'] = -1
path.write_text(json.dumps(data, indent=2) + '\n')
PY

set +e
output="$("$ROOT/commands/collab/engine/registry.py" validate 2>&1)"
status=$?
set -e
if [[ "$status" -eq 0 || "$output" != *"revision must be a non-negative integer"* ]]; then
  printf 'FAIL: malformed revision was not rejected\n%s\n' "$output" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data['revision'] = 1
data['eventIndex'] = 'bad'
path.write_text(json.dumps(data, indent=2) + '\n')
PY

set +e
output="$("$ROOT/commands/collab/engine/registry.py" validate 2>&1)"
status=$?
set -e
if [[ "$status" -eq 0 || "$output" != *"eventIndex must be a non-negative integer"* ]]; then
  printf 'FAIL: malformed eventIndex was not rejected\n%s\n' "$output" >&2
  exit 1
fi

python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))

from commands.collab.engine import registry as r

schema = json.loads((root / 'registry.schema.json').read_text())
parity = schema['x-dc-validatorParity']
assert parity['schemaRole'].startswith('reference/projection only'), parity
assert parity['createdAtRequiredCollabFields'] == r.CREATED_AT_REQUIRED_COLLAB_FIELDS, parity
assert parity['createdAtRequiredReviewerFields'] == r.CREATED_AT_REQUIRED_REVIEWER_FIELDS, parity
assert parity['createdAtRequiredVerificationFields'] == r.CREATED_AT_REQUIRED_VERIFICATION_FIELDS, parity
PY

printf 'OK: registry schema contract rejects known malformed fields and preserves unknown fields\n'
