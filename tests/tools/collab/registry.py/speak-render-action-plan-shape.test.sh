#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="${RUN_DATE}-action-plan-shape-gate"

"$ROOT/tools/collab/registry.py" init --agent-id codex "Action Plan Shape Gate" >/dev/null
REGISTRY="$("$ROOT/tools/collab/registry.py" registry-path)"
TRANSCRIPT="$(python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
target = sys.argv[2]
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['id'] == target)
print(registry.parent / entry['transcriptPath'])
PY
)"
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pe --agent-id gpt >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase "Action Plan" --force --caller-role mod >/dev/null

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

  state="$("$ROOT/tools/collab/registry.py" speak-state "$TARGET" pe)"
  observed_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"
  phase_before="$(registry_value "entry['activePhase']")"
  revision_before="$(revision)"
  cp "$TRANSCRIPT" "before-${label}.md"

  set +e
  output="$("$ROOT/tools/collab/registry.py" speak-render "$TARGET" pe --content-file "$content_file" --observed-revision "$observed_revision" --caller-role pe 2>&1)"
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
- [ ] **pe:** Add the validator.
PROSE

run_rejected_case \
  "prose-header" \
  prose-header.md \
  "ABORT: line 1 does not match Action Plan shape '- [ ] **<role>:** ...' (Invariant #9, _invariants.md). Offending line: 'Implementation notes'. Example: '- [ ] **tw:** Update the route doc.'"

cat >plain-bullet.md <<'PLAIN'
- [ ] Implement the helper.
PLAIN

run_rejected_case \
  "plain-bullet" \
  plain-bullet.md \
  "ABORT: line 1 does not match Action Plan shape '- [ ] **<role>:** ...' (Invariant #9, _invariants.md). Offending line: '- [ ] Implement the helper.'. Example: '- [ ] **tw:** Update the route doc.'"

cat >empty-after-exempts.md <<'EMPTY'
EFFORT OVERRIDE: matrix

<!-- hidden note
still hidden -->
### Assignments
EMPTY

run_rejected_case \
  "empty-after-exempts" \
  empty-after-exempts.md \
  "ABORT: Action Plan body contains no assignment lines after exempt content is removed (Invariant #9, _invariants.md). Example: '- [ ] **tw:** Update the route doc.'"

printf 'OK: speak-render rejects malformed Action Plan checklist shapes before mutation\n'
