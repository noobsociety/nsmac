"""Phase sequencing and lifecycle notices; does not own registry mutations, rendering, or sealing."""
# Tests: phase-advance sequencing, restore-target validation, reopen from non-success verdict,
#        close and archive transitions, structured notice message shapes.
from __future__ import annotations

import json

from tools.collab.registry_constants import PHASES

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
            'message': 'Use a subagent or compacted execution context before /collab run plan.',
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

def terminal_notice(status: str) -> dict:
    return {
        'notice': 'clear',
        'status': status,
        'message': 'Run /clear before starting another collab.',
    }

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
