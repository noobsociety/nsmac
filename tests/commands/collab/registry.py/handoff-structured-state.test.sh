#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="${RUN_DATE}-structured-handoff"

"$ROOT/commands/collab/engine/registry.py" init --agent-id mod-agent "Structured Handoff" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Handoff --force --caller-role mod >/dev/null

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe)"
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"

cat >bad-handoff.md <<'BAD'
EFFORT OVERRIDE: matrix

**writeScope:**
- `commands/collab/engine/registry.py`

**validationCommands:** `./platform/tooling/audit.sh && ./tests/run.sh`
BAD

set +e
bad_output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" pe --content-file bad-handoff.md --observed-revision "$revision" --caller-role pe 2>&1)"
bad_status=$?
set -e

if [[ "$bad_status" -eq 0 ]]; then
  printf 'FAIL: speak-render accepted shell-string validationCommands\n' >&2
  exit 1
fi

if [[ "$bad_output" != *"ABORT: validationCommands contains disallowed pattern: ./platform/tooling/audit.sh && ./tests/run.sh"* ]]; then
  printf 'FAIL: malformed Handoff rejection message mismatch\n%s\n' "$bad_output" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'structured-handoff')
assert 'handoff' not in entry
assert 'handoff-pe-1' not in (registry.parent / Path(entry['transcriptPath'])).read_text()
PY

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe)"
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"

cat >good-handoff.md <<'GOOD'
EFFORT OVERRIDE: matrix

**writeScope:**
- `commands/collab/engine/registry.py`
- `tests/commands/collab/registry.py` _requires: #1_

**validationCommands:**
- `["./platform/tooling/audit.sh"]`
- `{"argv":["./tests/run.sh"]}`
GOOD

"$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" pe --content-file good-handoff.md --observed-revision "$revision" --caller-role pe >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'structured-handoff')
state = entry['handoff']['roles']['pe']
assert 'schema' + 'Version' not in entry['handoff']
assert 'schema' + 'Version' not in state
assert state['writeScope'] == ['commands/collab/engine/registry.py', 'tests/commands/collab/registry.py']
assert state['validationCommands'] == [['./platform/tooling/audit.sh'], ['./tests/run.sh']]
assert '_requires: #1_' in state['body']
transcript = (registry.parent / Path(entry['transcriptPath'])).read_text()
assert 'handoff-pe-1' in transcript
assert '_requires: #1_' in transcript
assert '["./platform/tooling/audit.sh"]' in transcript
PY

"$ROOT/commands/collab/engine/registry.py" handoff-state "$TARGET" pe >handoff-state.json
python3 - <<'PY'
import json
from pathlib import Path
state = json.loads(Path('handoff-state.json').read_text())
assert state['writeScope'][0] == 'commands/collab/engine/registry.py'
PY

transcript_path="$(python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
target = sys.argv[2]
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['id'] == target)
print(registry.parent / Path(entry['transcriptPath']))
PY
)"
"$ROOT/commands/collab/engine/registry.py" render-status "$TARGET" >/dev/null
cp "$transcript_path" first-render.md
"$ROOT/commands/collab/engine/registry.py" render-status "$TARGET" >/dev/null
cmp "$transcript_path" first-render.md

"$ROOT/commands/collab/engine/registry.py" execute-spawn "$TARGET" pe --scope commands/collab/engine/registry.py --returned-path commands/collab/engine/registry.py >/dev/null

set +e
execution_scope_output="$("$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-16T03:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path README.md \
  --caller-role pe 2>&1)"
execution_scope_status=$?
set -e

if [[ "$execution_scope_status" -eq 0 ]]; then
  printf 'FAIL: execution accepted touched path outside declared writeScope\n' >&2
  exit 1
fi

if [[ "$execution_scope_output" != *"execution touched path outside declared writeScope: README.md"* ]]; then
  printf 'FAIL: execution touched-path scope message mismatch\n%s\n' "$execution_scope_output" >&2
  exit 1
fi

"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-05-16T03:01:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path commands/collab/engine/registry.py \
  --caller-role pe >/dev/null

set +e
scope_output="$("$ROOT/commands/collab/engine/registry.py" execute-spawn "$TARGET" pe --scope tools --returned-path commands/collab/engine/registry.py 2>&1)"
scope_status=$?
set -e

if [[ "$scope_status" -eq 0 ]]; then
  printf 'FAIL: execute-spawn accepted scope outside declared writeScope\n' >&2
  exit 1
fi

if [[ "$scope_output" != *"execute-spawn scope outside declared writeScope: tools"* ]]; then
  printf 'FAIL: execute-spawn declared-scope message mismatch\n%s\n' "$scope_output" >&2
  exit 1
fi

set +e
returned_output="$("$ROOT/commands/collab/engine/registry.py" execute-spawn "$TARGET" pe --scope commands/collab/engine/registry.py --returned-path tests/commands/collab/registry.py/outside.test.sh 2>&1)"
returned_status=$?
set -e

if [[ "$returned_status" -eq 0 ]]; then
  printf 'FAIL: execute-spawn accepted returned path outside assigned scope\n' >&2
  exit 1
fi

if [[ "$returned_output" != *"returned path outside assigned scope: tests/commands/collab/registry.py/outside.test.sh"* ]]; then
  printf 'FAIL: execute-spawn returned-path message mismatch\n%s\n' "$returned_output" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'structured-handoff')
entry['handoff']['roles']['pe']['futureOptionalField'] = {'compatible': True}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
"$ROOT/commands/collab/engine/registry.py" validate >/dev/null

printf 'OK: structured Handoff state is validated, persisted, rendered, and consumed\n'
