#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

export COLLAB_STATE_HOME="$TMPDIR/state-home"

PROJECT="$TMPDIR/project"
mkdir -p "$PROJECT"
git -C "$PROJECT" init -q
git -C "$PROJECT" config user.email tester@example.com
git -C "$PROJECT" config user.name tester
printf 'tracked\n' >"$PROJECT/tracked.txt"
git -C "$PROJECT" add tracked.txt
git -C "$PROJECT" -c commit.gpgsign=false commit -qm 'seed'

cd "$PROJECT"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Work Repo Auto Binding" >/dev/null
registry="$("$ROOT/commands/collab/engine/registry.py" registry-path)"

python3 - "$registry" "$PROJECT" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

registry, project = sys.argv[1:3]
data = json.loads(Path(registry).read_text())
entry = data['collabs'][0]
expected = subprocess.check_output(
    ['git', '-C', project, 'rev-parse', '--show-toplevel'],
    text=True,
).strip()
assert entry['workRepo'] == expected, entry
del entry['workRepo']
entry['activePhase'] = 'Completion'
entry['participants'].append({'role': 'pe', 'agentId': 'codex'})
entry['turnOrder'] = ['pe']
Path(registry).write_text(json.dumps(data, indent=2) + '\n')
PY

set +e
output="$("$ROOT/commands/collab/engine/registry.py" execution "$(date +%Y-%m-%d)-work-repo-auto-binding" pe completed "2026-06-02T12:00:00+00:00" --assigned-role pe --validation-result passed --validation-scope scoped --touched-path tracked.txt --caller-role pe 2>&1)"
status=$?
set -e

if [[ "$status" -eq 0 || "$output" != *"workRepo missing for external project"* ]]; then
  printf 'FAIL: legacy external record without workRepo did not fail loudly\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: init persists workRepo and legacy external records fail without a binding\n'
