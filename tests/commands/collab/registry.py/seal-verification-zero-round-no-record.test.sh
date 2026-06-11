#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

init_reviewer_target "Seal Verification Zero Round No Record" "seal-verification-zero-round-no-record"
TARGET="$RUN_DATE-seal-verification-zero-round-no-record"
REGISTRY="$(registry_path)"
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
complete_execution "$TARGET"

state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
revision="$(read_json_field registryRevision <<<"$state")"
rounds="$(read_json_field verificationRounds <<<"$state")"

if [[ "$rounds" != "0" ]]; then
  printf 'FAIL: seal-state should expose zero verification rounds before any seal attempt\n%s\n' "$state" >&2
  exit 1
fi

set +e
output="$("$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$revision" --caller-role pa 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"zero verification rounds; at least one reviewer-executor paired event is required before sealing"* ]]; then
  printf 'FAIL: seal-render accepted a zero-round first seal attempt\n%s\n' "$output" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(
    item
    for item in json.loads(registry.read_text())['collabs']
    if item['slug'] == 'seal-verification-zero-round-no-record'
)
transcript = (registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md")).read_text()

assert entry['status'] == 'open', entry
assert entry['activePhase'] == 'Completion', entry
assert entry['completion']['subState'] == 'verification', entry['completion']
assert entry['verification']['subState'] == 'seal', entry['verification']
assert entry['verification']['rounds'] == 0, entry['verification']
assert 'pairedExecutionSignature' not in entry['verification'], entry['verification']
assert 'verificationSeal' not in entry, entry
assert 'verdict' not in entry, entry
assert entry['terminal'] == 'seal', entry
assert 'terminalMode' not in entry, entry
assert 'workflowModel' not in entry, entry
assert '**pa:** sealed' not in transcript, transcript
PY

printf 'OK: zero-round seal-render abort records no verification round and no terminal-mode state\n'
