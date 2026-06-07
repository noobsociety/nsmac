#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import json
import sys
import tempfile
from pathlib import Path

root = sys.argv[1]
sys.path.insert(0, root)

from commands.collab.engine import registry_io as r


def aborts(fn, contains):
    try:
        fn()
    except SystemExit as exc:
        assert contains in str(exc), str(exc)
    else:
        raise AssertionError(f'expected abort containing {contains!r}')


r.REGISTRY_VALIDATOR = None
aborts(lambda: r._validate_registry({}, None), 'validator not configured')

validator_calls = []


def validator(data, path):
    assert isinstance(data, dict)
    assert isinstance(data.get('collabs'), list)
    assert 'registryRevision' not in data
    validator_calls.append(None if path is None else Path(path).name)


r.configure_registry_io(validator)

with tempfile.TemporaryDirectory() as tmp:
    registry = Path(tmp) / 'registry.json'
    collab_id = '2026-06-04-unit-test'
    data = {
        'activeCollabId': collab_id,
        'registryRevision': 9,
        'collabs': [
            {
                'id': collab_id,
                'slug': 'unit-test',
                'sequence': 1,
            }
        ],
    }

    r.save_registry(registry, data)
    saved = json.loads(registry.read_text())
    assert saved['revision'] == 1
    assert saved['eventIndex'] == 1
    assert 'registryRevision' not in saved
    assert validator_calls[-1] == 'registry.json'

    loaded = r.load_registry(registry)
    assert loaded['activeCollabId'] == collab_id
    assert r.resolve_collab(loaded, collab_id)['slug'] == 'unit-test'
    assert r.resolve_collab(loaded, 'unit-test')['id'] == collab_id
    assert r.resolve_collab(loaded, '#1')['id'] == collab_id
    assert r.require_active_collab(loaded)['id'] == collab_id

    events = r.read_revision_events(registry, collab_id)
    assert events[0]['eventType'] == 'registry-write'
    assert events[0]['eventIndex'] == 1
    assert r.read_revision_events(registry, 'missing')[0]['eventType'] == 'legacy-baseline'

    assert r.registry_revision(saved) == 1
    assert r.registry_event_index(saved) == 1
    before = dict(saved, revision=999, eventIndex=999)
    assert not r.registry_has_semantic_change(before, saved)
    after = dict(saved, activeCollabId=None)
    assert r.registry_has_semantic_change(saved, after)

    bootstrap = r.load_registry_or_bootstrap(Path(tmp) / 'missing.json')
    assert bootstrap['activeCollabId'] is None
    assert bootstrap['collabs'] == []

    with r.registry_lock(registry):
        assert registry.with_name('registry.json.lock').exists()

    invalid = Path(tmp) / 'invalid.json'
    invalid.write_text('{not-json')
    aborts(lambda: r.load_registry(invalid), 'registry invalid JSON')

print('OK: registry_io module is directly exercised')
PY
