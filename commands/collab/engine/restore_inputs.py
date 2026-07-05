#!/usr/bin/env python3
"""Restore-input readers: validate and parse the restore event-index argument and locate a historical collab entry (deep-copied) by id within a pre-restore registry snapshot; does not own restore-command orchestration, registry persistence, or revision-event writing."""
from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

from commands.collab.engine.errors import die


def parse_restore_event_index(raw: str | None, event_dir: Path) -> int:
    if raw is None or not re.fullmatch(r'\d+', raw.strip() if isinstance(raw, str) else ''):
        die(f'invalid event index: {raw}; revision event directory: {event_dir}')
    value = int(raw)
    if value < 0:
        die(f'invalid event index: {raw}; revision event directory: {event_dir}')
    return value


def collab_entry_from_registry_snapshot(snapshot: dict, collab_id: str) -> dict | None:
    collabs = snapshot.get('collabs')
    if not isinstance(collabs, list):
        return None
    for entry in collabs:
        if isinstance(entry, dict) and entry.get('id') == collab_id:
            return deepcopy(entry)
    return None
