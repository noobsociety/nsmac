#!/usr/bin/env python3
"""Speak-path command handlers: the auto-advance lifecycle applied when required roles have contributed (`apply_speak_lifecycle_to_entry` / `apply_speak_lifecycle_with_notice`), set the active record (`activate`), advance phase from a contributor list (`speak`), project a role's speak-readiness state (`speak-state`), advance from the live transcript (`speak-live`), append a rendered contribution (`speak-render`), rewrite the latest contribution (`rewrite-speak-render`), and retract (tombstone) the latest active-phase contribution (`retract-speak`). The five write paths cannot import the core-owned `commit_registry_and_transcript` two-file write without a cycle, so it is injected via `configure_speak_commands`; the read/notice helpers and `activate`/`speak`'s non-commit branch persist via the importable `save_registry`. Does not own the two-file commit, the speak-state projection, transcript rendering, or contribution validation."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Callable

from commands.collab.engine.advisories import print_post_action_advisories
from commands.collab.engine.command_lines import resume_command
from commands.collab.engine.config_paths import DEFAULT_ROLES_DIR
from commands.collab.engine.content_files import read_content_file, read_optional_content_file
from commands.collab.engine.contribution_store import (
    append_contribution_store_record,
    mark_contribution_store_record_retracted,
    replace_latest_contribution_store_record,
)
from commands.collab.engine.contribution_validation import (
    action_plan_label_advisory,
    enforce_contribution_budget,
    polish_moderator_content,
    validate_action_plan_executable_scope,
    validate_action_plan_shape,
    validate_conclusion_directive_gap,
    validate_effort_override,
    validate_reviewer_conclusion_gates,
)
from commands.collab.engine.dispatch_forms import collab_dispatch
from commands.collab.engine.effort import effort_phase_after_speak
from commands.collab.engine.errors import die
from commands.collab.engine.execution import seal_terminal
from commands.collab.engine.handoff_shape import parse_handoff_content, set_handoff_state
from commands.collab.engine.normalizers import format_timestamp
from commands.collab.engine.participants import (
    assert_caller_role,
    effective_turn_order,
    has_participant,
    optional_reviewer_allowed_at_round_boundary,
    participant_agent_id,
    pending_reviewer_role,
    remove_moderator_from_turn_order,
    reviewer_optional_for_phase,
    reviewer_required_for_phase,
)
from commands.collab.engine.phase_lifecycle import (
    add_completion_summary_notice,
    discussion_turn_notice,
    next_phase_name,
    print_lifecycle_diagnostic,
    print_phase_result,
    transition_notice,
)
from commands.collab.engine.registry_constants import (
    AUTO_ADVANCE_EXEMPT_PHASES,
    MOD_EXCLUDED_PHASES,
    ONE_SPEAK_PHASES,
)
from commands.collab.engine.registry_io import (
    load_registry,
    registry_lock,
    registry_revision,
    resolve_collab,
    save_registry,
)
from commands.collab.engine.seal_verification import initialize_completion_state
from commands.collab.engine.speak_state import (
    add_participation_resume_fields,
    blocked_resume_state_for_entry,
    next_line_after_speak,
    speak_state_for_entry,
)
from commands.collab.engine.transcript_readers import (
    contribution_block_bounds,
    contribution_body_lines,
    read_transcript_for_entry,
    transcript_path_for_entry,
)
from commands.collab.engine.transcript_render import (
    append_phase_block,
    contribution_store_record,
    latest_contribution_anchor,
    next_anchor_counter,
    print_header_overwrite,
    reject_full_body_details_controls,
    reject_hand_authored_excerpt_details,
    render_contribution_block,
    render_managed_header_text,
    rendered_retracted_content_block,
    replace_latest_contribution,
    reviewer_notice_for_rewrite,
)

_commit_registry_and_transcript: Callable[[Path, dict, Path, str], None] | None = None


def configure_speak_commands(
    *,
    commit_registry_and_transcript: Callable[[Path, dict, Path, str], None],
) -> None:
    """Inject the cycle-blocked dependency of the speak/render write paths: the core-owned two-file commit."""
    global _commit_registry_and_transcript
    _commit_registry_and_transcript = commit_registry_and_transcript


def _require_commit() -> Callable[[Path, dict, Path, str], None]:
    if _commit_registry_and_transcript is None:
        die('speak commands engine is not configured: commit callback missing')
    return _commit_registry_and_transcript


def die_with_resume(message: str, entry: dict, role: str) -> None:
    die(f'{message}\n{resume_command(entry, role)}')


def apply_speak_lifecycle_to_entry(
    entry: dict,
    contributors: list[str],
    transcript: str | None = None,
) -> bool:
    phase = entry['activePhase']
    order = effective_turn_order(entry)
    reviewer = reviewer_required_for_phase(entry, phase)
    required_roles = list(order)
    if reviewer:
        required_roles.append(reviewer)
    counts = {role: contributors.count(role) for role in required_roles}

    if phase in ONE_SPEAK_PHASES:
        duplicates = [role for role, count in counts.items() if count > 1]
        if duplicates:
            die(f'duplicate contribution in one-speak phase {phase}: {duplicates[0]}')
        if optional_reviewer_allowed_at_round_boundary(entry, phase, contributors, order):
            return False

    if phase in AUTO_ADVANCE_EXEMPT_PHASES or not all(counts.get(role, 0) >= 1 for role in required_roles):
        return False

    next_phase = next_phase_name(phase)
    if next_phase is None:
        return False
    if phase == 'Action Plan':
        validate_action_plan_executable_scope(transcript if transcript is not None else read_transcript_for_entry(entry))
    entry['activePhase'] = next_phase
    if next_phase in MOD_EXCLUDED_PHASES:
        remove_moderator_from_turn_order(entry, order)
    if next_phase == 'Completion' and seal_terminal(entry):
        initialize_completion_state(entry, 'execution', reset_rounds=True)
    return True


def apply_speak_lifecycle_with_notice(
    entry: dict,
    contributors: list[str],
    transcript: str | None = None,
) -> tuple[bool, dict | None]:
    from_phase = entry['activePhase']
    advanced = apply_speak_lifecycle_to_entry(entry, contributors, transcript)
    notice = transition_notice(from_phase, entry['activePhase']) if advanced else None
    if not notice and from_phase == 'Discussion':
        notice = discussion_turn_notice(entry, contributors)
    return advanced, notice


def activate_collab(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['archived']:
            die(f'registry target archived: {target}')
        data['activeCollabId'] = entry['id']
        save_registry(path, data)
    print(entry['id'])
    return 0


def speak_lifecycle(path: Path, target: str, contributors: list[str]) -> int:
    if not contributors:
        die('contributors requires at least one role')
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        for role in contributors:
            if not has_participant(entry, role):
                die(f'contributor must already be a participant: {role}')
        transcript_path = transcript_path_for_entry(entry)
        transcript = transcript_path.read_text() if transcript_path.exists() else None
        advanced, notice = apply_speak_lifecycle_with_notice(entry, contributors, transcript)
        if transcript_path.exists():
            rendered, header_changed = render_managed_header_text(transcript or '', entry, DEFAULT_ROLES_DIR)
            notice = add_completion_summary_notice(notice, rendered)
            print_header_overwrite(header_changed)
            _require_commit()(path, data, transcript_path, rendered)
        else:
            save_registry(path, data)
    print_phase_result(entry['activePhase'] if advanced else 'unchanged', notice)
    return 0


def speak_state(path: Path, target: str, role: str, resume: bool = False) -> int:
    data = load_registry(path)
    entry = resolve_collab(data, target)
    if entry['status'] in {'closed', 'archived'}:
        die('record is closed')
    if not has_participant(entry, role):
        die(f'role must already be a participant: {role}')
    transcript = read_transcript_for_entry(entry)
    pending_reviewer = pending_reviewer_role(entry)
    if pending_reviewer:
        if resume:
            state = blocked_resume_state_for_entry(entry, transcript)
            state['roleAgentId'] = participant_agent_id(entry, role)
            state['readyToWrite'] = False
            state['registryRevision'] = registry_revision(data)
            add_participation_resume_fields(state, entry, transcript, role, pending_reviewer)
            print(json.dumps(state, sort_keys=True))
            return 0
        die_with_resume(f'pending reviewerRole: {pending_reviewer}', entry, role)
    state = speak_state_for_entry(entry, transcript)
    state['roleAgentId'] = participant_agent_id(entry, role)
    state['readyToWrite'] = role in state['allowedRoles']
    state['registryRevision'] = registry_revision(data)
    if resume:
        add_participation_resume_fields(state, entry, transcript, role)
        print(json.dumps(state, sort_keys=True))
        return 0
    if role not in state['allowedRoles']:
        if role == reviewer_optional_for_phase(entry, entry['activePhase']):
            die_with_resume('reviewer may speak after all turn-order participants have contributed in this round', entry, role)
        die_with_resume(f"expected role: {state['expectedRole']}", entry, role)
    print(json.dumps(state, sort_keys=True))
    return 0


def speak_lifecycle_live(path: Path, target: str) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        state = speak_state_for_entry(entry, transcript)
        advanced, notice = apply_speak_lifecycle_with_notice(entry, state['contributors'], transcript)
        rendered, header_changed = render_managed_header_text(transcript, entry, DEFAULT_ROLES_DIR)
        print_header_overwrite(header_changed)
        _require_commit()(path, data, transcript_path, rendered)
    print_phase_result(entry['activePhase'] if advanced else 'unchanged', notice)
    return 0


def render_speak(
    path: Path,
    target: str,
    role: str,
    content_file: Path,
    full_body_file: Path | None = None,
    observed_revision: int | None = None,
    timestamp: str | None = None,
    emit_json: bool = False,
    caller_role: str | None = None,
    verbatim: bool = False,
) -> int:
    content = read_content_file(content_file)
    full_body = read_optional_content_file(full_body_file)
    with registry_lock(path):
        data = load_registry(path)
        current_entry = resolve_collab(data, target)
        assert_caller_role(current_entry, caller_role, 'speak-render', role)
        if current_entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if current_entry['activePhase'] == 'Completion':
            die('speak-render is not permitted in Completion')
        if not has_participant(current_entry, role):
            die(f'role must already be a participant: {role}')
        live_revision = registry_revision(data)
        resume = resume_command(current_entry, role)
        if observed_revision is None:
            die(f'speak-render requires --observed-revision\n{resume}')
        if observed_revision != live_revision:
            die(
                f'stale registry revision: observed {observed_revision}, live {live_revision}\n'
                f'{resume}'
            )

        transcript_path = transcript_path_for_entry(current_entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        pending_reviewer = pending_reviewer_role(current_entry)
        if pending_reviewer:
            die(f'pending reviewerRole: {pending_reviewer}\n{resume}')
        state = speak_state_for_entry(current_entry, transcript)
        if role not in state['allowedRoles']:
            if role == reviewer_optional_for_phase(current_entry, current_entry['activePhase']):
                die(
                    'reviewer may speak after all turn-order participants have contributed in this round\n'
                    f'{resume}'
                )
            die(f"expected role: {state['expectedRole']}\n{resume}")
        phase = current_entry['activePhase']
        if phase in ONE_SPEAK_PHASES and role in state['contributors']:
            die(f'duplicate phase contribution: {role} in {phase}\n{resume}')
        if role == current_entry['moderatorRole'] and not verbatim:
            content = polish_moderator_content(content)
        reject_hand_authored_excerpt_details(content)
        reject_full_body_details_controls(full_body)
        enforce_contribution_budget(content, phase, role, current_entry['moderatorRole'], verbatim)
        validate_effort_override(content, phase, role, current_entry['moderatorRole'])
        validate_conclusion_directive_gap(content, phase)
        validate_reviewer_conclusion_gates(content, phase, role, current_entry)
        validate_action_plan_shape(content, phase)
        handoff_state = parse_handoff_content(content) if phase == 'Handoff' else None

        lines = transcript.splitlines()
        counter = next_anchor_counter(lines, phase, role)
        render_timestamp = timestamp or format_timestamp()
        anchor, block = render_contribution_block(
            phase,
            role,
            counter,
            content,
            render_timestamp,
            full_body,
        )
        contribution_record = contribution_store_record(
            phase,
            role,
            anchor,
            content,
            render_timestamp,
            full_body,
        )
        rendered_lines = append_phase_block(lines, phase, block)

        nextdata = deepcopy(data)
        next_entry = resolve_collab(nextdata, target)
        if handoff_state is not None:
            set_handoff_state(next_entry, role, handoff_state)
        rendered_text = '\n'.join(rendered_lines) + '\n'
        rendered_state = speak_state_for_entry(next_entry, rendered_text)
        advanced, notice = apply_speak_lifecycle_with_notice(next_entry, rendered_state['contributors'], rendered_text)
        rendered_text, header_changed = render_managed_header_text(rendered_text, next_entry, DEFAULT_ROLES_DIR)
        notice = add_completion_summary_notice(notice, rendered_text)
        print('BOUNDARY: transcript write only; no shell commands or source edits outside the user-scope collab state root')
        print('SUCCINCTLY: stay within role concerns; do not pad or summarize other roles')
        print(f'RETRACT: use {collab_dispatch("retract speak")} to tombstone the latest active-phase contribution')
        print_header_overwrite(header_changed)
        label_advisory = action_plan_label_advisory(content, phase)
        if label_advisory:
            print(label_advisory)
        _require_commit()(path, nextdata, transcript_path, rendered_text)
        append_contribution_store_record(path, next_entry, contribution_record)
    print_post_action_advisories(
        next_entry,
        role,
        effort_phase_after_speak(phase),
        notice,
        next_line_after_speak(next_entry, role, phase, rendered_text),
    )
    lifecycle = {'phaseState': next_entry['activePhase'] if advanced else 'unchanged'}
    if notice:
        lifecycle['notice'] = notice
    print('appended')
    print_lifecycle_diagnostic(lifecycle, emit_json)
    return 0


def render_re_speak(
    path: Path,
    target: str,
    role: str,
    content_file: Path,
    full_body_file: Path | None = None,
    timestamp: str | None = None,
    caller_role: str | None = None,
    verbatim: bool = False,
) -> int:
    content = read_content_file(content_file)
    full_body = read_optional_content_file(full_body_file)
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'rewrite-speak-render', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] == 'Completion':
            die('rewrite-speak-render is not permitted in Completion')
        if not has_participant(entry, role):
            die(f'role must already be a participant: {role}')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        phase = entry['activePhase']
        if role == entry['moderatorRole'] and not verbatim:
            content = polish_moderator_content(content)
        reject_hand_authored_excerpt_details(content)
        reject_full_body_details_controls(full_body)
        enforce_contribution_budget(content, phase, role, entry['moderatorRole'], verbatim)
        validate_effort_override(content, phase, role, entry['moderatorRole'])
        validate_conclusion_directive_gap(content, phase)
        validate_reviewer_conclusion_gates(content, phase, role, entry)
        validate_action_plan_shape(content, phase)
        handoff_state = parse_handoff_content(content) if phase == 'Handoff' else None
        reviewer_notice = reviewer_notice_for_rewrite(entry, transcript, role)
        render_timestamp = timestamp or format_timestamp()
        rendered = replace_latest_contribution(
            transcript,
            phase,
            role,
            content,
            render_timestamp,
            full_body,
        )
        replacement_record = contribution_store_record(
            phase,
            role,
            latest_contribution_anchor(rendered, phase, role),
            content,
            render_timestamp,
            full_body,
        )
        if handoff_state is not None:
            rendered_lines = rendered.splitlines()
            bounds = contribution_block_bounds(rendered_lines, phase, role)
            if bounds is None:
                die(f'no prior contribution to rewrite; use {collab_dispatch("speak")} to create the first contribution')
            start, end = bounds
            handoff_state['body'] = '\n'.join(contribution_body_lines(rendered_lines[start:end])).rstrip('\n')
            set_handoff_state(entry, role, handoff_state)
            rendered, header_changed = render_managed_header_text(rendered, entry, DEFAULT_ROLES_DIR)
            print_header_overwrite(header_changed)
        _require_commit()(path, data, transcript_path, rendered)
        replace_latest_contribution_store_record(path, entry, phase, role, replacement_record)
    if reviewer_notice:
        print(reviewer_notice)
    print_post_action_advisories(
        entry,
        role,
        effort_phase_after_speak(phase),
        None,
        next_line_after_speak(entry, role, phase, rendered),
    )
    print(entry['id'])
    return 0


def retract_latest_contribution(
    path: Path,
    target: str,
    role: str,
    reason: str | None,
    timestamp: str | None = None,
    caller_role: str | None = None,
) -> int:
    with registry_lock(path):
        data = load_registry(path)
        entry = resolve_collab(data, target)
        assert_caller_role(entry, caller_role, 'retract-speak', role)
        if entry['status'] in {'closed', 'archived'}:
            die('record is closed')
        if entry['activePhase'] == 'Completion':
            die('retract-speak is not permitted after Completion')
        if not has_participant(entry, role):
            die(f'role must already be a participant: {role}')
        transcript_path = transcript_path_for_entry(entry)
        if not transcript_path.exists():
            die(f'transcript missing: {transcript_path}')
        transcript = transcript_path.read_text()
        lines = transcript.splitlines()
        bounds = contribution_block_bounds(lines, entry['activePhase'], role)
        if bounds is None:
            die(f'no contribution found for {role} in {entry["activePhase"]}')
        start, end = bounds
        anchor = latest_contribution_anchor(transcript, entry['activePhase'], role)
        block = lines[start:end]
        marker_index: int | None = None
        for index, line in enumerate(block):
            if line.strip() == '<!-- collab:content-only; do-not-execute -->':
                marker_index = index
                break
        if marker_index is None:
            die('contribution content marker missing')
        existing_body = '\n'.join(block[marker_index + 1:len(block) - 1]).strip()
        if existing_body.startswith('RETRACTED:'):
            die(f'contribution already retracted for {role} in {entry["activePhase"]}')
        summary = reason.strip() if reason and reason.strip() else 'No reason supplied'
        stamp = timestamp or format_timestamp()
        tombstone = [
            'RETRACTED: contribution withdrawn; retained for audit history.',
            f'RETRACTION REASON: {summary}',
            f'RETRACTION TIMESTAMP: {stamp}',
            '',
            *rendered_retracted_content_block(existing_body),
        ]
        replacement = block[:marker_index + 1] + [''] + tombstone + [''] + [block[-1]]
        rendered = '\n'.join(lines[:start] + replacement + lines[end:]) + '\n'
        _require_commit()(path, data, transcript_path, rendered)
        mark_contribution_store_record_retracted(path, entry, anchor, summary, stamp)
    print(entry['id'])
    print('retracted')
    return 0
