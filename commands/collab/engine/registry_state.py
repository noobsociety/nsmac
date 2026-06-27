#!/usr/bin/env python3
"""Project-identity binding and state-root resolution; does not own transcript reading, route planning, or phase lifecycle."""
from __future__ import annotations

import json
import os
import re
import hashlib
from pathlib import Path

from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.registry_constants import DISALLOWED_VERSION_FIELD
from commands.collab.engine.errors import die

PROJECT_ID_FILENAME = '.collab.json'
STATE_HOME_ENV = 'COLLAB_STATE_HOME'
DEFAULT_STATE_HOME = Path.home() / '.collabs'
PROJECT_ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{7,127}$')
STATE_ROOT_PROOF_COMMAND = './tests/commands/collab/registry.py/state-root-resolution.test.sh'

RESOLVED_PROJECT_IDENTITY: dict | None = None


def find_project_identity_path(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        identity_path = directory / PROJECT_ID_FILENAME
        if identity_path.exists():
            return identity_path
    return None


def read_project_identity(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f'project identity invalid JSON: {path}: {exc}')
    if not isinstance(data, dict):
        die(f'project identity must be an object: {path}')
    if DISALLOWED_VERSION_FIELD in data:
        die(f'project identity contains disallowed version field: {path}')
    project_id = data.get('projectId')
    if not isinstance(project_id, str) or not PROJECT_ID_RE.match(project_id):
        die(f'project identity projectId must be a readable, collision-safe slug: {path}')
    label = data.get('label')
    if label is not None and (not isinstance(label, str) or not label.strip()):
        die(f'project identity label must be a non-empty string when present: {path}')
    state = data.get('state')
    if state is not None and not isinstance(state, dict):
        die(f'project identity state must be an object when present: {path}')
    return data


def sanitize_project_id_seed(value: str | None) -> str:
    seed = (value or 'command-project').strip().lower()
    seed = re.sub(r'[^a-z0-9]+', '-', seed)
    seed = re.sub(r'-+', '-', seed).strip('-')
    if not seed:
        seed = 'command-project'
    if not seed[0].isalnum():
        seed = f'project-{seed}'
    while len(seed) < 8:
        seed = f'{seed}-project'
    return seed[:128].strip('-') or 'command-project'


def project_collision_suffix(project_root: Path) -> str:
    """Use a short path hash so collision names stay stable without a central allocation ledger."""
    resolved = str(project_root.expanduser().resolve())
    return hashlib.sha256(resolved.encode()).hexdigest()[:8]


def _fit_project_id(base: str, suffix: str | None = None, ordinal: int | None = None) -> str:
    parts = [base]
    if suffix:
        parts.append(suffix)
    if ordinal is not None:
        parts.append(str(ordinal))
    reserved = sum(len(part) for part in parts[1:]) + len(parts[1:])
    head = parts[0][: max(1, 128 - reserved)].strip('-') or 'project'
    candidate = '-'.join([head, *parts[1:]])
    while len(candidate) < 8:
        candidate = f'{candidate}-project'
    return candidate[:128].strip('-')


def project_id_for_project(
    project_root: Path,
    label: str | None = None,
    state_home: Path | None = None,
    current_project_id: str | None = None,
) -> str:
    base = sanitize_project_id_seed(label or project_root.name)
    home = state_home if state_home is not None else collab_state_home()
    preferred = _fit_project_id(base)
    if current_project_id == preferred or not (home / preferred).exists():
        return preferred

    suffix = project_collision_suffix(project_root)
    candidate = _fit_project_id(base, suffix)
    if current_project_id == candidate or not (home / candidate).exists():
        return candidate

    ordinal = 2
    while True:
        candidate = _fit_project_id(base, suffix, ordinal)
        if current_project_id == candidate or not (home / candidate).exists():
            return candidate
        ordinal += 1


def write_project_identity(project_root: Path, label: str | None = None) -> dict:
    project_root.mkdir(parents=True, exist_ok=True)
    identity_path = project_root / PROJECT_ID_FILENAME
    if identity_path.exists():
        return read_project_identity(identity_path)
    project_label = label or project_root.name or 'command-project'
    project_id = project_id_for_project(project_root, project_label)
    data = {
        'projectId': project_id,
        'label': project_label,
        'state': {
            'mode': 'shared',
            'isolation': 'opt-in',
        },
    }
    identity_path.write_text(json.dumps(data, indent=2) + '\n')
    return data


def collab_state_home() -> Path:
    configured = os.environ.get(STATE_HOME_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_STATE_HOME


def state_root_for_project(project_id: str) -> Path:
    return collab_state_home() / project_id


def project_metadata_from_identity(identity: dict | None = None) -> dict | None:
    source = identity if identity is not None else RESOLVED_PROJECT_IDENTITY
    if not isinstance(source, dict):
        return None
    project_id = source.get('projectId')
    if not isinstance(project_id, str) or not project_id.strip():
        return None
    label = source.get('label')
    if not isinstance(label, str) or not label.strip():
        label = 'command-project'
    return {'projectId': project_id, 'label': label.strip()}


def assert_registry_project_binding(data: dict, registry_path: Path) -> None:
    expected = project_metadata_from_identity()
    if expected is None:
        return
    project = data.get('project')
    if project is None:
        return
    if not isinstance(project, dict):
        die(f'{registry_path}: project must be an object when present')
    actual = project.get('projectId')
    if actual != expected['projectId']:
        die(
            f'project identity mismatch: registry {registry_path} is bound to '
            f'{actual}; marker {PROJECT_ID_FILENAME} declares {expected["projectId"]}'
        )


def sync_registry_project_metadata(data: dict) -> None:
    metadata = project_metadata_from_identity()
    if metadata is not None:
        data['project'] = metadata


def resolve_default_registry_path(command: str | None) -> tuple[Path, bool]:
    global RESOLVED_PROJECT_IDENTITY
    project_root = Path.cwd().resolve()
    identity_path = find_project_identity_path(project_root)

    if identity_path is None and command == 'init':
        identity = write_project_identity(project_root)
        identity_path = project_root / PROJECT_ID_FILENAME
    elif identity_path is not None:
        identity = read_project_identity(identity_path)
        project_root = identity_path.parent
    else:
        die(f'project marker missing: {PROJECT_ID_FILENAME}; run {collab_dispatch("init")} from the project root')

    RESOLVED_PROJECT_IDENTITY = identity
    state_root = state_root_for_project(identity['projectId'])
    label_path = state_root / 'label'
    metadata = project_metadata_from_identity(identity)
    if metadata:
        current = metadata['label'] + '\n'
        if not label_path.exists() or label_path.read_text() != current:
            state_root.mkdir(parents=True, exist_ok=True)
            label_path.write_text(current)
    return state_root / 'registry.json', True
