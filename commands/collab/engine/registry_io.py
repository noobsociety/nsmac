"""Registry persistence, schema validation, lock, and resolve; does not own phase or lifecycle decisions."""
# Tests: registry load/save with lock serialization, revision bump and event management,
#        collab-id resolution (slug, id, numeric), bootstrap from absent registry,
#        semantic-change detection, legacy field retirement.
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import re
from collections.abc import Callable
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from commands.collab.engine.errors import die
from commands.collab.engine.registry_constants import (
    REGISTRY_EVENT_DIR,
    REGISTRY_EVENT_IGNORED_ROOT_KEYS,
    REGISTRY_EVENT_SCHEMA,
    RETIRED_ROOT_KEYS,
    STALE_LOCK_SECONDS,
)
from commands.collab.engine.registry_state import (
    assert_registry_project_binding,
    sync_registry_project_metadata,
)

ROOT = Path(__file__).resolve().parents[3]
CURRENT_REGISTRY_PROJECT: dict | None = None
REGISTRY_VALIDATOR: Callable[[dict, Path | None], None] | None = None


def configure_registry_io(validator: Callable[[dict, Path | None], None]) -> None:
    global REGISTRY_VALIDATOR
    REGISTRY_VALIDATOR = validator


def _validate_registry(data: dict, path: Path | None = None) -> None:
    if REGISTRY_VALIDATOR is None:
        die('registry validator not configured')
    REGISTRY_VALIDATOR(data, path)

def load_registry(path: Path) -> dict:
    if not path.exists():
        die(f'registry missing: {path}')
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f'registry invalid JSON: {path}: {exc}')
    retire_legacy_registry_fields(data)
    _validate_registry(data, path)
    assert_registry_project_binding(data, path)
    capture_registry_project(data)
    return data

def save_registry(path: Path, data: dict) -> None:
    registry_before = path.read_text() if path.exists() else None
    sync_registry_project_metadata(data)
    retire_legacy_registry_fields(data)
    registry_event = prepare_registry_event(path, registry_before, data, 'registry-write')
    bump_registry_revision(data)
    if registry_event is not None:
        bump_registry_event_index(data)
        registry_event = finalize_registry_event(data, registry_event)
    _validate_registry(data, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f'{path.name}.tmp')
    try:
        tmp_path.write_text(json.dumps(data, indent=2) + '\n')
        tmp_path.replace(path)
        if registry_event is not None:
            write_revision_event(path, registry_event)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise

def bump_registry_revision(data: dict) -> int:
    revision = data.get('revision', 0)
    if not isinstance(revision, int) or revision < 0:
        die('registry revision must be a non-negative integer')
    revision += 1
    data['revision'] = revision
    return revision

def registry_revision(data: dict) -> int:
    revision = data.get('revision', 0)
    if not isinstance(revision, int) or revision < 0:
        die('registry revision must be a non-negative integer')
    return revision

def next_sequence(data: dict) -> int:
    sequences = [
        entry.get('sequence')
        for entry in data.get('collabs', [])
        if isinstance(entry.get('sequence'), int)
    ]
    return max(sequences, default=0) + 1

def retire_legacy_registry_fields(data: dict) -> None:
    for key in RETIRED_ROOT_KEYS:
        data.pop(key, None)

def registry_event_index(data: dict) -> int:
    event_index = data.get('eventIndex', 0)
    if not isinstance(event_index, int) or event_index < 0:
        die('registry eventIndex must be a non-negative integer')
    return event_index

def bump_registry_event_index(data: dict) -> int:
    event_index = registry_event_index(data) + 1
    data['eventIndex'] = event_index
    return event_index

def registry_semantic_snapshot(data: dict | None) -> object:
    if data is None:
        return None
    snapshot = deepcopy(data)
    if isinstance(snapshot, dict):
        for key in REGISTRY_EVENT_IGNORED_ROOT_KEYS:
            snapshot.pop(key, None)
    return snapshot

def parse_registry_before(text: str | None) -> dict | None:
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None

def registry_has_semantic_change(before: dict | None, after: dict) -> bool:
    return registry_semantic_snapshot(before) != registry_semantic_snapshot(after)

def collab_ids_by_id(data: dict | None) -> dict[str, dict]:
    if not isinstance(data, dict):
        return {}
    collabs = data.get('collabs')
    if not isinstance(collabs, list):
        return {}
    result: dict[str, dict] = {}
    for entry in collabs:
        if isinstance(entry, dict) and isinstance(entry.get('id'), str):
            result[entry['id']] = entry
    return result

def registry_event_collab_id(before: dict | None, after: dict) -> str:
    before_collabs = collab_ids_by_id(before)
    after_collabs = collab_ids_by_id(after)
    changed: list[str] = []
    for collab_id in sorted(set(before_collabs) | set(after_collabs)):
        if registry_semantic_snapshot(before_collabs.get(collab_id)) != registry_semantic_snapshot(after_collabs.get(collab_id)):
            changed.append(collab_id)
    if len(changed) == 1:
        return changed[0]
    active_id = after.get('activeCollabId') or (before or {}).get('activeCollabId')
    if isinstance(active_id, str) and active_id.strip():
        return active_id
    return '_registry'

def prepare_registry_event(
    registry_path: Path,
    registry_before: str | None,
    data: dict,
    event_type: str,
) -> dict | None:
    before = parse_registry_before(registry_before)
    if not registry_has_semantic_change(before, data):
        return None
    return {
        'schema': REGISTRY_EVENT_SCHEMA,
        'eventType': event_type,
        'timestamp': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'collabId': registry_event_collab_id(before, data),
        'summary': f'{event_type} for {registry_event_collab_id(before, data)}',
        '_registryPath': str(registry_path),
        '_before': before,
    }

def finalize_registry_event(data: dict, event: dict) -> dict:
    finalized = dict(event)
    finalized['_legacyBefore'] = finalized.pop('_before', None)
    finalized.pop('_registryPath', None)
    finalized['revision'] = registry_revision(data)
    finalized['eventIndex'] = registry_event_index(data)
    return finalized

def revision_event_root(registry_path: Path) -> Path:
    return registry_path.parent / REGISTRY_EVENT_DIR

def revision_event_dir(registry_path: Path, collab_id: str) -> Path:
    safe_id = re.sub(r'[^A-Za-z0-9_.-]+', '-', collab_id).strip('-') or '_registry'
    return revision_event_root(registry_path) / safe_id

def write_json_if_absent(path: Path, data: dict) -> None:
    if path.exists():
        return
    tmp_path = path.with_name(f'{path.name}.tmp')
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    tmp_path.replace(path)

def ensure_legacy_revision_baselines(registry_path: Path, before: dict | None) -> None:
    if not isinstance(before, dict):
        return
    collabs = before.get('collabs')
    if not isinstance(collabs, list):
        return
    for entry in collabs:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str):
            continue
        event_dir = revision_event_dir(registry_path, entry['id'])
        event_dir.mkdir(parents=True, exist_ok=True)
        write_json_if_absent(
            event_dir / 'legacy-baseline.json',
            {
                'schema': REGISTRY_EVENT_SCHEMA,
                'eventIndex': None,
                'revision': entry.get('revision'),
                'timestamp': None,
                'eventType': 'legacy-baseline',
                'collabId': entry['id'],
                'summary': 'Legacy baseline for a pre-existing collab; no synthetic eventIndex assigned.',
            },
        )

def write_revision_event(registry_path: Path, event: dict) -> None:
    event_to_write = dict(event)
    legacy_before = event_to_write.get('_legacyBefore')
    ensure_legacy_revision_baselines(registry_path, legacy_before)
    event_dir = revision_event_dir(registry_path, event_to_write['collabId'])
    event_dir.mkdir(parents=True, exist_ok=True)
    event_path = event_dir / f'{event_to_write["eventIndex"]:012d}.json'
    tmp_path = event_path.with_name(f'{event_path.name}.tmp')
    tmp_path.write_text(json.dumps(event_to_write, indent=2, sort_keys=True) + '\n')
    tmp_path.replace(event_path)

def read_revision_events(registry_path: Path, collab_id: str) -> list[dict]:
    event_dir = revision_event_dir(registry_path, collab_id)
    if not event_dir.is_dir():
        return [
            {
                'eventIndex': None,
                'revision': None,
                'timestamp': None,
                'eventType': 'legacy-baseline',
                'summary': 'Legacy baseline for a pre-existing collab; no revision event files found.',
                'collabId': collab_id,
            }
        ]
    events: list[dict] = []
    for path in sorted(event_dir.glob('*.json')):
        try:
            event = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get('collabId') == collab_id:
            events.append(event)
    if not events:
        return [
            {
                'eventIndex': None,
                'revision': None,
                'timestamp': None,
                'eventType': 'legacy-baseline',
                'summary': 'Legacy baseline for a pre-existing collab; no readable revision events found.',
                'collabId': collab_id,
            }
        ]
    return sorted(
        events,
        key=lambda item: (
            -1 if item.get('eventIndex') is None else int(item.get('eventIndex', 0)),
            str(item.get('timestamp') or ''),
        ),
        reverse=True,
    )

@contextmanager
def registry_lock(path: Path):
    """Serialize registry/transcript mutations that derive state from live files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f'{path.name}.lock')
    with lock_path.open('a+') as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        os.utime(lock_path, None)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

@contextmanager
def registry_lock_nonblocking(path: Path):
    """Acquire a registry lock without waiting; used by migration preflight."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f'{path.name}.lock')
    with lock_path.open('a+') as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            die(f'registry lock held: {lock_path}')
        os.utime(lock_path, None)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def stale_registry_lock_message(path: Path, now: float | None = None) -> str | None:
    lock_path = path.with_name(f'{path.name}.lock')
    if not lock_path.exists():
        return None
    age = (now if now is not None else dt.datetime.now().timestamp()) - lock_path.stat().st_mtime
    if age < STALE_LOCK_SECONDS:
        return None
    try:
        with lock_path.open('a+') as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return (
                    f'stale registry lock: {lock_path}; a collab command has held it for '
                    f'at least {STALE_LOCK_SECONDS} seconds. Confirm whether a collab command '
                    'is stuck before terminating it.'
                )
            os.utime(lock_path, None)
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    except OSError as exc:
        return f'stale registry lock check failed: {lock_path}: {exc}'
    return None


def load_registry_or_bootstrap(path: Path) -> dict:
    if not path.exists():
        data = {'activeCollabId': None, 'collabs': []}
        sync_registry_project_metadata(data)
        capture_registry_project(data)
        return data
    data = load_registry(path)
    sync_registry_project_metadata(data)
    capture_registry_project(data)
    return data

def capture_registry_project(data: dict) -> None:
    global CURRENT_REGISTRY_PROJECT
    project = data.get('project')
    CURRENT_REGISTRY_PROJECT = project if isinstance(project, dict) else None

def root_project_id() -> str | None:
    identity_path = ROOT / '.collab.json'
    if not identity_path.exists():
        return None
    try:
        data = json.loads(identity_path.read_text())
    except json.JSONDecodeError:
        return None
    project_id = data.get('projectId')
    return project_id if isinstance(project_id, str) and project_id.strip() else None

def current_registry_project_id() -> str | None:
    if not isinstance(CURRENT_REGISTRY_PROJECT, dict):
        return None
    project_id = CURRENT_REGISTRY_PROJECT.get('projectId')
    return project_id if isinstance(project_id, str) and project_id.strip() else None

def resolve_collab(data: dict, target: str) -> dict:
    numeric_target = target[1:] if target.startswith('#') else target
    if numeric_target.isdigit():
        number = int(numeric_target)
        for index, entry in enumerate(data['collabs'], start=1):
            if entry.get('sequence', index) == number:
                return entry
        die(f'registry target not found: {target}')
    for entry in data['collabs']:
        if target in {entry['id'], entry['slug']}:
            return entry
    die(f'registry target not found: {target}')

def require_active_collab(data: dict) -> dict:
    active_id = data.get('activeCollabId')
    if not active_id:
        die('registry activeCollabId is empty')
    return resolve_collab(data, active_id)
