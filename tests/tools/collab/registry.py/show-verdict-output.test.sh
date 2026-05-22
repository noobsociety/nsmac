#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Show Verdict Output" "show-verdict-output"
TARGET="$RUN_DATE-show-verdict-output"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$TARGET"
revision="$(assessment_revision "$TARGET")"
"$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" \
  --outcome success \
  --evidence '{"registryRevision":2,"committedPaths":["tools/collab/registry.py"],"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"]}' \
  --caller-role pa >/dev/null

"$ROOT/tools/collab/registry.py" show-verdict "$TARGET" >verdict.json
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path('verdict.json').read_text())
assert data['target'].endswith('show-verdict-output')
assert data['status'] == 'closed'
assert data['activePhase'] == 'Completion'
assert data['completionSubState'] == 'verification'
assert data['verificationReviewSubState'] == 'assessment'
assert data['verdict']['outcome'] == 'success'
assert data['verificationSeal']['sealedBy'] == 'pa'
PY

set +e
missing_output="$("$ROOT/tools/collab/registry.py" show-verdict "$RUN_DATE-show-verdict-output-missing" 2>&1)"
missing_status=$?
set -e
if [[ "$missing_status" -eq 0 || "$missing_output" != *"registry target not found"* ]]; then
  printf 'FAIL: show-verdict missing target rejection mismatch\n%s\n' "$missing_output" >&2
  exit 1
fi

printf 'OK: show-verdict emits closed-collab verdict metadata\n'
