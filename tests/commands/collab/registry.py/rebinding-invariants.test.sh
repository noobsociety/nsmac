#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

RUN_DATE="$(date +%Y-%m-%d)"

mkdir "$TMPDIR/project-rebinding"
cd "$TMPDIR/project-rebinding"
export COLLAB_STATE_HOME="$TMPDIR/project-state-home"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Project Rebinding Source" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
ORIGINAL_PROJECT_ID="$(python3 - <<'PY'
import json
from pathlib import Path

print(json.loads(Path('.collab.json').read_text())['projectId'])
PY
)"
REBIND_PROJECT_ID="rebinding-target-0001"

python3 - "$REGISTRY" "$COLLAB_STATE_HOME" "$REBIND_PROJECT_ID" <<'PY'
import shutil
import sys
from pathlib import Path

registry, state_home, rebound = sys.argv[1:4]
target = Path(state_home) / rebound
target.mkdir(parents=True, exist_ok=True)
shutil.copyfile(registry, target / 'registry.json')
PY

python3 - "$REBIND_PROJECT_ID" <<'PY'
import json
import sys
from pathlib import Path

path = Path('.collab.json')
identity = json.loads(path.read_text())
identity['projectId'] = sys.argv[1]
identity['label'] = 'rebound-project'
path.write_text(json.dumps(identity, indent=2) + '\n')
PY

set +e
PROJECT_OUTPUT="$("$ROOT/commands/collab/engine/registry.py" list 2>&1)"
PROJECT_STATUS=$?
set -e

if [[ "$PROJECT_STATUS" -eq 0 ]]; then
  printf 'FAIL: projectId rebinding was accepted across separate state roots\n' >&2
  exit 1
fi
if [[ "$PROJECT_OUTPUT" != *"project identity mismatch:"* || "$PROJECT_OUTPUT" != *"$ORIGINAL_PROJECT_ID"* || "$PROJECT_OUTPUT" != *"$REBIND_PROJECT_ID"* ]]; then
  printf 'FAIL: projectId rebinding rejection message mismatch\n%s\n' "$PROJECT_OUTPUT" >&2
  exit 1
fi

mkdir "$TMPDIR/agentid-rebinding"
cd "$TMPDIR/agentid-rebinding"
export COLLAB_STATE_HOME="$TMPDIR/agent-state-home"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Agentid Rebinding" >/dev/null
TARGET="$RUN_DATE-agentid-rebinding"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id gpt >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"

set +e
AGENT_OUTPUT="$("$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex 2>&1)"
AGENT_STATUS=$?
set -e

if [[ "$AGENT_STATUS" -ne 0 ]]; then
  printf 'FAIL: repeat join should reject agentId rebinding as a no-op advisory, not abort\n%s\n' "$AGENT_OUTPUT" >&2
  exit 1
fi
if [[ "$AGENT_OUTPUT" != *"IDENTITY-WARN: pe already joined as gpt; supplied agentId codex ignored"* ]]; then
  printf 'FAIL: agentId rebinding warning mismatch\n%s\n' "$AGENT_OUTPUT" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'agentid-rebinding')
pe = next(item for item in entry['participants'] if item['role'] == 'pe')
assert pe['agentId'] == 'gpt', pe
PY

python3 - "$ROOT" "$TMPDIR" <<'PY'
import importlib.util
import sys
from pathlib import Path

root = Path(sys.argv[1])
tmp = Path(sys.argv[2]) / 'issue-bridge-root'
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('registry_under_test', root / 'commands/collab/engine/registry.py')
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

def write(rel: str, text: str) -> None:
    path = tmp / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

write('commands/collab/export-issues/index.md', '# /collab export-issues\n')
write('commands/collab/index.md', '# /collab\n')
write('commands/commands.md', '# /commands\n')
write(
    'commands/collab/init/index.md',
    '\n'.join([
        '# /collab init',
        'Use --terminal seal|issue.',
        '```route-arg',
        'param: name=--terminal; values=seal|issue; default=seal',
        '```',
    ]),
)
write(
    'commands/collab/reference/registry.md',
    '\n'.join([
        '# /collab registry',
        '| `terminal` | string | Workflow-model terminal selector: seal|issue. |',
    ]),
)
write(
    'commands/collab/engine/registry.py',
    '\n'.join([
        "ALLOWED_TERMINALS = {'seal', 'issue'}",
        "if token == '--terminal': pass",
        "entry = {'terminal': terminal}",
    ]),
)

try:
    module.validate_issue_bridge_block(tmp)
except SystemExit as exc:
    message = str(exc)
    assert 'issue bridge blocked until prerequisite artifacts are present: commands/collab/reference/helper-output.md and tests/commands/collab/registry.py/rebinding-invariants.test.sh' in message, message
    assert 'full-body envelope rejection' in message, message
    assert 'rebinding invariant test file' in message, message
else:
    raise AssertionError('issue bridge gate accepted missing prerequisites')

write(
    'commands/collab/reference/helper-output.md',
    '\n'.join([
        '## Abort families',
        'Each entry names the logical module.',
        'Full-body envelope rejection',
        'Paired-execution-signature double-increment guard',
        'seal-verification-archive-protocol-violation',
    ]),
)
write(
    'tests/commands/collab/registry.py/rebinding-invariants.test.sh',
    '\n'.join([
        '#!/usr/bin/env bash',
        '# projectId rebinding',
        '# agentId rebinding',
        '# issue bridge',
    ]),
)
write(
    'commands/collab/reference/workflow-models.md',
    '\n'.join([
        '# Workflow models',
        '## Issue workflow model (`--terminal issue`)',
        '### Issue lifecycle',
        '### Seal-free close',
        '### Replacement close-gate',
    ]),
)
write(
    'commands/collab/reference/glossary.md',
    '\n'.join([
        '- **terminal**',
        '- **workflow model**',
        '- **issue terminal**',
    ]),
)
module.validate_issue_bridge_block(tmp)
PY

printf 'OK: projectId rebinding, agentId rebinding, and issue bridge gate invariants hold\n'
