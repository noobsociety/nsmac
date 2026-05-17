#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export CURSOR_COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Verification Assessment Flow" "verification-assessment-flow"
TARGET="$RUN_DATE-verification-assessment-flow"
REGISTRY="$(registry_path)"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$TARGET"

state="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa)"
ready="$(read_json_field readyToAssess <<<"$state")"
if [[ "$ready" != "True" ]]; then
  printf 'FAIL: seal-state did not expose assessment readiness\n%s\n' "$state" >&2
  exit 1
fi

revision="$(read_json_field registryRevision <<<"$state")"
output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" \
  --outcome incomplete \
  --restore-target "Action Plan" \
  --restore-reason "Action Plan acceptance criteria were not met." \
  --failure-category missing-acceptance \
  --evidence '{"registryRevision":2,"transcriptIds":["action-plan-pe-1"],"committedPaths":["tools/collab/registry.py"],"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"]}' \
  --caller-role pa)"

if [[ "$output" != *"NEXT: Moderator should run /collab reopen action-plan $TARGET."* ]]; then
  printf 'FAIL: assessment did not emit restore guidance\n%s\n' "$output" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['slug'] == 'verification-assessment-flow')
transcript = (registry.parent / entry['transcriptPath']).read_text()
assert entry['status'] == 'open'
assert entry['activePhase'] == 'Completion'
assert entry['completion']['subState'] == 'verification'
assert entry['verification']['subState'] == 'assessment'
assert entry['verdict']['outcome'] == 'incomplete'
assert entry['verdict']['restoreTarget'] == 'Action Plan'
assert entry['verdict']['failureCategory'] == 'missing-acceptance'
assert entry['verdict']['evidence']['transcriptIds'] == ['action-plan-pe-1']
assert '**pa:** assessed' in transcript
PY

printf 'OK: verification assessment records incomplete verdicts and restore guidance\n'
