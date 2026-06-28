#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-real-record-behavior-smoke"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Real Record Behavior Smoke" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null

REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
TRANSCRIPT="$(python3 - "$REGISTRY" "$TARGET" "$COLLAB_STATE_HOME" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
state_home = Path(sys.argv[3]).resolve()
if state_home not in registry.resolve().parents:
    raise SystemExit(f"registry escaped COLLAB_STATE_HOME: {registry}")
entry = next(item for item in json.loads(registry.read_text())["collabs"] if item["id"] == target)
transcript = registry.parent / Path(entry["transcriptPath"])
if state_home not in transcript.resolve().parents:
    raise SystemExit(f"transcript escaped COLLAB_STATE_HOME: {transcript}")
print(transcript)
PY
)"

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe --resume)"
observed_revision="$(STATE="$state" python3 - <<'PY'
import json
import os

state = json.loads(os.environ["STATE"])
assert state["freshRegistryRead"] is True, state
assert state["freshTranscriptRead"] is True, state
assert state["phaseSummary"]["activePhase"] == "Audit", state
assert state["expectedRole"] == "pe", state
assert state["readyToWrite"] is True, state
print(state["registryRevision"])
PY
)"

cat >audit.md <<'AUDIT'
<!-- collab:stance converges -->

Smoke-test contribution for real-record behavior.
AUDIT

render_output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" pe \
  --content-file audit.md \
  --observed-revision "$observed_revision" \
  --caller-role pe)"

if [[ "$render_output" != *"PHASE: Discussion"* ]]; then
  printf 'FAIL: speak-render did not report the Audit->Discussion lifecycle transition\n%s\n' "$render_output" >&2
  exit 1
fi

status_output="$("$ROOT/commands/collab/engine/registry.py" status-view "$TARGET")"
if [[ "$status_output" != *"activePhase:  Discussion"* ]]; then
  printf 'FAIL: status-view did not display Discussion after lifecycle transition\n%s\n' "$status_output" >&2
  exit 1
fi

audit_view="$("$ROOT/commands/collab/engine/registry.py" transcript-view "$TARGET" Audit --raw)"
if [[ "$audit_view" != *'audit-pe-1'* || "$audit_view" != *'Smoke-test contribution for real-record behavior.'* ]]; then
  printf 'FAIL: transcript-view did not display the rendered Audit contribution\n%s\n' "$audit_view" >&2
  exit 1
fi

assert_reconciled_discussion_round_trip() {
  local label="$1"
  local state
  state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe --resume)"
  STATE="$state" python3 - "$label" "$TRANSCRIPT" <<'PY'
import json
import os
import sys
from pathlib import Path

label, transcript = sys.argv[1:3]
state = json.loads(os.environ["STATE"])
text = Path(transcript).read_text()

assert state["freshRegistryRead"] is True, (label, state)
assert state["freshTranscriptRead"] is True, (label, state)
assert state["phaseSummary"]["activePhase"] == "Discussion", (label, state)
assert state["expectedRole"] == "pe", (label, state)
assert state["readyToWrite"] is True, (label, state)
assert state["contributors"] == [], (label, state)
assert '<a name="audit-pe-1"></a>' in text, label
assert "Smoke-test contribution for real-record behavior." in text, label
PY
}

assert_reconciled_discussion_round_trip "green-before-desync"

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data["collabs"] if item["id"] == target)
entry["activePhase"] = "Audit"
path.write_text(json.dumps(data, indent=2) + "\n")
PY

set +e
assert_reconciled_discussion_round_trip "red-desynchronized-phase-pointer" >red.out 2>red.err
red_status=$?
set -e

if [[ "$red_status" -eq 0 ]]; then
  printf 'FAIL: round-trip assertion stayed green after registry/transcript desynchronization\n' >&2
  exit 1
fi

python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data["collabs"] if item["id"] == target)
entry["activePhase"] = "Discussion"
path.write_text(json.dumps(data, indent=2) + "\n")
PY

assert_reconciled_discussion_round_trip "green-after-reconcile"

printf 'OK: real-record behavior smoke gate proves red/green speak-render to speak-state lifecycle reconciliation\n'
