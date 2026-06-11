#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

python3 - "$ROOT" "$TMPDIR" <<'PY'
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
tmp = Path(sys.argv[2])
roles = tmp / 'roles'
projectors = tmp / 'projectors'
records = tmp / 'records'
roles.mkdir()
projectors.mkdir()
records.mkdir()

(roles / 'mod.json').write_text(json.dumps({
    'key': 'mod',
    'displayName': 'Moderator',
    'concerns': ['coordination'],
}) + '\n')
(projectors / 'dp.json').write_text(json.dumps({
    'key': 'dp',
    'displayName': 'Deterministic Projector',
    'concerns': ['traceability'],
}) + '\n')

registry_path = tmp / 'registry.json'
target = '2026-06-11-projector-boundary'
registry = {
    'revision': 1,
    'activeCollabId': target,
    'collabs': [{
        'id': target,
        'slug': 'projector-boundary',
        'title': 'Projector Boundary',
        'description': 'Projector boundary',
        'status': 'open',
        'activePhase': 'Audit',
        'moderatorRole': 'mod',
        'participants': [
            {'role': 'mod', 'agentId': 'codex'},
            {'role': 'dp', 'agentId': 'gemini-cli'},
        ],
        'turnOrder': ['dp'],
        'transcriptPath': f'records/{target}.md',
        'archived': False,
    }],
}
registry_path.write_text(json.dumps(registry, indent=2) + '\n')
(records / f'{target}-raw.md').write_text('# Projector Boundary\n')

sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('registry_under_test', root / 'commands/collab/engine/registry.py')
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
module.DEFAULT_ROLES_DIR = roles
module.DEFAULT_PROJECTORS_DIR = projectors

module.validate_registry(registry, registry_path)

roles_output = subprocess.run(
    [sys.executable, str(root / 'platform/tooling/roles.py'), '--roles-dir', str(roles), 'roles'],
    check=True,
    text=True,
    stdout=subprocess.PIPE,
).stdout
assert ' dp ' not in roles_output, roles_output
assert 'Deterministic Projector' not in roles_output, roles_output

try:
    module.join_participants(registry_path, target, 'dp', 'gemini-cli', roles)
except SystemExit as exc:
    assert f'role missing: {roles / "dp.json"}' in str(exc), str(exc)
else:
    raise AssertionError('projector metadata was accepted as a joinable role')

from commands.collab.engine.transcript_render import rendered_participants_table

rendered = rendered_participants_table(registry['collabs'][0], roles)
assert '| 2 | dp | Deterministic Projector | gemini-cli | traceability |' in rendered, rendered
PY

printf 'OK: projector metadata remains nonjoinable while historical participants render\n'
