"""Contribution-store path and shape helpers shared by registry and readers."""
from __future__ import annotations

import json
from pathlib import Path

from commands.collab.engine.errors import die


def path_for_entry_target(registry_path: Path, entry: dict, target_path: str) -> Path:
    path = Path(target_path)
    if path.is_absolute():
        return path
    return registry_path.parent / path


def contribution_store_path_for_entry(registry_path: Path, entry: dict) -> Path:
    transcript_path = Path(entry['transcriptPath'])
    return path_for_entry_target(
        registry_path,
        entry,
        str(transcript_path.with_name(f'{transcript_path.stem}-contributions.json')),
    )


def empty_contribution_store(timestamp: str | None = None) -> dict:
    store = {'contributions': []}
    if timestamp:
        store['metadata'] = {'rawTranscriptTimestamp': timestamp}
    return store


def normalize_contribution_store(loaded: object, store_path: Path) -> dict:
    if isinstance(loaded, list):
        return {'contributions': loaded}
    if not isinstance(loaded, dict):
        die(f'contribution store must be an object: {store_path}')
    contributions = loaded.setdefault('contributions', [])
    if not isinstance(contributions, list):
        die(f'contribution store contributions must be a list: {store_path}')
    return loaded


def mutable_contribution_store_for_entry(registry_path: Path, entry: dict) -> dict:
    store_path = contribution_store_path_for_entry(registry_path, entry)
    if not store_path.exists():
        return empty_contribution_store()
    try:
        loaded = json.loads(store_path.read_text())
    except json.JSONDecodeError as exc:
        die(f'contribution store invalid JSON: {store_path}: {exc}')
    return normalize_contribution_store(loaded, store_path)


def write_contribution_store_for_entry(registry_path: Path, entry: dict, store: dict) -> None:
    store_path = contribution_store_path_for_entry(registry_path, entry)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(store, indent=2, ensure_ascii=True) + '\n')


def append_contribution_store_record(
    registry_path: Path,
    entry: dict,
    record: dict,
) -> None:
    store = mutable_contribution_store_for_entry(registry_path, entry)
    store.setdefault('contributions', []).append(record)
    write_contribution_store_for_entry(registry_path, entry, store)


def replace_latest_contribution_store_record(
    registry_path: Path,
    entry: dict,
    phase: str,
    role: str,
    record: dict,
) -> None:
    store = mutable_contribution_store_for_entry(registry_path, entry)
    contributions = store.setdefault('contributions', [])
    for index in range(len(contributions) - 1, -1, -1):
        existing = contributions[index]
        if isinstance(existing, dict) and existing.get('phase') == phase and existing.get('role') == role:
            contributions[index] = record
            write_contribution_store_for_entry(registry_path, entry, store)
            return
    contributions.append(record)
    write_contribution_store_for_entry(registry_path, entry, store)


def mark_contribution_store_record_retracted(
    registry_path: Path,
    entry: dict,
    anchor: str,
    reason: str,
    timestamp: str,
) -> None:
    store = mutable_contribution_store_for_entry(registry_path, entry)
    contributions = store.setdefault('contributions', [])
    for index in range(len(contributions) - 1, -1, -1):
        existing = contributions[index]
        if isinstance(existing, dict) and existing.get('anchor') == anchor:
            existing['retracted'] = True
            existing['retractionReason'] = reason
            existing['retractionTimestamp'] = timestamp
            write_contribution_store_for_entry(registry_path, entry, store)
            return
