#!/usr/bin/env python3
"""Rebind user-scope collab state root directories from legacy ids to readable slugs."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from commands.collab.engine.registry_io import registry_lock_nonblocking
from commands.collab.engine.registry_state import (
    PROJECT_ID_FILENAME,
    PROJECT_ID_RE,
    collab_state_home,
    project_id_for_project,
    read_project_identity,
)


def fail(message: str) -> None:
    print(f'ABORT: {message}', file=sys.stderr)
    raise SystemExit(1)


def write_json(path: Path, data: dict) -> None:
    tmp_path = path.with_name(f'{path.name}.tmp')
    tmp_path.write_text(json.dumps(data, indent=2) + '\n')
    tmp_path.replace(path)


def load_registry(registry_path: Path) -> dict:
    try:
        data = json.loads(registry_path.read_text())
    except json.JSONDecodeError as exc:
        fail(f'registry invalid JSON: {registry_path}: {exc}')
    if not isinstance(data, dict):
        fail(f'registry must be an object: {registry_path}')
    return data


def validate_project_id(value: str, label: str) -> None:
    if not PROJECT_ID_RE.match(value):
        fail(f'{label} projectId is not a readable, collision-safe slug: {value}')


def marker_path_for_root(project_root: Path) -> Path:
    return project_root / PROJECT_ID_FILENAME


def read_marker(project_root: Path) -> tuple[Path, dict, str]:
    identity_path = marker_path_for_root(project_root)
    if not identity_path.exists():
        fail(f'project marker missing: {identity_path}')
    return identity_path, read_project_identity(identity_path), identity_path.read_text()


def collect_markers(primary_root: Path, extra_roots: list[Path]) -> list[tuple[Path, dict, str]]:
    seen: set[Path] = set()
    markers: list[tuple[Path, dict, str]] = []
    for root in [primary_root, *extra_roots]:
        identity_path, identity, raw = read_marker(root)
        resolved = identity_path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        markers.append((identity_path, identity, raw))
    return markers


def delete_empty_orphan(state_home: Path, project_id: str) -> dict:
    validate_project_id(project_id, 'orphan')
    orphan = state_home / project_id
    if not orphan.exists():
        fail(f'empty orphan not found: {orphan}')
    if not orphan.is_dir():
        fail(f'empty orphan is not a directory: {orphan}')
    registry_path = orphan / 'registry.json'
    if registry_path.exists():
        data = load_registry(registry_path)
        if data.get('activeCollabId') is not None:
            fail(f'orphan registry has activeCollabId: {registry_path}')
        collabs = data.get('collabs')
        if collabs != []:
            fail(f'orphan registry is not empty: {registry_path}')
        project = data.get('project')
        if isinstance(project, dict) and project.get('projectId') not in {None, project_id}:
            fail(f'orphan registry project.projectId does not match {project_id}: {registry_path}')
        for payload_dir_name in ('records', 'revisions'):
            payload_dir = orphan / payload_dir_name
            if payload_dir.exists() and any(payload_dir.iterdir()):
                fail(f'orphan {payload_dir_name} directory is not empty: {payload_dir}')
    elif any(orphan.iterdir()):
        fail(f'orphan is not empty: {orphan}')
    shutil.rmtree(orphan)
    return {
        'status': 'deleted-empty-orphan',
        'projectId': project_id,
        'path': str(orphan),
    }


def migration_record(
    old_id: str,
    new_id: str,
    source_markers: list[Path],
    registry_path: Path,
) -> dict:
    return {
        'oldProjectId': old_id,
        'newProjectId': new_id,
        'sourceMarkers': [str(path) for path in source_markers],
        'sourceMarker': str(source_markers[0]),
        'registryPath': str(registry_path),
        'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
    }


def assert_source_state(identity_path: Path, old_root: Path, old_id: str) -> Path:
    if not old_root.exists():
        fail(f'partial migration state: source user-scope collab state root missing: {old_root}')
    if not old_root.is_dir():
        fail(f'partial migration state: source user-scope collab state root is not a directory: {old_root}')
    registry_path = old_root / 'registry.json'
    if not registry_path.exists():
        fail(f'partial migration state: registry missing for marker {identity_path}: {registry_path}')
    data = load_registry(registry_path)
    project = data.get('project')
    if isinstance(project, dict):
        actual_id = project.get('projectId')
        if actual_id is not None and actual_id != old_id:
            fail(
                'partial migration state: registry project.projectId '
                f'{actual_id} does not match marker {old_id}'
            )
    return registry_path


def already_complete(markers: list[tuple[Path, dict, str]], current_root: Path, current_id: str) -> dict:
    registry_path = current_root / 'registry.json'
    if not registry_path.exists():
        fail(f'partial migration state: completed marker has no registry: {registry_path}')
    data = load_registry(registry_path)
    project = data.get('project')
    if isinstance(project, dict) and project.get('projectId') not in {None, current_id}:
        fail(
            'partial migration state: completed registry project.projectId '
            f'{project.get("projectId")} does not match marker {current_id}'
        )
    for identity_path, identity, _raw in markers:
        if identity.get('projectId') != current_id:
            fail(f'partial migration state: marker {identity_path} does not match completed id {current_id}')
    return {
        'status': 'already-complete',
        'oldProjectId': current_id,
        'newProjectId': current_id,
        'sourceMarkers': [str(marker[0]) for marker in markers],
        'sourceMarker': str(markers[0][0]),
        'registryPath': str(registry_path),
    }


def assert_marker_set(markers: list[tuple[Path, dict, str]], old_id: str) -> None:
    for identity_path, identity, _raw in markers:
        actual = identity.get('projectId')
        if actual != old_id:
            fail(f'project marker {identity_path} declares {actual}; expected {old_id}')


def updated_identity(identity: dict, new_id: str, old_id: str, timestamp: str) -> dict:
    updated = dict(identity)
    updated['projectId'] = new_id
    state = updated.get('state')
    if not isinstance(state, dict):
        state = {}
    state['previousProjectId'] = old_id
    state['projectIdMigratedAt'] = timestamp
    updated['state'] = state
    return updated


def migrate(primary_root: Path, state_home: Path, extra_roots: list[Path]) -> dict:
    markers = collect_markers(primary_root, extra_roots)
    primary_identity_path, identity, _marker_before = markers[0]
    old_id = identity['projectId']
    label = identity.get('label') if isinstance(identity.get('label'), str) else primary_root.name
    validate_project_id(old_id, 'marker')
    assert_marker_set(markers, old_id)

    new_id = project_id_for_project(primary_root, label, state_home, current_project_id=old_id)
    validate_project_id(new_id, 'target')

    old_root = state_home / old_id
    new_root = state_home / new_id
    if old_id == new_id:
        return already_complete(markers, old_root, old_id)
    if new_root.exists():
        fail(f'target user-scope collab state root already exists; no auto-merge: {new_root}')
    old_registry = assert_source_state(primary_identity_path, old_root, old_id)

    marker_befores = {identity_path: raw for identity_path, _identity, raw in markers}
    registry_before = old_registry.read_text()
    record = migration_record(old_id, new_id, [marker[0] for marker in markers], new_root / 'registry.json')

    with registry_lock_nonblocking(old_registry):
        try:
            old_root.rename(new_root)
            new_registry = new_root / 'registry.json'
            data = load_registry(new_registry)
            data['project'] = {
                'projectId': new_id,
                'label': label,
            }
            migrations = data.setdefault('projectIdMigrations', [])
            if not isinstance(migrations, list):
                fail('registry projectIdMigrations must be a list when present')
            migrations.append(record)
            write_json(new_registry, data)
            (new_root / 'label').write_text(label + '\n')

            for identity_path, marker_identity, _raw in markers:
                write_json(identity_path, updated_identity(marker_identity, new_id, old_id, record['timestamp']))
        except BaseException:
            if not old_root.exists() and new_root.exists():
                current_registry = new_root / 'registry.json'
                if current_registry.exists():
                    current_registry.write_text(registry_before)
                new_root.rename(old_root)
            for identity_path, raw in marker_befores.items():
                identity_path.write_text(raw)
            raise

    return {
        'status': 'migrated',
        **record,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Rebind a collab project to its readable user-scope collab state root.'
    )
    parser.add_argument('--project-root', default=os.getcwd())
    parser.add_argument('--state-home', default=None)
    parser.add_argument('--extra-project-root', action='append', default=[])
    parser.add_argument('--delete-empty-orphan')
    args = parser.parse_args(argv)

    state_home = Path(args.state_home).expanduser().resolve() if args.state_home else collab_state_home()
    state_home.mkdir(parents=True, exist_ok=True)
    if args.delete_empty_orphan:
        result = delete_empty_orphan(state_home, args.delete_empty_orphan)
    else:
        primary_root = Path(args.project_root).expanduser().resolve()
        extra_roots = [Path(root).expanduser().resolve() for root in args.extra_project_root]
        result = migrate(primary_root, state_home, extra_roots)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
