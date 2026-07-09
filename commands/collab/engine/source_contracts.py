#!/usr/bin/env python3
"""Source-contract validation command: validate that the registry loads cleanly (no stale lock) and that the required source-contract anchors are present across the flag-taxonomy, seal-verification, and invariants reference documents under the config root; aggregates lower-tier leaves (config_paths, errors, registry_io). Does not own registry persistence, phase mutation, or any write path."""
from __future__ import annotations

from pathlib import Path

from commands.collab.engine.config_paths import DEFAULT_CONFIG_ROOT, DEFAULT_FLAG_TAXONOMY_PATH
from commands.collab.engine.errors import die
from commands.collab.engine.registry_io import load_registry, stale_registry_lock_message


def require_source_text(path: Path, needle: str, label: str) -> None:
    if not path.exists():
        die(f'source contract missing {label}: {path.relative_to(DEFAULT_CONFIG_ROOT)}')
    if needle not in path.read_text():
        die(f'source contract missing {label}: {path.relative_to(DEFAULT_CONFIG_ROOT)}')


def validate_source_contracts() -> None:
    if not DEFAULT_FLAG_TAXONOMY_PATH.exists():
        die(f'source contract missing flag taxonomy: {DEFAULT_FLAG_TAXONOMY_PATH.relative_to(DEFAULT_CONFIG_ROOT)}')

    seal_verification = DEFAULT_CONFIG_ROOT / 'commands/collab/seal-verification/index.md'
    require_source_text(seal_verification, 'restore-route-recovery', 'restore-route recovery anchor')
    require_source_text(seal_verification, '(collab show verdict)', 'restore-route verdict inspection')
    require_source_text(seal_verification, '(collab reopen action-plan)', 'restore-route action-plan reopen')
    require_source_text(seal_verification, '(collab reopen handoff)', 'restore-route handoff reopen')
    require_source_text(seal_verification, '(collab run plan)', 'restore-route rerun step')
    require_source_text(seal_verification, '(collab seal verification)', 'restore-route reseal step')

    invariants = DEFAULT_CONFIG_ROOT / 'commands/collab/reference/invariants.md'
    require_source_text(invariants, 'Rollback triggers', 'rollback trigger section')
    require_source_text(invariants, 'Observation backlog', 'observation backlog section')


def validate_command(path: Path) -> int:
    load_registry(path)
    stale_lock = stale_registry_lock_message(path)
    if stale_lock:
        die(stale_lock)
    validate_source_contracts()
    print('registry OK')
    return 0
