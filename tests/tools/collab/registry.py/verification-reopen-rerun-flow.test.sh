#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Verification Reopen Rerun Flow" "verification-reopen-rerun-flow"
TARGET="$RUN_DATE-verification-reopen-rerun-flow"
REGISTRY="$(registry_path)"

"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Handoff --force --caller-role mod >/dev/null
state="$("$ROOT/tools/collab/registry.py" speak-state "$TARGET" pe)"
revision="$(read_json_field registryRevision <<<"$state")"

cat >handoff.md <<'HANDOFF'
EFFORT OVERRIDE: high — implementation-density: test handoff setup

**writeScope**
`tools/collab/registry.py`

**validationCommands**
`[["./tools/command-system/audit.sh"]]`
HANDOFF

"$ROOT/tools/collab/registry.py" speak-render "$TARGET" pe \
  --content-file handoff.md \
  --observed-revision "$revision" \
  --caller-role pe >/dev/null

"$ROOT/tools/collab/registry.py" execution "$TARGET" pe completed "2026-05-17T10:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path tools/collab/registry.py \
  --caller-role pe >/dev/null

seal_target "$TARGET"
revision="$(assessment_revision "$TARGET")"
output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" \
  --outcome failed \
  --restore-target Handoff \
  --restore-reason "The Handoff scope missed the route function file." \
  --failure-category out-of-scope \
  --evidence '{"registryRevision":2,"transcriptIds":["handoff-pe-1"],"committedPaths":["tools/collab/registry.py"],"executionEntryIds":["pe-2026-05-17t10-00-00-02-00"]}' \
  --caller-role pa)"

if [[ "$output" != *"NEXT: Moderator should run /collab reopen handoff $TARGET."* ]]; then
  printf 'FAIL: assessment verdict did not point at /collab reopen handoff\n%s\n' "$output" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'verification-reopen-rerun-flow')
transcript = (registry.parent / entry['transcriptPath']).read_text()
start = transcript.index('<a name="reviewer-findings-1"></a>')
end = transcript.index('</details>', start) + len('</details>')
block = transcript[start:end]
assert 'restoreTarget: Handoff' in block
assert f'  NEXT: /collab reopen handoff {entry["id"]}' in block
assert block.index('  NEXT:') < block.index('helperNext:')
Path('findings-block.txt').write_text(block)
PY

"$ROOT/tools/collab/registry.py" reopen "$TARGET" handoff --caller-role mod >/dev/null

cat >revised-handoff.md <<'HANDOFF'
EFFORT OVERRIDE: high — implementation-density: revised test handoff setup

Scope revised after verification found the route function file missing.

**writeScope**
`tools/collab/registry.py`
`_functions/collab/reopen.md`

**validationCommands**
`[["./tools/command-system/audit.sh"],["./tests/run.sh"]]`
HANDOFF

"$ROOT/tools/collab/registry.py" rewrite-speak-render "$TARGET" pe \
  --content-file revised-handoff.md \
  --caller-role pe >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'verification-reopen-rerun-flow')
state = entry['handoff']['roles']['pe']
assert state['writeScope'] == ['tools/collab/registry.py', '_functions/collab/reopen.md']
assert state['validationCommands'] == [['./tools/command-system/audit.sh'], ['./tests/run.sh']]
assert 'Scope revised after verification' in state['body']
assert 'Previous revision,' in state['body']
assert 'verdict' not in entry
transcript = (registry.parent / entry['transcriptPath']).read_text()
assert Path('findings-block.txt').read_text() in transcript
assert '> Reopened from [reviewer findings](#reviewer-findings-1); next expected role: `pe`.' in transcript
assert '_functions/collab/reopen.md' in transcript
assert 'Previous revision,' in transcript
PY

"$ROOT/tools/collab/registry.py" render-status "$TARGET" >/dev/null
python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'verification-reopen-rerun-flow')
transcript = (registry.parent / entry['transcriptPath']).read_text()
assert 'Previous revision,' in transcript
assert '_functions/collab/reopen.md' in transcript
PY

"$ROOT/tools/collab/registry.py" advance "$TARGET" next --caller-role mod >/dev/null

"$ROOT/tools/collab/registry.py" execution "$TARGET" pe completed "2026-05-17T10:30:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path tools/collab/registry.py \
  --touched-path _functions/collab/reopen.md \
  --caller-role pe >/dev/null

seal_target "$TARGET"
revision="$(assessment_revision "$TARGET")"
"$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" \
  --outcome success \
  --evidence '{"registryRevision":3,"transcriptIds":["handoff-pe-1"],"committedPaths":["tools/collab/registry.py","_functions/collab/reopen.md"],"executionEntryIds":["pe-2026-05-17t10-30-00-02-00"]}' \
  --caller-role pa >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(item for item in json.loads(Path(sys.argv[1]).read_text())['collabs'] if item['slug'] == 'verification-reopen-rerun-flow')
assert entry['status'] == 'closed'
assert entry['execution']['pe']['entryId'] == 'pe-2026-05-17t10-30-00-02-00'
assert entry['verdict']['outcome'] == 'success'
PY

printf 'OK: non-success verdict reopens Handoff, resyncs rewritten Handoff scope, reruns execution, and re-seals\n'
