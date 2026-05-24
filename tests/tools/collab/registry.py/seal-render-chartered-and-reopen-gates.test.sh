#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

# shellcheck source=/dev/null
source "$ROOT/tests/tools/collab/registry.py/verification-test-lib.sh"

RUN_DATE="$(date +%Y-%m-%d)"

insert_chartered_deliverable() {
  local target="$1"
  local deliverable="$2"
  python3 - "$target" "$deliverable" "$(registry_path)" <<'PY'
import json
import sys
from pathlib import Path

target, deliverable, registry = sys.argv[1:4]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
transcript_path = path.parent / entry['transcriptPath']
text = transcript_path.read_text()
marker = "## Audit\n<!-- collab:content-only; do-not-execute -->\n"
replacement = marker + f"\ncharteredDeliverables:\n- {deliverable}\n"
transcript_path.write_text(text.replace(marker, replacement, 1))
PY
}

init_reviewer_target "Chartered Deliverable Missing" "chartered-deliverable-missing"
CHARTERED_TARGET="$RUN_DATE-chartered-deliverable-missing"
insert_chartered_deliverable "$CHARTERED_TARGET" "commands/agent/index.md: move agent router"
"$ROOT/tools/collab/registry.py" set "$CHARTERED_TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$CHARTERED_TARGET"
chartered_revision="$(assessment_revision "$CHARTERED_TARGET")"
set +e
chartered_output="$("$ROOT/tools/collab/registry.py" seal-render "$CHARTERED_TARGET" pa \
  --observed-revision "$chartered_revision" \
  --outcome success \
  --caller-role pa 2>&1)"
chartered_status=$?
set -e
if [[ "$chartered_status" -eq 0 || "$chartered_output" != *"CHARTERED-DELIVERABLE-MISSING: commands/agent/index.md"* ]]; then
  printf 'FAIL: success assessment accepted missing chartered deliverable\n%s\n' "$chartered_output" >&2
  exit 1
fi

init_reviewer_target "Reopen Turn Order Drift" "reopen-turn-order-drift"
TURN_TARGET="$RUN_DATE-reopen-turn-order-drift"
"$ROOT/tools/collab/registry.py" join-participants "$TURN_TARGET" tw --agent-id sonnet >/dev/null
python3 - "$TURN_TARGET" "$(registry_path)" <<'PY'
import json
import sys
from pathlib import Path

target, registry = sys.argv[1:3]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entry['activePhase'] = 'Completion'
entry['status'] = 'open'
entry['turnOrder'] = ['tw', 'pe']
entry['verdict'] = {
    'outcome': 'incomplete',
    'restoreTarget': 'Action Plan',
    'restoreReason': 'test reopen drift',
    'failureCategory': 'test',
}
path.write_text(json.dumps(data, indent=2) + '\n')
PY
set +e
turn_output="$("$ROOT/tools/collab/registry.py" reopen "$TURN_TARGET" action-plan --caller-role mod 2>&1)"
turn_status=$?
set -e
if [[ "$turn_status" -eq 0 || "$turn_output" != *"TURN-ORDER-DRIFT:"* ]]; then
  printf 'FAIL: reopen accepted drifted turn order\n%s\n' "$turn_output" >&2
  exit 1
fi

init_reviewer_target "Reviewer Conclusion Gates" "reviewer-conclusion-gates"
CONCLUSION_TARGET="$RUN_DATE-reviewer-conclusion-gates"
"$ROOT/tools/collab/registry.py" set "$CONCLUSION_TARGET" active-phase Conclusion --force --caller-role mod >/dev/null
pe_state="$("$ROOT/tools/collab/registry.py" speak-state "$CONCLUSION_TARGET" pe)"
pe_revision="$(read_json_field registryRevision <<<"$pe_state")"
pe_content="$TMPDIR/pe-conclusion.md"
cat >"$pe_content" <<'PE'
**Directive:** "Verify reviewer conclusion gates."
**Action Plan: satisfies**

participant conclusion
PE
"$ROOT/tools/collab/registry.py" speak-render "$CONCLUSION_TARGET" pe \
  --content-file "$pe_content" \
  --observed-revision "$pe_revision" \
  --caller-role pe >/dev/null
pa_state="$("$ROOT/tools/collab/registry.py" speak-state "$CONCLUSION_TARGET" pa)"
pa_revision="$(read_json_field registryRevision <<<"$pa_state")"
pa_content="$TMPDIR/pa-conclusion.md"
cat >"$pa_content" <<'PA'
EFFORT OVERRIDE: matrix

**Directive:** "Verify reviewer conclusion gates."
**Action Plan: satisfies**

reviewer conclusion without required gates
PA
set +e
pa_output="$("$ROOT/tools/collab/registry.py" speak-render "$CONCLUSION_TARGET" pa \
  --content-file "$pa_content" \
  --observed-revision "$pa_revision" \
  --caller-role pa 2>&1)"
pa_status=$?
set -e
if [[ "$pa_status" -eq 0 || "$pa_output" != *"REVIEWER-CONCLUSION-GATE-MISSING:"* ]]; then
  printf 'FAIL: reviewer Conclusion accepted missing gates\n%s\n' "$pa_output" >&2
  exit 1
fi

printf 'OK: seal, reopen, and reviewer conclusion gates reject missing required evidence\n'
