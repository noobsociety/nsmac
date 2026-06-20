#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"

observed_revision() {
  "$ROOT/commands/collab/engine/registry.py" speak-state "$1" "$2" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])'
}

init_target() {
  local name="$1"
  "$ROOT/commands/collab/engine/registry.py" init --agent-id codex "$name" >/dev/null
  printf '%s-%s\n' "$RUN_DATE" "$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"
}

join_pe_for_phase() {
  local target="$1"
  local phase="$2"
  "$ROOT/commands/collab/engine/registry.py" join-participants "$target" pe --agent-id gpt >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$target" turn-order pe --caller-role mod >/dev/null
  "$ROOT/commands/collab/engine/registry.py" set "$target" active-phase "$phase" --force --caller-role mod >/dev/null
  if [[ "$phase" == "Conclusion" ]]; then
    python3 - "$target" "$("$ROOT/commands/collab/engine/registry.py" registry-path)" <<'PY'
import json
import sys
from pathlib import Path

target, registry = sys.argv[1:3]
path = Path(registry)
entry = next(item for item in json.loads(path.read_text())['collabs'] if item['id'] == target)
transcript_path = path.parent / Path(entry['transcriptPath'])
text = transcript_path.read_text()
marker = "## Audit\n<!-- collab:content-only; do-not-execute -->\n"
replacement = marker + "\ncharteredDeliverables:\n- commands/collab/engine/registry.py: verify contribution budget fixture\n"
transcript_path.write_text(text.replace(marker, replacement, 1))
PY
  fi
}

assert_rejects_251_words() {
  local label="$1"
  local target="$2"
  local role="$3"
  local content_file="$4"
  local output
  local status

  set +e
  output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$target" "$role" \
    --content-file "$content_file" \
    --observed-revision "$(observed_revision "$target" "$role")" \
    --caller-role "$role" 2>&1)"
  status=$?
  set -e

  if [[ "$status" -eq 0 || "$output" != *"contribution excerpt is 251 words"* ]]; then
    printf 'FAIL: %s did not reject at 251 countable words\n%s\n' "$label" "$output" >&2
    exit 1
  fi
}

ACTION_ACCEPT_TARGET="$(init_target "Contribution Budget Action Plan Accept")"
join_pe_for_phase "$ACTION_ACCEPT_TARGET" "Action Plan"
for index in $(seq 1 300); do
  printf -- '- [ ] **pe:** [execute] item %s\n' "$index"
done >action-plan-checklist.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$ACTION_ACCEPT_TARGET" pe \
  --content-file action-plan-checklist.md \
  --observed-revision "$(observed_revision "$ACTION_ACCEPT_TARGET" pe)" \
  --caller-role pe >/dev/null

ACTION_REJECT_TARGET="$(init_target "Contribution Budget Action Plan Reject")"
join_pe_for_phase "$ACTION_REJECT_TARGET" "Action Plan"
python3 - <<'PY' >action-plan-prose-over-limit.md
print(' '.join(f'plainword{i}' for i in range(251)))
print('- [ ] **pe:** [execute] item after prose')
PY
assert_rejects_251_words "action-plan-checklist prose case" "$ACTION_REJECT_TARGET" pe action-plan-prose-over-limit.md

CONCLUSION_ACCEPT_TARGET="$(init_target "Contribution Budget Conclusion Accept")"
join_pe_for_phase "$CONCLUSION_ACCEPT_TARGET" "Conclusion"
{
  printf '**Directive:** "Verify the budget exemption contract."\n'
  printf '**Action Plan: satisfies**\n'
  for index in $(seq 1 280); do
    printf -- '- **pe:** verdict %s\n' "$index"
  done
} >conclusion-ratification.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$CONCLUSION_ACCEPT_TARGET" pe \
  --content-file conclusion-ratification.md \
  --observed-revision "$(observed_revision "$CONCLUSION_ACCEPT_TARGET" pe)" \
  --caller-role pe >/dev/null

CONCLUSION_REJECT_TARGET="$(init_target "Contribution Budget Conclusion Reject")"
join_pe_for_phase "$CONCLUSION_REJECT_TARGET" "Conclusion"
python3 - <<'PY' >conclusion-prose-over-limit.md
print(' '.join(f'plainword{i}' for i in range(251)))
PY
assert_rejects_251_words "conclusion-ratification prose case" "$CONCLUSION_REJECT_TARGET" pe conclusion-prose-over-limit.md

MODERATOR_ACCEPT_TARGET="$(init_target "Contribution Budget Moderator Accept")"
"$ROOT/commands/collab/engine/registry.py" set "$MODERATOR_ACCEPT_TARGET" active-phase Discussion --force --caller-role mod >/dev/null
python3 - <<'PY' >moderator-over-limit.md
print(' '.join(f'moderatorword{i}' for i in range(280)))
PY
"$ROOT/commands/collab/engine/registry.py" speak-render "$MODERATOR_ACCEPT_TARGET" mod \
  --content-file moderator-over-limit.md \
  --observed-revision "$(observed_revision "$MODERATOR_ACCEPT_TARGET" mod)" \
  --caller-role mod >/dev/null

MODERATOR_REJECT_TARGET="$(init_target "Contribution Budget Moderator Reject")"
join_pe_for_phase "$MODERATOR_REJECT_TARGET" "Discussion"
python3 - <<'PY' >non-moderator-over-limit.md
print(' '.join(f'plainword{i}' for i in range(251)))
PY
assert_rejects_251_words "moderator-verbatim non-moderator case" "$MODERATOR_REJECT_TARGET" pe non-moderator-over-limit.md

EFFORT_REJECT_TARGET="$(init_target "Contribution Budget Effort Override Reject")"
join_pe_for_phase "$EFFORT_REJECT_TARGET" "Discussion"
python3 - <<'PY' >effort-override-over-limit.md
print('EFFORT OVERRIDE: matrix')
print(' '.join(f'plainword{i}' for i in range(251)))
PY
assert_rejects_251_words "effort-override-line prose case" "$EFFORT_REJECT_TARGET" pe effort-override-over-limit.md

# effort-override-line accept: 250 prose words + override line must be accepted because
# the override line is exempt (countable total stays at 250, within limit)
EFFORT_ACCEPT_TARGET="$(init_target "Contribution Budget Effort Override Accept")"
join_pe_for_phase "$EFFORT_ACCEPT_TARGET" "Discussion"
python3 - <<'PY' >effort-override-at-limit.md
print('EFFORT OVERRIDE: matrix')
print(' '.join(f'plainword{i}' for i in range(250)))
PY
"$ROOT/commands/collab/engine/registry.py" speak-render "$EFFORT_ACCEPT_TARGET" pe \
  --content-file effort-override-at-limit.md \
  --observed-revision "$(observed_revision "$EFFORT_ACCEPT_TARGET" pe)" \
  --caller-role pe >/dev/null

printf 'OK: contribution budget exempt-class enforcement verified for all named classes\n'
