#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/verification-test-lib.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

python3 - "$ROOT/tools/collab/registry.py" "$ROOT/core/collab/verification.md" <<'PY'
import re
import sys
from pathlib import Path

constant_source = Path(sys.argv[1]).read_text()
doc_source = Path(sys.argv[2]).read_text()

constant_match = re.search(r'^DEFAULT_VERIFICATION_CAP = (\d+)$', constant_source, re.MULTILINE)
doc_match = re.search(
    r'A round cap is set at collab initialization \(default: (\d+)\)\.',
    doc_source,
)

assert constant_match, 'DEFAULT_VERIFICATION_CAP declaration missing'
assert doc_match, 'verification default-cap prose missing'
assert constant_match.group(1) == '3', constant_match.group(0)
assert doc_match.group(1) == '3', doc_match.group(0)
PY

"$ROOT/tools/collab/registry.py" init --agent-id codex --reviewer pa "Verification Cap Default" >/dev/null
TARGET="$RUN_DATE-verification-cap-default"
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
REGISTRY="$(registry_path)"
seed_handoff_scope "verification-cap-default"

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(
    item
    for item in json.loads(Path(sys.argv[1]).read_text())['collabs']
    if item['slug'] == 'verification-cap-default'
)
verification = entry['verification']
assert verification['cap'] == 3, verification
assert verification['rounds'] == 0, verification
assert verification['participantVerification'] is True, verification
assert verification['subState'] == 'participant', verification
PY

complete_execution "$TARGET"

participant_state="$("$ROOT/tools/collab/registry.py" participant-verify-state "$TARGET" pe)"
participant_revision="$(read_json_field registryRevision <<<"$participant_state")"

AUDIT_FILE="$TMPDIR/audit.txt"
REMEDIATION_FILE="$TMPDIR/remediation.txt"
FINAL_AUDIT_FILE="$TMPDIR/final-audit.txt"
printf 'audit clean\n' > "$AUDIT_FILE"
printf 'no remediation needed\n' > "$REMEDIATION_FILE"
printf 'final audit clean\n' > "$FINAL_AUDIT_FILE"

"$ROOT/tools/collab/registry.py" participant-verify-render "$TARGET" pe \
  --observed-revision "$participant_revision" \
  --audit-file "$AUDIT_FILE" \
  --remediation-file "$REMEDIATION_FILE" \
  --final-audit-file "$FINAL_AUDIT_FILE" \
  --status completed \
  --execution-agent-id codex \
  --audit-agent-id codex \
  --remediation-agent-id codex \
  --caller-role pe >/dev/null

seal_state="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa)"
seal_revision="$(read_json_field registryRevision <<<"$seal_state")"
rounds="$(read_json_field verificationRounds <<<"$seal_state")"
cap="$(read_json_field verificationCap <<<"$seal_state")"

if [[ "$rounds" != "1" || "$cap" != "3" ]]; then
  printf 'FAIL: default-cap seal state did not expose one paired round under cap 3\n%s\n' "$seal_state" >&2
  exit 1
fi

"$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$seal_revision" \
  --caller-role pa >/dev/null

python3 - "$REGISTRY" <<'PY'
import json
import sys
from pathlib import Path

entry = next(
    item
    for item in json.loads(Path(sys.argv[1]).read_text())['collabs']
    if item['slug'] == 'verification-cap-default'
)
assert entry['status'] == 'open', entry
assert entry['completion']['subState'] == 'verification', entry['completion']
assert entry['verification']['subState'] == 'assessment', entry['verification']
assert entry['verification']['cap'] == 3, entry['verification']
assert entry['verification']['rounds'] == 1, entry['verification']
assert entry['verification']['pairedExecutionSignature'] == entry['verificationSeal']['executionSignature']
assert entry['verificationSeal']['sealedBy'] == 'pa', entry['verificationSeal']
assert 'capExit' not in entry['verificationSeal'], entry['verificationSeal']
assert 'verdict' not in entry, entry
PY

printf 'OK: default verification cap is 3 and clean reviewer-backed verification reaches assessment without cap exit\n'
