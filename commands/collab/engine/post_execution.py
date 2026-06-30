#!/usr/bin/env python3
"""Post-execution lifecycle projections: given an entry and its assigned roles, compute (a) whether the collab is close-eligible after execution completes and (b) the next-line guidance string after execution — read-only projections over high-level verification/issue-export/seal state, injected into execution.py as callbacks because that lower-tier module cannot import the seal_verification/issue_export leaves directly; does not own registry persistence, phase mutation, or any write path."""
from __future__ import annotations

from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.execution import issue_terminal
from commands.collab.engine.issue_export import exported_issue_handoff_present
from commands.collab.engine.participants import (
    effective_turn_order,
    has_participant,
    reviewer_backed,
    reviewer_role,
)
from commands.collab.engine.seal_verification import (
    first_pending_participant_verification_role,
    participant_verification_enabled,
    successful_verdict,
)
from commands.collab.engine.speak_state import next_line_for_state


def close_eligible_after_execution(entry: dict, assigned_roles: list[str]) -> bool:
    roles = [role for role in assigned_roles if role != entry['moderatorRole']]
    if not roles:
        return False
    execution = entry.get('execution', {})
    completed = all(execution.get(role, {}).get('status') == 'completed' for role in roles)
    if not completed:
        return False
    if issue_terminal(entry):
        return exported_issue_handoff_present(entry)
    if reviewer_backed(entry):
        seal = entry.get('verificationSeal')
        return isinstance(seal, dict) and not seal.get('stale') and successful_verdict(entry)
    return True


def next_line_after_execution(entry: dict, assigned_roles: list[str]) -> str:
    if entry['status'] in {'closed', 'archived'}:
        return next_line_for_state(entry)
    execution = entry.get('execution', {})
    for assigned_role in effective_turn_order(entry):
        if assigned_role == entry['moderatorRole']:
            continue
        if execution.get(assigned_role, {}).get('status') != 'completed':
            return f'NEXT: Run {collab_dispatch("run plan")} for role {assigned_role}.'
    if issue_terminal(entry):
        if not exported_issue_handoff_present(entry):
            export_role = 'pe' if has_participant(entry, 'pe') else next(
                (
                    role for role in effective_turn_order(entry)
                    if role != entry['moderatorRole']
                ),
                'pe',
            )
            return f'NEXT: Run {collab_dispatch("export-issues")} for role {export_role}.'
        return next_line_for_state(entry)
    if reviewer_backed(entry):
        if participant_verification_enabled(entry):
            pending_role = first_pending_participant_verification_role(entry)
            if pending_role:
                return f'NEXT: Run {collab_dispatch("participant verify")} for role {pending_role}.'
        return f'NEXT: Run {collab_dispatch("seal verification")} for role {reviewer_role(entry)}.'
    return next_line_for_state(entry)
