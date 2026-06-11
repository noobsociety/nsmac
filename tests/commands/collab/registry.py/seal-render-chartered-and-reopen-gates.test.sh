#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

# shellcheck source=/dev/null
source "$ROOT/tests/commands/collab/registry.py/verification-test-lib.sh"

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
transcript_path = path.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md")
text = transcript_path.read_text()
marker = "## Audit\n<!-- collab:content-only; do-not-execute -->\n"
replacement = marker + f"\ncharteredDeliverables:\n- {deliverable}\n"
transcript_path.write_text(text.replace(marker, replacement, 1))
PY
}

insert_audit_block() {
  local target="$1"
  local block="$2"
  python3 - "$target" "$block" "$(registry_path)" <<'PY'
import json
import sys
from pathlib import Path

target, block, registry = sys.argv[1:4]
path = Path(registry)
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
transcript_path = path.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md")
text = transcript_path.read_text()
marker = "## Audit\n<!-- collab:content-only; do-not-execute -->\n"
replacement = marker + "\n" + block + "\n"
transcript_path.write_text(text.replace(marker, replacement, 1))
PY
}

# A lenient label variant must be RECOGNIZED: if it were not, the block would
# parse to empty and a success seal would pass. The fact that the seal is
# rejected with CHARTERED-DELIVERABLE-MISSING proves the variant label was
# parsed and its (uncovered) deliverable was enforced by Invariant #17.
assert_variant_label_enforced() {
  local title="$1"
  local slug="$2"
  local block="$3"
  local target="$RUN_DATE-$slug"
  local revision
  local output
  local status

  init_reviewer_target "$title" "$slug"
  insert_audit_block "$target" "$block"
  "$ROOT/commands/collab/engine/registry.py" set "$target" active-phase Completion --force --caller-role mod >/dev/null
  start_assessment "$target"
  revision="$(assessment_revision "$target")"
  set +e
  output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$target" pa \
    --observed-revision "$revision" \
    --outcome success \
    --caller-role pa 2>&1)"
  status=$?
  set -e
  if [[ "$status" -eq 0 || "$output" != *"CHARTERED-DELIVERABLE-MISSING: commands/agent/index.md"* ]]; then
    printf 'FAIL: variant charteredDeliverables label not honored at seal for %s\n%s\n' "$slug" "$output" >&2
    exit 1
  fi
}

assert_success_accepts_absent_chartered_deliverables() {
  local target="$RUN_DATE-absent-chartered-deliverables"
  local revision
  local output
  local status

  init_reviewer_target "Absent Chartered Deliverables" "absent-chartered-deliverables"
  "$ROOT/commands/collab/engine/registry.py" set "$target" active-phase Completion --force --caller-role mod >/dev/null
  start_assessment "$target"
  revision="$(assessment_revision "$target")"
  set +e
  output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$target" pa \
    --observed-revision "$revision" \
    --outcome success \
    --caller-role pa 2>&1)"
  status=$?
  set -e
  if [[ "$status" -ne 0 ]]; then
    printf 'FAIL: success assessment rejected absent charteredDeliverables block\n%s\n' "$output" >&2
    exit 1
  fi
}

assert_success_accepts_empty_chartered_deliverables() {
  local target="$RUN_DATE-empty-chartered-deliverables"
  local revision
  local output
  local status

  init_reviewer_target "Empty Chartered Deliverables" "empty-chartered-deliverables"
  insert_audit_block "$target" $'**Chartered Deliverables:**\n\nThis paragraph is not a bullet.'
  "$ROOT/commands/collab/engine/registry.py" set "$target" active-phase Completion --force --caller-role mod >/dev/null
  start_assessment "$target"
  revision="$(assessment_revision "$target")"
  set +e
  output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$target" pa \
    --observed-revision "$revision" \
    --outcome success \
    --caller-role pa 2>&1)"
  status=$?
  set -e
  if [[ "$status" -ne 0 ]]; then
    printf 'FAIL: success assessment rejected empty charteredDeliverables block\n%s\n' "$output" >&2
    exit 1
  fi
}

assert_success_ignores_prose_mention_of_chartered_deliverables() {
  local target="$RUN_DATE-prose-mention-chartered-deliverables"
  local revision
  local output
  local status

  init_reviewer_target "Prose Mention Chartered Deliverables" "prose-mention-chartered-deliverables"
  insert_audit_block "$target" "This audit discusses chartered deliverables without declaring the field."
  "$ROOT/commands/collab/engine/registry.py" set "$target" active-phase Completion --force --caller-role mod >/dev/null
  start_assessment "$target"
  revision="$(assessment_revision "$target")"
  set +e
  output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$target" pa \
    --observed-revision "$revision" \
    --outcome success \
    --caller-role pa 2>&1)"
  status=$?
  set -e
  if [[ "$status" -ne 0 ]]; then
    printf 'FAIL: prose mention was misparsed as charteredDeliverables label\n%s\n' "$output" >&2
    exit 1
  fi
}

assert_success_accepts_absent_chartered_deliverables
assert_success_accepts_empty_chartered_deliverables
assert_success_ignores_prose_mention_of_chartered_deliverables

init_reviewer_target "Chartered Deliverable Missing" "chartered-deliverable-missing"
CHARTERED_TARGET="$RUN_DATE-chartered-deliverable-missing"
insert_chartered_deliverable "$CHARTERED_TARGET" "commands/agent/index.md: move agent router"
"$ROOT/commands/collab/engine/registry.py" set "$CHARTERED_TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$CHARTERED_TARGET"
chartered_revision="$(assessment_revision "$CHARTERED_TARGET")"
set +e
chartered_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$CHARTERED_TARGET" pa \
  --observed-revision "$chartered_revision" \
  --outcome success \
  --caller-role pa 2>&1)"
chartered_status=$?
set -e
if [[ "$chartered_status" -eq 0 || "$chartered_output" != *"CHARTERED-DELIVERABLE-MISSING: commands/agent/index.md"* ]]; then
  printf 'FAIL: success assessment accepted missing chartered deliverable\n%s\n' "$chartered_output" >&2
  exit 1
fi

assert_variant_label_enforced \
  "Emphasized Chartered Deliverables" \
  "emphasized-chartered-deliverables" \
  $'**charteredDeliverables:**\n- commands/agent/index.md: move agent router'

assert_variant_label_enforced \
  "Spaced Chartered Deliverables" \
  "spaced-chartered-deliverables" \
  $'charteredDeliverables :\n- commands/agent/index.md: move agent router'

assert_variant_label_enforced \
  "Case Variant Chartered Deliverables" \
  "case-variant-chartered-deliverables" \
  $'CharteredDeliverables:\n- commands/agent/index.md: move agent router'

assert_variant_label_enforced \
  "Two Word Chartered Deliverables" \
  "two-word-chartered-deliverables" \
  $'Chartered Deliverables:\n- commands/agent/index.md: move agent router'

assert_variant_label_enforced \
  "Backtick No Colon Chartered Deliverables" \
  "backtick-no-colon-chartered-deliverables" \
  $'`charteredDeliverables`\n- commands/agent/index.md: move agent router'

assert_variant_label_enforced \
  "Blank Line Chartered Deliverables" \
  "blank-line-chartered-deliverables" \
  $'charteredDeliverables:\n\n- commands/agent/index.md: move agent router'

init_reviewer_target "Prose Label Chartered Deliverables" "prose-label-chartered-deliverables"
PROSE_TARGET="$RUN_DATE-prose-label-chartered-deliverables"
insert_chartered_deliverable "$PROSE_TARGET" "Missed collaboration goals: identify targets not met"
"$ROOT/commands/collab/engine/registry.py" set "$PROSE_TARGET" active-phase Completion --force --caller-role mod >/dev/null
start_assessment "$PROSE_TARGET"
prose_revision="$(assessment_revision "$PROSE_TARGET")"
set +e
prose_output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$PROSE_TARGET" pa \
  --observed-revision "$prose_revision" \
  --outcome success \
  --caller-role pa 2>&1)"
prose_status=$?
set -e
if [[ "$prose_status" -ne 0 || "$prose_output" != *"CHARTER-NOTICE:"* ]]; then
  printf 'FAIL: prose-label charter was not treated as optional audit context\n%s\n' "$prose_output" >&2
  exit 1
fi

init_reviewer_target "Reopen Turn Order Drift" "reopen-turn-order-drift"
TURN_TARGET="$RUN_DATE-reopen-turn-order-drift"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TURN_TARGET" tw --agent-id sonnet >/dev/null
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
turn_output="$("$ROOT/commands/collab/engine/registry.py" reopen "$TURN_TARGET" action-plan --caller-role mod 2>&1)"
turn_status=$?
set -e
if [[ "$turn_status" -eq 0 || "$turn_output" != *"TURN-ORDER-DRIFT:"* ]]; then
  printf 'FAIL: reopen accepted drifted turn order\n%s\n' "$turn_output" >&2
  exit 1
fi

init_reviewer_target "Reviewer Conclusion Gates" "reviewer-conclusion-gates"
CONCLUSION_TARGET="$RUN_DATE-reviewer-conclusion-gates"
"$ROOT/commands/collab/engine/registry.py" set "$CONCLUSION_TARGET" active-phase Conclusion --force --caller-role mod >/dev/null
pe_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$CONCLUSION_TARGET" pe)"
pe_revision="$(read_json_field registryRevision <<<"$pe_state")"
pe_content="$TMPDIR/pe-conclusion.md"
cat >"$pe_content" <<'PE'
**Directive:** "Verify reviewer conclusion gates."
**Action Plan: satisfies**

participant conclusion
PE
"$ROOT/commands/collab/engine/registry.py" speak-render "$CONCLUSION_TARGET" pe \
  --content-file "$pe_content" \
  --observed-revision "$pe_revision" \
  --caller-role pe >/dev/null
pa_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$CONCLUSION_TARGET" pa)"
pa_revision="$(read_json_field registryRevision <<<"$pa_state")"
pa_content="$TMPDIR/pa-conclusion.md"
cat >"$pa_content" <<'PA'
EFFORT OVERRIDE: matrix

**Directive:** "Verify reviewer conclusion gates."
**Action Plan: satisfies**

reviewer conclusion without required gates
PA
set +e
pa_output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$CONCLUSION_TARGET" pa \
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
