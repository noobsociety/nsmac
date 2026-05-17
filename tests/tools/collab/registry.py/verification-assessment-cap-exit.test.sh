#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export CURSOR_COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Verification Assessment Cap Exit" "verification-assessment-cap-exit"
TARGET="$RUN_DATE-verification-assessment-cap-exit"
REGISTRY="$(registry_path)"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-assessment-cap-exit')
entry['verification']['cap'] = 1
path.write_text(json.dumps(data, indent=2) + '\n')
PY

state="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
set +e
output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa 2>&1)"
status=$?
set -e
if [[ "$status" -eq 0 || "$output" != *"round cap reached; reissue with --cap-exit reopen-action-plan, --cap-exit reopen-handoff, --cap-exit follow-up-collab, or --cap-exit archive"* ]]; then
  printf 'FAIL: seal-render did not require cap exit\n%s\n' "$output" >&2
  exit 1
fi

"$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" \
  --cap-exit reopen-action-plan \
  --caller-role pa >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(item for item in json.loads(Path(sys.argv[1]).read_text())['collabs'] if item['slug'] == 'verification-assessment-cap-exit')
assert entry['status'] == 'open'
assert entry['activePhase'] == 'Action Plan'
assert entry['completion']['subState'] == 'execution'
assert entry['verification']['subState'] == 'assessment'
assert entry['verificationSeal']['capExit'] == 'reopen-action-plan'
assert 'verdict' not in entry
PY

init_reviewer_target "Verification Follow Up Cap Exit" "verification-follow-up-cap-exit"
FOLLOW_TARGET="$RUN_DATE-verification-follow-up-cap-exit"
"$ROOT/tools/collab/registry.py" set "$FOLLOW_TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$FOLLOW_TARGET"

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-follow-up-cap-exit')
entry['verification']['cap'] = 1
path.write_text(json.dumps(data, indent=2) + '\n')
PY

follow_state="$("$ROOT/tools/collab/registry.py" seal-state "$FOLLOW_TARGET" pa)"
follow_revision="$(read_json_field registryRevision <<<"$follow_state")"
set +e
missing_output="$("$ROOT/tools/collab/registry.py" seal-render "$FOLLOW_TARGET" pa --observed-revision "$follow_revision" --cap-exit follow-up-collab --caller-role pa 2>&1)"
missing_status=$?
set -e
if [[ "$missing_status" -eq 0 || "$missing_output" != *"follow-up-collab cap-exit requires --restore-reason, --evidence, and --failure-category"* ]]; then
  printf 'FAIL: follow-up-collab cap exit did not require structured fields\n%s\n' "$missing_output" >&2
  exit 1
fi

follow_output="$("$ROOT/tools/collab/registry.py" seal-render "$FOLLOW_TARGET" pa \
  --observed-revision "$follow_revision" \
  --cap-exit follow-up-collab \
  --restore-reason "open participant verification finding" \
  --evidence '{"registryRevision":1,"executionEntryIds":["pe-2026-05-15t21-00-00-02-00"],"committedPaths":["tools/collab/registry.py"]}' \
  --failure-category "verification-gap" \
  --caller-role pa)"

if [[ "$follow_output" != *'NEXT: Open a follow-up collab {"evidence":'* || "$follow_output" != *'"failureCategory":"verification-gap"'* || "$follow_output" != *'"restoreReason":"open participant verification finding"'* ]]; then
  printf 'FAIL: follow-up-collab NEXT guidance was not structured\n%s\n' "$follow_output" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(item for item in json.loads(Path(sys.argv[1]).read_text())['collabs'] if item['slug'] == 'verification-follow-up-cap-exit')
assert entry['status'] == 'open'
assert entry['activePhase'] == 'Completion'
assert entry['verification']['subState'] == 'assessment'
assert entry['verificationSeal']['capExit'] == 'follow-up-collab'
assert entry['verificationSeal']['followUp']['restoreReason'] == 'open participant verification finding'
assert entry['verificationSeal']['followUp']['failureCategory'] == 'verification-gap'
assert entry['verificationSeal']['followUp']['evidence']['committedPaths'] == ['tools/collab/registry.py']
PY

printf 'OK: verification cap exits enter assessment state without applying verdict work and follow-up exits carry structured guidance\n'
