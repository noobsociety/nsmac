#!/usr/bin/env python3
"""Read-only inspection/report command handlers: list collabs, project the revision-event log, render a single-entry status view, compute drift, and audit closed collabs — each loads and projects a multi-entry or transcript-derived read view, prints it, and returns an exit code; does not own registry persistence, phase mutation, or any write path."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from commands.collab.engine.contribution_store import path_for_entry_target
from commands.collab.engine.diff import diff_result, render_diff
from commands.collab.engine.effort import effort_override_audit_items
from commands.collab.engine.errors import die
from commands.collab.engine.execution import completed_execution_unchecked_items
from commands.collab.engine.normalizers import collab_date, display_title
from commands.collab.engine.participants import (
    effective_turn_order,
    reviewer_backed,
    reviewer_mode,
    reviewer_role,
)
from commands.collab.engine.registry_constants import ALLOWED_STATUSES
from commands.collab.engine.registry_io import (
    load_registry,
    read_revision_events,
    registry_lock,
    registry_revision,
    require_active_collab,
    resolve_collab,
)
from commands.collab.engine.registry_state import project_metadata_for_display
from commands.collab.engine.seal_verification import verification_substate
from commands.collab.engine.transcript_readers import (
    transcript_path_for_entry,
    unchecked_assigned_items_by_role,
)


def log_command(path: Path, target: str) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    for event in read_revision_events(path, entry['id']):
        index = event.get('eventIndex')
        index_label = '#legacy' if index is None else f'#{index}'
        timestamp = event.get('timestamp') or '-'
        event_type = event.get('eventType') or 'registry-write'
        summary = event.get('summary') or ''
        print(f'{index_label}  {timestamp}  {event_type}  {summary}')
    return 0


def list_collabs(data: dict, status_filter: str | None = None) -> int:
    if status_filter is not None and status_filter not in ALLOWED_STATUSES:
        die(f'invalid status filter: {status_filter}')
    active_id = data.get('activeCollabId')
    indexed = [
        (index, entry)
        for index, entry in enumerate(data['collabs'], start=1)
        if status_filter is None or entry['status'] == status_filter
    ]
    indexed.sort(key=lambda item: (
        item[1]['id'] != active_id,
        -item[1].get('sequence', item[0]),
        item[1]['slug'],
    ))
    project = project_metadata_for_display(data)
    if project is not None:
        print(f"Project: {project['label']} · {project['projectId']}")
    for output_index, (index, entry) in enumerate(indexed):
        marker = '[*]' if entry['id'] == active_id else '[ ]'
        number = entry.get('sequence', index)
        title = display_title(entry['title'])
        phase = entry['activePhase'] if entry['activePhase'] else '—'
        participant_label = 'participant' if len(entry['participants']) == 1 else 'participants'
        if output_index or project is not None:
            print()
        print(f"{marker} #{number} - {entry['slug']}    {title}")
        print(
            f"         {entry['status']} · {phase} · "
            f"{len(entry['participants'])} {participant_label} · {collab_date(entry)}",
        )
    return 0


def print_status_view(entry: dict, transcript: str, revision: int) -> None:
    active_phase = entry['activePhase']
    completion_substate = None
    if active_phase == 'Completion' and reviewer_backed(entry):
        completion_substate = verification_substate(entry)
        active_phase = f"Completion.{completion_substate}"
    turn_order = ', '.join(effective_turn_order(entry)) or '—'
    reviewer = reviewer_role(entry)
    participants = ', '.join(
        f"{participant['role']} ({participant.get('agentId') or 'unknown'})"
        for participant in entry.get('participants', [])
    ) or '—'
    lines = [
        f"id:           {entry['id']}",
        f"slug:         {entry['slug']}",
        f"title:        {entry['title']}",
        f"status:       {entry['status']}",
        f"activePhase:  {active_phase}",
    ]
    if completion_substate is not None:
        lines.append(f"completionSubState: {completion_substate}")
    lines.extend([
        f"turnOrder:    {turn_order}",
        f"reviewerRole: {reviewer or '—'}",
    ])
    if reviewer:
        lines.append(f"reviewerMode: {reviewer_mode(entry)}")
    lines.append(f"revision:     {revision}")
    if reviewer_backed(entry) and entry['activePhase'] == 'Completion':
        unchecked = unchecked_assigned_items_by_role(transcript)
        lines.append(f"uncheckedAssignedItemsByRole: {json.dumps(unchecked, sort_keys=True)}")
    lines.append(f"participants: {participants}")
    print('\n'.join(lines))


def status_view(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        revision = registry_revision(data)
    print_status_view(entry, transcript, revision)
    return 0


def diff_command(path: Path, target: str | None) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target) if target else require_active_collab(data)
    transcript_path = path_for_entry_target(path, entry, entry['transcriptPath'])
    if not transcript_path.exists():
        die(f'transcript missing: {transcript_path}')
    sys.stdout.write(render_diff(diff_result(path, entry, transcript_path.read_text())))
    return 0


def audit_closed(path: Path) -> int:
    data = load_registry(path)
    findings: list[dict] = []
    for entry in data['collabs']:
        if entry['status'] != 'closed':
            continue
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        violations = completed_execution_unchecked_items(entry, transcript)
        for violation in violations:
            findings.append({
                'target': entry['id'],
                'role': violation['role'],
                'uncheckedCount': violation['uncheckedCount'],
            })
        findings.extend(effort_override_audit_items(entry['id'], transcript))
    print(json.dumps(findings, sort_keys=True))
    return 0
