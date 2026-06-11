#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="${RUN_DATE}-action-plan-shape-gate"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Action Plan Shape Gate" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
TRANSCRIPT="$(python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
target = sys.argv[2]
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['id'] == target)
print(registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md"))
PY
)"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase "Action Plan" --force --caller-role mod >/dev/null

registry_value() {
  python3 -c "import json,sys; data=json.load(open('$REGISTRY')); entry=next(item for item in data['collabs'] if item['id'] == '$TARGET'); print($1)"
}

revision() {
  python3 -c "import json; print(json.load(open('$REGISTRY'))['revision'])"
}

run_rejected_case() {
  local label="$1"
  local content_file="$2"
  local expected="$3"
  local state
  local observed_revision
  local phase_before
  local phase_after
  local revision_before
  local revision_after
  local output
  local status

  state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe)"
  observed_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"
  phase_before="$(registry_value "entry['activePhase']")"
  revision_before="$(revision)"
  cp "$TRANSCRIPT" "before-${label}.md"

  set +e
  output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" pe --content-file "$content_file" --observed-revision "$observed_revision" --caller-role pe 2>&1)"
  status=$?
  set -e

  if [[ "$status" -eq 0 ]]; then
    printf 'FAIL: speak-render accepted invalid Action Plan body for %s\n' "$label" >&2
    exit 1
  fi

  if [[ "$output" != "$expected" ]]; then
    printf 'FAIL: Action Plan shape ABORT mismatch for %s\nexpected: %s\nactual: %s\n' "$label" "$expected" "$output" >&2
    exit 1
  fi

  cmp "$TRANSCRIPT" "before-${label}.md"

  phase_after="$(registry_value "entry['activePhase']")"
  if [[ "$phase_after" != "$phase_before" ]]; then
    printf 'FAIL: registry phase changed for %s: %s -> %s\n' "$label" "$phase_before" "$phase_after" >&2
    exit 1
  fi

  revision_after="$(revision)"
  if [[ "$revision_after" != "$revision_before" ]]; then
    printf 'FAIL: registry revision changed for %s: %s -> %s\n' "$label" "$revision_before" "$revision_after" >&2
    exit 1
  fi
}

cat >prose-header.md <<'PROSE'
Implementation notes
- [ ] **pe:** [execute] Add the validator.
PROSE

run_rejected_case \
  "prose-header" \
  prose-header.md \
  "ABORT: line 1 does not match Action Plan shape '- [ ] **<role>:** ...' (Invariant #9, invariants.md). Offending line: 'Implementation notes'. Example: '- [ ] **tw:** Update the route doc.'"

cat >plain-bullet.md <<'PLAIN'
- [ ] Implement the helper.
PLAIN

run_rejected_case \
  "plain-bullet" \
  plain-bullet.md \
  "ABORT: line 1 does not match Action Plan shape '- [ ] **<role>:** ...' (Invariant #9, invariants.md). Offending line: '- [ ] Implement the helper.'. Example: '- [ ] **tw:** Update the route doc.'"

cat >empty-after-exempts.md <<'EMPTY'
EFFORT OVERRIDE: matrix

<!-- hidden note
still hidden -->
### Assignments
EMPTY

run_rejected_case \
  "empty-after-exempts" \
  empty-after-exempts.md \
  "ABORT: Action Plan body contains no assignment lines after exempt content is removed (Invariant #9, invariants.md). Example: '- [ ] **tw:** Update the route doc.'"

cat >missing-tag.md <<'MISSINGTAG'
- [ ] **pe:** Add the validator.
MISSINGTAG

run_rejected_case \
  "missing-tag" \
  missing-tag.md \
  "ABORT: line 1 missing recognized Action Plan item tag; loop target: Action Plan for missing executable scope. Expected one of: [execute], [doc-fix], [verify], [precondition], [verify-precondition], [verify-objective]. Offending line: '- [ ] **pe:** Add the validator.'."

cat >defer-tag.md <<'DEFER'
- [ ] **pe:** [defer] Move this to a later collab.
DEFER

run_rejected_case \
  "defer-tag" \
  defer-tag.md \
  "ABORT: line 1 missing recognized Action Plan item tag; loop target: Action Plan for missing executable scope. Expected one of: [execute], [doc-fix], [verify], [precondition], [verify-precondition], [verify-objective]. Offending line: '- [ ] **pe:** [defer] Move this to a later collab.'."

cat >precondition-only.md <<'PRECONDITION'
- [ ] **pe:** [precondition] Confirm the workspace is clean.
- [ ] **pe:** [doc-fix] Update the note.
- [ ] **pe:** [verify-precondition] Confirm the note exists.
PRECONDITION

run_rejected_case \
  "precondition-only" \
  precondition-only.md \
  "ABORT: action-plan advance blocked: missing [execute] item for execution directive; loop target: Action Plan for missing executable scope."

cat >execute-item.md <<'EXECUTE'
- [ ] **pe:** [execute] Add runtime item-kind enforcement for the directive.
EXECUTE

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe)"
observed_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"
"$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" pe --content-file execute-item.md --observed-revision "$observed_revision" --caller-role pe >/dev/null
phase_after="$(registry_value "entry['activePhase']")"
if [[ "$phase_after" != "Handoff" ]]; then
  printf 'FAIL: Action Plan with [execute] item did not advance to Handoff: %s\n' "$phase_after" >&2
  exit 1
fi

printf 'OK: speak-render rejects malformed Action Plan checklist shapes and terminal non-execute plans before mutation\n'
