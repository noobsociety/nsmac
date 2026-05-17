#!/usr/bin/env bash
set -euo pipefail

# NOTE: Current helper blocks post-cap-exit assessment writes at the activePhase gate instead of exercising budget-exempt assessment accounting.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_verification_test_lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export CURSOR_COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Verification Assessment Post Cap Rounds" "verification-assessment-post-cap-rounds"
TARGET="$RUN_DATE-verification-assessment-post-cap-rounds"
REGISTRY="$(registry_path)"
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'verification-assessment-post-cap-rounds')
entry['verification']['cap'] = 1
path.write_text(json.dumps(data, indent=2) + '\n')
PY

registry_rounds() {
  python3 - "$TARGET" "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

target, registry = sys.argv[1:3]
entry = next(item for item in json.loads(Path(registry).read_text())['collabs'] if item['id'] == target)
print(entry['verification']['rounds'])
PY
}

assert_rounds() {
  local label="$1"
  local expected="$2"
  local actual
  actual="$(registry_rounds)"
  if [[ "$actual" != "$expected" ]]; then
    printf 'FAIL: expected verificationRounds %s after %s; got %s\n' "$expected" "$label" "$actual" >&2
    exit 1
  fi
}

state="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa)"
rounds="$(read_json_field verificationRounds <<<"$state")"
revision="$(read_json_field registryRevision <<<"$state")"
if [[ "$rounds" != "1" ]]; then
  printf 'FAIL: seal-state did not record exactly one verification round\n%s\n' "$state" >&2
  exit 1
fi
assert_rounds "paired reviewer-executor round" 1

set +e
cap_output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa 2>&1)"
cap_status=$?
set -e
if [[ "$cap_status" -eq 0 || "$cap_output" != *"round cap reached; reissue with --cap-exit reopen-action-plan, --cap-exit reopen-handoff, --cap-exit follow-up-collab, or --cap-exit archive"* ]]; then
  printf 'FAIL: seal-render did not enforce cap before cap-exit\n%s\n' "$cap_output" >&2
  exit 1
fi
assert_rounds "blocked over-cap seal attempt" 1

"$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" \
  --cap-exit reopen-action-plan \
  --caller-role pa >/dev/null
assert_rounds "cap-exit reopen-action-plan" 0

post_cap_revision="$(registry_revision)"
set +e
assessment_output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$post_cap_revision" \
  --outcome incomplete \
  --restore-target "Action Plan" \
  --restore-reason "test" \
  --caller-role pa 2>&1)"
assessment_status=$?
set -e
if [[ "$assessment_status" -eq 0 || "$assessment_output" != *"/collab seal verification is valid only in the Completion phase"* ]]; then
  printf 'FAIL: post-cap assessment write did not abort at the Completion phase gate\n%s\n' "$assessment_output" >&2
  exit 1
fi
assert_rounds "blocked post-cap assessment write" 0

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(item for item in json.loads(Path(sys.argv[1]).read_text())['collabs'] if item['slug'] == 'verification-assessment-post-cap-rounds')
assert entry['status'] == 'open'
assert entry['activePhase'] == 'Action Plan'
assert entry['completion']['subState'] == 'execution'
assert entry['verification']['subState'] == 'assessment'
assert entry['verification']['rounds'] == 0
assert entry['verificationSeal']['capExit'] == 'reopen-action-plan'
assert 'verdict' not in entry
PY

printf 'OK: post-cap-exit assessment writes are blocked at the phase gate and do not spend verification rounds\n'
