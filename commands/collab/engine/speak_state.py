#!/usr/bin/env python3
"""Speak-eligibility state model: derives the per-entry speak-state dict and the read-only next-command, next-line, policy-blocker, and phase-summary projections over it; does not own registry persistence, phase mutation, or rendering."""
from __future__ import annotations

from commands.collab.engine.registry_constants import AUTO_ADVANCE_EXEMPT_PHASES
from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.command_lines import transcript_view_command_for_role
from commands.collab.engine.transcript_readers import (
    active_phase_anchors,
    contribution_roles,
    read_transcript_for_entry,
    unchecked_assigned_items_by_role,
)
from commands.collab.engine.participants import (
    effective_turn_order,
    expected_speaker,
    optional_reviewer_allowed_at_round_boundary,
    participant_agent_id,
    reviewer_backed,
    reviewer_mode,
    reviewer_optional_phases,
    reviewer_role,
    reviewer_state,
)
from commands.collab.engine.seal_verification_logic import (
    first_pending_participant_verification_role,
    participant_verification_enabled,
    participant_verification_incomplete,
    verification_review_substate,
    verification_substate,
)


def speak_state_for_entry(entry: dict, transcript: str) -> dict:
    phase = entry['activePhase']
    contributors = contribution_roles(transcript, phase)
    order = effective_turn_order(entry)
    expected = expected_speaker(entry, contributors)
    optional_reviewer = optional_reviewer_allowed_at_round_boundary(entry, phase, contributors, order)
    allowed_roles = [expected]
    if optional_reviewer and optional_reviewer not in allowed_roles:
        allowed_roles.append(optional_reviewer)
    state = {
        'target': entry['id'],
        'activePhase': phase,
        'turnOrder': order,
        'contributors': contributors,
        'lastContributor': contributors[-1] if contributors else None,
        'expectedRole': expected,
        'reviewerRole': reviewer_role(entry),
        'reviewerState': reviewer_state(entry),
        'reviewerMode': reviewer_mode(entry) if reviewer_role(entry) else None,
        'reviewerOptionalPhases': reviewer_optional_phases(entry) if reviewer_role(entry) else [],
        'allowedRoles': allowed_roles,
        'autoAdvanceExempt': phase in AUTO_ADVANCE_EXEMPT_PHASES,
        'freshRegistryRead': True,
        'freshTranscriptRead': True,
    }
    if reviewer_backed(entry) and phase == 'Completion':
        completion_substate = verification_substate(entry)
        review_substate = verification_review_substate(entry)
        if (
            completion_substate == 'verification'
            and review_substate != 'assessment'
            and participant_verification_incomplete(entry)
        ):
            review_substate = 'participant'
        state['completionSubState'] = completion_substate
        state['verificationReviewSubState'] = review_substate
        state['participantVerification'] = participant_verification_enabled(entry)
        state['nextParticipantVerificationRole'] = first_pending_participant_verification_role(entry)
        if completion_substate == 'execution':
            execution_roles = [role for role in order if role != entry.get('moderatorRole')]
            execution = entry.get('execution') if isinstance(entry.get('execution'), dict) else {}
            expected = next(
                (
                    role
                    for role in execution_roles
                    if not (
                        isinstance(execution.get(role), dict)
                        and execution[role].get('status') == 'completed'
                    )
                ),
                None,
            )
            state['expectedRole'] = expected
            state['allowedRoles'] = execution_roles
        elif completion_substate == 'verification':
            if review_substate == 'participant':
                expected = state['nextParticipantVerificationRole']
                allowed_roles = [expected] if expected else []
            else:
                expected = reviewer_role(entry)
                allowed_roles = [expected] if expected else []
            state['expectedRole'] = expected
            state['allowedRoles'] = allowed_roles
    expected_agent_id = participant_agent_id(entry, expected)
    if expected_agent_id:
        state['expectedAgentId'] = expected_agent_id
    if reviewer_role(entry):
        state['uncheckedAssignedItemsByRole'] = unchecked_assigned_items_by_role(transcript)
    return state


def blocked_resume_state_for_entry(entry: dict, transcript: str) -> dict:
    phase = entry['activePhase']
    contributors = contribution_roles(transcript, phase)
    state = {
        'target': entry['id'],
        'activePhase': phase,
        'turnOrder': effective_turn_order(entry),
        'contributors': contributors,
        'lastContributor': contributors[-1] if contributors else None,
        'expectedRole': None,
        'reviewerRole': reviewer_role(entry),
        'reviewerState': reviewer_state(entry),
        'reviewerMode': reviewer_mode(entry) if reviewer_role(entry) else None,
        'reviewerOptionalPhases': reviewer_optional_phases(entry) if reviewer_role(entry) else [],
        'allowedRoles': [],
        'autoAdvanceExempt': phase in AUTO_ADVANCE_EXEMPT_PHASES,
        'freshRegistryRead': True,
        'freshTranscriptRead': True,
    }
    requested_agent_id = participant_agent_id(entry, entry.get('moderatorRole', ''))
    if requested_agent_id:
        state['moderatorAgentId'] = requested_agent_id
    if reviewer_role(entry):
        state['uncheckedAssignedItemsByRole'] = unchecked_assigned_items_by_role(transcript)
    return state


def current_completion_command(entry: dict) -> str | None:
    substate = verification_substate(entry)
    if substate == 'verification':
        review_substate = verification_review_substate(entry)
        if review_substate == 'assessment':
            return None
        if (
            review_substate == 'participant'
            or (
                review_substate != 'assessment'
                and participant_verification_incomplete(entry)
            )
        ):
            pending_role = first_pending_participant_verification_role(entry)
            if pending_role:
                return collab_dispatch('participant verify', entry["id"], pending_role)
            return collab_dispatch('participant verify', entry["id"])
        return collab_dispatch('seal verification', entry["id"])
    return collab_dispatch('run plan', entry["id"])


def next_command_for_state(entry: dict, transcript: str | None = None) -> str | None:
    if entry['status'] in {'closed', 'archived'}:
        return '/clear'
    phase = entry['activePhase']
    if phase == 'Completion':
        return current_completion_command(entry)
    if transcript is None:
        transcript = read_transcript_for_entry(entry)
    state = speak_state_for_entry(entry, transcript)
    if state.get('expectedRole') and state.get('expectedRole') != entry.get('moderatorRole'):
        return collab_dispatch('speak', entry["id"])
    return None


def phase_summary_for_state(entry: dict, state: dict) -> dict:
    summary = {
        'activePhase': entry['activePhase'],
        'status': entry['status'],
    }
    if state.get('completionSubState'):
        summary['completionSubState'] = state['completionSubState']
    if state.get('verificationReviewSubState'):
        summary['verificationReviewSubState'] = state['verificationReviewSubState']
    expected = state.get('expectedRole')
    if expected:
        summary['expectedRole'] = expected
    if state.get('lastContributor'):
        summary['lastContributor'] = state['lastContributor']
    unchecked = state.get('uncheckedAssignedItemsByRole')
    if unchecked:
        summary['uncheckedAssignedItemsByRole'] = unchecked
    return summary


def policy_blockers_for_role(state: dict, role: str, pending_reviewer: str | None = None) -> list[dict]:
    blockers: list[dict] = []
    if pending_reviewer:
        blockers.append({'code': 'pending-reviewer', 'reviewerRole': pending_reviewer})
    allowed = state.get('allowedRoles', [])
    if role not in allowed:
        expected = state.get('expectedRole')
        if expected:
            blockers.append({'code': 'expected-role', 'expectedRole': expected})
        elif not pending_reviewer:
            blockers.append({'code': 'no-eligible-role'})
    return blockers


def next_line_for_state(entry: dict, transcript: str | None = None) -> str:
    if entry['status'] == 'closed':
        return 'NEXT: Collab closed; run /clear before starting another collab.'
    if entry['status'] == 'archived':
        return 'NEXT: Collab archived; run /clear before starting another collab.'
    phase = entry['activePhase']
    if phase == 'Completion':
        return f"NEXT: Run {collab_dispatch('run plan')} for role {effective_turn_order(entry)[0]}."
    if transcript is None:
        try:
            transcript = read_transcript_for_entry(entry)
        except SystemExit:
            order = effective_turn_order(entry)
            if order:
                return f'NEXT: Run {collab_dispatch("speak")} for role {order[0]}.'
            return f'NEXT: Active phase is {phase}.'
    try:
        state = speak_state_for_entry(entry, transcript)
    except SystemExit:
        order = effective_turn_order(entry)
        if order:
            return f'NEXT: Run {collab_dispatch("speak")} for role {order[0]}.'
        return f'NEXT: Active phase is {phase}.'
    expected = state.get('expectedRole')
    if expected:
        return f'NEXT: Run {collab_dispatch("speak")} for role {expected}.'
    return f'NEXT: Active phase is {phase}.'


def next_line_after_speak(entry: dict, role: str, phase: str, transcript: str) -> str:
    if phase == 'Discussion':
        return f'NEXT: Run /compact before your next collab command for role {role}.'
    return next_line_for_state(entry, transcript)


def add_participation_resume_fields(
    state: dict,
    entry: dict,
    transcript: str,
    role: str,
    pending_reviewer: str | None = None,
) -> None:
    next_command = next_command_for_state(entry, transcript)
    if next_command:
        state['nextCommand'] = next_command
    state['nextTranscriptCommand'] = transcript_view_command_for_role(entry, role)
    state['policyBlockers'] = policy_blockers_for_role(state, role, pending_reviewer)
    state['phaseSummary'] = phase_summary_for_state(entry, state)
    anchors = active_phase_anchors(transcript, entry['activePhase'])
    if anchors:
        state['excerptAnchors'] = anchors
