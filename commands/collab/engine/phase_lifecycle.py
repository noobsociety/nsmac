"""Phase sequencing and lifecycle notices; does not own registry mutations, rendering, or sealing."""
# Tests: phase-advance sequencing, restore-target validation, reopen from non-success verdict,
#        close and archive transitions, structured notice message shapes.
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.errors import die
from commands.collab.engine.contribution_validation import validate_action_plan_executable_scope
from commands.collab.engine.participants import (
    assert_caller_role,
    normalize_turn_order_for_phase,
    remove_moderator_from_turn_order,
)
from commands.collab.engine.registry_constants import MOD_EXCLUDED_PHASES, PHASES
from commands.collab.engine.registry_io import load_registry, registry_lock, resolve_collab
from commands.collab.engine.transcript_readers import completion_summary_empty, transcript_path_for_entry


@dataclass(frozen=True)
class PhaseLifecycleCallbacks:
    seal_terminal: Callable[[dict], bool]
    initialize_completion_state: Callable[..., None]
    invalidate_verification_seal: Callable[[dict, str], None]
    render_managed_header_text: Callable[[str, dict, Path], tuple[str, bool]]
    print_header_overwrite: Callable[[bool], None]
    commit_registry_and_transcript: Callable[[Path, dict, Path, str], None]
    print_post_action_advisories: Callable[[dict, str | None, str | None, dict | None, str], None]
    next_line_for_state: Callable[[dict], str]

def next_phase_name(phase: str) -> str | None:
    index = PHASES.index(phase)
    if index == len(PHASES) - 1:
        return None
    return PHASES[index + 1]

def transition_notice(from_phase: str, to_phase: str) -> dict | None:
    transition = f'{from_phase}->{to_phase}'
    if transition == 'Discussion->Conclusion':
        return {
            'notice': 'compact',
            'transition': transition,
            'message': 'Run /compact before continuing to Conclusion.',
        }
    if transition == 'Conclusion->Action Plan':
        return {
            'notice': 'action-plan-shape',
            'transition': transition,
            'message': (
                'Action Plan entries must follow invariants.md Invariant #9: '
                r'^- \[[ x]\] \*\*[a-z]+:\*\*.'
            ),
        }
    if transition == 'Handoff->Completion':
        return {
            'notice': 'subagent',
            'transition': transition,
            'message': f'Use a subagent or compacted execution context before {collab_dispatch("run plan")}.',
        }
    return None

def discussion_turn_notice(entry: dict, contributors: list[str]) -> dict | None:
    if entry['activePhase'] != 'Discussion' or not contributors:
        return None
    if contributors[-1] == entry['moderatorRole']:
        return None
    # This is advisory visibility only. The helper cannot observe or orchestrate /compact.
    return {
        'compactBeforeNextCommand': True,
        'notice': 'compact',
        'transition': 'Discussion-turn',
        'message': 'Run /compact before issuing your next collab command.',
    }

def lifecycle_status_notice(status: str) -> dict:
    return {
        'notice': 'clear',
        'status': status,
        'message': 'Run /clear before starting another collab.',
    }

def add_completion_summary_notice(notice: dict | None, transcript: str) -> dict | None:
    if notice and notice.get('transition') == 'Handoff->Completion' and completion_summary_empty(transcript):
        notice = dict(notice)
        notice['summaryEmpty'] = True
    return notice

def efficiency_line_from_notice(notice: dict | None) -> str | None:
    if not notice:
        return None
    notice_type = notice.get('notice')
    transition = notice.get('transition')
    status = notice.get('status')
    if notice_type == 'compact' and transition in {'Discussion-turn', 'Discussion->Conclusion'}:
        return 'EFFICIENCY: Run /compact before next collab command.'
    if notice_type == 'subagent' and transition == 'Handoff->Completion':
        return 'EFFICIENCY: Run /compact, then prepare or use the assigned subagent work.'
    if notice_type == 'clear' or status in {'closed', 'archived'}:
        return 'EFFICIENCY: Run /clear before starting another collab.'
    return None

def notice_message(notice: dict) -> str:
    message = notice.get('message')
    if isinstance(message, str) and message.strip():
        return message.strip()
    notice_type = notice.get('notice')
    if isinstance(notice_type, str) and notice_type.strip():
        return notice_type.strip()
    return 'Lifecycle notice emitted.'

def print_notice_diagnostic(notice: dict | None, emit_json: bool) -> None:
    if not notice:
        return
    if not emit_json:
        print(f'NOTICE: {notice_message(notice)}')
    if emit_json:
        print(json.dumps(notice, sort_keys=True))

def print_lifecycle_diagnostic(lifecycle: dict, emit_json: bool) -> None:
    phase_state = lifecycle.get('phaseState')
    if phase_state:
        print(f'PHASE: {phase_state}')
    notice = lifecycle.get('notice')
    if isinstance(notice, dict):
        print_notice_diagnostic(notice, emit_json)
    if emit_json:
        print(json.dumps(lifecycle, sort_keys=True))

def print_phase_result(phase: str, notice: dict | None = None, emit_json: bool = True) -> None:
    print(phase)
    print_notice_diagnostic(notice, emit_json)


def advance_phase_state(
    path: Path,
    target: str,
    direction: str,
    callbacks: PhaseLifecycleCallbacks,
    roles_dir: Path,
    emit_json: bool = False,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'advance' if direction == 'next' else 'restore')
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        active_phase = entry.get('activePhase')
        if active_phase not in PHASES:
            die('active phase missing in metadata')
        index = PHASES.index(active_phase)
        from_phase = active_phase
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        if direction == 'next':
            if index == len(PHASES) - 1:
                die('no next phase')
            if from_phase == 'Action Plan':
                validate_action_plan_executable_scope(transcript)
            entry['activePhase'] = PHASES[index + 1]
            if entry['activePhase'] in MOD_EXCLUDED_PHASES:
                remove_moderator_from_turn_order(entry)
            if entry['activePhase'] == 'Completion' and callbacks.seal_terminal(entry):
                callbacks.initialize_completion_state(entry, 'execution', reset_rounds=True, scope_aware=True)
        else:
            if index == 0:
                die('no previous phase')
            entry['activePhase'] = PHASES[index - 1]
            normalize_turn_order_for_phase(entry, entry['activePhase'])
            if entry['activePhase'] != 'Completion':
                callbacks.invalidate_verification_seal(entry, f'restored to {entry["activePhase"]}')

        notice = transition_notice(from_phase, entry['activePhase'])
        rendered, header_changed = callbacks.render_managed_header_text(transcript, entry, roles_dir)
        notice = add_completion_summary_notice(notice, rendered)
        callbacks.print_header_overwrite(header_changed)
        callbacks.commit_registry_and_transcript(path, data, transcript_path, rendered)
    callbacks.print_post_action_advisories(
        entry,
        None,
        None,
        notice,
        callbacks.next_line_for_state(entry),
    )
    print_phase_result(entry['activePhase'], notice, emit_json)
    return 0
