#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa "Seal Verification Paired Round Records" >/dev/null
TARGET="$RUN_DATE-seal-verification-paired-round-records"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
REGISTRY="$(registry_path)"
seed_handoff_scope "seal-verification-paired-round-records"
complete_execution "$TARGET"

state="$("$ROOT/commands/collab/engine/registry.py" participant-verify-state "$TARGET" pe)"
revision="$(read_json_field registryRevision <<<"$state")"

AUDIT_FILE="$TMPDIR/audit.txt"
REMEDIATION_FILE="$TMPDIR/remediation.txt"
FINAL_AUDIT_FILE="$TMPDIR/final-audit.txt"
printf 'audit clean\n' > "$AUDIT_FILE"
printf 'no remediation needed\n' > "$REMEDIATION_FILE"
printf 'final audit clean\n' > "$FINAL_AUDIT_FILE"

"$ROOT/commands/collab/engine/registry.py" participant-verify-render "$TARGET" pe \
  --observed-revision "$revision" \
  --audit-file "$AUDIT_FILE" \
  --remediation-file "$REMEDIATION_FILE" \
  --final-audit-file "$FINAL_AUDIT_FILE" \
  --status completed \
  --touched-path platform/tooling/audit.sh \
  --execution-agent-id codex \
  --audit-agent-id codex \
  --remediation-agent-id codex \
  --caller-role pe >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(
    item
    for item in json.loads(Path(sys.argv[1]).read_text())['collabs']
    if item['slug'] == 'seal-verification-paired-round-records'
)
verification = entry['verification']
assert verification['subState'] == 'seal', verification
assert verification['rounds'] == 1, verification
assert verification['pairedExecutionSignature'], verification
assert 'verificationSeal' not in entry, entry
PY

seal_state="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa)"
seal_revision="$(read_json_field registryRevision <<<"$seal_state")"
rounds="$(read_json_field verificationRounds <<<"$seal_state")"
if [[ "$rounds" != "1" ]]; then
  printf 'FAIL: seal-state did not expose one paired verification round\n%s\n' "$seal_state" >&2
  exit 1
fi

"$ROOT/commands/collab/engine/registry.py" seal-render "$TARGET" pa --observed-revision "$seal_revision" --caller-role pa >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
entry = next(
    item
    for item in json.loads(registry.read_text())['collabs']
    if item['slug'] == 'seal-verification-paired-round-records'
)
transcript = (registry.parent / entry['transcriptPath']).read_text()
verification = entry['verification']
assert verification['rounds'] == 1, verification
assert verification['pairedExecutionSignature'] == entry['verificationSeal']['executionSignature']
assert entry['verificationSeal']['sealedBy'] == 'pa', entry['verificationSeal']
assert entry['verificationSeal']['stale'] is False, entry['verificationSeal']
assert '**pa:** sealed' in transcript, transcript
PY

printf 'OK: completed participant verification records one paired round and permits sealing\n'
