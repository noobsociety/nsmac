#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="${RUN_DATE}-structured-handoff"

"$ROOT/tools/collab/registry.py" init --agent-id mod-agent "Structured Handoff" >/dev/null
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Handoff --force --caller-role mod >/dev/null

state="$("$ROOT/tools/collab/registry.py" speak-state "$TARGET" pe)"
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"

cat >bad-handoff.md <<'BAD'
EFFORT OVERRIDE: matrix

**writeScope:**
- `tools/collab/registry.py`

**validationCommands:** `./tools/cursor/audit.sh && ./tests/run.sh`
BAD

set +e
bad_output="$("$ROOT/tools/collab/registry.py" speak-render "$TARGET" pe --content-file bad-handoff.md --observed-revision "$revision" --caller-role pe 2>&1)"
bad_status=$?
set -e

if [[ "$bad_status" -eq 0 ]]; then
  printf 'FAIL: speak-render accepted shell-string validationCommands\n' >&2
  exit 1
fi

if [[ "$bad_output" != *"ABORT: validationCommands contains disallowed pattern: ./tools/cursor/audit.sh && ./tests/run.sh"* ]]; then
  printf 'FAIL: malformed Handoff rejection message mismatch\n%s\n' "$bad_output" >&2
  exit 1
fi

python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path('.collabs/registry.json').read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'structured-handoff')
assert 'handoff' not in entry
assert 'handoff-pe-1' not in Path(entry['transcriptPath']).read_text()
PY

state="$("$ROOT/tools/collab/registry.py" speak-state "$TARGET" pe)"
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"

cat >good-handoff.md <<'GOOD'
EFFORT OVERRIDE: matrix

**writeScope:**
- `tools/collab/registry.py`
- `tests/tools/collab/registry.py` _requires: #1_

**validationCommands:**
- `["./tools/cursor/audit.sh"]`
- `{"argv":["./tests/run.sh"]}`
GOOD

"$ROOT/tools/collab/registry.py" speak-render "$TARGET" pe --content-file good-handoff.md --observed-revision "$revision" --caller-role pe >/dev/null

python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path('.collabs/registry.json').read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'structured-handoff')
state = entry['handoff']['roles']['pe']
assert state['schemaVersion'] == 1
assert state['writeScope'] == ['tools/collab/registry.py', 'tests/tools/collab/registry.py']
assert state['validationCommands'] == [['./tools/cursor/audit.sh'], ['./tests/run.sh']]
assert '_requires: #1_' in state['body']
transcript = Path(entry['transcriptPath']).read_text()
assert 'handoff-pe-1' in transcript
assert '_requires: #1_' in transcript
assert '["./tools/cursor/audit.sh"]' in transcript
PY

"$ROOT/tools/collab/registry.py" handoff-state "$TARGET" pe >handoff-state.json
python3 - <<'PY'
import json
from pathlib import Path
state = json.loads(Path('handoff-state.json').read_text())
assert state['writeScope'][0] == 'tools/collab/registry.py'
PY

transcript_path=".collabs/records/${TARGET}.md"
"$ROOT/tools/collab/registry.py" render-status "$TARGET" >/dev/null
cp "$transcript_path" first-render.md
"$ROOT/tools/collab/registry.py" render-status "$TARGET" >/dev/null
cmp "$transcript_path" first-render.md

"$ROOT/tools/collab/registry.py" execute-spawn "$TARGET" pe --scope tools/collab/registry.py --returned-path tools/collab/registry.py >/dev/null

set +e
scope_output="$("$ROOT/tools/collab/registry.py" execute-spawn "$TARGET" pe --scope tools --returned-path tools/collab/registry.py 2>&1)"
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
returned_output="$("$ROOT/tools/collab/registry.py" execute-spawn "$TARGET" pe --scope tools/collab/registry.py --returned-path tests/tools/collab/registry.py/outside.test.sh 2>&1)"
returned_status=$?
set -e

if [[ "$returned_status" -eq 0 ]]; then
  printf 'FAIL: execute-spawn accepted returned path outside assigned scope\n' >&2
  exit 1
fi

if [[ "$returned_output" != *"returned path outside assigned scope: tests/tools/collab/registry.py/outside.test.sh"* ]]; then
  printf 'FAIL: execute-spawn returned-path message mismatch\n%s\n' "$returned_output" >&2
  exit 1
fi

python3 - <<'PY'
import json
from pathlib import Path
path = Path('.collabs/registry.json')
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'structured-handoff')
entry['handoff']['roles']['pe']['futureOptionalField'] = {'compatible': True}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
"$ROOT/tools/collab/registry.py" validate >/dev/null

printf 'OK: structured Handoff state is validated, persisted, rendered, and consumed\n'
