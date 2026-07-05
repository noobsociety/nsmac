#!/usr/bin/env python3
"""Route write-path guard (`write-guard`): confirm a route only writes under the user-scope collab state root — the registry file, its lock, and the `records/` transcript tree — rejecting absolute paths and any target outside that set. The internal `execute` guard token is exempt because Completion execution writes through the work repo, not the state root. Self-contained: no registry state, transcript reads, or commit primitives — only path-shape validation."""
from __future__ import annotations

from pathlib import Path

from commands.collab.engine.errors import die


def write_guard(route: str, paths: list[str]) -> int:
    if not paths:
        die('write-guard requires at least one path')
    if route == 'execute':
        print('ok')
        return 0
    for item in paths:
        normalized = Path(item).as_posix()
        if normalized.startswith('./'):
            normalized = normalized[2:]
        if Path(item).is_absolute() or not (
            normalized in {'registry.json', 'registry.json.lock', 'records'}
            or normalized.startswith('records/')
        ):
            die(f'route may only write under the user-scope collab state root: {route}: {item}')
    print('ok')
    return 0
