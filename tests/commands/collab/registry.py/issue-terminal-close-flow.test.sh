#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-issue-terminal-close-flow"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer pa --terminal issue --work-repo "$ROOT" "Issue Terminal Close Flow" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null

execution_output="$("$ROOT/commands/collab/engine/registry.py" execution "$TARGET" pe completed "2026-06-08T12:10:00+02:00" \
  --assigned-role pe \
  --auto-close \
  --validation-result passed \
  --validation-scope scoped \
  --touched-path commands/collab/engine/registry.py \
  --caller-role pe)"

if [[ "$execution_output" != *"NEXT: Run /collab export-issues for role pe."* || "$execution_output" != *"open"* ]]; then
  printf 'FAIL: issue terminal execution did not route to export-issues while evidence was absent\n%s\n' "$execution_output" >&2
  exit 1
fi

set +e
close_output="$("$ROOT/commands/collab/engine/registry.py" close "$TARGET" --caller-role mod 2>&1)"
close_status=$?
set -e
if [[ "$close_status" -eq 0 || "$close_output" != *"close blocked: issue terminal requires exported issue handoff evidence"* ]]; then
  printf 'FAIL: issue terminal close did not require exported issue evidence\n%s\n' "$close_output" >&2
  exit 1
fi

set +e
seal_state_output="$("$ROOT/commands/collab/engine/registry.py" seal-state "$TARGET" pa 2>&1)"
seal_state_status=$?
set -e
if [[ "$seal_state_status" -eq 0 || "$seal_state_output" != *"seal verification is not used for issue-terminal collabs"* ]]; then
  printf 'FAIL: seal-state did not reject issue-terminal collab\n%s\n' "$seal_state_output" >&2
  exit 1
fi

cat >issues.json <<'JSON'
{"issues":[{"title":"Ship issue-terminal handoff","url":"https://example.invalid/issues/1"}]}
JSON

"$ROOT/commands/collab/engine/registry.py" export-issues "$TARGET" pe --evidence-file issues.json --caller-role pe >/dev/null

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
assert entry['terminal'] == 'issue', entry
assert entry['reviewerRole'] == 'pa', entry
assert 'verificationSeal' not in entry, entry
assert entry['exportedIssues']['issues'][0]['url'] == 'https://example.invalid/issues/1'
PY

printf 'OK: issue terminal close path uses exported issue evidence and does not wait on verificationSeal\n'
