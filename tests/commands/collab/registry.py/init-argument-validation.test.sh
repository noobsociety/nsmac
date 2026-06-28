#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

set +e
missing_name_output="$("$ROOT/commands/collab/engine/registry.py" init --agent-id codex 2>&1)"
missing_name_status=$?
set -e
if [[ "$missing_name_status" -eq 0 || "$missing_name_output" != *'<name> is required'* ]]; then
  printf 'FAIL: init accepted a missing name\n%s\n' "$missing_name_output" >&2
  exit 1
fi

set +e
bad_reviewer_output="$("$ROOT/commands/collab/engine/registry.py" init --agent-id codex --reviewer bad-role "Argument Validation" 2>&1)"
bad_reviewer_status=$?
set -e
if [[ "$bad_reviewer_status" -eq 0 || "$bad_reviewer_output" != *'--reviewer requires a role key'* ]]; then
  printf 'FAIL: init accepted an invalid reviewer value\n%s\n' "$bad_reviewer_output" >&2
  exit 1
fi

set +e
old_opt_in_output="$("$ROOT/commands/collab/engine/registry.py" init --agent-id codex --participant-verification "Argument Validation" 2>&1)"
old_opt_in_status=$?
set -e
if [[ "$old_opt_in_status" -eq 0 || "$old_opt_in_output" != *'unknown flag: --participant-verification'* ]]; then
  printf 'FAIL: init accepted retired --participant-verification flag\n%s\n' "$old_opt_in_output" >&2
  exit 1
fi

set +e
retired_cap_output="$("$ROOT/commands/collab/engine/registry.py" init --agent-id codex --verification-cap 2 "Argument Validation" 2>&1)"
retired_cap_status=$?
set -e
if [[ "$retired_cap_status" -eq 0 || "$retired_cap_output" != *'unknown flag: --verification-cap'* ]]; then
  printf 'FAIL: init accepted retired --verification-cap flag\n%s\n' "$retired_cap_output" >&2
  exit 1
fi

set +e
preview_output="$($ROOT/commands/collab/engine/registry.py init --agent-id codex --preview "Argument Validation" 2>&1)"
preview_status=$?
set -e
if [[ "$preview_status" -eq 0 || "$preview_output" != *'unknown flag: --preview'* ]]; then
  printf 'FAIL: init accepted retired --preview flag
%s
' "$preview_output" >&2
  exit 1
fi

init_help="$($ROOT/commands/collab/engine/registry.py init --help 2>&1)"
if [[ "$init_help" != *'--open'* || "$init_help" == *'--preview'* ]]; then
  printf 'FAIL: init help does not expose only --open
%s
' "$init_help" >&2
  exit 1
fi

set +e
none_terminal_output="$("$ROOT/commands/collab/engine/registry.py" init --agent-id codex --terminal none "None Terminal" 2>&1)"
none_terminal_status=$?
set -e
if [[ "$none_terminal_status" -eq 0 || "$none_terminal_output" != *'--terminal requires one of: seal, issue'* ]]; then
  printf 'FAIL: init accepted removed --terminal none value\n%s\n' "$none_terminal_output" >&2
  exit 1
fi

issue_terminal_output="$("$ROOT/commands/collab/engine/registry.py" init --agent-id codex --terminal issue "Issue Terminal" 2>&1)"
if [[ "$issue_terminal_output" != records/*issue-terminal.md || "$issue_terminal_output" == *-raw.md* ]]; then
  printf 'FAIL: init did not report an issue-terminal moderator project transcript\n%s\n' "$issue_terminal_output" >&2
  exit 1
fi

set +e
slug_empty_output="$("$ROOT/commands/collab/engine/registry.py" init --agent-id codex "!!!" 2>&1)"
slug_empty_status=$?
set -e
if [[ "$slug_empty_status" -eq 0 || "$slug_empty_output" != *'slug is empty'* ]]; then
  printf 'FAIL: init accepted an empty slug\n%s\n' "$slug_empty_output" >&2
  exit 1
fi

default_output="$("$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Default Seal" 2>&1)"
if [[ "$default_output" != records/*default-seal.md || "$default_output" == *-raw.md* ]]; then
  printf 'FAIL: init did not report a default-seal moderator project transcript\n%s\n' "$default_output" >&2
  exit 1
fi

python3 - "$COLLAB_STATE_HOME" "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

state_home = Path(sys.argv[1])
sys.path.insert(0, sys.argv[2])
from commands.collab.engine.contribution_store import contribution_store_path_for_entry

registries = list(state_home.glob('*/registry.json'))
assert len(registries) == 1, registries
data = json.loads(registries[0].read_text())
entry = next(item for item in data['collabs'] if item['slug'] == 'default-seal')
assert entry['terminal'] == 'seal', entry
projection = registries[0].parent / entry['transcriptPath']
store = contribution_store_path_for_entry(registries[0], entry)
assert projection.exists(), projection
assert store.exists(), store
issue = next(item for item in data['collabs'] if item['slug'] == 'issue-terminal')
assert issue['terminal'] == 'issue', issue
issue_projection = registries[0].parent / issue['transcriptPath']
assert issue_projection.exists(), issue_projection
assert contribution_store_path_for_entry(registries[0], issue).exists()
assert 'verificationSeal' not in issue, issue
assert 'verification' not in issue, issue
PY

python3 - "$ROOT" <<'PY'
import importlib.util
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
constants_path = root / 'commands/collab/engine/registry_constants.py'
spec = importlib.util.spec_from_file_location('registry_constants', constants_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if 'issue' not in module.ALLOWED_TERMINALS:
    raise SystemExit(0)

paths = [
    root / 'commands/collab/reference/workflow-models.md',
    root / 'commands/collab/init/index.md',
    root / 'commands/collab/reference/glossary.md',
]
bad = re.compile(r'reserved|not yet implemented|hard[- ]?aborts?|hard[- ]?aborting', re.I)
issue = re.compile(r'--terminal\s+issue|terminal\s+issue|issue\s+terminal|issue\s+workflow|`issue`', re.I)

failures = []
for path in paths:
    lines = path.read_text().splitlines()
    for index, line in enumerate(lines):
        if not bad.search(line):
            continue
        window = '\n'.join(lines[max(0, index - 2): index + 3])
        if issue.search(window):
            failures.append(f'{path.relative_to(root)}:{index + 1}: {line}')

if failures:
    raise SystemExit(
        'issue terminal is active but docs still describe it as reserved or hard-aborting:\n'
        + '\n'.join(failures)
    )
PY

python3 - "$ROOT" <<'INNER_PY'
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from commands.collab.engine import registry as module

parsed = module.parse_init_tokens(['--agent-id', 'codex', '--open', 'Quoted Title'])
assert parsed[0] == 'Quoted Title', parsed
assert parsed[3] is True, parsed

quoted = module.parse_init_tokens(['--agent-id', 'codex', 'Route UX Cleanup'])
assert quoted[0] == 'Route UX Cleanup', quoted

try:
    module.parse_init_tokens(['--agent-id', 'codex', 'Route', 'UX'])
except SystemExit as exc:
    assert 'unknown positional argument: UX' in str(exc), str(exc)
else:
    raise AssertionError('unquoted trailing positional was accepted')

help_text = (Path(sys.argv[1]) / 'commands/collab/reference/init-helper-spec.md').read_text()
documented_flags = set()
for line in help_text.splitlines():
    if line.startswith('- Required: `') or line.startswith('- Optional: `'):
        documented_flags.add(line.split('`', 2)[1].split()[0])
expected = {
    '--agent-id',
    '--reviewer',
    '--terminal',
    '--no-participant-verification',
    '--work-repo',
    '--open',
}
assert documented_flags == expected, documented_flags
INNER_PY

printf 'OK: init argument validation rejects missing names, invalid reviewer values, retired verification flags, retired preview flag, invalid terminal selectors, and empty slugs; default terminal is seal and issue terminal initializes without seal state\n'
