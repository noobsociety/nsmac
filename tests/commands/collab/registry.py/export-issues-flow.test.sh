#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-export-issues-flow"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --terminal issue --work-repo "$ROOT" "Export Issues Flow" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null

cat >bad.json <<'JSON'
{"issues":[]}
JSON

set +e
bad_output="$("$ROOT/commands/collab/engine/registry.py" export-issues "$TARGET" pe --evidence-file bad.json --caller-role pe 2>&1)"
bad_status=$?
set -e
if [[ "$bad_status" -eq 0 || "$bad_output" != *"issue export evidence requires a non-empty issues list"* ]]; then
  printf 'FAIL: export-issues accepted empty issue evidence\n%s\n' "$bad_output" >&2
  exit 1
fi

cat >issues.json <<'JSON'
{
  "issues": [
    {
      "title": "Implement issue terminal close gate",
      "body": "/git issue implement\n\nrequirements:\n- Preserve exported issue evidence",
      "owner": "pe",
      "delivery": "prefill",
      "requires": ["#1"]
    }
  ]
}
JSON

set +e
pending_output="$("$ROOT/commands/collab/engine/registry.py" export-issues "$TARGET" pe --evidence-file issues.json --caller-role pe 2>&1)"
pending_status=$?
set -e
if [[ "$pending_status" -eq 0 || "$pending_output" != *"issue export blocked: pending execution role(s) remain"* ]]; then
  printf 'FAIL: export-issues did not block before execution completed\n%s\n' "$pending_output" >&2
  exit 1
fi

"$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-06-08T12:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path commands/collab/engine/registry.py \
  --caller-role pe >/dev/null

output="$("$ROOT/commands/collab/engine/registry.py" export-issues "$TARGET" pe --evidence-file issues.json --caller-role pe)"
if [[ "$output" != *"closed"* || "$output" != *"NOTICE: Run /clear before starting another collab."* ]]; then
  printf 'FAIL: export-issues did not close after evidence was recorded\n%s\n' "$output" >&2
  exit 1
fi

REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path

registry = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(registry.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
assert entry['status'] == 'closed', entry
assert data['activeCollabId'] is None, data
assert entry['exportedIssues']['exportedBy'] == 'pe', entry['exportedIssues']
assert entry['exportedIssues']['issues'][0]['title'] == 'Implement issue terminal close gate'
assert entry['exportedIssues']['issues'][0]['requires'] == ['#1']
assert 'verificationSeal' not in entry, entry
PY

printf 'OK: export-issues validates evidence, blocks pending execution, records handoff evidence, and closes issue-terminal collabs\n'
