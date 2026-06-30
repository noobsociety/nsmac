#!/usr/bin/env python3
"""Field and participant mutation command handlers: set or force a single registry field (`set`, including the reviewer assignment and the force-only `active-phase` jump), clear the reviewer assignment (`unset reviewer`), and drop a participant from the roster and turn order (`remove-participant`). Each validates, re-renders the managed header, and persists registry + transcript together. The one dependency these write-path commands cannot import without a cycle — the core-owned `commit_registry_and_transcript` two-file write — is injected via `configure_field_commands`. Does not own the two-file commit implementation, header rendering, or registry validation."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Callable

from roles import load_role

from commands.collab.engine.advisories import forced_active_phase_advisory
from commands.collab.engine.config_paths import DEFAULT_ROLES_DIR
from commands.collab.engine.errors import die
from commands.collab.engine.execution import seal_terminal
from commands.collab.engine.git_repo import resolve_git_work_tree
from commands.collab.engine.participants import (
    assert_caller_role,
    has_participant,
    participant_roles,
    parse_reviewer_optional_phases,
    reviewer_role,
)
from commands.collab.engine.registry_constants import (
    ALLOWED_SET_FIELDS,
    DEFAULT_REVIEWER_MODE,
    DEFAULT_REVIEWER_OPTIONAL_PHASES,
    FORCE_ONLY_FIELDS,
    PHASES,
)
from commands.collab.engine.registry_io import (
    load_registry,
    registry_lock,
    resolve_collab,
)
from commands.collab.engine.registry_validation import validate_registry as validate_registry_data
from commands.collab.engine.seal_verification import initialize_completion_state
from commands.collab.engine.transcript_readers import transcript_path_for_entry
from commands.collab.engine.transcript_render import (
    print_header_overwrite,
    render_managed_header_text,
)

_commit_registry_and_transcript: Callable[[Path, dict, Path, str], None] | None = None


def configure_field_commands(
    *,
    commit_registry_and_transcript: Callable[[Path, dict, Path, str], None],
) -> None:
    """Inject the cycle-blocked dependency of the set/unset/remove-participant write paths: the core-owned two-file commit."""
    global _commit_registry_and_transcript
    _commit_registry_and_transcript = commit_registry_and_transcript


def _require_commit() -> Callable[[Path, dict, Path, str], None]:
    if _commit_registry_and_transcript is None:
        die('field commands engine is not configured: commit callback missing')
    return _commit_registry_and_transcript


def set_field(
    path: Path,
    target: str,
    field: str,
    value: str | None,
    force: bool,
    roles_dir: Path,
    caller_role: str | None = None,
) -> int:
    force_advisory: str | None = None
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'set')
        forced_active_phase = False
        if field in FORCE_ONLY_FIELDS:
            if value is None:
                die(f'{field} requires a value')
            if not force:
                die(f'field requires --force: {field}')
            if field == 'active-phase':
                if value not in PHASES:
                    die(f'active-phase must be one of {PHASES}')
                entry['activePhase'] = value
                forced_active_phase = True
                if value == 'Completion' and seal_terminal(entry):
                    # Mirror advance_phase's Completion entry so a forced jump
                    # cannot bypass the scope-aware reset and strand a reopened
                    # cycle at rounds=0 with every stage preserved (the old
                    # deadlock). No-op on a fresh force (no completed stages yet).
                    initialize_completion_state(entry, 'execution', reset_rounds=True, scope_aware=True)
        elif field == 'reviewer':
            if value == '--clear':
                clear_reviewer(entry)
            else:
                if value is None:
                    die('reviewer requires a role or --clear')
                if not has_participant(entry, value):
                    die('reviewer must already be a participant')
                load_role(roles_dir, value)
                if value == entry['moderatorRole']:
                    die('reviewer must not be the moderator')
                if value in entry['turnOrder']:
                    die('reviewer must not appear in turnOrder')
                entry['reviewerRole'] = value
                entry['reviewerMode'] = DEFAULT_REVIEWER_MODE
                entry['reviewerOptionalPhases'] = list(DEFAULT_REVIEWER_OPTIONAL_PHASES)
        elif field == 'reviewer-optional-phases':
            if not reviewer_role(entry):
                die('reviewer-optional-phases requires reviewerRole')
            entry['reviewerOptionalPhases'] = parse_reviewer_optional_phases(value)
        elif field not in ALLOWED_SET_FIELDS:
            die(f'field not settable: {field}')
        elif field == 'turn-order':
            if value is None:
                die('turn-order requires a value')
            turnOrder = value.split()
            if not turnOrder:
                die('turn-order requires at least one role')
            if len(set(turnOrder)) != len(turnOrder):
                die('turn-order roles must be unique')
            if not set(turnOrder).issubset(set(participant_roles(entry))):
                die('turn-order roles must already be participants')
            reviewer = reviewer_role(entry)
            if reviewer and reviewer in turnOrder:
                die('turn-order must not include reviewerRole')
            entry['turnOrder'] = turnOrder
        elif field == 'work-repo':
            if value is None:
                die('work-repo requires a path')
            entry['workRepo'] = str(resolve_git_work_tree(value, 'work-repo'))
        else:
            if value is None:
                die(f'{field} requires a value')
            if not value.strip():
                die(f'{field} requires a non-empty value')
            entry[field] = value
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), entry, roles_dir)
        if forced_active_phase:
            force_advisory = forced_active_phase_advisory(entry, rendered)
        print_header_overwrite(header_changed)
        _require_commit()(path, data, transcript_path, rendered)
    print(entry['id'])
    if force_advisory:
        print(force_advisory)
    return 0


def clear_reviewer(entry: dict) -> bool:
    changed = False
    for key in ('reviewerRole', 'reviewerMode', 'reviewerOptionalPhases'):
        if key in entry:
            entry.pop(key)
            changed = True
    return changed


def unset_field(
    path: Path,
    target: str,
    field: str,
    roles_dir: Path,
    caller_role: str | None = None,
) -> int:
    if field != 'reviewer':
        die(f'field not unsettable: {field}')

    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        assert_caller_role(current_entry, caller_role, 'unset')
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')

        nextdata = deepcopy(data)
        next_entry = resolve_collab(nextdata, target)
        clear_reviewer(next_entry)
        validate_registry_data(nextdata, path, DEFAULT_ROLES_DIR)

        transcript_path = transcript_path_for_entry(next_entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), next_entry, roles_dir)
        print_header_overwrite(header_changed)
        _require_commit()(path, nextdata, transcript_path, rendered)
    print(next_entry['id'])
    return 0


def remove_participant(
    path: Path,
    target: str,
    role: str,
    roles_dir: Path,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        assert_caller_role(current_entry, caller_role, 'remove-participant')
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if role == current_entry['moderatorRole']:
            die('moderator cannot be removed')
        if role == reviewer_role(current_entry):
            die('reviewer cannot be removed while assigned')
        if not has_participant(current_entry, role):
            print(f'participant already absent: {role}')
            return 0

        nextdata = deepcopy(data)
        next_entry = resolve_collab(nextdata, target)
        next_entry['participants'] = [
            participant
            for participant in next_entry.get('participants', [])
            if participant.get('role') != role
        ]
        next_entry['turnOrder'] = [
            participant_role
            for participant_role in next_entry.get('turnOrder', [])
            if participant_role != role
        ]
        validate_registry_data(nextdata, path, DEFAULT_ROLES_DIR)

        transcript_path = transcript_path_for_entry(next_entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        rendered, header_changed = render_managed_header_text(transcript_path.read_text(), next_entry, roles_dir)
        print_header_overwrite(header_changed)
        _require_commit()(path, nextdata, transcript_path, rendered)
    print(next_entry['id'])
    return 0
