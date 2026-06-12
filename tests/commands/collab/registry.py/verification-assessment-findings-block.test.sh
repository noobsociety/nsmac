#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Verification Assessment Findings Block" "verification-assessment-findings-block"
TARGET="$RUN_DATE-verification-assessment-findings-block"
REGISTRY="$(registry_path)"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$TARGET"

revision="$(assessment_revision "$TARGET")"
output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" \
  --outcome incomplete \
  --restore-target "Action Plan" \
  --restore-reason "Action Plan acceptance criteria were not met." \
  --failure-category missing-acceptance \
  --evidence '{"registryRevision":2,"transcriptIds":["action-plan-pe-1"],"committedPaths":["platform/tooling/audit.sh"],"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"]}' \
  --caller-role pa)"

if [[ "$output" != *"NEXT: Moderator should run (collab reopen action-plan $TARGET)."* ]]; then
  printf 'FAIL: helper NEXT did not emit reopen guidance\n%s\n' "$output" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'verification-assessment-findings-block')
transcript = (registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md")).read_text()
start = transcript.index('<a name="reviewer-findings-1"></a>')
end = transcript.index('</details>', start) + len('</details>')
block = transcript[start:end]
assert '<summary>pa · reopen brief (incomplete, missing-acceptance)</summary>' in block
assert 'restoreReason: Action Plan acceptance criteria were not met.' in block
assert 'restoreTarget: Action Plan' in block
assert 'failureCategory: missing-acceptance' in block
assert '  revision: 2' in block
assert '  committedPaths: ["platform/tooling/audit.sh"]' in block
assert '  executionEntryIds: ["pe-2026-05-15t21-00-00-02-00"]' in block
assert '  transcriptIds: ["action-plan-pe-1"]' in block
assert f'  NEXT: (collab reopen action-plan {entry["id"]})' in block
assert '  REASON: Action Plan acceptance criteria were not met.' in block
assert '  AFFECTED: committedPaths=["platform/tooling/audit.sh"]; executionEntryIds=["pe-2026-05-15t21-00-00-02-00"]; transcriptIds=["action-plan-pe-1"]' in block
assert '  RETURN: Action Plan' in block
assert f'helperNext: NEXT: Moderator should run (collab reopen action-plan {entry["id"]}).' in block
assert block.index('  RETURN: Action Plan') < block.index('helperNext:')
Path('findings-block.txt').write_text(block)
PY

"$ROOT/commands/collab/engine/registry.py" reopen "$TARGET" action-plan --caller-role mod >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'verification-assessment-findings-block')
transcript = (registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md")).read_text()
block = Path('findings-block.txt').read_text()
assert 'verdict' not in entry
assert block in transcript
assert '> Reopened from [reviewer findings](#reviewer-findings-1); next expected role: `pe`.' in transcript
PY

init_reviewer_target "Verification Assessment Success Omits Findings" "verification-assessment-success-omits-findings"
SUCCESS_TARGET="$RUN_DATE-verification-assessment-success-omits-findings"
SUCCESS_REGISTRY="$(registry_path)"
"$ROOT/commands/collab/engine/registry.py" set "$SUCCESS_TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$SUCCESS_TARGET"
success_revision="$(assessment_revision "$SUCCESS_TARGET")"
"$ROOT/commands/collab/engine/registry.py" seal-render "$SUCCESS_TARGET" pa \
  --observed-revision "$success_revision" \
  --outcome success \
  --evidence '{"registryRevision":2,"committedPaths":["platform/tooling/audit.sh"],"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"]}' \
  --caller-role pa >/dev/null

python3 - "$SUCCESS_REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'verification-assessment-success-omits-findings')
transcript = (registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md")).read_text()
assert entry['status'] == 'closed'
assert entry['verdict']['outcome'] == 'success'
assert 'reviewer-findings-' not in transcript
PY

printf 'OK: non-success assessment emits durable findings, reopen preserves it, and success omits it\n'
