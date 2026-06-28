#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/registry.py/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Seal Verdict" "seal-verdict"
TARGET="$RUN_DATE-seal-verdict"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$TARGET"
revision="$(assessment_revision "$TARGET")"
"$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" \
  --outcome success \
  --evidence '{"registryRevision":2,"committedPaths":["platform/tooling/audit.sh"],"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"]}' \
  --caller-role pa >/dev/null

REGISTRY="$(registry_path)"
COMPANION="$(python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['id'] == target)
print(registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-seal-verdict.json"))
PY
)"

python3 - "$COMPANION" <<'PY'
import json
import sys
from pathlib import Path

companion = json.loads(Path(sys.argv[1]).read_text())
assert companion['authoritative'] is False, companion
assert companion['authority'] == 'verificationSeal', companion
assert companion['closeGate'] == 'verificationSeal', companion
assert companion['verdict']['outcome'] == 'success', companion
assert companion['stale'] is False, companion
PY

"$ROOT/commands/collab/engine/registry.py" show-verdict "$TARGET" >show-verdict.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path('show-verdict.json').read_text())
assert data['target'].endswith('seal-verdict')
assert data['status'] == 'closed'
assert data['activePhase'] == 'Completion'
assert data['completionSubState'] == 'verification'
assert data['verificationReviewSubState'] == 'assessment'
assert data['verdict']['outcome'] == 'success'
assert data['verificationSeal']['sealedBy'] == 'pa'
assert data['sealVerdict']['authoritative'] is False, data
assert data['sealVerdict']['closeGate'] == 'verificationSeal', data
assert data['sealVerdict']['verdict']['outcome'] == 'success', data
PY

set +e
missing_output="$("$ROOT/commands/collab/engine/registry.py" show-verdict "$RUN_DATE-seal-verdict-missing" 2>&1)"
missing_status=$?
set -e
if [[ "$missing_status" -eq 0 || "$missing_output" != *"registry target not found"* ]]; then
  printf 'FAIL: show-verdict missing target rejection mismatch\n%s\n' "$missing_output" >&2
  exit 1
fi

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['status'] = 'open'
data['activeCollabId'] = target
registry.write_text(json.dumps(data, indent=2) + '\n')
PY

"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-06-11T01:30:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope full \
  --touched-path platform/tooling/audit.sh \
  --caller-role pe >/dev/null

python3 - "$REGISTRY" "$TARGET" "$COMPANION" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
companion_path = Path(sys.argv[3])
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
seal = entry['verificationSeal']
companion = json.loads(companion_path.read_text())
assert seal['stale'] is True, seal
assert seal['staleReason'] == 'execution changed for pe', seal
assert companion['authoritative'] is False, companion
assert companion['closeGate'] == 'verificationSeal', companion
assert companion['stale'] is True, companion
assert companion['staleReason'] == 'execution changed for pe', companion
assert companion['verdict'] is None, companion
PY

set +e
close_output="$("$ROOT/commands/collab/engine/registry.py" close "$TARGET" --caller-role mod 2>&1)"
close_status=$?
set -e
if [[ "$close_status" -eq 0 || "$close_output" != *"close blocked: verificationSeal is stale: execution changed for pe"* ]]; then
  printf 'FAIL: close did not gate on stale verificationSeal\n%s\n' "$close_output" >&2
  exit 1
fi

printf 'OK: seal-verdict companion is regenerated and non-authoritative after seal input changes\n'
