#!/usr/bin/env python3
"""Record reactivation command handlers.

Owns `restore-content`, `reopen`, and the restore path's event-typed
single-file write helper. Registry/transcript commits stay owned by
`registry_io`; seal invalidation stays owned by `seal_verification_logic`.
"""
from __future__ import annotations

import datetime as dt
import json
from copy import deepcopy
from pathlib import Path

from commands.collab.engine.advisories import print_post_action_advisories
from commands.collab.engine.config_paths import DEFAULT_ROLES_DIR
from commands.collab.engine.contribution_validation import assert_turn_order_not_drifted
from commands.collab.engine.digests import execution_coverage_entries
from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.errors import die
from commands.collab.engine.participants import assert_caller_role, effective_turn_order
from commands.collab.engine.registry_io import (
    bump_registry_event_index,
    bump_registry_revision,
    commit_registry_and_transcript,
    finalize_registry_event,
    load_registry,
    prepare_registry_event,
    read_revision_events,
    registry_lock,
    resolve_collab,
    retire_legacy_registry_fields,
    revision_event_dir,
    write_revision_event,
)
from commands.collab.engine.registry_state import sync_registry_project_metadata
from commands.collab.engine.registry_validation import validate_registry as validate_registry_data
from commands.collab.engine.restore_inputs import (
    collab_entry_from_registry_snapshot,
    parse_restore_event_index,
)
from commands.collab.engine.seal_verification_logic import (
    clear_verdict,
    initialize_completion_state,
    invalidate_verification_seal,
)
from commands.collab.engine.seal_verification_render import (
    insert_reopen_pointer,
    latest_reviewer_findings_anchor,
)
from commands.collab.engine.speak_state import next_line_for_state
from commands.collab.engine.transcript_readers import transcript_path_for_entry
from commands.collab.engine.transcript_render import (
    print_header_overwrite,
    render_managed_header_text,
)


def save_registry_with_event_type(path: Path, data: dict, event_type: str, summary: str) -> None:
    registry_before = path.read_text() if path.exists() else None
    sync_registry_project_metadata(data)
    retire_legacy_registry_fields(data)
    registry_event = prepare_registry_event(path, registry_before, data, event_type)
    bump_registry_revision(data)
    if registry_event is not None:
        bump_registry_event_index(data)
        registry_event = finalize_registry_event(data, registry_event)
        registry_event['summary'] = summary
    validate_registry_data(data, path, DEFAULT_ROLES_DIR)
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


def restore_collab_content(path: Path, target: str, event_index_raw: str, caller_role: str | None = None) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'restore')
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        event_dir = revision_event_dir(path, entry['id'])
        event_index = parse_restore_event_index(event_index_raw, event_dir)
        event = next(
            (
                item
                for item in read_revision_events(path, entry['id'])
                if item.get('eventIndex') == event_index
            ),
            None,
        )
        if event is None or event.get('eventType') == 'legacy-baseline':
            die(f'invalid event index: {event_index_raw}; revision event directory: {event_dir}')
        before = event.get('_legacyBefore')
        if not isinstance(before, dict):
            die(f'invalid event index: {event_index_raw}; event has no restorable _legacyBefore snapshot')
        restored_entry = collab_entry_from_registry_snapshot(before, entry['id'])
        if restored_entry is None:
            die('restored entry fails validation: collabs')
        projected = deepcopy(data)
        for index, candidate in enumerate(projected.get('collabs', [])):
            if isinstance(candidate, dict) and candidate.get('id') == entry['id']:
                projected['collabs'][index] = restored_entry
                break
        else:
            die('restored entry fails validation: collabs')
        validate_registry_data(projected, path, DEFAULT_ROLES_DIR)
        data.clear()
        data.update(projected)
        save_registry_with_event_type(
            path,
            data,
            'restore-content',
            f'restore-content for {entry["id"]} from eventIndex {event_index}',
        )
    print(next_line_for_state(resolve_collab(data, target)))
    print(data.get('revision', 0))
    return 0


def reopen_collab(
    path: Path,
    target: str,
    phase_token: str,
    caller_role: str | None = None,
) -> int:
    if phase_token == 'action-plan':
        phase = 'Action Plan'
    elif phase_token == 'handoff':
        phase = 'Handoff'
    else:
        die('reopen phase must be one of: action-plan, handoff')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'reopen')
        if entry['status'] == 'archived':
            die('record is archived')
        if entry['activePhase'] != 'Completion':
            die(f'{collab_dispatch("reopen")} is valid only after a non-success Completion verdict')
        verdict = entry.get('verdict')
        if not isinstance(verdict, dict) or verdict.get('outcome') not in {'incomplete', 'failed'}:
            die(f'{collab_dispatch("reopen")} requires a non-success Completion verdict')
        restore_target = verdict.get('restoreTarget')
        if restore_target != phase:
            expected_token = 'handoff' if restore_target == 'Handoff' else 'action-plan'
            die(f'{collab_dispatch("reopen")} phase mismatch: verdict restoreTarget is {restore_target}; expected {expected_token}')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        findings_anchor = latest_reviewer_findings_anchor(transcript)
        derived_turn_order = assert_turn_order_not_drifted(entry, phase)
        coverage_entries = execution_coverage_entries(entry)
        if coverage_entries:
            entry['reopenCoverage'] = {
                'createdAt': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
                'executionEntries': coverage_entries,
            }
        entry['status'] = 'open'
        entry['archived'] = False
        entry['activePhase'] = phase
        data['activeCollabId'] = entry['id']
        entry['turnOrder'] = derived_turn_order
        # Preserve completed per-role verification across the reopen rather than
        # clearing it now: at reopen time no scope has been revised yet, so the
        # scope-aware decision is deferred to the advance back into Completion
        # (after the reopened phase revises scope and re-executes). This lets a
        # reopen that re-scopes only some roles re-verify just those roles.
        initialize_completion_state(entry, 'execution', reset_rounds=True, reset_stages=False)
        invalidate_verification_seal(entry, f'reopened {phase}')
        clear_verdict(entry)
        expected_role = next((item for item in effective_turn_order(entry) if item != entry['moderatorRole']), None)
        transcript = insert_reopen_pointer(transcript, phase, findings_anchor, expected_role)
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        commit_registry_and_transcript(path, data, transcript_path, rendered)
    print_post_action_advisories(entry, None, None, None, next_line_for_state(entry))
    print(entry['id'])
    return 0
