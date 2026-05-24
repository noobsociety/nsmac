#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

python3 - "$ROOT" "$TMPDIR" <<'PY'
import importlib.util
import json
import os
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

root = Path(sys.argv[1])
tmp = Path(sys.argv[2]) / 'issue-bridge-root'
init_tmp = Path(sys.argv[2]) / 'init-root'
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('registry_under_test', root / 'tools/collab/registry.py')
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

def write(rel: str, text: str) -> None:
    path = tmp / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

write('commands/collab/export-issues/index.md', '# /collab export-issues\n')
write('commands/collab/index.md', '# /collab\n')
write('commands/commands.md', '# /commands\n')
write(
    'core/collab/helper-output.md',
    '\n'.join([
        '## Abort families',
        'Each entry names the logical module.',
        'Full-body envelope rejection',
        'Paired-execution-signature double-increment guard',
        'seal-verification-archive-protocol-violation',
    ]),
)
write(
    'tests/tools/collab/registry.py/rebinding-invariants.test.sh',
    '\n'.join([
        '#!/usr/bin/env bash',
        '# projectId rebinding',
        '# agentId rebinding',
        '# issue bridge',
    ]),
)
write(
    'commands/git/issue/index.md',
    '\n'.join([
        '## Notes',
        '- **Output contract:** Issue delivery: prefill or connector-backed.',
        '- **Owner metadata:** Preserve Owner.',
        '- **`_requires:` preservation:** Keep `_requires:`.',
        '- **Implement handoff shape:** structured input.',
    ]),
)

try:
    module.validate_planned_route_prerequisites(tmp)
except SystemExit as exc:
    message = str(exc)
    assert message.startswith('workflow-model selection blocked: missing --terminal prerequisite(s): '), message
    assert 'init --terminal selector' in message, message
    assert 'init route-arg --terminal' in message, message
    assert 'registry terminal field' in message, message
    assert 'helper --terminal parser' in message, message
else:
    raise AssertionError('planned route gate accepted missing workflow-model selection contract')

write(
    'commands/collab/init/index.md',
    '\n'.join([
        '# /collab init',
        'Use --terminal seal|issue.',
        '```route-arg',
        'param: name=--terminal; values=seal|issue; default=seal',
        '```',
    ]),
)
write(
    'core/collab/registry.md',
    '\n'.join([
        '# /collab registry',
        '| `terminal` | string | Workflow-model terminal selector: seal|issue. |',
    ]),
)
write(
    'tools/collab/registry.py',
    '\n'.join([
        "ALLOWED_TERMINALS = {'seal', 'issue'}",
        "if token == '--terminal': pass",
        "entry = {'terminal': terminal}",
    ]),
)

(tmp / 'commands/git/issue/index.md').unlink()
try:
    module.validate_planned_route_prerequisites(tmp)
except SystemExit as exc:
    message = str(exc)
    assert 'third prerequisite: commands/git/issue/index.md (output contract)' in message, message
    assert 'issue output contract' in message, message
    assert 'issue owner metadata' in message, message
    assert 'issue requires preservation' in message, message
    assert 'issue implement handoff shape' in message, message
else:
    raise AssertionError('planned route gate accepted missing /git issue contract')

write(
    'commands/git/issue/index.md',
    '\n'.join([
        '## Notes',
        '- **Output contract:** Issue delivery: prefill or connector-backed.',
        '- **Owner metadata:** Preserve Owner.',
        '- **`_requires:` preservation:** Keep `_requires:`.',
        '- **Implement handoff shape:** structured input.',
    ]),
)
module.validate_planned_route_prerequisites(tmp)

assert module.parse_init_tokens(['--agent-id', 'codex', '--terminal', 'issue', 'Issue Terminal'])[5] == 'issue'
assert module.parse_init_tokens(['--agent-id', 'codex', '--terminal', 'seal', 'Seal Terminal'])[5] == 'seal'

try:
    module.parse_init_tokens(['--agent-id', 'codex', '--terminal', 'bad', 'Bad Terminal'])
except SystemExit as exc:
    assert str(exc) == '--terminal requires one of: seal, issue', exc
else:
    raise AssertionError('init accepted invalid terminal selector')

try:
    module.parse_init_tokens(['--agent-id', 'codex', '--terminal', 'none', 'None Terminal'])
except SystemExit as exc:
    assert str(exc) == '--terminal requires one of: seal, issue', exc
else:
    raise AssertionError('init accepted removed terminal selector')

init_tmp.mkdir(parents=True)
old_cwd = Path.cwd()
try:
    os.chdir(init_tmp)
    registry = init_tmp / 'registry.json'
    try:
        module.init_collab(registry, ['--agent-id', 'codex', '--terminal', 'issue', 'Issue Init'], root / 'core/collab/roles')
    except SystemExit as exc:
        assert str(exc) == '--terminal issue is reserved and not yet implemented; use --terminal seal or omit --terminal', exc
    else:
        raise AssertionError('init accepted reserved issue terminal selector')
    with redirect_stdout(StringIO()):
        module.init_collab(registry, ['--agent-id', 'codex', '--terminal', 'seal', 'Seal Init'], root / 'core/collab/roles')
        module.init_collab(registry, ['--agent-id', 'codex', 'Default Init'], root / 'core/collab/roles')
finally:
    os.chdir(old_cwd)

data = json.loads((init_tmp / 'registry.json').read_text())
by_slug = {entry['slug']: entry for entry in data['collabs']}
assert by_slug['seal-init']['terminal'] == 'seal', by_slug['seal-init']
assert by_slug['default-init']['terminal'] == 'seal', by_slug['default-init']
assert by_slug['seal-init']['createdAt'], by_slug['seal-init']
PY

printf 'OK: issue bridge planned-route prerequisite gate holds\n'
