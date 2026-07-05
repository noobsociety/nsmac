#!/usr/bin/env python3
"""Read-only CLI query/projection command handlers: load and project a single read view — registry path, role roster rows, reviewer/handoff state, timestamps, summary role — then print it and return an exit code; does not own registry persistence, phase mutation, or any write path."""
from __future__ import annotations

import json
from pathlib import Path

from roles import load_role, participant_row, role_catalog
from commands.collab.engine.errors import die
from commands.collab.engine.handoff_shape import handoff_state_for_role
from commands.collab.engine.normalizers import format_banner_timestamp, format_timestamp
from commands.collab.engine.participants import has_participant, reviewer_state, role_is_joinable
from commands.collab.engine.registry_io import load_registry, resolve_collab
from commands.collab.engine.transcript_readers import summary_role


def registry_path_command(path: Path) -> int:
    print(path)
    return 0


def role_row_command(roles_dir: Path, role: str, index: int) -> int:
    print(participant_row(load_role(roles_dir, role), index))
    return 0


def roles_command(roles_dir: Path) -> int:
    index = 1
    for data in role_catalog(roles_dir):
        if not role_is_joinable(data):
            continue
        print(participant_row(data, index))
        index += 1
    return 0


def reviewer_state_command(path: Path, target: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    print(json.dumps(reviewer_state(entry), sort_keys=True))
    return 0


def handoff_state_command(path: Path, target: str, role: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if not has_participant(entry, role):
        die(f'handoff role must already be a participant: {role}')
    state = handoff_state_for_role(entry, role) or {}
    print(json.dumps(state, sort_keys=True))
    return 0


def timestamp_command() -> int:
    print(format_timestamp())
    return 0


def banner_timestamp_command() -> int:
    print(format_banner_timestamp())
    return 0


def summary_role_command(line: str) -> int:
    role = summary_role(line)
    if role is None:
        die('summary role unavailable')
    print(role)
    return 0
