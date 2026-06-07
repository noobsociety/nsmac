#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

python3 - "$ROOT" "$TMPDIR" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
tmp = Path(sys.argv[2])
roles = tmp / 'roles'
roles.mkdir()
(roles / 'mod.json').write_text(json.dumps({
    'key': 'mod',
    'displayName': 'Moderator',
    'concerns': ['coordination'],
}) + '\n')

sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('registry_under_test', root / 'commands/collab/engine/registry.py')
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
module.DEFAULT_ROLES_DIR = roles

registry = {
    'revision': 1,
    'activeCollabId': '2026-05-19-role-file-check',
    'collabs': [{
        'id': '2026-05-19-role-file-check',
        'slug': 'role-file-check',
        'title': 'Role File Check',
        'description': 'Role file check',
        'status': 'open',
        'activePhase': 'Audit',
        'moderatorRole': 'mod',
        'participants': [
            {'role': 'mod', 'agentId': 'codex'},
            {'role': 'ghost', 'agentId': 'codex'},
        ],
        'turnOrder': ['ghost'],
        'transcriptPath': 'records/2026-05-19-role-file-check.md',
        'archived': False,
    }],
}

try:
    module.validate_registry(registry, tmp / 'registry.json')
except SystemExit as exc:
    message = str(exc)
    assert 'participants role file unreadable for ghost' in message, message
    assert 'roles/ghost.json' in message, message
else:
    raise AssertionError('missing participant role file was accepted')
PY

printf 'OK: participant role-file readability is enforced\n'
